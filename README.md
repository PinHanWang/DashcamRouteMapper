# DashcamRouteMapper - 行車記錄器路線繪製工具

## 專案概述

DashcamRouteMapper 從行車記錄器影片提取嵌入式 GPS 資料，輸出 GeoJSON 及 CSV 格式，可供 QGIS、Leaflet、Folium 等工具視覺化，並可選擇性上傳至 [Dawarich](https://dawarich.app) 地理軌跡平台。

## 主要功能

- **GPS 軌跡提取**：透過 exiftool 從 MP4 EXIF/metadata 提取 GPS 資訊
- **格式轉換**：輸出 GeoJSON（LineString + Point）及 CSV
- **平行批次處理**：ThreadPoolExecutor 多 worker 同時處理多支影片，大幅縮短整體時間
- **GPX 支援**：讀取、插值 GPX 軌跡並視覺化（PolyLine + FastMarkerCluster）
- **Dawarich 上傳**：可直接上傳至 Dawarich，支援 GeoJSON、OwnTracks、Google Takeout 等多種格式

## 專案架構

```
DashcamRouteMapper/
├── src/module/
│   ├── trajectory/                  # 軌跡生成模組
│   │   ├── config.py                # 集中設定（exiftool 路徑、FPS、預設路徑）
│   │   ├── main.py                  # 批次處理入口（含 --upload 旗標）
│   │   ├── video2geojson.py         # 影片 → GeoJSON 核心轉換
│   │   └── utils/
│   │       ├── exif.py              # EXIF GPS 資料提取（subprocess）
│   │       ├── geo.py               # 共用地理工具：座標轉換、Haversine 距離
│   │       ├── gps_processor.py     # GPX 讀取、插值、視覺化
│   │       └── json2csv.py          # GeoJSON → CSV（含 EPSG:3857 轉換）
│   └── uploader/                    # Dawarich 上傳模組
│       ├── config.py                # 從 .env 讀取連線設定
│       ├── parser.py                # 多格式解析、座標驗證、軌跡分析
│       ├── client.py                # DawarichUploader（context manager）
│       └── main.py                  # 獨立 CLI 入口
├── docs/
│   └── cli-usage.md                 # 完整 CLI 使用說明
├── data/raw/                        # 輸入影片（git 忽略）
├── output/                          # 輸出結果（git 忽略）
├── history/                         # 合併後 GeoJSON 歷史（已版控）
├── .env.sample                      # 上傳設定範本
└── requirements.txt
```

## 環境需求

- Python 3.10+
- **exiftool**：需安裝在系統 PATH，或在 `trajectory/config.py` 設定路徑

```bash
pip install -r requirements.txt
```

## 快速開始

### 1. 軌跡生成

```bash
# 使用預設路徑（data/raw/ → output/）
python -m src.module.trajectory.main

# 指定路徑、類型、平行 worker 數
python -m src.module.trajectory.main \
    --input M:/DCIM/Movie \
    --output E:/output \
    --type point \
    --workers 4
```

| 參數 | 縮寫 | 預設值 | 說明 |
|------|------|--------|------|
| `--input` | `-i` | `data/raw/` | 輸入影片資料夾（遞迴掃描） |
| `--output` | `-o` | `output/` | GeoJSON 輸出資料夾 |
| `--type` | `-t` | `point` | Feature 類型：`all`、`point`、`line` |
| `--workers` | `-w` | `4` | 平行 thread 數 |
| `--upload` | — | `False` | 生成後自動上傳至 Dawarich |

### 2. 上傳至 Dawarich（選用）

複製並填寫 `.env`：

```bash
copy .env.sample .env
# 編輯 .env，填入 DAWARICH_URL 與 DAWARICH_API_KEY
```

```bash
# 方式一：生成時一併上傳
python -m src.module.trajectory.main --input M:/DCIM/Movie --output E:/output --upload

# 方式二：獨立上傳既有 GeoJSON
python -m src.module.uploader.main --input E:/output/merged/20260327_103045.geojson
```

> 詳細說明見 [`docs/cli-usage.md`](docs/cli-usage.md)

## Python API

### 批次處理

```python
from pathlib import Path
from src.module.trajectory.main import DashcamRouteProcessor

processor = DashcamRouteProcessor()
processor.process(
    video_dir=Path("data/raw/20260327"),
    output_dir=Path("output/20260327"),
    feature_type="point",   # 'all' | 'point' | 'line'
    max_workers=4,
    upload=False,           # True 時自動上傳至 Dawarich
)
```

### 單一影片轉換

```python
from pathlib import Path
from src.module.trajectory.video2geojson import Video2GeoJson

converter = Video2GeoJson(Path("video.MP4"))
converter.save_geojson(Path("output"), feature_type="all")
stats = converter._get_stats()
print(stats)
```

### GeoJSON → CSV

```python
from pathlib import Path
from src.module.trajectory.utils.json2csv import json_to_csv_with_fields

json_to_csv_with_fields(
    input_folder=Path("output/20260327"),
    output_folder=Path("output/20260327"),
    fps=30,  # 選填，預設讀自 config.DEFAULT_FPS
)
```

### GPX 視覺化

```python
from src.module.trajectory.utils.gps_processor import GPXProcessor

processor = GPXProcessor("data/raw/insta360/Guilin_Rd.gpx")
interpolated = processor.interpolate_gpx(frequency=3)
processor.draw_tracking(interpolated, "output/tracking.html")
```

### Dawarich 上傳

```python
import json
from src.module.uploader.parser import parse_json_format, validate_coordinates, sort_by_timestamp
from src.module.uploader.client import DawarichUploader

with open("output/merged/20260327_103045.geojson") as f:
    data = json.load(f)

points = sort_by_timestamp(validate_coordinates(parse_json_format(data)))

config = {
    "DAWARICH_URL": "http://192.168.61.2:3000",
    "API_KEY": "your_api_key",
    "BATCH_SIZE": 100,
    "REQUEST_TIMEOUT": 30,
}
with DawarichUploader(config) as uploader:
    uploader.upload_trajectory(points)
```

## 效能特性

| 項目 | 實作方式 | 效益 |
|------|----------|------|
| 批次影片轉換 | `ThreadPoolExecutor`（多 worker） | 多支影片時速度近線性提升 |
| GPS 點距離計算 | 向量化 Haversine（numpy） | 比逐點 `geopy.geodesic` 快約 50x |
| Point Feature 建立 | `zip` 迭代 Series（取代 `iterrows`） | 省去 pandas 每列 Series 物件開銷 |
| 座標轉換 | 單一 `Transformer` 實例（`utils/geo.py`） | 避免多模組重複初始化 pyproj |
| Folium 地圖 | `PolyLine` + `FastMarkerCluster` | HTML 大幅縮小，瀏覽器渲染流暢 |
| 上傳 session 管理 | `DawarichUploader` context manager | 確保 HTTP session 正確關閉 |

## GeoJSON 輸出結構

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "LineString", "coordinates": [[lon, lat], "..."] },
      "properties": {
        "filename": "VIDEO001",
        "starttime": "2026-03-27T10:00:00",
        "endtime": "2026-03-27T10:30:00",
        "length(m)": 5000.0
      }
    },
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [lon, lat] },
      "properties": {
        "datetime": "2026-03-27T10:00:00Z",
        "timestamp": 1743069600,
        "speed": 30.5,
        "azimuth": 90.0
      }
    }
  ]
}
```

## 授權

TMS 內部專案
