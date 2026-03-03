# DashcamRouteMapper - 行車記錄器路線繪製工具

## 專案概述

DashcamRouteMapper 是一個專為行車記錄器影片設計的 GPS 軌跡提取與路線視覺化工具。本系統能夠從行車記錄器影片的 EXIF/metadata 中提取 GPS 資訊，並在地圖上繪製完整的行車路線,主要應用於道路資料收集、路線規劃分析與行車軌跡記錄。

## 主要功能

- **📹 影片 GPS 提取**：從行車記錄器影片提取嵌入的 GPS 資訊
- **🗺️ 路線視覺化**：在互動式地圖上繪製行車路線
- **📊 軌跡分析**：計算行駛距離、時間、平均速度等統計資訊
- **🔄 格式轉換**：支援多種 GPS 資料格式 (GPX, KML, GeoJSON, CSV)
- **📸 關鍵幀提取**：提取特定 GPS 位置的影片幀
- **🎯 熱圖生成**：分析行駛熱區與頻繁路線

## 專案架構

```
DashcamRouteMapper/
├── src/                               # 原始碼
│   ├── __init__.py
│   ├── gps_extractor.py              # GPS 資訊提取
│   ├── route_mapper.py               # 路線繪製
│   ├── video_processor.py            # 影片處理
│   └── utils/                        # 工具函數
├── data/                             # 測試資料
├── output/                           # 輸出結果
├── history/                          # 歷史記錄
├── setup.py                          # 套件安裝
└── README.md
```

## 核心功能

### GPS 資訊提取

```python
from src.gps_extractor import DashcamGPSExtractor

# 從影片提取 GPS 軌跡
extractor = DashcamGPSExtractor()
gps_data = extractor.extract_from_video('data/dashcam_video.mp4')

# 匯出為不同格式
extractor.export_gpx('output/route.gpx')
extractor.export_kml('output/route.kml')
extractor.export_geojson('output/route.geojson')
```

### 路線視覺化

```python
from src.route_mapper import RouteVisualizer

# 建立互動式地圖
visualizer = RouteVisualizer()
map_html = visualizer.create_map(gps_data)
visualizer.save('output/route_map.html')

# 添加路線統計資訊
visualizer.add_statistics(
    distance=True,
    duration=True,
    speed=True
)
```

### 軌跡分析

```python
from src.route_mapper import RouteAnalyzer

analyzer = RouteAnalyzer(gps_data)
stats = analyzer.get_statistics()

print(f"總距離: {stats['distance']} km")
print(f"行駛時間: {stats['duration']} 分鐘")
print(f"平均速度: {stats['avg_speed']} km/h")
print(f"最高速度: {stats['max_speed']} km/h")
```

## 環境需求

- Python 3.8+
- ffmpeg (影片處理)

## 安裝

```bash
pip install -e .
```

## 使用範例

### 基本使用

```bash
# 從影片提取並繪製路線
python -m src.main --video data/dashcam_video.mp4 --output output/route.html
```

### 進階使用

```bash
# 包含速度熱圖
python -m src.main \
    --video data/dashcam_video.mp4 \
    --output output/route.html \
    --heatmap \
    --statistics

# 匯出多種格式
python -m src.main \
    --video data/dashcam_video.mp4 \
    --export-gpx output/route.gpx \
    --export-kml output/route.kml \
    --export-csv output/route.csv
```

## 支援的行車記錄器格式

- Garmin Dash Cam
- Nextbase Dash Cam
- BlackVue
- Viofo
- 通用 NMEA GPS 嵌入格式

## 開發狀態

- ✅ GPS 提取：支援主流行車記錄器
- ✅ 路線視覺化：互動式地圖
- ✅ 格式轉換：多種輸出格式
- 🚧 即時追蹤：即時 GPS 追蹤功能 (規劃中)

## 相關專案

- **GMSxGPS_Receiver** - GPS 即時資料接收
- **geo-tracker** - GeoJSON 軌跡工具
- **GeovisioUpdate** - 地理空間資料上傳

## 授權

TMS 內部專案

**最後更新：** 2026-01-26
