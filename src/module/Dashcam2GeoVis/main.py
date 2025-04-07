import os
from pathlib import Path
import glob
from video2geojson import Video2GeoJson, PanoramaVideo2GeoJson
from tqdm import tqdm
import geojson
import datetime


def merge_all_geojson(dir: Path):
    geojson_files = glob.glob(f"{dir}/**/*.geojson", recursive=True)

    all_faetures = []

    for geojson_file in geojson_files:
        with open(geojson_file, "r") as f:
            data = geojson.load(f)
            all_faetures.extend(data["features"])
    
    combined_feature_collection = geojson.FeatureCollection(all_faetures)

    with open(os.path.join(dir, f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.geojson"), "w") as f:
        geojson.dump(combined_feature_collection, f, indent=2)

    print(f"Combined geojson saved to {os.path.join(dir, 'combined.geojson')}")

def convert_video_to_geojson(video_dir: Path, output_dir: Path):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    mp4_files = [Path(x) for x in glob.glob(f"{video_dir}/**/*.mp4", recursive=True)]
    

    
    for mp4_file in tqdm(mp4_files, desc="Converting video information to geojson"):
        
        if os.path.exists(os.path.join(video_dir, mp4_file.stem + ".gpx")):
            try:
                pano2geojson = PanoramaVideo2GeoJson(mp4_file, os.path.join(video_dir, mp4_file.stem + ".gpx"))
                pano2geojson.save_geojson(output_dir=output_dir)
            except Exception as e:
                print(f"Error processing in {mp4_file}: {e}")
        else:
            try:
                video2geojson = Video2GeoJson(mp4_file)
                video2geojson.save_geojson(output_dir=output_dir)
            except Exception as e:
                print(f"Error processing in {mp4_file}: {e}")
                
    merge_all_geojson(outptut_dir)


if __name__ == "__main__":
    dir = Path(r'data\raw\insta360')
    outptut_dir = Path(r'output\insta360')
    convert_video_to_geojson(dir, outptut_dir)

    
