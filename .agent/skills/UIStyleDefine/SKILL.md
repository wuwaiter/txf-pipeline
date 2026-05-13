---
name: frontend-ui-style
description: 定義 TXF Pipeline 前端 UI 風格規範，包含深色系 Design Token、字型、元件樣式與版面慣例。於新增或修改 frontend/ 頁面、元件、CSS 時套用，確保與現有風格一致。
---

# 前端 UI 風格規範

## 使用時機

- 新增或修改 `frontend/` 下的 HTML、CSS 時
- 使用者提到「照現有風格」「跟介面一致」「UI 風格」時
- 設計按鈕、卡片、標籤、遮罩、動畫等介面元件時

---

## 色彩系統

所有顏色統一定義於 `:root` CSS 變數，**不可在元件中硬寫十六進位色碼**。

### 背景色階（深色堆疊，數字越大越淺）

| 變數 | 用途 |
|------|------|
| `--bg-0` | 最底層，頁面 body、圖表背景 |
| `--bg-1` | 第一層，Header、Sidebar、Stats Bar |
| `--bg-2` | 第二層，Badge、狀態指示背景 |
| `--bg-3` | 第三層，Hover 狀態、Active 元件背景 |

> 實際色票值見 `txf-architecture/SKILL.md`。

### 文字色階

| 變數 | 用途 |
|------|------|
| `--text-1` | 主要文字、標題、價格數字 |
| `--text-2` | 次要說明、時間、輔助資訊 |
| `--text-3` | 裝飾性標題、placeholder、圖示 |

### 語意色

| 變數 | 語意 |
|------|------|
| `--accent` | 品牌主色、作用中元件、focus 邊框 |
| `--accent-glow` | 主色低透明度光暈（hover 疊加層） |
| `--green` | 正面狀態（連線成功、特定價格方向） |
| `--red` | 負面狀態（錯誤、斷線、特定價格方向） |

> `.up` / `.dn` 對應哪個顏色，由各專案市場慣例決定，見 `txf-architecture/SKILL.md`。

### 邊框與圓角

```css
--border: rgba(255, 255, 255, .07);  /* 半透明白，所有分隔線統一使用 */
--radius: 12px;                       /* 預設圓角；小型元件可用 8px 或 20px */
```

---

## 字型與排版

兩支字型，**職責嚴格分工，不可互換**：

| 字型 | 用途 |
|------|------|
| `'Inter', sans-serif` | 所有 UI 文字（按鈕、標籤、說明文字） |
| `'JetBrains Mono', monospace` | 數值、代碼、時間戳（會隨資料變動的數字） |

> 數字欄位使用等寬字型，確保數值更新時版面不跳動。

### 字型大小慣例

| 用途 | 大小 |
|------|------|
| 主要大數字（價格） | `1.5rem` – `2rem` |
| 標題 / 代碼 | `1rem` – `1.25rem` |
| 一般內文 | `0.85rem` – `0.9rem` |
| 次要說明 | `0.75rem` – `0.8rem` |
| 分類標題（全大寫） | `0.65rem` – `0.7rem` + `letter-spacing: .1em` |

---

## 元件規範

### 按鈕

```css
padding: 5px 12px;
border-radius: 8px;
border: 1px solid var(--border);
background: transparent;
color: var(--text-2);
font-size: .8rem;
font-family: 'Inter', sans-serif;
cursor: pointer;
transition: all .15s;
```

- **Hover**：`background: var(--bg-3); color: var(--text-1);`
- **Active**：`background: var(--accent); border-color: var(--accent); color: #fff;`

### 狀態 Badge

```css
display: flex; align-items: center; gap: 6px;
font-size: .8rem;
padding: 5px 12px;
background: var(--bg-2);
border-radius: 20px;
border: 1px solid var(--border);
color: var(--text-2);
```

狀態指示點（`.status-dot`）：

```css
width: 7px; height: 7px; border-radius: 50%;
background: var(--text-3);          /* 預設：灰 */
transition: background .3s, box-shadow .3s;

/* 已連線 */
.status-dot.connected { background: var(--green); box-shadow: 0 0 8px var(--green); }
/* 錯誤 */
.status-dot.error     { background: var(--red);   box-shadow: 0 0 8px var(--red); }
```

### 卡片 / 列表項目

```css
padding: 12px 14px;
border-radius: var(--radius);
border: 1px solid transparent;
cursor: pointer;
transition: background .15s, border-color .15s;
position: relative; overflow: hidden;  /* 供 ::before 光暈使用 */
```

Active 狀態：`background: var(--bg-3); border-color: var(--accent);`

### 光暈疊加（Glow Overlay）

用 `::before` 偽元素實現，不影響 DOM 結構：

```css
.card::before {
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(135deg, var(--accent-glow), transparent);
  opacity: 0;
  transition: opacity .2s;
}
.card:hover::before   { opacity: .5; }
.card.active::before  { opacity: 1; }
```

### 分類標題（Sidebar Section Title）

```css
font-size: .7rem;
font-weight: 600;
text-transform: uppercase;
letter-spacing: .12em;
color: var(--text-3);
```

### Stats 欄位

```css
/* 容器 */
.stats-bar { display: flex; border-top: 1px solid var(--border); background: var(--bg-1); }

/* 單一欄 */
.stat-item { flex: 1; padding: 10px 18px; border-right: 1px solid var(--border); }
.stat-item:last-child { border-right: none; }

.stat-label { font-size: .68rem; color: var(--text-3); text-transform: uppercase; letter-spacing: .1em; }
.stat-value { font-family: 'JetBrains Mono', monospace; font-size: .95rem; font-weight: 600; }
```

### 遮罩 / Overlay

空資料與隱藏狀態使用絕對定位遮罩，`pointer-events: none` 確保不攔截底層互動：

```css
.overlay {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px;
  color: var(--text-3);
  pointer-events: none;
}
/* 毛玻璃遮罩 */
.overlay.blur {
  background: rgba(11, 14, 23, .92);
  backdrop-filter: blur(6px);
}
```

---

## 動畫模式

### Pulse（心跳）— 即時連線指示燈

```css
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: .6; transform: scale(.85); }
}
/* 套用 */
animation: pulse 2s infinite;
```

### Flash（價格跳動）— 資料更新閃爍

```css
@keyframes flash-up { 0% { background: rgba(色票, .3); } 100% { background: transparent; } }
@keyframes flash-dn { 0% { background: rgba(色票, .3); } 100% { background: transparent; } }
/* 套用 */
animation: flash-up .4s ease;
```

> `flash-up` / `flash-dn` 對應的實際顏色由市場慣例決定，見 `txf-architecture/SKILL.md`。

---

## 版面與間距

- **Header**：`padding: 14px 28px`，`position: sticky; top: 0; z-index: 100`，`backdrop-filter: blur(12px)`
- **主佈局**：`display: grid; grid-template-columns: <sidebar-width> 1fr`（寬度見 txf-architecture）
- **區塊間隔**：`gap: 0`（靠 border 分隔）
- **捲軸樣式**：

```css
::-webkit-scrollbar       { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--bg-3); border-radius: 4px; }
```

---

## HTML 慣例

- 一律 `<html lang="zh-TW">`
- Reset：`*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }`
- Google Fonts 引入 Inter 與 JetBrains Mono：
  ```html
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700
    &family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet" />
  ```

---

## 禁止事項

- **不可**在元件中硬寫色碼，所有顏色必須使用 `var(--*)` Design Token。
- **不可**在數值顯示欄位使用 Inter，數字跳動時版面會抖動。
- **不可**自行增加未定義的 `--bg-4` 等層級，需先在 `:root` 定義並說明語意。
- **不可**對裝飾性元素加超過 0.5s 的動畫，避免干擾資料閱讀。

---

## 檢查清單（新增 / 修改頁面時）

- [ ] 所有顏色使用 CSS 變數，無硬寫色碼
- [ ] 數字欄位使用 JetBrains Mono，UI 文字使用 Inter
- [ ] 按鈕、Badge、卡片圓角與 transition 與現有一致
- [ ] Active / Hover 狀態使用 `--bg-3` 與 `--accent`
- [ ] 狀態指示點（dot）使用 connected / error class 切換
- [ ] 新增動畫時長 ≤ 0.5s（pulse 除外）
- [ ] Overlay 加上 `pointer-events: none`
