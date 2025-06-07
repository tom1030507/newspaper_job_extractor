"""
檔案上傳路由模組
處理檔案上傳和圖像處理相關的路由
"""
import os
import cv2
import uuid
import shutil
import fitz  # PyMuPDF
import numpy as np
from werkzeug.utils import secure_filename
from flask import Blueprint, request, flash, redirect, url_for, session
from config.settings import Config
from utils.file_utils import allowed_file
from services.progress_tracker import progress_tracker
from services.image_processing_service import image_processing_service
from services import cleanup_service

upload_bp = Blueprint('upload', __name__)

@upload_bp.route('/create_process_id', methods=['POST'])
def create_process_id():
    """創建新的 process_id 供客戶端使用"""
    from flask import jsonify
    process_id = str(uuid.uuid4())
    return jsonify({'process_id': process_id})

@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """處理檔案上傳"""
    if 'files' not in request.files:
        flash('未選擇檔案', 'danger')
        return redirect(url_for('main.index'))
    
    files = request.files.getlist('files')
    if not files or all(file.filename == '' for file in files):
        flash('未選擇檔案', 'danger')
        return redirect(url_for('main.index'))
    
    # 檢查是否已設置Gemini API密鑰
    if not session.get('gemini_api_key'):
        flash('請先設置Gemini API密鑰', 'warning')
        return redirect(url_for('main.index'))
    
    # 獲取處理選項
    auto_rotate = request.form.get('auto_rotate') == 'true'
    parallel_process = request.form.get('parallel_process') == 'true'
    
    # 將選項儲存到session中，供處理函數使用
    session['auto_rotate'] = auto_rotate
    session['parallel_process'] = parallel_process
    
    print(f"處理選項 - 自動校正方向: {auto_rotate}, 並行處理: {parallel_process}")
    
    # 檢查檔案數量限制
    if len(files) > Config.MAX_FILES_PER_UPLOAD:
        flash(f'一次最多只能上傳 {Config.MAX_FILES_PER_UPLOAD} 個檔案', 'danger')
        return redirect(url_for('main.index'))
    
    # 檢查所有檔案格式
    valid_files = []
    for file in files:
        if file.filename != '' and allowed_file(file.filename, Config.ALLOWED_EXTENSIONS):
            valid_files.append(file)
        elif file.filename != '':
            flash(f'檔案 "{file.filename}" 格式不支援', 'danger')
            return redirect(url_for('main.index'))
    
    if not valid_files:
        flash('沒有有效的檔案', 'danger')
        return redirect(url_for('main.index'))
    
    # 獲取前端提供的 process_id，如果沒有則創建新的
    process_id = request.form.get('process_id')
    if not process_id:
        process_id = str(uuid.uuid4())
    
    # 初始化進度追蹤
    progress_tracker.update_progress(process_id, "upload", 5, "開始處理檔案")
    
    # 創建處理目錄
    process_dir = os.path.join(Config.UPLOAD_FOLDER, process_id)
    os.makedirs(process_dir, exist_ok=True)
    
    processed_files = []  # 記錄已處理的檔案，用於錯誤時清理
    
    try:
        file_counter = 0  # 用於為不同檔案創建唯一的處理ID
        total_files = len(valid_files)
        
        progress_tracker.update_progress(process_id, "upload", 10, f"準備處理 {total_files} 個檔案")
        
        for file in valid_files:
            file_counter += 1
            
            # 更新檔案處理進度 - 為每個檔案分配合理的進度範圍
            file_start_progress = int((file_counter - 1) / total_files * 10)  # 當前檔案開始進度
            file_end_progress = int(file_counter / total_files * 10)  # 當前檔案結束進度
            progress_tracker.update_progress(process_id, "upload", file_start_progress, f"處理檔案 {file_counter}/{total_files}: {file.filename}")
            
            # 保留原始檔名，並產生唯一的儲存檔名
            original_filename = file.filename
            _, file_extension = os.path.splitext(original_filename)
            # 使用 UUID 作為儲存的檔名，但保留原始副檔名
            safe_filename = str(uuid.uuid4()) + file_extension
            file_path = os.path.join(process_dir, safe_filename)
            file.save(file_path)
            processed_files.append(file_path)
            
            # 處理檔案
            if file_path.lower().endswith('.pdf'):
                # PDF 處理
                _process_pdf_file(file_path, original_filename, file_counter, total_files, process_id)
            else:
                # 單一圖像處理
                _process_single_image_file(file_path, original_filename, file_counter, total_files, process_id)
        
        # 在圖像處理完成後，立即執行 AI 分析
        _perform_batch_ai_analysis(process_id)
        
        # 處理完成
        progress_tracker.update_progress(process_id, "complete", 100, "所有檔案處理完成")
        
        # 執行檔案數量限制清理
        try:
            cleanup_service.cleanup_by_file_count()  # 使用配置檔中的預設值
        except Exception as cleanup_error:
            print(f"檔案清理時發生錯誤（不影響主流程）: {str(cleanup_error)}")
        
        # 處理成功，顯示成功訊息
        if len(valid_files) > 1:
            flash(f'成功處理了 {len(valid_files)} 個檔案', 'success')
        else:
            flash('檔案處理完成', 'success')
        
        # 重定向到結果頁面
        return redirect(url_for('results.show_results', process_id=process_id))
        
    except Exception as e:
        progress_tracker.update_progress(process_id, "error", 0, f"處理錯誤: {str(e)}")
        flash(f'處理檔案時發生錯誤: {str(e)}', 'danger')
        return redirect(url_for('main.index'))
    
    finally:
        # 清理上傳的檔案
        for file_path in processed_files:
            if os.path.exists(file_path):
                os.remove(file_path)
        if os.path.exists(process_dir):
            shutil.rmtree(process_dir, ignore_errors=True)

def _process_pdf_file(file_path: str, original_filename: str, file_counter: int, total_files: int, process_id: str):
    """處理PDF檔案"""
    # PDF 處理 - 為每個檔案分配10-60%範圍內的子進度
    file_process_start = 10 + int((file_counter - 1) / total_files * 50)  # 當前檔案在10-60%範圍內的起始點
    file_process_range = int(50 / total_files)  # 當前檔案可用的進度範圍
    
    progress_tracker.update_progress(process_id, "process", file_process_start, f"開始處理 PDF {file_counter}/{total_files}: {original_filename}")
    pdf_document = fitz.open(file_path)
    # 使用原始檔名（不含副檔名）作為基礎名稱
    pdf_base_name = os.path.splitext(original_filename)[0]
    total_pages = len(pdf_document)
    
    for page_num in range(total_pages):
        # 計算當前頁面在當前檔案進度範圍內的位置
        page_progress_in_file = int((page_num / total_pages) * file_process_range)
        current_progress = file_process_start + page_progress_in_file
        progress_tracker.update_progress(process_id, "process", current_progress, f"處理檔案 {file_counter}/{total_files} 第 {page_num + 1}/{total_pages} 頁")
        
        page = pdf_document.load_page(page_num)
        page_rect = page.rect
        width_inch = page_rect.width / 72
        height_inch = page_rect.height / 72
        suggested_dpi = max(300, int(2000 / max(width_inch, height_inch)))
        pix = page.get_pixmap(dpi=suggested_dpi, alpha=False, annots=True)
        
        # 轉換為 OpenCV 格式
        img_array = np.frombuffer(pix.samples, dtype=np.uint8)
        image = img_array.reshape((pix.height, pix.width, pix.n))
        if pix.n == 3:  # RGB
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        elif pix.n == 4:  # RGBA
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
        
        if image is not None:
            # 為多檔案場景調整處理ID和圖片名稱
            if total_files > 1:
                # 多檔案：包含檔案編號
                image_name = f"file{file_counter:02d}_{pdf_base_name}_page{page_num + 1}"
                page_process_id = f"{process_id}_file{file_counter:02d}_page{page_num + 1}"
            else:
                # 單檔案：保持原有邏輯
                image_name = f"{pdf_base_name}_page{page_num + 1}"
                page_process_id = f"{process_id}_page{page_num + 1}"
            
            # 為每一頁分配適當的進度範圍
            page_progress_start = file_process_start + int((page_num / total_pages) * file_process_range)
            page_progress_range = max(1, int(file_process_range / total_pages))  # 確保至少有1%的進度範圍
            
            # 獲取處理選項
            api_key = session.get('gemini_api_key', '')
            auto_rotate = session.get('auto_rotate', True)
            
            image_processing_service.process_image_data(
                image, page_process_id, image_name, 
                page_progress_start, page_progress_range,
                api_key, auto_rotate, Config.RESULTS_FOLDER
            )
    
    pdf_document.close()

def _process_single_image_file(file_path: str, original_filename: str, file_counter: int, total_files: int, process_id: str):
    """處理單一圖像檔案"""
    # 單一圖像處理 - 為每個檔案分配10-60%範圍內的子進度
    file_process_start = 10 + int((file_counter - 1) / total_files * 50)  # 當前檔案在10-60%範圍內的起始點
    file_process_range = int(50 / total_files)  # 當前檔案可用的進度範圍
    
    image = cv2.imread(file_path)
    if image is not None:
        # 為多檔案場景調整處理ID和圖片名稱
        if total_files > 1:
            # 多檔案：包含檔案編號
            image_name = f"file{file_counter:02d}_{os.path.splitext(original_filename)[0]}"
            image_process_id = f"{process_id}_file{file_counter:02d}"
        else:
            # 單檔案：保持原有邏輯
            image_name = os.path.splitext(original_filename)[0]
            image_process_id = process_id
        
        # 獲取處理選項
        api_key = session.get('gemini_api_key', '')
        auto_rotate = session.get('auto_rotate', True)
        
        # 傳遞進度範圍給process_image_data函數
        image_processing_service.process_image_data(
            image, image_process_id, image_name, 
            file_process_start, file_process_range,
            api_key, auto_rotate, Config.RESULTS_FOLDER
        )

def _perform_batch_ai_analysis(process_id: str):
    """執行批量 AI 分析"""
    from models.storage import image_storage
    
    progress_tracker.update_progress(process_id, "analyze", 60, "開始 AI 分析")
    
    # 收集所有需要分析的圖片
    batch_analysis_requests = {}  # {process_key: [filenames]}
    
    # 檢查是否為PDF或多檔案
    pdf_page_keys = [key for key in image_storage._storage.keys() if key.startswith(f"{process_id}_page")]
    multi_file_keys = [key for key in image_storage._storage.keys() if key.startswith(f"{process_id}_file")]
    
    if pdf_page_keys or multi_file_keys or process_id in image_storage._storage:
        # 處理PDF頁面
        for page_key in pdf_page_keys:
            filenames = [fname for fname in image_storage._storage[page_key].keys() 
                       if not any(debug_type in fname for debug_type in ['_original', '_mask_', '_final_combined'])]
            if filenames:
                batch_analysis_requests[page_key] = filenames
        
        # 處理多檔案
        for file_key in multi_file_keys:
            filenames = [fname for fname in image_storage._storage[file_key].keys() 
                       if not any(debug_type in fname for debug_type in ['_original', '_mask_', '_final_combined'])]
            if filenames:
                batch_analysis_requests[file_key] = filenames
        
        # 處理單一圖像
        if process_id in image_storage._storage and not pdf_page_keys and not multi_file_keys:
            filenames = [fname for fname in image_storage._storage[process_id].keys() 
                       if not any(debug_type in fname for debug_type in ['_original', '_mask_', '_final_combined'])]
            if filenames:
                batch_analysis_requests[process_id] = filenames
        
        # 執行批量AI分析
        total_images = sum(len(filenames) for filenames in batch_analysis_requests.values())
        if total_images > 0:
            progress_tracker.update_progress(process_id, "analyze", 65, f"準備分析 {total_images} 張圖片")
            
            api_key = session.get('gemini_api_key', '')
            parallel_process = session.get('parallel_process', True)
            processed_images = 0
            
            for process_key, filenames in batch_analysis_requests.items():
                if filenames:
                    descriptions = image_processing_service.analyze_images_batch(
                        process_key, filenames, api_key, processed_images, total_images, parallel_process
                    )
                    processed_images += len(filenames)
                    
                    # 儲存AI分析結果
                    for filename, description in descriptions.items():
                        if process_key in image_storage._storage and filename in image_storage._storage[process_key]:
                            image_storage._storage[process_key][filename]['description'] = description
    
    # AI 分析完成
    progress_tracker.update_progress(process_id, "analyze", 95, "AI 分析完成") 