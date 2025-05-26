import json
import pandas as pd
from pathlib import Path
from pyproj import Transformer
from datetime import datetime

def _getDfTransGps(lon: float, lat: float) -> tuple[float, float]:
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    return transformer.transform(lon, lat)

def json_to_csv_with_fields(input_folder: Path, output_folder: Path):
    output_folder.mkdir(parents=True, exist_ok=True)

    for json_file in input_folder.glob("*.geojson"):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        features = data.get("features", [])

        rows = []
        filename = json_file.stem
        starttime = ""
        sec = 0  # 秒數初始

        for feature in features:
            if feature["geometry"]["type"] == "LineString":
                starttime = feature["properties"].get("starttime", "")
                continue

            if feature["geometry"]["type"] == "Point":
                props = feature["properties"]
                coords = feature["geometry"]["coordinates"]
                lon, lat = coords

                speed = props.get("speed", "")
                azimuth = props.get("azimuth", "")
                dt = props.get("datetime", "")

                # WGS84 to EPSG:3857
                lon3857, lat3857 = _getDfTransGps(lon, lat)

                row = {
                    "filename": filename,
                    "starttime": starttime,
                    "datetime": dt,
                    "lat": lat,
                    "lon": lon,
                    "speed": speed,
                    "azimuth": azimuth,
                    "fps": 60,
                    "sec": sec,
                    "frame": sec * 60,
                    "lon3857": lon3857,
                    "lat3857": lat3857
                }

                rows.append(row)
                sec += 1  # 下一秒

        df = pd.DataFrame(rows)

        # 調整時間格式
        if not df.empty:
            df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
            df["datetime"] = df["datetime"].dt.strftime("%Y:%m:%d %H:%M:%S")

        output_path = output_folder / f"{filename}.csv"
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"已輸出: {output_path}")

# 範例用法：
# json_to_csv_with_fields(Path("input/json_folder"), Path("output/csv_folder"))

# 範例執行（你可以改成你自己的路徑）
if __name__ == "__main__":
    json_to_csv_with_fields(
        input_folder=Path(r"output\20250408"),    # 替換為你的 JSON 資料夾路徑
        output_folder=Path(r"output\20250408")    # 替換為輸出 CSV 的資料夾
    )
