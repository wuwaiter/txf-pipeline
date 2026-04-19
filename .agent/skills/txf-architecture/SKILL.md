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

本專案的前端介面為輕量化單頁應用程式 (SPA)，不依賴龐大的建構工具（如 Webpack、Vite 等），全部採用原生 HTML/CSS/JS 開發，主要分為以下階層與視覺風格：

### 1. 元件階層與功能

| 元件層級 | 子元件/區段 | 核心功能 | 尺寸大小 (Size) | 字型設定 (Font) | 顏色配置 (Color) |
| :------- | :---------- | :------- | :-------------- | :-------------- | :--------------- |
| **Header** | Logo | 專案名稱與狀態脈衝 (`pulse`) | `1.1rem` | Inter (Bold) | 字: `--text-1`<br>點: `--accent` |
| | Status Badge | 系統連線狀態指示燈 | `0.8rem` | Inter | 底: `--bg-2`<br>字: `--text-2` |
| | Clock | 當前系統時間 | `0.85rem` | JetBrains Mono | 字: `--text-2` |
| **Sidebar** | Section Title | 分類標題 | `0.7rem` | Inter (Semi-Bold)| 字: `--text-3` |
| | Contract Card | 顯示代碼、最新價格與漲跌幅 | Code: `0.9rem`<br>Price: `1.35rem`<br>Change: `0.75rem`| 混用等寬與標準 | 底: `--bg-1` / `--bg-3`<br>字: 隨漲跌跳色 |
| **Chart Area**| Header Info | 所選合約詳細代碼報價資訊 | Code: `1.25rem`<br>Price: `2rem` | 混用等寬與標準 | 字: `--text-1` / `--text-2` |
| | Toolbar | Timeframe / K線隱藏控制鈕 | `0.8rem` | Inter | 底: 透明 / `--accent`<br>字: `--text-1`/`--text-2` |
| | K-Line View | 渲染 Lightweight Charts | 自適應填滿 | - | 底: `--bg-0` |
| | Stats Bar | 開盤/高/低/最後報價統整列 | Label: `0.68rem`<br>Value: `0.95rem` | 混用等寬與標準 | 底: `--bg-1`<br>字: `--text-1`/`--text-3`|

### 2. 視覺設計特徵與規範清單

| 設計屬性類別 | 變數/屬性名稱 | 數值參數 | 應用對象與描述 |
| :----------- | :------------ | :------- | :------------- |
| **字體 (Font)** | Primary Font | `'Inter', sans-serif` | 全局預設之中英文字體 (如 Header, 按鈕, 標籤) |
| | Monospace Font | `'JetBrains Mono', monospace` | 強調對齊的數值 (如合約代碼、價格、時間) |
| **背景色 (Bg)** | `--bg-0` | `#0b0e17` | 最底層深色背景 (Body, Chart Container) |
| | `--bg-1` | `#111520` | 第一層次背景 (Header, Sidebar, Stats Bar) |
| | `--bg-2` | `#181d2e` | 第二層次背景 (Status Badge) |
| | `--bg-3` | `#1f2640` | 高亮背景色 (Hover 狀態、Active Contract) |
| **文字色 (Text)** | `--text-1` | `#f0f4ff` | 主要高亮文字 (Primary Text) |
| | `--text-2` | `#94a3b8` | 次要資訊文字 (Secondary Text) |
| | `--text-3` | `#64748b` | 裝飾或補充資訊 (分類標題、Market Tag) |
| **輔助色 (Color)**| `--accent` | `#3b82f6` | 主題點綴色 (Logo 光點、作用中按鈕邊框) |
| | Up Color | `#22c55e` | 價格上漲提示色與 K線陽線顏色 |
| | Down Color | `#ef4444` | 價格下跌提示色與 K線陰線顏色 |
| | Flash Green | `rgba(34,197,94,.3)`| 價格上漲時的動態跳動底色 (`flash-up`) |
| | Flash Red | `rgba(239,68,68,.3)`| 價格下跌時的動態跳動底色 (`flash-dn`) |
| **邊緣效果** | `--border` | `rgba(255,255,255,.07)`| 全局分割線與元件邊框色 |
| | `--radius` | `12px` | 預設視窗與清單元件圓角 |

### 3. 前後端資料流機制
- **歷史 K 線拉取 (REST API)**：前端起始或切換合約時，向 `/api/candles` 拉取並繪製歷史 K 線。對於未有歷史支援的 timeframe，前端會直接阻擋抓取並以空白畫布等待即時資料。
- **即時報價串流 (WebSocket)**：透過 `/ws` 建立長時間連線，每 0.5 秒接收後端發送的報價快照。前端 JS 內的 `processTicks` 負責解析，並以增量狀態更新（如 K 線的 high/low/close 重繪）來最小化效能開銷。

## 架構特徵與觀察

### 優點 / 規範要求
- **關注點分離**：基礎設施設定檔 `config/` 與應用邏輯 `src/` 徹底分離。
- **容器化規範明確**：自定義 `Dockerfile` 收斂於 `docker/<服務名>/` 底下，外部設定檔於 `config/` 對應掛載，維持根目錄整潔。
- **集中參數管理**：透過 `.env` 與 `config.toml` 分開管理敏感資料與系統參數。

## 指令

常見或建議的開發指令參考：

| 指令 | 用途 |
|------|------|
| `docker-compose -f docker-compose.yml up -d` | 啟動全套管線服務與基礎設施 |
