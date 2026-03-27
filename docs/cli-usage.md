# CLI 使用說明

> 所有指令請從**專案根目錄**執行（`D:\MyProject\DashcamRouteMapper\`）

---

## 一、軌跡生成模組（trajectory）

從行車記錄器 MP4 提取 GPS 軌跡，輸出 GeoJSON 檔案。

### 基本用法

```bash
# 使用 config.py 預設路徑（data/raw → output/）
python -m src.module.trajectory.main

# 指定輸入 / 輸出路徑
python -m src.module.trajectory.main --input M:/DCIM/Movie --output E:/output

# 查看所有選項
python -m src.module.trajectory.main --help
```

### 完整參數說明

| 參數 | 縮寫 | 預設值 | 說明 |
|------|------|--------|------|
| `--input` | `-i` | `data/raw` | 輸入影片資料夾（遞迴掃描 `.mp4`、`.mov`、`.avi`） |
| `--output` | `-o` | `output/` | GeoJSON 輸出資料夾 |
| `--type` | `-t` | `point` | 輸出 Feature 類型：`all`（線＋點）、`point`（僅點）、`line`（僅線） |
| `--workers` | `-w` | `4` | 平行處理執行緒數（建議設為 CPU 核心數） |
| `--upload` | — | `False` | 生成完成後自動上傳至 Dawarich（需先設定 `.env`） |

### 使用範例

```bash
# 4 個 worker 平行處理，只輸出點位
python -m src.module.trajectory.main \
    --input M:/DCIM/Movie \
    --output E:/output/20260327 \
    --type point \
    --workers 4

# 輸出全部 Feature（LineString + Point）
python -m src.module.trajectory.main \
    --input M:/DCIM/Movie \
    --output E:/output/20260327 \
    --type all

# 生成後自動上傳（需先設定 .env，見第三節）
python -m src.module.trajectory.main \
    --input M:/DCIM/Movie \
    --output E:/output/20260327 \
    --upload
```

### 輸出結構

```
E:/output/20260327/
├── VIDEO001.geojson       ← 每部影片一個 GeoJSON
├── VIDEO002.geojson
├── ...
└── merged/
    └── 20260327_103045.geojson   ← 所有影片合併後的 GeoJSON
```

---

## 二、上傳模組（uploader）

將 GeoJSON 軌跡上傳至 Dawarich。可單獨使用，也可透過 `--upload` 旗標由軌跡生成模組自動呼叫。

### 前置設定

複製 `.env.sample` 為 `.env` 並填入設定：

```bash
copy .env.sample .env
```

編輯 `.env`：

```dotenv
DAWARICH_URL=http://your-dawarich-host:3000    # Dawarich 服務位址
DAWARICH_API_KEY=your_api_key_here             # 從 Dawarich Settings 頁面取得
DAWARICH_BATCH_SIZE=100                        # 每批次上傳點數（建議 50–200）
DAWARICH_REQUEST_TIMEOUT=30                    # API 超時秒數
```

> ⚠️ `.env` 已加入 `.gitignore`，不會被提交至版本控制。

### 基本用法

```bash
# 上傳指定 GeoJSON
python -m src.module.uploader.main --input E:/output/20260327/merged/20260327_103045.geojson

# 查看所有選項
python -m src.module.uploader.main --help
```

### 完整參數說明

| 參數 | 縮寫 | 預設值 | 說明 |
|------|------|--------|------|
| `--input` | `-i` | （必填）| 要上傳的 GeoJSON 檔案路徑 |
| `--batch-size` | — | `.env` 設定值 | 每批次上傳點數 |
| `--timeout` | — | `.env` 設定值 | API 請求超時秒數 |
| `--no-sort` | — | `False` | 跳過依時間排序 |
| `--no-validate` | — | `False` | 跳過座標範圍驗證 |

### 使用範例

```bash
# 標準上傳（自動排序 + 驗證座標）
python -m src.module.uploader.main \
    --input E:/output/merged/20260327_103045.geojson

# 指定批次大小與超時（覆蓋 .env 設定）
python -m src.module.uploader.main \
    --input E:/output/merged/20260327_103045.geojson \
    --batch-size 50 \
    --timeout 60

# 跳過排序與驗證（資料已確認乾淨時使用）
python -m src.module.uploader.main \
    --input E:/output/merged/20260327_103045.geojson \
    --no-sort \
    --no-validate
```

### 支援的輸入格式

| 格式 | 說明 |
|------|------|
| GeoJSON FeatureCollection | 本專案 `trajectory/` 模組的輸出格式 |
| OwnTracks JSON | `_type: "location"` 陣列 |
| Google Takeout Records.json | `locations` 陣列，E7 座標格式 |
| 簡單點位陣列 | 含 `lat`、`lon` 的 dict 陣列 |
| GeoJSON LineString Feature | 自動以 1 分鐘間隔生成時間戳記 |

---

## 三、Pipeline 串接（生成 + 上傳）

```bash
# 生成 GeoJSON 完成後自動上傳至 Dawarich
python -m src.module.trajectory.main \
    --input M:/DCIM/Movie \
    --output E:/output/20260327 \
    --upload
```

執行流程：
1. 掃描影片 → 平行轉換為 GeoJSON
2. 合併所有 GeoJSON → `merged/<timestamp>.geojson`
3. 解析合併檔 → 驗證座標 → 依時間排序
4. 批次上傳至 Dawarich

若 `.env` 未設定，步驟 3–4 會跳過並印出錯誤提示，**不影響**步驟 1–2 的 GeoJSON 輸出。

---

## 四、工具指令

### GPX 視覺化

```bash
python -m src.module.trajectory.utils.gps_processor [gpx_file]
```

輸出 Folium HTML 地圖至 `output/`，包含軌跡線與聚合標記。

### GeoJSON 轉 CSV

```bash
python -m src.module.trajectory.utils.json2csv [input_folder] [output_folder]
```

將 `input_folder` 內所有 `.geojson` 轉為 CSV，新增 `lon3857`、`lat3857`（EPSG:3857）欄位。
