import os
import time
import json
from flask import Flask, send_from_directory
from flask_sock import Sock

from app.config import APP_PORT, REDIS_STREAM_KEY
from app.services.redis_client import get_redis_client

app = Flask(__name__)
sock = Sock(app)
r = get_redis_client(decode_responses=True)

# Absolute path to the frontend directory (container: /app/frontend)
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@sock.route("/ws")
def ws_tick(ws):
    while True:
        try:
            result = r.xrevrange(REDIS_STREAM_KEY, max="+", min="-", count=1)
            if result:
                _, data = result[0]
                ws.send(json.dumps({
                    "ts": float(data.get("ts", time.time())),
                    "price": float(data.get("price", 0)),
                }))
            time.sleep(0.5)
        except Exception as e:
            print(f"WebSocket error: {e}")
            break


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=APP_PORT)
