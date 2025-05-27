import geopandas as gpd
import pandas as pd
from datetime import datetime
import os

def to_unix_timestamp(dt):
    if pd.isna(dt):
        return None
    try:
        return int(pd.to_datetime(dt).timestamp())
    except Exception as e:
        print(f"無法轉換 datetime 值：{dt}，錯誤：{e}")
        return None

def process_geojson_file(input_path, output_path):
    try:
        gdf = gpd.read_file(input_path)

        # 過濾出 Point 資料
        gdf = gdf[gdf.geometry.type == 'Point'].copy()
        # print(gdf.head())
        if 'datetime' not in gdf.columns:
            print(f"檔案 {os.path.basename(input_path)} 缺少 'datetime' 欄位，跳過。")
            return

        # 加入 timestamp 欄位
        gdf['timestamp'] = gdf['datetime'].apply(to_unix_timestamp)

        # 移除原本的 datetime 欄位
        gdf = gdf[['geometry', 'timestamp']]

        # 儲存新的 GeoJSON
        gdf.to_file(output_path, driver='GeoJSON')
        print(f"✅ 已處理並儲存：{output_path}")
    except Exception as e:
        print(f"❌ 處理失敗 {input_path}，錯誤：{e}")

def batch_process_geojson(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    for filename in os.listdir(input_folder):
        if filename.lower().endswith('.geojson'):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)
            process_geojson_file(input_path, output_path)

# 🟡 修改這裡為你的資料夾路徑
input_dir = r"D:\MyProject\DashcamRouteMapper\output\20250521"
output_dir = r"D:\MyProject\DashcamRouteMapper\output\20250521_filtered"

batch_process_geojson(input_dir, output_dir)
