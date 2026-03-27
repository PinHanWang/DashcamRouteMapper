# Module Refactor Design: trajectory + uploader

**Date:** 2026-03-27
**Status:** Approved

---

## 背景

目前 `src/module/` 下有三個目錄：

- `DashcamRouteMapper/` — 功能完整的軌跡生成模組
- `Uploadtest/dawarich_uploader.py` — 上傳工具，有 API key 硬編碼等問題
- `DashcamRouteProcessor/main.py` — 舊版殘留，有 import 錯誤，已無用

另有 `backup_download/data_check.py` 與 `download.py` 已在 git 中被標記為刪除（`D` 狀態），本次重構會一併 `git rm` 確認移除。

目標是將程式碼整理為兩個職責清晰的子模組，並修正已知問題。

---

## 架構設計

### 目錄結構

```
src/module/
├── trajectory/                    # 軌跡生成模組
│   ├── __init__.py
│   ├── config.py                  # EXIFTOOL_PATH、DEFAULT_FPS、預設路徑
│   ├── main.py                    # CLI 入口（ThreadPoolExecutor 平行處理）
│   ├── video2geojson.py           # 核心轉換：Video2GeoJson 類別
│   └── utils/
│       ├── __init__.py
│       ├── exif.py                # exiftool 呼叫與 GPS EXIF 解析
│       ├── geo.py                 # 座標轉換、Haversine 距離
│       ├── gps_processor.py       # GPX 讀取、插值、Folium 視覺化
│       └── json2csv.py            # GeoJSON → CSV
│
└── uploader/                      # 上傳模組
    ├── __init__.py
    ├── config.py                  # 從 .env 讀取 DAWARICH_URL、DAWARICH_API_KEY
    ├── client.py                  # DawarichUploader 類別（HTTP 批次上傳）
    ├── parser.py                  # GeoJSON/OwnTracks/Google Takeout 解析、座標驗證
    └── main.py                    # 獨立 CLI 入口

.env                               # 敏感設定（.gitignore 忽略）
.env.sample                        # 設定範本（納入版控）
```

**兩模組完全獨立**：`uploader/` 不 import `trajectory/` 的任何程式碼，`trajectory/` 也不依賴 `uploader/`（pipeline 在 `trajectory/main.py` 中以 `try/except ImportError` 動態 import）。

---

## 模組職責

### `trajectory/`

從行車記錄器 MP4 提取 GPS 軌跡，輸出 GeoJSON 及 CSV。

- 輸入：影片目錄（`.mp4` / `.mov` / `.avi`）
- 輸出：每部影片一個 `.geojson`，合併後輸出至 `merged/` 子目錄
- CLI 參數（保持現有介面不變）：
  - `--input / -i`：影片目錄
  - `--output / -o`：輸出目錄
  - `--type / -t`：`all` | `point` | `line`（預設 `point`）
  - `--workers / -w`：執行緒數量（預設 4）
  - `--upload`：（新增）生成後自動上傳，選用旗標

### `uploader/`

將 GeoJSON 軌跡上傳至 Dawarich。

- 輸入：GeoJSON 檔案路徑（支援 FeatureCollection、OwnTracks、Google Takeout 格式）
- 輸出：批次 HTTP POST 至 Dawarich Overland API
- 設定由 `.env` 提供，不在程式碼中硬編碼
- CLI 參數（`uploader/main.py`）：
  - `--input / -i`：GeoJSON 檔案路徑（必要）
  - `--batch-size`：每批點數（預設讀自 `.env`，fallback 100）
  - `--timeout`：超時秒數（預設讀自 `.env`，fallback 30）
  - `--no-sort`：跳過依時間排序
  - `--no-validate`：跳過座標驗證

---

## Pipeline 串接

### 呼叫流程（`--upload` 啟用時）

```
trajectory/main.py
  └─ DashcamRouteProcessor.process()
       └─ merge_all_geojson() → 產生 output_dir/merged/<timestamp>.geojson
            └─（若 --upload）_run_upload(merged_path)
                 └─ 動態 import uploader.client.DawarichUploader
                      └─ upload_trajectory(points)
```

**`_run_upload` 的錯誤處理：**
1. `try: from src.module.uploader.client import DawarichUploader` — 若 `python-dotenv` 未安裝或 `.env` 不存在，捕捉 `ImportError` / `KeyError` 並給出可讀錯誤訊息（例如「請確認已安裝 python-dotenv 並建立 .env 檔案」）
2. `uploader/config.py` 中必填的 `DAWARICH_URL` / `DAWARICH_API_KEY` 若未設定，以 `KeyError` 報錯，並在 `_run_upload` 中轉為友善訊息

### CLI 使用方式

```bash
# 只生成軌跡（預設）
python -m src.module.trajectory.main --input M:/DCIM --output E:/output

# 生成後自動上傳
python -m src.module.trajectory.main --input M:/DCIM --output E:/output --upload

# 單獨上傳既有 GeoJSON
python -m src.module.uploader.main --input E:/output/merged/20260327.geojson
```

---

## GeoJSON 欄位相容性

`trajectory/` 輸出的 Point feature properties：

```json
{
  "datetime": "2026-03-27T10:30:00Z",
  "timestamp": 1743072600,
  "speed": 50.0,
  "azimuth": 180.0
}
```

`uploader/parser.py` 解析 GeoJSON FeatureCollection 時，timestamp 欄位讀取順序為 `props.get('time', props.get('timestamp', ''))`，能正確識別 `timestamp` 欄位。**`trajectory/` 產出格式與 `parser.py` Format 1 相容，無需額外轉換。**

---

## 設定管理

### `.env`（加入 `.gitignore`）

```dotenv
DAWARICH_URL=http://192.168.61.2:3000
DAWARICH_API_KEY=your_api_key_here
DAWARICH_BATCH_SIZE=100
DAWARICH_REQUEST_TIMEOUT=30
```

### `.env.sample`（納入版控）

```dotenv
# Dawarich 服務 URL
DAWARICH_URL=http://your-dawarich-host:3000

# 從 Dawarich Settings 頁面取得的 API Key
DAWARICH_API_KEY=your_api_key_here

# 每批次上傳點數（建議 50-200）
DAWARICH_BATCH_SIZE=100

# API 請求超時時間（秒）
DAWARICH_REQUEST_TIMEOUT=30
```

### `uploader/config.py`

```python
from dotenv import load_dotenv
import os

# 依賴從專案根目錄執行（python -m src.module...），load_dotenv() 不帶路徑
load_dotenv()

DAWARICH_URL = os.environ["DAWARICH_URL"]          # 必填，未設定拋 KeyError
DAWARICH_API_KEY = os.environ["DAWARICH_API_KEY"]  # 必填
BATCH_SIZE = int(os.environ.get("DAWARICH_BATCH_SIZE", "100"))
REQUEST_TIMEOUT = int(os.environ.get("DAWARICH_REQUEST_TIMEOUT", "30"))
```

---

## `DawarichUploader` Session 生命週期

`client.py` 中的 `DawarichUploader` 實作 `__enter__` / `__exit__`，作為 context manager 使用：

```python
with DawarichUploader(config) as uploader:
    uploader.upload_trajectory(points)
# session.close() 在 __exit__ 中自動呼叫
```

---

## `uploader/` 的 Haversine 實作

`uploader/parser.py` 的 `calculate_distance()` 保留獨立的 Haversine 實作（不 import `trajectory/utils/geo.py`），維持兩模組完全解耦。

---

## 修正清單

| 問題 | 位置 | 處理方式 |
|------|------|---------|
| 舊版殘留，import 錯誤 | `DashcamRouteProcessor/` 整個目錄 | 刪除 |
| 已刪除但未確認的檔案 | `backup_download/data_check.py`、`download.py` | `git rm` 確認 |
| API Key 硬編碼 | `Uploadtest/dawarich_uploader.py` | 移至 `.env` |
| `datetime.utcnow()` / `utcfromtimestamp()` Python 3.12 棄用（共 6 處） | `Uploadtest/dawarich_uploader.py` | 全部改為 `datetime.now(timezone.utc)` / `datetime.fromtimestamp(..., tz=timezone.utc)` |
| `_calculate_distance` dead code | `video2geojson.py:136` | 刪除 |
| `_get_exif_start_time` 在 `df.empty` 前呼叫 | `exif.py:129` | 移至 `df.empty` 檢查之後 |

---

## 相依套件變更

新增 `python-dotenv` 至 `requirements.txt`。

---

## 不在本次範圍內

- GPX 視覺化（`gps_processor.py`）功能不變，直接搬移
- Dawarich API 版本升級
- 新增測試
