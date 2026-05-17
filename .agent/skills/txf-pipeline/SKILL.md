---
name: "txf-pipeline"
description: "TXF Pipeline 專案專屬規範：目錄結構、設定管理、程式碼職責分工、Redis 與 InfluxDB 資料層、前端 UI 特殊套用。通用 UI 規則見 UIStyleDefine/SKILL.md。"
---

# TXF Pipeline — 架構規範

> 系統架構圖見 `md/project.md`。

## 目錄結構

```text
txf-pipeline/
├── .agent/                         # Agent 規範與 Skill 定義
│   └── skills/
│       ├── SKILL.md                # Skills 索引
│       ├── CodingStyle/SKILL.md    # 程式碼風格規範
│       ├── CICD_Define/SKILL.md    # CI/CD 最佳實踐藍圖
│       ├── InfluxDB-Schema/SKILL.md# InfluxDB 通用操作規範
│       ├── Redis/SKILL.md          # Redis Stream 通用操作規範
│       ├── Shioaji/SKILL.md        # 永豐金 API 串接規則
│       ├── UIStyleDefine/SKILL.md  # 前端 UI 風格通用規範
│       ├── Version/SKILL.md        # 版本管理慣例
│       ├── example-skill/SKILL.md  # Skill 範本
│       └── txf-pipeline/SKILL.md   # 本專案專屬規範（本檔）
│
├── .env                            # 敏感資料（API Key、DB 帳密），不進版控
├── .gitignore
├── config.toml                     # 系統參數（Port、Host、訂閱清單等）
├── docker-compose.yml              # 全服務啟動定義
│
├── cert/                           # 憑證與私鑰（不進版控）
├── config/                         # 各服務掛載用設定檔
│   ├── influxdb/
│   │   ├── influxdb.conf
│   │   └── init-buckets.sh
│   └── grafana/
│       ├── dashboards/market_dashboard.json
│       └── provisioning/
│           ├── dashboards/dashboard.yaml
│           └── datasources/influxdb.yaml
│
├── docker/
│   └── python/Dockerfile
│
├── frontend/index.html             # 前端 SPA（原生 HTML/CSS/JS）
├── md/
│   ├── Version.md                  # 版本歷史記錄
│   └── project.md                  # 系統架構圖（Mermaid）
│
├── src/
│   └── app/
│       ├── config.py               # 統一讀取 .env 與 config.toml
│       ├── main.py                 # Flask App + WebSocket 入口
│       ├── services/
│       │   ├── redis_client.py
│       │   └── influx_client.py
│       └── workers/
│           ├── shioaji.py          # Shioaji 登入 / 訂閱 / Ingest 邏輯
│           ├── collector.py        # Celery 排程 + OHLC 聚合
│           └── ScheduleTask.py     # 排程任務定義
│
├── logs/                           # 執行時期 log（不進版控）
├── tests/                          # 測試（待補充）
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## 設定管理

| 類型 | 位置 | 範例 |
|---|---|---|
| 敏感資訊 | `.env` | API Key、DB 帳密、Token |
| 系統參數 | `config.toml` | Port、Host、訂閱清單 |
| 統一讀取 | `src/app/config.py` | 供全專案引用，不可在其他檔案直接讀取 `.env` |

## 程式碼職責分工

| 目錄 | 職責 |
|---|---|
| `src/app/services/` | 基礎設施連線封裝（Redis、InfluxDB client） |
| `src/app/workers/` | 資料擷取（Shioaji ingest）、排程聚合（Celery）、排程任務定義 |
| `src/app/main.py` | Flask App、REST API、WebSocket 入口 |
| `frontend/` | 前端 SPA 靜態檔案，由 Flask 掛載服務 |
| `config/` | Docker 服務掛載用設定檔（InfluxDB、Grafana），非應用程式參數 |

## Redis 資料層規範

### Key 命名規則

所有 Key 以 `REDIS_STREAM_KEY`（預設 `tick:txf`，由 `config.toml` 的 `redis.stream_key` 控制）為前綴：

| Key 格式 | 類型 | 用途 |
|---|---|---|
| `tick:txf:fop:<code>` | Redis Stream | 期貨 Tick 報價 |
| `tick:txf:stk:<code>` | Redis Stream | 股票 Tick 報價 |
| `tick:txf:status` | String | 連線狀態（`connected` / `disconnected` / `unknown`） |
| `tick:txf:cmd` | String | 指令通道（`login` / `usage` / `check_usage`） |
| `tick:txf:usage_bytes` | String | Shioaji 已用流量（bytes，整數字串） |
| `tick:txf:limit_bytes` | String | Shioaji 流量上限（bytes，整數字串） |

> 新增商品類型時，前綴一律沿用 `tick:txf:<type>:<code>`，`<type>` 使用小寫縮寫。

### Stream 資料結構

```python
{"price": str(quote.close), "ts": str(int(time.time()))}
# 讀取：float(data["price"])、float(data["ts"])
```

### 指令集（cmd 通道）

每 5 秒輪詢，讀取後須立即 `r.delete(...)` 清除。優先順序：`login` > `reload` > `check_usage` > `usage`

| 指令值 | 觸發來源 | 行為 |
|---|---|---|
| `login` | 前端「重新連線」→ `POST /api/reconnect` | 重新 login + subscribe，不寫 InfluxDB |
| `reload` | 前端訂閱管理 Modal → `POST/DELETE /api/subscriptions` | 動態 diff 訂閱清單（不重新登入），不寫 InfluxDB |
| `usage` | 頁面開啟 / WebSocket 建立 | 只刷新流量顯示，不寫 InfluxDB |
| `check_usage` | ScheduleTask 背景排程（每分鐘） | 刷新流量並寫入 InfluxDB monitoring bucket |

### decode_responses 規則

| 模組 | decode_responses | 原因 |
|---|---|---|
| `main.py`（Flask / WS） | `True` | 直接操作字串 |
| `collector.py`（Celery Worker） | `False` | 聚合時比對 bytes prefix 效能較高 |

### 禁止事項
- Tick 報價**必須**用 `xadd` 寫入 Stream，不可用 `set/get`。
- 掃描所有 Key 時**必須**過濾非 Stream Key（`status`、`cmd`、`usage_bytes`、`limit_bytes`）。
- **不可**自行發明新的 Key 命名前綴。

---

## InfluxDB 資料層規範

### Bucket 設計

| Bucket | 來源常數 | 用途 |
|---|---|---|
| `txf` | `INFLUXDB_BUCKET`（`.env`） | 主要 OHLC K 線業務資料 |
| `monitoring` | `INFLUXDB_MONITORING_BUCKET`（`config.py`） | Shioaji API 流量監控 |

> Bucket 名稱**不可**硬寫於 `collector.py`，必須從 `app.config` 引入常數。

### Measurement Schema

**`txf`** — OHLC K 線，由 `_aggregate_and_write()` 寫入：

| 屬性 | 名稱 | 型別 | 值域 |
|---|---|---|---|
| Tag | `interval` | string | `"1m"` / `"5m"` / `"60m"` |
| Tag | `market` | string | `"futures"` / `"stocks"` |
| Tag | `code` | string | 合約代碼（如 `"TXFR1"`、`"2330"`） |
| Field | `open` / `high` / `low` / `close` | float | OHLC 價格 |

**`shioaji_usage`** — 流量監控，由 `check_and_update_status(write_influx=True)` 寫入：

| Field | 型別 |
|---|---|
| `bytes_used` / `bytes_limit` / `bytes_remaining` | int |

### Timeframe 對照表

新增 timeframe 時，以下四處必須同步更新：

| tf 秒數 | interval | Celery Task | `SUPPORTED_HISTORY_TF` | 前端 Toolbar |
|---|---|---|---|---|
| `60` | `"1m"` | `agg_1m` | ✅ | ✅ |
| `300` | `"5m"` | `agg_5m` | ✅ | ✅ |
| `3600` | `"60m"` | `agg_60m` | ✅ | ✅ |

### 禁止事項
- 同一 Field 型別在不同批次**必須一致**（`int` / `float` 不可混用）。
- Flux 查詢**必須**先 `filter(_measurement)`，不可直接只過濾 Tag。
- `INFLUXDB_TOKEN` **不可**硬寫，必須透過 `.env` → `app.config` 引入。
- `monitoring` bucket **只存**維運資料，不可寫入 OHLC 業務資料。

---

## 前端 UI 規範

> 通用風格規則（Design Token 系統、字型、元件模式、動畫）定義於 `UIStyleDefine/SKILL.md`。
> 本章節定義本專案在通用規則之上的**特殊套用與覆寫**。

### Design Token 實際色票

```css
:root {
  --bg-0: #0b0e17;                     /* 頁面底色、圖表背景 */
  --bg-1: #111520;                     /* Header、Sidebar、Stats Bar */
  --bg-2: #181d2e;                     /* Status Badge */
  --bg-3: #1f2640;                     /* Hover、Active Contract */
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

### 漲跌色慣例（台灣市場，覆寫通用語意）

本專案依台灣市場慣例，**漲為紅、跌為綠**，與 `UIStyleDefine` 中 `--red` / `--green` 的直覺語意相反：

| CSS Class | 顏色 | 語意 |
|---|---|---|
| `.up` | `#ef4444`（`--red`） | 價格上漲 |
| `.dn` | `#22c55e`（`--green`） | 價格下跌 |
| `.up-muted` | `#d77a7a` | 上漲（淡） |
| `.dn-muted` | `#7ad79a` | 下跌（淡） |
| `.flat-muted` | `#d7cd7a` | 平盤 |

Flash 動畫：`.flash-up` → `rgba(239, 68, 68, .3)`；`.flash-dn` → `rgba(34, 197, 94, .3)`

### 版面尺寸

| 區域 | 尺寸 |
|---|---|
| Sidebar | `260px`（固定） |
| 主佈局 | `grid-template-columns: 260px 1fr` |
| Chart container | `flex: 1; min-height: 0` |

### 元件尺寸對照

| 元件 | 子項目 | 字型大小 | 字型 |
|---|---|---|---|
| Header | Logo | `1.1rem` | Inter Bold |
| | Status Badge / Clock | `0.8rem` / `0.85rem` | Inter / JetBrains Mono |
| Sidebar | Section Title | `0.7rem` | Inter Semi-Bold |
| | 合約代碼 | `0.9rem` | JetBrains Mono |
| Chart Header | 選中代碼 / 選中價格 | `1.25rem` / `2rem` | JetBrains Mono Bold |
| | Toolbar 按鈕 | `0.8rem` | Inter |
| Stats Bar | Label / Value | `0.68rem` / `0.95rem` | Inter / JetBrains Mono |

### REST API 一覽

| Method | Path | 功能 |
|---|---|---|
| `GET` | `/api/streams` | 所有合約最新 tick 快照 |
| `POST` | `/api/reconnect` | 觸發 shioaji.py 重新 login + subscribe |
| `GET` | `/api/candles?code=&tf=` | 指定合約 K 線（tf=60/300/3600） |
| `GET` | `/api/subscriptions` | 讀取 config.toml 訂閱清單 |
| `POST` | `/api/subscriptions` | 新增一筆訂閱（寫 config.toml + 發 reload cmd） |
| `DELETE` | `/api/subscriptions` | 刪除一筆訂閱（寫 config.toml + 發 reload cmd） |

### 前後端資料流

- **歷史 K 線**：`GET /api/candles?code=&tf=`，拉取最近 60 根；不支援的 timeframe 不發請求，等待即時資料。
- **即時報價**：`/ws` WebSocket，每 0.5 秒推送；`processTicks()` 增量更新 K 線（只重繪 high/low/close）。
- **訂閱管理**：前端 Sidebar 齒輪按鈕開啟 Modal，透過 `GET/POST/DELETE /api/subscriptions` 管理；`main.py` 寫入 config.toml 後發送 `reload` Redis cmd，`shioaji.py` 執行 diff 訂閱。

### Lightweight Charts 整合

- CDN：`unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js`
- 圖表背景：`--bg-0`；陽線：`#ef4444`；陰線：`#22c55e`

---

## 指令

| 指令 | 用途 |
|---|---|
| `docker-compose up -d` | 啟動全套服務 |
