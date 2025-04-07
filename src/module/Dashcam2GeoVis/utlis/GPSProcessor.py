import gpxpy
import gpxpy.gpx
import folium
import os
from scipy.interpolate import interp1d
from datetime import datetime, timedelta
import numpy as np


class GPXProcessor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.track_pts = self.read_gpx()

    def read_gpx(self):
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
                                'ele': point.elevation
                            })

                return track_pts

        except Exception as e:
            print(f"Error reading GPX file: {e}")

    def interpolate_gpx(self, frequency = 2):

        if frequency < 1:
            raise ValueError("Frequency must be at least 1")

        if len(self.track_pts) < 2:
            raise ValueError("Track points must be at least 2")
        
        time = [pt['time'].timestamp() for pt in self.track_pts]
        lat = [pt['lat'] for pt in self.track_pts]
        lon = [pt['lon'] for pt in self.track_pts]
        ele = [pt['ele'] for pt in self.track_pts]

        time_interval = 1 / frequency
        new_times = np.arange(time[0], time[-1], time_interval)

        lat_interp = interp1d(time, lat, kind='linear')
        lon_interp = interp1d(time, lon, kind='linear')
        ele_interp = interp1d(time, ele, kind='linear')

        new_datetimes = [datetime.fromtimestamp(t) for t in new_times]
        new_lats = lat_interp(new_times)
        new_lons = lon_interp(new_times)
        new_eles = ele_interp(new_times)

        interpolated_points = [{'time': t, 'lat': l, 'lon': lon, 'ele': ele} 
                            for t, l, lon, ele in zip(new_datetimes, new_lats, new_lons, new_eles)]

        return interpolated_points

    def draw_tracking(self, track_pts, output_file = None):
        map = folium.Map(location=[track_pts[0]['lat'], track_pts[0]['lon']], zoom_start=12)

        for point in track_pts:
            folium.Marker(location=[point['lat'], point['lon']], popup=point['time']).add_to(map)

        map.save(output_file)





if __name__ == "__main__":
    gpx_file_path = r"data\raw\insta360\Guilin_Rd.gpx"
    gpx_processor = GPXProcessor(gpx_file_path)

    original_track_pts = gpx_processor.track_pts
    print(f"Original track points length: {len(original_track_pts)}")
    output_file = os.path.join(r'output', 'original_gpx_tracking.html')
    gpx_processor.draw_tracking(original_track_pts, output_file)


    interpolated_track_pts = gpx_processor.interpolate_gpx(3)
    print(f"Interpolated track points length: {len(interpolated_track_pts)}")
    output_file = os.path.join(r'output', 'interpolated_gpx_tracking.html')
    gpx_processor.draw_tracking(interpolated_track_pts, output_file)




    
