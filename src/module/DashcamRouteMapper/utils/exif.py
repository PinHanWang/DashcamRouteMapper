"""
透過 exiftool CLI 從行車記錄器 MP4 提取 EXIF GPS 資料
"""
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from pyproj import Transformer

from src.module.DashcamRouteMapper.config import EXIFTOOL_PATH

logger = logging.getLogger(__name__)

# 模組層級建立一次，避免每筆 GPS 點重建（效能修正）
_wgs84_to_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)


def _get_exif_start_time(p: Path) -> tuple[float, str]:
    """
    取得檔案的 EXIF 資訊並計算出影像的第一秒 GPS 時間。
    影像開始時間(start_date) = 檔案創建時間(create_date) - 影像持續時間(duration)
    檔案創建時間為整個錄影完成後。
    """
    fps, start_date = -1.0, ""
    cmd = f'"{EXIFTOOL_PATH}" -s "{str(p)}" -VideoFrameRate -CreateDate -Duration'
    with os.popen(cmd) as t:
        context = t.read()[:-1]

        if not context or "'exiftool'" in context:
            raise RuntimeError(
                "exiftool 未找到。請安裝 exiftool 並加入系統 PATH，"
                f"或在 config.py 設定 EXIFTOOL_PATH（目前值：{EXIFTOOL_PATH}）"
            )

        lines = [x for x in context.split("\n") if ":" in x]
        if len(lines) < 3:
            raise RuntimeError(
                f"exiftool 輸出格式不符預期，無法解析 FPS/CreateDate/Duration：{context!r}"
            )

        fields = [x.split(":", 1)[1].strip() for x in lines]
        fps = float(fields[0])
        create_date = datetime.strptime(fields[1], "%Y:%m:%d %H:%M:%S")
        if 's' in fields[2]:
            duration = timedelta(seconds=int(float(fields[2].replace(" s", "").strip())))
            start_date = create_date - duration
        else:
            duration = datetime.strptime(fields[2], "%H:%M:%S")
            start_date = create_date - timedelta(
                hours=duration.hour, minutes=duration.minute, seconds=duration.second
            )

    return fps, start_date.strftime("%Y:%m:%d %H:%M:%S")


def _get_exif_extract_embedded_data(p: Path) -> dict:
    """
    取得檔案 EXIF 中的 GPS 詳細資訊（ExtractEmbeddedData），處理後傳回字典。
    """
    def _calculate_gps(s: str) -> float:
        """
        將 EXIF GPS 資訊從 度分秒格式 轉換為 浮點數。
        ex: 23 deg 59' 7.82" N ---> 23.985505555555555
        """
        direction = {"N": 1, "S": -1, "E": 1, "W": -1}
        d = direction[s[-1]]
        role = re.compile(r"[\d.]+")
        result = role.findall(s)
        a, b, c = (float(x) for x in result)
        return d * (a + b / 60 + c / 3600)

    data = {}
    cmd = f'"{EXIFTOOL_PATH}" -ee -T -GPS* "{str(p)}"'
    with os.popen(cmd) as t:
        context = t.read()[:-1]

        if not context or "'exiftool'" in context:
            return data

        cells = context.split("\t")[:-1]
        if len(cells) == 0:
            return data

        data["GPSDateTime"] = [cells[i][:-1] for i in range(0, len(cells), 5)]
        data["GPSLatitude"] = [_calculate_gps(cells[i]) for i in range(1, len(cells), 5)]
        data["GPSLongitude"] = [_calculate_gps(cells[i]) for i in range(2, len(cells), 5)]
        data["GPSSpeed"] = [float(cells[i]) for i in range(3, len(cells), 5)]
        data["GPSTrack"] = [float(cells[i]) for i in range(4, len(cells), 5)]

    if not data:
        logger.warning("MP4 檔案 %s 沒有 GPS 資料", p)
    return data


def _get_df_seconds_difference(start_time: str, date_time: str) -> float:
    """計算 sec：目前時間點距影片開始時間的秒數差"""
    t0 = datetime.strptime(start_time, "%Y:%m:%d %H:%M:%S")
    t1 = datetime.strptime(date_time, "%Y:%m:%d %H:%M:%S")
    return (t1 - t0).total_seconds()


def _get_df_trans_gps(lon: float, lat: float) -> tuple[float, float]:
    """座標轉換：WGS84（EPSG:4326）→ Web Mercator（EPSG:3857）"""
    return _wgs84_to_3857.transform(lon, lat)


def make_exif_df(p: Path, columns: list | None = None) -> pd.DataFrame:
    """
    給定影像路徑及 columns，傳回影像內 GPS 紀錄的 DataFrame。
    若不給定 columns 則輸出所有欄位：
        ["filename", "datetime", "lat", "lon", "speed", "azimuth",
         "starttime", "fps", "sec", "frame", "lat3857", "lon3857"]
    """
    data = _get_exif_extract_embedded_data(p)
    df = pd.DataFrame(data)
    df = df.rename(columns={
        "GPSDateTime": "datetime",
        "GPSLatitude": "lat",
        "GPSLongitude": "lon",
        "GPSSpeed": "speed",
        "GPSTrack": "azimuth",
    })
    fps, start_date = _get_exif_start_time(p)
    df.drop_duplicates(inplace=True)
    if df.empty:
        return df

    df["filename"] = p.stem
    df["starttime"] = start_date
    df["fps"] = fps
    df["sec"] = df["datetime"].map(lambda x: int(_get_df_seconds_difference(start_date, x)))
    df["frame"] = df["sec"].map(lambda x: int(x * fps))
    first_frame = df.loc[df.index[0], "frame"]
    if first_frame < 0:
        df["frame"] = df["frame"] - first_frame
    # 向量化轉換，一次呼叫處理所有點（效能修正：避免每列重建 Transformer）
    lon3857, lat3857 = _wgs84_to_3857.transform(df["lon"].to_numpy(), df["lat"].to_numpy())
    df["lon3857"] = lon3857
    df["lat3857"] = lat3857
    return df[columns] if columns else df


def save_exif_csv(df: pd.DataFrame, out: Path) -> None:
    """將 DataFrame 儲存為 CSV"""
    df.to_csv(out, index=False)
