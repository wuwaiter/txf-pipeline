---
name: "Example Project Skill"
description: "這是一個專案的範例。在這裡定義專案的特定操作流程、常規任務或除錯指南。"
---

# Example Skill — 技能設計分析
## 目錄結構
```text
txf-pipeline/
├── .agent/                         # Agent 規範與 Skill 定義
│   └── skills/
│       ├── SKILL.md                # Skills 索引
├── cert/                           # 憑證與私鑰（不進版控）
├── config/                         # 各服務掛載用設定檔
├── docker/                         # Dockerfile（映像建置定義）
├── frontend/                       # 前端 SPA（原生 HTML/CSS/JS）
│   └── index.html
├── md/                             # 專案文件（README 除外）
│   ├── Version.md                  # 版本歷史記錄
│   └── project.md                  # 系統架構圖
├── src/
│   └── app/
│       ├── __init__.py
│       ├── config.py               # 統一讀取 .env 與 config.toml
│       ├── main.py                 # Flask App + WebSocket 入口
│       ├── api/
│       ├── services/
│       │   ├── redis_client.py     # Redis 連線封裝
│       │   └── influx_client.py    # InfluxDB 連線封裝
│       └── workers/
│           ├── collector.py        # Celery 排程 + OHLC 聚合 + 寫入 InfluxDB
│           └── ScheduleTask.py     # 排程任務定義
│
├── tests/                          # 測試（待補充）
├── .env                            # 敏感資料（API Key、DB 帳密），不進版控
├── .gitignore
├── config.toml                     # 系統參數（Port、Host、訂閱清單等）
├── docker-compose.yml              # 全服務啟動定義
├── pyproject.toml                  # Python 專案設定
├── requirements.txt                # 正式依賴
├── requirements-dev.txt            # 開發依賴
└── README.md                       # 專案說明（保留於根目錄）
```

## 核心邏輯 

### 當觸發此 Skill 時的行為守則
1. **程式碼風格**：強制遵守專案內特有之命名與排版要求。
2. **例外處理**：指導開發者或 AI 處理諸如 Ingestion 中斷或 WebSocket 連線失敗時的 SOP 流程。
3. **擴充輔助**：透過附帶的腳本與模板，快速整合常見開發需求。

## 架構特徵與觀察

### 優點
- **架構擴充性高**：不限於純文字描述，可外掛 `scripts/` 等實際資源。
- **標準化流程**：讓每一次修改都有除錯 SOP 與測試指令作為依循。

## 指令

| 指令 | 用途 |
|------|------|
| `docker-compose -f docker-compse.yml up -d` | 建置並在背景啟動專案服務容器 |