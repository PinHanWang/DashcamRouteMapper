"""
行車記錄器影片 → GeoJSON 轉換核心模組
"""
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import geojson
from geojson import Feature, FeatureCollection, LineString, Point
from geopy.distance import geodesic

from src.module.DashcamRouteMapper.utils.exif import make_exif_df

logger = logging.getLogger(__name__)


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
        """從每一筆 GPS 記錄建立 Point Feature 清單"""
        point_features = []  # 修正 typo：point_feartures → point_features
        for _, row in self.df.iterrows():
            point = Point((row["lon"], row["lat"]))
            datetime_str = re.sub(
                r"(\d{4}):(\d{2}):(\d{2})", r"\1-\2-\3", row["datetime"]
            )
            dt_obj = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            properties = {
                "datetime": dt_obj.isoformat() + "Z",   # 修正：恢復完整屬性
                "timestamp": int(dt_obj.timestamp()),
                "speed": row.get("speed", ""),
                "azimuth": row.get("azimuth", ""),
            }
            point_feature = Feature(geometry=point, properties=properties)
            point_features.append(point_feature)

        return point_features

    def create_line_feature(self) -> Feature:
        """從所有 GPS 記錄建立 LineString Feature"""
        line_coordinates = list(zip(self.df["lon"], self.df["lat"]))

        total_distance = self._calculate_distance(line_coordinates)  # 修正：統一使用私有方法
        starttime_str = re.sub(
            r"(\d{4}):(\d{2}):(\d{2})", r"\1-\2-\3", self.df["datetime"].iloc[0]
        )
        endtime_str = re.sub(
            r"(\d{4}):(\d{2}):(\d{2})", r"\1-\2-\3", self.df["datetime"].iloc[-1]
        )
        starttime_obj = datetime.strptime(starttime_str, "%Y-%m-%d %H:%M:%S")
        endtime_obj = datetime.strptime(endtime_str, "%Y-%m-%d %H:%M:%S")
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
        os.makedirs(output_dir, exist_ok=True)

        feature_collection = self.create_feature_collection(feature_type)
        output_path = Path(output_dir) / f"{self.video_path.stem}.geojson"

        with open(output_path, "w", encoding="utf-8") as f:
            geojson.dump(feature_collection, f, indent=2)

        logger.info("GeoJSON 已儲存至 %s", output_path)

    def _calculate_distance(self, coordinates: List[Tuple[float, float]]) -> float:
        """計算軌跡總長度（公尺），座標格式為 (lon, lat)"""
        if len(coordinates) < 2:
            return 0.0

        total_distance = 0.0
        for i in range(len(coordinates) - 1):
            point1 = (coordinates[i][1], coordinates[i][0])      # (lat, lon)
            point2 = (coordinates[i + 1][1], coordinates[i + 1][0])
            try:
                total_distance += geodesic(point1, point2).meters
            except Exception as e:
                logger.warning("geodesic 計算失敗（點 %d）：%s", i, e)
                continue

        return total_distance

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
            stats['Total_distance_m'] = self._calculate_distance(
                list(zip(self.df["lon"], self.df["lat"]))
            )
            stats['Boundary'] = {
                'min_lon': self.df['lon'].min(),
                'max_lon': self.df['lon'].max(),
                'min_lat': self.df['lat'].min(),
                'max_lat': self.df['lat'].max(),
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
