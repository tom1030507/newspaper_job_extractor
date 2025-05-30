"""
報紙工作廣告區塊提取系統 - 模組化重構版本
主應用程式檔案
"""
import os
import threading
import time
import schedule
from datetime import datetime
from flask import Flask
from flask_socketio import SocketIO, emit

# 導入配置
from config import Config, config

# 導入模型和存儲
from models import image_storage, job_storage, progress_storage

# 導入服務
from services import progress_tracker, ai_service, image_processing_service

# 導入路由
from routes import main_bp, upload_bp, results_bp

# 導入工具函數
from utils import cleanup_old_files, get_storage_info

def create_app(config_name='default'):
    """應用程式工廠函數"""
    app = Flask(__name__, static_folder='.', static_url_path='')
    
    # 載入配置
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # 初始化 SocketIO
    socketio = SocketIO(app, cors_allowed_origins=Config.CORS_ALLOWED_ORIGINS)
    
    # 設置進度追蹤器的 SocketIO 實例
    progress_tracker.socketio = socketio
    
    # 註冊藍圖
    app.register_blueprint(main_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(results_bp)
    
    # SocketIO 事件處理
    @socketio.on('connect')
    def handle_connect():
        """處理客戶端連接"""
        from flask import request
        print(f"客戶端已連接: {request.sid}")

    @socketio.on('disconnect')
    def handle_disconnect():
        """處理客戶端斷開連接"""
        from flask import request
        print(f"客戶端已斷開: {request.sid}")

    @socketio.on('get_progress')
    def handle_get_progress(data):
        """處理客戶端請求進度資訊"""
        process_id = data.get('process_id')
        progress_data = progress_tracker.get_progress(process_id)
        if progress_data:
            emit('progress_update', {
                'process_id': process_id,
                **progress_data
            })
    
    # 管理路由
    @app.route('/admin/storage')
    def admin_storage():
        """管理員查看存儲狀態"""
        from flask import jsonify
        
        storage_info = get_storage_info(Config.RESULTS_FOLDER)
        storage_info['memory_processes'] = len(image_storage._storage)
        
        # 獲取最近的處理記錄
        recent_processes = []
        if os.path.exists(Config.RESULTS_FOLDER):
            for item in os.listdir(Config.RESULTS_FOLDER):
                item_path = os.path.join(Config.RESULTS_FOLDER, item)
                if os.path.isdir(item_path):
                    recent_processes.append({
                        'process_id': item,
                        'created_time': datetime.fromtimestamp(os.path.getctime(item_path)).isoformat(),
                        'size_mb': round(sum(os.path.getsize(os.path.join(root, file)) 
                                           for root, dirs, files in os.walk(item_path) 
                                           for file in files) / (1024 * 1024), 2)
                    })
        
        # 按創建時間排序
        recent_processes.sort(key=lambda x: x['created_time'], reverse=True)
        
        return jsonify({
            'storage_info': storage_info,
            'recent_processes': recent_processes[:10],  # 只顯示最近10個
            'status': 'success'
        })

    @app.route('/admin/cleanup', methods=['POST'])
    def admin_cleanup():
        """手動清理舊檔案"""
        from flask import request, jsonify
        
        try:
            max_age_hours = request.json.get('max_age_hours', Config.CLEANUP_MAX_AGE_HOURS) if request.json else Config.CLEANUP_MAX_AGE_HOURS
            cleanup_old_files(Config.UPLOAD_FOLDER, Config.RESULTS_FOLDER, max_age_hours)
            
            # 獲取清理後的存儲資訊
            storage_info = get_storage_info(Config.RESULTS_FOLDER)
            storage_info['memory_processes'] = len(image_storage._storage)
            
            return jsonify({
                'message': f'已清理超過 {max_age_hours} 小時的檔案',
                'storage_info': storage_info,
                'status': 'success'
            })
        except Exception as e:
            return jsonify({
                'error': f'清理失敗: {str(e)}',
                'status': 'error'
            }), 500

    @app.route('/admin/cleanup/auto', methods=['POST'])
    def toggle_auto_cleanup():
        """切換自動清理功能"""
        from flask import request, jsonify
        
        try:
            enabled = request.json.get('enabled', True) if request.json else True
            
            if enabled:
                start_cleanup_scheduler()
                message = f"自動清理已啟用，每{Config.CLEANUP_INTERVAL_HOURS}小時執行一次"
            else:
                schedule.clear()
                message = "自動清理已停用"
            
            return jsonify({
                'message': message,
                'auto_cleanup_enabled': enabled,
                'status': 'success'
            })
        except Exception as e:
            return jsonify({
                'error': f'切換自動清理失敗: {str(e)}',
                'status': 'error'
            }), 500
    
    # Google Sheets 整合路由
    @app.route('/send_to_spreadsheet/<process_id>', methods=['POST'])
    def send_to_spreadsheet(process_id):
        """將處理結果發送到 Google Sheets"""
        from flask import request, jsonify
        from utils.file_utils import is_valid_job
        import requests
        
        try:
            # 從請求中獲取 Google Apps Script URL（現在變為可選）
            data = request.get_json() if request.get_json() else {}
            apps_script_url = data.get('apps_script_url', '')
            
            # 如果沒有提供 URL，使用默認的自動創建 Google Sheet 的 Apps Script
            if not apps_script_url:
                # TODO: 請將下面的 URL 替換為您實際部署的 Google Apps Script URL
                apps_script_url = 'YOUR_ACTUAL_GOOGLE_APPS_SCRIPT_URL_HERE'  # 請替換為實際部署的 URL
                
                # 如果還沒有設置真實的 URL，返回錯誤
                if apps_script_url == 'YOUR_ACTUAL_GOOGLE_APPS_SCRIPT_URL_HERE':
                    return jsonify({
                        'error': '請先設置 Google Apps Script URL',
                        'message': '請參考 GOOGLE_APPS_SCRIPT_SETUP.md 文件來部署您的 Google Apps Script，然後更新程式中的 URL'
                    }), 400
            
            # 收集職缺資料 - 使用與 results 和 download 相同的邏輯
            all_jobs = []
            
            # 檢查是否為PDF或多檔案
            pdf_page_keys = [key for key in image_storage._storage.keys() if key.startswith(f"{process_id}_page")]
            multi_file_keys = [key for key in image_storage._storage.keys() if key.startswith(f"{process_id}_file")]
            
            if pdf_page_keys:
                # PDF情況
                pdf_page_keys.sort(key=lambda x: int(x.split('_page')[-1]))
                
                for page_key in pdf_page_keys:
                    page_num = page_key.split('_page')[-1]
                    
                    for filename, image_data in image_storage._storage[page_key].items():
                        # 跳過偵錯圖像
                        if any(debug_type in filename for debug_type in ['_original', '_mask_', '_final_combined']):
                            continue
                        
                        # 直接從 image_storage 獲取描述
                        description = []
                        if page_key in image_storage._storage and \
                           filename in image_storage._storage[page_key] and \
                           'description' in image_storage._storage[page_key][filename]:
                            description = image_storage._storage[page_key][filename]['description']
                        else:
                            print(f"警告: 在 send_to_spreadsheet 中找不到圖片 {filename} (page_key: {page_key}) 的描述，將使用空描述。")
                            description = [{
                                "工作": "描述未找到",
                                "行業": "", "時間": "", "薪資": "",
                                "地點": "", "聯絡方式": "", "其他": ""
                            }]
                        
                        # 收集有效的工作資訊
                        if isinstance(description, list):
                            for i, job in enumerate(description):
                                if is_valid_job(job):
                                    job_info = job.copy()
                                    job_info['來源圖片'] = filename
                                    job_info['頁碼'] = page_num
                                    job_info['圖片編號'] = f"page{page_num}_{filename.split('.')[0]}"
                                    if len([j for j in description if is_valid_job(j)]) > 1:
                                        valid_jobs = [j for j in description if is_valid_job(j)]
                                        job_index = valid_jobs.index(job) + 1
                                        job_info['工作編號'] = f"工作 {job_index}"
                                    else:
                                        job_info['工作編號'] = ""
                                    all_jobs.append(job_info)
            elif multi_file_keys:
                # 多檔案情況
                multi_file_keys.sort(key=lambda x: x.split('_file')[-1])
                
                for file_key in multi_file_keys:
                    # 解析檔案編號和可能的頁碼
                    key_parts = file_key.replace(f"{process_id}_", "").split('_')
                    if 'page' in file_key:
                        # 多檔案PDF的情況
                        file_part = key_parts[0]  # file01
                        page_part = key_parts[1]  # page1
                        page_num = page_part.replace('page', '')
                        file_display = f"{file_part}_page{page_num}"
                    else:
                        # 多檔案圖片的情況
                        file_display = key_parts[0]
                        page_num = file_display
                    
                    for filename, image_data in image_storage._storage[file_key].items():
                        # 跳過偵錯圖像
                        if any(debug_type in filename for debug_type in ['_original', '_mask_', '_final_combined']):
                            continue
                        
                        # 直接從 image_storage 獲取描述
                        description = []
                        if file_key in image_storage._storage and \
                           filename in image_storage._storage[file_key] and \
                           'description' in image_storage._storage[file_key][filename]:
                            description = image_storage._storage[file_key][filename]['description']
                        else:
                            print(f"警告: 在 send_to_spreadsheet 中找不到圖片 {filename} (file_key: {file_key}) 的描述，將使用空描述。")
                            description = [{
                                "工作": "描述未找到",
                                "行業": "", "時間": "", "薪資": "",
                                "地點": "", "聯絡方式": "", "其他": ""
                            }]
                        
                        # 收集有效的工作資訊
                        if isinstance(description, list):
                            for i, job in enumerate(description):
                                if is_valid_job(job):
                                    job_info = job.copy()
                                    job_info['來源圖片'] = filename
                                    job_info['頁碼'] = page_num
                                    job_info['圖片編號'] = f"{file_display}_{filename.split('.')[0]}"
                                    if len([j for j in description if is_valid_job(j)]) > 1:
                                        valid_jobs = [j for j in description if is_valid_job(j)]
                                        job_index = valid_jobs.index(job) + 1
                                        job_info['工作編號'] = f"工作 {job_index}"
                                    else:
                                        job_info['工作編號'] = ""
                                    all_jobs.append(job_info)
            elif process_id in image_storage._storage:
                # 單一圖像情況
                for filename, image_data in image_storage._storage[process_id].items():
                    # 跳過偵錯圖像
                    if any(debug_type in filename for debug_type in ['_original', '_mask_', '_final_combined']):
                        continue
                    
                    # 直接從 image_storage 獲取描述
                    description = []
                    if process_id in image_storage._storage and \
                       filename in image_storage._storage[process_id] and \
                       'description' in image_storage._storage[process_id][filename]:
                        description = image_storage._storage[process_id][filename]['description']
                    else:
                        print(f"警告: 在 send_to_spreadsheet 中找不到圖片 {filename} (process_id: {process_id}) 的描述，將使用空描述。")
                        description = [{
                            "工作": "描述未找到",
                            "行業": "", "時間": "", "薪資": "",
                            "地點": "", "聯絡方式": "", "其他": ""
                        }]
                    
                    # 收集有效的工作資訊
                    if isinstance(description, list):
                        for i, job in enumerate(description):
                            if is_valid_job(job):
                                job_info = job.copy()
                                job_info['來源圖片'] = filename
                                job_info['頁碼'] = '1'
                                job_info['圖片編號'] = filename.split('.')[0]
                                if len([j for j in description if is_valid_job(j)]) > 1:
                                    valid_jobs = [j for j in description if is_valid_job(j)]
                                    job_index = valid_jobs.index(job) + 1
                                    job_info['工作編號'] = f"工作 {job_index}"
                                else:
                                    job_info['工作編號'] = ""
                                all_jobs.append(job_info)
            else:
                return jsonify({'error': '處理結果不存在'}), 404
            
            if not all_jobs:
                return jsonify({'error': '沒有找到有效的職缺資料'}), 404
            
            # 準備發送到 Google Apps Script 的資料
            payload = {
                'action': 'addJobs',
                'jobs': all_jobs,
                'metadata': {
                    'process_id': process_id,
                    'total_jobs': len(all_jobs),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'newspaper_job_extractor'
                }
            }
            
            # 添加詳細日誌記錄
            print(f"準備發送資料到 Google Apps Script: {apps_script_url}")
            print(f"職缺資料數量: {len(all_jobs)}")
            print(f"第一筆職缺資料範例: {all_jobs[0] if all_jobs else 'None'}")
            print(f"Payload 大小: {len(str(payload))} 字符")
            
            # 發送資料到 Google Apps Script
            headers = {
                'Content-Type': 'application/json'
            }
            
            try:
                response = requests.post(apps_script_url, json=payload, headers=headers, timeout=Config.REQUEST_TIMEOUT)
                print(f"HTTP 回應狀態碼: {response.status_code}")
                print(f"HTTP 回應內容: {response.text[:500]}...")  # 只顯示前500字符
            except Exception as e:
                print(f"發送請求時發生錯誤: {str(e)}")
                raise
            
            if response.status_code == 200:
                result = response.json() if response.content else {}
                return jsonify({
                    'success': True,
                    'message': f'成功發送 {len(all_jobs)} 筆職缺資料到 Google Sheets',
                    'jobs_sent': len(all_jobs),
                    'spreadsheet_url': result.get('spreadsheet_url', ''),
                    'spreadsheet_id': result.get('spreadsheet_id', ''),
                    'response': result
                }), 200
            else:
                return jsonify({
                    'error': f'發送失敗，狀態碼: {response.status_code}',
                    'response_text': response.text
                }), response.status_code
                
        except requests.exceptions.Timeout:
            return jsonify({'error': '請求超時，請檢查 Google Apps Script URL 是否正確'}), 408
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'網路請求錯誤: {str(e)}'}), 500
        except Exception as e:
            return jsonify({'error': f'發生錯誤: {str(e)}'}), 500
    
    return app, socketio

def cleanup_memory_storage(process_id):
    """清理記憶體中的過期資料"""
    # 清理所有相關的process_id記錄
    image_storage.remove_process(process_id)
    job_storage.remove_process(process_id)
    progress_tracker.remove_progress(process_id)
    print(f"清理記憶體資料: {process_id}")

def start_cleanup_scheduler():
    """啟動定時清理任務"""
    def run_scheduled_cleanup():
        print("執行定時清理任務...")
        cleanup_old_files(Config.UPLOAD_FOLDER, Config.RESULTS_FOLDER, Config.CLEANUP_MAX_AGE_HOURS)
    
    # 設置每4小時執行一次清理
    schedule.every(Config.CLEANUP_INTERVAL_HOURS).hours.do(run_scheduled_cleanup)
    
    # 在背景執行緒中運行排程器
    def schedule_runner():
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分鐘檢查一次
    
    cleanup_thread = threading.Thread(target=schedule_runner, daemon=True)
    cleanup_thread.start()
    print(f"定時清理任務已啟動，每{Config.CLEANUP_INTERVAL_HOURS}小時執行一次")

# 創建應用實例
app, socketio = create_app()

if __name__ == '__main__':
    # 啟動定時清理任務
    start_cleanup_scheduler()
    
    # 立即執行一次清理（清理啟動時的舊檔案）
    cleanup_old_files(Config.UPLOAD_FOLDER, Config.RESULTS_FOLDER, Config.CLEANUP_MAX_AGE_HOURS)
    
    # 從配置讀取伺服器設定
    host = Config.FLASK_HOST
    port = Config.FLASK_PORT
    debug = Config.FLASK_DEBUG
    
    print(f"🚀 啟動報紙工作廣告提取系統...")
    print(f"📡 伺服器地址: http://{host}:{port}")
    print(f"🔧 除錯模式: {debug}")
    print(f"🧹 自動清理: 每{Config.CLEANUP_INTERVAL_HOURS}小時執行")
    
    socketio.run(app, debug=debug, host=host, port=port) 