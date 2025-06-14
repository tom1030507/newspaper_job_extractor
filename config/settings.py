"""
應用程式配置設定
"""
import os
import secrets
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

class Config:
    """基礎配置類"""
    
    # Flask 基本配置
    SECRET_KEY = secrets.token_hex(16)
    
    # 檔案上傳配置
    UPLOAD_FOLDER = 'uploads'
    RESULTS_FOLDER = 'results'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
    
    # 檔案處理限制
    MAX_FILES_PER_UPLOAD = 10
    
    # 清理設定
    CLEANUP_MAX_AGE_HOURS = 1  # 時間基礎清理：超過此時間的檔案會被清理
    CLEANUP_INTERVAL_HOURS = 1  # 自動清理執行間隔（小時）
    CLEANUP_MAX_FILE_COUNT = 3  # 數量基礎清理：最多保留的檔案數量
    CLEANUP_ENABLE_COUNT_LIMIT = True  # 是否啟用檔案數量限制清理
    
    # Gemini API 設定
    GEMINI_MODEL_NAME = "gemini-2.0-flash-lite"
    GEMINI_VISION_MODEL = "gemini-2.0-flash-001"
    GEMINI_TEMPERATURE = 0.0
    GEMINI_TOP_K = 1
    GEMINI_TOP_P = 0.0
    GEMINI_MAX_RETRIES = 3  # API 限制錯誤的最大重試次數
    GEMINI_ORIENTATION_MAX_RETRIES = 2  # 方向檢測的最大重試次數（通常較快，重試次數少）
    
    # 伺服器設定
    FLASK_HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.environ.get('FLASK_PORT', 8080))
    FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Google Apps Script URL
    GOOGLE_APPS_SCRIPT_URL = os.environ.get('GOOGLE_APPS_SCRIPT_URL', 'YOUR_ACTUAL_GOOGLE_APPS_SCRIPT_URL_HERE')
    
    # CORS 設定
    CORS_ALLOWED_ORIGINS = "*"
    
    # 並行處理設定
    MAX_WORKERS = 8
    REQUEST_TIMEOUT = 30
    
    @staticmethod
    def init_app(app):
        """初始化應用程式配置"""
        # 確保目錄存在
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.RESULTS_FOLDER, exist_ok=True)

class DevelopmentConfig(Config):
    """開發環境配置"""
    DEBUG = True

class ProductionConfig(Config):
    """生產環境配置"""
    DEBUG = False

class TestingConfig(Config):
    """測試環境配置"""
    TESTING = True
    WTF_CSRF_ENABLED = False

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 