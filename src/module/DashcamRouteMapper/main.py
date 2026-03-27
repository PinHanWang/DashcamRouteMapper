"""
DashcamRouteMapper 批次處理入口

使用方式：
    python -m src.module.DashcamRouteMapper.main --help

    # 使用 config.py 預設路徑
    python -m src.module.DashcamRouteMapper.main

    # 指定路徑（4 個 worker 平行處理）
    python -m src.module.DashcamRouteMapper.main \\
        --input M:/DCIM/Movie \\
        --output E:/output/1015 \\
        --type point \\
        --workers 4
"""
import argparse
import datetime
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional

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
        max_workers: int = 4,
    ) -> None:
        """
        掃描 video_dir 下所有影片，轉換為 GeoJSON 後合併輸出至 output_dir。

        Args:
            video_dir:    輸入影片資料夾
            output_dir:   GeoJSON 輸出資料夾
            feature_type: 'all' | 'point' | 'line'
            max_workers:  平行處理的 thread 數量
        """
        os.makedirs(output_dir, exist_ok=True)

        if not video_dir.exists():
            raise ValueError(f"影片資料夾不存在：{video_dir}")

        try:
            video_files = self._find_video_files(video_dir)
            if not video_files:
                raise ValueError(f"在 {video_dir} 找不到任何影片檔案")

            self.convert_video_to_geojson(video_files, output_dir, feature_type, max_workers)
            self.merge_all_geojson(output_dir)
        except Exception as e:
            logger.error("批次處理失敗：%s", e)

    def _find_video_files(self, video_dir: Path) -> List[Path]:
        """遞迴尋找目錄下所有影片檔案（大小寫不敏感去重）"""
        found = set()
        result = []
        for p in video_dir.rglob("*"):
            if p.suffix.lower() in {".mp4", ".mov", ".avi"} and p.stat().st_size > 0:
                # 用 resolve() 規範化路徑，避免大小寫重複
                canonical = p.resolve()
                if canonical not in found:
                    found.add(canonical)
                    result.append(p)
        return result

    def convert_video_to_geojson(
        self,
        video_files: List[Path],
        output_dir: Path,
        feature_type: str = "all",
        max_workers: int = 4,
    ) -> None:
        """
        平行轉換影片為 GeoJSON（ThreadPoolExecutor）。
        exiftool 呼叫為 I/O 密集，多 thread 可有效縮短整體等待時間。
        """
        os.makedirs(output_dir, exist_ok=True)

        def _convert_one(video_file: Path) -> tuple[Path, Optional[Exception]]:
            try:
                converter = Video2GeoJson(video_file)
                converter.save_geojson(output_dir=output_dir, feature_type=feature_type)
                return video_file, None
            except Exception as e:
                return video_file, e

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_convert_one, f): f for f in video_files}
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc=f"轉換影片 → GeoJSON（{max_workers} workers）",
            ):
                video_file, error = future.result()
                if error:
                    logger.warning("處理 %s 失敗：%s", video_file, error)

    def merge_all_geojson(self, directory: Path) -> None:
        """
        合併 directory 內的個別影片 GeoJSON 為單一時間戳記檔案。
        合併結果輸出至 directory/merged/ 子目錄，避免重複執行時舊合併檔被再次納入。
        """
        # 只掃描 directory 頂層的 .geojson（個別影片輸出），不遞迴避免納入舊合併檔
        gjson_files = list(directory.glob("*.geojson"))

        all_features = []
        for gjson_file in gjson_files:
            try:
                with open(gjson_file, "r", encoding="utf-8") as f:
                    data = geojson.load(f)
                    all_features.extend(data["features"])
            except Exception as e:
                logger.warning("讀取 %s 失敗：%s", gjson_file, e)

        combined = geojson.FeatureCollection(all_features)
        merged_dir = directory / "merged"
        merged_dir.mkdir(exist_ok=True)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        merged_path = merged_dir / f"{timestamp}.geojson"

        try:
            with open(merged_path, "w", encoding="utf-8") as f:
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
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=4,
        help="平行處理的 thread 數量（建議設為 CPU 核心數）",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    logger.info("輸入：%s", args.input)
    logger.info("輸出：%s", args.output)
    logger.info("類型：%s", args.type)
    logger.info("Workers：%s", args.workers)

    processor = DashcamRouteProcessor()
    processor.process(
        video_dir=args.input,
        output_dir=args.output,
        feature_type=args.type,
        max_workers=args.workers,
    )


if __name__ == "__main__":
    main()
