"""
進度追蹤服務
"""
import time
from typing import Optional
from models.storage import progress_storage

class ProgressTracker:
    """進度追蹤管理類"""
    
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.storage = progress_storage
    
    def update_progress(self, process_id: str, step: str, progress: int, description: str = "") -> None:
        """更新處理進度並通過 SocketIO 發送到前端"""
        
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
        self.storage.update_progress(original_process_id, step, progress, description)
        
        # 通過 SocketIO 發送到前端（使用原始process_id）
        if self.socketio:
            self.socketio.emit('progress_update', {
                'process_id': original_process_id,
                **progress_data
            })
        
        print(f"進度更新 [{original_process_id}]: {step} - {progress}% - {description}")
    
    def get_progress(self, process_id: str) -> Optional[dict]:
        """獲取進度資訊"""
        return self.storage.get_progress(process_id)
    
    def remove_progress(self, process_id: str) -> None:
        """移除進度資訊"""
        self.storage.remove_process(process_id)

# 創建全域進度追蹤器實例（在應用初始化時會重新設置socketio）
progress_tracker = ProgressTracker() 