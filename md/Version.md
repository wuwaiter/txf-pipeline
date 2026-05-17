# Version History

## v0.6.0 — 2026-05-18

### Changes
- 新增動態訂閱清單管理功能（無需重啟服務）
  - `shioaji.py`：新增 `_subscribed_fop / _subscribed_stk` 追蹤目前訂閱、`reload_subscriptions()` diff 訂閱、cmd 迴圈支援 `reload` 指令
  - `main.py`：新增 `GET/POST/DELETE /api/subscriptions` 三個 endpoint，讀寫 config.toml 並發送 `reload` Redis cmd
  - `frontend/index.html`：Sidebar 新增齒輪按鈕，點擊開啟訂閱管理 Modal（可新增/刪除期貨與股票訂閱）
  - `requirements.txt`：新增 `tomli_w` 依賴（config.toml 寫入）
- 更新 `.agent/skills/txf-pipeline/SKILL.md`：補充 API 清單、cmd 指令集（`reload`）、訂閱管理資料流

---

## v0.5.0 — 2026-05-12

### Changes
- Created `md/` directory in project root
- Moved `project.md` from root to `md/` folder
- Created `md/Version.md` to track version history
- Created `.agent/Version/SKILLS.md` to document versioning skill

---

## v0.4.0 — UI modify
- UI modifications (commit: b2a8aa5)

## v0.3.0 — ScheduleTask
- Added `ScheduleTask.py` for scheduled task placement (commits: 068a82b, 90946f4)

## v0.2.0 — .gitignore update
- Modified `.gitignore` (commit: e7d1761)

## v0.1.0 — Traffic monitoring
- Added Traffic monitoring into InfluxDB (commit: 5a9fe9c)
