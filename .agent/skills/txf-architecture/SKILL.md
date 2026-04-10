---
name: "TXF Pipeline Architecture"
description: "定義了 TXF Pipeline 專案的標準目錄結構及配置規則，確保未來重構或新增功能時皆符合此設計。"
---

# TXF Pipeline 架構標準指南

在協助開發、重構或處理任務時，請一律遵守以下的專案結構及規範。

## 目錄結構標準

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

## 開發與修改規則

1. **參數與環境變數管理**：
    - **敏感資訊**（例如 API_KEY, DB 帳號密碼等）必須移至 `.env` 中管理。
    - **系統參數**（如 Port, Host 網址, 相關參數配置等）必須移至 `config.toml` 中管理。
    - 由 `src/app/config.py` 負責統一讀取環境變數與 TOML 參數，供專案全局參照。

2. **程式碼配置與職責**：
    - 所有核心邏輯必須置於 `src/app/` 之下。
    - 提供外界與基礎建設連線的客戶端或封裝（如 Redis, InfluxDB 的 Client）實作於 `services/`。
    - 外部資料搜集（爬蟲機制）與定時排程聚合的邏輯（如 Celery 分鐘級資料聚合）等實作，統一集中在 `workers/collector.py`。

3. **容器化規範**：
    - 專案中所自定義的 `Dockerfile` 都要放入 `docker/<服務名>/` 底下。
    - `docker-compose.yml` 所需使用的外部設定檔（例：grafana dashboard 注入、預設配置），必須收斂到根目錄的 `config/` 底下並對應各自的服務資料夾掛載。
