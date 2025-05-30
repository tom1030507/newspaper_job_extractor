from flask import Flask, request, render_template, redirect, url_for, send_from_directory, send_file, session, flash, make_response, jsonify
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
import requests  # 添加 requests 庫用於發送 HTTP 請求
from datetime import datetime
import threading
import concurrent.futures
from functools import partial
import time
from flask_socketio import SocketIO, emit
import pandas as pd
import schedule

# 載入環境變數
load_dotenv()

# 使用當前目錄作為靜態文件目錄，這樣可以直接訪問結果目錄
app = Flask(__name__, static_folder='.', static_url_path='')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULTS_FOLDER'] = 'results'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上傳檔案大小為16MB
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg'}
app.config['SECRET_KEY'] = secrets.token_hex(16)  # 添加密鑰用於session加密

# 初始化 SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# 設定Gemini API相關配置

# 全局變數存儲圖片和工作資訊
image_storage = {}  # 改為存儲檔案路徑和元數據
job_storage = {}

# 進度追蹤字典 - 存儲每個 process_id 的進度資訊
progress_storage = {}

# 確保上傳目錄存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)  # 確保結果目錄存在

def update_progress(process_id, step, progress, description=""):
    """更新處理進度並通過 SocketIO 發送到前端"""
    
    # 提取原始的 process_id（移除 _page 或 _file 後綴）
    original_process_id = process_id
    if '_page' in process_id:
        original_process_id = process_id.split('_page')[0]
    elif '_file' in process_id:
        original_process_id = process_id.split('_file')[0]
    
    progress_data = {
        'step': step,
        'progress': progress,
        'description': description,
        'timestamp': time.time()
    }
    
    # 儲存進度資訊（使用原始process_id）
    progress_storage[original_process_id] = progress_data
    
    # 通過 SocketIO 發送到前端（使用原始process_id）
    socketio.emit('progress_update', {
        'process_id': original_process_id,
        **progress_data
    })
    
    print(f"進度更新 [{original_process_id}]: {step} - {progress}% - {description}")

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def evaluate_single_orientation(api_key, orientation_name, rotated_image):
    """評估單個方向的圖片 - 用於多線程處理"""
    try:
        # 為每個線程創建獨立的 API 配置
        genai.configure(api_key=api_key)
        MODEL = genai.GenerativeModel(
            'gemini-2.0-flash-001',
            generation_config={
                "temperature": 0.0,
                "top_k": 1,
                "top_p": 0.0
            }
        )
        
        # 將OpenCV圖片轉換為PIL格式
        image_rgb = cv2.cvtColor(rotated_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        
        # 調用Gemini API進行評分
        prompt = f"""你是一位專業的報紙排版分析師。請判斷這張圖片中的報紙內容是否為正常的閱讀方向。主要依據以下幾點：
1.  **標題方向**：報紙的大標題是否水平且易讀？
2.  **欄位方向**：內文的文字欄位是否垂直排列，且文字是水平的？
3.  **圖片方向**：如果圖片中有可辨識的人物或物體，其方向是否自然？
4.  **整體佈局**：報紙的整體版面配置是否符合常見的閱讀習慣？

請給這個方向的「自然閱讀程度」打分，分數範圍 1 到 10：
- 10分：完全正常，所有元素方向正確。
- 7-9分：基本正常，可能有輕微傾斜但整體閱讀方向正確。
- 4-6分：方向有明顯問題，如文字是垂直的或倒置的，但仍能辨識出部分內容。
- 1-3分：完全錯誤，無法辨識為正常的報紙閱讀方向。

請「僅僅」回覆一個「阿拉伯數字」表示的分數（例如：8.5 或 7），「絕對不要」包含任何其他文字、標點符號、空格或額外說明。"""
        
        response = MODEL.generate_content([prompt, pil_image])
        score_text = response.text.strip()
        
        # 嘗試解析分數
        try:
            # 清理分數文字，移除空格並處理可能的 "1. 5" 這種情況
            cleaned_score_text = "".join(char for char in score_text if char.isdigit() or char == '.')
            # 確保小數點只有一個，且在數字中間
            if cleaned_score_text.count('.') > 1:
                # 如果有多個小數點，只保留第一個
                parts = cleaned_score_text.split('.')
                cleaned_score_text = parts[0] + '.' + "".join(parts[1:])
            
            # 再次嘗試移除開頭或結尾可能存在的多餘非數字字元 (除了點)
            cleaned_score_text = ''.join(filter(lambda x: x.isdigit() or x == '.', cleaned_score_text))
            if not cleaned_score_text or cleaned_score_text == '.': # 如果清理後為空或只剩小數點
                print(f"清理後的分數文字無效 ({orientation_name}): '{score_text}' -> '{cleaned_score_text}'")
                return orientation_name, 1.0

            score = float(cleaned_score_text)
            # 確保分數在1-10範圍內
            score = max(1.0, min(10.0, score))
            print(f"{orientation_name}: {score}分 (原始回應: '{score_text}')")
            return orientation_name, score
        except ValueError:
            print(f"無法解析{orientation_name}的分數: {score_text}")
            return orientation_name, 1.0
            
    except Exception as e:
        print(f"評估{orientation_name}時出錯: {str(e)}")
        return orientation_name, 1.0

def check_and_get_rotation_direction(image):
    """使用Gemini API檢查圖片方向，返回需要旋轉的方向信息（支援並行或序列處理）"""
    
    # 從session中獲取API密鑰
    api_key = session.get('gemini_api_key', '')
    
    if not api_key:
        print("未設置Gemini API密鑰，跳過方向檢查")
        return "正確"
    
    # 檢查是否啟用並行處理
    parallel_process = session.get('parallel_process', True)  # 默認啟用
    
    try:
        # 生成四個方向的圖片
        orientations = {
            "正確": image,
            "順時針90度": cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE),
            "180度": cv2.rotate(image, cv2.ROTATE_180),
            "逆時針90度": cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        }
        
        if parallel_process:
            print("開始並行分析四個方向的圖片...")
            start_time = time.time()
            
            # 使用 ThreadPoolExecutor 並行處理四個方向
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                # 創建部分函數，固定 api_key 參數
                evaluate_func = partial(evaluate_single_orientation, api_key)
                
                # 提交所有任務
                future_to_orientation = {
                    executor.submit(evaluate_func, orientation_name, rotated_image): orientation_name
                    for orientation_name, rotated_image in orientations.items()
                }
                
                scores = {}
                # 收集結果
                for future in concurrent.futures.as_completed(future_to_orientation):
                    try:
                        orientation_name, score = future.result()
                        scores[orientation_name] = score
                    except Exception as e:
                        orientation_name = future_to_orientation[future]
                        print(f"處理{orientation_name}時出錯: {str(e)}")
                        scores[orientation_name] = 1.0
        
            end_time = time.time()
            print(f"並行處理完成，耗時: {end_time - start_time:.2f}秒")
        else:
            # 序列處理
            print("開始序列分析四個方向的圖片...")
            start_time = time.time()
            
            scores = {}
            for orientation_name, rotated_image in orientations.items():
                print(f"分析方向: {orientation_name}")
                try:
                    orientation_name, score = evaluate_single_orientation(api_key, orientation_name, rotated_image)
                    scores[orientation_name] = score
                except Exception as e:
                    print(f"處理{orientation_name}時出錯: {str(e)}")
                    scores[orientation_name] = 1.0
            
            end_time = time.time()
            print(f"序列處理完成，耗時: {end_time - start_time:.2f}秒")
        
        # 找出得分最高的方向
        if scores:
            # 獲取所有方向的最高分
            max_score = 0
            for score_val in scores.values():
                if score_val is not None:
                    max_score = max(max_score, score_val)
            
            # 檢查 "正確" 方向的分數是否等於最高分，且 "正確" 方向的分數不為 None
            correct_score = scores.get("正確")
            if correct_score is not None and correct_score == max_score:
                print(f"各方向得分: {scores}")
                print(f"\'正確\' 方向得分為 {correct_score}，與最高分相同，優先選擇 \'正確\' 方向")
                return "正確"
            
            # 如果 "正確" 方向不是最高分，或分數為 None，則找出實際最高分的方向
            best_orientation = "正確" # 預設值
            current_max_score = 0.0 # 處理 scores 可能包含 None 的情況
            for orientation_name, score_val in scores.items():
                if score_val is not None and score_val > current_max_score:
                    current_max_score = score_val
                    best_orientation = orientation_name
                elif score_val is not None and score_val == current_max_score:
                    # 如果分數相同，且當前最佳方向不是 "正確"，則比較是否為 "正確"
                    if best_orientation != "正確" and orientation_name == "正確":
                        best_orientation = "正確"
            
            best_score = scores.get(best_orientation, 0.0) # 確保 best_score 有值
            if best_score is None: best_score = 0.0

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

def get_image_description_for_single_image(api_key, process_id, image_name):
    """為單張圖片獲取描述 - 用於多線程處理"""
    
    # 檢查圖片是否存在
    if process_id not in image_storage or image_name not in image_storage[process_id]:
        return image_name, [{
            "工作": "圖片不存在",
            "行業": "",
            "時間": "",
            "薪資": "",
            "地點": "",
            "聯絡方式": "",
            "其他": ""
        }]
    
    try:
        # 為每個線程創建獨立的 API 配置
        genai.configure(api_key=api_key)
        MODEL = genai.GenerativeModel('gemini-2.0-flash-lite')
        
        # 取得圖片資料
        if process_id in image_storage and image_name in image_storage[process_id]:
            image_info = image_storage[process_id][image_name]
            
            # 優先從本地檔案讀取
            if 'file_path' in image_info and os.path.exists(image_info['file_path']):
                img = Image.open(image_info['file_path'])
            elif 'binary' in image_info:  # 向後兼容舊數據
                image_data = image_info['binary']
                img = Image.open(BytesIO(image_data))
            else:
                return image_name, [{
                    "工作": "無法讀取圖片",
                    "行業": "", "時間": "", "薪資": "",
                    "地點": "", "聯絡方式": "", "其他": "圖片檔案不存在"
                }]
        else:
            return image_name, [{
                "工作": "圖片不存在",
                "行業": "", "時間": "", "薪資": "",
                "地點": "", "聯絡方式": "", "其他": ""
            }]
        
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
                return image_name, [{
                    "工作": "未識別到工作資訊",
                    "行業": "",
                    "時間": "",
                    "薪資": "",
                    "地點": "",
                    "聯絡方式": "",
                    "其他": "此圖片可能不包含就業相關資訊"
                }]
            
            print(f"處理完成圖片: {image_name}, 找到 {len(description_json)} 個工作")
            return image_name, description_json
            
        except json.JSONDecodeError:
            # 如果JSON解析失敗，嘗試從文字中提取資訊
            return image_name, [{
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
        return image_name, [{
            "工作": "獲取描述時出錯",
            "行業": "",
            "時間": "",
            "薪資": "",
            "地點": "",
            "聯絡方式": "",
            "其他": str(e)
        }]

def get_descriptions_for_multiple_images(process_id, image_names, already_processed=0, total_global_images=None):
    """為多張圖片獲取描述（支援並行或序列處理）"""
    
    # 從session中獲取API密鑰
    api_key = session.get('gemini_api_key', '')
    
    # 如果沒有設置API密鑰，返回默認訊息
    if not api_key:
        return {name: [{
            "工作": "未設置Gemini API密鑰",
            "行業": "",
            "時間": "",
            "薪資": "",
            "地點": "",
            "聯絡方式": "",
            "其他": "請在首頁設置API密鑰"
        }] for name in image_names}
    
    # 如果沒有提供全局總數，使用當前圖片數量
    if total_global_images is None:
        total_global_images = len(image_names)
        already_processed = 0
    
    # 更新進度：開始 AI 分析
    update_progress(process_id, "analyze", 60, f"開始 AI 分析 {len(image_names)} 張圖片")
    
    # 檢查是否啟用並行處理
    parallel_process = session.get('parallel_process', True)  # 默認啟用
    
    if parallel_process:
        print(f"開始並行處理 {len(image_names)} 張圖片的描述...")
        start_time = time.time()
        
        # 使用 ThreadPoolExecutor 並行處理多張圖片
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(image_names))) as executor:
            # 創建部分函數，固定 api_key 和 process_id 參數
            get_desc_func = partial(get_image_description_for_single_image, api_key, process_id)
            
            # 提交所有任務
            future_to_image = {
                executor.submit(get_desc_func, image_name): image_name
                for image_name in image_names
            }
            
            results = {}
            completed_count = 0
            total_images = len(image_names)
            
            # 收集結果
            for future in concurrent.futures.as_completed(future_to_image):
                completed_count += 1
                try:
                    image_name, description = future.result()
                    results[image_name] = description
                    
                    # 更新 AI 分析進度 (60-95%) - 使用全局進度
                    global_completed = already_processed + completed_count
                    progress = 60 + int((global_completed / total_global_images) * 35)
                    update_progress(process_id, "analyze", progress, f"已分析 {global_completed}/{total_global_images} 張圖片")
                    
                except Exception as e:
                    image_name = future_to_image[future]
                    print(f"處理 {image_name} 時出錯: {str(e)}")
                    results[image_name] = [{
                        "工作": "處理失敗",
                        "行業": "",
                        "時間": "",
                        "薪資": "",
                        "地點": "",
                        "聯絡方式": "",
                        "其他": str(e)
                    }]
        
        end_time = time.time()
        print(f"並行描述處理完成，耗時: {end_time - start_time:.2f}秒")
    else:
        # 序列處理
        print(f"開始序列處理 {len(image_names)} 張圖片的描述...")
        start_time = time.time()
        
        results = {}
        for i, image_name in enumerate(image_names, 1):
            print(f"處理圖片 {i}/{len(image_names)}: {image_name}")
            
            # 更新 AI 分析進度 (60-95%) - 使用全局進度
            global_completed = already_processed + i
            progress = 60 + int((global_completed - 1) / total_global_images * 35)
            update_progress(process_id, "analyze", progress, f"分析圖片 {global_completed}/{total_global_images}: {image_name}")
            
            try:
                image_name, description = get_image_description_for_single_image(api_key, process_id, image_name)
                results[image_name] = description
            except Exception as e:
                print(f"處理 {image_name} 時出錯: {str(e)}")
                results[image_name] = [{
                    "工作": "處理失敗",
                    "行業": "",
                    "時間": "",
                    "薪資": "",
                    "地點": "",
                    "聯絡方式": "",
                    "其他": str(e)
                }]
        
        end_time = time.time()
        print(f"序列描述處理完成，耗時: {end_time - start_time:.2f}秒")
    
    # AI 分析完成
    update_progress(process_id, "analyze", 95, "AI 分析完成")
    
    return results

def process_image_data(image, process_id, image_name, progress_start=10, progress_range=50):
    """處理圖像並儲存結果"""
    from image_processor import process_image as original_process_image
    import tempfile
    import shutil
    
    # 更新進度：開始圖像處理
    update_progress(process_id, "process", progress_start, f"開始處理圖像: {image_name}")
    
    # 檢查是否啟用自動校正方向
    auto_rotate = session.get('auto_rotate', True)  # 默認啟用
    
    if auto_rotate:
        # 首先檢查圖片需要旋轉的方向，但不立即旋轉
        print(f"開始檢查圖片方向: {image_name}")
        direction_check_progress = progress_start + int(progress_range * 0.2)  # 20%的範圍用於方向檢查
        update_progress(process_id, "process", direction_check_progress, f"檢查圖片方向: {image_name}")
        rotation_direction = check_and_get_rotation_direction(image)
        print(f"檢測到需要旋轉方向: {rotation_direction}")
        direction_done_progress = progress_start + int(progress_range * 0.6)  # 60%完成方向檢測
        update_progress(process_id, "process", direction_done_progress, f"方向檢測完成: {rotation_direction}")
    else:
        print(f"自動校正方向已停用，跳過方向檢查: {image_name}")
        rotation_direction = "正確"
        direction_done_progress = progress_start + int(progress_range * 0.6)
        update_progress(process_id, "process", direction_done_progress, "跳過方向檢測")
    
    # 創建臨時目錄進行處理
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 使用原始圖片進行處理（不旋轉）
        print("使用原始圖片進行區塊分割處理...")
        segment_start_progress = progress_start + int(progress_range * 0.65)
        update_progress(process_id, "process", segment_start_progress, "執行區塊分割處理")
        original_process_image(image, temp_dir, image_name)
        segment_done_progress = progress_start + int(progress_range * 0.8)
        update_progress(process_id, "process", segment_done_progress, "區塊分割處理完成")
        
        # 將處理結果儲存到本地檔案系統
        if process_id not in image_storage:
            image_storage[process_id] = {}
        
        # 創建此次處理的結果目錄
        # 提取原始process_id（去除_page或_file後綴）
        base_process_id = process_id
        if '_page' in process_id:
            base_process_id = process_id.split('_page')[0]
        elif '_file' in process_id:
            base_process_id = process_id.split('_file')[0]
        
        process_result_dir = os.path.join(app.config['RESULTS_FOLDER'], base_process_id, process_id)
        os.makedirs(process_result_dir, exist_ok=True)
        
        # 遍歷臨時目錄中的所有圖片檔案
        processed_files = []
        total_files = len([f for f in os.listdir(temp_dir) if f.endswith(('.jpg', '.jpeg', '.png'))])
        processed_count = 0
        
        file_process_start_progress = progress_start + int(progress_range * 0.85)
        update_progress(process_id, "process", file_process_start_progress, f"處理 {total_files} 個輸出檔案")
        
        for filename in os.listdir(temp_dir):
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                file_path = os.path.join(temp_dir, filename)
                
                # 讀取圖片
                processed_image = cv2.imread(file_path)
                if processed_image is not None:
                    # 對處理後的圖片應用旋轉
                    rotated_image = apply_rotation_to_image(processed_image, rotation_direction)
                    
                    # 將旋轉後的圖片保存到結果目錄
                    result_file_path = os.path.join(process_result_dir, filename)
                    cv2.imwrite(result_file_path, rotated_image)
                    
                    # 生成base64編碼（用於網頁顯示）
                    _, buffer = cv2.imencode('.jpg', rotated_image)
                    image_data = buffer.tobytes()
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                    
                    # 儲存檔案路徑和元數據（不存儲binary資料）
                    image_storage[process_id][filename] = {
                        'file_path': result_file_path,
                        'base64': base64_data,  # 暫時保留base64用於網頁顯示
                        'format': 'jpg',
                        'size': len(image_data)
                    }
                    processed_files.append(filename)
                    processed_count += 1
                    
                    # 更新進度
                    file_process_progress = file_process_start_progress + int((processed_count / total_files) * (progress_range * 0.15))
                    update_progress(process_id, "process", file_process_progress, f"已處理 {processed_count}/{total_files} 個檔案")
                else:
                    print(f"無法讀取處理後的圖片: {filename}")
        
        print(f"處理完成，共處理了 {len(processed_files)} 張圖片")
        final_progress = progress_start + progress_range
        if rotation_direction != "正確":
            print(f"所有圖片已根據檢測結果進行旋轉: {rotation_direction}")
            update_progress(process_id, "process", final_progress, f"圖片旋轉完成: {rotation_direction}")
        else:
            print("圖片方向正確，無需旋轉")
            update_progress(process_id, "process", final_progress, "圖片處理完成")
        
        return processed_files
        
    finally:
        # 清理臨時目錄
        shutil.rmtree(temp_dir, ignore_errors=True)

def get_image_description(process_id, image_name):
    """獲取圖片的AI描述（單張圖片版本，為了向後兼容）"""
    
    # 使用新的多線程版本來處理單張圖片
    results = get_descriptions_for_multiple_images(process_id, [image_name])
    return results.get(image_name, [{
        "工作": "獲取描述失敗",
        "行業": "",
        "時間": "",
        "薪資": "",
        "地點": "",
        "聯絡方式": "",
        "其他": ""
    }])

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
        
        # 檢查請求是否為 AJAX
        if request.headers.get('Content-Type', '').startswith('multipart/form-data'):
            # AJAX 請求，返回 JSON 響應
            return jsonify({'success': True, 'message': 'Gemini API密鑰已設置成功！'})
        else:
            # 傳統表單提交，使用 flash 和重定向
            flash('Gemini API密鑰已設置成功！', 'success')
            return redirect(url_for('index'))
    else:
        # 檢查請求是否為 AJAX
        if request.headers.get('Content-Type', '').startswith('multipart/form-data'):
            # AJAX 請求，返回 JSON 響應
            return jsonify({'success': False, 'message': 'API密鑰不能為空！'}), 400
        else:
            # 傳統表單提交，使用 flash 和重定向
            flash('API密鑰不能為空！', 'danger')
            return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'files' not in request.files:
        flash('未選擇檔案', 'danger')
        return redirect(url_for('index'))
    
    files = request.files.getlist('files')
    if not files or all(file.filename == '' for file in files):
        flash('未選擇檔案', 'danger')
        return redirect(url_for('index'))
    
    # 檢查是否已設置Gemini API密鑰
    if not session.get('gemini_api_key'):
        flash('請先設置Gemini API密鑰', 'warning')
        return redirect(url_for('index'))
    
    # 獲取處理選項
    auto_rotate = request.form.get('auto_rotate') == 'true'
    parallel_process = request.form.get('parallel_process') == 'true'
    
    # 將選項儲存到session中，供處理函數使用
    session['auto_rotate'] = auto_rotate
    session['parallel_process'] = parallel_process
    
    print(f"處理選項 - 自動校正方向: {auto_rotate}, 並行處理: {parallel_process}")
    
    # 檢查檔案數量限制
    MAX_FILES = 10
    if len(files) > MAX_FILES:
        flash(f'一次最多只能上傳 {MAX_FILES} 個檔案', 'danger')
        return redirect(url_for('index'))
    
    # 檢查所有檔案格式
    valid_files = []
    for file in files:
        if file.filename != '' and allowed_file(file.filename):
            valid_files.append(file)
        elif file.filename != '':
            flash(f'檔案 "{file.filename}" 格式不支援', 'danger')
            return redirect(url_for('index'))
    
    if not valid_files:
        flash('沒有有效的檔案', 'danger')
        return redirect(url_for('index'))
    
    # 創建唯一的處理ID
    process_id = str(uuid.uuid4())
    
    # 初始化進度追蹤
    update_progress(process_id, "upload", 5, "開始處理檔案")
    
    # 創建處理目錄
    process_dir = os.path.join(app.config['UPLOAD_FOLDER'], process_id)
    os.makedirs(process_dir, exist_ok=True)
    
    processed_files = []  # 記錄已處理的檔案，用於錯誤時清理
    
    try:
        file_counter = 0  # 用於為不同檔案創建唯一的處理ID
        total_files = len(valid_files)
        
        update_progress(process_id, "upload", 10, f"準備處理 {total_files} 個檔案")
        
        for file in valid_files:
            file_counter += 1
            
            # 更新檔案處理進度 - 為每個檔案分配合理的進度範圍
            file_start_progress = int((file_counter - 1) / total_files * 10)  # 當前檔案開始進度
            file_end_progress = int(file_counter / total_files * 10)  # 當前檔案結束進度
            update_progress(process_id, "upload", file_start_progress, f"處理檔案 {file_counter}/{total_files}: {file.filename}")
            
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
                # PDF 處理 - 為每個檔案分配10-60%範圍內的子進度
                import fitz
                file_process_start = 10 + int((file_counter - 1) / total_files * 50)  # 當前檔案在10-60%範圍內的起始點
                file_process_range = int(50 / total_files)  # 當前檔案可用的進度範圍
                
                update_progress(process_id, "process", file_process_start, f"開始處理 PDF {file_counter}/{total_files}: {original_filename}")
                pdf_document = fitz.open(file_path)
                # 使用原始檔名（不含副檔名）作為基礎名稱
                pdf_base_name = os.path.splitext(original_filename)[0]
                total_pages = len(pdf_document)
                
                for page_num in range(total_pages):
                    # 計算當前頁面在當前檔案進度範圍內的位置
                    page_progress_in_file = int((page_num / total_pages) * file_process_range)
                    current_progress = file_process_start + page_progress_in_file
                    update_progress(process_id, "process", current_progress, f"處理檔案 {file_counter}/{total_files} 第 {page_num + 1}/{total_pages} 頁")
                    
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
                        if len(valid_files) > 1:
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
                        
                        process_image_data(image, page_process_id, image_name, page_progress_start, page_progress_range)
                
                pdf_document.close()
            else:
                # 單一圖像處理 - 為每個檔案分配10-60%範圍內的子進度
                file_process_start = 10 + int((file_counter - 1) / total_files * 50)  # 當前檔案在10-60%範圍內的起始點
                file_process_range = int(50 / total_files)  # 當前檔案可用的進度範圍
                
                image = cv2.imread(file_path)
                if image is not None:
                    # 為多檔案場景調整處理ID和圖片名稱
                    if len(valid_files) > 1:
                        # 多檔案：包含檔案編號
                        image_name = f"file{file_counter:02d}_{os.path.splitext(original_filename)[0]}"
                        image_process_id = f"{process_id}_file{file_counter:02d}"
                    else:
                        # 單檔案：保持原有邏輯
                        image_name = os.path.splitext(original_filename)[0]
                        image_process_id = process_id
                    
                    # 傳遞進度範圍給process_image_data函數
                    process_image_data(image, image_process_id, image_name, file_process_start, file_process_range)
        
        # 在圖像處理完成後，立即執行 AI 分析
        update_progress(process_id, "analyze", 60, "開始 AI 分析")
        
        # 收集所有需要分析的圖片
        all_image_keys = []
        
        # 檢查是否為PDF或多檔案
        pdf_page_keys = [key for key in image_storage.keys() if key.startswith(f"{process_id}_page")]
        multi_file_keys = [key for key in image_storage.keys() if key.startswith(f"{process_id}_file")]
        
        if pdf_page_keys or multi_file_keys or process_id in image_storage:
            # 收集所有圖片進行批量分析
            batch_analysis_requests = {}  # {process_key: [filenames]}
            
            # 處理PDF頁面
            for page_key in pdf_page_keys:
                filenames = [fname for fname in image_storage[page_key].keys() 
                           if not any(debug_type in fname for debug_type in ['_original', '_mask_', '_final_combined'])]
                if filenames:
                    batch_analysis_requests[page_key] = filenames
            
            # 處理多檔案
            for file_key in multi_file_keys:
                filenames = [fname for fname in image_storage[file_key].keys() 
                           if not any(debug_type in fname for debug_type in ['_original', '_mask_', '_final_combined'])]
                if filenames:
                    batch_analysis_requests[file_key] = filenames
            
            # 處理單一圖像
            if process_id in image_storage and not pdf_page_keys and not multi_file_keys:
                filenames = [fname for fname in image_storage[process_id].keys() 
                           if not any(debug_type in fname for debug_type in ['_original', '_mask_', '_final_combined'])]
                if filenames:
                    batch_analysis_requests[process_id] = filenames
            
            # 執行批量AI分析
            total_images = sum(len(filenames) for filenames in batch_analysis_requests.values())
            if total_images > 0:
                update_progress(process_id, "analyze", 65, f"準備分析 {total_images} 張圖片")
                
                processed_images = 0
                for process_key, filenames in batch_analysis_requests.items():
                    if filenames:
                        descriptions = get_descriptions_for_multiple_images(process_key, filenames, processed_images, total_images)
                        processed_images += len(filenames)
                        
                        # 儲存AI分析結果
                        for filename, description in descriptions.items():
                            if process_key in image_storage and filename in image_storage[process_key]:
                                image_storage[process_key][filename]['description'] = description
        
        # AI 分析完成
        update_progress(process_id, "analyze", 95, "AI 分析完成")
        
        # 處理完成
        update_progress(process_id, "complete", 100, "所有檔案處理完成")
        
        # 處理成功，顯示成功訊息
        if len(valid_files) > 1:
            flash(f'成功處理了 {len(valid_files)} 個檔案', 'success')
        else:
            flash('檔案處理完成', 'success')
        
        # 重定向到結果頁面
        return redirect(url_for('results', process_id=process_id))
        
    except Exception as e:
        update_progress(process_id, "error", 0, f"處理錯誤: {str(e)}")
        flash(f'處理檔案時發生錯誤: {str(e)}', 'danger')
        return redirect(url_for('index'))
    
    finally:
        # 清理上傳的檔案
        for file_path in processed_files:
            if os.path.exists(file_path):
                os.remove(file_path)
        if os.path.exists(process_dir):
            shutil.rmtree(process_dir, ignore_errors=True)

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
    
    # 檢查是否為PDF或多檔案（尋找帶有 _page 或 _file 的處理ID）
    pdf_page_keys = [key for key in image_storage.keys() if key.startswith(f"{process_id}_page")]
    multi_file_keys = [key for key in image_storage.keys() if key.startswith(f"{process_id}_file")]
    
    # 收集所有需要處理的圖片和對應的 process_id
    batch_requests = []  # [(process_id, filename, page_num), ...]
    
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
                    # 收集需要批量處理的圖片
                    batch_requests.append((page_key, filename, page_num, image_data))
    elif multi_file_keys:
        # 多檔案處理
        # 按檔案編號排序
        multi_file_keys.sort(key=lambda x: x.split('_file')[-1])
        
        for file_key in multi_file_keys:
            # 解析檔案編號和可能的頁碼
            key_parts = file_key.replace(f"{process_id}_", "").split('_')
            if 'page' in file_key:
                # 多檔案PDF的情況：file01_page1
                file_part = key_parts[0]  # file01
                page_part = key_parts[1]  # page1
                page_num = page_part.replace('page', '')
                file_display = f"{file_part}_page{page_num}"
            else:
                # 多檔案圖片的情況：file01
                file_display = key_parts[0]
                page_num = file_display
            
            for filename, image_data in image_storage[file_key].items():
                # 檢查是否為偵錯圖像
                if any(debug_type in filename for debug_type in ['_original', '_mask_', '_final_combined']):
                    debug_files.append({
                        'filename': filename,
                        'page': file_display,
                        'base64': image_data['base64'],
                        'format': image_data['format']
                    })
                else:
                    # 收集需要批量處理的圖片
                    batch_requests.append((file_key, filename, file_display, image_data))
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
                # 收集需要批量處理的圖片
                batch_requests.append((process_id, filename, '1', image_data))
    else:
        return "處理結果不存在", 404
    
    # 從快取中讀取已分析的結果（AI分析已在上傳時完成）
    if batch_requests:
        print(f"從快取中讀取 {len(batch_requests)} 張圖片的分析結果...")
        
        # 直接從 image_storage 中讀取已分析的結果
        for process_key, filename, page_num, image_data in batch_requests:
            # 獲取已儲存的描述
            description = []
            if process_key in image_storage and filename in image_storage[process_key] and 'description' in image_storage[process_key][filename]:
                description = image_storage[process_key][filename]['description']
            else:
                # 如果沒有描述，可能是舊資料或分析失敗
                description = [{
                    "工作": "AI分析結果不存在",
                    "行業": "",
                    "時間": "",
                    "薪資": "",
                    "地點": "",
                    "聯絡方式": "",
                    "其他": "請重新上傳檔案進行分析"
                }]
            
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
                        if is_pdf:
                            job_info['來源圖片'] = filename
                            job_info['圖片編號'] = f"page{page_num}_{filename.split('.')[0]}"
                        else:
                            job_info['來源圖片'] = filename
                            job_info['圖片編號'] = filename.split('.')[0]
                        
                        if len([j for j in description if is_valid_job(j)]) > 1:
                            valid_jobs = [j for j in description if is_valid_job(j)]
                            job_index = valid_jobs.index(job) + 1
                            job_info['工作編號'] = f"工作 {job_index}"
                        else:
                            job_info['工作編號'] = ""
                        all_jobs.append(job_info)
    
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
    
    # 定義頁碼排序函數，處理多檔案情況
    def get_page_sort_key(page_str):
        """處理不同格式的頁碼字符串，返回可排序的元組"""
        try:
            # 如果是純數字，直接轉換
            return (0, int(page_str))
        except ValueError:
            # 如果包含文字，嘗試解析
            if 'file' in page_str and '_page' in page_str:
                # 格式：file01_page1
                parts = page_str.split('_page')
                file_part = parts[0]  # file01
                page_part = parts[1] if len(parts) > 1 else '1'
                
                # 提取檔案編號
                file_num = 0
                if 'file' in file_part:
                    try:
                        file_num = int(file_part.replace('file', ''))
                    except ValueError:
                        file_num = 0
                
                # 提取頁碼
                try:
                    page_num = int(page_part)
                except ValueError:
                    page_num = 1
                
                return (file_num, page_num)
            elif 'file' in page_str:
                # 格式：file01
                try:
                    file_num = int(page_str.replace('file', ''))
                    return (file_num, 0)  # 單頁圖片，頁碼為0
                except ValueError:
                    return (999, 0)  # 無法解析的放在最後
            else:
                # 其他格式，嘗試提取數字
                import re
                numbers = re.findall(r'\d+', page_str)
                if numbers:
                    return (0, int(numbers[0]))
                else:
                    return (999, 999)  # 無法解析的放在最後
    
    # 先按頁碼排序，再按步驟順序排序
    debug_files.sort(key=lambda x: (get_page_sort_key(x['page']), get_step_order(x)))
    
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
        file_path = image_storage[process_id][filename]['file_path']
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='image/jpeg')
    
    # 檢查PDF頁面
    pdf_page_keys = [key for key in image_storage.keys() if key.startswith(f"{process_id}_page")]
    for page_key in pdf_page_keys:
        if filename in image_storage[page_key]:
            file_path = image_storage[page_key][filename]['file_path']
            if os.path.exists(file_path):
                return send_file(file_path, mimetype='image/jpeg')
    
    # 檢查多檔案
    multi_file_keys = [key for key in image_storage.keys() if key.startswith(f"{process_id}_file")]
    for file_key in multi_file_keys:
        if filename in image_storage[file_key]:
            file_path = image_storage[file_key][filename]['file_path']
            if os.path.exists(file_path):
                return send_file(file_path, mimetype='image/jpeg')
    
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
    
    # 檢查是否為PDF或多檔案
    pdf_page_keys = [key for key in image_storage.keys() if key.startswith(f"{process_id}_page")]
    multi_file_keys = [key for key in image_storage.keys() if key.startswith(f"{process_id}_file")]
    
    if not pdf_page_keys and not multi_file_keys and process_id not in image_storage:
        return "處理結果不存在", 404
    
    # 收集所有工作資訊 - 使用與results函數相同的過濾邏輯
    all_jobs = []
    all_images = []
    debug_images = []
    batch_download_requests = []
    
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
                    # 收集需要批量處理的圖片
                    batch_download_requests.append((page_key, filename, page_num, image_data))
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
            
            for filename, image_data in image_storage[file_key].items():
                if any(debug_type in filename for debug_type in ['_original', '_mask_', '_final_combined']):
                    # 處理步驟圖片
                    debug_images.append({
                        'filename': filename,
                        'page': file_display,
                        'data': image_data
                    })
                else:
                    # 收集需要批量處理的圖片
                    batch_download_requests.append((file_key, filename, file_display, image_data))
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
                # 收集需要批量處理的圖片
                batch_download_requests.append((process_id, filename, '1', image_data))
    
    # 批量處理描述（使用與 results 函數相同的邏輯）
    if batch_download_requests:
        print(f"準備從快取中讀取 {len(batch_download_requests)} 張圖片的描述...")
        
        for process_key, filename, page_num, image_data in batch_download_requests:
            description = [] # Default to empty list
            if process_key in image_storage and \
               filename in image_storage[process_key] and \
               'description' in image_storage[process_key][filename]:
                description = image_storage[process_key][filename]['description']
            else:
                # 理論上不應該發生，因為 results 頁面應該已經填充了描述
                print(f"警告: 在 image_storage 中找不到圖片 {filename} (process_key: {process_key}) 的描述，將使用空描述。")
                description = [{
                    "工作": "描述未找到",
                    "行業": "", "時間": "", "薪資": "",
                    "地點": "", "聯絡方式": "", "其他": ""
                }]
            
            # 檢查是否有有效的工作資訊 - 只有有效工作的圖片才會被包含
            has_valid_jobs = any(is_valid_job(job) for job in description)
            
            if has_valid_jobs:
                # 只包含在頁面上顯示的圖片
                all_images.append({
                    'filename': filename,
                    'page': page_num,
                    'data': image_data, # image_data 包含 binary 和 base64
                    'description': description
                })
                
                # 收集工作資訊 - 只包含有效的工作
                if isinstance(description, list):
                    for i, job in enumerate(description):
                        if is_valid_job(job):
                            job_info = job.copy()
                            job_info['來源圖片'] = filename
                            job_info['頁碼'] = page_num
                            if page_num != '1': # 處理 PDF 和單張圖片的情況
                                job_info['圖片編號'] = f"page{page_num}_{filename.split('.')[0]}"
                            else:
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
                # 從本地檔案讀取圖片數據
                if 'file_path' in image['data'] and os.path.exists(image['data']['file_path']):
                    arcname = f"images/{image['filename']}"
                    with open(image['data']['file_path'], 'rb') as f:
                        image_binary = f.read()
                    zf.writestr(arcname, image_binary)
                elif 'binary' in image['data']:  # 向後兼容舊數據
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
                # 從本地檔案讀取圖片數據
                if 'file_path' in debug_img['data'] and os.path.exists(debug_img['data']['file_path']):
                    arcname = f"processing_steps/{debug_img['filename']}"
                    with open(debug_img['data']['file_path'], 'rb') as f:
                        image_binary = f.read()
                    zf.writestr(arcname, image_binary)
                elif 'binary' in debug_img['data']:  # 向後兼容舊數據
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

def cleanup_old_files(max_age_hours=4):
    """清理超過指定時間的檔案"""
    import time
    from datetime import datetime, timedelta
    
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    cutoff_timestamp = cutoff_time.timestamp()
    
    print(f"開始清理超過 {max_age_hours} 小時的檔案...")
    
    # 清理上傳目錄
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        for item in os.listdir(app.config['UPLOAD_FOLDER']):
            item_path = os.path.join(app.config['UPLOAD_FOLDER'], item)
            if os.path.isdir(item_path) and os.path.getctime(item_path) < cutoff_timestamp:
                shutil.rmtree(item_path)
                print(f"清理上傳目錄: {item_path}")
    
    # 清理結果目錄
    if os.path.exists(app.config['RESULTS_FOLDER']):
        for item in os.listdir(app.config['RESULTS_FOLDER']):
            item_path = os.path.join(app.config['RESULTS_FOLDER'], item)
            if os.path.isdir(item_path) and os.path.getctime(item_path) < cutoff_timestamp:
                shutil.rmtree(item_path)
                print(f"清理結果目錄: {item_path}")
                
                # 同時從memory storage中移除對應的記錄
                cleanup_memory_storage(item)

def cleanup_memory_storage(process_id):
    """清理記憶體中的過期資料"""
    # 清理所有相關的process_id記錄
    keys_to_remove = []
    for key in image_storage.keys():
        if key == process_id or key.startswith(f"{process_id}_"):
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del image_storage[key]
        print(f"清理記憶體資料: {key}")
    
    # 清理進度記錄
    if process_id in progress_storage:
        del progress_storage[process_id]
    
    # 清理工作資料
    if process_id in job_storage:
        del job_storage[process_id]

def get_storage_info():
    """獲取存儲使用情況"""
    total_files = 0
    total_size = 0
    
    if os.path.exists(app.config['RESULTS_FOLDER']):
        for root, dirs, files in os.walk(app.config['RESULTS_FOLDER']):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.exists(file_path):
                    total_files += 1
                    total_size += os.path.getsize(file_path)
    
    return {
        'total_files': total_files,
        'total_size_mb': round(total_size / (1024 * 1024), 2),
        'memory_processes': len(image_storage)
    }

@app.route('/send_to_spreadsheet/<process_id>', methods=['POST'])
def send_to_spreadsheet(process_id):
    """將處理結果發送到 Google Sheets"""
    try:
        # 從請求中獲取 Google Apps Script URL（現在變為可選）
        data = request.get_json() if request.get_json() else {}
        apps_script_url = data.get('apps_script_url', '')
        
        # 如果沒有提供 URL，使用默認的自動創建 Google Sheet 的 Apps Script
        if not apps_script_url:
            # TODO: 請將下面的 URL 替換為您實際部署的 Google Apps Script URL
            # 您可以在 Google Apps Script 部署後獲得真實的 URL
            apps_script_url = 'YOUR_ACTUAL_GOOGLE_APPS_SCRIPT_URL_HERE'  # 請替換為實際部署的 URL
            
            # 如果還沒有設置真實的 URL，返回錯誤
            if apps_script_url == 'YOUR_ACTUAL_GOOGLE_APPS_SCRIPT_URL_HERE':
                return jsonify({
                    'error': '請先設置 Google Apps Script URL',
                    'message': '請參考 GOOGLE_APPS_SCRIPT_SETUP.md 文件來部署您的 Google Apps Script，然後更新 app.py 中的 URL'
                }), 400
        
        # 收集職缺資料 - 使用與 results 和 download 相同的邏輯
        all_jobs = []
        
        # 檢查是否為PDF或多檔案
        pdf_page_keys = [key for key in image_storage.keys() if key.startswith(f"{process_id}_page")]
        multi_file_keys = [key for key in image_storage.keys() if key.startswith(f"{process_id}_file")]
        
        if pdf_page_keys:
            # PDF情況
            pdf_page_keys.sort(key=lambda x: int(x.split('_page')[-1]))
            
            for page_key in pdf_page_keys:
                page_num = page_key.split('_page')[-1]
                
                for filename, image_data in image_storage[page_key].items():
                    # 跳過偵錯圖像
                    if any(debug_type in filename for debug_type in ['_original', '_mask_', '_final_combined']):
                        continue
                    
                    # MODIFIED: 直接從 image_storage 獲取描述
                    description = []
                    if page_key in image_storage and \
                       filename in image_storage[page_key] and \
                       'description' in image_storage[page_key][filename]:
                        description = image_storage[page_key][filename]['description']
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
                
                for filename, image_data in image_storage[file_key].items():
                    # 跳過偵錯圖像
                    if any(debug_type in filename for debug_type in ['_original', '_mask_', '_final_combined']):
                        continue
                    
                    # MODIFIED: 直接從 image_storage 獲取描述
                    description = []
                    if file_key in image_storage and \
                       filename in image_storage[file_key] and \
                       'description' in image_storage[file_key][filename]:
                        description = image_storage[file_key][filename]['description']
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
        elif process_id in image_storage:
            # 單一圖像情況
            for filename, image_data in image_storage[process_id].items():
                # 跳過偵錯圖像
                if any(debug_type in filename for debug_type in ['_original', '_mask_', '_final_combined']):
                    continue
                
                # MODIFIED: 直接從 image_storage 獲取描述
                description = []
                if process_id in image_storage and \
                   filename in image_storage[process_id] and \
                   'description' in image_storage[process_id][filename]:
                    description = image_storage[process_id][filename]['description']
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
            response = requests.post(apps_script_url, json=payload, headers=headers, timeout=30)
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

@socketio.on('connect')
def handle_connect():
    """處理客戶端連接"""
    print(f"客戶端已連接: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """處理客戶端斷開連接"""
    print(f"客戶端已斷開: {request.sid}")

@socketio.on('get_progress')
def handle_get_progress(data):
    """處理客戶端請求進度資訊"""
    process_id = data.get('process_id')
    if process_id in progress_storage:
        emit('progress_update', {
            'process_id': process_id,
            **progress_storage[process_id]
        })

@app.route('/admin/storage')
def admin_storage():
    """管理員查看存儲狀態"""
    from datetime import datetime
    
    storage_info = get_storage_info()
    
    # 獲取最近的處理記錄
    recent_processes = []
    if os.path.exists(app.config['RESULTS_FOLDER']):
        for item in os.listdir(app.config['RESULTS_FOLDER']):
            item_path = os.path.join(app.config['RESULTS_FOLDER'], item)
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
    try:
        max_age_hours = request.json.get('max_age_hours', 4) if request.json else 4
        cleanup_old_files(max_age_hours)
        
        # 獲取清理後的存儲資訊
        storage_info = get_storage_info()
        
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

def start_cleanup_scheduler():
    """啟動定時清理任務"""
    def run_scheduled_cleanup():
        print("執行定時清理任務...")
        cleanup_old_files(4)  # 清理超過4小時的檔案
    
    # 設置每4小時執行一次清理
    schedule.every(4).hours.do(run_scheduled_cleanup)
    
    # 在背景執行緒中運行排程器
    def schedule_runner():
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分鐘檢查一次
    
    cleanup_thread = threading.Thread(target=schedule_runner, daemon=True)
    cleanup_thread.start()
    print("定時清理任務已啟動，每4小時執行一次")

@app.route('/admin/cleanup/auto', methods=['POST'])
def toggle_auto_cleanup():
    """切換自動清理功能"""
    try:
        enabled = request.json.get('enabled', True) if request.json else True
        
        if enabled:
            start_cleanup_scheduler()
            message = "自動清理已啟用，每4小時執行一次"
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

@app.route('/health')
def health_check():
    """健康檢查端點 - 用於Docker健康檢查"""
    try:
        # 檢查基本功能
        storage_info = get_storage_info()
        
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

@app.route('/api/status')
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
            'max_file_size_mb': app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024),
            'max_files_per_upload': 10,
            'supported_formats': list(app.config['ALLOWED_EXTENSIONS'])
        }
    })

if __name__ == '__main__':
    # 啟動定時清理任務
    start_cleanup_scheduler()
    
    # 立即執行一次清理（清理啟動時的舊檔案）
    cleanup_old_files(4)
    
    # 從環境變數讀取配置
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 啟動報紙工作廣告提取系統...")
    print(f"📡 伺服器地址: http://{host}:{port}")
    print(f"🔧 除錯模式: {debug}")
    print(f"🧹 自動清理: 每4小時執行")
    
    socketio.run(app, debug=debug, host=host, port=port) 