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
