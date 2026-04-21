---
name: "Shioajii"
description: "定義Shioaji API (永豐金 API) 的串接規則"
---

# Shioajii API — 技能設計分析

## 專案概述

- **名稱**：Shioajii (永豐證券/期貨 API 串接規章)
- **來源**：https://sinotrade.github.io/shioaji/
- **目的**：定義 Shioaji API 登入、訂閱即時報價(Quote)與取得快照歷史資料的標準流程。
- **類型**：Python 腳本與 Flask Web 應用整合範例。


## 技術堆疊

- **核心套件**：`shioaji` (永豐金 Python API)
- **環境管理**：`python-dotenv` (讀取 `.env` 中的帳密)
- **非同步與併發**：`threading` (將 Shioaji 執行緒與 Flask 主執行緒分離)
- **Web 框架**：`Flask` (作為報價資料展示的前端渲染或 API 提供者)

## 核心邏輯

### 1. API 基礎參考 (基本操作)
最基礎的 Shioaji 登入與報價存取流程：
```python
import shioaji as sj

api = sj.Shioaji(simulation=False)
api.login(api_key="YOUR_API_KEY", secret_key="YOUR_SECRET_KEY")

# 訂閱證券報價
contract = api.Contracts.Stocks['2330']
api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.Quote, version=sj.constant.QuoteVersion.v1)

# 訂閱期貨報價
contract = api.Contracts.Futures.TXF['TXF202602']
api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.Quote, version=sj.constant.QuoteVersion.v1)

# 取得報價快照
api.quote.snapshot(contract)

# 取得歷史資料
api.quote.history(contract, start='2026-01-01', end='2026-01-31', interval=sj.constant.Interval.Min)
```

### 2. 環境變數讀取與動態初始化
- 透過 `load_dotenv` 載入 `.env` 來讀取 `API_KEY` 與 `SECRET_KEY` 保護敏感資訊。
- 載入自定義的 `config.py`，從 `WATCH_LIST` 讀取欲訂閱的商品清單，動態生成內部儲存字典 `market_data`。

### 3. 動態訂閱機制 (Subscribe)
區分股票與期貨的合約物件提取邏輯：
- **Stock**：走 `getattr(api.Contracts.Stocks, item['id'])` 動態提取股票介面，且 `subscribe` 時建議使用 `version=sj.constant.QuoteVersion.v1` 以匹配 v1 版 Quote API。
- **Future**：走 `getattr(api.Contracts.Futures, item['category'])[item['id']]` 動態提取期貨總類（例如 TXF）。
- Future 因為有時間限制, 到期後合約無法再透過 api.Contracts 取得. 需要改使用R1, R2合約來取得
  例如 `api.Contracts.Futures.TXF.TXFR1`
- stock/future 的合約都使用`Quote` 訂閱資料流

### 4. Callback 處理行情
利用 Decorator 來監聽即時 Quote 封包，並更新 `market_data` 內容：
- `@api.on_quote_stk_v1()`：用來更新證券報價。
- `@api.on_quote_fop_v1()`：用來更新期貨報價。
收到資料後交由 `update_tick_data` 轉換時間格式與數字格式（千分位）後儲存。

### 5. 流量確認
依Shioaji的API `api.usage`, 查詢當下的流量
當流量為0的時候
1. 執行 api.logout()
2. 暫停從 shioaji API繼續獲取流量  並同時將 上方的連線狀態指示燈 "即時連線"顯示為"連線中斷"
3. 點擊連線狀態指示燈的 "連線中斷"時, 重新執行 api.login()

流量限制 : https://sinotrade.github.io/zh/tutor/limit/



## 元件階層與資料流

```text
Shioaji Thread (非同步讀取即時行情)
 ├── load_dotenv (.env)
 ├── api.login()
 ├── subscribe_quotes() (依據 config.WATCH_LIST)
 └── on_quote (更新記憶體內 market_data)

Flask App Thread (提供對外服務)
 ├── /         → 渲染 index.html，回傳前端 UI
 └── /api/data → 提供前端 AJAX 呼叫，查詢快照 (snapshots) 與 market_data，回傳 JSON
```

## 架構特徵與觀察

### 優點 / 觀察結果
- **關注點分離**：Shioaji 連線邏輯運作在獨立 `threading.Thread` 中，不阻擋 Flask 主執行緒運作。
- **設定驅動化**：由外部的 `config.py` 帶動所有訂閱行為，增減品種時不需修改核心程式碼。
- **雙軌確保資料準確**：除了使用 Callback 接收即時 Quote 外，在 `/api/data` 中亦混用 Snapshot 來補充完整的跌漲幅資訊。

## 完整串接範例參考

此為實作上述邏輯的 Flask + Shioaji 結合腳本 (節錄結構)。

```python
import os
import threading
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
import shioaji as sj

try:
    import config
except ImportError:
    from sj_trading import config

# 1. 讀取 .env 與初始化
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
app = Flask(__name__)
market_data = {item['id']: {"name": item['name'], "price": "--", "change": 0, "pct": 0, "vol": "--", "time": "--", "status": "none"} for item in config.WATCH_LIST}
api = sj.Shioaji(simulation=False)

def init_shioaji():
    api_key, secret_key = os.getenv("API_KEY"), os.getenv("SECRET_KEY")
    if api_key:
        api.login(api_key, secret_key, contracts_timeout=10000)
        time.sleep(5)
        subscribe_quotes()

def subscribe_quotes():
    for item in config.WATCH_LIST:
        ... # 判斷 type 為 Stock 或 Future 並進行 subscribe

@api.on_quote_stk_v1()
def quote_callback_stk(exchange, quote):
    ... # 比對合約代碼並更新 market_data

@app.route('/api/data')
def get_data():
    ... # 透過 api.snapshots() 查詢並更新漲跌幅後返回 JSON

if __name__ == '__main__':
    t = threading.Thread(target=init_shioaji)
    t.daemon = True
    t.start()
    app.run(debug=True, port=5000, use_reloader=False)
```