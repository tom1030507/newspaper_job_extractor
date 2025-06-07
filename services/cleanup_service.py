"""
檔案清理服務
"""
from config import Config
from utils.file_utils import cleanup_by_count
from models.storage import ImageStorage
from services.progress_tracker import ProgressTracker

class CleanupService:
    """檔案和記憶體清理服務"""

    def __init__(self, image_storage: ImageStorage, progress_tracker: ProgressTracker):
        self.image_storage = image_storage
        self.progress_tracker = progress_tracker

    def cleanup_memory_storage(self, process_id: str):
        """清理與 process_id 相關的記憶體存儲"""
        self.image_storage.remove_process(process_id)
        self.progress_tracker.remove_progress(process_id)
        print(f"清理記憶體資料: {process_id}")

    def cleanup_by_file_count(self, max_count: int = None):
        """
        執行檔案數量限制清理，同時清理記憶體存儲
        
        Args:
            max_count: 最大保留檔案數量，如果為 None 則使用配置中的預設值
        """
        # 檢查是否啟用檔案數量限制清理
        if not Config.CLEANUP_ENABLE_COUNT_LIMIT:
            print("檔案數量限制清理已停用")
            return []
        
        # 使用配置中的預設值
        if max_count is None:
            max_count = Config.CLEANUP_MAX_FILE_COUNT
        
        print(f"執行檔案數量限制清理（最多保留 {max_count} 個檔案）...")
        
        # 執行檔案數量清理
        removed_process_ids = cleanup_by_count(Config.RESULTS_FOLDER, max_count)
        
        # 清理對應的記憶體存儲
        for process_id in removed_process_ids:
            self.cleanup_memory_storage(process_id)
            print(f"已清理檔案和記憶體資料: {process_id}")
        
        if removed_process_ids:
            print(f"總共清理了 {len(removed_process_ids)} 個過期檔案")
        
        return removed_process_ids