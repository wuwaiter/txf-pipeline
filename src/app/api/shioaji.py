"""
shioaji.py
----------
Shioaji API 服務，負責：
1. 登入與訂閱
2. 接收即時 Tick 報價並寫入 Redis Stream
3. 定期檢查 API 使用量並視情況寫入 InfluxDB
4. 處理手動重連與頁面刷新的指令
"""
import time
import threading
import datetime
import shioaji as sj
from influxdb_client import Point

from app.config import (
    REDIS_STREAM_KEY, INFLUXDB_MONITORING_BUCKET,
    SHIOAJI_API_KEY, SHIOAJI_SECRET_KEY, SHIOAJI_SIMULATION,
    SHIOAJI_FUTURES, SHIOAJI_STOCKS,
)
from app.services.redis_client import get_redis_client
from app.services.influx_client import get_write_api

r = get_redis_client(decode_responses=False)
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
            api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.Tick, version=sj.constant.QuoteVersion.v1)
        except Exception as e:
            print(f">>> [Futures] Failed to sub {item.get('id')}: {e}")
    for item in SHIOAJI_STOCKS:
        try:
            contract = api.Contracts.Stocks[item["id"]]
            api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.Tick, version=sj.constant.QuoteVersion.v1)
        except Exception as e:
            print(f">>> [Stocks] Failed to sub {item.get('id')}: {e}")

def run_shioaji_ingest():
    api = sj.Shioaji(simulation=SHIOAJI_SIMULATION)

    @api.on_tick_fop_v1()
    def on_tick_fop(exchange, tick):
        """處理期貨(Futures) Tick，寫入 Redis Stream"""
        stream_key = f"{REDIS_STREAM_KEY}:fop:{tick.code}"
        r.xadd(stream_key, {"price": str(tick.close), "ts": str(int(time.time()))})

    @api.on_tick_stk_v1()
    def on_tick_stk(exchange, tick):
        """處理股票(Stock) Tick，寫入 Redis Stream"""
        stream_key = f"{REDIS_STREAM_KEY}:stk:{tick.code}"
        r.xadd(stream_key, {"price": str(tick.close), "ts": str(int(time.time()))})

    def check_and_update_status(write_influx: bool = False):
        """更新連線狀態與使用量。write_influx=True 時才寫入 InfluxDB monitoring bucket。"""
        current_status = r.get(f"{REDIS_STREAM_KEY}:status")
        try:
            if current_status != b"connected":
                perform_login(api)
            usage = api.usage()
            used_bytes = usage.limit_bytes - usage.remaining_bytes
            r.set(f"{REDIS_STREAM_KEY}:usage_bytes", used_bytes)
            r.set(f"{REDIS_STREAM_KEY}:limit_bytes", usage.limit_bytes)
            print(f">>> [Check] bytes={usage.bytes}, remaining_bytes={usage.remaining_bytes}, limit={usage.limit_bytes} | write_influx={write_influx}")
            
            if write_influx:
                try:
                    point = (
                        Point("shioaji_usage")
                        .field("bytes_used", int(used_bytes))
                        .field("bytes_limit", int(usage.limit_bytes))
                        .field("bytes_remaining", int(usage.remaining_bytes))
                    )
                    write_api.write(bucket=INFLUXDB_MONITORING_BUCKET, record=point)
                    print(f">>> [Monitor] Usage written to InfluxDB monitoring bucket")
                except Exception as influx_err:
                    print(f">>> [Monitor] Failed to write usage to InfluxDB: {influx_err}")
            
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
    check_and_update_status(write_influx=False)

    while True:
        time.sleep(5)
        cmd = r.get(f"{REDIS_STREAM_KEY}:cmd")
        if cmd == b"login":
            r.delete(f"{REDIS_STREAM_KEY}:cmd")
            print(">>> [Manual] Reconnect requested.")
            check_and_update_status(write_influx=False)
        elif cmd == b"usage":
            r.delete(f"{REDIS_STREAM_KEY}:cmd")
            print(">>> [Page] Usage refresh requested (no InfluxDB write).")
            check_and_update_status(write_influx=False)
        elif cmd == b"check_usage":
            r.delete(f"{REDIS_STREAM_KEY}:cmd")
            print(">>> [Schedule] Executing usage check (write InfluxDB).")
            check_and_update_status(write_influx=True)
