import shioaji as sj
import redis
import time

r = redis.Redis(host="redis", port=6379)

api = sj.Shioaji(simulation=True)

api.login("API_KEY", "SECRET_KEY")

contract = api.Contracts.Futures.TXF.TXFR1
api.quote.subscribe(contract, quote_type="tick")

@api.on_tick_fop_v1()
def cb(exchange, tick):
    data = {
        "price": tick.close,
        "ts": int(time.time())
    }
    r.xadd("tick:txf", data, maxlen=10000)

while True:
    time.sleep(1)