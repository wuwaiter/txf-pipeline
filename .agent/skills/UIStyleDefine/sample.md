---
name: frontend-ui-style
description: 定義 GanttProject 前端 UI 風格規範，包含色彩、字型、元件樣式與版面慣例。於新增或修改 frontend 頁面、元件、CSS 時套用，確保與現有一致。
---

# 前端 UI 風格規範

## 使用時機

- 新增或修改 `frontend/` 下的 HTML、CSS、頁面元件時
- 使用者提到「照現有風格」「跟其他頁面一致」「UI 風格」時
- 設計表單、按鈕、表格、卡片、通知等介面時

---

## 色彩系統

### 背景
- **一般頁面**：`linear-gradient(135deg, #f5f7fa 0%, #174568ff 100%)`
- **首頁**：深色 `linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)`，文字與按鈕為淺色

### 主色與語意色
| 用途 | 主色 | Hover / 深色 |
|------|------|--------------|
| 主要按鈕、連結、焦點 | #2196f3 | #1976d2 |
| 成功、篩選、確認 | #4caf50 | #45a049 |
| 警告 | #ff9800 | #f57c00 |
| 錯誤、危險 | #f44336 | #d32f2f |
| 次要 / 返回 | #666 | #555 |
| 紫色強調（特定頁如任務執行） | #ba68c8 | #ab47bc |

### 中性色
- 邊框：`#ddd`、`#dee2e6`
- 表頭背景：`#f8f9fa`
- 表頭 hover：`#e9ecef`
- 次要文字：`#6c757d`、`#333`

### 焦點樣式
- 輸入框/選單 focus：`border-color` 改為主色，並加 `box-shadow: 0 0 0 2px rgba(主色, 0.1)`

---

## 字型與排版

- **字型**：`font-family: Arial, sans-serif;`
- **語言**：`<html lang="zh-TW">`
- **內文**：`font-size: 14px`
- **標題**：依層級使用 `font-weight: bold` 或 `600`，必要時 `text-shadow` 配合深色背景

---

## 元件規範

### 按鈕
- `padding: 8px 16px`，`border-radius: 6px`，`font-size: 14px`
- `border: none`，`cursor: pointer`，`transition: background-color 0.3s`（或 `all 0.3s ease`）
- 主按鈕：主色背景、白字；次要：`background-color: #666`
- 首頁導航按鈕可用 `min-width: 180px`、`border-radius: 10px`、`padding: 20px 30px`，hover 可 `transform: translateY(-5px)` 與陰影

### 表單控制項（input / select）
- `padding: 8px 12px`，`border: 1px solid #ddd`，`border-radius: 6px`，`font-size: 14px`，`background-color: white`
- focus：`outline: none`，邊框與 box-shadow 改為主色

### 搜尋/篩選區塊（.search-container、.filter-container）
- 背景白、`padding: 20px`、`border-radius: 10px`、`box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1)`
- 篩選區可加 `border-left: 4px solid #4caf50` 或對應語意色
- 內部用 `display: flex`、`flex-wrap: wrap`、`gap: 10px` 或 `12px`、`align-items: center`

### 表格（.table）
- 背景白、`border-radius: 10px`、`overflow: hidden`、`box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1)`
- `th`：`background-color: #f8f9fa`，`padding: 12px`，`border-bottom: 2px solid #dee2e6`
- `td`：`padding: 12px`，`border-bottom: 1px solid #dee2e6`
- `tbody tr:hover`：`background-color: #f8f9fa`
- 可排序表頭：`.sortable` 用 `::after` 顯示 ↕，`.sort-asc` ↑、`.sort-desc` ↓，箭頭色可用主色

### 卡片（.card）
- 背景白、`border-radius: 10px`、`box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1)`、`padding: 20px`、`margin-bottom: 20px`
- `.card-header`：`border-bottom: 1px solid #dee2e6`，`padding-bottom: 10px`，`margin-bottom: 15px`

### 狀態標籤（.status-badge）
- `padding: 4px 8px`，`border-radius: 4px`，`font-size: 12px`，`font-weight: bold`，`text-transform: uppercase`
- 語意類：`.status-running` 綠、`.status-completed` 青、`.status-paused` 黃底深字、`.status-not-started` 灰

### 通知 / 提示（.notification、.alert）
- 固定 `position: fixed; top: 20px; right: 20px`，`z-index: 10000`
- `border-radius: 6px` 或 `8px`，`box-shadow: 0 4px 12px rgba(25, 105, 159, 0.15)`，`max-width: 300px~350px`
- 類型：`.notification-info` / `.alert-info` 藍、`.notification-success` / `.alert-success` 綠、`.notification-warning` / `.alert-warning` 橙、`.notification-error` / `.alert-error` 紅
- 可搭配 `animation: slideInRight 0.3s ease` 自右滑入

### 載入動畫（.loading）
- 小圓形旋轉：`border` 淺灰 + 主色 `border-top`，`border-radius: 50%`，`animation: spin 1s linear infinite`

---

## 版面與間距

- 頁面 `body`：`margin: 0`，`padding: 20px`，`min-height: 100vh`
- 區塊間：`margin-bottom: 20px` 或 `margin-top: 20px`，表單內用 `gap: 10px` / `12px`
- 網格：`.grid` + `.grid-2` / `.grid-3` / `.grid-4`，`gap: 20px`
- 工具類：`.mt-10`、`.mb-20`、`.p-20` 等 10/20px 間距；`.text-center`、`.hidden` 等

---

## 響應式

- 斷點：`@media (max-width: 768px)`
- 搜尋/篩選可改 `flex-direction: column`、`align-items: stretch`
- 表格可縮小 `padding`、`font-size: 14px`
- 網格改為單欄：`grid-template-columns: 1fr`

---

## 甘特圖相關

- 容器：`.gantt-container`，`border-radius: 8px`，高度可用 `70vh` 或變數
- 圖例：`.legend-container` 用 flex、`gap: 20px`、置中
- 統計區：`.stats-container` 白底、圓角、陰影，內部分欄

---

## CSS 檔案結構

- **共用**：`frontend/css/common.css` — 按鈕、表單、表格、卡片、狀態、通知、工具類、甘特共用等
- **頁面專用**：`frontend/css/index.css`、`byproject.css`、`byuser.css` 等，在 common 之後引入以覆寫
- 新頁面：先引用 `common.css`，再引用該頁專用 CSS；盡量把共用樣式放在 common，避免重複

---

## HTML 慣例

- 一律 `<html lang="zh-TW">`
- `<head>` 內：`<link rel="icon" type="image/x-icon" href="favicon.ico">`、`<meta charset="UTF-8" />`、必要時 viewport
- 共用腳本：`config.js`、`js/common/api.js`、`js/common/utils.js`（依頁面需要引入）
- 區塊標題可搭配 emoji（如 🔍）與 `h3`，保持與現有頁面一致

---

## 檢查清單（新增/修改頁面時）

- [ ] 背景與主色符合上述色彩系統
- [ ] 按鈕、輸入框、表格使用既有 class 或相同數值
- [ ] 圓角（6px / 10px）、陰影、間距與現有頁面一致
- [ ] 有 768px 響應式考量
- [ ] 共用樣式放在 common.css，頁面專用放在對應 CSS 檔
- [ ] HTML 含 lang、favicon、必要 script 引用
