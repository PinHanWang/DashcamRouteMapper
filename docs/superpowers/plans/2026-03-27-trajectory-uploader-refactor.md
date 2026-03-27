# Trajectory + Uploader Module Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將 `src/module/` 下的程式碼重整為兩個獨立子模組 `trajectory/`（軌跡生成）與 `uploader/`（Dawarich 上傳），修正所有已知 bug，並新增 pipeline 串接的 `--upload` 選用旗標。

**Architecture:** 兩模組完全解耦，`trajectory/main.py` 以 `try/except ImportError` 動態 import `uploader`，確保未安裝 `python-dotenv` 或未建立 `.env` 時，核心軌跡功能仍可正常運作。`uploader/` 透過 `python-dotenv` 從 `.env` 讀取敏感設定，`DawarichUploader` 實作 context manager 確保 session 正確關閉。

**Tech Stack:** Python 3.10+, pandas, pyproj, geojson, requests, python-dotenv, tqdm, exiftool CLI

**Spec:** `docs/superpowers/specs/2026-03-27-module-refactor-design.md`

---

## 檔案清單

### 新建檔案
| 路徑 | 說明 |
|------|------|
| `src/module/trajectory/__init__.py` | 模組標識 |
| `src/module/trajectory/config.py` | 從 DashcamRouteMapper/config.py 搬移，import 路徑不變 |
| `src/module/trajectory/video2geojson.py` | 從 DashcamRouteMapper/video2geojson.py 搬移，刪除 dead code，更新 import |
| `src/module/trajectory/main.py` | 從 DashcamRouteMapper/main.py 搬移，加入 `--upload` 旗標 |
| `src/module/trajectory/utils/__init__.py` | 模組標識 |
| `src/module/trajectory/utils/geo.py` | 直接搬移，無邏輯變更 |
| `src/module/trajectory/utils/exif.py` | 搬移，修正 `_get_exif_start_time` 呼叫順序 |
| `src/module/trajectory/utils/gps_processor.py` | 直接搬移，無邏輯變更 |
| `src/module/trajectory/utils/json2csv.py` | 搬移，更新 import 路徑 |
| `src/module/uploader/__init__.py` | 模組標識 |
| `src/module/uploader/config.py` | 新建，從 `.env` 讀取設定 |
| `src/module/uploader/parser.py` | 從 dawarich_uploader.py 提取解析函式，修正 5 處 datetime 棄用 |
| `src/module/uploader/client.py` | 從 dawarich_uploader.py 提取 DawarichUploader，加入 context manager |
| `src/module/uploader/main.py` | 新建 CLI 入口 |
| `.env.sample` | 設定範本 |

### 修改檔案
| 路徑 | 說明 |
|------|------|
| `requirements.txt` | 新增 `python-dotenv`, `requests` |
| `.gitignore` | 確認 `.env` 已忽略 |

### 刪除目錄
| 路徑 | 說明 |
|------|------|
| `src/module/DashcamRouteMapper/` | 已搬移至 trajectory/ |
| `src/module/DashcamRouteProcessor/` | 舊版殘留，import 錯誤 |
| `src/module/Uploadtest/` | 已搬移至 uploader/ |
| `src/module/backup_download/` | 已在 git 中標記刪除，確認清除 |

---

## Task 1: 清理舊的殘留目錄

**Files:**
- Delete: `src/module/DashcamRouteProcessor/`
- Delete: `src/module/backup_download/`（git rm 確認）

- [ ] **Step 1: 刪除 DashcamRouteProcessor 目錄**

```bash
git rm -r src/module/DashcamRouteProcessor/
```

- [ ] **Step 2: 確認 backup_download 已從 git 移除**

```bash
git status src/module/backup_download/
# 若顯示 D（deleted），執行：
git rm -r --cached src/module/backup_download/ 2>/dev/null || true
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: remove obsolete DashcamRouteProcessor and backup_download modules"
```

---

## Task 2: 建立 trajectory/ 骨架與 config、geo

**Files:**
- Create: `src/module/trajectory/__init__.py`
- Create: `src/module/trajectory/utils/__init__.py`
- Create: `src/module/trajectory/config.py`
- Create: `src/module/trajectory/utils/geo.py`

- [ ] **Step 1: 建立目錄結構**

```bash
mkdir -p src/module/trajectory/utils
```

- [ ] **Step 2: 建立 `__init__.py` 檔案**

`src/module/trajectory/__init__.py`（空白）和 `src/module/trajectory/utils/__init__.py`（複製自 DashcamRouteMapper/utils/__init__.py）。

- [ ] **Step 3: 建立 `trajectory/config.py`**

完整複製 `src/module/DashcamRouteMapper/config.py`，**不需要修改任何內容**（沒有 module-specific import）。

- [ ] **Step 4: 建立 `trajectory/utils/geo.py`**

完整複製 `src/module/DashcamRouteMapper/utils/geo.py`，**不需要修改任何內容**。

- [ ] **Step 5: 確認**

```bash
python -c "from src.module.trajectory.config import EXIFTOOL_PATH, DEFAULT_FPS; print('config OK')"
python -c "from src.module.trajectory.utils.geo import haversine_total_distance; print('geo OK')"
```

Expected: 兩行均印出 `OK`

- [ ] **Step 6: Commit**

```bash
git add src/module/trajectory/
git commit -m "feat: scaffold trajectory module with config and geo utils"
```

---

## Task 3: 建立 trajectory/utils/exif.py（含 bug fix）

**Files:**
- Create: `src/module/trajectory/utils/exif.py`

**修正內容：** `_get_exif_start_time()` 在 `df.empty` 檢查之前被呼叫，導致無 GPS 資料時仍多做一次 exiftool 呼叫。

- [ ] **Step 1: 複製並修改 exif.py**

複製 `src/module/DashcamRouteMapper/utils/exif.py`，將所有 import 路徑更新：

```python
# 舊
from src.module.DashcamRouteMapper.config import EXIFTOOL_PATH
from src.module.DashcamRouteMapper.utils.geo import transform_array_wgs84_to_3857

# 新
from src.module.trajectory.config import EXIFTOOL_PATH
from src.module.trajectory.utils.geo import transform_array_wgs84_to_3857
```

- [ ] **Step 2: 修正 `make_exif_df` 函式中的順序問題**

找到 `make_exif_df` 函式（約第 113 行），將 `_get_exif_start_time` 呼叫**移至** `df.empty` 檢查之後：

```python
def make_exif_df(p: Path, columns: list | None = None) -> pd.DataFrame:
    data = _get_exif_extract_embedded_data(p)
    df = pd.DataFrame(data)
    df = df.rename(columns={
        "GPSDateTime": "datetime",
        "GPSLatitude": "lat",
        "GPSLongitude": "lon",
        "GPSSpeed": "speed",
        "GPSTrack": "azimuth",
    })
    df.drop_duplicates(inplace=True)

    # 修正：先確認有 GPS 資料再呼叫 exiftool 取 starttime
    if df.empty:
        return df

    fps, start_date = _get_exif_start_time(p)   # ← 移到 empty 檢查之後

    df["filename"] = p.stem
    df["starttime"] = start_date
    df["fps"] = fps
    df["sec"] = df["datetime"].map(lambda x: int(_get_df_seconds_difference(start_date, x)))
    df["frame"] = df["sec"].map(lambda x: int(x * fps))
    first_frame = df.loc[df.index[0], "frame"]
    if first_frame < 0:
        df["frame"] = df["frame"] - first_frame
    lon3857, lat3857 = transform_array_wgs84_to_3857(df["lon"].to_numpy(), df["lat"].to_numpy())
    df["lon3857"] = lon3857
    df["lat3857"] = lat3857
    return df[columns] if columns else df
```

- [ ] **Step 3: 確認**

```bash
python -c "from src.module.trajectory.utils.exif import make_exif_df; print('exif OK')"
```

Expected: `exif OK`

- [ ] **Step 4: Commit**

```bash
git add src/module/trajectory/utils/exif.py
git commit -m "feat: add trajectory/utils/exif.py, fix _get_exif_start_time call order"
```

---

## Task 4: 建立 trajectory/utils/gps_processor.py 與 json2csv.py

**Files:**
- Create: `src/module/trajectory/utils/gps_processor.py`
- Create: `src/module/trajectory/utils/json2csv.py`

- [ ] **Step 1: 複製 gps_processor.py**

完整複製 `src/module/DashcamRouteMapper/utils/gps_processor.py`，**不需要修改**（無 module import）。

- [ ] **Step 2: 複製並修改 json2csv.py**

複製 `src/module/DashcamRouteMapper/utils/json2csv.py`，更新 import 路徑：

```python
# 舊
from src.module.DashcamRouteMapper.config import DEFAULT_FPS
from src.module.DashcamRouteMapper.utils.geo import transform_wgs84_to_3857

# 新
from src.module.trajectory.config import DEFAULT_FPS
from src.module.trajectory.utils.geo import transform_wgs84_to_3857
```

- [ ] **Step 3: 確認**

```bash
python -c "from src.module.trajectory.utils.gps_processor import GPXProcessor; print('gps_processor OK')"
python -c "from src.module.trajectory.utils.json2csv import json_to_csv_with_fields; print('json2csv OK')"
```

- [ ] **Step 4: Commit**

```bash
git add src/module/trajectory/utils/
git commit -m "feat: add trajectory/utils gps_processor and json2csv"
```

---

## Task 5: 建立 trajectory/video2geojson.py（刪除 dead code）

**Files:**
- Create: `src/module/trajectory/video2geojson.py`

**修正內容：** 刪除 `_calculate_distance` 方法（dead code，類別內部無人呼叫）。

- [ ] **Step 1: 複製並修改 video2geojson.py**

複製 `src/module/DashcamRouteMapper/video2geojson.py`，做以下修改：

**1. 更新 import 路徑：**
```python
# 舊
from src.module.DashcamRouteMapper.utils.exif import make_exif_df
from src.module.DashcamRouteMapper.utils.geo import haversine_total_distance

# 新
from src.module.trajectory.utils.exif import make_exif_df
from src.module.trajectory.utils.geo import haversine_total_distance
```

**2. 刪除 `_calculate_distance` 方法**（第 136–141 行，整個方法移除）：

```python
# 刪除以下整段：
def _calculate_distance(self, coordinates: List[tuple]) -> float:
    """計算軌跡總長度（公尺），向量化 Haversine（取代逐點 geopy.geodesic）"""
    if len(coordinates) < 2:
        return 0.0
    coords = np.array(coordinates)
    return haversine_total_distance(coords[:, 0], coords[:, 1])
```

- [ ] **Step 2: 確認**

```bash
python -c "from src.module.trajectory.video2geojson import Video2GeoJson; print('video2geojson OK')"
```

- [ ] **Step 3: Commit**

```bash
git add src/module/trajectory/video2geojson.py
git commit -m "feat: add trajectory/video2geojson.py, remove _calculate_distance dead code"
```

---

## Task 6: 建立 trajectory/main.py（含 --upload pipeline）

**Files:**
- Create: `src/module/trajectory/main.py`

**新增內容：**
1. `--upload` 選用旗標（argparse）
2. `_run_upload(merged_path)` 函式（動態 import uploader，含錯誤保護）
3. `process()` 結尾呼叫 `_run_upload`（若 `--upload` 旗標啟用）

- [ ] **Step 1: 建立 trajectory/main.py**

複製 `src/module/DashcamRouteMapper/main.py` 並做以下修改：

**1. 更新 import 路徑（保留原有 `from typing import List, Optional`，`Optional` 在 `merge_all_geojson` 回傳型別中需要）：**
```python
# 舊
from src.module.DashcamRouteMapper.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR
from src.module.DashcamRouteMapper.video2geojson import Video2GeoJson

# 新
from src.module.trajectory.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR
from src.module.trajectory.video2geojson import Video2GeoJson
# 注意：保留 `from typing import List, Optional`（原始檔案第 23 行已有）
```

**2. 在 `merge_all_geojson` 之後，於 `process()` 方法的 `try` 區塊新增 upload 呼叫：**

```python
def process(
    self,
    video_dir: Path,
    output_dir: Path,
    feature_type: str = "point",
    max_workers: int = 4,
    upload: bool = False,       # ← 新增參數
) -> None:
    os.makedirs(output_dir, exist_ok=True)

    if not video_dir.exists():
        raise ValueError(f"影片資料夾不存在：{video_dir}")

    try:
        video_files = self._find_video_files(video_dir)
        if not video_files:
            raise ValueError(f"在 {video_dir} 找不到任何影片檔案")

        self.convert_video_to_geojson(video_files, output_dir, feature_type, max_workers)
        merged_path = self.merge_all_geojson(output_dir)

        if upload and merged_path:
            _run_upload(merged_path)
    except Exception as e:
        logger.error("批次處理失敗：%s", e)
```

**3. `merge_all_geojson` 修改為回傳合併檔案路徑：**

```python
def merge_all_geojson(self, directory: Path) -> Optional[Path]:
    # ... 原有邏輯不變 ...
    try:
        with open(merged_path, "w", encoding="utf-8") as f:
            geojson.dump(combined, f, indent=2)
        logger.info("合併 GeoJSON 已儲存至 %s", merged_path)
        return merged_path          # ← 新增：回傳路徑
    except Exception as e:
        logger.error("寫入合併 GeoJSON 失敗：%s", e)
        return None
```

**4. 在模組頂層新增 `_run_upload` 函式（放在 `logger = logging.getLogger(__name__)` 這行之後、class 定義之前；`_run_upload` 內部使用 `logger`，需確保 logger 已先定義）：**

```python
def _run_upload(merged_path: Path) -> None:
    """
    動態 import uploader 模組並上傳合併後的 GeoJSON。
    以 try/except 包裝，確保 uploader 未安裝或 .env 未設定時給出友善訊息。
    """
    try:
        from src.module.uploader.parser import parse_json_format, validate_coordinates, sort_by_timestamp
        from src.module.uploader.client import DawarichUploader
        from src.module.uploader import config as uploader_config
    except ImportError as e:
        logger.error(
            "無法載入 uploader 模組（%s）。"
            "請確認已安裝 python-dotenv：pip install python-dotenv",
            e,
        )
        return
    except KeyError as e:
        logger.error(
            "上傳設定缺失（環境變數 %s 未設定）。"
            "請建立 .env 檔案並參考 .env.sample 填入設定。",
            e,
        )
        return

    try:
        import json
        with open(merged_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        points = parse_json_format(data)
        points = validate_coordinates(points)
        points = sort_by_timestamp(points)

        if not points:
            logger.warning("上傳：解析後無有效點位，略過上傳")
            return

        cfg = {
            "DAWARICH_URL": uploader_config.DAWARICH_URL,
            "API_KEY": uploader_config.DAWARICH_API_KEY,
            "BATCH_SIZE": uploader_config.BATCH_SIZE,
            "REQUEST_TIMEOUT": uploader_config.REQUEST_TIMEOUT,
        }
        with DawarichUploader(cfg) as uploader:
            uploader.upload_trajectory(points)
    except Exception as e:
        logger.error("上傳失敗：%s", e)
```

**5. 在 `_parse_args()` 中新增 `--upload` 旗標：**

```python
parser.add_argument(
    "--upload",
    action="store_true",
    default=False,
    help="生成軌跡後自動上傳至 Dawarich（需設定 .env）",
)
```

**6. 在 `main()` 中傳遞 `upload` 參數：**

```python
processor.process(
    video_dir=args.input,
    output_dir=args.output,
    feature_type=args.type,
    max_workers=args.workers,
    upload=args.upload,        # ← 新增
)
```

- [ ] **Step 2: 確認**

```bash
python -m src.module.trajectory.main --help
```

Expected: 印出 help 訊息，包含 `--upload` 選項

- [ ] **Step 3: Commit**

```bash
git add src/module/trajectory/main.py
git commit -m "feat: add trajectory/main.py with --upload pipeline flag"
```

---

## Task 7: 建立 uploader/ 骨架與 config.py

**Files:**
- Create: `src/module/uploader/__init__.py`
- Create: `src/module/uploader/config.py`

- [ ] **Step 1: 建立目錄與 `__init__.py`**

```bash
mkdir -p src/module/uploader
touch src/module/uploader/__init__.py
```

- [ ] **Step 2: 建立 `uploader/config.py`**

```python
"""
uploader 設定模組
從 .env 讀取 Dawarich 連線設定，敏感資料不寫入程式碼。
請從專案根目錄執行（python -m src.module...），load_dotenv() 才能正確找到 .env。
"""
import os

from dotenv import load_dotenv

# 從專案根目錄的 .env 載入設定
load_dotenv()

# 必填：未設定直接拋 KeyError，由呼叫端（_run_upload）轉為友善訊息
DAWARICH_URL: str = os.environ["DAWARICH_URL"]
DAWARICH_API_KEY: str = os.environ["DAWARICH_API_KEY"]

# 選填：提供合理預設值
BATCH_SIZE: int = int(os.environ.get("DAWARICH_BATCH_SIZE", "100"))
REQUEST_TIMEOUT: int = int(os.environ.get("DAWARICH_REQUEST_TIMEOUT", "30"))
```

- [ ] **Step 3: 確認（需先建立 .env）**

```bash
# 暫時建立測試用 .env（不 commit）
echo "DAWARICH_URL=http://localhost:3000" > .env
echo "DAWARICH_API_KEY=test_key" >> .env
python -c "from src.module.uploader.config import DAWARICH_URL; print('config OK:', DAWARICH_URL)"
```

Expected: `config OK: http://localhost:3000`

- [ ] **Step 4: Commit**

```bash
git add src/module/uploader/__init__.py src/module/uploader/config.py
git commit -m "feat: add uploader module scaffold with dotenv config"
```

---

## Task 8: 建立 uploader/parser.py

**Files:**
- Create: `src/module/uploader/parser.py`

**修正內容：**
- `datetime.utcnow()` → `datetime.now(timezone.utc)`
- `datetime.utcfromtimestamp()` → `datetime.fromtimestamp(..., tz=timezone.utc)`

- [ ] **Step 1: 建立 `uploader/parser.py`**

提取 `dawarich_uploader.py` 中的解析相關函式，修正 datetime 棄用問題：

```python
"""
GeoJSON / OwnTracks / Google Takeout 軌跡解析與資料處理工具
"""
from datetime import datetime, timezone
from math import atan2, cos, radians, sin, sqrt
from typing import Dict, List


def parse_json_format(data) -> List[Dict]:
    """
    自動識別並解析不同的 JSON 格式為標準點位列表。

    支援格式：
    1. GeoJSON FeatureCollection（含 trajectory/ 模組輸出格式）
    2. OwnTracks JSON 陣列
    3. Google Takeout Records.json
    4. 簡單的點位陣列
    5. GeoJSON LineString Feature
    """
    points = []

    # 格式 1: GeoJSON FeatureCollection
    if isinstance(data, dict) and data.get("type") == "FeatureCollection":
        for feature in data.get("features", []):
            if feature.get("geometry", {}).get("type") == "Point":
                coords = feature["geometry"]["coordinates"]
                props = feature.get("properties", {})
                points.append({
                    "lon": coords[0],
                    "lat": coords[1],
                    "timestamp": props.get("time", props.get("timestamp", "")),
                    "altitude": coords[2] if len(coords) > 2 else props.get("altitude", props.get("ele", 0)),
                    "accuracy": props.get("accuracy", props.get("horizontal_accuracy", 10)),
                    "speed": props.get("speed", props.get("velocity", 0)),
                })

    # 格式 2: OwnTracks JSON 陣列
    elif isinstance(data, list) and data and isinstance(data[0], dict) and data[0].get("_type") == "location":
        for item in data:
            if item.get("lat") is not None and item.get("lon") is not None:
                points.append({
                    "lat": item.get("lat"),
                    "lon": item.get("lon"),
                    "timestamp": item.get("tst"),
                    "altitude": item.get("alt", 0),
                    "accuracy": item.get("acc", 10),
                    "speed": item.get("vel", 0),
                })

    # 格式 3: Google Takeout Records.json
    elif isinstance(data, dict) and "locations" in data:
        for location in data["locations"]:
            lat = location.get("latitudeE7", 0) / 1e7
            lon = location.get("longitudeE7", 0) / 1e7
            timestamp = location.get("timestamp", location.get("timestampMs", ""))
            if isinstance(timestamp, str) and timestamp.isdigit():
                timestamp = int(timestamp) / 1000
            if lat != 0 and lon != 0:
                points.append({
                    "lat": lat,
                    "lon": lon,
                    "timestamp": timestamp,
                    "altitude": location.get("altitude", 0),
                    "accuracy": location.get("accuracy", 10),
                    "speed": location.get("velocity", 0),
                })

    # 格式 4: 簡單點位陣列
    elif isinstance(data, list) and data:
        for item in data:
            if isinstance(item, dict) and "lat" in item and "lon" in item:
                points.append({
                    "lat": item.get("lat"),
                    "lon": item.get("lon"),
                    "timestamp": item.get("timestamp", item.get("time", item.get("tst", ""))),
                    "altitude": item.get("altitude", item.get("alt", item.get("ele", 0))),
                    "accuracy": item.get("accuracy", item.get("acc", 10)),
                    "speed": item.get("speed", item.get("velocity", item.get("vel", 0))),
                })

    # 格式 5: GeoJSON LineString Feature（無個別時間戳記，以 1 分鐘間隔生成）
    elif isinstance(data, dict) and data.get("type") == "Feature":
        geom = data.get("geometry", {})
        if geom.get("type") == "LineString":
            base_time = datetime.now(timezone.utc).timestamp()     # 修正：取代 utcnow()
            for i, coord in enumerate(geom.get("coordinates", [])):
                points.append({
                    "lon": coord[0],
                    "lat": coord[1],
                    "timestamp": base_time + i * 60,
                    "altitude": coord[2] if len(coord) > 2 else 0,
                    "accuracy": 10,
                    "speed": 0,
                })

    return points


def normalize_timestamp(timestamp) -> str:
    """將各種時間格式統一轉換為 ISO 8601 字串（UTC，帶 Z 後綴）"""
    if not timestamp:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")    # 修正

    if isinstance(timestamp, (int, float)):
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")    # 修正

    if isinstance(timestamp, str):
        if "T" in timestamp:
            if not timestamp.endswith("Z") and "+" not in timestamp:
                return timestamp + "Z"
            return timestamp
        if timestamp.isdigit():
            return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat().replace("+00:00", "Z")    # 修正

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")    # 修正


def validate_coordinates(points: List[Dict], show_warnings: bool = True) -> List[Dict]:
    """驗證並過濾無效座標（lat ∈ [-90,90]，lon ∈ [-180,180]）"""
    valid_points = []
    invalid_count = 0

    for i, point in enumerate(points):
        lat = point.get("lat")
        lon = point.get("lon")
        if lat is None or lon is None:
            invalid_count += 1
            continue
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            if show_warnings and invalid_count < 5:
                print(f"   ⚠️  點位 {i}: 無效座標 ({lat}, {lon})")
            invalid_count += 1
            continue
        valid_points.append(point)

    if invalid_count > 0 and show_warnings:
        print(f"⚠️  過濾了 {invalid_count} 個無效座標")

    return valid_points


def sort_by_timestamp(points: List[Dict]) -> List[Dict]:
    """依時間戳記升冪排序點位"""
    return sorted(points, key=lambda p: normalize_timestamp(p.get("timestamp")))


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """使用 Haversine 公式計算兩點間距離（公尺）"""
    R = 6_371_000
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def analyze_trajectory(points: List[Dict], show_warnings: bool = True) -> Dict:
    """計算軌跡統計資訊（總點數、總距離、起訖時間、大間隔警告）"""
    if not points:
        return {}

    total_distance = sum(
        calculate_distance(points[i]["lat"], points[i]["lon"], points[i + 1]["lat"], points[i + 1]["lon"])
        for i in range(len(points) - 1)
    )

    large_gaps = []
    if show_warnings:
        for i in range(len(points) - 1):
            t1 = datetime.fromisoformat(normalize_timestamp(points[i]["timestamp"]).replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(normalize_timestamp(points[i + 1]["timestamp"]).replace("Z", "+00:00"))
            gap = (t2 - t1).total_seconds() / 60
            if gap > 60:
                large_gaps.append((i, gap))

    return {
        "total_points": len(points),
        "total_distance_km": total_distance / 1000,
        "start_time": normalize_timestamp(points[0]["timestamp"]),
        "end_time": normalize_timestamp(points[-1]["timestamp"]),
        "large_gaps": large_gaps,
    }
```

- [ ] **Step 2: 確認**

```bash
python -c "from src.module.uploader.parser import parse_json_format, normalize_timestamp; print('parser OK')"
```

- [ ] **Step 3: Commit**

```bash
git add src/module/uploader/parser.py
git commit -m "feat: add uploader/parser.py with fixed datetime (timezone.utc)"
```

---

## Task 9: 建立 uploader/client.py（含 context manager）

**Files:**
- Create: `src/module/uploader/client.py`

- [ ] **Step 1: 建立 `uploader/client.py`**

```python
"""
Dawarich API 上傳客戶端
使用 context manager 確保 requests.Session 正確關閉。
"""
import logging
from typing import Dict, List

import requests

from src.module.uploader.parser import normalize_timestamp

logger = logging.getLogger(__name__)


class DawarichUploader:
    """
    Dawarich Overland API 批次上傳客戶端。

    建議以 context manager 使用：
        with DawarichUploader(config) as uploader:
            uploader.upload_trajectory(points)
    """

    def __init__(self, config: Dict) -> None:
        self.base_url = config["DAWARICH_URL"].rstrip("/")
        self.api_key = config["API_KEY"]
        self.batch_size = config["BATCH_SIZE"]
        self.timeout = config["REQUEST_TIMEOUT"]
        self.session = requests.Session()

    def __enter__(self) -> "DawarichUploader":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.session.close()

    def test_connection(self) -> bool:
        """測試 Dawarich API 連線是否正常"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/health",
                timeout=5,
            )
            if response.status_code == 200:
                logger.info("Dawarich 連線正常：%s", response.json().get("status", "unknown"))
                return True
            logger.warning("Dawarich 回應異常：HTTP %d", response.status_code)
            return False
        except Exception as e:
            logger.error("無法連線到 Dawarich：%s", e)
            return False

    def upload_batch(self, points: List[Dict]) -> Dict:
        """上傳一批點位至 Dawarich Overland API"""
        locations = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
                "properties": {
                    "timestamp": normalize_timestamp(p.get("timestamp")),
                    "altitude": float(p.get("altitude", 0)),
                    "speed": float(p.get("speed", 0)),
                    "horizontal_accuracy": float(p.get("accuracy", 10)),
                },
            }
            for p in points
        ]

        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/overland/batches",
                params={"api_key": self.api_key},
                json={"locations": locations},
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            return {
                "success": response.status_code in (200, 201),
                "status_code": response.status_code,
                "message": response.text,
                "points_uploaded": len(points),
            }
        except requests.Timeout:
            return {"success": False, "status_code": 0, "message": "請求超時", "points_uploaded": 0}
        except Exception as e:
            return {"success": False, "status_code": 0, "message": str(e), "points_uploaded": 0}

    def upload_trajectory(self, points: List[Dict]) -> bool:
        """上傳完整軌跡（自動分批），回傳是否全部成功"""
        if not points:
            logger.warning("沒有點位可上傳")
            return False

        total_batches = (len(points) + self.batch_size - 1) // self.batch_size
        success_count = 0
        failed_count = 0

        logger.info("開始上傳 %d 個點位（分 %d 批次）", len(points), total_batches)

        for i in range(0, len(points), self.batch_size):
            batch = points[i : i + self.batch_size]
            batch_num = i // self.batch_size + 1
            result = self.upload_batch(batch)

            if result["success"]:
                success_count += len(batch)
                logger.info("批次 %d/%d 上傳成功（%d 點）", batch_num, total_batches, len(batch))
            else:
                failed_count += len(batch)
                logger.error("批次 %d/%d 上傳失敗：%s", batch_num, total_batches, result["message"])

        logger.info("上傳完成：成功 %d 點，失敗 %d 點", success_count, failed_count)
        return failed_count == 0
```

- [ ] **Step 2: 確認**

```bash
python -c "from src.module.uploader.client import DawarichUploader; print('client OK')"
```

- [ ] **Step 3: Commit**

```bash
git add src/module/uploader/client.py
git commit -m "feat: add uploader/client.py with context manager and structured logging"
```

---

## Task 10: 建立 uploader/main.py（獨立 CLI）

**Files:**
- Create: `src/module/uploader/main.py`

- [ ] **Step 1: 建立 `uploader/main.py`**

```python
"""
Dawarich 軌跡上傳工具 CLI

使用方式：
    python -m src.module.uploader.main --input path/to/file.geojson
    python -m src.module.uploader.main --help
"""
import argparse
import json
import logging
from pathlib import Path

from src.module.uploader import config as cfg
from src.module.uploader.client import DawarichUploader
from src.module.uploader.parser import (
    analyze_trajectory,
    parse_json_format,
    sort_by_timestamp,
    validate_coordinates,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dawarich 軌跡上傳工具：將 GeoJSON 上傳至 Dawarich",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        required=True,
        help="要上傳的 GeoJSON 檔案路徑",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=cfg.BATCH_SIZE,
        help="每批次上傳點數",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=cfg.REQUEST_TIMEOUT,
        help="API 請求超時時間（秒）",
    )
    parser.add_argument(
        "--no-sort",
        action="store_true",
        default=False,
        help="跳過依時間排序",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        default=False,
        help="跳過座標範圍驗證",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if not args.input.exists():
        logger.error("找不到檔案：%s", args.input)
        return

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    points = parse_json_format(data)
    if not points:
        logger.error("無法解析資料或沒有有效點位")
        return

    logger.info("解析完成：%d 個點位", len(points))

    if not args.no_validate:
        points = validate_coordinates(points)

    if not args.no_sort:
        points = sort_by_timestamp(points)

    logger.info("處理後剩餘 %d 個有效點位", len(points))

    if not points:
        logger.error("沒有有效點位可上傳")
        return

    stats = analyze_trajectory(points)
    logger.info(
        "軌跡資訊：%d 點，%.2f 公里，%s ~ %s",
        stats["total_points"],
        stats["total_distance_km"],
        stats["start_time"],
        stats["end_time"],
    )

    upload_config = {
        "DAWARICH_URL": cfg.DAWARICH_URL,
        "API_KEY": cfg.DAWARICH_API_KEY,
        "BATCH_SIZE": args.batch_size,
        "REQUEST_TIMEOUT": args.timeout,
    }

    with DawarichUploader(upload_config) as uploader:
        if not uploader.test_connection():
            logger.error("無法連線到 Dawarich，請確認 URL 與網路狀態")
            return
        success = uploader.upload_trajectory(points)

    if success:
        logger.info("上傳完成！請至 %s 查看軌跡", cfg.DAWARICH_URL)
    else:
        logger.error("上傳過程中發生錯誤，請查看上方日誌")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 確認**

```bash
python -m src.module.uploader.main --help
```

Expected: 印出 help 訊息，包含 `--input`, `--batch-size`, `--timeout`, `--no-sort`, `--no-validate`

- [ ] **Step 3: Commit**

```bash
git add src/module/uploader/main.py
git commit -m "feat: add uploader/main.py with full CLI interface"
```

---

## Task 11: 建立 .env.sample，更新 .gitignore 與 requirements.txt

**Files:**
- Create: `.env.sample`
- Modify: `requirements.txt`
- Modify: `.gitignore`（確認 `.env` 已忽略）

- [ ] **Step 1: 建立 `.env.sample`**

```dotenv
# Dawarich 服務 URL（含 port，結尾不加斜線）
DAWARICH_URL=http://your-dawarich-host:3000

# 從 Dawarich 設定頁面取得的 API Key
DAWARICH_API_KEY=your_api_key_here

# 每批次上傳點數（建議 50-200，數字越大速度越快但失敗時損失越多）
DAWARICH_BATCH_SIZE=100

# API 請求超時時間（秒）
DAWARICH_REQUEST_TIMEOUT=30
```

- [ ] **Step 2: 更新 `requirements.txt`**

在 `# External dependencies` 段落之前，新增：

```
# HTTP client
requests>=2.28.0

# Environment variable management
python-dotenv>=1.0.0
```

- [ ] **Step 3: 確認 `.gitignore` 已忽略 `.env`**

目前 `.gitignore` 已有 `.env` 規則（第 6 行）。確認後不需修改。

- [ ] **Step 4: Commit**

```bash
git add .env.sample requirements.txt
git commit -m "chore: add .env.sample and update requirements.txt with requests, python-dotenv"
```

---

## Task 12: 刪除舊目錄

**Files:**
- Delete: `src/module/DashcamRouteMapper/`
- Delete: `src/module/Uploadtest/`

- [ ] **Step 1: 刪除舊目錄**

```bash
git rm -r src/module/DashcamRouteMapper/
git rm -r src/module/Uploadtest/
```

- [ ] **Step 2: Commit**

```bash
git commit -m "chore: remove old DashcamRouteMapper and Uploadtest directories"
```

---

## Task 13: 整合驗證

- [ ] **Step 0: 確認 `.env` 存在（必要前置條件）**

`uploader/config.py` 在 import 時即載入 `.env`，若不存在會拋 `KeyError`。
Task 7 Step 3 的測試用 `.env` 若已刪除，執行以下指令重建：

```bash
# 確認 .env 存在（使用真實的測試值）
echo "DAWARICH_URL=http://localhost:3000" > .env
echo "DAWARICH_API_KEY=test_key_for_import_check" >> .env
echo "DAWARICH_BATCH_SIZE=100" >> .env
echo "DAWARICH_REQUEST_TIMEOUT=30" >> .env
```

> ⚠️ 注意：`.env` 已加入 `.gitignore`，不會被 commit。

- [ ] **Step 1: 確認所有模組可正常 import**

```bash
python -c "
from src.module.trajectory.config import EXIFTOOL_PATH, DEFAULT_FPS
from src.module.trajectory.utils.geo import haversine_total_distance
from src.module.trajectory.utils.exif import make_exif_df
from src.module.trajectory.utils.gps_processor import GPXProcessor
from src.module.trajectory.utils.json2csv import json_to_csv_with_fields
from src.module.trajectory.video2geojson import Video2GeoJson
from src.module.trajectory.main import DashcamRouteProcessor
from src.module.uploader.config import DAWARICH_URL
from src.module.uploader.parser import parse_json_format, normalize_timestamp
from src.module.uploader.client import DawarichUploader
print('所有模組 import 成功')
"
```

Expected: `所有模組 import 成功`

- [ ] **Step 2: 確認 trajectory CLI help**

```bash
python -m src.module.trajectory.main --help
```

Expected: 顯示 `--input`, `--output`, `--type`, `--workers`, `--upload` 五個選項

- [ ] **Step 3: 確認 uploader CLI help**

```bash
python -m src.module.uploader.main --help
```

Expected: 顯示 `--input`, `--batch-size`, `--timeout`, `--no-sort`, `--no-validate` 五個選項

- [ ] **Step 4: 驗證 GeoJSON 解析相容性**

```python
# 用 trajectory/ 輸出格式測試 parser
import json
from src.module.uploader.parser import parse_json_format

sample = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [121.5, 25.0]},
            "properties": {"datetime": "2026-03-27T10:00:00Z", "timestamp": 1743069600, "speed": 50.0, "azimuth": 180.0}
        }
    ]
}
points = parse_json_format(sample)
assert len(points) == 1
assert points[0]["lon"] == 121.5
assert points[0]["timestamp"] == 1743069600
print("GeoJSON 相容性驗證通過")
```

- [ ] **Step 5: 最終 Commit**

```bash
git add -A
git status  # 確認無多餘檔案
git commit -m "chore: final cleanup and verification" --allow-empty
```
