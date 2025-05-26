#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Apps Script 測試腳本

這個腳本可以幫助您測試 Google Apps Script 是否正常工作
在運行此腳本之前，請先設置您的 Google Apps Script URL
"""

import requests
import json
from datetime import datetime

def test_google_apps_script(apps_script_url):
    """測試 Google Apps Script 是否正常工作"""
    
    if not apps_script_url or apps_script_url == 'YOUR_ACTUAL_GOOGLE_APPS_SCRIPT_URL_HERE':
        print("❌ 錯誤：請先設置您的 Google Apps Script URL")
        print("請在此腳本中將 APPS_SCRIPT_URL 變數設置為您的實際 URL")
        return False
    
    print("🔄 正在測試 Google Apps Script...")
    print(f"📍 URL: {apps_script_url}")
    
    # 準備測試資料
    test_payload = {
        'action': 'addJobs',
        'jobs': [
            {
                '工作': '測試職位 - 軟體工程師',
                '行業': '出版影音及資通訊業',
                '時間': '週一至週五 9:00-18:00',
                '薪資': '月薪 45,000-60,000 元',
                '地點': '台北市信義區',
                '聯絡方式': '02-1234-5678',
                '其他': '需具備 Python 程式設計經驗',
                '來源圖片': 'test_image.jpg',
                '頁碼': '1',
                '工作編號': '測試工作 1'
            },
            {
                '工作': '測試職位 - 行政助理',
                '行業': '其他服務業',
                '時間': '週一至週五 8:30-17:30',
                '薪資': '月薪 28,000-35,000 元',
                '地點': '台北市大安區',
                '聯絡方式': '02-5678-9012',
                '其他': '需具備基本電腦操作能力',
                '來源圖片': 'test_image.jpg',
                '頁碼': '1',
                '工作編號': '測試工作 2'
            }
        ],
        'metadata': {
            'process_id': 'test-' + datetime.now().strftime('%Y%m%d-%H%M%S'),
            'total_jobs': 2,
            'timestamp': datetime.now().isoformat(),
            'source': 'test_script'
        }
    }
    
    try:
        print("📤 正在發送測試資料...")
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        response = requests.post(apps_script_url, json=test_payload, headers=headers, timeout=30)
        
        print(f"📊 HTTP 狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print("✅ 成功！Google Apps Script 回應：")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                
                if result.get('success'):
                    print(f"🎉 Google Sheet 創建成功！")
                    if 'spreadsheet_url' in result:
                        print(f"🔗 Google Sheet URL: {result['spreadsheet_url']}")
                        print("📝 請開啟上述連結確認 Google Sheet 是否正確創建")
                    return True
                else:
                    print(f"❌ Google Apps Script 返回錯誤: {result.get('error', '未知錯誤')}")
                    return False
                    
            except json.JSONDecodeError as e:
                print(f"❌ 無法解析回應的 JSON: {e}")
                print(f"原始回應內容: {response.text}")
                return False
        else:
            print(f"❌ HTTP 請求失敗，狀態碼: {response.status_code}")
            print(f"錯誤內容: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ 請求超時，請檢查網路連線或 Google Apps Script 狀態")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 網路請求錯誤: {e}")
        return False
    except Exception as e:
        print(f"❌ 發生未預期的錯誤: {e}")
        return False

def main():
    """主函數"""
    print("🧪 Google Apps Script 測試工具")
    print("=" * 50)
    
    # TODO: 請將下面的 URL 替換為您的實際 Google Apps Script URL
    APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycby1CtTal9kevYOXcNXBowwa3gOrXRoV0WvbcyGmtvhLHJBk7fgZgD5Bdie4AxQY2qTe4A/exec"
    
    # 如果您想測試特定的 URL，可以直接在這裡設置
    # APPS_SCRIPT_URL = "https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec"
    
    success = test_google_apps_script(APPS_SCRIPT_URL)
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 測試完成！Google Apps Script 工作正常")
        print("您現在可以在主系統中使用 Google Spreadsheet 功能了")
    else:
        print("❌ 測試失敗！請檢查以下項目：")
        print("1. Google Apps Script URL 是否正確")
        print("2. Google Apps Script 是否已正確部署")
        print("3. Google Apps Script 的權限設置是否正確")
        print("4. 網路連線是否正常")
        print("\n請參考 GOOGLE_APPS_SCRIPT_SETUP.md 文件進行設置")

if __name__ == "__main__":
    main() 