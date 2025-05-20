from flask import Flask, request, render_template, redirect, url_for, send_from_directory, send_file
import os
import cv2
import numpy as np
from werkzeug.utils import secure_filename
from image_processor import process_image, main
import uuid
import shutil
import zipfile
import io
import glob

# 使用當前目錄作為靜態文件目錄，這樣可以直接訪問結果目錄
app = Flask(__name__, static_folder='.', static_url_path='')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULTS_FOLDER'] = 'results'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上傳檔案大小為16MB
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg'}

# 確保上傳和結果目錄存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        # 獲取偵錯模式選項
        debug_mode = 1 if request.form.get('debug_mode') == 'on' else 0
        
        # 創建唯一的處理ID
        process_id = str(uuid.uuid4())
        
        # 創建處理目錄
        process_dir = os.path.join(app.config['UPLOAD_FOLDER'], process_id)
        os.makedirs(process_dir, exist_ok=True)
        
        # 保存上傳的檔案
        filename = secure_filename(file.filename)
        file_path = os.path.join(process_dir, filename)
        file.save(file_path)
        
        # 設定輸出目錄
        output_folder = os.path.join(app.config['RESULTS_FOLDER'], process_id)
        
        # 處理檔案
        main(file_path, output_folder, debug_mode=debug_mode)
        
        # 重定向到結果頁面
        return redirect(url_for('results', process_id=process_id))
    
    return redirect(request.url)

@app.route('/results/<process_id>')
def results(process_id):
    base_result_dir = os.path.join(app.config['RESULTS_FOLDER'], process_id)
    
    # 檢查如果是PDF檔案（檢查是否存在以_page1結尾的目錄）
    pdf_page_dirs = glob.glob(f"{base_result_dir}_page*")
    
    if not pdf_page_dirs and not os.path.exists(base_result_dir):
        return "處理結果不存在", 404
    
    # 獲取結果目錄中的所有圖像檔案
    image_files = []
    debug_files = []
    
    # PDF處理 - 遍歷所有頁面目錄
    if pdf_page_dirs:
        # 按頁碼排序
        pdf_page_dirs.sort(key=lambda x: int(x.split('_page')[-1]))
        
        for page_dir in pdf_page_dirs:
            page_num = os.path.basename(page_dir).split('_page')[-1]
            
            # 為每一頁創建一個子目錄結構
            for root, dirs, files in os.walk(page_dir):
                for file in files:
                    if file.endswith(('.jpg', '.jpeg', '.png')):
                        # 獲取相對於results目錄的路徑
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, app.config['RESULTS_FOLDER'])
                        
                        # 檢查是否為偵錯圖像
                        if any(debug_type in file for debug_type in ['_original', '_mask_', '_final_combined']):
                            debug_files.append({
                                'path': rel_path,
                                'page': page_num
                            })
                        else:
                            image_files.append({
                                'path': rel_path,
                                'page': page_num
                            })
    else:
        # 單一圖像處理
        for root, dirs, files in os.walk(base_result_dir):
            for file in files:
                if file.endswith(('.jpg', '.jpeg', '.png')):
                    rel_path = os.path.relpath(os.path.join(root, file), app.config['RESULTS_FOLDER'])
                    # 檢查是否為偵錯圖像
                    if any(debug_type in file for debug_type in ['_original', '_mask_', '_final_combined']):
                        debug_files.append({
                            'path': rel_path,
                            'page': '1'
                        })
                    else:
                        image_files.append({
                            'path': rel_path,
                            'page': '1'
                        })
    
    # 對頁碼進行排序
    image_files.sort(key=lambda x: int(x['page']))
    debug_files.sort(key=lambda x: int(x['page']))
    
    return render_template('results.html', 
                          process_id=process_id, 
                          image_files=image_files,
                          debug_files=debug_files,
                          has_debug_files=len(debug_files) > 0,
                          is_pdf=len(pdf_page_dirs) > 0)

@app.route('/view_image/<path:filename>')
def view_image(filename):
    # 將路徑中的斜線轉換為操作系統適用的斜線
    parts = filename.split('/')
    if len(parts) > 1:
        # 處理子目錄的情況
        directory = os.path.join(app.config['RESULTS_FOLDER'], *parts[:-1])
        filename = parts[-1]
    else:
        # 沒有子目錄的情況
        directory = app.config['RESULTS_FOLDER']
    
    # 檢查文件是否存在
    if not os.path.exists(os.path.join(directory, filename)):
        return "圖像不存在", 404
    
    return send_from_directory(directory, filename)

@app.route('/download/<process_id>')
def download_results(process_id):
    base_result_dir = os.path.join(app.config['RESULTS_FOLDER'], process_id)
    
    # 檢查是否為PDF（檢查是否存在以_page1結尾的目錄）
    pdf_page_dirs = glob.glob(f"{base_result_dir}_page*")
    
    if not pdf_page_dirs and not os.path.exists(base_result_dir):
        return "處理結果不存在", 404
    
    # 創建記憶體中的ZIP檔案
    memory_file = io.BytesIO()
    
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # PDF情況 - 遍歷所有頁面目錄
        if pdf_page_dirs:
            for page_dir in pdf_page_dirs:
                page_num = os.path.basename(page_dir).split('_page')[-1]
                
                # 遍歷當前頁面目錄中的所有文件
                for root, dirs, files in os.walk(page_dir):
                    for file in files:
                        if file.endswith(('.jpg', '.jpeg', '.png')):
                            file_path = os.path.join(root, file)
                            # 在ZIP中創建頁面子目錄
                            arcname = f"page_{page_num}/{os.path.basename(file)}"
                            zf.write(file_path, arcname)
        else:
            # 單一圖像情況
            for root, dirs, files in os.walk(base_result_dir):
                for file in files:
                    if file.endswith(('.jpg', '.jpeg', '.png')):
                        file_path = os.path.join(root, file)
                        # 計算相對路徑，使ZIP內的檔案結構更清晰
                        arcname = os.path.relpath(file_path, base_result_dir)
                        zf.write(file_path, arcname)
    
    # 將指針移到檔案開頭
    memory_file.seek(0)
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'newspaper_blocks_{process_id}.zip'
    )

# 定期清理功能（可以通過排程任務調用）
def cleanup_old_files(max_age_hours=24):
    import time
    from datetime import datetime, timedelta
    
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    cutoff_timestamp = cutoff_time.timestamp()
    
    # 清理上傳目錄
    for item in os.listdir(app.config['UPLOAD_FOLDER']):
        item_path = os.path.join(app.config['UPLOAD_FOLDER'], item)
        if os.path.isdir(item_path) and os.path.getctime(item_path) < cutoff_timestamp:
            shutil.rmtree(item_path)
    
    # 清理結果目錄
    for item in os.listdir(app.config['RESULTS_FOLDER']):
        item_path = os.path.join(app.config['RESULTS_FOLDER'], item)
        if os.path.isdir(item_path) and os.path.getctime(item_path) < cutoff_timestamp:
            shutil.rmtree(item_path)
        # 同時清理PDF頁面目錄
        pdf_dirs = glob.glob(f"{item_path}_page*")
        for pdf_dir in pdf_dirs:
            if os.path.isdir(pdf_dir) and os.path.getctime(pdf_dir) < cutoff_timestamp:
                shutil.rmtree(pdf_dir)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') 