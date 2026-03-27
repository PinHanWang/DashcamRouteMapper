#!/usr/bin/env python3
"""快速檢查 Dawarich 資料結構"""

import requests
import json

DAWARICH_URL = "http://192.168.61.2:3000"
API_KEY = "a3308a2f19b6d40cdf36ea3e50878b13"  # 請改成你的 API Key

headers = {'Authorization': f'Bearer {API_KEY}'}

print("取得第一個點...")
response = requests.get(
    f'{DAWARICH_URL}/api/v1/points',
    headers=headers,
    params={'page': 1, 'per_page': 1},
    timeout=30
)

points = response.json()

if points:
    print("\n完整資料結構：")
    print("="*60)
    print(json.dumps(points[0], indent=2, ensure_ascii=False))
    print("="*60)
    
    print("\n關鍵欄位檢查：")
    point = points[0]
    print(f"latitude:  {point.get('latitude')}")
    print(f"longitude: {point.get('longitude')}")
    print(f"tracked_at: {point.get('tracked_at')}")
    print(f"timestamp: {point.get('timestamp')}")
    
    print("\n所有可用欄位：")
    for key in sorted(point.keys()):
        value = point.get(key)
        if value is not None:
            # 截斷過長的值
            str_value = str(value)
            if len(str_value) > 50:
                str_value = str_value[:50] + "..."
            print(f"  {key}: {str_value}")
else:
    print("沒有資料")