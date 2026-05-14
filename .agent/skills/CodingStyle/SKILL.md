---
name: "CodingStyle"
description: "定義專案的程式碼風格規範，涵蓋 Python 命名、型別標注、Docstring、Import 順序、錯誤處理與 Print 慣例。新增或修改任何 src/ 下的 Python 檔案時套用。參考自 Google Python Style Guide 與 PEP 8。"
---

# Coding Style 規範

## 使用時機

- 新增或修改 `src/` 下任何 Python 檔案時
- Code Review 或重構既有程式碼時
- 使用者提到「風格」「命名」「格式」「排版」時

> 參考來源：[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)、[PEP 8](https://peps.python.org/pep-0008/)

---

## 命名規則

| 對象 | 風格 | 範例 |
|---|---|---|
| 函式 / 方法 | `snake_case` | `get_redis_client()`, `perform_login()` |
| 私有函式 | `_snake_case`（單底線前綴） | `_get_latest_ticks()`, `_aggregate_and_write()` |
| 變數 | `snake_case` | `stream_key`, `used_bytes` |
| 常數（模組層級） | `UPPER_SNAKE_CASE` | `REDIS_STREAM_KEY`, `FOP_PREFIX` |
| 類別 | `PascalCase` | `RedisClient`, `InfluxWriter` |
| 例外類別 | `PascalCase` + `Error` 後綴 | `ConnectionError`, `QuotaExceededError` |

> 名稱應具描述性，避免單字母（`i`、`x` 等）除非是極短的 loop 變數。

---

## Import 順序

依 PEP 8 與 Google Style Guide，分三區塊，區塊間空一行：

```python
# 1. 標準函式庫
import os
import time
import json

# 2. 第三方套件
from flask import Flask, jsonify
from influxdb_client import Point

# 3. 本專案模組
from app.config import REDIS_STREAM_KEY
from app.services.redis_client import get_redis_client
```

- 每區塊內依字母排序
- 使用 `from X import Y` 優先於 `import X.Y`
- **不可**使用 `from X import *`

---

## 型別標注（Type Hints）

所有公開函式的參數與回傳值**必須**標注型別：

```python
# ✅ 正確
def get_redis_client(decode_responses: bool = True) -> redis.Redis:
    ...

def _get_latest_ticks() -> list[dict]:
    ...

def _fetch_from_influx(code: str, tf_seconds: int) -> dict[int, dict]:
    ...

# ❌ 不標注
def perform_login(api):
    ...
```

- 使用 Python 3.10+ 內建泛型語法（`list[dict]` 而非 `List[Dict]`）
- 複雜型別可用 `type` alias 或 `TypeAlias`

---

## Docstring 規範

### 模組層級

檔案開頭使用三引號說明職責，以編號清單列出：

```python
"""
collector.py
------------
整合三大職責：
1. Shioaji Tick 即時報價擷取 -> 寫入 Redis Stream
2. Celery 定時排程 (1m / 5m / 60m)
3. OHLC 聚合計算 -> 寫入 InfluxDB
"""
```

### 函式層級

單行說明使用中文，複雜函式加參數說明：

```python
def _get_latest_ticks() -> list[dict]:
    """掃描所有 tick stream keys，回傳每個合約的最新 tick。"""
    ...

def check_and_update_status(write_influx: bool = False):
    """更新連線狀態與使用量。

    Args:
        write_influx: True 時才將使用量寫入 InfluxDB monitoring bucket。
    """
    ...
```

- 單行 docstring：同一行開關引號
- 多行 docstring：首行摘要，空行後接 `Args:` / `Returns:` / `Raises:`
- **不可**省略 docstring（至少一行中文說明）

---

## 錯誤處理

```python
# ✅ 明確捕捉並記錄，不吞掉 exception
try:
    data_list = r.xrevrange(key, max="+", min="-", count=1)
except Exception as e:
    print(f"Redis scan error: {e}")
    return []

# ❌ 空 except，吞掉錯誤
try:
    ...
except:
    pass
```

- 使用 `except Exception as e`，**不可**裸寫 `except:`
- 捕捉後**必須** `print` 或 log 錯誤訊息
- 區域性錯誤就地處理後回傳安全預設值（`[]`、`{}`、`False`）
- 不在底層函式 `raise`，改在上層決策點處理

---

## Print / Logging 慣例

本專案以 `print()` 作為運營日誌輸出，格式統一：

```python
# 前綴 >>> 區別系統輸出與業務輸出
print(">>> Shioaji Login Called")
print(f">>> API Key detected: {SHIOAJI_API_KEY[:4]}****")

# 加 [來源標籤] 說明觸發位置
print(f">>> [Monitor] Quota = 0, executing logout()...")
print(f">>> [Manual] Reconnect requested.")
print(f">>> [Schedule] Executing usage check (write InfluxDB).")
print(f">>> [Check] bytes={usage.bytes}, remaining_bytes={usage.remaining_bytes}")
```

| 標籤 | 用途 |
|---|---|
| `>>>` | 一般流程訊息 |
| `>>> [Monitor]` | 流量監控與連線狀態 |
| `>>> [Manual]` | 使用者手動觸發 |
| `>>> [Schedule]` | 排程任務觸發 |
| `>>> [Check]` | 狀態確認輸出 |
| `>>> ERROR:` | 錯誤訊息（大寫強調） |

> 敏感資料（API Key）只印前 4 碼，其餘以 `****` 遮蔽：`{key[:4]}****`

---

## 模組層級常數

- 統一置於 import 之後、函式定義之前
- 相關常數分組並加上註解說明用途：

```python
# Stream key prefix patterns
FOP_PREFIX = f"{REDIS_STREAM_KEY}:fop:"
STK_PREFIX = f"{REDIS_STREAM_KEY}:stk:"

# Supported timeframes for historical candle fetch (seconds)
SUPPORTED_HISTORY_TF = {60, 300, 3600}
```

---

## 程式碼格式

- **縮排**：4 個空格，不使用 Tab
- **行長**：最長 100 字元（含型別標注時可延伸至 120）
- **空行**：函式間空 2 行，函式內邏輯段落空 1 行
- **字串**：優先使用雙引號 `"`；f-string 中需嵌套時用單引號 `'`
- **尾隨逗號**：多行參數或 dict 最後一項加逗號：

```python
return redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=decode_responses,   # ← 尾隨逗號
)
```

---

## 禁止事項

- **不可**使用 `from X import *`，破壞命名空間可見性
- **不可**裸寫 `except:` 或空的 `except Exception: pass`
- **不可**在函式中直接讀取 `os.getenv()`，必須透過 `app.config` 引入
- **不可**硬寫敏感資料（Token、Key、密碼）於程式碼中
- **不可**省略公開函式的型別標注與 docstring

---

## 檢查清單（新增 / 修改 Python 檔案時）

- [ ] 函式、變數、常數命名符合對應風格
- [ ] Import 分三區塊並依字母排序
- [ ] 所有公開函式有型別標注與 docstring
- [ ] `except` 明確指定例外類型並輸出錯誤訊息
- [ ] Print 輸出含 `>>>` 前綴與適當 `[標籤]`
- [ ] 無硬寫敏感資料，敏感值透過 `app.config` 引入
