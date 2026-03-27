"""
GPX 軌跡讀取、插值與 Folium 視覺化
"""
import logging
from datetime import datetime, timezone
import os

import gpxpy
import gpxpy.gpx
import folium
import numpy as np
from scipy.interpolate import interp1d

logger = logging.getLogger(__name__)


class GPXProcessor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.track_pts = self.read_gpx()

    def read_gpx(self) -> list[dict]:
        """讀取 GPX 檔案，傳回軌跡點清單"""
        try:
            with open(self.file_path, 'r') as f:
                gpx = gpxpy.parse(f)
                track_pts = []
                for track in gpx.tracks:
                    for segment in track.segments:
                        for point in segment.points:
                            track_pts.append({
                                'time': point.time,
                                'lat': point.latitude,
                                'lon': point.longitude,
                                'ele': point.elevation,
                            })
                return track_pts
        except Exception as e:
            logger.error("讀取 GPX 檔案失敗：%s", e)
            return []

    def interpolate_gpx(self, frequency: int = 2) -> list[dict]:
        """
        對 GPX 軌跡點進行線性插值，提高時間解析度。
        frequency：每秒輸出幾個點（預設 2）
        """
        if frequency < 1:
            raise ValueError("frequency 必須 >= 1")
        if len(self.track_pts) < 2:
            raise ValueError("軌跡點數量至少需要 2 個")

        time = [pt['time'].timestamp() for pt in self.track_pts]
        lat = [pt['lat'] for pt in self.track_pts]
        lon = [pt['lon'] for pt in self.track_pts]
        # elevation 為 GPX 選填欄位，None 時以 0.0 替代，避免 interp1d crash
        ele = [pt['ele'] if pt['ele'] is not None else 0.0 for pt in self.track_pts]

        time_interval = 1 / frequency
        new_times = np.arange(time[0], time[-1], time_interval)

        lat_interp = interp1d(time, lat, kind='linear')
        lon_interp = interp1d(time, lon, kind='linear')
        ele_interp = interp1d(time, ele, kind='linear')

        new_datetimes = [datetime.fromtimestamp(t, tz=timezone.utc) for t in new_times]
        new_lats = lat_interp(new_times)
        new_lons = lon_interp(new_times)
        new_eles = ele_interp(new_times)

        # 修正：迴圈變數使用 lo / e，避免與外層 lon / ele 清單遮蔽
        interpolated_points = [
            {'time': t, 'lat': la, 'lon': lo, 'ele': e}
            for t, la, lo, e in zip(new_datetimes, new_lats, new_lons, new_eles)
        ]

        return interpolated_points

    def draw_tracking(self, track_pts: list[dict], output_file: str) -> None:
        """
        將軌跡點繪製成 Folium HTML 地圖並存檔。

        使用 PolyLine 繪製路線 + FastMarkerCluster 聚合標記，
        取代逐點 Marker，大量 GPS 點時 HTML 大小與瀏覽器渲染速度顯著改善。

        output_file 為必填，例如 'output/tracking.html'
        """
        if not track_pts:
            logger.warning("軌跡點為空，略過地圖繪製")
            return

        from folium.plugins import FastMarkerCluster

        coords = [[p['lat'], p['lon']] for p in track_pts]

        m = folium.Map(location=coords[0], zoom_start=12)
        # 軌跡線
        folium.PolyLine(coords, color="blue", weight=2.5, opacity=0.8).add_to(m)
        # 聚合標記（點數多時自動分群，避免瀏覽器渲染過慢）
        FastMarkerCluster(coords).add_to(m)

        m.save(output_file)
        logger.info("地圖已儲存至 %s（%d 點）", output_file, len(track_pts))


if __name__ == "__main__":
    import sys
    from pathlib import Path

    gpx_file = sys.argv[1] if len(sys.argv) > 1 else r"data/raw/insta360/Guilin_Rd.gpx"
    processor = GPXProcessor(gpx_file)

    original_pts = processor.track_pts
    print(f"原始軌跡點數量：{len(original_pts)}")
    os.makedirs("output", exist_ok=True)
    processor.draw_tracking(original_pts, "output/original_gpx_tracking.html")

    interpolated_pts = processor.interpolate_gpx(3)
    print(f"插值後軌跡點數量：{len(interpolated_pts)}")
    processor.draw_tracking(interpolated_pts, "output/interpolated_gpx_tracking.html")
