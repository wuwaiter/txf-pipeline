"""
shioaji.py
----------
Shioaji API 服務，負責：
1. 登入與訂閱
2. 接收即時 Tick 報價並寫入 Redis Stream
3. 定期檢查 API 使用量並視情況寫入 InfluxDB
4. 處理手動重連與頁面刷新的指令
5. 動態重載訂閱清單（reload 指令）
"""
import time
import logging
import os
import threading
import datetime
import shioaji as sj
import tomli
from influxdb_client import Point

from app.config import (
    REDIS_STREAM_KEY, INFLUXDB_MONITORING_BUCKET,
    SHIOAJI_API_KEY, SHIOAJI_SECRET_KEY, SHIOAJI_SIMULATION,
    SHIOAJI_FUTURES, SHIOAJI_STOCKS,
)
from app.services.redis_client import get_redis_client
from app.services.influx_client import get_write_api

# ── config.toml 路徑（用於動態重載）──────────────────────────────────
_TOML_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config.toml")

# ── 目前已訂閱合約的 contract 物件（code -> contract）────────────────
_subscribed_fop: dict = {}  # 期貨：code -> contract
_subscribed_stk: dict = {}  # 股票：code -> contract

# ── Logging：將 shioaji 套件 log 輸出導向 logs/ 資料夾 ──────────────
_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs")
os.makedirs(_LOG_DIR, exist_ok=True)
_log_handler = logging.FileHandler(os.path.join(_LOG_DIR, "shioaji.log"))
_log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logging.getLogger("shioaji").addHandler(_log_handler)
logging.getLogger("shioaji").setLevel(logging.INFO)
# ─────────────────────────────────────────────────────────────────────

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
    """初始訂閱所有 config 中定義的合約，並記錄到 _subscribed_fop / _subscribed_stk。"""
    global _subscribed_fop, _subscribed_stk
    print(">>> Subscribing to contracts...")
    # SHIOAJI_FUTURES: dict[category, list[{id, name}]]
    for category, contracts in SHIOAJI_FUTURES.items():
        future_cat = getattr(api.Contracts.Futures, category, None)
        if future_cat is None:
            print(f">>> [Futures] Unknown category: {category}")
            continue
        for item in contracts:
            try:
                contract = future_cat[item["id"]]
                api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.Tick, version=sj.constant.QuoteVersion.v1)
                _subscribed_fop[item["id"]] = contract
            except Exception as e:
                print(f">>> [Futures/{category}] Failed to sub {item.get('id')}: {e}")
    for item in SHIOAJI_STOCKS:
        try:
            contract = api.Contracts.Stocks[item["id"]]
            api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.Tick, version=sj.constant.QuoteVersion.v1)
            _subscribed_stk[item["id"]] = contract
        except Exception as e:
            print(f">>> [Stocks] Failed to sub {item.get('id')}: {e}")


def reload_subscriptions(api):
    """
    動態重載訂閱清單（不重新登入）：
    - 重新讀取 config.toml
    - 對移除的合約執行 unsubscribe
    - 對新增的合約執行 subscribe
    - 更新 _subscribed_fop / _subscribed_stk
    """
    global _subscribed_fop, _subscribed_stk
    print(">>> [Reload] Reloading subscription list from config.toml...")
    try:
        with open(_TOML_PATH, "rb") as f:
            cfg = tomli.load(f)
    except Exception as e:
        print(f">>> [Reload] Failed to read config.toml: {e}")
        return

    new_futures: dict = cfg.get("shioaji", {}).get("futures", {})
    new_stocks: list = cfg.get("shioaji", {}).get("stocks", [])

    # 建立新清單的 code set（期貨） + category 對照表
    new_fop_ids: dict[str, str] = {}  # code -> category
    for category, contracts in new_futures.items():
        for item in contracts:
            new_fop_ids[item["id"]] = category

    new_stk_ids: set[str] = {item["id"] for item in new_stocks}

    # ── 期貨：unsubscribe 已移除的 ──────────────────────────────────
    for code in list(_subscribed_fop.keys()):
        if code not in new_fop_ids:
            try:
                api.quote.unsubscribe(_subscribed_fop[code], quote_type=sj.constant.QuoteType.Tick, version=sj.constant.QuoteVersion.v1)
                print(f">>> [Reload] Unsubscribed futures: {code}")
            except Exception as e:
                print(f">>> [Reload] Failed to unsub futures {code}: {e}")
            del _subscribed_fop[code]

    # ── 期貨：subscribe 新增的 ──────────────────────────────────────
    for code, category in new_fop_ids.items():
        if code not in _subscribed_fop:
            try:
                future_cat = getattr(api.Contracts.Futures, category, None)
                if future_cat is None:
                    print(f">>> [Reload] Unknown futures category: {category}")
                    continue
                contract = future_cat[code]
                api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.Tick, version=sj.constant.QuoteVersion.v1)
                _subscribed_fop[code] = contract
                print(f">>> [Reload] Subscribed futures: {code} ({category})")
            except Exception as e:
                print(f">>> [Reload] Failed to sub futures {code}: {e}")

    # ── 股票：unsubscribe 已移除的 ──────────────────────────────────
    for code in list(_subscribed_stk.keys()):
        if code not in new_stk_ids:
            try:
                api.quote.unsubscribe(_subscribed_stk[code], quote_type=sj.constant.QuoteType.Tick, version=sj.constant.QuoteVersion.v1)
                print(f">>> [Reload] Unsubscribed stock: {code}")
            except Exception as e:
                print(f">>> [Reload] Failed to unsub stock {code}: {e}")
            del _subscribed_stk[code]

    # ── 股票：subscribe 新增的 ──────────────────────────────────────
    for item in new_stocks:
        code = item["id"]
        if code not in _subscribed_stk:
            try:
                contract = api.Contracts.Stocks[code]
                api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.Tick, version=sj.constant.QuoteVersion.v1)
                _subscribed_stk[code] = contract
                print(f">>> [Reload] Subscribed stock: {code}")
            except Exception as e:
                print(f">>> [Reload] Failed to sub stock {code}: {e}")

    print(">>> [Reload] Done.")


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
        elif cmd == b"reload":
            r.delete(f"{REDIS_STREAM_KEY}:cmd")
            print(">>> [Manual] Subscription reload requested.")
            reload_subscriptions(api)
        elif cmd == b"check_usage":
            r.delete(f"{REDIS_STREAM_KEY}:cmd")
            print(">>> [Schedule] Executing usage check (write InfluxDB).")
            check_and_update_status(write_influx=True)
