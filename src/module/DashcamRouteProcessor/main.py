import os
from pathlib import Path
import glob
from Video2Geojson import Video2GeoJson
from tqdm import tqdm
import geojson
import datetime
from typing import List


class DashcamRouteProcessor:
    def __init__(self):
        pass

    def process(self, video_dir: Path, output_dir: Path, feature_type: str = "point"):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if not os.path.exists(video_dir):
            raise ValueError(f"Video directory {video_dir} does not exist")

        try:
            video_files = self._find_video_files(video_dir)
            if not video_files:
                raise ValueError(f"No video files found in {video_dir}")

            self.convert_video_to_geojson(video_files, output_dir, feature_type)
            self.merge_all_geojson(output_dir)
        except Exception as e:
            print(f"Error processing videos directory: {e}")

    def _find_video_files(self, video_dir: Path) -> List[Path]:
        video_extensions = ['*.mp4', '*.MP4', '*.mov', '*.MOV', '*.avi', '*.AVI']
        video_files = []
        
        for ext in video_extensions:
            pattern = str(video_dir / "**" / ext)
            found_files = glob.glob(pattern, recursive=True)
            video_files.extend(found_files)
        
        return list(set(Path(f) for f in video_files))

    def convert_video_to_geojson(self, video_files, output_dir: Path, feature_type: str = "all"):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for video_file in tqdm(video_files, desc="Converting video information to geojson"):
            try:
                video2geojson = Video2GeoJson(video_file)
                video2geojson.save_geojson(
                    output_dir=output_dir, feature_type=feature_type)
            except Exception as e:
                print(f"Error processing in {video_file}: {e}")

    def merge_all_geojson(self, dir: Path):
        gjson_files = glob.glob(f"{dir}/**/*.geojson", recursive=True)

        all_features = []

        for gjson_file in gjson_files:
            try:
                with open(gjson_file, "r") as f:
                    data = geojson.load(f)
                    all_features.extend(data["features"])
            except Exception as e:
                print(f"Error reading {gjson_file}: {e}")

        combined_feature_collection = geojson.FeatureCollection(all_features)

        merged_geojson_path = os.path.join(
            dir, f"{datetime.datetime.now().strftime('%Y%m%d')}.geojson")
        try:
            with open(merged_geojson_path, "w") as f:
                geojson.dump(combined_feature_collection, f, indent=2)
        except Exception as e:
            print(f"Error writing combined geojson: {e}")
            return

        print(f"Combined geojson saved to {merged_geojson_path}")




def main():
    dir = Path(r'H:\DCIM\Movie')
    outptut_dir = Path(r'H:\DCIM\Movie\gjson')
    processor = DashcamRouteProcessor()
    processor.process(dir, outptut_dir, feature_type="all")

if __name__ == "__main__":
    main()
