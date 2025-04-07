import pandas as pd
from pathlib import Path
import geojson
from pyproj import Transformer
from datetime import datetime
import os
from geojson import Point, LineString, Feature, FeatureCollection
from utlis.makeExif import makeExifDf, saveExifCsv
import re


class Video2GeoJson:
    def __init__(self, video_path: Path) -> None:
        self.video_path = video_path
        self.df = makeExifDf(video_path, [])

    def create_point_feature(self):
        point_feartures = []
        for _, row in self.df.iterrows():
            point = Point((row["lon"], row["lat"]))
            properties = {
                "datetime": re.sub(r"(\d{4}):(\d{2}):(\d{2})", r"\1-\2-\3", row["datetime"]),
                "speed": row["speed"],
                "azimuth": row["azimuth"],
            }
            point_feature = Feature(geometry=point, properties=properties)
            point_feartures.append(point_feature)

        return point_feartures

    def create_line_feature(self):
        line_coordinates = list(zip(self.df["lon"], self.df["lat"]))
        line_properties = {
            "filename": self.df["filename"].iloc[0],
            "starttime": re.sub(r"(\d{4}):(\d{2}):(\d{2})", r"\1-\2-\3", self.df["datetime"].iloc[0]),
            "endtime": re.sub(r"(\d{4}):(\d{2}):(\d{2})", r"\1-\2-\3", self.df["datetime"].iloc[-1]),
        }

        line_feature = Feature(geometry=LineString(
            line_coordinates), properties=line_properties)

        return line_feature

    def create_feature_collection(self):
        point_features = self.create_point_feature()
        line_feature = self.create_line_feature()

        feature_collection = FeatureCollection(
            features=[line_feature] + point_features
        )

        return feature_collection

    def save_geojson(self, output_dir:Path):
        feature_collection = self.create_feature_collection()
        output_path = os.path.join(output_dir, f"{self.video_path.stem}.geojson")
        with open(output_path, "w") as f:
            geojson.dump(feature_collection, f, indent=2)


class PanoramaVideo2GeoJson:
    def __init__(self, video_path: Path, gpx_path: Path) -> None:
        self.video_path = video_path
        self.gpx_path = gpx_path


import subprocess
import json

def read_exif(video_path):
    try:
        # 使用 exiftool 輸出 JSON 格式
        result = subprocess.run(
            ['exiftool', '-j', video_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            print("ExifTool 錯誤訊息：", result.stderr)
            return None

        # 將 JSON 字串轉換成 Python 字典
        exif_data = json.loads(result.stdout)[0]
        return exif_data

    except Exception as e:
        print("讀取 exif 發生錯誤：", e)
        return None



if __name__ == "__main__":
    folder = Path(r"data\raw\insta360")
    name = "Guilin_Rd.mp4"
    
    video_path = os.path.join(folder, name)

    exif_info = read_exif(video_path)
    
    if exif_info:
        with open(os.path.join(folder, f"{name}_exif.json"), "w", encoding="utf-8") as f:

            json.dump(exif_info, f, indent=4, ensure_ascii=False)