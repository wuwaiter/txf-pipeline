# TXF Pipeline

台指期 (TXF) 與股票的即時報價及 K 線圖資料管線系統。採用現代微服務架構，全後端使用 Python 實現並透過 Docker Compose 統一管理。

## 系統架構圖 (架構與流程)

```mermaid
graph TD
    Shioaji[Sinopac API\nShioaji]
    Ingest(python-ingest\ncollector.py)
    Redis[(Redis Stream\ntick:txf:*)]
    Flask[flask-web\nmain.py :8080]
    Frontend[Browser\nTrading Dashboard]
    Worker(celery-worker\ncollector.py)
    Beat(celery-beat\ncollector.py)
    Influx[(InfluxDB :8086)]
    Grafana[Grafana :3000]

    Shioaji -->|即時 Tick| Ingest
    Ingest -->|xadd| Redis
    Redis -->|xrevrange| Flask
    Flask <-->|WebSocket /ws| Frontend

    Beat -.->|定時派發 1m/5m/60m| Worker
    Worker -->|xrange OHLC| Redis
    Worker -->|write| Influx
    Grafana -->|query| Influx
```

## 核心流程與服務運作

1. **報價接收 (Python Ingest)**:
   透過永豐金證券 Shioaji API，根據 `config.toml` 設定訂閱期貨與股票的即時 Tick 報價資料。接收到報價後，會打入 Redis Stream 當中。
2. **訊息佇列與暫存 (Redis)**:
   作為資料交換中心，並利用 **Redis Stream** 來保存時間序列的報價。
   - **Stream 初始化與對應機制**: Stream 的前綴 key 預設為 `tick:txf` (可於 `config.toml` 的 `stream_key` 配置)。當 Ingest 收到新報價時，會自動組合出專屬的 Stream Key。例如：期貨合約 TXFD6 會寫入 `tick:txf:fop:TXFD6`，股票 2330 則是寫入 `tick:txf:stk:2330`。Redis Stream 不需要事先建立，在執行第一次 `XADD` 指令時就會自動預設並生成持久化的 Stream 結構，供其他服務隨時取用與追溯最新 Tick。
3. **Web 服務 (Flask Web)**:
   監聽 8080 端口，不僅負責發送靜態的前端資源，也建立 WebSocket 端點 `/ws` 提供連線。它會定期從 Redis 中掃描所有 `tick:txf:*` Stream，並向所有連線的前端即時推送最新價格。
4. **前端展示層 (Frontend)**:
   現代化的即時交易看板。透過 WebSocket 即時接收更新，並使用 Lightweight Charts 在客戶端動態繪製 K 線圖、呈現閃爍報價跳動以及開高低收等統計數據。
5. **歷史資料落地與聚合 (Celery / InfluxDB)**:
   - **Celery Beat**: 扮演「排程器」的角色，負責「發號施令」。根據系統中定義的任務時間表 (如每分鐘、每 5 分鐘、每 60 分鐘)，定時往訊息列發送觸發訊號。Celery Beat 面並不處理任何具體的計算。
   - **Celery Worker**: 扮演負責「執行勞力」的工作節點。它會在後台不斷監聽佇列，一收到 Celery Beat 的觸發信號，就會進入 Redis 取出過去 N 秒內的即時報價，根據這些數據算出開盤 (Open)、最高 (High)、最低 (Low)、收盤 (Close) 的 OHLC K棒聚合數值，並寫入 InfluxDB 持久化儲存。你可以根據負載開多個 worker 來平衡工作量。
   - **InfluxDB**: 時間序列資料庫，保存以上計算好的歷史 K 線資料至專屬 Bucket。
6. **數據視覺化儀表板 (Grafana)**:
   監聽 3000 埠，連接並查詢 InfluxDB 中的資料，提供圖表化檢視歷史 K 線與報價聚合趨勢。預設已自動配置 Data Source 與 Dashboard。

## 服務清單 (Docker Compose Services)

專案使用 `docker-compose.yml` 統一啟動全系統，主要服務與用途如下：

| 服務名稱        | 連接埠號 (外:內) | 說明與用途 |
| --- | --- | --- |
| **redis** | `6379:6379` | 記憶體資料庫，做為即時 Tick 的高速串流佇列存儲與 Celery Broker。 |
| **influxdb** | `8086:8086` | 時間序列資料庫，存放計算好的各週期開高低收 (OHLC) 歷史資料。 |
| **grafana** | `3000:3000` | 用於圖表化檢視歷史報價趨勢的 Dashboard 儀表板。 |
| **flask-web** | `8080:8080` | Web 與 WebSocket 伺服器，負責服務前端網頁與推送即時報價。 |
| **python-ingest** | `N/A` | Shioaji API 接收報價轉拋至 Redis Stream。 |
| **celery-worker** | `N/A` | 負責執行非同步資料聚合背景任務 (1m, 5m, 60m OHLC)。 |
| **celery-beat** | `N/A` | 定時排程派發器，定時觸發 Celery Worker 執行聚合任務。 |

## 資料流向 (Data Flow)

**【即時圖表呈現流程】**
`Shioaji API` -> `Python Ingest` -> `Redis` (tick:txf) -> `Flask Web` (WebSocket) -> `Frontend Dashboard`

**【歷史紀錄與聚合流程】**
`Redis` (tick:txf) -> `Celery Worker/Beat` 取出一段區間的資料計算 OHLC -> 寫入 `InfluxDB` -> 透過 `Grafana` 查詢與呈現

## 開發技術棧 (Tech Stack)

- **核心語言**: Python, Rust (高效能併發), HTML/JS
- **資料庫/快取**: Redis, InfluxDB 2
- **排程與非同步任務**: Celery
- **API 與連線**: WebSocket (Warp 框架), Shioaji API (取得台股報價)
- **前端圖表**: TradingView Lightweight Charts
- **基礎設施**: Docker, Docker Compose, Nginx

## 執行與部署指引

1. 確保已安裝 Docker 及 Docker Compose。
2. 進入專案根目錄。
3. 建立並設置您的 `.env` 檔案（填入您的 Shioaji 憑證與密碼）。
4. （可選）在 `config.toml` 中調整想訂閱的股票或期貨合約代碼。
5. 執行命令啟動所有服務：
```bash
docker-compose up -d --build
```

### 存取服務

| 服務 | 網址 |
|---|---|
| 即時交易看板 | http://localhost:8080 |
| Grafana 儀表板 | http://localhost:3000 |
| InfluxDB 控制台 | http://localhost:8086 |

## 開發

安裝本地開發依賴：
```bash
pip install -r requirements.txt
```

### 環境堆疊與技術
- **微服務與佈署**: Docker, Docker Compose
- **Web 與 API**: Python Flask, Flask-Sock (WebSocket)
- **非同步與排程**: Celery
- **外部 API 整合**: Sinopac Shioaji
- **資料儲存與傳遞**: Redis (Stream), InfluxDB 2.x
- **資料展示**: HTML/CSS/JS, Lightweight Charts, Grafana