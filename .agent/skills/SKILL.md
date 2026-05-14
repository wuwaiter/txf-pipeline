# TXF Pipeline — Skills 索引

本目錄定義 AI Agent 處理此專案時的行為規範與參考指南。
各 Skill 獨立成資料夾，觸發條件與用途如下：

| Skill | 觸發時機 |
|---|---|
| `txf-pipeline` | 修改目錄結構、新增服務、調整設定管理、UI 元件對照 |
| `CodingStyle` | 新增或修改任何 `src/` Python 檔案、Code Review、重構 |
| `Shioaji` | 修改永豐金 API 串接、訂閱邏輯、流量處理 |
| `Redis` | 新增 Redis 操作、擴充 Stream Key、調整指令通道 |
| `InfluxDB-Schema` | 修改 InfluxDB 查詢、新增 Measurement 或 Field |
| `UIStyleDefine` | 新增或修改前端元件、CSS 樣式、動畫 |
| `CICD_Define` | 建立或修改 GitHub Actions、部署流程 |
| `Version` | 每次功能變更後更新版本紀錄 |
| `example-skill` | 建立新 Skill 時的格式範本 |
