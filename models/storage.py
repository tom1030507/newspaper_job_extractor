"""
數據存儲模型
管理圖片、工作資訊和進度的記憶體存儲
"""
import time
from typing import Dict, List, Any, Optional

class ImageStorage:
    """圖片存儲管理類"""
    
    def __init__(self):
        self._storage: Dict[str, Dict[str, Any]] = {}
    
    def store_image(self, process_id: str, filename: str, image_data: Dict[str, Any]) -> None:
        """存儲圖片數據"""
        if process_id not in self._storage:
            self._storage[process_id] = {}
        self._storage[process_id][filename] = image_data
    
    def get_image(self, process_id: str, filename: str) -> Optional[Dict[str, Any]]:
        """獲取圖片數據"""
        if process_id in self._storage and filename in self._storage[process_id]:
            return self._storage[process_id][filename]
        return None
    
    def get_process_images(self, process_id: str) -> Dict[str, Any]:
        """獲取指定處理ID的所有圖片"""
        return self._storage.get(process_id, {})
    
    def get_related_processes(self, process_id: str) -> List[str]:
        """獲取相關的處理ID（包括頁面和檔案）"""
        related_keys = [key for key in self._storage.keys() 
                       if key == process_id or key.startswith(f"{process_id}_")]
        return related_keys
    
    def remove_process(self, process_id: str) -> None:
        """移除指定處理ID的所有數據"""
        keys_to_remove = []
        for key in self._storage.keys():
            if key == process_id or key.startswith(f"{process_id}_"):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._storage[key]
    
    def list_all_processes(self) -> List[str]:
        """列出所有處理ID"""
        return list(self._storage.keys())
    
    def clear(self) -> None:
        """清空所有存儲"""
        self._storage.clear()

class JobStorage:
    """工作資訊存儲管理類"""
    
    def __init__(self):
        self._storage: Dict[str, List[Dict[str, Any]]] = {}
    
    def store_jobs(self, process_id: str, jobs: List[Dict[str, Any]]) -> None:
        """存儲工作資訊"""
        self._storage[process_id] = jobs
    
    def get_jobs(self, process_id: str) -> List[Dict[str, Any]]:
        """獲取工作資訊"""
        return self._storage.get(process_id, [])
    
    def remove_process(self, process_id: str) -> None:
        """移除指定處理ID的工作資訊"""
        if process_id in self._storage:
            del self._storage[process_id]
    
    def list_all_processes(self) -> List[str]:
        """列出所有處理ID"""
        return list(self._storage.keys())
    
    def clear(self) -> None:
        """清空所有存儲"""
        self._storage.clear()

class ProgressStorage:
    """進度追蹤存儲管理類"""
    
    def __init__(self):
        self._storage: Dict[str, Dict[str, Any]] = {}
    
    def update_progress(self, process_id: str, step: str, progress: int, description: str = "") -> None:
        """更新進度資訊"""
        # 提取原始的 process_id（移除 _page 或 _file 後綴）
        original_process_id = process_id
        if '_page' in process_id:
            original_process_id = process_id.split('_page')[0]
        elif '_file' in process_id:
            original_process_id = process_id.split('_file')[0]
        
        progress_data = {
            'step': step,
            'progress': progress,
            'description': description,
            'timestamp': time.time()
        }
        
        # 儲存進度資訊（使用原始process_id）
        self._storage[original_process_id] = progress_data
    
    def get_progress(self, process_id: str) -> Optional[Dict[str, Any]]:
        """獲取進度資訊"""
        return self._storage.get(process_id)
    
    def remove_process(self, process_id: str) -> None:
        """移除指定處理ID的進度資訊"""
        if process_id in self._storage:
            del self._storage[process_id]
    
    def list_all_processes(self) -> List[str]:
        """列出所有處理ID"""
        return list(self._storage.keys())
    
    def clear(self) -> None:
        """清空所有存儲"""
        self._storage.clear()

# 創建全域存儲實例
image_storage = ImageStorage()
job_storage = JobStorage()
progress_storage = ProgressStorage() 