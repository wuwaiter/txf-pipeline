"""
collector.py
------------
整合三大職責：
1. Shioaji Tick 即時報價擷取 -> 寫入 Redis Stream
2. Celery定時排程 (1m / 5m / 60m)
3. OHLC聚合計算 -> 寫入 InfluxDB
"""
import time
import shioaji as sj
from celery import Celery
from influxdb_client import Point

from app.config import (
    REDIS_STREAM_KEY, INFLUXDB_BUCKET,
    SHIOAJI_API_KEY, SHIOAJI_SECRET_KEY, SHIOAJI_SIMULATION,
    SHIOAJI_FUTURES, SHIOAJI_STOCKS,
    REDIS_HOST, REDIS_PORT,
)
from app.services.redis_client import get_redis_client
from app.services.influx_client import get_write_api

r = get_redis_client(decode_responses=False)

celery_app = Celery("collector", broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
celery_app.conf.beat_schedule = {
    "agg-1m":  {"task": "app.workers.collector.agg_1m",  "schedule": 60},
    "agg-5m":  {"task": "app.workers.collector.agg_5m",  "schedule": 300},
    "agg-60m": {"task": "app.workers.collector.agg_60m", "schedule": 3600},
}

write_api = get_write_api()


def perform_login(api):
    if not SHIOAJI_API_KEY:
        print(">>> ERROR: SHIOAJI_API_KEY not found in .env")
        return False
    print(f">>> API Key detected: {SHIOAJI_API_KEY[:4]}****")
    try:
        api.login(
            SHIOAJI_API_KEY,
            SHIOAJI_SECRET_KEY,
            contracts_cb=lambda x: print("Contracts loaded."),
            contracts_timeout=10000,
        )
        print(">>> Shioaji Login Called")
        time.sleep(5)
        return True
    except Exception as e:
        print(f">>> Login Error: {e}")
        return False

def perform_subscribe(api):
    print(">>> Subscribing to contracts...")
    for item in SHIOAJI_FUTURES:
        try:
            future_cat = getattr(api.Contracts.Futures, item["category"])
            contract   = future_cat[item["id"]]
            api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.Quote, version=sj.constant.QuoteVersion.v1)
        except Exception as e:
            print(f">>> [Futures] Failed to sub {item.get('id')}: {e}")
    for item in SHIOAJI_STOCKS:
        try:
            contract = api.Contracts.Stocks[item["id"]]
            api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.Quote, version=sj.constant.QuoteVersion.v1)
        except Exception as e:
            print(f">>> [Stocks] Failed to sub {item.get('id')}: {e}")

# ── Ingest ────────────────────────────────────────────────────────
def run_ingest():
    api = sj.Shioaji(simulation=SHIOAJI_SIMULATION)

    # ── 4. Quote Callbacks ───────────────────────────────────────────────────
    @api.on_quote_fop_v1()
    def on_quote_fop(exchange, quote):
        """處理期貨(Futures) Quote，寫入 Redis Stream"""
        stream_key = f"{REDIS_STREAM_KEY}:fop:{quote.code}"
        r.xadd(stream_key, {"price": str(quote.close), "ts": str(int(time.time()))}, maxlen=10000)

    @api.on_quote_stk_v1()
    def on_quote_stk(exchange, quote):
        """處理股票(Stock) Quote，寫入 Redis Stream"""
        stream_key = f"{REDIS_STREAM_KEY}:stk:{quote.code}"
        r.xadd(stream_key, {"price": str(quote.close), "ts": str(int(time.time()))}, maxlen=10000)

    def check_and_update_status():
        current_status = r.get(f"{REDIS_STREAM_KEY}:status")
        try:
            if current_status != b"connected":
                perform_login(api)
            usage = api.usage()
            print(f">>> [Check] Quota limit: {usage.limit_bytes}, remaining: {usage.remaining_bytes}")
            if usage.remaining_bytes <= 0:
                print(">>> [Monitor] Quota = 0, executing logout()...")
                api.logout()
                r.set(f"{REDIS_STREAM_KEY}:status", "disconnected")
            else:
                if current_status != b"connected":
                    print(">>> [Monitor] Quota > 0, subscribing...")
                    perform_subscribe(api)
                    r.set(f"{REDIS_STREAM_KEY}:status", "connected")
        except Exception as e:
            print(f">>> [Monitor] Error checking usage: {e}")
            r.set(f"{REDIS_STREAM_KEY}:status", "disconnected")

    print(">>> Initializing connection...")
    check_and_update_status()

    ticks = 0
    while True:
        time.sleep(1)
        ticks += 1
        
        # 手動 UI 重連
        cmd = r.get(f"{REDIS_STREAM_KEY}:cmd")
        if cmd == b"login":
            r.delete(f"{REDIS_STREAM_KEY}:cmd")
            print(">>> [Manual] Reconnect requested.")
            check_and_update_status()
            
        # 每 10 分鐘自動檢查 (600秒)
        if ticks >= 600:
            ticks = 0
            print(">>> [10-min Check] Executing usage check...")
            check_and_update_status()


# ── Aggregation helpers ───────────────────────────────────────────
def _get_ticks(seconds: int) -> list:
    """從所有期貨合約的 Redis Stream 讀取最近 N 秒的 price 清單"""
    now = int(time.time())
    prices = []
    for item in SHIOAJI_FUTURES:
        stream_key = f"{REDIS_STREAM_KEY}:fop:{item['id']}"
        data = r.xrange(stream_key, min="-", max="+")
        prices.extend([
            float(dict(e[1])[b"price"])
            for e in data
            if now - int(dict(e[1])[b"ts"]) <= seconds
        ])
    return prices


def _build_ohlc(prices: list) -> dict:
    return {"open": prices[0], "high": max(prices), "low": min(prices), "close": prices[-1]}


def _write_influx(interval: str, ohlc: dict):
    point = (
        Point("txf").tag("interval", interval)
        .field("open", ohlc["open"]).field("high", ohlc["high"])
        .field("low", ohlc["low"]).field("close", ohlc["close"])
    )
    write_api.write(bucket=INFLUXDB_BUCKET, record=point)


# ── Celery tasks ──────────────────────────────────────────────────
@celery_app.task
def agg_1m():
    prices = _get_ticks(60)
    if prices: _write_influx("1m", _build_ohlc(prices))


@celery_app.task
def agg_5m():
    prices = _get_ticks(300)
    if prices: _write_influx("5m", _build_ohlc(prices))


@celery_app.task
def agg_60m():
    prices = _get_ticks(3600)
    if prices: _write_influx("60m", _build_ohlc(prices))


if __name__ == "__main__":
    run_ingest()
