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
            r.set(f"{REDIS_STREAM_KEY}:usage_bytes", usage.bytes)
            r.set(f"{REDIS_STREAM_KEY}:limit_bytes", usage.limit_bytes)
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
def _aggregate_and_write(seconds: int, interval: str):
    now = int(time.time())
    try:
        all_keys = r.keys(f"{REDIS_STREAM_KEY}:*")
    except Exception as e:
        print(f"Redis err: {e}")
        return

    fop_prefix = f"{REDIS_STREAM_KEY}:fop:".encode()
    stk_prefix = f"{REDIS_STREAM_KEY}:stk:".encode()

    for b_key in all_keys:
        if not (b_key.startswith(fop_prefix) or b_key.startswith(stk_prefix)):
            continue
            
        data = r.xrange(b_key, min="-", max="+")
        prices = [
            float(dict(e[1])[b"price"])
            for e in data
            if now - int(dict(e[1])[b"ts"]) <= seconds
        ]
        if not prices:
            continue
            
        ohlc = {"open": prices[0], "high": max(prices), "low": min(prices), "close": prices[-1]}
        market = "futures" if b_key.startswith(fop_prefix) else "stocks"
        code = b_key.split(b":")[-1].decode()
        
        point = (
            Point("txf")
            .tag("interval", interval)
            .tag("market", market)
            .tag("code", code)
            .field("open", ohlc["open"])
            .field("high", ohlc["high"])
            .field("low", ohlc["low"])
            .field("close", ohlc["close"])
        )
        write_api.write(bucket=INFLUXDB_BUCKET, record=point)


# ── Celery tasks ──────────────────────────────────────────────────
@celery_app.task
def agg_1m():
    _aggregate_and_write(60, "1m")


@celery_app.task
def agg_5m():
    _aggregate_and_write(300, "5m")


@celery_app.task
def agg_60m():
    _aggregate_and_write(3600, "60m")


if __name__ == "__main__":
    run_ingest()
