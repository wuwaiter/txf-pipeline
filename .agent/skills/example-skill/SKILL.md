---
name: "Example Project Skill"
description: "這是一個 Skill 的範例。您可以在這裡定義專屬此專案的特定操作流程、常規任務或除錯指南。"
---

# Skill 指南

這份 `SKILL.md` 的主要目的是讓我（AI 助手）在處理您專案內特定任務時，能夠有一個標準、依循的教材或指令！

## 當觸發這個 Skill 時，AI 會遵守的規則
1. 這裡可以寫下您專案特有的程式碼風格要求。
2. 可以放入常用的建置或測試指令，例如 `docker-compose -f docker-compse.yml up -d`。
3. 可以指導如果在 Ingestion 或 WebSocket 遇到 Error 時的標準 SOP 流程。

## 資料夾結構
除了這份 `SKILL.md` 之外，您也可以在當前這個目錄（例如 `.agent/skills/example-skill/`）底下放入其他支援的資源夾：
- `/scripts/`：放一些我可以幫您自動執行的腳本 (.sh 或 .py 等)。
- `/examples/`：放一些程式碼重構或設計模式的參考檔案。
- `/resources/`：放一些輔助文件或模板。
