---
name: "TXF Pipeline Architecture"
description: "定義了 TXF Pipeline 專案的標準目錄結構及配置規則，確保未來重構或新增功能時皆符合此設計。"
---

# TXF Pipeline — 架構設計分析

## 專案概述

- **名稱**：TXF Pipeline Architecture
- **目的**：定義 TXF Pipeline 專案的標準目錄結構及配置規則，確保未來重構或新增功能時皆符合此設計規範。

## 目錄結構

本專案強硬要求採用以下結構，請勿隨意在專案內散落應用邏輯或 Dockerfile：

```text
txf-pipeline/
├─ docker-compose.yml
├─ .env
├─ docker/
│  └─ python/
│       └─ Dockerfile
├─ config/
│  ├─ influxdb/
│  │   └─ influxdb.conf
│  │
│  └─ grafana/
│      ├─ provisioning/
│      │   ├─ datasources/
│      │   │   └─ influxdb.yaml
│      │   └─ dashboards/
│      │       └─ dashboard.yaml
│      │
│      └─ dashboards/
│          └─ market_dashboard.json
│
├─ pyproject.toml
├─ requirements.txt
├─ requirements-dev.txt
│
├─ frontend/
│   └─ index.html
│
├─ src/
│   └─ app/
│        ├─ main.py
│        ├─ config.py
│        │
│        ├─ services/
│        │   ├─ redis_client.py
│        │   └─ influx_client.py
│        │
│        └─ workers/
│            └─ collector.py
│
├─ tests/
│
└─ README.md
```

## 核心邏輯

### 參數與環境變數管理
- **敏感資訊**（例如 API_KEY, DB 帳號密碼等）必須移至 `.env` 中管理。
- **系統參數**（如 Port, Host 網址, 相關參數配置等）必須移至 `config.toml` 中管理。
- 由 `src/app/config.py` 負責統一讀取環境變數與 TOML 參數，供專案全局參照。

### 程式碼配置與職責
- 所有核心邏輯必須置於 `src/app/` 之下。
- 提供外界與基礎建設連線的客戶端或封裝（如 Redis, InfluxDB 的 Client）實作於 `services/`。
- 外部資料搜集（爬蟲機制）與定時排程聚合的邏輯（如 Celery 分鐘級資料聚合）等實作，統一集中在 `workers/collector.py`。
- 前端單頁應用程式 (SPA) 的靜態檔案存放於 `frontend/` 目錄下（如 `index.html`），並交由 Flask 掛載服務。

## 前端架構與 UI 規範

> 通用風格規則（Design Token 系統、字型、元件模式、動畫）定義於 `UIStyleDefine/SKILL.md`。
> 本章節僅記錄 **TXF Pipeline 專案的特殊套用方式**。

前端為輕量化 SPA，採用原生 HTML/CSS/JS，不依賴建構工具。

### Design Token 實際色票

```css
:root {
  --bg-0: #0b0e17;                    /* 頁面底色、圖表背景 */
  --bg-1: #111520;                    /* Header、Sidebar、Stats Bar */
  --bg-2: #181d2e;                    /* Status Badge */
  --bg-3: #1f2640;                    /* Hover、Active Contract */
  --accent: #3b82f6;
  --accent-glow: rgba(59, 130, 246, .25);
  --green: #22c55e;
  --red: #ef4444;
  --text-1: #f0f4ff;
  --text-2: #94a3b8;
  --text-3: #64748b;
  --border: rgba(255, 255, 255, .07);
  --radius: 12px;
}
```

### 漲跌色慣例（台灣市場）

本專案依台灣市場慣例，**漲為紅、跌為綠**，與 `--red` / `--green` 對應如下：

| CSS Class | 顏色變數 | 語意 |
|---|---|---|
| `.up` | `var(--red)` `#ef4444` | 價格上漲 |
| `.dn` | `var(--green)` `#22c55e` | 價格下跌 |
| `.up-muted` | `#d77a7a` | 上漲（淡） |
| `.dn-muted` | `#7ad79a` | 下跌（淡） |
| `.flat-muted` | `#d7cd7a` | 平盤 |
| `.white-muted` | `#d1d5db` | 無變化 / 中性 |

Flash 動畫對應：
- `.flash-up`（價格上漲）→ `flash-red`：`rgba(239, 68, 68, .3)` 閃爍
- `.flash-dn`（價格下跌）→ `flash-green`：`rgba(34, 197, 94, .3)` 閃爍

### 版面尺寸

| 區域 | 尺寸 |
|---|---|
| Sidebar 寬度 | `260px`（固定） |
| Header 高度 | `57px`（padding 14px 28px + 內容） |
| 主佈局 | `display: grid; grid-template-columns: 260px 1fr` |
| Chart container | `flex: 1; min-height: 0`（填滿剩餘空間） |

### 元件尺寸對照

| 元件 | 子項目 | 字型大小 | 字型 |
|---|---|---|---|
| Header | Logo 文字 | `1.1rem` | Inter Bold |
| | Status Badge | `0.8rem` | Inter |
| | Clock | `0.85rem` | JetBrains Mono |
| Sidebar | Section Title | `0.7rem` | Inter Semi-Bold |
| | 合約代碼 (cc-code) | `0.9rem` | JetBrains Mono |
| | Market Tag | `0.65rem` | Inter |
| Chart Header | 選中代碼 | `1.25rem` | JetBrains Mono Bold |
| | 選中價格 | `2rem` | JetBrains Mono Bold |
| | Toolbar 按鈕 | `0.8rem` | Inter |
| Stats Bar | Label | `0.68rem` | Inter（全大寫） |
| | Value | `0.95rem` | JetBrains Mono |

### 前後端資料流

- **歷史 K 線**：切換合約或 timeframe 時，`GET /api/candles?code=&tf=` 拉取最近 60 根；不支援的 timeframe 直接跳過不發請求，等待即時資料填入。
- **即時報價**：`/ws` WebSocket，每 0.5 秒推送所有合約最新 tick。前端 `processTicks()` 解析後增量更新 K 線（只重繪 high / low / close），不重繪全圖。

### Lightweight Charts 整合

- 引用：`unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js`
- 圖表背景色：`--bg-0`；陽線：`--red`（#ef4444）；陰線：`--green`（#22c55e）
- 容器 `#chart` 寬高設定 `width: 100%; height: 100%`，由父層 flex 控制實際尺寸

## 架構特徵與觀察

### 優點 / 規範要求
- **關注點分離**：基礎設施設定檔 `config/` 與應用邏輯 `src/` 徹底分離。
- **容器化規範明確**：自定義 `Dockerfile` 收斂於 `docker/<服務名>/` 底下，外部設定檔於 `config/` 對應掛載，維持根目錄整潔。
- **集中參數管理**：透過 `.env` 與 `config.toml` 分開管理敏感資料與系統參數。

## Redis 資料層規範

### Key 命名規則

所有 Key 以 `REDIS_STREAM_KEY`（預設 `tick:txf`，由 `config.toml` 的 `redis.stream_key` 控制）為前綴：

| Key 格式 | 類型 | 用途 |
|---|---|---|
| `tick:txf:fop:<code>` | Redis Stream | 期貨 Tick 報價（Futures/Options） |
| `tick:txf:stk:<code>` | Redis Stream | 股票 Tick 報價（Stocks） |
| `tick:txf:status` | String | 連線狀態（`connected` / `disconnected` / `unknown`） |
| `tick:txf:cmd` | String | 指令通道（`login` / `usage` / `check_usage`） |
| `tick:txf:usage_bytes` | String | Shioaji 已用流量（bytes，整數字串） |
| `tick:txf:limit_bytes` | String | Shioaji 流量上限（bytes，整數字串） |

> 新增商品類型時，前綴一律沿用 `tick:txf:<type>:<code>` 格式，`<type>` 使用小寫縮寫（如 `fop`、`stk`）。

### Stream 資料結構

每筆 Tick 寫入的欄位固定為兩個，皆以**字串**儲存，讀取後須手動轉型：

```python
{"price": str(quote.close), "ts": str(int(time.time()))}
# 讀取：float(data["price"])、float(data["ts"])
```

### 指令集（cmd 通道）

`tick:txf:cmd` 為 collector 主迴圈控制通道，每 5 秒輪詢；指令讀取後須立即 `r.delete(...)` 清除：

| 指令值 | 觸發來源 | 行為 |
|---|---|---|
| `login` | 前端「重新連線」按鈕 → `POST /api/reconnect` | 重新 login + subscribe，不寫 InfluxDB |
| `usage` | 頁面開啟 / WebSocket 建立 | 只刷新流量顯示，不寫 InfluxDB |
| `check_usage` | ScheduleTask 背景排程（每分鐘） | 刷新流量並寫入 InfluxDB monitoring bucket |

優先順序：`login` > `check_usage` > `usage`

### decode_responses 規則

| 模組 | decode_responses | 原因 |
|---|---|---|
| `main.py`（Flask / WS） | `True`（str） | 直接操作字串，避免手動 decode |
| `collector.py`（Celery Worker） | `False`（bytes） | 聚合時比對 bytes prefix 效能較高 |

### 禁止事項
- Tick 報價**必須**用 `xadd` 寫入 Stream，不可用 `set/get` 儲存，會破壞時序資料。
- 掃描所有 Key 時，**必須**過濾非 Stream Key（`status`、`cmd`、`usage_bytes`、`limit_bytes`），否則解析會出錯。
- **不可**自行發明新的 Key 命名前綴，一律沿用 `{REDIS_STREAM_KEY}:<type>:<code>` 格式。

---

## InfluxDB 資料層規範

### Bucket 設計

| Bucket 名稱 | 來源常數 | 用途 |
|---|---|---|
| `txf` | `INFLUXDB_BUCKET`（`.env`） | 主要 OHLC K 線業務資料 |
| `monitoring` | `INFLUXDB_MONITORING_BUCKET`（`config.py` 硬寫） | Shioaji API 流量監控 |

> Bucket 名稱**不可**硬寫於 `collector.py`，必須從 `app.config` 引入常數。

### Measurement Schema

**`txf`** — OHLC K 線，由 `_aggregate_and_write()` 寫入：

| 屬性 | 名稱 | 型別 | 值域 |
|---|---|---|---|
| Tag | `interval` | string | `"1m"` / `"5m"` / `"60m"` |
| Tag | `market` | string | `"futures"` / `"stocks"` |
| Tag | `code` | string | 合約代碼（如 `"TXFR1"`、`"2330"`） |
| Field | `open` | float | 聚合區間第一筆價格 |
| Field | `high` | float | 聚合區間最高價 |
| Field | `low` | float | 聚合區間最低價 |
| Field | `close` | float | 聚合區間最後一筆價格 |

**`shioaji_usage`** — 流量監控，由 `check_and_update_status(write_influx=True)` 寫入：

| Field | 型別 | 說明 |
|---|---|---|
| `bytes_used` | int | 已使用流量 |
| `bytes_limit` | int | 流量上限 |
| `bytes_remaining` | int | 剩餘流量 |

### Timeframe 對照表

新增 timeframe 時，以下四處必須同步更新：

| tf 秒數 | interval 字串 | `beat_schedule` Task | `SUPPORTED_HISTORY_TF` |
|---|---|---|---|
| `60` | `"1m"` | `agg_1m`（每分鐘） | ✅ |
| `300` | `"5m"` | `agg_5m`（每 5 分鐘） | ✅ |
| `3600` | `"60m"` | `agg_60m`（每小時） | ✅ |

> 前端 Toolbar 的時間週期按鈕也需一併新增。

### 禁止事項
- 同一個 Field 在不同批次的型別**必須一致**（不可混用 `int` 與 `float`），否則 InfluxDB 拒絕寫入。
- Flux 查詢**必須**先 `filter(_measurement)`，不可直接只過濾 Tag，會造成全 bucket 掃描。
- `INFLUXDB_TOKEN` **不可**硬寫於程式碼，必須透過 `.env` → `app.config` 引入。
- `monitoring` bucket **只存**維運監控資料，不可寫入 OHLC 業務資料。

---

## 指令

常見或建議的開發指令參考：

| 指令 | 用途 |
|------|------|
| `docker-compose -f docker-compose.yml up -d` | 啟動全套管線服務與基礎設施 |
