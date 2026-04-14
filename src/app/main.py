import os
import time
import json
from flask import Flask, send_from_directory, jsonify
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


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/api/streams")
def api_streams():
    """返回目前有資料的合約清單"""
    return jsonify(_get_latest_ticks())


@sock.route("/ws")
def ws_tick(ws):
    """WebSocket：每 0.5 秒推送所有合約的最新 tick"""
    while True:
        try:
            ticks = _get_latest_ticks()
            if ticks:
                ws.send(json.dumps(ticks))
            time.sleep(0.5)
        except Exception as e:
            print(f"WebSocket error: {e}")
            break


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=APP_PORT)
