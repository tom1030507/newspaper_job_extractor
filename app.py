from flask import Flask, request, render_template, redirect, url_for, send_from_directory, send_file, session, flash, make_response
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
import google.generativeai as genai
from PIL import Image
import base64
from io import BytesIO
import json
import time
import secrets

# 使用當前目錄作為靜態文件目錄，這樣可以直接訪問結果目錄
app = Flask(__name__, static_folder='.', static_url_path='')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULTS_FOLDER'] = 'results'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上傳檔案大小為16MB
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg'}
app.config['SECRET_KEY'] = secrets.token_hex(16)  # 添加密鑰用於session加密

# 設定Gemini API相關配置

# 儲存處理後的圖片資料
image_storage = {}

# 確保上傳目錄存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def process_image_data(image, process_id, image_name, debug_mode=0):
    """處理圖像並儲存結果"""
    from image_processor import process_image as original_process_image
    import tempfile
    import shutil
    
    # 創建臨時目錄進行處理
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 使用原始處理函數處理到臨時目錄
        original_process_image(image, temp_dir, image_name, debug_mode)
        
        # 將處理結果儲存
        if process_id not in image_storage:
            image_storage[process_id] = {}
        
        # 遍歷臨時目錄中的所有圖片檔案
        for filename in os.listdir(temp_dir):
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                file_path = os.path.join(temp_dir, filename)
                
                # 讀取圖片並編碼
                with open(file_path, 'rb') as f:
                    image_data = f.read()
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                    
                    # 儲存圖片資料
                    image_storage[process_id][filename] = {
                        'base64': base64_data,
                        'binary': image_data,
                        'format': filename.split('.')[-1].lower()
                    }
        
        return list(image_storage[process_id].keys())
        
    finally:
        # 清理臨時目錄
        shutil.rmtree(temp_dir, ignore_errors=True)

def get_image_description(process_id, image_name):
    """獲取圖片的AI描述"""
    
    # 從session中獲取API密鑰
    api_key = session.get('gemini_api_key', '')
    
    # 如果沒有設置API密鑰，返回默認訊息
    if not api_key:
        return [{
            "工作": "未設置Gemini API密鑰",
            "時間": "",
            "薪資": "",
            "地點": "",
            "聯絡方式": "",
            "其他": "請在首頁設置API密鑰"
        }]
    
    # 檢查圖片是否存在
    if process_id not in image_storage or image_name not in image_storage[process_id]:
        return [{
            "工作": "圖片不存在",
            "時間": "",
            "薪資": "",
            "地點": "",
            "聯絡方式": "",
            "其他": ""
        }]
    
    try:
        # 配置API密鑰
        genai.configure(api_key=api_key)
        MODEL = genai.GenerativeModel('gemini-2.0-flash-lite')
        
        # 取得圖片資料
        image_data = image_storage[process_id][image_name]['binary']
        img = Image.open(BytesIO(image_data))
        
        # 調用Gemini API
        prompt = """請分析這張圖片中的所有就業資訊，可能包含多個工作崗位。請以JSON格式回答，包含一個工作列表，每個工作包含以下欄位：
        - 工作：工作職位或職業名稱
        - 時間：工作時間或營業時間
        - 薪資：薪資待遇或收入
        - 地點：工作地點或地址
        - 聯絡方式：電話、地址或其他聯絡資訊
        - 其他：其他相關資訊或備註

        請用繁體中文回答，如果某個欄位沒有資訊請填入空字串。
        請直接回答JSON格式的工作列表，不要包含其他說明文字。
        
        範例格式：
        [
            {
                "工作": "服務員",
                "時間": "9:00-18:00",
                "薪資": "時薪160元起",
                "地點": "台北市信義區",
                "聯絡方式": "02-1234-5678",
                "其他": "需輪班"
            },
            {
                "工作": "廚師",
                "時間": "早班 6:00-14:00",
                "薪資": "月薪35000元",
                "地點": "台北市大安區",
                "聯絡方式": "02-8765-4321",
                "其他": "具餐飲經驗佳"
            }
        ]
        
        如果只有一個工作，也請用陣列格式回答。如果圖片中沒有工作資訊，請回答空陣列 []。"""
        
        response = MODEL.generate_content([prompt, img])
        
        # 獲取響應文字
        description_text = response.text.strip()
        
        # 嘗試解析JSON
        try:
            # 移除可能的markdown格式標記
            if description_text.startswith('```json'):
                description_text = description_text.replace('```json', '').replace('```', '').strip()
            elif description_text.startswith('```'):
                description_text = description_text.replace('```', '').strip()
            
            description_json = json.loads(description_text)
            
            # 確保返回的是列表
            if not isinstance(description_json, list):
                # 如果返回的是單一物件，轉換為列表
                if isinstance(description_json, dict):
                    description_json = [description_json]
                else:
                    description_json = []
            
            # 確保每個工作物件都有所有必要欄位
            required_fields = ["工作", "時間", "薪資", "地點", "聯絡方式", "其他"]
            for job in description_json:
                if isinstance(job, dict):
                    for field in required_fields:
                        if field not in job:
                            job[field] = ""
            
            # 如果沒有工作，返回一個空的提示
            if not description_json:
                return [{
                    "工作": "未識別到工作資訊",
                    "時間": "",
                    "薪資": "",
                    "地點": "",
                    "聯絡方式": "",
                    "其他": "此圖片可能不包含就業相關資訊"
                }]
            
            return description_json
            
        except json.JSONDecodeError:
            # 如果JSON解析失敗，嘗試從文字中提取資訊
            return [{
                "工作": "",
                "時間": "",
                "薪資": "",
                "地點": "",
                "聯絡方式": "",
                "其他": description_text
            }]
    
    except Exception as e:
        print(f"獲取圖片描述時出錯: {str(e)}")
        return [{
            "工作": "獲取描述時出錯",
            "時間": "",
            "薪資": "",
            "地點": "",
            "聯絡方式": "",
            "其他": str(e)
        }]

def get_image_description_legacy(image_path, process_id, image_name):
    """使用Gemini API獲取圖片的文字說明（兼容舊版本）"""
    
    # 從session中獲取API密鑰
    api_key = session.get('gemini_api_key', '')
    
    # 如果沒有設置API密鑰，返回默認訊息
    if not api_key:
        return "未設置Gemini API密鑰，請在首頁設置"
    
    try:
        # 配置API密鑰
        genai.configure(api_key=api_key)
        MODEL = genai.GenerativeModel('gemini-2.0-flash-lite')
        
        # 讀取圖片
        img = Image.open(image_path)
        
        # 調用Gemini API
        prompt = "請描述這張圖片中的內容，特別是裡面可能包含的就業資訊或新聞內容。請使用繁體中文回答，並保持簡潔（不超過100字）。"
        response = MODEL.generate_content([prompt, img])
        
        # 獲取響應文字
        description = response.text
        
        return description
    
    except Exception as e:
        print(f"獲取圖片描述時出錯: {str(e)}")
        return f"獲取圖片描述時出錯: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html', api_key=session.get('gemini_api_key', ''), model_name="gemini-2.0-flash-lite")

@app.route('/set_api_key', methods=['POST'])
def set_api_key():
    api_key = request.form.get('api_key', '')
    if api_key:
        session['gemini_api_key'] = api_key
        flash('Gemini API密鑰已設置成功！', 'success')
    else:
        flash('API密鑰不能為空！', 'danger')
    return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('未選擇檔案', 'danger')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('未選擇檔案', 'danger')
        return redirect(url_for('index'))
    
    # 檢查是否已設置Gemini API密鑰
    if not session.get('gemini_api_key'):
        flash('請先設置Gemini API密鑰', 'warning')
        return redirect(url_for('index'))
    
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
        
        # 處理檔案
        try:
            if file_path.lower().endswith('.pdf'):
                # PDF 處理
                import fitz
                pdf_document = fitz.open(file_path)
                pdf_base_name = os.path.splitext(filename)[0]
                
                for page_num in range(len(pdf_document)):
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
                        image_name = f"{pdf_base_name}_page{page_num + 1}"
                        page_process_id = f"{process_id}_page{page_num + 1}"
                        process_image_data(image, page_process_id, image_name, debug_mode)
                
                pdf_document.close()
            else:
                # 單一圖像處理
                image = cv2.imread(file_path)
                if image is not None:
                    image_name = os.path.splitext(filename)[0]
                    process_image_data(image, process_id, image_name, debug_mode)
            
            # 重定向到結果頁面
            return redirect(url_for('results', process_id=process_id))
            
        except Exception as e:
            flash(f'處理檔案時發生錯誤: {str(e)}', 'danger')
            return redirect(url_for('index'))
        
        finally:
            # 清理上傳的檔案
            if os.path.exists(file_path):
                os.remove(file_path)
            if os.path.exists(process_dir):
                shutil.rmtree(process_dir, ignore_errors=True)
    
    flash('不支援的檔案格式', 'danger')
    return redirect(url_for('index'))

def is_valid_job(job):
    """檢查是否為有效的工作資訊"""
    invalid_jobs = ['未識別到工作資訊', '未設置Gemini API密鑰', '圖片不存在', '獲取描述時出錯']
    return job.get('工作') and job.get('工作') not in invalid_jobs

@app.route('/results/<process_id>')
def results(process_id):
    # 檢查是否有此處理ID的資料
    image_files = []
    debug_files = []
    all_jobs = []  # 統一的工作列表
    is_pdf = False
    
    # 檢查是否為PDF（尋找帶有 _page 的處理ID）
    pdf_page_keys = [key for key in image_storage.keys() if key.startswith(f"{process_id}_page")]
    
    if pdf_page_keys:
        is_pdf = True
        # 按頁碼排序
        pdf_page_keys.sort(key=lambda x: int(x.split('_page')[-1]))
        
        for page_key in pdf_page_keys:
            page_num = page_key.split('_page')[-1]
            
            for filename, image_data in image_storage[page_key].items():
                # 檢查是否為偵錯圖像
                if any(debug_type in filename for debug_type in ['_original', '_mask_', '_final_combined']):
                    debug_files.append({
                        'filename': filename,
                        'page': page_num,
                        'base64': image_data['base64'],
                        'format': image_data['format']
                    })
                else:
                    # 獲取圖片描述
                    description = get_image_description(page_key, filename)
                    
                    # 檢查是否有有效的工作資訊
                    has_valid_jobs = any(is_valid_job(job) for job in description)
                    
                    if has_valid_jobs:
                        image_files.append({
                            'filename': filename,
                            'page': page_num,
                            'base64': image_data['base64'],
                            'format': image_data['format'],
                            'description': description
                        })
                        
                        # 將工作資訊加入統一列表
                        for i, job in enumerate(description):
                            # 只加入有效的工作資訊
                            if is_valid_job(job):
                                job_info = job.copy()
                                job_info['來源圖片'] = f"第{page_num}頁 - {filename}"
                                job_info['圖片編號'] = f"page{page_num}_{filename.split('.')[0]}"
                                if len([j for j in description if is_valid_job(j)]) > 1:
                                    valid_jobs = [j for j in description if is_valid_job(j)]
                                    job_index = valid_jobs.index(job) + 1
                                    job_info['工作編號'] = f"工作 {job_index}"
                                else:
                                    job_info['工作編號'] = ""
                                all_jobs.append(job_info)
    elif process_id in image_storage:
        # 單一圖像處理
        for filename, image_data in image_storage[process_id].items():
            if any(debug_type in filename for debug_type in ['_original', '_mask_', '_final_combined']):
                debug_files.append({
                    'filename': filename,
                    'page': '1',
                    'base64': image_data['base64'],
                    'format': image_data['format']
                })
            else:
                # 獲取圖片描述
                description = get_image_description(process_id, filename)
                
                # 檢查是否有有效的工作資訊
                has_valid_jobs = any(is_valid_job(job) for job in description)
                
                if has_valid_jobs:
                    image_files.append({
                        'filename': filename,
                        'page': '1',
                        'base64': image_data['base64'],
                        'format': image_data['format'],
                        'description': description
                    })
                    
                    # 將工作資訊加入統一列表
                    for i, job in enumerate(description):
                        # 只加入有效的工作資訊
                        if is_valid_job(job):
                            job_info = job.copy()
                            job_info['來源圖片'] = filename
                            job_info['圖片編號'] = filename.split('.')[0]
                            if len([j for j in description if is_valid_job(j)]) > 1:
                                valid_jobs = [j for j in description if is_valid_job(j)]
                                job_index = valid_jobs.index(job) + 1
                                job_info['工作編號'] = f"工作 {job_index}"
                            else:
                                job_info['工作編號'] = ""
                            all_jobs.append(job_info)
    else:
        return "處理結果不存在", 404
    
    # 對頁碼進行排序
    image_files.sort(key=lambda x: int(x['page']))
    debug_files.sort(key=lambda x: int(x['page']))
    
    return render_template('results.html', 
                          process_id=process_id, 
                          image_files=image_files,
                          debug_files=debug_files,
                          all_jobs=all_jobs,
                          has_debug_files=len(debug_files) > 0,
                          is_pdf=is_pdf,
                          model_name="gemini-2.0-flash-lite")

@app.route('/view_image/<process_id>/<filename>')
def view_image(process_id, filename):
    # 檢查是否存在該圖片
    if process_id in image_storage and filename in image_storage[process_id]:
        image_data = image_storage[process_id][filename]['binary']
        format_type = image_storage[process_id][filename]['format']
        
        response = make_response(image_data)
        response.headers['Content-Type'] = f'image/{format_type}'
        return response
    
    # 檢查PDF頁面
    pdf_page_keys = [key for key in image_storage.keys() if key.startswith(f"{process_id}_page")]
    for page_key in pdf_page_keys:
        if filename in image_storage[page_key]:
            image_data = image_storage[page_key][filename]['binary']
            format_type = image_storage[page_key][filename]['format']
            
            response = make_response(image_data)
            response.headers['Content-Type'] = f'image/{format_type}'
            return response
    
    return "圖像不存在", 404

@app.route('/download/<process_id>')
def download_results(process_id):
    # 創建ZIP檔案
    memory_file = io.BytesIO()
    
    # 檢查是否為PDF
    pdf_page_keys = [key for key in image_storage.keys() if key.startswith(f"{process_id}_page")]
    
    if not pdf_page_keys and process_id not in image_storage:
        return "處理結果不存在", 404
    
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # PDF情況
        if pdf_page_keys:
            pdf_page_keys.sort(key=lambda x: int(x.split('_page')[-1]))
            
            for page_key in pdf_page_keys:
                page_num = page_key.split('_page')[-1]
                
                for filename, image_data in image_storage[page_key].items():
                    # 添加圖片
                    arcname = f"page_{page_num}/{filename}"
                    zf.writestr(arcname, image_data['binary'])
                    
                    # 添加描述（如果不是偵錯圖片）
                    if not any(debug_type in filename for debug_type in ['_original', '_mask_', '_final_combined']):
                        description = get_image_description(page_key, filename)
                        desc_text_name = f"page_{page_num}/{os.path.splitext(filename)[0]}_description.txt"
                        
                        # 將工作列表轉換為可讀的表格格式
                        if isinstance(description, list) and description:
                            desc_text = "工作資訊分析結果\n" + "="*50 + "\n\n"
                            for i, job in enumerate(description, 1):
                                if len(description) > 1:
                                    desc_text += f"工作 {i}\n" + "-"*20 + "\n"
                                desc_text += f"工作：{job.get('工作', '無資訊')}\n"
                                desc_text += f"時間：{job.get('時間', '無資訊')}\n"
                                desc_text += f"薪資：{job.get('薪資', '無資訊')}\n"
                                desc_text += f"地點：{job.get('地點', '無資訊')}\n"
                                desc_text += f"聯絡方式：{job.get('聯絡方式', '無資訊')}\n"
                                if job.get('其他'):
                                    desc_text += f"其他：{job.get('其他')}\n"
                                if i < len(description):
                                    desc_text += "\n" + "="*30 + "\n\n"
                        else:
                            desc_text = str(description)
                        
                        zf.writestr(desc_text_name, desc_text)
        else:
            # 單一圖像情況
            for filename, image_data in image_storage[process_id].items():
                # 添加圖片
                zf.writestr(filename, image_data['binary'])
                
                # 添加描述（如果不是偵錯圖片）
                if not any(debug_type in filename for debug_type in ['_original', '_mask_', '_final_combined']):
                    description = get_image_description(process_id, filename)
                    desc_text_name = f"{os.path.splitext(filename)[0]}_description.txt"
                    
                    # 將工作列表轉換為可讀的表格格式
                    if isinstance(description, list) and description:
                        desc_text = "工作資訊分析結果\n" + "="*50 + "\n\n"
                        for i, job in enumerate(description, 1):
                            if len(description) > 1:
                                desc_text += f"工作 {i}\n" + "-"*20 + "\n"
                            desc_text += f"工作：{job.get('工作', '無資訊')}\n"
                            desc_text += f"時間：{job.get('時間', '無資訊')}\n"
                            desc_text += f"薪資：{job.get('薪資', '無資訊')}\n"
                            desc_text += f"地點：{job.get('地點', '無資訊')}\n"
                            desc_text += f"聯絡方式：{job.get('聯絡方式', '無資訊')}\n"
                            if job.get('其他'):
                                desc_text += f"其他：{job.get('其他')}\n"
                            if i < len(description):
                                desc_text += "\n" + "="*30 + "\n\n"
                    else:
                        desc_text = str(description)
                    
                    zf.writestr(desc_text_name, desc_text)
    
    # 將指針移到檔案開頭
    memory_file.seek(0)
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'newspaper_blocks_{process_id}.zip'
    )

# 定期清理功能
def cleanup_old_data(max_age_hours=24):
    """清理超過指定時間的資料"""
    import time
    from datetime import datetime, timedelta
    
    # 注意：這個實作假設我們在資料中添加時間戳記
    # 在實際使用中，您可能需要追蹤每個 process_id 的創建時間
    pass

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') 