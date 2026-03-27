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
            base_time = datetime.now(timezone.utc).timestamp()
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
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    if isinstance(timestamp, (int, float)):
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")

    if isinstance(timestamp, str):
        if "T" in timestamp:
            if not timestamp.endswith("Z") and "+" not in timestamp:
                return timestamp + "Z"
            return timestamp
        if timestamp.isdigit():
            return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat().replace("+00:00", "Z")

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
