"""
ScheduleTask.py
---------------
Celery 定時排程任務：
1. OHLC 聚合計算 (1m / 5m / 60m) -> 寫入 InfluxDB
2. 定期清理 Redis Stream
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
write_api = get_write_api()

celery_app = Celery("collector", broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
celery_app.conf.beat_schedule = {
    # 每分鐘第 0 秒觸發
    "agg-1m":  {"task": "app.workers.ScheduleTask.agg_1m",  "schedule": crontab()},
    # 每5分鐘整點觸發 (0,5,10,...,55)
    "agg-5m":  {"task": "app.workers.ScheduleTask.agg_5m",  "schedule": crontab(minute="0,5,10,15,20,25,30,35,40,45,50,55")},
    # 每小時整點觸發
    "agg-60m": {"task": "app.workers.ScheduleTask.agg_60m", "schedule": crontab(minute="0")},
    # 每分鐘觸發清理 Redis
    "trim-streams": {"task": "app.workers.ScheduleTask.trim_streams", "schedule": crontab()},
    # 每分鐘觸發流量檢查
    "check-usage": {"task": "app.workers.ScheduleTask.check_usage", "schedule": crontab()},
}
celery_app.conf.timezone = "Asia/Taipei"

# ── Aggregation helpers ───────────────────────────────────────────
def _aggregate_and_write(seconds: int, interval: str):
    now = int(time.time())
    # 計算時間範圍的起始時間戳 (毫秒)，用於 Stream 查詢
    start_ts_ms = (now - seconds) * 1000

    fop_prefix = f"{REDIS_STREAM_KEY}:fop:".encode()
    stk_prefix = f"{REDIS_STREAM_KEY}:stk:".encode()

    try:
        # 使用 scan_iter 避免在大量 keys 時阻塞 Redis
        for b_key in r.scan_iter(f"{REDIS_STREAM_KEY}:*"):
            market = None
            if b_key.startswith(fop_prefix):
                market = "futures"
            elif b_key.startswith(stk_prefix):
                market = "stocks"
            else:
                continue

            # 直接利用 Redis Stream 的時間範圍查詢，大幅提升效率。
            # 此作法假設 Stream ID 是由 Redis 自動生成的時間戳 ID。
            data = r.xrange(b_key, min=f"{start_ts_ms}-0", max="+")
            if not data:
                continue

            prices = [float(dict(e[1])[b"price"]) for e in data]

            ohlc = {"open": prices[0], "high": max(prices), "low": min(prices), "close": prices[-1]}
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
    except Exception as e:
        print(f"Error during aggregation for interval {interval}: {e}")


# ── Celery tasks ──────────────────────────────────────────────────
@celery_app.task
def trim_streams():
    """定期清理 Redis Stream，維持約 100,000 筆最新報價"""
    fop_prefix = f"{REDIS_STREAM_KEY}:fop:".encode()
    stk_prefix = f"{REDIS_STREAM_KEY}:stk:".encode()

    try:
        # 使用 scan_iter 迭代鍵，避免 KEYS 指令阻塞 Redis
        for b_key in r.scan_iter(f"{REDIS_STREAM_KEY}:*"):
            if b_key.startswith(fop_prefix) or b_key.startswith(stk_prefix):
                try:
                    # ~100,000: 大約保留的大小
                    r.xtrim(b_key, maxlen=100000, approximate=True)
                except Exception as e:
                    print(f"Failed to trim {b_key.decode()}: {e}")
    except Exception as e:
        print(f"Redis err during key scan: {e}")

@celery_app.task
def check_usage():
    """定期觸發流量檢查 (發送命令給 collector)"""
    try:
        r.set(f"{REDIS_STREAM_KEY}:cmd", "check_usage")
    except Exception as e:
        print(f"Failed to set check_usage cmd: {e}")

@celery_app.task
def agg_1m():
    _aggregate_and_write(60, "1m")


@celery_app.task
def agg_5m():
    _aggregate_and_write(300, "5m")


@celery_app.task
def agg_60m():
    _aggregate_and_write(3600, "60m")
