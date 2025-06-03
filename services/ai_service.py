"""
AI 分析服務
使用 Google Gemini API 進行圖片方向檢測和工作資訊提取
"""
import cv2
import numpy as np
import google.generativeai as genai
from PIL import Image
import json
import time
import re
import concurrent.futures
from functools import partial
from typing import Tuple, Dict, List, Any, Optional
from config.settings import Config

class AIService:
    """AI 分析服務類"""
    
    def __init__(self):
        self.model_name = Config.GEMINI_MODEL_NAME
        self.vision_model = Config.GEMINI_VISION_MODEL
        self.temperature = Config.GEMINI_TEMPERATURE
        self.top_k = Config.GEMINI_TOP_K
        self.top_p = Config.GEMINI_TOP_P
        self.max_workers = Config.MAX_WORKERS
        self.progress_tracker = None  # 將在後續設置
    
    def set_progress_tracker(self, progress_tracker):
        """設置進度追蹤器"""
        self.progress_tracker = progress_tracker
    
    def parse_api_error(self, error_message: str) -> Dict[str, Any]:
        """解析 API 錯誤訊息，提取重試延遲時間"""
        error_info = {
            'is_rate_limit': False,
            'retry_delay': 0,
            'quota_metric': '',
            'quota_value': 0,
            'description': str(error_message)
        }
        
        try:
            # 檢查是否為 429 錯誤
            if '429' in error_message:
                error_info['is_rate_limit'] = True
                
                # 提取 retry_delay 中的 seconds
                retry_match = re.search(r'retry_delay\s*{\s*seconds:\s*(\d+)', error_message)
                if retry_match:
                    error_info['retry_delay'] = int(retry_match.group(1))
                
                # 提取 quota_metric
                quota_metric_match = re.search(r'quota_metric:\s*"([^"]+)"', error_message)
                if quota_metric_match:
                    error_info['quota_metric'] = quota_metric_match.group(1)
                
                # 提取 quota_value
                quota_value_match = re.search(r'quota_value:\s*(\d+)', error_message)
                if quota_value_match:
                    error_info['quota_value'] = int(quota_value_match.group(1))
                    
                # 如果沒有找到具體的重試時間，使用預設值
                if error_info['retry_delay'] == 0:
                    error_info['retry_delay'] = 60  # 預設等待60秒
                    
        except Exception as e:
            print(f"解析錯誤訊息時出錯: {str(e)}")
            
        return error_info
    
    def wait_with_progress_update(self, process_id: str, wait_seconds: int, error_info: Dict[str, Any]):
        """等待重試延遲時間，並更新進度顯示"""
        if not self.progress_tracker:
            print(f"等待 {wait_seconds} 秒後重試...")
            time.sleep(wait_seconds)
            return
            
        quota_info = ""
        if error_info['quota_metric']:
            quota_info = f"（限制: {error_info['quota_value']}/分鐘）"
            
        for remaining in range(wait_seconds, 0, -1):
            description = f"API 請求頻率超限{quota_info}，等待 {remaining} 秒後自動重試..."
            self.progress_tracker.update_progress(
                process_id, 
                "analyze", 
                70,  # 固定在70%顯示等待狀態
                description
            )
            time.sleep(1)
            
        # 重試前的訊息
        self.progress_tracker.update_progress(
            process_id, 
            "analyze", 
            75, 
            "重新嘗試 API 請求..."
        )

    def configure_api(self, api_key: str) -> None:
        """配置 Gemini API"""
        genai.configure(api_key=api_key)
    
    def evaluate_single_orientation(self, api_key: str, orientation_name: str, rotated_image: np.ndarray, process_id: Optional[str] = None, max_retries: int = None) -> Tuple[str, float]:
        """評估單個方向的圖片 - 用於多線程處理，支援重試機制"""
        
        if max_retries is None:
            max_retries = Config.GEMINI_ORIENTATION_MAX_RETRIES
        
        for retry_attempt in range(max_retries + 1):
            try:
                # 為每個線程創建獨立的 API 配置
                genai.configure(api_key=api_key)
                MODEL = genai.GenerativeModel(
                    self.vision_model,
                    generation_config={
                        "temperature": self.temperature,
                        "top_k": self.top_k,
                        "top_p": self.top_p
                    }
                )
                
                # 將OpenCV圖片轉換為PIL格式
                image_rgb = cv2.cvtColor(rotated_image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(image_rgb)
                
                # 調用Gemini API進行評分
                prompt = """你是一位專業的報紙排版分析師。請判斷這張圖片中的報紙內容是否為正常的閱讀方向。主要依據以下幾點：
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
                
                # 獲取評分
                score_text = response.text.strip()
                
                try:
                    # 清理文字，移除非數字字符（保留小數點）
                    cleaned_score_text = re.sub(r'[^\d.]', '', score_text)
                    if not cleaned_score_text:
                        print(f"無法從 {orientation_name} 回應中提取分數: '{score_text}'")
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
                error_message = str(e)
                print(f"評估{orientation_name}時出錯: {error_message}")
                
                # 解析錯誤訊息
                error_info = self.parse_api_error(error_message)
                
                # 如果是 API 限制錯誤且還有重試次數
                if error_info['is_rate_limit'] and retry_attempt < max_retries:
                    retry_count = retry_attempt + 1
                    remaining_retries = max_retries - retry_attempt
                    
                    print(f"方向檢測 API 限制錯誤，第 {retry_count} 次重試，剩餘 {remaining_retries} 次重試機會")
                    
                    # 等待重試（方向檢測通常不需要太長時間，縮短等待時間）
                    wait_time = min(error_info['retry_delay'], 30)  # 最多等待30秒
                    if process_id and self.progress_tracker:
                        # 簡化的等待訊息
                        self.progress_tracker.update_progress(
                            process_id, 
                            "process", 
                            30, 
                            f"方向檢測遇到限制，等待 {wait_time} 秒後重試..."
                        )
                        time.sleep(wait_time)
                    else:
                        time.sleep(wait_time)
                    
                    continue  # 重試
                else:
                    # 非限制錯誤或重試次數已用完
                    return orientation_name, 1.0
        
        # 重試次數用完
        return orientation_name, 1.0
    
    def check_image_orientation(self, image: np.ndarray, api_key: str, parallel_process: bool = True, process_id: Optional[str] = None) -> str:
        """檢查圖片方向，返回需要旋轉的方向信息"""
        
        if not api_key:
            print("未設置Gemini API密鑰，跳過方向檢查")
            return "正確"
        
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
                
                # 使用線程池並行處理
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                    # 創建部分函數，綁定 api_key 和 process_id
                    evaluate_func = partial(self.evaluate_single_orientation, api_key, process_id=process_id)
                    
                    # 提交所有任務
                    future_to_orientation = {
                        executor.submit(evaluate_func, name, img): name 
                        for name, img in orientations.items()
                    }
                    
                    # 收集結果
                    scores = {}
                    for future in concurrent.futures.as_completed(future_to_orientation):
                        orientation_name, score = future.result()
                        scores[orientation_name] = score
                
                elapsed_time = time.time() - start_time
                print(f"並行分析完成，耗時: {elapsed_time:.2f} 秒")
            else:
                print("開始順序分析四個方向的圖片...")
                start_time = time.time()
                
                scores = {}
                for orientation_name, rotated_image in orientations.items():
                    orientation_name, score = self.evaluate_single_orientation(
                        api_key, orientation_name, rotated_image, process_id
                    )
                    scores[orientation_name] = score
                
                elapsed_time = time.time() - start_time
                print(f"順序分析完成，耗時: {elapsed_time:.2f} 秒")
            
            # 找出最高分的方向
            best_orientation = max(scores.items(), key=lambda x: x[1])
            best_name, best_score = best_orientation
            
            print(f"所有方向評分: {scores}")
            print(f"最佳方向: {best_name} (分數: {best_score})")
            
            return best_name
            
        except Exception as e:
            print(f"檢查圖片方向時出錯: {str(e)}")
            return "正確"
    
    def apply_rotation_to_image(self, image: np.ndarray, rotation_direction: str) -> np.ndarray:
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
    
    def analyze_job_from_image(self, api_key: str, image_path: str, process_id: Optional[str] = None, max_retries: int = None) -> List[Dict[str, Any]]:
        """從圖片中分析工作資訊，支援 API 限制錯誤重試"""
        
        if max_retries is None:
            max_retries = Config.GEMINI_MAX_RETRIES
        
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

        for retry_attempt in range(max_retries + 1):
            try:
                # 為每個線程創建獨立的 API 配置
                genai.configure(api_key=api_key)
                MODEL = genai.GenerativeModel(self.model_name)
                
                # 讀取圖片
                img = Image.open(image_path)
                
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
                error_message = str(e)
                print(f"獲取圖片描述時出錯: {error_message}")
                
                # 解析錯誤訊息
                error_info = self.parse_api_error(error_message)
                
                # 如果是 API 限制錯誤且還有重試次數
                if error_info['is_rate_limit'] and retry_attempt < max_retries:
                    retry_count = retry_attempt + 1
                    remaining_retries = max_retries - retry_attempt
                    
                    print(f"API 限制錯誤，第 {retry_count} 次重試，剩餘 {remaining_retries} 次重試機會")
                    
                    # 向前端發送錯誤訊息和重試資訊
                    if process_id and self.progress_tracker:
                        self.wait_with_progress_update(process_id, error_info['retry_delay'], error_info)
                    else:
                        time.sleep(error_info['retry_delay'])
                    
                    continue  # 重試
                else:
                    # 非限制錯誤或重試次數已用完
                    if error_info['is_rate_limit']:
                        error_detail = f"API 請求頻率超限，已重試 {max_retries} 次仍失敗"
                    else:
                        error_detail = error_message
                        
                    return [{
                        "工作": "獲取描述時出錯",
                        "行業": "",
                        "時間": "",
                        "薪資": "",
                        "地點": "",
                        "聯絡方式": "",
                        "其他": error_detail
                    }]
        
        # 不應該到這裡，但以防萬一
        return [{
            "工作": "獲取描述時出錯",
            "行業": "",
            "時間": "",
            "薪資": "",
            "地點": "",
            "聯絡方式": "",
            "其他": "未知錯誤"
        }]

# 創建全域 AI 服務實例
ai_service = AIService() 