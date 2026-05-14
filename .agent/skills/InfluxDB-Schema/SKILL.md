---
name: "InfluxDB Schema & 查詢規範"
description: "InfluxDB 的通用操作模式：Point 寫入、Flux 查詢結構與各步驟說明。"
---

# InfluxDB Schema & 查詢規範

## 概述

InfluxDB 是時序資料庫，資料以 **Measurement + Tags + Fields + Timestamp** 組成一筆 Point。專案特定的 Bucket 設計、Measurement Schema 與 Timeframe 對照表，定義於各專案專屬 Skill 中。

---

## Point 寫入

```python
from influxdb_client import Point
from influxdb_client.client.write_api import SYNCHRONOUS
from app.services.influx_client import get_write_api

write_api = get_write_api()  # 使用 SYNCHRONOUS 模式

point = (
    Point("measurement_name")   # Measurement（類似資料表名）
    .tag("tag_key", "tag_val")  # Tag：用於過濾與分組，值為字串，建立索引
    .field("field_key", 1.23)   # Field：實際儲存的數值，不建索引
    # .time(...)                # 省略則自動使用寫入當下時間
)
write_api.write(bucket="bucket_name", record=point)
```

**型別規則**：同一個 Field 在所有寫入批次中型別必須一致（`float` vs `int` 不可混用），否則 InfluxDB 拒絕寫入。

---

## Flux 查詢結構

### 基本查詢範本

```python
from app.services.influx_client import get_query_api

query_api = get_query_api()

query = '''
    from(bucket: "bucket_name")
      |> range(start: -7d)
      |> filter(fn: (r) => r._measurement == "measurement_name")
      |> filter(fn: (r) => r.tag_key == "tag_val")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> tail(n: 100)
'''

tables = query_api.query(query)
for table in tables:
    for record in table.records:
        ts    = int(record.get_time().timestamp())
        value = record.values.get("field_key")
```

### 各步驟說明

| 步驟 | 用途 | 注意事項 |
|---|---|---|
| `range(start: ...)` | 限定查詢時間範圍 | 必須放在最前面，缺少會全表掃描 |
| `filter(_measurement)` | 指定 Measurement | **必須**先過濾，避免掃描整個 bucket |
| `filter(tag)` | 依 Tag 縮小範圍 | 可串接多個 `filter`，OR 條件用 `or` 連接 |
| `pivot(...)` | 將 `_field` 欄轉為獨立欄位 | 讓多個 field 在同一 row 可同時存取 |
| `tail(n: N)` | 只取最後 N 筆 | 取最新資料用；取最舊用 `first(n: N)` |

---

## 常見注意事項

- `filter(_measurement)` **不可省略**，直接只過濾 Tag 會導致全 bucket 掃描，效能極差。
- Tag 值為**字串索引**，適合放低基數（cardinality）的分類值（如 interval、market）；高基數值（如時間戳）放 Field。
- `INFLUXDB_TOKEN` 不可硬寫於程式碼，須透過 `.env` → `app.config` 引入。
