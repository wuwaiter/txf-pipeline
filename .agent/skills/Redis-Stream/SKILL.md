---
name: "Redis Stream 操作規範"
description: "Redis Stream 的通用操作模式：xadd 寫入、xrange/xrevrange 讀取、Key 掃描過濾與 decode_responses 選擇。"
---

# Redis Stream 操作規範

## 概述

Redis Stream 是一種僅附加（append-only）的日誌型資料結構，適合作為事件佇列或時序資料通道。本專案透過 `src/app/services/redis_client.py` 的 `get_redis_client()` 取得連線。

> 本專案的 Key 命名規則、Stream 資料結構與指令集，定義於 `txf-architecture/SKILL.md` 的「Redis 資料層規範」章節。

---

## 基本操作

### 寫入事件（xadd）

```python
r.xadd("stream:key", {"field1": "value1", "field2": "value2"})
```

- 自動產生遞增 ID（`<ms>-<seq>`），無需手動指定。
- 欄位值須為**字串**，讀取後依需要自行轉型。

### 讀取最新一筆（xrevrange）

```python
data_list = r.xrevrange("stream:key", max="+", min="-", count=1)
if data_list:
    entry_id, data = data_list[0]
    value = float(data["field1"])
```

### 讀取指定時間範圍（xrange）

```python
# min 以毫秒為單位，格式為 "<ms>-0"
start_ms = int(start_timestamp * 1000)
entries = r.xrange("stream:key", min=f"{start_ms}-0", max="+")
for entry_id, data in entries:
    ...
```

### 掃描多個 Stream Keys

掃描後**務必過濾**非 Stream 的 Key（String 類型的控制 Key 等），避免型別錯誤：

```python
all_keys = r.keys("prefix:*")
for key in all_keys:
    if key.startswith("prefix:stream-type:"):
        # 只處理 Stream 類型的 key
        ...
    else:
        continue
```

---

## decode_responses 選擇

| 值 | 回傳型別 | 適用場景 |
|---|---|---|
| `True` | `str` | 一般讀寫，直接使用字串，無需手動 decode |
| `False` | `bytes` | 需要比對 bytes prefix、效能敏感的批次處理 |

```python
# 一般用途（優先選擇）
r = get_redis_client(decode_responses=True)

# Celery Worker 等批次處理
r = get_redis_client(decode_responses=False)
key_prefix = b"prefix:stream-type:"
if b_key.startswith(key_prefix):
    ...
```

---

## 常見注意事項

- `xadd` 的欄位值只能是字串，數字須先轉 `str()`，讀取後再轉回 `float()` / `int()`。
- `xrange` / `xrevrange` 的時間邊界使用**毫秒**級 ID（`<ms>-<seq>`），而非秒。
- 使用 `r.keys(pattern)` 掃描時，production 環境資料量大建議改用 `r.scan_iter(pattern)` 避免阻塞。
