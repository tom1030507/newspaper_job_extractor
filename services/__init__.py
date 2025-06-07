"""
服務模組
"""
from models import image_storage
from .progress_tracker import ProgressTracker, progress_tracker
from .ai_service import AIService, ai_service
from .image_processing_service import ImageProcessingService, image_processing_service
from .cleanup_service import CleanupService

# 創建清理服務實例
cleanup_service = CleanupService(image_storage=image_storage, progress_tracker=progress_tracker)

__all__ = [
    'ProgressTracker',
    'progress_tracker',
    'AIService', 
    'ai_service',
    'ImageProcessingService',
    'image_processing_service',
    'CleanupService',
    'cleanup_service'
] 