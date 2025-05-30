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
    CLEANUP_MAX_AGE_HOURS = 4
    CLEANUP_INTERVAL_HOURS = 4
    
    # Gemini API 設定
    GEMINI_MODEL_NAME = "gemini-2.0-flash-lite"
    GEMINI_VISION_MODEL = "gemini-2.0-flash-001"
    GEMINI_TEMPERATURE = 0.0
    GEMINI_TOP_K = 1
    GEMINI_TOP_P = 0.0
    
    # 伺服器設定
    FLASK_HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.environ.get('FLASK_PORT', 5000))
    FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # CORS 設定
    CORS_ALLOWED_ORIGINS = "*"
    
    # 並行處理設定
    MAX_WORKERS = 4
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