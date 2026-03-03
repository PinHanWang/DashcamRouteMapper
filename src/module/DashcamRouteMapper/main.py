"""
DashcamRouteMapper 批次處理入口

使用方式：
    python -m src.module.DashcamRouteMapper.main --help

    # 使用 config.py 預設路徑
    python -m src.module.DashcamRouteMapper.main

    # 指定路徑
    python -m src.module.DashcamRouteMapper.main \\
        --input M:/DCIM/Movie \\
        --output E:/output/1015 \\
        --type point
"""
import argparse
import datetime
import glob
import logging
import os
from pathlib import Path
from typing import List

import geojson
from tqdm import tqdm

from src.module.DashcamRouteMapper.config import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR
from src.module.DashcamRouteMapper.video2geojson import Video2GeoJson

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class DashcamRouteProcessor:
    def process(
        self,
        video_dir: Path,
        output_dir: Path,
        feature_type: str = "point",
    ) -> None:
        """
        掃描 video_dir 下所有影片，轉換為 GeoJSON 後合併輸出至 output_dir。

        Args:
            video_dir:    輸入影片資料夾
            output_dir:   GeoJSON 輸出資料夾
            feature_type: 'all' | 'point' | 'line'
        """
        os.makedirs(output_dir, exist_ok=True)

        if not video_dir.exists():
            raise ValueError(f"影片資料夾不存在：{video_dir}")

        try:
            video_files = self._find_video_files(video_dir)
            if not video_files:
                raise ValueError(f"在 {video_dir} 找不到任何影片檔案")

            self.convert_video_to_geojson(video_files, output_dir, feature_type)
            self.merge_all_geojson(output_dir)
        except Exception as e:
            logger.error("批次處理失敗：%s", e)

    def _find_video_files(self, video_dir: Path) -> List[Path]:
        """遞迴尋找目錄下所有影片檔案"""
        video_extensions = ['*.mp4', '*.MP4', '*.mov', '*.MOV', '*.avi', '*.AVI']
        video_files = []
        for ext in video_extensions:
            pattern = str(video_dir / "**" / ext)
            found = glob.glob(pattern, recursive=True)
            video_files.extend(found)
        return list(set(Path(f) for f in video_files))

    def convert_video_to_geojson(
        self,
        video_files: List[Path],
        output_dir: Path,
        feature_type: str = "all",
    ) -> None:
        """逐一轉換影片為 GeoJSON"""
        os.makedirs(output_dir, exist_ok=True)

        for video_file in tqdm(video_files, desc="轉換影片 → GeoJSON"):
            try:
                converter = Video2GeoJson(video_file)
                converter.save_geojson(output_dir=output_dir, feature_type=feature_type)
            except Exception as e:
                logger.warning("處理 %s 失敗：%s", video_file, e)

    def merge_all_geojson(self, directory: Path) -> None:
        """合併資料夾內所有 GeoJSON 為單一時間戳記檔案"""
        gjson_files = glob.glob(f"{directory}/**/*.geojson", recursive=True)

        all_features = []
        for gjson_file in gjson_files:
            try:
                with open(gjson_file, "r") as f:
                    data = geojson.load(f)
                    all_features.extend(data["features"])
            except Exception as e:
                logger.warning("讀取 %s 失敗：%s", gjson_file, e)

        combined = geojson.FeatureCollection(all_features)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        merged_path = directory / f"{timestamp}.geojson"

        try:
            with open(merged_path, "w") as f:
                geojson.dump(combined, f, indent=2)
            logger.info("合併 GeoJSON 已儲存至 %s", merged_path)
        except Exception as e:
            logger.error("寫入合併 GeoJSON 失敗：%s", e)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="DashcamRouteMapper：批次將行車記錄器影片轉換為 GeoJSON 軌跡",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="輸入影片資料夾路徑",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="GeoJSON 輸出資料夾路徑",
    )
    parser.add_argument(
        "--type", "-t",
        choices=["all", "point", "line"],
        default="point",
        help="GeoJSON Feature 類型",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    logger.info("輸入：%s", args.input)
    logger.info("輸出：%s", args.output)
    logger.info("類型：%s", args.type)

    processor = DashcamRouteProcessor()
    processor.process(
        video_dir=args.input,
        output_dir=args.output,
        feature_type=args.type,
    )


if __name__ == "__main__":
    main()
