"""
Dawarich API 上傳客戶端
使用 context manager 確保 requests.Session 正確關閉。
"""
import logging
from typing import Dict, List

import requests

from src.module.uploader.parser import normalize_timestamp

logger = logging.getLogger(__name__)


class DawarichUploader:
    """
    Dawarich Overland API 批次上傳客戶端。

    建議以 context manager 使用：
        with DawarichUploader(config) as uploader:
            uploader.upload_trajectory(points)
    """

    def __init__(self, config: Dict) -> None:
        self.base_url = config["DAWARICH_URL"].rstrip("/")
        self.api_key = config["API_KEY"]
        self.batch_size = config["BATCH_SIZE"]
        self.timeout = config["REQUEST_TIMEOUT"]
        self.session = requests.Session()

    def __enter__(self) -> "DawarichUploader":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.session.close()

    def test_connection(self) -> bool:
        """測試 Dawarich API 連線是否正常"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/health",
                timeout=5,
            )
            if response.status_code == 200:
                logger.info("Dawarich 連線正常：%s", response.json().get("status", "unknown"))
                return True
            logger.warning("Dawarich 回應異常：HTTP %d", response.status_code)
            return False
        except Exception as e:
            logger.error("無法連線到 Dawarich：%s", e)
            return False

    def upload_batch(self, points: List[Dict]) -> Dict:
        """上傳一批點位至 Dawarich Overland API"""
        locations = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
                "properties": {
                    "timestamp": normalize_timestamp(p.get("timestamp")),
                    "altitude": float(p.get("altitude", 0)),
                    "speed": float(p.get("speed", 0)),
                    "horizontal_accuracy": float(p.get("accuracy", 10)),
                },
            }
            for p in points
        ]

        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/overland/batches",
                params={"api_key": self.api_key},
                json={"locations": locations},
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            return {
                "success": response.status_code in (200, 201),
                "status_code": response.status_code,
                "message": response.text,
                "points_uploaded": len(points),
            }
        except requests.Timeout:
            return {"success": False, "status_code": 0, "message": "請求超時", "points_uploaded": 0}
        except Exception as e:
            return {"success": False, "status_code": 0, "message": str(e), "points_uploaded": 0}

    def upload_trajectory(self, points: List[Dict]) -> bool:
        """上傳完整軌跡（自動分批），回傳是否全部成功"""
        if not points:
            logger.warning("沒有點位可上傳")
            return False

        total_batches = (len(points) + self.batch_size - 1) // self.batch_size
        success_count = 0
        failed_count = 0

        logger.info("開始上傳 %d 個點位（分 %d 批次）", len(points), total_batches)

        for i in range(0, len(points), self.batch_size):
            batch = points[i : i + self.batch_size]
            batch_num = i // self.batch_size + 1
            result = self.upload_batch(batch)

            if result["success"]:
                success_count += len(batch)
                logger.info("批次 %d/%d 上傳成功（%d 點）", batch_num, total_batches, len(batch))
            else:
                failed_count += len(batch)
                logger.error("批次 %d/%d 上傳失敗：%s", batch_num, total_batches, result["message"])

        logger.info("上傳完成：成功 %d 點，失敗 %d 點", success_count, failed_count)
        return failed_count == 0
