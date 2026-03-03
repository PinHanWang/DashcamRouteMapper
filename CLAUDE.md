# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案簡介

DashcamRouteMapper 從行車記錄器影片提取嵌入式 GPS 資料，輸出 GeoJSON、CSV 及 Folium 互動式 HTML 地圖。支援兩種來源：
1. **標準行車記錄器 MP4**（GPS 嵌入在影片 EXIF/metadata 中）
2. **全景相機（Insta360）**（GPS 存放於外部 `.gpx` 文件）

## 實際程式架構

> 注意：`README.md` 描述的是規劃架構，**實際程式碼**位於 `src/module/Dashcam2GeoVis/`：

```
src/module/Dashcam2GeoVis/
├── main.py                  # 批次處理入口：掃描影片資料夾 → GeoJSON → 合併
├── video2geojson.py         # 核心轉換類別
│   ├── Video2GeoJson        # 標準行車記錄器（讀取嵌入 GPS）
│   └── PanoramaVideo2GeoJson # 全景相機（讀取外部 GPX）
├── GeoVis.py                # 視覺化：GeoJSON → Folium HTML 地圖
└── utlis/
    ├── makeExif.py          # 透過 exiftool CLI 提取 EXIF GPS 資料
    ├── GPSProcessor.py      # 解析 GPX 檔、線性插值、Folium 繪圖
    └── json2csv.py          # GeoJSON → CSV（含 EPSG:3857 座標轉換）
```

## 外部工具相依

- **`exiftool`**：必須安裝在系統 PATH（`makeExif.py` 用 `os.popen` 呼叫）。用於提取 MP4 的 `VideoFrameRate`、`CreateDate`、`Duration` 及逐秒 GPS 軌跡。
- **`ffmpeg`**：影片處理需求（README 說明）

## Python 套件

```
gpxpy, folium, geopy, geojson, pandas, pyproj, scipy, numpy, tqdm
```

安裝（開發模式）：
```bash
pip install -e .
```

## 執行方式

**批次處理影片資料夾**（從 `Dashcam2GeoVis/` 目錄執行）：
```bash
cd src/module/Dashcam2GeoVis
python main.py
```
- 輸入：`data/raw/20250319/`（MP4 檔；同名 `.gpx` 存在時用全景模式）
- 輸出：`output/20250319/`（個別 `.geojson` + 合併後的時間戳記 `.geojson`）

**單一影片轉換（全景模式）**：
```bash
cd src/module/Dashcam2GeoVis
python video2geojson.py
```

**GPX 視覺化**：
```bash
cd src/module/Dashcam2GeoVis
python utlis/GPSProcessor.py
```

**GeoJSON 轉 CSV**：
```bash
cd src/module/Dashcam2GeoVis
python utlis/json2csv.py
```

**GeoJSON 轉 HTML 地圖**：
```bash
cd src/module/Dashcam2GeoVis
python GeoVis.py
```

## 座標系統

- 原始 GPS：**WGS84（EPSG:4326）**，`(lon, lat)` 順序存入 GeoJSON
- 轉換輸出：**Web Mercator（EPSG:3857）**，存為 `lon3857`、`lat3857` 欄位（CSV 輸出用）
- 使用 `pyproj.Transformer` 進行轉換

## GeoJSON 輸出結構

每個影片對應一個 `.geojson`，包含：
- 1 個 `LineString` Feature（properties：`filename`、`starttime`、`endtime`、`length(m)`）
- N 個 `Point` Features（properties：`datetime`、`speed`、`azimuth`）

## 已知問題

- [main.py:53](src/module/Dashcam2GeoVis/main.py#L53)：typo `outptut_dir`（應為 `output_dir`），會導致 `merge_all_geojson` 呼叫失敗
- `main.py` 的 import 採相對模組名稱（`from video2geojson import ...`），必須從 `Dashcam2GeoVis/` 目錄執行
- `json2csv.py` 中 FPS 硬編碼為 `60`（行 52），非從影片動態讀取

## 資料目錄

- `data/raw/`：輸入影片（git 忽略）
- `output/`：輸出結果（git 忽略）
- `history/`：合併後的 GeoJSON 歷史存檔（已納入版控）
