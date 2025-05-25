from flask import Flask, request, render_template, redirect, url_for, send_from_directory, send_file, session, flash, make_response
import os
import cv2
import numpy as np
from werkzeug.utils import secure_filename
import uuid
import shutil
import zipfile
import io
import google.generativeai as genai
from PIL import Image
import base64
from io import BytesIO
import json
import secrets
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

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

def check_and_get_rotation_direction(image):
    """使用Gemini API檢查圖片方向，返回需要旋轉的方向信息"""
    
    # 從session中獲取API密鑰
    api_key = session.get('gemini_api_key', '')
    
    if not api_key:
        print("未設置Gemini API密鑰，跳過方向檢查")
        return "正確"
    
    try:
        # 配置API密鑰，並設定temperature、top_k、top_p讓生成結果固定
        genai.configure(api_key=api_key)
        MODEL = genai.GenerativeModel(
            'gemini-2.0-flash-001',
            generation_config={
                "temperature": 0.0,
                "top_k": 1,
                "top_p": 0.0
            }
        )
        
        # 生成四個方向的圖片
        orientations = {
            "正確": image,
            "順時針90度": cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE),
            "180度": cv2.rotate(image, cv2.ROTATE_180),
            "逆時針90度": cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        }
        
        print("開始分析四個方向的圖片...")
        scores = {}
        
        # 對每個方向進行評分
        for orientation_name, rotated_image in orientations.items():
            try:
                # 將OpenCV圖片轉換為PIL格式
                image_rgb = cv2.cvtColor(rotated_image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(image_rgb)
                
                # 調用Gemini API進行評分
                prompt = f"""你現在是一個專門判斷圖片方向的AI助手。請仔細觀察這張圖片中的文字閱讀方向。

請給這張圖片的文字可讀性打分，分數範圍是1到10（可以包含小數點，例如7.5）：
- 10分：文字完全正確，可以正常閱讀
- 7-9分：文字基本正確，稍有傾斜但可讀
- 4-6分：文字有明顯問題，但還能勉強辨識
- 1-3分：文字完全顛倒或側向，無法正常閱讀

請只回覆一個數字分數（例如：8.5），不要加任何其他說明文字。"""
                
                response = MODEL.generate_content([prompt, pil_image])
                score_text = response.text.strip()
                
                # 嘗試解析分數
                try:
                    score = float(score_text)
                    # 確保分數在1-10範圍內
                    score = max(1.0, min(10.0, score))
                    scores[orientation_name] = score
                    print(f"{orientation_name}: {score}分")
                except ValueError:
                    print(f"無法解析{orientation_name}的分數: {score_text}")
                    scores[orientation_name] = 1.0
                    
            except Exception as e:
                print(f"評估{orientation_name}時出錯: {str(e)}")
                scores[orientation_name] = 1.0
        
        # 找出得分最高的方向
        if scores:
            best_orientation = max(scores, key=scores.get)
            best_score = scores[best_orientation]
            
            print(f"各方向得分: {scores}")
            print(f"最佳方向: {best_orientation} (得分: {best_score})")
            
            # 如果最高分低於6分，可能圖片質量有問題，返回原始方向
            if best_score < 6.0:
                print("所有方向得分都較低，可能圖片質量有問題，保持原始方向")
                return "正確"
            
            # 根據最佳方向返回需要的旋轉操作
            if best_orientation == "正確":
                return "正確"
            elif best_orientation == "順時針90度":
                return "順時針90度"
            elif best_orientation == "180度":
                return "180度"
            elif best_orientation == "逆時針90度":
                return "逆時針90度"
        
        return "正確"
        
    except Exception as e:
        print(f"圖片方向檢查出錯: {str(e)}")
        return "正確"

def apply_rotation_to_image(image, rotation_direction):
    """根據旋轉方向旋轉圖片"""
    if rotation_direction == "順時針90度":
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    elif rotation_direction == "180度":
        return cv2.rotate(image, cv2.ROTATE_180)
    elif rotation_direction == "逆時針90度":
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    elif rotation_direction == "正確":
        return image
    else:
        # 如果是未知的方向，保持原圖
        print(f"未知的旋轉方向: {rotation_direction}，保持原圖")
        return image

def check_and_correct_image_orientation(image):
    """使用Gemini API檢查圖片方向並自動糾正（保留舊函數以向後兼容）"""
    rotation_direction = check_and_get_rotation_direction(image)
    return apply_rotation_to_image(image, rotation_direction)

def process_image_data(image, process_id, image_name):
    """處理圖像並儲存結果"""
    from image_processor import process_image as original_process_image
    import tempfile
    import shutil
    
    # 首先檢查圖片需要旋轉的方向，但不立即旋轉
    print(f"開始檢查圖片方向: {image_name}")
    rotation_direction = check_and_get_rotation_direction(image)
    print(f"檢測到需要旋轉方向: {rotation_direction}")
    
    # 創建臨時目錄進行處理
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 使用原始圖片進行處理（不旋轉）
        print("使用原始圖片進行區塊分割處理...")
        original_process_image(image, temp_dir, image_name)
        
        # 將處理結果儲存
        if process_id not in image_storage:
            image_storage[process_id] = {}
        
        # 遍歷臨時目錄中的所有圖片檔案
        processed_files = []
        for filename in os.listdir(temp_dir):
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                file_path = os.path.join(temp_dir, filename)
                
                # 讀取圖片
                processed_image = cv2.imread(file_path)
                if processed_image is not None:
                    # 對處理後的圖片應用旋轉
                    rotated_image = apply_rotation_to_image(processed_image, rotation_direction)
                    
                    # 將旋轉後的圖片編碼為二進制資料
                    _, buffer = cv2.imencode('.jpg', rotated_image)
                    image_data = buffer.tobytes()
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                    
                    # 儲存圖片資料
                    image_storage[process_id][filename] = {
                        'base64': base64_data,
                        'binary': image_data,
                        'format': 'jpg'
                    }
                    processed_files.append(filename)
                else:
                    print(f"無法讀取處理後的圖片: {filename}")
        
        print(f"處理完成，共處理了 {len(processed_files)} 張圖片")
        if rotation_direction != "正確":
            print(f"所有圖片已根據檢測結果進行旋轉: {rotation_direction}")
        else:
            print("圖片方向正確，無需旋轉")
        
        return processed_files
        
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
            "行業": "",
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
            "行業": "",
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
        prompt = """請先仔細判斷這張圖片是否包含工作招聘、求職、就業相關的資訊。

        如果這張圖片不是工作相關的內容（例如：純粹的新聞報導、廣告、商品資訊、活動公告等），請回答空陣列 []。

        如果這張圖片確實包含工作招聘或就業相關資訊，請分析其中的所有工作崗位，並以JSON格式回答，包含一個工作列表，每個工作包含以下欄位：
        - 工作：工作職位或職業名稱
        - 行業：根據工作內容判斷屬於以下哪個行業分類，必須從下列選項中選擇一個：
          "農、林、漁、牧業"、"礦業及土石採取業"、"製造業"、"電力及燃氣供應業"、"用水供應及污染整治業"、"營建工程業"、"批發及零售業"、"運輸及倉儲業"、"住宿及餐飲業"、"出版影音及資通訊業"、"金融及保險業"、"不動產業"、"專業、科學及技術服務業"、"支援服務業"、"公共行政及國防；強制性社會安全"、"教育業"、"醫療保健及社會工作服務業"、"藝術、娛樂及休閒服務業"、"其他服務業"
        - 時間：工作時間或營業時間
        - 薪資：薪資待遇或收入
        - 地點：工作地點或地址
        - 聯絡方式：電話、地址或其他聯絡資訊
        - 其他：其他相關資訊或備註

        請用繁體中文回答，如果某個欄位沒有資訊請填入空字串。行業欄位必須從上述19個分類中選擇最合適的一個。
        請直接回答JSON格式的工作列表，不要包含其他說明文字。

        工作相關內容的範例格式：
        [
            {
                "工作": "服務員",
                "行業": "住宿及餐飲業",
                "時間": "9:00-18:00",
                "薪資": "時薪160元起",
                "地點": "台北市信義區",
                "聯絡方式": "02-1234-5678",
                "其他": "需輪班"
            }
        ]

        非工作相關內容請回答：[]

        重要提醒：
        - 只有明確的工作招聘、求職、徵人啟事才算工作相關
        - 純粹的商業廣告、新聞報導、產品介紹不算工作相關
        - 如果圖片內容模糊不清或無法確定，請回答 []"""
        
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
            required_fields = ["工作", "行業", "時間", "薪資", "地點", "聯絡方式", "其他"]
            for job in description_json:
                if isinstance(job, dict):
                    for field in required_fields:
                        if field not in job:
                            job[field] = ""
            
            # 如果沒有工作，返回一個空的提示
            if not description_json:
                return [{
                    "工作": "未識別到工作資訊",
                    "行業": "",
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
                "行業": "",
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
            "行業": "",
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
    # 從環境變數讀取 API key，如果 session 中沒有的話
    if not session.get('gemini_api_key'):
        env_api_key = os.environ.get('GEMINI_API_KEY', '')
        if env_api_key:
            session['gemini_api_key'] = env_api_key
    
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
                        process_image_data(image, page_process_id, image_name)
                
                pdf_document.close()
            else:
                # 單一圖像處理
                image = cv2.imread(file_path)
                if image is not None:
                    image_name = os.path.splitext(filename)[0]
                    process_image_data(image, process_id, image_name)
            
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
    invalid_jobs = ['未識別到工作資訊', '未設置Gemini API密鑰', '圖片不存在', '獲取描述時出錯', '不詳']
    
    # 首先檢查工作名稱是否有效
    if not job.get('工作') or job.get('工作') in invalid_jobs:
        return False
    
    # 檢查主要欄位中有多少個是"無資訊"
    main_fields = ['工作', '行業', '時間', '薪資', '地點', '聯絡方式']
    no_info_count = 0
    
    for field in main_fields:
        field_value = job.get(field, '')
        if field_value == '無資訊' or field_value == '':
            no_info_count += 1
    
    # 如果有4個或更多欄位是"無資訊"，則認為是無效工作
    if no_info_count >= 4:
        return False
    
    return True

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
                                job_info['來源圖片'] = filename  # 移除頁碼顯示，只保留檔名
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
    
    # 對圖片按工作數量從小到大排序
    def count_valid_jobs(image):
        """計算圖片中有效工作的數量"""
        if not image.get('description'):
            return 0
        return len([job for job in image['description'] if is_valid_job(job)])
    
    image_files.sort(key=count_valid_jobs)
    
    # 定義處理步驟的順序
    def get_step_order(debug_file):
        filename = debug_file['filename']
        if 'original' in filename:
            return 1
        elif 'mask_unprocessed' in filename:
            return 2
        elif 'mask_processed' in filename:
            return 3
        elif 'final_combined' in filename:
            return 4
        else:
            return 5
    
    # 先按頁碼排序，再按步驟順序排序
    debug_files.sort(key=lambda x: (int(x['page']), get_step_order(x)))
    
    return render_template('results.html', 
                          process_id=process_id, 
                          image_files=image_files,
                          debug_files=debug_files,
                          all_jobs=all_jobs,
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
    import csv
    from datetime import datetime
    
    # 獲取選擇的下載項目
    include_options = request.args.getlist('include')
    if not include_options:
        # 如果沒有指定，默認下載所有內容
        include_options = ['csv', 'sql', 'images', 'descriptions', 'readme']
    
    # 創建ZIP檔案
    memory_file = io.BytesIO()
    
    # 檢查是否為PDF
    pdf_page_keys = [key for key in image_storage.keys() if key.startswith(f"{process_id}_page")]
    
    if not pdf_page_keys and process_id not in image_storage:
        return "處理結果不存在", 404
    
    # 收集所有工作資訊 - 使用與results函數相同的過濾邏輯
    all_jobs = []
    all_images = []
    debug_images = []
    
    if pdf_page_keys:
        # PDF情況
        pdf_page_keys.sort(key=lambda x: int(x.split('_page')[-1]))
        
        for page_key in pdf_page_keys:
            page_num = page_key.split('_page')[-1]
            
            for filename, image_data in image_storage[page_key].items():
                if any(debug_type in filename for debug_type in ['_original', '_mask_', '_final_combined']):
                    # 處理步驟圖片
                    debug_images.append({
                        'filename': filename,
                        'page': page_num,
                        'data': image_data
                    })
                else:
                    # 獲取圖片描述
                    description = get_image_description(page_key, filename)
                    
                    # 檢查是否有有效的工作資訊 - 只有有效工作的圖片才會被包含
                    has_valid_jobs = any(is_valid_job(job) for job in description)
                    
                    if has_valid_jobs:
                        # 只包含在頁面上顯示的圖片
                        all_images.append({
                            'filename': filename,
                            'page': page_num,
                            'data': image_data,
                            'description': description
                        })
                        
                        # 收集工作資訊 - 只包含有效的工作
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
    else:
        # 單一圖像情況
        for filename, image_data in image_storage[process_id].items():
            if any(debug_type in filename for debug_type in ['_original', '_mask_', '_final_combined']):
                # 處理步驟圖片
                debug_images.append({
                    'filename': filename,
                    'page': '1',
                    'data': image_data
                })
            else:
                # 獲取圖片描述
                description = get_image_description(process_id, filename)
                
                # 檢查是否有有效的工作資訊 - 只有有效工作的圖片才會被包含
                has_valid_jobs = any(is_valid_job(job) for job in description)
                
                if has_valid_jobs:
                    # 只包含在頁面上顯示的圖片
                    all_images.append({
                        'filename': filename,
                        'page': '1',
                        'data': image_data,
                        'description': description
                    })
                    
                    # 收集工作資訊 - 只包含有效的工作
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
    
    # 對圖片按工作數量從小到大排序，與頁面顯示順序一致
    def count_valid_jobs_in_image(image):
        """計算圖片中有效工作的數量"""
        if not image.get('description'):
            return 0
        return len([job for job in image['description'] if is_valid_job(job)])
    
    all_images.sort(key=count_valid_jobs_in_image)
    
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        
        # 1. CSV 工作資料表
        if 'csv' in include_options and all_jobs:
            csv_content = io.StringIO()
            fieldnames = ['工作', '行業', '時間', '薪資', '地點', '聯絡方式', '其他', '來源圖片', '頁碼', '工作編號']
            writer = csv.DictWriter(csv_content, fieldnames=fieldnames)
            writer.writeheader()
            
            for job in all_jobs:
                # 清理資料，確保沒有None值
                clean_job = {}
                for field in fieldnames:
                    value = job.get(field, '')
                    clean_job[field] = value if value else ''
                writer.writerow(clean_job)
            
            zf.writestr('工作資料表.csv', csv_content.getvalue().encode('utf-8-sig'))
        
        # 2. SQL 資料庫檔案
        if 'sql' in include_options and all_jobs:
            sql_content = """-- 報紙工作廣告提取結果資料庫
-- 生成時間: {datetime}

-- 建立工作資訊表
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_title TEXT,
    industry TEXT,
    work_time TEXT,
    salary TEXT,
    location TEXT,
    contact TEXT,
    other_info TEXT,
    source_image TEXT,
    page_number TEXT,
    job_number TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 插入工作資料
""".format(datetime=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            for job in all_jobs:
                # SQL注入防護：轉義單引號
                def escape_sql(value):
                    if value is None:
                        return 'NULL'
                    return "'" + str(value).replace("'", "''") + "'"
                
                sql_content += f"""INSERT INTO jobs (job_title, industry, work_time, salary, location, contact, other_info, source_image, page_number, job_number) 
VALUES ({escape_sql(job.get('工作', ''))}, {escape_sql(job.get('行業', ''))}, {escape_sql(job.get('時間', ''))}, {escape_sql(job.get('薪資', ''))}, {escape_sql(job.get('地點', ''))}, {escape_sql(job.get('聯絡方式', ''))}, {escape_sql(job.get('其他', ''))}, {escape_sql(job.get('來源圖片', ''))}, {escape_sql(job.get('頁碼', ''))}, {escape_sql(job.get('工作編號', ''))});
"""
            
            sql_content += f"\n-- 總計插入 {len(all_jobs)} 筆工作資料\n"
            zf.writestr('工作資料庫.sql', sql_content.encode('utf-8'))
        
        # 3. 工作區塊圖片
        if 'images' in include_options:
            for image in all_images:
                arcname = f"images/{image['filename']}"
                zf.writestr(arcname, image['data']['binary'])
        
        # 4. AI 分析描述
        if 'descriptions' in include_options:
            for image in all_images:
                if image['description']:
                    desc_filename = f"descriptions/{os.path.splitext(image['filename'])[0]}_description.txt"
                    
                    # 將工作列表轉換為可讀的表格格式 - 只包含有效工作
                    if isinstance(image['description'], list) and image['description']:
                        # 過濾出有效工作
                        valid_jobs = [job for job in image['description'] if is_valid_job(job)]
                        
                        if valid_jobs:  # 只有當有有效工作時才生成描述檔案
                            desc_text = f"工作資訊分析結果 - {image['filename']}\n" + "="*60 + "\n\n"
                            for i, job in enumerate(valid_jobs, 1):
                                if len(valid_jobs) > 1:
                                    desc_text += f"工作 {i}\n" + "-"*30 + "\n"
                                desc_text += f"工作職位：{job.get('工作', '無資訊')}\n"
                                desc_text += f"所屬行業：{job.get('行業', '無資訊')}\n"
                                desc_text += f"工作時間：{job.get('時間', '無資訊')}\n"
                                desc_text += f"薪資待遇：{job.get('薪資', '無資訊')}\n"
                                desc_text += f"工作地點：{job.get('地點', '無資訊')}\n"
                                desc_text += f"聯絡方式：{job.get('聯絡方式', '無資訊')}\n"
                                if job.get('其他'):
                                    desc_text += f"其他資訊：{job.get('其他')}\n"
                                desc_text += f"來源圖片：{image['filename']}\n"
                                if image['page'] != '1':
                                    desc_text += f"頁碼：第 {image['page']} 頁\n"
                                if i < len(valid_jobs):
                                    desc_text += "\n" + "="*40 + "\n\n"
                            
                            zf.writestr(desc_filename, desc_text.encode('utf-8'))
        
        # 5. 處理步驟圖片
        if 'processing_steps' in include_options:
            for debug_img in debug_images:
                arcname = f"processing_steps/{debug_img['filename']}"
                zf.writestr(arcname, debug_img['data']['binary'])
        
        # 6. 說明文件
        if 'readme' in include_options:
            readme_content = f"""報紙工作廣告區塊提取結果
================================

生成時間：{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
處理ID：{process_id}

統計資訊
--------
• 總工作崗位數：{len(all_jobs)}
• 有效圖片數：{len(all_images)}
• 處理步驟圖片數：{len(debug_images)}
• 是否為PDF：{'是' if pdf_page_keys else '否'}

檔案結構說明
------------
"""
            
            if 'csv' in include_options:
                readme_content += "• 工作資料表.csv - 所有工作資訊的結構化表格，可用Excel開啟\n"
            
            if 'sql' in include_options:
                readme_content += "• 工作資料庫.sql - 完整的SQL資料庫建表和插入語句\n"
            
            if 'images' in include_options:
                readme_content += "• images/ - 所有識別出的工作廣告區塊圖片\n"
            
            if 'descriptions' in include_options:
                readme_content += "• descriptions/ - 每張圖片的詳細AI分析描述文字檔\n"
            
            if 'processing_steps' in include_options:
                readme_content += "• processing_steps/ - 圖像處理的各個步驟圖片\n"
                readme_content += "  - *_original.jpg: 原始圖像\n"
                readme_content += "  - *_mask_unprocessed.jpg: 初始區塊檢測\n"
                readme_content += "  - *_mask_processed.jpg: 區塊優化處理\n"
                readme_content += "  - *_final_combined.jpg: 最終結果展示\n"
            
            readme_content += f"""
工作資訊欄位說明
--------------
• 工作：工作職位或職業名稱
• 行業：所屬行業分類（共19個標準分類）
• 時間：工作時間或營業時間
• 薪資：薪資待遇或收入
• 地點：工作地點或地址
• 聯絡方式：電話、地址或其他聯絡資訊
• 其他：其他相關資訊或備註

技術資訊
--------
• AI模型：Google Gemini 2.0 Flash Lite
• 圖像處理：OpenCV + 自定義區塊分割算法
• 方向檢測：四方向評分系統
• 資料格式：UTF-8編碼

使用說明
--------
1. CSV檔案可直接用Excel或其他試算表軟體開啟
2. SQL檔案可匯入SQLite、MySQL等資料庫系統
3. 圖片檔案按原始檔名組織，便於對照
4. 描述檔案提供詳細的文字分析結果

注意事項
--------
• 所有工作資訊由AI自動識別，建議人工核實
• 圖片品質會影響識別準確度
• 部分欄位可能為空，表示該資訊未在圖片中識別出

版權聲明
--------
本工具由報紙工作廣告區塊提取系統生成
僅供學習和研究使用
"""
            
            zf.writestr('README.txt', readme_content.encode('utf-8'))
    
    # 將指針移到檔案開頭
    memory_file.seek(0)
    
    # 根據選擇的內容生成檔名
    content_types = []
    if 'csv' in include_options:
        content_types.append('CSV')
    if 'sql' in include_options:
        content_types.append('SQL')
    if 'images' in include_options:
        content_types.append('圖片')
    if 'descriptions' in include_options:
        content_types.append('描述')
    if 'processing_steps' in include_options:
        content_types.append('步驟')
    
    if len(content_types) == 5:  # 包含所有內容
        filename_suffix = '完整'
    elif len(content_types) == 1:
        filename_suffix = content_types[0]
    else:
        filename_suffix = '+'.join(content_types)
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'報紙工作提取_{filename_suffix}_{process_id[:8]}.zip'
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