import pandas as pd
from pathlib import Path
import geojson
import os
from geojson import Point, LineString, Feature, FeatureCollection
from utlis.makeExif import makeExifDf
from utlis.GPSProcessor import GPXProcessor
import re
from geopy.distance import geodesic
from datetime import datetime


class Video2GeoJson:
    def __init__(self, video_path: Path) -> None:
        self.video_path = video_path
        self.df = makeExifDf(video_path, [])
        if self.df.empty:
            raise ValueError(f"No GPS data found in video")

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

    def create_feature_collection(self, type="all"):
        if type == "all":
            point_features = self.create_point_feature()
            line_feature = self.create_line_feature()
            feature_collection = FeatureCollection(
                features=[line_feature] + point_features)
            return feature_collection

        elif type == "point":
            point_features = self.create_point_feature()
            feature_collection = FeatureCollection(
                features=point_features
            )
            return feature_collection
        elif type == "line":
            line_feature = self.create_line_feature()
            feature_collection = FeatureCollection(
                features=[line_feature]
            )
            return feature_collection
        else:
            raise ValueError("Invalid type. Choose 'all', 'point', or 'line'.")

    def save_geojson(self, output_dir: Path,  type: str = "all"):
        feature_collection = self.create_feature_collection(type)
        output_path = os.path.join(
            output_dir, f"{self.video_path.stem}.geojson")
        with open(output_path, "w") as f:
            geojson.dump(feature_collection, f, indent=2)

    def calculate_distance(self, line_coordinates):
        total_distance = 0.0
        for i in range(len(line_coordinates) - 1):
            point1 = (line_coordinates[i][1], line_coordinates[i][0])
            point2 = (line_coordinates[i + 1][1], line_coordinates[i + 1][0])
            distance = geodesic(point1, point2).meters
            total_distance += distance
        return total_distance


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


if __name__ == "__main__":
    video_path = Path(r"H:\DCIM\Movie\20250523155419_000036A.MP4")
    video2geojson = Video2GeoJson(video_path)
    video2geojson.save_geojson(output_dir=Path(r"H:\DCIM\Movie\output"))
