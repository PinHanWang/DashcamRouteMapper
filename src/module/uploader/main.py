"""
Dawarich 軌跡上傳工具 CLI

使用方式：
    python -m src.module.uploader.main --input path/to/file.geojson
    python -m src.module.uploader.main --help
"""
import argparse
import json
import logging
from pathlib import Path

from src.module.uploader import config as cfg
from src.module.uploader.client import DawarichUploader
from src.module.uploader.parser import (
    analyze_trajectory,
    parse_json_format,
    sort_by_timestamp,
    validate_coordinates,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dawarich 軌跡上傳工具：將 GeoJSON 上傳至 Dawarich",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        required=True,
        help="要上傳的 GeoJSON 檔案路徑",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=cfg.BATCH_SIZE,
        help="每批次上傳點數",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=cfg.REQUEST_TIMEOUT,
        help="API 請求超時時間（秒）",
    )
    parser.add_argument(
        "--no-sort",
        action="store_true",
        default=False,
        help="跳過依時間排序",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        default=False,
        help="跳過座標範圍驗證",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if not args.input.exists():
        logger.error("找不到檔案：%s", args.input)
        return

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    points = parse_json_format(data)
    if not points:
        logger.error("無法解析資料或沒有有效點位")
        return

    logger.info("解析完成：%d 個點位", len(points))

    if not args.no_validate:
        points = validate_coordinates(points)

    if not args.no_sort:
        points = sort_by_timestamp(points)

    logger.info("處理後剩餘 %d 個有效點位", len(points))

    if not points:
        logger.error("沒有有效點位可上傳")
        return

    stats = analyze_trajectory(points)
    logger.info(
        "軌跡資訊：%d 點，%.2f 公里，%s ~ %s",
        stats["total_points"],
        stats["total_distance_km"],
        stats["start_time"],
        stats["end_time"],
    )

    upload_config = {
        "DAWARICH_URL": cfg.DAWARICH_URL,
        "API_KEY": cfg.DAWARICH_API_KEY,
        "BATCH_SIZE": args.batch_size,
        "REQUEST_TIMEOUT": args.timeout,
    }

    with DawarichUploader(upload_config) as uploader:
        if not uploader.test_connection():
            logger.error("無法連線到 Dawarich，請確認 URL 與網路狀態")
            return
        success = uploader.upload_trajectory(points)

    if success:
        logger.info("上傳完成！請至 %s 查看軌跡", cfg.DAWARICH_URL)
    else:
        logger.error("上傳過程中發生錯誤，請查看上方日誌")


if __name__ == "__main__":
    main()
