"""
路由模組
"""
from .main_routes import main_bp
from .upload_routes import upload_bp
from .results_routes import results_bp

__all__ = ['main_bp', 'upload_bp', 'results_bp'] 