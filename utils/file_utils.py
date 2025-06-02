"""
檔案處理工具函數
"""
import os
import shutil
from datetime import datetime, timedelta
from typing import Set, List

def allowed_file(filename: str, allowed_extensions: Set[str]) -> bool:
    """檢查檔案是否為允許的格式"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def is_valid_job(job: dict) -> bool:
    """檢查是否為有效的工作資訊"""
    invalid_jobs = ['未識別到工作資訊', '未設置Gemini API密鑰', '圖片不存在', '獲取描述時出錯', '不詳']
    
    # 首先檢查工作名稱是否有效
    if not job.get('工作') or job.get('工作') in invalid_jobs:
        return False
    
    # 檢查主要欄位中有多少個是"無資訊"
    main_fields = ['工作', '行業', '時間', '薪資', '地點', '聯絡方式']
    no_info_count = 0
    
    for field in main_fields:
        field_value = job.get(field, '')
        if field_value == '無資訊' or field_value == '':
            no_info_count += 1
    
    # 如果有4個或更多欄位是"無資訊"，則認為是無效工作
    if no_info_count >= 4:
        return False
    
    return True

def get_storage_info(results_folder: str) -> dict:
    """獲取存儲使用情況"""
    total_files = 0
    total_size = 0
    
    if os.path.exists(results_folder):
        for root, dirs, files in os.walk(results_folder):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.exists(file_path):
                    total_files += 1
                    total_size += os.path.getsize(file_path)
    
    return {
        'total_files': total_files,
        'total_size_mb': round(total_size / (1024 * 1024), 2)
    }

def cleanup_by_count(results_folder: str, max_count: int = 3) -> List[str]:
    """
    限制 results 資料夾中的檔案數量，如果超過 max_count 就刪除最舊的檔案
    
    Args:
        results_folder: 結果資料夾路徑
        max_count: 最大保留檔案數量
        
    Returns:
        被刪除的 process_id 列表
    """
    removed_process_ids = []
    
    if not os.path.exists(results_folder):
        return removed_process_ids
    
    # 獲取所有子資料夾（每個代表一個 process_id）
    process_dirs = []
    for item in os.listdir(results_folder):
        item_path = os.path.join(results_folder, item)
        if os.path.isdir(item_path):
            # 獲取資料夾的創建時間
            ctime = os.path.getctime(item_path)
            process_dirs.append((item, item_path, ctime))
    
    # 如果檔案數量不超過限制，不需要清理
    if len(process_dirs) <= max_count:
        print(f"Results 資料夾中有 {len(process_dirs)} 個檔案，未超過限制 {max_count}")
        return removed_process_ids
    
    # 按創建時間排序（最舊的在前面）
    process_dirs.sort(key=lambda x: x[2])
    
    # 計算需要刪除的檔案數量
    files_to_remove = len(process_dirs) - max_count
    
    print(f"Results 資料夾中有 {len(process_dirs)} 個檔案，超過限制 {max_count}，將刪除最舊的 {files_to_remove} 個檔案")
    
    # 刪除最舊的檔案
    for i in range(files_to_remove):
        process_id, item_path, ctime = process_dirs[i]
        try:
            shutil.rmtree(item_path)
            removed_process_ids.append(process_id)
            created_time = datetime.fromtimestamp(ctime).strftime('%Y-%m-%d %H:%M:%S')
            print(f"已刪除最舊的檔案: {process_id} (創建時間: {created_time})")
        except Exception as e:
            print(f"刪除檔案 {process_id} 時發生錯誤: {str(e)}")
    
    return removed_process_ids

def cleanup_old_files(upload_folder: str, results_folder: str, max_age_hours: int = 4) -> None:
    """清理超過指定時間的檔案"""
    import time
    
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    cutoff_timestamp = cutoff_time.timestamp()
    
    print(f"開始清理超過 {max_age_hours} 小時的檔案...")
    
    # 清理上傳目錄
    if os.path.exists(upload_folder):
        for item in os.listdir(upload_folder):
            item_path = os.path.join(upload_folder, item)
            if os.path.isdir(item_path) and os.path.getctime(item_path) < cutoff_timestamp:
                shutil.rmtree(item_path)
                print(f"清理上傳目錄: {item_path}")
    
    # 清理結果目錄
    if os.path.exists(results_folder):
        for item in os.listdir(results_folder):
            item_path = os.path.join(results_folder, item)
            if os.path.isdir(item_path) and os.path.getctime(item_path) < cutoff_timestamp:
                shutil.rmtree(item_path)
                print(f"清理結果目錄: {item_path}")
                
                # 返回被清理的 process_id，供調用者清理記憶體存儲
                return item
    
    return None

def get_page_sort_key(page_str: str) -> tuple:
    """處理不同格式的頁碼字符串，返回可排序的元組"""
    try:
        # 如果是純數字，直接轉換
        return (0, int(page_str))
    except ValueError:
        # 如果包含文字，嘗試解析
        if 'file' in page_str and '_page' in page_str:
            # 格式：file01_page1
            parts = page_str.split('_page')
            file_part = parts[0]  # file01
            page_part = parts[1] if len(parts) > 1 else '1'
            
            # 提取檔案編號
            file_num = 0
            if 'file' in file_part:
                try:
                    file_num = int(file_part.replace('file', ''))
                except ValueError:
                    file_num = 0
            
            # 提取頁碼
            try:
                page_num = int(page_part)
            except ValueError:
                page_num = 1
            
            return (file_num, page_num)
        elif 'file' in page_str:
            # 格式：file01
            try:
                file_num = int(page_str.replace('file', ''))
                return (file_num, 0)  # 單頁圖片，頁碼為0
            except ValueError:
                return (999, 0)  # 無法解析的放在最後
        else:
            # 其他格式，嘗試提取數字
            import re
            numbers = re.findall(r'\d+', page_str)
            if numbers:
                return (0, int(numbers[0]))
            else:
                return (999, 999)  # 無法解析的放在最後 