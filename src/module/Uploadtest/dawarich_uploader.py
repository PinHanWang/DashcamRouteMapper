"""
Dawarich 軌跡上傳工具
支援多種 JSON 格式自動解析並上傳到 Dawarich
"""

import json
import requests
import os
from datetime import datetime
from typing import List, Dict, Optional
from math import radians, sin, cos, sqrt, atan2

# ============================================================
# 🔧 配置區域 - 請在此修改你的設定
# ============================================================

CONFIG = {
    # Dawarich 服務設定
    "DAWARICH_URL": "http://192.168.61.2:3000",  # 你的 Dawarich 網址
    "API_KEY": "a3308a2f19b6d40cdf36ea3e50878b13",           # 你的 API Key（從 Dawarich Settings 取得）
    
    # 上傳設定
    "BATCH_SIZE": 100,          # 每批次上傳點數（建議 50-200）
    "REQUEST_TIMEOUT": 30,      # API 請求超時時間（秒）
    
    # JSON 檔案路徑
    "INPUT_JSON_FILE": r"E:\Peter\DashcamRouteMapper\output\20260326\20260327.geojson",  # 要上傳的 JSON 檔案路徑
    
    # 進階設定
    "SORT_BY_TIME": True,       # 是否依時間排序點位
    "VALIDATE_COORDS": True,    # 是否驗證座標有效性
    "SHOW_WARNINGS": True,      # 是否顯示警告訊息
}

# ============================================================
# 📝 JSON 格式解析器
# ============================================================

def parse_json_format(data) -> List[Dict]:
    """
    自動識別並解析不同的 JSON 格式
    
    支援格式：
    1. GeoJSON FeatureCollection
    2. OwnTracks JSON 陣列
    3. Google Takeout Records.json
    4. 簡單的點位陣列
    
    Args:
        data: JSON 資料（dict 或 list）
    
    Returns:
        標準化的點位列表
    """
    points = []
    
    # 格式 1: GeoJSON FeatureCollection
    if isinstance(data, dict) and data.get('type') == 'FeatureCollection':
        print("📋 檢測到 GeoJSON FeatureCollection 格式")
        for feature in data.get('features', []):
            if feature.get('geometry', {}).get('type') == 'Point':
                coords = feature['geometry']['coordinates']
                props = feature.get('properties', {})
                
                point = {
                    'lon': coords[0],
                    'lat': coords[1],
                    'timestamp': props.get('time', props.get('timestamp', '')),
                    'altitude': coords[2] if len(coords) > 2 else props.get('altitude', props.get('ele', 0)),
                    'accuracy': props.get('accuracy', props.get('horizontal_accuracy', 10)),
                    'speed': props.get('speed', props.get('velocity', 0))
                }
                points.append(point)
    
    # 格式 2: OwnTracks JSON 陣列
    elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and data[0].get('_type') == 'location':
        print("📋 檢測到 OwnTracks 格式")
        for item in data:
            point = {
                'lat': item.get('lat'),
                'lon': item.get('lon'),
                'timestamp': item.get('tst'),  # Unix timestamp
                'altitude': item.get('alt', 0),
                'accuracy': item.get('acc', 10),
                'speed': item.get('vel', 0)
            }
            if point['lat'] is not None and point['lon'] is not None:
                points.append(point)
    
    # 格式 3: Google Takeout Records.json
    elif isinstance(data, dict) and 'locations' in data:
        print("📋 檢測到 Google Takeout Records.json 格式")
        for location in data['locations']:
            # Google 使用 E7 格式（乘以 10^7）
            lat = location.get('latitudeE7', 0) / 1e7
            lon = location.get('longitudeE7', 0) / 1e7
            
            # 時間戳記可能是字串或整數（毫秒）
            timestamp = location.get('timestamp', location.get('timestampMs', ''))
            if isinstance(timestamp, str) and timestamp.isdigit():
                timestamp = int(timestamp) / 1000  # 毫秒轉秒
            
            point = {
                'lat': lat,
                'lon': lon,
                'timestamp': timestamp,
                'altitude': location.get('altitude', 0),
                'accuracy': location.get('accuracy', 10),
                'speed': location.get('velocity', 0)
            }
            if lat != 0 and lon != 0:
                points.append(point)
    
    # 格式 4: 簡單的點位陣列
    elif isinstance(data, list) and len(data) > 0:
        print("📋 檢測到簡單陣列格式")
        for item in data:
            if isinstance(item, dict) and 'lat' in item and 'lon' in item:
                point = {
                    'lat': item.get('lat'),
                    'lon': item.get('lon'),
                    'timestamp': item.get('timestamp', item.get('time', item.get('tst', ''))),
                    'altitude': item.get('altitude', item.get('alt', item.get('ele', 0))),
                    'accuracy': item.get('accuracy', item.get('acc', 10)),
                    'speed': item.get('speed', item.get('velocity', item.get('vel', 0)))
                }
                points.append(point)
    
    # 格式 5: GeoJSON LineString 或 MultiLineString
    elif isinstance(data, dict) and data.get('type') == 'Feature':
        geom = data.get('geometry', {})
        geom_type = geom.get('type', '')
        
        if geom_type == 'LineString':
            print("📋 檢測到 GeoJSON LineString 格式")
            coords = geom.get('coordinates', [])
            props = data.get('properties', {})
            
            # LineString 通常沒有個別時間戳記，需要生成
            base_time = datetime.utcnow()
            for i, coord in enumerate(coords):
                point = {
                    'lon': coord[0],
                    'lat': coord[1],
                    'timestamp': (base_time.timestamp() + i * 60),  # 假設每點間隔 1 分鐘
                    'altitude': coord[2] if len(coord) > 2 else 0,
                    'accuracy': 10,
                    'speed': 0
                }
                points.append(point)
    
    return points

# ============================================================
# 🔧 資料處理工具
# ============================================================

def normalize_timestamp(timestamp) -> str:
    """
    將各種時間格式統一轉換為 ISO 8601 格式
    
    Args:
        timestamp: 時間戳記（可能是字串、整數或浮點數）
    
    Returns:
        ISO 8601 格式的時間字串
    """
    if not timestamp:
        return datetime.utcnow().isoformat() + 'Z'
    
    # Unix timestamp (整數或浮點數)
    if isinstance(timestamp, (int, float)):
        return datetime.utcfromtimestamp(timestamp).isoformat() + 'Z'
    
    # 字串格式
    if isinstance(timestamp, str):
        # 如果已經是 ISO 格式
        if 'T' in timestamp:
            if not timestamp.endswith('Z') and '+' not in timestamp:
                return timestamp + 'Z'
            return timestamp
        
        # 如果是純數字字串（Unix timestamp）
        if timestamp.isdigit():
            return datetime.utcfromtimestamp(int(timestamp)).isoformat() + 'Z'
    
    # 預設返回當前時間
    return datetime.utcnow().isoformat() + 'Z'

def validate_coordinates(points: List[Dict], show_warnings: bool = True) -> List[Dict]:
    """
    驗證並過濾無效座標
    
    Args:
        points: 點位列表
        show_warnings: 是否顯示警告
    
    Returns:
        有效的點位列表
    """
    valid_points = []
    invalid_count = 0
    
    for i, point in enumerate(points):
        lat = point.get('lat')
        lon = point.get('lon')
        
        # 檢查座標是否在有效範圍內
        if lat is None or lon is None:
            invalid_count += 1
            continue
        
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            if show_warnings and invalid_count < 5:  # 只顯示前 5 個警告
                print(f"   ⚠️  點位 {i}: 無效座標 ({lat}, {lon})")
            invalid_count += 1
            continue
        
        valid_points.append(point)
    
    if invalid_count > 0 and show_warnings:
        print(f"⚠️  過濾了 {invalid_count} 個無效座標\n")
    
    return valid_points

def sort_by_timestamp(points: List[Dict]) -> List[Dict]:
    """依時間戳記排序點位"""
    return sorted(points, key=lambda p: normalize_timestamp(p.get('timestamp')))

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    使用 Haversine 公式計算兩點間距離
    
    Returns:
        距離（米）
    """
    R = 6371000  # 地球半徑（米）
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

def analyze_trajectory(points: List[Dict], show_warnings: bool = True) -> Dict:
    """
    分析軌跡資訊
    
    Returns:
        軌跡統計資訊
    """
    if not points:
        return {}
    
    # 計算總距離
    total_distance = 0
    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i + 1]
        total_distance += calculate_distance(p1['lat'], p1['lon'], p2['lat'], p2['lon'])
    
    # 檢查時間間隔
    large_gaps = []
    if show_warnings:
        for i in range(len(points) - 1):
            t1 = datetime.fromisoformat(normalize_timestamp(points[i]['timestamp']).replace('Z', '+00:00'))
            t2 = datetime.fromisoformat(normalize_timestamp(points[i+1]['timestamp']).replace('Z', '+00:00'))
            gap = (t2 - t1).total_seconds() / 60  # 轉換為分鐘
            
            if gap > 60:  # 超過 1 小時
                large_gaps.append((i, gap))
    
    start_time = normalize_timestamp(points[0]['timestamp'])
    end_time = normalize_timestamp(points[-1]['timestamp'])
    
    return {
        'total_points': len(points),
        'total_distance_km': total_distance / 1000,
        'start_time': start_time,
        'end_time': end_time,
        'large_gaps': large_gaps
    }

# ============================================================
# 🚀 Dawarich API 客戶端
# ============================================================

class DawarichUploader:
    """Dawarich API 上傳客戶端"""
    
    def __init__(self, config: Dict):
        self.base_url = config['DAWARICH_URL'].rstrip('/')
        self.api_key = config['API_KEY']
        self.batch_size = config['BATCH_SIZE']
        self.timeout = config['REQUEST_TIMEOUT']
        self.session = requests.Session()
    
    def test_connection(self) -> bool:
        """測試 API 連線"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/health",
                timeout=5
            )
            if response.status_code == 200:
                health = response.json()
                print(f"✅ Dawarich 服務正常")
                print(f"   狀態: {health.get('status', 'unknown')}\n")
                return True
            else:
                print(f"❌ Dawarich 服務回應異常: {response.status_code}\n")
                return False
        except Exception as e:
            print(f"❌ 無法連線到 Dawarich: {e}\n")
            return False
    
    def upload_batch(self, points: List[Dict]) -> Dict:
        """
        上傳一批點位
        
        Args:
            points: 點位列表
        
        Returns:
            上傳結果
        """
        endpoint = f"{self.base_url}/api/v1/overland/batches"
        
        # 轉換為 Overland 格式
        locations = []
        for point in points:
            location = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [point["lon"], point["lat"]]
                },
                "properties": {
                    "timestamp": normalize_timestamp(point.get('timestamp')),
                    "altitude": float(point.get("altitude", 0)),
                    "speed": float(point.get("speed", 0)),
                    "horizontal_accuracy": float(point.get("accuracy", 10))
                }
            }
            locations.append(location)
        
        payload = {"locations": locations}
        
        try:
            response = self.session.post(
                endpoint,
                params={"api_key": self.api_key},
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            
            return {
                "success": response.status_code in [200, 201],
                "status_code": response.status_code,
                "message": response.text,
                "points_uploaded": len(points)
            }
        except requests.Timeout:
            return {
                "success": False,
                "status_code": 0,
                "message": "請求超時",
                "points_uploaded": 0
            }
        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "message": str(e),
                "points_uploaded": 0
            }
    
    def upload_trajectory(self, points: List[Dict]) -> bool:
        """
        上傳完整軌跡（自動分批）
        
        Args:
            points: 點位列表
        
        Returns:
            是否全部成功
        """
        if not points:
            print("❌ 沒有點位可上傳")
            return False
        
        total_batches = (len(points) + self.batch_size - 1) // self.batch_size
        success_count = 0
        failed_count = 0
        
        print(f"📤 開始上傳 {len(points)} 個點位（分 {total_batches} 批次）\n")
        
        for i in range(0, len(points), self.batch_size):
            batch = points[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            
            print(f"   批次 {batch_num}/{total_batches}: {len(batch)} 個點位...", end=" ")
            
            result = self.upload_batch(batch)
            
            if result['success']:
                print("✅")
                success_count += len(batch)
            else:
                print(f"❌")
                print(f"      錯誤: {result['message']}")
                failed_count += len(batch)
        
        print(f"\n{'='*60}")
        print(f"📊 上傳結果：")
        print(f"   成功: {success_count} 個點位")
        print(f"   失敗: {failed_count} 個點位")
        print(f"{'='*60}\n")
        
        return failed_count == 0

# ============================================================
# 🎯 主要執行流程
# ============================================================

def main():
    """主程式"""
    
    print("=" * 60)
    print("🚀 Dawarich 軌跡上傳工具")
    print("=" * 60)
    print()
    
    # 步驟 1: 驗證配置
    print("步驟 1: 檢查配置")
    print(f"   Dawarich URL: {CONFIG['DAWARICH_URL']}")
    print(f"   API Key: {CONFIG['API_KEY'][:10]}..." if len(CONFIG['API_KEY']) > 10 else "   ⚠️  請設定 API Key")
    print(f"   輸入檔案: {CONFIG['INPUT_JSON_FILE']}")
    print()
    
    if CONFIG['API_KEY'] == "your_api_key_here":
        print("❌ 錯誤: 請先在程式頂端的 CONFIG 中設定你的 API Key")
        print("   從 Dawarich Settings 頁面取得 API Key 後，修改程式碼中的 API_KEY 變數")
        return
    
    if not os.path.exists(CONFIG['INPUT_JSON_FILE']):
        print(f"❌ 錯誤: 找不到檔案 {CONFIG['INPUT_JSON_FILE']}")
        return
    
    # 步驟 2: 測試連線
    print("步驟 2: 測試 Dawarich 連線")
    uploader = DawarichUploader(CONFIG)
    if not uploader.test_connection():
        print("❌ 無法連線到 Dawarich，請檢查 URL 是否正確")
        return
    
    # 步驟 3: 讀取 JSON 檔案
    print("步驟 3: 讀取 JSON 檔案")
    try:
        with open(CONFIG['INPUT_JSON_FILE'], 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"   ✅ 成功讀取檔案\n")
    except Exception as e:
        print(f"   ❌ 讀取失敗: {e}\n")
        return
    
    # 步驟 4: 解析資料格式
    print("步驟 4: 解析資料格式")
    points = parse_json_format(data)
    
    if not points:
        print("   ❌ 無法解析資料或沒有有效點位\n")
        return
    
    print(f"   ✅ 成功解析 {len(points)} 個點位\n")
    
    # 步驟 5: 資料處理
    print("步驟 5: 資料處理與驗證")
    
    if CONFIG['VALIDATE_COORDS']:
        print("   🔍 驗證座標...")
        points = validate_coordinates(points, CONFIG['SHOW_WARNINGS'])
    
    if CONFIG['SORT_BY_TIME']:
        print("   🔄 依時間排序...")
        points = sort_by_timestamp(points)
    
    print(f"   ✅ 處理後剩餘 {len(points)} 個有效點位\n")
    
    if not points:
        print("❌ 沒有有效的點位可上傳")
        return
    
    # 步驟 6: 分析軌跡
    print("步驟 6: 分析軌跡資訊")
    stats = analyze_trajectory(points, CONFIG['SHOW_WARNINGS'])
    
    print(f"   📍 總點位數: {stats['total_points']}")
    print(f"   📏 總距離: {stats['total_distance_km']:.2f} 公里")
    print(f"   📅 開始時間: {stats['start_time']}")
    print(f"   📅 結束時間: {stats['end_time']}")
    
    if stats.get('large_gaps'):
        print(f"   ⚠️  發現 {len(stats['large_gaps'])} 處時間間隔超過 1 小時")
        print(f"      軌跡可能會在這些位置斷開")
        for idx, gap in stats['large_gaps'][:3]:  # 只顯示前 3 個
            print(f"      - 點位 {idx} 到 {idx+1}: 間隔 {gap:.1f} 分鐘")
    
    print()
    
    # 步驟 7: 確認上傳
    print("步驟 7: 準備上傳")
    print(f"   將上傳 {len(points)} 個點位到 Dawarich")
    
    # 可以在這裡加入確認提示
    # response = input("   確定要上傳嗎？ (y/n): ")
    # if response.lower() != 'y':
    #     print("   ❌ 已取消上傳")
    #     return
    
    print()
    
    # 步驟 8: 上傳
    print("步驟 8: 上傳軌跡")
    success = uploader.upload_trajectory(points)
    
    # 步驟 9: 完成
    if success:
        print("🎉 上傳完成！")
        print()
        print("📊 如何查看軌跡：")
        print(f"   1. 開啟 {CONFIG['DAWARICH_URL']}")
        print(f"   2. 選擇對應的日期範圍")
        print(f"      ({stats['start_time'][:10]} 到 {stats['end_time'][:10]})")
        print(f"   3. 在地圖上啟用 'Lines' 圖層 ⭐")
        print(f"   4. 你會看到完整的軌跡線！")
        print()
    else:
        print("❌ 上傳過程中發生錯誤")
        print("   請檢查錯誤訊息並重試")
        print()

# ============================================================
# 🔥 程式進入點
# ============================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  使用者中斷執行")
    except Exception as e:
        print(f"\n\n❌ 發生未預期的錯誤: {e}")
        import traceback
        traceback.print_exc()