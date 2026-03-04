"""
GeoJSON → CSV 轉換工具，含 EPSG:3857 座標欄位
"""
import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.module.DashcamRouteMapper.config import DEFAULT_FPS
from src.module.DashcamRouteMapper.utils.geo import transform_wgs84_to_3857

logger = logging.getLogger(__name__)


def json_to_csv_with_fields(
    input_folder: Path,
    output_folder: Path,
    fps: int = DEFAULT_FPS,
) -> None:
    """
    將 input_folder 內所有 .geojson 轉換為 CSV，輸出至 output_folder。

    Args:
        input_folder:  包含 .geojson 的資料夾
        output_folder: CSV 輸出資料夾
        fps:           影片 FPS（用於計算 frame 欄位，預設讀自 config.DEFAULT_FPS）
    """
    output_folder.mkdir(parents=True, exist_ok=True)

    for json_file in input_folder.glob("*.geojson"):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        features = data.get("features", [])
        rows = []
        filename = json_file.stem
        starttime = ""
        sec_counter = 0  # fallback 計數器（無 datetime 時使用）

        for feature in features:
            geom_type = feature["geometry"]["type"]

            if geom_type == "LineString":
                starttime = feature["properties"].get("starttime", "")
                continue

            if geom_type == "Point":
                props = feature["properties"]
                coords = feature["geometry"]["coordinates"]
                # 修正：GeoJSON 座標可能含第三個元素（altitude），只取 lon/lat
                lon, lat = coords[0], coords[1]

                speed = props.get("speed", "")
                azimuth = props.get("azimuth", "")
                dt = props.get("datetime", "")

                # 修正：優先從 datetime 與 starttime 計算真實秒數，fallback 用計數器
                sec = sec_counter
                if dt and starttime:
                    try:
                        dt_parsed = datetime.fromisoformat(dt.rstrip("Z"))
                        st_parsed = datetime.fromisoformat(starttime)
                        sec = int((dt_parsed - st_parsed).total_seconds())
                    except Exception:
                        sec = sec_counter

                # WGS84 → EPSG:3857（使用共用 geo 工具）
                lon3857, lat3857 = transform_wgs84_to_3857(lon, lat)

                row = {
                    "filename": filename,
                    "starttime": starttime,
                    "datetime": dt,
                    "lat": lat,
                    "lon": lon,
                    "speed": speed,
                    "azimuth": azimuth,
                    "fps": fps,
                    "sec": sec,
                    "frame": sec * fps,
                    "lon3857": lon3857,
                    "lat3857": lat3857,
                }
                rows.append(row)
                sec_counter += 1

        df = pd.DataFrame(rows)

        if not df.empty:
            df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
            df["datetime"] = df["datetime"].dt.strftime("%Y:%m:%d %H:%M:%S")

        output_path = output_folder / f"{filename}.csv"
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info("已輸出：%s", output_path)


if __name__ == "__main__":
    import sys

    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/20250408")
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else input_dir
    json_to_csv_with_fields(input_dir, output_dir)
