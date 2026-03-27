"""
集中管理所有可配置值，避免各模組硬編碼
"""
import os
import shutil
from pathlib import Path


def _find_exiftool() -> str:
    """
    自動偵測 exiftool 路徑：
    1. 優先使用系統 PATH（跨平台通用）
    2. Fallback 到 Windows 常見安裝路徑
    """
    if shutil.which("exiftool"):
        return "exiftool"
    # Windows 常見安裝路徑 fallback
    windows_fallback = r'C:\Program Files\ExifTool\exiftool.exe'
    if os.path.exists(windows_fallback):
        return windows_fallback
    # 讓呼叫端自然報錯，方便診斷
    return "exiftool"


# ── ExifTool ──────────────────────────────────────────────────────────────────
EXIFTOOL_PATH: str = _find_exiftool()

# ── 影片 FPS 預設值 ───────────────────────────────────────────────────────────
# 用於 json2csv 計算 frame；優先從影片 EXIF 讀取，無法讀取時 fallback 至此值
DEFAULT_FPS: int = 30

# ── 預設輸入 / 輸出路徑 ────────────────────────────────────────────────────────
# 相對於專案根目錄（DashcamRouteMapper/）
_MODULE_DIR = Path(__file__).parent          # src/module/trajectory/
PROJECT_ROOT = _MODULE_DIR.parent.parent.parent  # DashcamRouteMapper/

DEFAULT_INPUT_DIR: Path = PROJECT_ROOT / "data" / "raw"
DEFAULT_OUTPUT_DIR: Path = PROJECT_ROOT / "output"
