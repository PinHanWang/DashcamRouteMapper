import folium
from pathlib import Path



def create_map(geojson_path: Path, output_path: Path):

    MAP = folium.Map(location=[25.0330, 121.5654], zoom_start=12) # Taipei, Taiwan

    folium.GeoJson(geojson_path).add_to(MAP)

    folium.LayerControl().add_to(MAP)

    MAP.save(output_path)



def main():
    geojson_path = r"output\20250319\20250407140747.geojson"
    output_path = r"output\20250319\20250407140747.html"

    create_map(geojson_path, output_path)


if __name__ == "__main__":
    main()