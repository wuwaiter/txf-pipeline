# MSN Chatlog Viewer — 專案設計分析

## 專案概述

- **名稱**：MSN Chatlog Viewer (`msn-viewer`)
- **來源**：https://github.com/jellekralt/msn-viewer
- **作者**:jellekralt.com
- **目的**:瀏覽舊時代 MSN Messenger 匯出的 XML / TXT 格式聊天紀錄,並用懷舊的 MSN Messenger 視窗外觀重現對話。
- **類型**:單頁 Web 應用 (SPA),全部於瀏覽器端執行,無後端。

## 技術堆疊

- **框架**:React 18.3.1 (function component + hooks)
- **建構工具**:Create React App (`react-scripts` 5.0.1)
- **測試**:Jest 27 + @testing-library/react
- **樣式**:純 CSS,每個 component 一支 `.css`,無 CSS-in-JS 或 Tailwind
- **依賴**:極簡,沒有 router、狀態管理庫、UI 套件、XML 解析庫 (用瀏覽器原生 `DOMParser`);TXT 解析為自寫 regex-based parser

## 目錄結構

```
msn-viewer-main/
├── public/              # CRA 靜態資源(index.html、favicon、manifest)
├── old_data/            # 舊版 TXT 格式聊天紀錄樣本(Big5 編碼)
├── src/
│   ├── App.js           # 根 component,持有全域 state,依副檔名分流 XML/TXT 解析
│   ├── App.css          # (空檔)
│   ├── index.js         # React 進入點
│   ├── index.css        # MSN 視窗外框 + body 背景樣式
│   ├── emojiMap.js      # MSN 表情符號文字 → Unicode emoji 對照表
│   ├── parseTxt.js      # 舊版 TXT 聊天紀錄解析器
│   ├── logo.svg
│   ├── reportWebVitals.js
│   ├── setupTests.js
│   ├── __tests__/
│   │   └── App.test.js  # 整合測試(檔案上傳 + 訊息渲染)
│   └── components/
│       ├── TitleBar/        # 視窗標題列(含 _ □ × 控制按鈕)
│       ├── Toolbar/         # 工具列(7 個 emoji 裝飾按鈕)
│       ├── WarningBar/      # 安全警告列
│       ├── ChatContainer/   # 訊息滾動容器 + 日期分隔線
│       ├── ChatWindow/      # (未被 App 使用,類似 ChatContainer 的舊版)
│       ├── Message/         # 單則訊息(使用者名稱 + 內文 + 表情轉換)
│       ├── LastMessage/     # 底部「最後訊息時間」列
│       ├── InputArea/       # 檔案選擇 + 拖放上傳區
│       └── FileInput.js     # (未被使用的簡化版 input)
```

## 元件階層與資料流

```
App (state: messages, chatTitle, lastMessageDate)
├── div.msn-window
│   ├── TitleBar       ← chatTitle
│   ├── Toolbar
│   ├── WarningBar
│   ├── ChatContainer  ← messages
│   │   └── Message × N (含日期分隔線)
│   ├── LastMessage    ← lastMessageDate
│   └── div.input-section
│       └── InputArea  → onFileLoad(data, filename, format) 回傳檔案文字與格式('xml'|'txt')
└── div.footer
```

**資料流**:`InputArea` 讀取檔案 → 回呼 `App.handleFileLoad(data, filename, format)` → 按 `format` 分流到 `parseXml`(`DOMParser`)或 `parseTxtChatlog` → `setMessages/setChatTitle/setLastMessageDate` → 重新渲染下游元件。兩條解析路徑輸出同樣的 `{ dateTime, username, text }[]` 結構,下游元件無感。state 全部集中於 `App.js`,子元件皆為受控 (controlled) 或純展示元件。

## 核心邏輯

### XML 解析 ([src/App.js](src/App.js))
- 使用瀏覽器內建 `DOMParser` 將 XML 字串轉為 DOM。
- 針對每個 `<Message>` 節點取出:
  - `DateTime` 屬性 → 時間戳
  - `<From><User FriendlyName="...">` → 發訊者暱稱
  - `<Text>` textContent → 訊息內文
- 組成陣列 `{ dateTime, username, text }[]` 儲存至 state。
- 由檔名推導聊天標題:去除 `.xml` / `.txt` 與尾端數字後作為對話對象名稱。

### TXT 解析 ([src/parseTxt.js](src/parseTxt.js))
舊版 MSN Messenger 文字匯出格式,結構如下:
- **Session 標頭**:`| Session Start: 07 May 2003 |` 內嵌日期(英文月份);單一檔案可能含多個 session
- **訊息行**:`[HH:MM:SS] 暱稱..: 內文`(暱稱被截斷時以 `..` 結尾,否則直接 `:`)
- **續行**:前面縮排 11 空白,附加到前一則訊息的 `text` 後(以 `\n` 相接)
- **系統訊息**:時間戳後無 `: ` 分隔符(如檔案傳輸通知),`username` 設為 `"System"`
- 解析策略:逐行 regex 比對 `SESSION_RE` / `MESSAGE_RE` / `SYSTEM_RE` / `CONTINUATION_RE`;時間戳組合 session 日期 + 行內時分秒後以 ISO-like 本地字串 (`YYYY-MM-DDTHH:MM:SS`) 輸出
- **編碼**:TXT 檔多為 Big5(繁中)。`InputArea` 提供 big5/gbk/utf-8/shift_jis 編碼下拉選單,透過 `FileReader.readAsText(file, encoding)` 指定

### 表情符號轉換 ([src/components/Message/Message.js:7-23](src/components/Message/Message.js#L7-L23))
- `emojiMap` 定義 21 組 MSN 經典文字 emoticon → Unicode emoji (例如 `:)` → 😊、`(Y)` → 👍、`<3` → ❤️)。
- 使用 regex 切分文字,匹配到的部份包進 `<span class="emoticon">`。
- regex 鍵值有做特殊字元跳脫 (`replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')`),避免 `(K)`、`:*` 等被誤判。

### 日期分隔線 ([src/components/ChatContainer/ChatContainer.js:6-27](src/components/ChatContainer/ChatContainer.js#L6-L27))
- 逐條比對當前訊息的 `toLocaleDateString` 與上一條,不同時插入 `<div class="date-separator">`。
- 過濾空文字與無效日期。

### 檔案上傳 ([src/components/InputArea/InputArea.js](src/components/InputArea/InputArea.js))
- 同時支援「點擊選檔」與「拖放」,兩條路徑用 `FileReader.readAsText` 讀取。
- 接受 `.xml`(MIME `text/xml` 或副檔名)與 `.txt`(副檔名判斷);其他格式 `alert` 提示。
- TXT 檔讀取時使用使用者選擇的編碼(預設 `big5`),XML 走預設 UTF-8。
- 回呼格式為 `onFileLoad(data, filename, 'xml' | 'txt')`,由 `App.js` 依格式分派解析器。

## 視覺設計

復刻 **Windows XP / MSN Messenger 7.x** 時代的 Luna 藍色主題:

| 元素 | 設計特徵 |
|------|----------|
| 視窗容器 | `#f0f8ff` (AliceBlue) 背景、`#99b4d1` 淺藍邊框、圓角 3px、陰影 |
| 標題列 | 上白下淺藍漸層 (`#ffffff → #d9e7ff`),仿 XP 玻璃感 |
| 按鈕 | 同款漸層 + 淡藍框 + 3px 圓角 (`_` 最小化、`□` 最大化、`×` 關閉,純裝飾) |
| 工具列 | 7 個 emoji 按鈕 (👤💬🎮🎨📁🎵👥),純裝飾 |
| 警告列 | 淺粉底 (`#fff9f9`) + 灰字,模仿「不要透漏密碼」提示 |
| 訊息區 | 白底、12px 字、使用者名稱藍色粗體 (`#0066cc`) 配 "says:" 後折行 |
| 日期分隔線 | 置中文字 + 橫線 (透過 `::before` 偽元素疊合) |
| 底部檔案選擇 | 同款漸層按鈕 + 「拖放 .xml / .txt 檔」提示 + TXT 編碼下拉選單 |
| 字型 | `'Segoe UI', Tahoma, Geneva, Verdana, sans-serif` (XP 系統字型) |
| 外框背景 | `#eef3fa` 淡藍 |

整體為「懷舊致敬」導向,沒有 dark mode、沒有 responsive 斷點 (只用 `max-width: 600px` 置中)。

## 架構特徵與觀察

### 優點
- **極簡依賴**:只靠 React + CRA,沒有不必要的套件。
- **關注點分離乾淨**:`App` 當 state 容器,子元件各司其職,每個元件配一支 CSS。
- **資料夾慣例一致**:每個 component 自有資料夾,有利於擴充。
- **完全前端**:XML / TXT 不會離開使用者的瀏覽器,隱私友善。
- **雙格式支援**:新版 XML 與舊版 TXT 共用同一個下游渲染管線,透過兩個獨立 parser 在 App 層面分派。

### 缺點 / 可改進
- **死碼**:`ChatWindow.js` 與 `FileInput.js` 未被引用,與 `ChatContainer`、`InputArea` 功能重複,應刪除或合併。
- **App.css 空檔**,可移除。
- **CSS 重複定義**:`.chat-container` 在 `index.css` 與 `ChatContainer.css` 兩處都有定義,樣式會彼此覆蓋。
- **key 用 index**:`ChatContainer` 以陣列 index 當 React key,訊息數量大且有過濾時可能造成渲染異常,建議改用 `dateTime + username` 的穩定 key。
- **XML schema 未驗證**:假設 `<Messages><Message><From><User><Text>` 結構,對非預期格式只會吃空。
- **無 i18n**:`"says:"`、`"Last message received at"` 等字串硬寫。
- **無錯誤邊界 / loading state**:大檔案解析時畫面會卡住。
- **Toolbar 與 TitleBar 按鈕皆無互動**,純裝飾,`button` 無 `aria-label`,有無障礙問題。

## 指令

| 指令 | 用途 |
|------|------|
| `npm start` | 啟動 dev server (http://localhost:3000) |
| `npm test` | Jest watch 模式 |
| `npm run build` | 產出 `build/` production bundle |
| `npm run eject` | CRA 脫殼 (不可逆) |

## XML 輸入格式範例

```xml
<Messages>
  <Message DateTime="2024-01-01T12:00:00">
    <From>
      <User FriendlyName="Alice" />
    </From>
    <Text>Hello, World!</Text>
  </Message>
</Messages>
```

檔名建議:`<對話對象暱稱>.xml` 或 `<對話對象暱稱>001.xml` (尾端數字會被剝除作為標題)。

## TXT 輸入格式範例

```
.--------------------------------------------------------------------.
| Session Start: 07 May 2003                                         |
| Participants:                                                      |
|    Alice (alice@hotmail.com)                                       |
|    Bob (bob@hotmail.com)                                           |
.--------------------------------------------------------------------.
[01:05:15] Bob..: hello
[01:05:23] Alice..: hi there
[01:06:18] Alice..: this is
           a multi-line message
[23:14:59] Bob wants to send file "foo.txt"
```

- 單檔可包含多個 Session 區塊,時間戳會依當前 session 的日期組合
- 暱稱若在原 MSN 被截斷會以 `..` 結尾,解析時去除
- 無 `: ` 分隔符的時間戳行視為系統訊息(`username` 為 `"System"`)
- 範例檔案位於 [old_data/](old_data/)(Big5 編碼,載入時於 InputArea 選 `big5`)
