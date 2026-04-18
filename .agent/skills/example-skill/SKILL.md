---
name: "Example Project Skill"
description: "這是一個 Skill 的範例。您可以在這裡定義專屬此專案的特定操作流程、常規任務或除錯指南。"
---

# Example Skill — 技能設計分析

## 專案概述

- **名稱**：Example Project Skill
- **目的**：提供 Skill 範本與基礎規範，作為 AI 助手處理專案特定任務時的標準、依循教材或指令指引。

## 目錄結構

除了這份主設定檔外，同目錄下（例如 `.agent/skills/example-skill/`）亦可支援配置資源資料夾：

```text
example-skill/
├── SKILL.md      # 核心行為規範與指南
├── scripts/      # 放置自動執行指令碼 (.sh 或 .py 等)
├── examples/     # 放置程式碼重構或設計模式的參考檔案
└── resources/    # 放置輔助文件或專案模板
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