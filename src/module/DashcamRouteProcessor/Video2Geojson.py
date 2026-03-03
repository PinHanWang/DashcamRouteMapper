import pandas as pd
from pathlib import Path
import geojson
import os
from typing import List, Tuple
from geojson import Point, LineString, Feature, FeatureCollection  
import sys
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from utlis.makeExif import makeExifDf
import re
from geopy.distance import geodesic
from datetime import datetime


class Video2GeoJson:
    def __init__(self, video_path: Path) -> None:
        self.video_path = Path(video_path)
        try:
            self.df = makeExifDf(video_path, [])
        except Exception as e:
            raise ValueError(
                f"Error reading video metadata, no GPS data found: {e}")

    def create_point_feature(self):
        point_feartures = []
        for _, row in self.df.iterrows():
            point = Point((row["lon"], row["lat"]))
            datetime_str = re.sub(
                r"(\d{4}):(\d{2}):(\d{2})", r"\1-\2-\3", row["datetime"])
            dt_obj = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            timestamp = int(dt_obj.timestamp())
            properties = {
                "timestamp": timestamp
                # "datetime": dt_obj.isoformat() + 'Z',
                # "speed": row["speed"],
                # "azimuth": row["azimuth"],
            }
            point_feature = Feature(geometry=point, properties=properties)
            point_feartures.append(point_feature)

        return point_feartures

    def create_line_feature(self):
        line_coordinates = list(zip(self.df["lon"], self.df["lat"]))

        # Calculate the total distance of the line
        total_distance = self.calculate_distance(line_coordinates)
        starttime_str = re.sub(
            r"(\d{4}):(\d{2}):(\d{2})", r"\1-\2-\3", self.df["datetime"].iloc[0])
        endtime_str = re.sub(r"(\d{4}):(\d{2}):(\d{2})",
                             r"\1-\2-\3", self.df["datetime"].iloc[-1])
        starttime_obj = datetime.strptime(starttime_str, "%Y-%m-%d %H:%M:%S")
        endtime_obj = datetime.strptime(endtime_str, "%Y-%m-%d %H:%M:%S")
        line_properties = {
            "filename": self.df["filename"].iloc[0],
            "starttime": starttime_obj.isoformat(),
            "endtime": endtime_obj.isoformat(),
            "length(m)": round(total_distance, 3),  # meters
        }

        line_feature = Feature(geometry=LineString(
            line_coordinates), properties=line_properties)

        return line_feature

    def create_feature_collection(self, feature_type="all"):

        feature_collection = []
        if feature_type == "all":
            try:
                line_features = self.create_line_feature()
                feature_collection.append(line_features)
            except Exception as e:
                pass

            try:
                point_features = self.create_point_feature()
                feature_collection.extend(point_features)
            except Exception as e:
                pass

        elif feature_type == "point":
            try:
                point_features = self.create_point_feature()
                feature_collection.extend(point_features)
            except Exception as e:
                pass

        elif feature_type == "line":
            try:
                line_features = self.create_line_feature()
                feature_collection.append(line_features)
            except Exception as e:
                pass
        else:
            raise ValueError("Invalid type. Choose 'all', 'point', or 'line'.")

        return FeatureCollection(features=feature_collection)

    def save_geojson(self, output_dir: Path,  feature_type: str = "all"):

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        feature_collection = self.create_feature_collection(feature_type)

        output_path = os.path.join(
            output_dir, f"{self.video_path.stem}.geojson")

        with open(output_path, "w") as f:
            geojson.dump(feature_collection, f, indent=2)

        # print(f"Geojson saved to {output_path}")

    def _calculate_distance(self, coordinates: List[Tuple[float, float]]) -> float:
        if len(coordinates) < 2:
            return 0.0
        
        total_distance = 0.0
        for i in range(len(coordinates) - 1):
            point1 = (coordinates[i][1], coordinates[i][0])
            point2 = (coordinates[i + 1][1], coordinates[i + 1][0])
            
            try:
                distance = geodesic(point1, point2).meters
                total_distance += distance
            except Exception:
                continue
        
        return total_distance

    def _get_stats(self) -> dict:
        stats = {}
        coordinates = list(zip(self.df["lon"], self.df["lat"]))

        try:
            stats['Num_points'] = len(self.df)
            stats['Start_time'] = self.df['datetime'].min()
            stats['End_time'] = self.df['datetime'].max()
            stats['Duration_sec'] = (datetime.strptime(stats['End_time'], "%Y:%m:%d %H:%M:%S") - datetime.strptime(stats['Start_time'], "%Y:%m:%d %H:%M:%S")).total_seconds() 
            stats['Total_distance_m'] = self._calculate_distance(
                list(zip(self.df["lon"], self.df["lat"])))
            stats['Boundary'] = {
                'min_lon': self.df['lon'].min(),
                'max_lon': self.df['lon'].max(),
                'min_lat': self.df['lat'].min(),
                'max_lat': self.df['lat'].max(),
            }
        except Exception as e:
            print(f"Error calculating stats: {e}")
        
        return stats

# class PanoramaVideo2GeoJson:
#     def __init__(self, video_path: Path, gpx_path: Path) -> None:
#         self.video_path = Path(video_path)
#         self.gpx_path = Path(gpx_path)
#         self.track_pts = GPXProcessor(gpx_path).read_gpx()
#         self.df = pd.DataFrame(self.track_pts)

#     def create_point_feature(self):
#         point_feartures = []
#         for _, row in self.df.iterrows():
#             point = Point((row["lon"], row["lat"]))
#             properties = {
#                 "datetime": row["time"].strftime("%Y-%m-%d %H:%M:%S"),
#                 "elevation": row["ele"],
#             }
#             point_feature = Feature(geometry=point, properties=properties)
#             point_feartures.append(point_feature)

#         return point_feartures

#     def create_line_feature(self):
#         line_coordinates = list(zip(self.df["lon"], self.df["lat"]))

#         # Calculate the total distance of the line
#         total_distance = self.calculate_distance(line_coordinates)

#         line_properties = {
#             "filename": self.video_path.stem,
#             "starttime": self.df["time"].iloc[0].strftime("%Y-%m-%d %H:%M:%S"),
#             "endtime": self.df["time"].iloc[-1].strftime("%Y-%m-%d %H:%M:%S"),
#             "length(m)": round(total_distance, 3),  # meters
#         }

#         line_feature = Feature(geometry=LineString(
#             line_coordinates), properties=line_properties)

#         return line_feature

#     def create_feature_collection(self):
#         point_features = self.create_point_feature()
#         line_feature = self.create_line_feature()

#         feature_collection = FeatureCollection(
#             features=[line_feature] + point_features
#         )

#         return feature_collection

#     def save_geojson(self, output_dir: Path):
#         feature_collection = self.create_feature_collection()
#         output_path = os.path.join(
#             output_dir, f"{self.video_path.stem}.geojson")
#         with open(output_path, "w") as f:
#             geojson.dump(feature_collection, f, indent=2)

#     def calculate_distance(self, line_coordinates):
#         total_distance = 0.0
#         for i in range(len(line_coordinates) - 1):
#             point1 = (line_coordinates[i][1], line_coordinates[i][0])
#             point2 = (line_coordinates[i + 1][1], line_coordinates[i + 1][0])
#             distance = geodesic(point1, point2).meters
#             total_distance += distance
#         return total_distance


def main():
    video_path = Path(r"M:\DCIM\Movie\20251015121134_000025A.MP4")
    video2geojson = Video2GeoJson(video_path)
    video2geojson.save_geojson(output_dir=Path(r"H:\DCIM\Movie\output"), feature_type="point")
    stats = video2geojson._get_stats()
    print(stats)


if __name__ == "__main__":
    main()