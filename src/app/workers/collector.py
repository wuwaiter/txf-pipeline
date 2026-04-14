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


# ── Ingest ────────────────────────────────────────────────────────
def run_ingest():
    api = sj.Shioaji(simulation=SHIOAJI_SIMULATION)

    # ── 1. 登入（依 SKILL 標準寫法）──────────────────────────────────
    if not SHIOAJI_API_KEY:
        print(">>> ERROR: SHIOAJI_API_KEY not found in .env")
        return

    print(f">>> API Key detected: {SHIOAJI_API_KEY[:4]}****")
    api.login(
        SHIOAJI_API_KEY,
        SHIOAJI_SECRET_KEY,
        contracts_cb=lambda x: print("Contracts loaded."),
        contracts_timeout=10000,
    )
    print(">>> Shioaji Login Successful")
    print(api.usage())
    time.sleep(5)  # 等待合約下載穩定

    # ── 2. 期貨訂閱清單（來自 config.toml [[shioaji.futures]]）──────────────
    for item in SHIOAJI_FUTURES:
        try:
            future_cat = getattr(api.Contracts.Futures, item["category"])
            contract   = future_cat[item["id"]]
            api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.Tick)
            api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.BidAsk)
            print(f">>> [Futures] Subscribed: {item['name']} ({item['category']}/{item['id']})")
        except Exception as e:
            print(f">>> [Futures] Failed to subscribe {item.get('name', item)}: {e}")

    # ── 3. 股票訂閱清單（來自 config.toml [[shioaji.stocks]]）───────────────
    for item in SHIOAJI_STOCKS:
        try:
            contract = api.Contracts.Stocks[item["id"]]
            api.quote.subscribe(
                contract,
                quote_type=sj.constant.QuoteType.Tick,
                version=sj.constant.QuoteVersion.v1,
            )
            api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.BidAsk)
            print(f">>> [Stocks]  Subscribed: {item['name']} ({item['id']})")
        except Exception as e:
            print(f">>> [Stocks]  Failed to subscribe {item.get('name', item)}: {e}")

    # ── 4. Tick Callbacks ────────────────────────────────────────────────────
    @api.on_tick_fop_v1()
    def on_tick_fop(exchange, tick):
        """處理期貨(Futures) Tick，寫入 Redis Stream"""
        stream_key = f"{REDIS_STREAM_KEY}:fop:{tick.code}"
        r.xadd(stream_key, {"price": str(tick.close), "ts": str(int(time.time()))}, maxlen=10000)

    @api.on_tick_stk_v1()
    def on_tick_stk(exchange, tick):
        """處理股票(Stock) Tick，寫入 Redis Stream"""
        stream_key = f"{REDIS_STREAM_KEY}:stk:{tick.code}"
        r.xadd(stream_key, {"price": str(tick.close), "ts": str(int(time.time()))}, maxlen=10000)

    while True:
        time.sleep(1)


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
