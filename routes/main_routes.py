"""
主要路由模組
包含首頁、API密鑰設定等基本路由
"""
import os
from flask import Blueprint, render_template, request, session, flash, redirect, url_for, jsonify
from config.settings import Config

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """首頁"""
    # 從環境變數讀取 API key，如果 session 中沒有的話
    if not session.get('gemini_api_key'):
        env_api_key = os.environ.get('GEMINI_API_KEY', '')
        if env_api_key:
            session['gemini_api_key'] = env_api_key
    
    return render_template('index.html', 
                          api_key=session.get('gemini_api_key', ''), 
                          model_name=Config.GEMINI_MODEL_NAME)

@main_bp.route('/set_api_key', methods=['POST'])
def set_api_key():
    """設定 Gemini API 密鑰"""
    api_key = request.form.get('api_key', '')
    if api_key:
        session['gemini_api_key'] = api_key
        
        # 檢查請求是否為 AJAX
        if request.headers.get('Content-Type', '').startswith('multipart/form-data'):
            # AJAX 請求，返回 JSON 響應
            return jsonify({'success': True, 'message': 'Gemini API密鑰已設置成功！'})
        else:
            # 傳統表單提交，使用 flash 和重定向
            flash('Gemini API密鑰已設置成功！', 'success')
            return redirect(url_for('main.index'))
    else:
        # 檢查請求是否為 AJAX
        if request.headers.get('Content-Type', '').startswith('multipart/form-data'):
            # AJAX 請求，返回 JSON 響應
            return jsonify({'success': False, 'message': 'API密鑰不能為空！'}), 400
        else:
            # 傳統表單提交，使用 flash 和重定向
            flash('API密鑰不能為空！', 'danger')
            return redirect(url_for('main.index'))

@main_bp.route('/health')
def health_check():
    """健康檢查端點 - 用於Docker健康檢查"""
    from datetime import datetime
    from utils.file_utils import get_storage_info
    import schedule
    
    try:
        # 檢查基本功能
        storage_info = get_storage_info(Config.RESULTS_FOLDER)
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'storage': storage_info,
            'services': {
                'flask': 'running',
                'socketio': 'running',
                'cleanup_scheduler': 'running' if schedule.jobs else 'stopped'
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@main_bp.route('/api/status')
def api_status():
    """API狀態端點"""
    return jsonify({
        'status': 'running',
        'version': '1.0.0',
        'features': {
            'file_upload': True,
            'pdf_processing': True,
            'ai_analysis': True,
            'auto_cleanup': True,
            'multi_file': True,
            'parallel_processing': True
        },
        'limits': {
            'max_file_size_mb': Config.MAX_CONTENT_LENGTH // (1024 * 1024),
            'max_files_per_upload': Config.MAX_FILES_PER_UPLOAD,
            'supported_formats': list(Config.ALLOWED_EXTENSIONS)
        }
    })