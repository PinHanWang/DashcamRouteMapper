# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案簡介

DashcamRouteMapper 從行車記錄器影片提取嵌入式 GPS 資料，輸出 GeoJSON 及 CSV。支援標準行車記錄器 MP4（GPS 嵌入 EXIF）以及 GPX 軌跡處理。

## 實際程式架構

```
src/module/DashcamRouteMapper/
├── __init__.py
├── config.py            # 集中設定：EXIFTOOL_PATH、DEFAULT_FPS、預設路徑
├── main.py              # 批次處理入口（argparse CLI）
├── video2geojson.py     # 核心轉換：Video2GeoJson 類別
└── utils/
    ├── __init__.py
    ├── exif.py          # exiftool 呼叫、EXIF GPS 資料解析
    ├── gps_processor.py # GPX 讀取、線性插值、Folium 視覺化
    └── json2csv.py      # GeoJSON → CSV（含 EPSG:3857 座標轉換）
```

## 外部工具相依

- **`exiftool`**：提取 MP4 GPS 軌跡。`config.py` 自動偵測 PATH，fallback 至 `C:\Program Files\ExifTool\exiftool.exe`

## Python 套件

```
gpxpy, folium, geopy, geojson, pandas, pyproj, scipy, numpy, tqdm
```

安裝：
```bash
pip install -r requirements.txt
```

## 執行方式

**批次處理（從專案根目錄執行）**：
```bash
# 使用預設路徑
python -m src.module.DashcamRouteMapper.main

# 指定路徑
python -m src.module.DashcamRouteMapper.main --input M:/DCIM/Movie --output E:/output

# 查看所有選項
python -m src.module.DashcamRouteMapper.main --help
```

**GPX 視覺化**：
```bash
python -m src.module.DashcamRouteMapper.utils.gps_processor [gpx_file]
```

**GeoJSON 轉 CSV**：
```bash
python -m src.module.DashcamRouteMapper.utils.json2csv [input_folder] [output_folder]
```

## 座標系統

- 原始 GPS：**WGS84（EPSG:4326）**，`(lon, lat)` 順序存入 GeoJSON
- CSV 輸出：新增 **Web Mercator（EPSG:3857）** 欄位 `lon3857`、`lat3857`

## GeoJSON 輸出結構

每個影片對應一個 `.geojson`，包含：
- 1 個 `LineString` Feature（properties：`filename`、`starttime`、`endtime`、`length(m)`）
- N 個 `Point` Features（properties：`datetime`、`timestamp`、`speed`、`azimuth`）

## 設定修改

請修改 `config.py`，不要在各模組中硬編碼：
- `EXIFTOOL_PATH`：exiftool 執行檔路徑
- `DEFAULT_FPS`：FPS fallback 值（目前 30）
- `DEFAULT_INPUT_DIR` / `DEFAULT_OUTPUT_DIR`：預設路徑

## 資料目錄

- `data/raw/`：輸入影片（git 忽略）
- `output/`：輸出結果（git 忽略）
- `history/`：合併後的 GeoJSON 歷史存檔（已納入版控）
