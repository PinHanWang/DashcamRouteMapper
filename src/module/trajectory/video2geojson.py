"""
行車記錄器影片 → GeoJSON 轉換核心模組
"""
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import geojson
from geojson import Feature, FeatureCollection, LineString, Point

from src.module.trajectory.utils.exif import make_exif_df
from src.module.trajectory.utils.geo import haversine_total_distance

logger = logging.getLogger(__name__)

# 行車記錄器 EXIF 日期格式（YYYY:MM:DD）→ ISO 格式（YYYY-MM-DD）
_EXIF_DATE_RE = re.compile(r"(\d{4}):(\d{2}):(\d{2})")


def _exif_to_iso(dt_str: str) -> str:
    """將 EXIF 日期格式轉為 ISO 8601，例如 '2024:01:15 10:30:00' → '2024-01-15 10:30:00'"""
    return _EXIF_DATE_RE.sub(r"\1-\2-\3", dt_str)


class Video2GeoJson:
    def __init__(self, video_path: Path) -> None:
        self.video_path = Path(video_path)
        try:
            self.df = make_exif_df(video_path, None)
        except Exception as e:
            raise ValueError(
                f"讀取影片 metadata 失敗，無 GPS 資料：{e}"
            )
        # 明確報錯：空 DataFrame 表示影片無 GPS 資料，後續 .iloc[] 會 crash
        if self.df.empty:
            raise ValueError(f"影片 {video_path.name} 不含 GPS 資料，已跳過")

    def create_point_feature(self) -> List[Feature]:
        """
        從每一筆 GPS 記錄建立 Point Feature 清單。
        使用 zip 迭代 Series 取代 iterrows()，避免每列建立 pandas Series 的額外開銷。
        """
        # 批次轉換 datetime 字串，一次處理整欄
        dt_series = pd.to_datetime(
            self.df["datetime"].str.replace(_EXIF_DATE_RE, r"\1-\2-\3", regex=True)
        )
        speeds = self.df["speed"] if "speed" in self.df.columns else [""] * len(self.df)
        azimuths = self.df["azimuth"] if "azimuth" in self.df.columns else [""] * len(self.df)

        return [
            Feature(
                geometry=Point((lon, lat)),
                properties={
                    "datetime": dt.isoformat() + "Z",
                    "timestamp": int(dt.timestamp()),
                    "speed": speed,
                    "azimuth": azimuth,
                },
            )
            for lon, lat, dt, speed, azimuth in zip(
                self.df["lon"], self.df["lat"], dt_series, speeds, azimuths
            )
        ]

    def create_line_feature(self) -> Feature:
        """從所有 GPS 記錄建立 LineString Feature"""
        lons = self.df["lon"].to_numpy()
        lats = self.df["lat"].to_numpy()
        line_coordinates = list(zip(lons, lats))

        # 向量化 Haversine 距離（取代逐點 geopy.geodesic）
        total_distance = haversine_total_distance(lons, lats)

        starttime_obj = datetime.strptime(_exif_to_iso(self.df["datetime"].iloc[0]), "%Y-%m-%d %H:%M:%S")
        endtime_obj = datetime.strptime(_exif_to_iso(self.df["datetime"].iloc[-1]), "%Y-%m-%d %H:%M:%S")
        line_properties = {
            "filename": self.df["filename"].iloc[0],
            "starttime": starttime_obj.isoformat(),
            "endtime": endtime_obj.isoformat(),
            "length(m)": round(total_distance, 3),
        }

        return Feature(geometry=LineString(line_coordinates), properties=line_properties)

    def create_feature_collection(self, feature_type: str = "all") -> FeatureCollection:
        """
        建立 GeoJSON FeatureCollection。
        feature_type：'all'（線 + 點）、'point'（僅點）、'line'（僅線）
        """
        feature_collection = []

        if feature_type == "all":
            try:
                feature_collection.append(self.create_line_feature())
            except Exception as e:
                logger.warning("建立 LineString Feature 失敗：%s", e)
            try:
                feature_collection.extend(self.create_point_feature())
            except Exception as e:
                logger.warning("建立 Point Features 失敗：%s", e)

        elif feature_type == "point":
            try:
                feature_collection.extend(self.create_point_feature())
            except Exception as e:
                logger.warning("建立 Point Features 失敗：%s", e)

        elif feature_type == "line":
            try:
                feature_collection.append(self.create_line_feature())
            except Exception as e:
                logger.warning("建立 LineString Feature 失敗：%s", e)

        else:
            raise ValueError("feature_type 無效，請選擇 'all'、'point' 或 'line'。")

        return FeatureCollection(features=feature_collection)

    def save_geojson(self, output_dir: Path, feature_type: str = "all") -> None:
        """將轉換結果儲存為 GeoJSON 檔案"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        feature_collection = self.create_feature_collection(feature_type)
        output_path = output_dir / f"{self.video_path.stem}.geojson"

        with open(output_path, "w", encoding="utf-8") as f:
            geojson.dump(feature_collection, f, indent=2)

        logger.info("GeoJSON 已儲存至 %s", output_path)

    def _get_stats(self) -> dict:
        """傳回軌跡統計資訊"""
        stats = {}
        try:
            stats['Num_points'] = len(self.df)
            stats['Start_time'] = self.df['datetime'].min()
            stats['End_time'] = self.df['datetime'].max()
            stats['Duration_sec'] = (
                datetime.strptime(stats['End_time'], "%Y:%m:%d %H:%M:%S")
                - datetime.strptime(stats['Start_time'], "%Y:%m:%d %H:%M:%S")
            ).total_seconds()
            lons = self.df["lon"].to_numpy()
            lats = self.df["lat"].to_numpy()
            stats['Total_distance_m'] = haversine_total_distance(lons, lats)
            stats['Boundary'] = {
                'min_lon': float(lons.min()),
                'max_lon': float(lons.max()),
                'min_lat': float(lats.min()),
                'max_lat': float(lats.max()),
            }
        except Exception as e:
            logger.error("計算統計資訊失敗：%s", e)

        return stats


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法：python video2geojson.py <video_path> [output_dir] [feature_type]")
        print("  feature_type：all | point | line（預設 point）")
        sys.exit(1)

    video_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output")
    feature_type = sys.argv[3] if len(sys.argv) > 3 else "point"

    converter = Video2GeoJson(video_path)
    converter.save_geojson(output_dir=output_dir, feature_type=feature_type)
    stats = converter._get_stats()
    print(stats)
