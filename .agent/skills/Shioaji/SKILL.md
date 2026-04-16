---
name: "Shioajii"
description: "定義Shioaji API (永豐金 API) 的串接規則"
---


# 1. API 參考, 來源參考官方 github : https://sinotrade.github.io/shioaji/
```python
import shioaji as sj

api = sj.Shioaji(simulation=False)
api.login(api_key="YOUR_API_KEY", secret_key="YOUR_SECRET_KEY")

# 訂閱證券報價
contract = api.Contracts.Stocks['2330']
api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.Tick)

# 訂閱期貨報價
contract = api.Contracts.Futures.TXF['TXF202602']
api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.Tick)

# 取得報價
api.quote.snapshot(contract)

# 取得歷史資料
api.quote.history(contract, start='2026-01-01', end='2026-01-31', interval=sj.constant.Interval.Min)
```


# 2. 以下是一個可執行的範例

```python
import os
import threading
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
import shioaji as sj


# 引入設定檔
# 注意：若直接執行此檔案，Python 會將當前目錄加入 path，因此可以直接 import config
try:
    import config
except ImportError:
    # 處理若從 src 外層執行的情況 (src.sj_trading.config)
    from sj_trading import config

# ==========================================
# 1. 環境變數讀取
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, '..', '..', '.env')
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)

# ==========================================
# 2. 動態初始化 Market Data
# ==========================================
# 根據 config.py 自動建立資料結構
market_data = {}

for item in config.WATCH_LIST:
    market_data[item['id']] = {
        "name": item['name'],
        "price": "--",
        "change": 0,
        "pct": 0,
        "vol": "--",
        "time": "--",
        "status": "none"
    }

# Shioaji 初始化
api = sj.Shioaji(simulation=False)
is_api_connected = False

def init_shioaji():
    global is_api_connected
    
    # 修改 1.2: 使用您指定的環境變數名稱
    api_key = os.getenv("API_KEY")
    secret_key = os.getenv("SECRET_KEY")
    
    if api_key:
        print(f">>> API Key detected: {api_key[:4]}****")
    else:
        print(">>> ERROR: API_KEY not found in .env")
        return

    try:
        api.login(api_key, secret_key, contracts_cb=lambda x: print("Contracts loaded."), contracts_timeout=10000)
        print(">>> Shioaji Login Successful")
        is_api_connected = True
        
        print( api.usage() )
        time.sleep(5)
        subscribe_quotes()
        
    except Exception as e:
        print(f">>> Shioaji Login Failed Details: {e}")

def subscribe_quotes():
    """
    修改 2.2: 讀取 Config 進行動態訂閱
    """
    for item in config.WATCH_LIST:
        try:
            contract = None
            
            if item['type'] == 'Stock':
                # e.g., api.Contracts.Stocks['2330']
                contract = api.Contracts.Stocks[item['contract_id']]
                
            elif item['type'] == 'Future':
                # 修改 1.1: 支援您的期貨寫法 api.Contracts.Futures.TXF['TXF202602']
                # 這裡使用 getattr 動態取得 Futures 下的分類 (如 TXF)
                future_category = getattr(api.Contracts.Futures, item['category'])
                contract = future_category[item['contract_id']]

            if contract:
                # 針對證券與期貨使用不同的訂閱參數
                if item['type'] == 'Stock':
                    # 修正: 證券改用 version=v1
                    api.quote.subscribe(
                        contract, 
                        quote_type=sj.constant.QuoteType.Tick,
                        version=sj.constant.QuoteVersion.v1
                    )
                else:
                    # 期貨維持原樣
                    api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.Tick)
                
                # 兩者都訂閱 BidAsk 以求完整
                api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.BidAsk)
                print(f">>> Subscribed to {item['name']}: {contract.code}")
            else:
                print(f">>> Contract not found for {item['name']}")

        except Exception as e:
            print(f"Failed to subscribe {item['name']}: {e}")

# ==========================================
# Callback Functions
# ==========================================

@api.on_tick_stk_v1()
def quote_callback_stk(exchange, tick):
    """處理證券(Stock)即時報價"""
    # 檢查收到的 tick code 是否在我們的監控清單中 (比對 contract_id)
    for item in config.WATCH_LIST:
        if item['type'] == 'Stock' and item['contract_id'] == tick.code:
            update_tick_data(item['id'], tick)
            break

@api.on_tick_fop_v1()
def quote_callback_fop(exchange, tick):
    """處理期貨(Futures/Options)即時報價"""
    # 期貨代碼可能比較複雜 (包含月份)，這裡做簡單的包含檢查
    for item in config.WATCH_LIST:
        if item['type'] == 'Future':
            # 若 tick.code 包含在我們的 contract_id 或是部分符合
            if tick.code == item['contract_id'] or (item['category'] == "TXF" and "TX" in tick.code):
                update_tick_data(item['id'], tick)
                break

def update_tick_data(target_id, tick):
    try:
        price = float(tick.close)
        time_str = tick.datetime.strftime("%H:%M:%S")
        
        market_data[target_id]['price'] = f"{price:,.0f}" if price > 1000 else f"{price:,.2f}"
        market_data[target_id]['vol'] = f"{int(tick.volume)}"
        market_data[target_id]['time'] = time_str
    except Exception as e:
        print(f"Error updating tick data: {e}")

# ==========================================
# Flask Routes
# ==========================================

@app.route('/')
def index():
    # 將 config 傳給前端，以便動態生成 UI (若前端改為 Jinja2 渲染會更方便，但目前維持 AJAX 架構)
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    """
    使用 Snapshots 取得完整漲跌幅資訊
    """
    contracts_to_query = []
    id_map = {} # 用來對應 contract 物件與 market_data id

    try:
        # 1. 準備合約清單
        for item in config.WATCH_LIST:
            try:
                contract = None
                if item['type'] == 'Stock':
                    contract = api.Contracts.Stocks[item['contract_id']]
                elif item['type'] == 'Future':
                    future_category = getattr(api.Contracts.Futures, item['category'])
                    contract = future_category[item['contract_id']]
                
                if contract:
                    contracts_to_query.append(contract)
                    id_map[contract.code] = item['id']
            except:
                continue

        # 2. 批量查詢 Snapshots
        if contracts_to_query:
            snapshots = api.snapshots(contracts_to_query)
            
            for snap in snapshots:
                # 找到對應的 market_data ID
                target_id = id_map.get(snap.code)
                if not target_id: continue

                market_data[target_id]['price'] = f"{snap.close:,.0f}" if snap.close > 1000 else f"{snap.close:,.2f}"
                market_data[target_id]['change'] = f"{snap.change_price:+.0f}" if abs(snap.change_price) > 1 else f"{snap.change_price:+.2f}"
                market_data[target_id]['pct'] = f"{snap.change_rate:+.2f}%"
                market_data[target_id]['vol'] = f"{snap.total_volume}"
                market_data[target_id]['status'] = "up" if snap.change_price > 0 else "down" if snap.change_price < 0 else "none"

    except Exception as e:
        # print(f"Snapshot update failed: {e}")
        pass

    return jsonify(market_data)

if __name__ == '__main__':
    t = threading.Thread(target=init_shioaji)
    t.daemon = True
    t.start()
    
    app.run(debug=True, port=5000, use_reloader=False)