# Module Refactor Design: trajectory + uploader

**Date:** 2026-03-27
**Status:** Approved

---

## 背景

目前 `src/module/` 下有三個目錄：

- `DashcamRouteMapper/` — 功能完整的軌跡生成模組
- `Uploadtest/dawarich_uploader.py` — 上傳工具，有 API key 硬編碼等問題
- `DashcamRouteProcessor/main.py` — 舊版殘留，有 import 錯誤，已無用

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

---

## 模組職責

### `trajectory/`

從行車記錄器 MP4 提取 GPS 軌跡，輸出 GeoJSON 及 CSV。

- 輸入：影片目錄（`.mp4` / `.mov` / `.avi`）
- 輸出：每部影片一個 `.geojson`，合併後輸出至 `merged/` 子目錄
- 不依賴 `uploader/`，可完全獨立使用

### `uploader/`

將 GeoJSON 軌跡上傳至 Dawarich。

- 輸入：GeoJSON 檔案路徑（支援 FeatureCollection、OwnTracks、Google Takeout 格式）
- 輸出：批次 HTTP POST 至 Dawarich Overland API
- 設定由 `.env` 提供，不在程式碼中硬編碼

---

## Pipeline 串接

`trajectory/main.py` 加入選用旗標 `--upload`，生成軌跡後自動呼叫 uploader：

```bash
# 只生成軌跡（預設）
python -m src.module.trajectory.main --input M:/DCIM --output E:/output

# 生成後自動上傳
python -m src.module.trajectory.main --input M:/DCIM --output E:/output --upload

# 單獨上傳既有 GeoJSON
python -m src.module.uploader.main --input E:/output/merged/20260327.geojson
```

上傳邏輯：找到 `output_dir/merged/` 下最新的 `.geojson` 檔案後呼叫 `uploader`。

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

同上，但 value 填入說明文字。

### `uploader/config.py`

```python
from dotenv import load_dotenv
import os

load_dotenv()

DAWARICH_URL = os.environ["DAWARICH_URL"]          # 必填，未設定直接報錯
DAWARICH_API_KEY = os.environ["DAWARICH_API_KEY"]  # 必填
BATCH_SIZE = int(os.environ.get("DAWARICH_BATCH_SIZE", "100"))
REQUEST_TIMEOUT = int(os.environ.get("DAWARICH_REQUEST_TIMEOUT", "30"))
```

---

## 修正清單

| 問題 | 位置 | 處理方式 |
|------|------|---------|
| 舊版殘留，import 錯誤 | `DashcamRouteProcessor/main.py` | 刪除整個目錄 |
| API Key 硬編碼 | `Uploadtest/dawarich_uploader.py` | 移至 `.env` |
| `datetime.utcnow()` Python 3.12 棄用 | `Uploadtest/dawarich_uploader.py` | 改為 `datetime.now(timezone.utc)` |
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
