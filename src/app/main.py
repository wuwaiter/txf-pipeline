import os
import time
import json
import math
from flask import Flask, send_from_directory, jsonify, request
from flask_sock import Sock

from app.config import APP_PORT, REDIS_STREAM_KEY
from app.services.redis_client import get_redis_client

app = Flask(__name__)
sock = Sock(app)
r = get_redis_client(decode_responses=True)

# Absolute path to the frontend directory (container: /app/frontend)
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))

# Stream key prefix patterns
FOP_PREFIX = f"{REDIS_STREAM_KEY}:fop:"
STK_PREFIX = f"{REDIS_STREAM_KEY}:stk:"

# Supported timeframes for historical candle fetch (seconds)
SUPPORTED_HISTORY_TF = {60, 300}


def _get_latest_ticks() -> list[dict]:
    """掃描所有 tick stream keys，回傳每個合約的最新 tick"""
    results = []
    try:
        all_keys = r.keys(f"{REDIS_STREAM_KEY}:*")
        for key in sorted(all_keys):
            data_list = r.xrevrange(key, max="+", min="-", count=1)
            if not data_list:
                continue
            _, data = data_list[0]
            # 判斷商品類型
            if key.startswith(FOP_PREFIX):
                market = "futures"
                code = key[len(FOP_PREFIX):]
            elif key.startswith(STK_PREFIX):
                market = "stocks"
                code = key[len(STK_PREFIX):]
            else:
                continue
            results.append({
                "market": market,
                "code": code,
                "price": float(data.get("price", 0)),
                "ts": float(data.get("ts", time.time())),
            })
    except Exception as e:
        print(f"Redis scan error: {e}")
    return results


def _build_candles_from_stream(stream_key: str, tf: int) -> list[dict]:
    """從 Redis Stream 讀取全部 ticks，彙整成 OHLC K 線清單"""
    try:
        raw = r.xrange(stream_key, min="-", max="+")
    except Exception as e:
        print(f"Redis xrange error: {e}")
        return []

    candles: dict[int, dict] = {}
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


@app.route("/api/candles")
def api_candles():
    """
    回傳指定合約的完整 K 線資料（僅支援 1分/5分）。
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
    while True:
        try:
            status = r.get(f"{REDIS_STREAM_KEY}:status") or "unknown"
            ws.send(json.dumps({"type": "status", "status": status}))
            
            ticks = _get_latest_ticks()
            if ticks:
                ws.send(json.dumps(ticks))
            time.sleep(0.5)
        except Exception as e:
            print(f"WebSocket error: {e}")
            break


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=APP_PORT)
