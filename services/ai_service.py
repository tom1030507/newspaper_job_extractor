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
import concurrent.futures
from functools import partial
from typing import Tuple, Dict, List, Any
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
    
    def configure_api(self, api_key: str) -> None:
        """配置 Gemini API"""
        genai.configure(api_key=api_key)
    
    def evaluate_single_orientation(self, api_key: str, orientation_name: str, rotated_image: np.ndarray) -> Tuple[str, float]:
        """評估單個方向的圖片 - 用於多線程處理"""
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
    
    def check_image_orientation(self, image: np.ndarray, api_key: str, parallel_process: bool = True) -> str:
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
                
                # 使用 ThreadPoolExecutor 並行處理四個方向
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # 創建部分函數，固定 api_key 參數
                    evaluate_func = partial(self.evaluate_single_orientation, api_key)
                    
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
                        orientation_name, score = self.evaluate_single_orientation(api_key, orientation_name, rotated_image)
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
                
                return best_orientation
            
            return "正確"
            
        except Exception as e:
            print(f"圖片方向檢查出錯: {str(e)}")
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
    
    def analyze_job_from_image(self, api_key: str, image_path: str) -> List[Dict[str, Any]]:
        """從圖片中分析工作資訊"""
        
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

# 創建全域 AI 服務實例
ai_service = AIService() 