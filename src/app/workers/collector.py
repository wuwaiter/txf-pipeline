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
    api.login(SHIOAJI_API_KEY, SHIOAJI_SECRET_KEY)
    contract = api.Contracts.Futures.TXF.TXFR1
    api.quote.subscribe(contract, quote_type="tick")

    @api.on_tick_fop_v1()
    def on_tick(exchange, tick):
        r.xadd(REDIS_STREAM_KEY, {"price": tick.close, "ts": int(time.time())}, maxlen=10000)

    while True:
        time.sleep(1)


# ── Aggregation helpers ───────────────────────────────────────────
def _get_ticks(seconds: int) -> list:
    now = int(time.time())
    data = r.xrange(REDIS_STREAM_KEY, min="-", max="+")
    return [
        float(dict(e[1])[b"price"])
        for e in data
        if now - int(dict(e[1])[b"ts"]) <= seconds
    ]


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
