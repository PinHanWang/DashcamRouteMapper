import json
import pandas as pd
from pathlib import Path
from datetime import datetime

def convert_single_json_to_csv(json_path: Path, csv_path: Path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    rows = []
    current_filename = "unknown"

    for feature in data['features']:
        geometry = feature['geometry']
        props = feature['properties']

        if geometry['type'] == 'LineString':
            current_filename = props.get('filename', 'unknown')

        elif geometry['type'] == 'Point':
            lon, lat = geometry['coordinates']
            speed = props.get('speed', None)
            azimuth = props.get('azimuth', None)
            dt_raw = props.get('datetime', None)

            # 時間格式轉換為：2025:03:19 10:24:34
            if dt_raw:
                try:
                    dt_obj = datetime.fromisoformat(dt_raw)
                    dt_formatted = dt_obj.strftime("%Y:%m:%d %H:%M:%S")
                except ValueError:
                    dt_formatted = dt_raw  # 如果格式錯誤則保留原始值
            else:
                dt_formatted = None

            rows.append({
                'filename': current_filename,
                'datetime': dt_formatted,
                'lat': lat,
                'lon': lon,
                'speed': speed,
                'azimuth': azimuth
            })

    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')

def convert_all_json_in_folder(input_folder: Path, output_folder: Path):
    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    json_files = list(input_folder.glob("*.geojson"))
    print(f"🔍 找到 {len(json_files)} 個 JSON 檔案。")

    for json_file in json_files:
        output_csv = output_folder / (json_file.stem + ".csv")
        print(f"🔄 轉換中：{json_file.name} ➜ {output_csv.name}")
        convert_single_json_to_csv(json_file, output_csv)

    print("✅ 全部轉換完成！")

# 範例執行（你可以改成你自己的路徑）
if __name__ == "__main__":
    convert_all_json_in_folder(
        input_folder=r"output\20250408",    # 替換為你的 JSON 資料夾路徑
        output_folder=r"output\20250408"    # 替換為輸出 CSV 的資料夾
    )
