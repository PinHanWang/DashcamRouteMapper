# DashcamRouteMapper - 行車記錄器路線繪製工具

## 專案概述

DashcamRouteMapper 從行車記錄器影片提取嵌入式 GPS 資料，輸出 GeoJSON 及 CSV 格式，可供 QGIS、Leaflet、Folium 等工具視覺化。

## 主要功能

- **GPS 軌跡提取**：透過 exiftool 從 MP4 EXIF/metadata 提取 GPS 資訊
- **格式轉換**：輸出 GeoJSON（LineString + Point）及 CSV
- **平行批次處理**：ThreadPoolExecutor 多 worker 同時處理多支影片，大幅縮短整體時間
- **GPX 支援**：讀取、插值 GPX 軌跡並視覺化（PolyLine + FastMarkerCluster）

## 專案架構

```
DashcamRouteMapper/
├── src/
│   └── module/
│       └── DashcamRouteMapper/
│           ├── __init__.py
│           ├── config.py           # 集中設定（exiftool 路徑、FPS、預設路徑）
│           ├── main.py             # 批次處理入口（含 argparse CLI）
│           ├── video2geojson.py    # 影片 → GeoJSON 核心轉換
│           └── utils/
│               ├── exif.py         # EXIF GPS 資料提取（subprocess）
│               ├── geo.py          # 共用地理工具：座標轉換、Haversine 距離
│               ├── gps_processor.py # GPX 讀取、插值、視覺化
│               └── json2csv.py     # GeoJSON → CSV（含 EPSG:3857 轉換）
├── data/
│   └── raw/                        # 輸入影片（git 忽略）
├── output/                         # 輸出結果（git 忽略）
├── history/                        # 合併後 GeoJSON 歷史（已版控）
└── requirements.txt
```

## 環境需求

- Python 3.8+
- **exiftool**：需安裝在系統 PATH，或在 `config.py` 設定路徑

```bash
pip install -r requirements.txt
```

## 使用方式

### 批次處理（CLI）

```bash
# 使用預設路徑（data/raw/ → output/）
python -m src.module.DashcamRouteMapper.main

# 指定路徑、類型、平行 worker 數
python -m src.module.DashcamRouteMapper.main \
    --input M:/DCIM/Movie \
    --output E:/output/1015 \
    --type point \
    --workers 4

# 查看所有選項
python -m src.module.DashcamRouteMapper.main --help
```

| 參數 | 縮寫 | 預設值 | 說明 |
|------|------|--------|------|
| `--input` | `-i` | `data/raw/` | 輸入影片資料夾 |
| `--output` | `-o` | `output/` | GeoJSON 輸出資料夾 |
| `--type` | `-t` | `point` | Feature 類型：`all`、`point`、`line` |
| `--workers` | `-w` | `4` | 平行 thread 數（建議設為 CPU 核心數） |

### Python API

```python
from pathlib import Path
from src.module.DashcamRouteMapper.main import DashcamRouteProcessor

processor = DashcamRouteProcessor()
processor.process(
    video_dir=Path("data/raw/20250319"),
    output_dir=Path("output/20250319"),
    feature_type="point",   # 'all' | 'point' | 'line'
    max_workers=4,          # 平行 thread 數
)
```

### 單一影片轉換

```python
from pathlib import Path
from src.module.DashcamRouteMapper.video2geojson import Video2GeoJson

converter = Video2GeoJson(Path("video.MP4"))
converter.save_geojson(Path("output"), feature_type="all")
stats = converter._get_stats()
print(stats)
```

### GeoJSON → CSV

```python
from pathlib import Path
from src.module.DashcamRouteMapper.utils.json2csv import json_to_csv_with_fields

json_to_csv_with_fields(
    input_folder=Path("output/20250319"),
    output_folder=Path("output/20250319"),
    fps=30,  # 選填，預設讀自 config.DEFAULT_FPS
)
```

### GPX 視覺化

```python
from src.module.DashcamRouteMapper.utils.gps_processor import GPXProcessor

processor = GPXProcessor("data/raw/insta360/Guilin_Rd.gpx")
interpolated = processor.interpolate_gpx(frequency=3)
processor.draw_tracking(interpolated, "output/tracking.html")
```

## 效能特性

| 項目 | 實作方式 | 效益 |
|------|----------|------|
| 批次影片轉換 | `ThreadPoolExecutor`（多 worker） | 多支影片時速度近線性提升 |
| GPS 點距離計算 | 向量化 Haversine（numpy） | 比逐點 `geopy.geodesic` 快約 50x |
| Point Feature 建立 | `zip` 迭代 Series（取代 `iterrows`） | 省去 pandas 每列 Series 物件開銷 |
| 座標轉換 | 單一 `Transformer` 實例（`utils/geo.py`） | 避免多模組重複初始化 pyproj |
| Folium 地圖 | `PolyLine` + `FastMarkerCluster` | HTML 大幅縮小，瀏覽器渲染流暢 |

## GeoJSON 輸出結構

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "LineString", "coordinates": [[lon, lat], ...] },
      "properties": {
        "filename": "video_name",
        "starttime": "2025-01-01T10:00:00",
        "endtime": "2025-01-01T10:30:00",
        "length(m)": 5000.0
      }
    },
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [lon, lat] },
      "properties": {
        "datetime": "2025-01-01T10:00:00Z",
        "timestamp": 1640995200,
        "speed": 30.5,
        "azimuth": 90.0
      }
    }
  ]
}
```

## 授權

TMS 內部專案
