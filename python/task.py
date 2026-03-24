import redis
from celery_app import app
from influxdb_client import InfluxDBClient, Point
import time

r = redis.Redis(host="redis", port=6379)

client = InfluxDBClient(
    url="http://influxdb:8086",
    token="admin123",
    org="my-org"
)
write_api = client.write_api()

def get_ticks(seconds):
    now = int(time.time())
    data = r.xrange("tick:txf", min="-", max="+")
    return [
        float(dict(x[1])[b'price'])
        for x in data
        if now - int(dict(x[1])[b'ts']) <= seconds
    ]

def build_ohlc(prices):
    return {
        "open": prices[0],
        "high": max(prices),
        "low": min(prices),
        "close": prices[-1]
    }

def write_influx(interval, ohlc):
    p = Point("txf") \
        .tag("interval", interval) \
        .field("open", ohlc["open"]) \
        .field("high", ohlc["high"]) \
        .field("low", ohlc["low"]) \
        .field("close", ohlc["close"])
    write_api.write(bucket="txf", record=p)

@app.task
def agg_1m():
    prices = get_ticks(60)
    if prices:
        write_influx("1m", build_ohlc(prices))

@app.task
def agg_5m():
    prices = get_ticks(300)
    if prices:
        write_influx("5m", build_ohlc(prices))

@app.task
def agg_60m():
    prices = get_ticks(3600)
    if prices:
        write_influx("60m", build_ohlc(prices))