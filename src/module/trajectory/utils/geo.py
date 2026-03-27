"""
共用地理座標轉換工具

集中管理座標轉換邏輯，避免各模組重複定義相同的 Transformer 實例。
"""
import numpy as np
from pyproj import Transformer

# 模組層級建立一次，整個程序只初始化一個 Transformer 實例
_wgs84_to_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)


def transform_wgs84_to_3857(lon: float, lat: float) -> tuple[float, float]:
    """WGS84（EPSG:4326）→ Web Mercator（EPSG:3857）單點座標轉換"""
    return _wgs84_to_3857.transform(lon, lat)


def transform_array_wgs84_to_3857(lons, lats) -> tuple[np.ndarray, np.ndarray]:
    """
    向量化 WGS84 → EPSG:3857 批次轉換。
    lons, lats 可為 numpy array、pandas Series 或 list。
    """
    return _wgs84_to_3857.transform(lons, lats)


def haversine_total_distance(lons: np.ndarray, lats: np.ndarray) -> float:
    """
    計算軌跡總長度（公尺），使用向量化 Haversine 公式取代逐點 geodesic。

    Args:
        lons: 經度陣列（度，WGS84）
        lats: 緯度陣列（度，WGS84）

    Returns:
        軌跡總長度（公尺）
    """
    lons = np.asarray(lons, dtype=float)
    lats = np.asarray(lats, dtype=float)
    if len(lons) < 2:
        return 0.0

    R = 6_371_000.0  # 地球平均半徑（公尺）
    lat_r = np.radians(lats)
    lon_r = np.radians(lons)
    dlat = np.diff(lat_r)
    dlon = np.diff(lon_r)
    a = np.sin(dlat / 2) ** 2 + np.cos(lat_r[:-1]) * np.cos(lat_r[1:]) * np.sin(dlon / 2) ** 2
    return float(np.sum(2 * R * np.arctan2(np.sqrt(a), np.sqrt(1 - a))))
