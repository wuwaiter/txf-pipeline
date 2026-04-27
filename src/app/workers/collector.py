"""
collector.py
------------
整合三大職責：
1. Shioaji Tick 即時報價擷取 -> 寫入 Redis Stream
2. Celery定時排程 (1m / 5m / 60m)
3. OHLC聚合計算 -> 寫入 InfluxDB
"""
import time
from celery import Celery
from celery.schedules import crontab
from influxdb_client import Point

from app.config import (
    REDIS_STREAM_KEY, INFLUXDB_BUCKET,
    REDIS_HOST, REDIS_PORT,
)
from app.services.redis_client import get_redis_client
from app.services.influx_client import get_write_api

r = get_redis_client(decode_responses=False)

celery_app = Celery("collector", broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
celery_app.conf.beat_schedule = {
    # 每分鐘第 0 秒觸發
    "agg-1m":  {"task": "app.workers.collector.agg_1m",  "schedule": crontab()},
    # 每5分鐘整點觸發 (0,5,10,...,55)
    "agg-5m":  {"task": "app.workers.collector.agg_5m",  "schedule": crontab(minute="0,5,10,15,20,25,30,35,40,45,50,55")},
    # 每小時整點觸發
    "agg-60m": {"task": "app.workers.collector.agg_60m", "schedule": crontab(minute="0")},
}
celery_app.conf.timezone = "Asia/Taipei"

write_api = get_write_api()





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
    from app.api.shioaji import run_shioaji_ingest
    run_shioaji_ingest()
