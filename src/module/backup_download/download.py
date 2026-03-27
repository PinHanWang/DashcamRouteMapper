#!/usr/bin/env python3
"""
Dawarich 軌跡匯出工具 - 大量資料優化版
適用於幾十萬個點的資料
"""

import requests
import json
from datetime import datetime
from collections import defaultdict
import time
import os


# ============ 設定區 ============
DAWARICH_URL = "http://192.168.61.2:3000"
API_KEY = "a3308a2f19b6d40cdf36ea3e50878b13"
OUTPUT_DIR = "tracks_by_day"

# 效能設定
PER_PAGE = 50           # 每頁點數（建議 20-50）
TIMEOUT = 120           # 每個請求的逾時時間（秒）
RETRY_TIMES = 5         # 重試次數
DELAY_BETWEEN_PAGES = 0.5  # 頁面之間的延遲（秒）

# 進階設定
SAVE_CHECKPOINT = True  # 每 100 頁儲存一次中間結果
CHECKPOINT_FILE = "export_checkpoint.json"
# ===============================


def save_checkpoint(page, points):
    """儲存檢查點"""
    if SAVE_CHECKPOINT:
        checkpoint = {
            'page': page,
            'total_points': len(points),
            'timestamp': datetime.now().isoformat()
        }
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(checkpoint, f)


def load_checkpoint():
    """載入檢查點"""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return None


def get_all_points(base_url, api_key, start_page=1):
    """取得所有軌跡點（支援斷點續傳）"""
    all_points = []
    page = start_page
    headers = {'Authorization': f'Bearer {api_key}'}
    
    print(f"開始取得資料（預估 6860 頁，每頁 {PER_PAGE} 點）...")
    if start_page > 1:
        print(f"從第 {start_page} 頁繼續...")
    
    consecutive_errors = 0
    max_consecutive_errors = 10
    
    start_time = time.time()
    last_report_time = start_time
    
    while True:
        # 每 100 頁顯示一次進度和預估時間
        if page % 100 == 0:
            elapsed = time.time() - start_time
            pages_done = page - start_page + 1
            if pages_done > 0:
                avg_time_per_page = elapsed / pages_done
                remaining_pages = 6860 - page
                eta_seconds = remaining_pages * avg_time_per_page
                eta_minutes = eta_seconds / 60
                
                print(f"\n進度報告：")
                print(f"  目前頁數: {page}/6860 ({page/6860*100:.1f}%)")
                print(f"  已取得點數: {len(all_points):,}")
                print(f"  平均速度: {avg_time_per_page:.2f} 秒/頁")
                print(f"  預估剩餘時間: {eta_minutes:.1f} 分鐘\n")
                
                # 儲存檢查點
                save_checkpoint(page, all_points)
        
        # 一般進度顯示
        if time.time() - last_report_time > 5:  # 每 5 秒更新一次
            print(f"\r正在取得第 {page} 頁... ({len(all_points):,} 個點)", end='', flush=True)
            last_report_time = time.time()
        
        # 重試機制
        success = False
        for retry in range(RETRY_TIMES):
            try:
                response = requests.get(
                    f'{base_url}/api/v1/points',
                    headers=headers,
                    params={'page': page, 'per_page': PER_PAGE},
                    timeout=TIMEOUT
                )
                
                response.raise_for_status()
                points = response.json()
                
                if not points:
                    print(f"\n已到達最後一頁（第 {page} 頁）")
                    return all_points
                
                all_points.extend(points)
                consecutive_errors = 0
                success = True
                
                total_pages = response.headers.get('X-Total-Pages')
                current_page = response.headers.get('X-Current-Page')
                
                if total_pages and int(current_page) >= int(total_pages):
                    print(f"\n完成！總共取得 {len(all_points):,} 個點")
                    return all_points
                
                page += 1
                time.sleep(DELAY_BETWEEN_PAGES)
                break
                
            except requests.exceptions.Timeout:
                if retry < RETRY_TIMES - 1:
                    wait_time = (retry + 1) * 2
                    print(f"\n⚠ 第 {page} 頁逾時，等待 {wait_time} 秒後重試 ({retry + 1}/{RETRY_TIMES})...", end='', flush=True)
                    time.sleep(wait_time)
                else:
                    print(f"\n✗ 第 {page} 頁逾時，已重試 {RETRY_TIMES} 次")
                    consecutive_errors += 1
                    
            except requests.exceptions.HTTPError as e:
                print(f"\n✗ HTTP 錯誤: {e}")
                if e.response.status_code == 401:
                    print("API Key 可能不正確，停止執行")
                    return all_points
                consecutive_errors += 1
                break
                
            except Exception as e:
                print(f"\n✗ 錯誤: {e}")
                consecutive_errors += 1
                break
        
        if not success:
            if consecutive_errors >= max_consecutive_errors:
                print(f"\n連續 {max_consecutive_errors} 次錯誤，停止執行")
                print(f"目前已取得 {len(all_points):,} 個點")
                print(f"可以修改 CHECKPOINT_FILE 從第 {page} 頁繼續")
                save_checkpoint(page, all_points)
                return all_points
    
    print(f"\n完成！總共 {len(all_points):,} 個點")
    return all_points


def group_by_day(points):
    """依日期分組"""
    grouped = defaultdict(list)
    no_time_count = 0
    
    print("\n依日期分組...")
    
    for i, point in enumerate(points):
        if i % 50000 == 0 and i > 0:
            print(f"  已處理 {i:,}/{len(points):,} 個點...")
        
        try:
            if 'tracked_at' in point:
                dt = datetime.fromisoformat(point['tracked_at'].replace('Z', '+00:00'))
            elif 'timestamp' in point:
                dt = datetime.fromtimestamp(point['timestamp'])
            else:
                no_time_count += 1
                continue
            
            date_key = dt.date().isoformat()
            point['_sort_time'] = dt
            grouped[date_key].append(point)
        except Exception as e:
            no_time_count += 1
            continue
    
    # 排序每天的點
    print("  排序各天的軌跡點...")
    for date in grouped:
        grouped[date].sort(key=lambda p: p.get('_sort_time', datetime.min))
    
    if no_time_count > 0:
        print(f"  ⚠ {no_time_count:,} 個點沒有時間資訊，已忽略")
    
    return dict(grouped)


def create_linestring_geojson(points, date):
    """建立 LineString GeoJSON"""
    
    if not points:
        return None
    
    coordinates = []
    
    for point in points:
        lon = point.get('longitude')
        lat = point.get('latitude')
        alt = point.get('altitude')
        
        # 轉換字串座標為浮點數（Dawarich 0.32.0 回傳字串格式）
        try:
            if lon is not None:
                lon = float(lon)
            if lat is not None:
                lat = float(lat)
            if alt is not None:
                alt = float(alt)
        except (ValueError, TypeError):
            continue
        
        if lon is not None and lat is not None:
            if alt is not None:
                coordinates.append([lon, lat, alt])
            else:
                coordinates.append([lon, lat])
    
    # 如果只有一個點，建立 Point
    if len(coordinates) == 0:
        return None
    elif len(coordinates) == 1:
        return {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": coordinates[0]
                },
                "properties": {
                    "date": date,
                    "point_count": 1,
                    "time": points[0].get('tracked_at') or str(points[0].get('timestamp'))
                }
            }]
        }
    else:
        # 多點使用 LineString
        return {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates
                },
                "properties": {
                    "date": date,
                    "point_count": len(coordinates),
                    "start_time": points[0].get('tracked_at') or str(points[0].get('timestamp')),
                    "end_time": points[-1].get('tracked_at') or str(points[-1].get('timestamp'))
                }
            }]
        }


def main():
    """主程式"""
    
    # 檢查設定
    if API_KEY == "your-api-key-here":
        print("錯誤: 請先設定你的 API Key")
        return
    
    print("="*60)
    print("Dawarich 軌跡匯出工具 - 大量資料優化版")
    print("="*60)
    print(f"預估資料量: 6860 頁 × {PER_PAGE} 點 = 343,000 點")
    print(f"預估時間: 約 {6860 * 0.5 / 60:.0f} 分鐘")
    print("="*60 + "\n")
    
    # 建立輸出目錄
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"建立輸出目錄: {OUTPUT_DIR}\n")
    
    # 檢查是否有檢查點
    checkpoint = load_checkpoint()
    start_page = 1
    
    if checkpoint:
        print(f"發現檢查點：")
        print(f"  上次執行到第 {checkpoint['page']} 頁")
        print(f"  已取得 {checkpoint['total_points']:,} 個點")
        print(f"  時間: {checkpoint['timestamp']}")
        
        resume = input("\n要從檢查點繼續嗎？(y/n): ").lower()
        if resume == 'y':
            start_page = checkpoint['page']
    
    # 取得所有點
    start_time = time.time()
    points = get_all_points(DAWARICH_URL, API_KEY, start_page)
    elapsed = time.time() - start_time
    
    if not points:
        print("\n沒有取得任何資料")
        return
    
    print(f"\n資料取得完成！")
    print(f"  總點數: {len(points):,}")
    print(f"  總耗時: {elapsed/60:.1f} 分鐘")
    print(f"  平均速度: {len(points)/elapsed:.0f} 點/秒")
    
    # 依日期分組
    grouped = group_by_day(points)
    print(f"共有 {len(grouped)} 天的資料\n")
    
    # 顯示日期範圍
    dates = sorted(grouped.keys())
    if dates:
        print(f"日期範圍: {dates[0]} ~ {dates[-1]}\n")
    
    # 匯出各天的檔案
    print("開始匯出...\n")
    success = 0
    
    for i, (date, day_points) in enumerate(sorted(grouped.items()), 1):
        if i % 10 == 0:
            print(f"  進度: {i}/{len(grouped)} 天")
        
        filename = os.path.join(OUTPUT_DIR, f"track_{date}.geojson")
        
        valid_coords = sum(1 for p in day_points if p.get('longitude') is not None and p.get('latitude') is not None)
        
        geojson = create_linestring_geojson(day_points, date)
        
        if geojson is None:
            print(f"  ✗ {date}: 無有效座標 (原始 {len(day_points)} 點)")
            continue
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(geojson, f, ensure_ascii=False, indent=2)
            
            geom_type = geojson['features'][0]['geometry']['type']
            if i <= 20 or i % 10 == 0:  # 只顯示前 20 天和每 10 天
                print(f"  ✓ {date}: {valid_coords} 點 ({geom_type})")
            success += 1
        except Exception as e:
            print(f"  ✗ {date}: 失敗 - {e}")
    
    # 清理檢查點檔案
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
    
    print(f"\n{'='*60}")
    print(f"完成！成功匯出 {success} 天的資料")
    print(f"輸出目錄: {OUTPUT_DIR}")
    print(f"總耗時: {(time.time() - start_time)/60:.1f} 分鐘")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()