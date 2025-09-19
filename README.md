# DashcamRouteMapper

## 專案概述

DashcamRouteMapper 是一個專為行車紀錄器GPS軌跡處理設計的Python工具套件。本專案能夠從行車紀錄器影片中提取GPS軌跡資訊，並將其轉換為標準的GeoJSON格式，支援軌跡視覺化、數據分析和地理空間應用。

## 主要功能

- **GPS軌跡提取**：從行車紀錄器影片的EXIF資料中提取GPS位置資訊
- **格式轉換**：支援轉換為GeoJSON、CSV等多種格式
- **批量處理**：可同時處理多個影片文件
- **數據輸出**：輸出標準GeoJSON格式供第三方工具視覺化
- **GPX支援**：支援讀取和處理GPX格式的軌跡文件

## 專案架構

```
DashcamRouteMapper/
├── src/
│   └── module/
│       ├── DashcamRouteProcessor/
│       │   ├── main.py                    # 主要處理流程
│       │   └── Video2Geojson.py          # 影片轉GeoJSON核心類
│       └── utils/
│           ├── gjsonfilter.py            # GeoJSON過濾工具
│           ├── GPSProcessor.py           # GPX處理工具
│           ├── json2csv.py               # JSON轉CSV工具
│           └── makeExif.py               # EXIF GPS資料提取
├── data/                                 # 原始資料目錄
├── output/                              # 輸出結果目錄
└── README.md
```

## 核心模組介紹

### 🎥 DashcamRouteProcessor - 主要處理模組

**核心功能：**
- 自動掃描目錄中的影片文件（支援MP4、MOV、AVI格式）
- 批量提取GPS軌跡並轉換為GeoJSON格式
- 自動合併多個軌跡文件為單一GeoJSON
- 支援點位（Point）和軌跡線（LineString）兩種幾何類型

**主要類別：**
- `DashcamRouteProcessor` - 批量處理管理器
- `Video2GeoJson` - 影片GPS資料轉換核心

### 🛠️ Utils - 工具模組

**makeExif.py** - EXIF GPS資料提取：
- 從影片EXIF中提取完整GPS軌跡
- 計算影片開始時間和幀率
- 支援座標系統轉換（WGS84 to EPSG:3857）

**gjsonfilter.py** - GeoJSON過濾工具：
- 過濾特定幾何類型（Point/LineString）
- 時間戳格式轉換
- 批量處理多個GeoJSON文件

**gjsonfilter.py** - GeoJSON過濾工具：
- 過濾特定幾何類型（Point/LineString）
- 時間戳格式轉換
- 批量處理多個GeoJSON文件

**GPSProcessor.py** - GPX軌跡處理：
- 讀取和解析GPX文件
- 軌跡插值功能
- 基礎軌跡數據處理（視覺化功能待開發）

**json2csv.py** - 格式轉換：
- GeoJSON轉CSV格式
- 座標系統轉換
- 添加時間和幀數資訊

## 環境需求

### 系統需求
- Python 3.8+
- ExifTool（需額外安裝）

### Python套件依賴
```bash
pip install -r requirements.txt
```

### ExifTool安裝

**Windows:**
1. 下載 ExifTool 從 https://exiftool.org/
2. 解壓縮並將執行檔加入系統PATH

**macOS:**
```bash
brew install exiftool
```

**Ubuntu/Debian:**
```bash
sudo apt install libimage-exiftool-perl
```

## 安裝與設定

1. **克隆專案**
```bash
git clone <repository-url>
cd DashcamRouteMapper
```

2. **安裝Python依賴**
```bash
pip install -r requirements.txt
```

3. **安裝ExifTool**
按照上述系統對應的方式安裝ExifTool

4. **驗證安裝**
```bash
exiftool -ver
```

## 使用指南

### 基本使用流程

#### 1. 批量處理行車紀錄器影片

```python
from pathlib import Path
from DashcamRouteProcessor.main import DashcamRouteProcessor

# 設定輸入和輸出目錄
video_dir = Path("H:/DCIM/Movie")
output_dir = Path("H:/DCIM/Movie/gjson")

# 初始化處理器
processor = DashcamRouteProcessor()

# 執行批量處理
processor.process(video_dir, output_dir, feature_type="all")
```

#### 2. 單一影片處理

```python
from pathlib import Path
from Video2Geojson import Video2GeoJson

# 處理單一影片
video_path = Path("path/to/your/video.MP4")
video2geojson = Video2GeoJson(video_path)

# 保存為GeoJSON
output_dir = Path("output")
video2geojson.save_geojson(output_dir, feature_type="all")

# 獲取軌跡統計資訊
stats = video2geojson._get_stats()
print(stats)
```

#### 3. 格式轉換工具

```python
from utils.json2csv import json_to_csv_with_fields
from pathlib import Path

# 將GeoJSON轉換為CSV格式
input_folder = Path("output/geojson")
output_folder = Path("output/csv") 
json_to_csv_with_fields(input_folder, output_folder)
```

#### 4. GPX軌跡處理

```python
from utils.GPSProcessor import GPXProcessor

# 讀取GPX文件
gpx_processor = GPXProcessor("track.gpx")

# 軌跡插值（每秒2個點）
interpolated_points = gpx_processor.interpolate_gpx(frequency=2)

# 獲取原始軌跡點
original_points = gpx_processor.track_pts
print(f"原始軌跡點數量: {len(original_points)}")
print(f"插值後軌跡點數量: {len(interpolated_points)}")
```

### 支援的功能類型

**feature_type 參數選項：**
- `"all"` - 包含點位和軌跡線
- `"point"` - 僅輸出GPS點位
- `"line"` - 僅輸出軌跡線

### 輸出格式

**GeoJSON 結構：**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": [[lon, lat], ...]
      },
      "properties": {
        "filename": "video_name",
        "starttime": "2025-01-01T10:00:00",
        "endtime": "2025-01-01T10:30:00",
        "length(m)": 5000.0
      }
    },
    {
      "type": "Feature", 
      "geometry": {
        "type": "Point",
        "coordinates": [lon, lat]
      },
      "properties": {
        "timestamp": 1640995200
      }
    }
  ]
}
```

## 工具使用範例

### 命令列使用

```bash
# 處理單一影片
python Video2Geojson.py

# 批量處理目錄
python main.py

# 轉換為CSV格式
python json2csv.py
```

### 程式碼整合

```python
# 完整處理流程範例
from pathlib import Path
from DashcamRouteProcessor.main import DashcamRouteProcessor
from utils.json2csv import json_to_csv_with_fields

# 1. 影片轉GeoJSON
video_dir = Path("raw_videos")
geojson_dir = Path("output/geojson")
processor = DashcamRouteProcessor()
processor.process(video_dir, geojson_dir)

# 2. 轉換為CSV格式
csv_dir = Path("output/csv")
json_to_csv_with_fields(geojson_dir, csv_dir)
```

## 注意事項

1. **ExifTool依賴**：確保系統已正確安裝ExifTool並可在命令列中執行
2. **GPS資料要求**：影片文件必須包含GPS資訊才能處理
3. **文件格式**：支援包含GPS metadata的MP4、MOV、AVI格式
4. **處理時間**：大型影片文件處理可能需要較長時間
5. **座標系統**：默認輸出WGS84座標，支援轉換為其他座標系統

## 錯誤處理

- 自動跳過無GPS資料的影片文件
- 處理異常時會顯示詳細錯誤訊息
- 支援部分失敗的批量處理模式

## 輸出數據應用

生成的GeoJSON和CSV文件可用於：
- GIS軟體分析（QGIS、ArcGIS）
- 網頁地圖應用（Leaflet、Mapbox）
- 第三方數據視覺化工具（Folium、Plotly）
- 路徑分析和統計

## 開發狀態

- ✅ **核心功能**：GPS軌跡提取和轉換
- ✅ **批量處理**：多影片文件處理
- ✅ **格式支援**：GeoJSON、CSV、GPX
- 🚧 **視覺化功能**：計劃中，目前輸出標準格式供第三方工具使用

## 貢獻指南

1. Fork 本專案
2. 創建功能分支 (`git checkout -b feature/NewFeature`)
3. 提交更改 (`git commit -m 'Add NewFeature'`)
4. 推送到分支 (`git push origin feature/NewFeature`)
5. 開啟 Pull Request

## 授權資訊

本專案採用 MIT 授權條款。

---

**技術支援：**
如有技術問題或建議，請創建 Issue 或聯絡開發團隊。