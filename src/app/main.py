import os
import time
import json
import math
import threading
import tomli
import tomli_w
from flask import Flask, send_from_directory, jsonify, request
from flask_sock import Sock

from app.config import APP_PORT, REDIS_STREAM_KEY, INFLUXDB_BUCKET
from app.services.redis_client import get_redis_client
from app.services.influx_client import get_query_api

app = Flask(__name__)
sock = Sock(app)
r = get_redis_client(decode_responses=True)
query_api = get_query_api()

# Absolute path to the frontend directory (container: /app/frontend)
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))

# Stream key prefix patterns
FOP_PREFIX = f"{REDIS_STREAM_KEY}:fop:"
STK_PREFIX = f"{REDIS_STREAM_KEY}:stk:"

# Supported timeframes for historical candle fetch (seconds)
SUPPORTED_HISTORY_TF = {60, 300, 3600}

# config.toml 路徑 + 讀寫鎖
_TOML_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config.toml"))
_toml_lock = threading.Lock()


def _read_toml() -> dict:
    """讀取 config.toml，回傳完整 dict。"""
    with open(_TOML_PATH, "rb") as f:
        return tomli.load(f)


def _write_toml(data: dict) -> None:
    """將 dict 寫回 config.toml（原子性：先寫暫存再 rename）。"""
    tmp_path = _TOML_PATH + ".tmp"
    with open(tmp_path, "wb") as f:
        tomli_w.dump(data, f)
    os.replace(tmp_path, _TOML_PATH)


def _get_latest_ticks() -> list[dict]:
    """掃描所有 tick stream keys，回傳每個合約的最新 tick"""
    results = []
    try:
        all_keys = r.keys(f"{REDIS_STREAM_KEY}:*")
        for key in sorted(all_keys):
            # 先判斷商品類型過濾非 Stream 的 key (如 txf:status)
            if key.startswith(FOP_PREFIX):
                market = "futures"
                code = key[len(FOP_PREFIX):]
            elif key.startswith(STK_PREFIX):
                market = "stocks"
                code = key[len(STK_PREFIX):]
            else:
                continue
                
            data_list = r.xrevrange(key, max="+", min="-", count=1)
            if not data_list:
                continue
            _, data = data_list[0]
            results.append({
                "market": market,
                "code": code,
                "price": float(data.get("price", 0)),
                "ts": float(data.get("ts", time.time())),
            })
    except Exception as e:
        print(f"Redis scan error: {e}")
    return results


def _fetch_from_influx(code: str, tf_seconds: int) -> dict[int, dict]:
    interval = "1m" if tf_seconds == 60 else "5m" if tf_seconds == 300 else "60m"
    query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: -30d)
        |> filter(fn: (r) => r._measurement == "txf")
        |> filter(fn: (r) => r.code == "{code}" and r.interval == "{interval}")
        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        |> tail(n: 60)
    '''
    candles = {}
    try:
        tables = query_api.query(query)
        for table in tables:
            for record in table.records:
                ts = int(record.get_time().timestamp())
                candles[ts] = {
                    "time": ts,
                    "open": record.values.get("open"),
                    "high": record.values.get("high"),
                    "low": record.values.get("low"),
                    "close": record.values.get("close"),
                }
    except Exception as e:
        print(f"Influx query error: {e}")
    return candles


def _build_candles_from_stream(stream_key: str, tf: int) -> list[dict]:
    """從 Redis Stream 讀取全部 ticks，並與 InfluxDB 歷史資料彙整成 OHLC K 線清單"""
    code = stream_key.split(":")[-1]
    
    # 1. Base candles from InfluxDB (last 60)
    candles = _fetch_from_influx(code, tf)
    
    # 2. Overlay intra-period updates & newest ticks from Redis stream (only for current candle)
    now_ts = int(time.time())
    current_bucket_start_ms = (now_ts // tf) * tf * 1000
    try:
        # 只抓取當前 K 線時間範圍內的 ticks
        raw = r.xrange(stream_key, min=f"{current_bucket_start_ms}-0", max="+")
    except Exception as e:
        print(f"Redis xrange error: {e}")
        raw = []

    for _, data in raw:
        try:
            price = float(data.get("price", 0))
            ts = float(data.get("ts", 0))
            bucket = math.floor(ts / tf) * tf
            if bucket not in candles:
                candles[bucket] = {"time": bucket, "open": price, "high": price, "low": price, "close": price}
            else:
                c = candles[bucket]
                c["high"] = max(c["high"], price)
                c["low"] = min(c["low"], price)
                c["close"] = price
        except (ValueError, TypeError):
            continue

    return [candles[k] for k in sorted(candles)]


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/api/streams")
def api_streams():
    """返回目前有資料的合約清單"""
    return jsonify(_get_latest_ticks())


@app.route("/api/reconnect", methods=["POST"])
def api_reconnect():
    """手動發出重新連線指令給 collector"""
    r.set(f"{REDIS_STREAM_KEY}:cmd", "login")
    return jsonify({"success": True})


@app.route("/api/subscriptions", methods=["GET"])
def api_subscriptions_get():
    """回傳目前 config.toml 中的訂閱清單 {futures: {...}, stocks: [...]}"""
    with _toml_lock:
        cfg = _read_toml()
    shioaji_cfg = cfg.get("shioaji", {})
    return jsonify({
        "futures": shioaji_cfg.get("futures", {}),
        "stocks": shioaji_cfg.get("stocks", []),
    })


@app.route("/api/subscriptions", methods=["POST"])
def api_subscriptions_add():
    """
    新增一筆訂閱並即時生效。
    Body JSON：
      { "type": "futures"|"stocks", "category": "MXF"(futures only), "id": "MXFR1", "name": "小台指近月" }
    """
    body = request.get_json(silent=True) or {}
    sub_type = body.get("type", "")
    sub_id = (body.get("id") or "").strip()
    sub_name = (body.get("name") or "").strip()

    if sub_type not in ("futures", "stocks"):
        return jsonify({"error": "type must be 'futures' or 'stocks'"}), 400
    if not sub_id:
        return jsonify({"error": "id is required"}), 400
    if not sub_name:
        return jsonify({"error": "name is required"}), 400

    with _toml_lock:
        cfg = _read_toml()
        if "shioaji" not in cfg:
            cfg["shioaji"] = {}

        if sub_type == "futures":
            category = (body.get("category") or "").strip()
            if not category:
                return jsonify({"error": "category is required for futures"}), 400
            futures_cfg: dict = cfg["shioaji"].setdefault("futures", {})
            cat_list: list = futures_cfg.setdefault(category, [])
            # 檢查重複
            if any(item["id"] == sub_id for item in cat_list):
                return jsonify({"error": f"{sub_id} already exists in {category}"}), 409
            cat_list.append({"id": sub_id, "name": sub_name})
        else:
            stocks_list: list = cfg["shioaji"].setdefault("stocks", [])
            if any(item["id"] == sub_id for item in stocks_list):
                return jsonify({"error": f"{sub_id} already exists in stocks"}), 409
            stocks_list.append({"id": sub_id, "name": sub_name})

        _write_toml(cfg)

    # 通知 shioaji.py 動態重載
    r.set(f"{REDIS_STREAM_KEY}:cmd", "reload")
    return jsonify({"success": True})


@app.route("/api/subscriptions", methods=["DELETE"])
def api_subscriptions_delete():
    """
    刪除一筆訂閱並即時生效。
    Body JSON：
      { "type": "futures"|"stocks", "id": "MXFR1" }
    """
    body = request.get_json(silent=True) or {}
    sub_type = body.get("type", "")
    sub_id = (body.get("id") or "").strip()

    if sub_type not in ("futures", "stocks"):
        return jsonify({"error": "type must be 'futures' or 'stocks'"}), 400
    if not sub_id:
        return jsonify({"error": "id is required"}), 400

    with _toml_lock:
        cfg = _read_toml()
        shioaji_cfg = cfg.get("shioaji", {})
        found = False

        if sub_type == "futures":
            futures_cfg: dict = shioaji_cfg.get("futures", {})
            for category, cat_list in futures_cfg.items():
                before = len(cat_list)
                futures_cfg[category] = [item for item in cat_list if item["id"] != sub_id]
                if len(futures_cfg[category]) < before:
                    found = True
        else:
            stocks_list: list = shioaji_cfg.get("stocks", [])
            new_list = [item for item in stocks_list if item["id"] != sub_id]
            if len(new_list) < len(stocks_list):
                found = True
            shioaji_cfg["stocks"] = new_list

        if not found:
            return jsonify({"error": f"{sub_id} not found in {sub_type}"}), 404

        _write_toml(cfg)

    # 通知 shioaji.py 動態重載
    r.set(f"{REDIS_STREAM_KEY}:cmd", "reload")
    return jsonify({"success": True})


@app.route("/api/candles")
def api_candles():
    """
    回傳指定合約的完整 K 線資料（支援 1分/5分/60分）。
    Query params:
        code  — 合約代碼 (e.g. TXFB5)
        tf    — timeframe in seconds (60 or 300)
    """
    code = request.args.get("code", "").strip()
    try:
        tf = int(request.args.get("tf", 60))
    except ValueError:
        return jsonify({"error": "invalid tf"}), 400

    if tf not in SUPPORTED_HISTORY_TF:
        return jsonify({"error": f"tf must be one of {sorted(SUPPORTED_HISTORY_TF)}"}), 400

    if not code:
        return jsonify({"error": "code is required"}), 400

    # 嘗試 futures 再嘗試 stocks
    fop_key = f"{FOP_PREFIX}{code}"
    stk_key = f"{STK_PREFIX}{code}"
    try:
        exists_fop = r.exists(fop_key)
    except Exception:
        exists_fop = False

    stream_key = fop_key if exists_fop else stk_key
    candles = _build_candles_from_stream(stream_key, tf)
    return jsonify(candles)


@sock.route("/ws")
def ws_tick(ws):
    """WebSocket：每 0.5 秒推送所有合約的最新 tick 及連線狀態"""
    # 頁面開啟時，通知 python-ingest 立即刷新流量（不寫 InfluxDB）
    try:
        current_cmd = r.get(f"{REDIS_STREAM_KEY}:cmd")
        if not current_cmd:  # 不覆蓋較高優先級的 login 指令
            r.set(f"{REDIS_STREAM_KEY}:cmd", "usage")
    except Exception:
        pass

    while True:
        try:
            status = r.get(f"{REDIS_STREAM_KEY}:status") or "unknown"
            usage_bytes = r.get(f"{REDIS_STREAM_KEY}:usage_bytes") or "0"
            limit_bytes = r.get(f"{REDIS_STREAM_KEY}:limit_bytes") or "0"
            
            ws.send(json.dumps({
                "type": "status", 
                "status": status,
                "usage_bytes": int(usage_bytes),
                "limit_bytes": int(limit_bytes)
            }))
            
            ticks = _get_latest_ticks()
            if ticks:
                ws.send(json.dumps(ticks))
            time.sleep(0.5)
        except Exception as e:
            print(f"WebSocket error: {e}")
            break


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=APP_PORT)
