"""
uploader 設定模組
從 .env 讀取 Dawarich 連線設定，敏感資料不寫入程式碼。
請從專案根目錄執行（python -m src.module...），load_dotenv() 才能正確找到 .env。
"""
import os

from dotenv import load_dotenv

# 從專案根目錄的 .env 載入設定
load_dotenv()

# 必填：未設定直接拋 KeyError，由呼叫端（_run_upload）轉為友善訊息
DAWARICH_URL: str = os.environ["DAWARICH_URL"]
DAWARICH_API_KEY: str = os.environ["DAWARICH_API_KEY"]

# 選填：提供合理預設值
BATCH_SIZE: int = int(os.environ.get("DAWARICH_BATCH_SIZE", "100"))
REQUEST_TIMEOUT: int = int(os.environ.get("DAWARICH_REQUEST_TIMEOUT", "30"))
