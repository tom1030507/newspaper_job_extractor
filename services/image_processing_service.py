"""
圖像處理服務
整合圖片處理、方向檢測和AI分析功能
"""
import os
import cv2
import time
import base64
import tempfile
import shutil
import concurrent.futures
import gc
from functools import partial
from typing import List, Dict, Any, Optional
from models.storage import image_storage
from services.ai_service import ai_service
from services.progress_tracker import progress_tracker
from image_processor import process_image as original_process_image

class ImageProcessingService:
    """圖像處理服務類"""
    
    def __init__(self):
        self.storage = image_storage
        self.ai_service = ai_service
        self.progress_tracker = progress_tracker
        # 設置 AI 服務的進度追蹤器
        self.ai_service.set_progress_tracker(progress_tracker)
    
    def process_image_data(self, image, process_id: str, image_name: str, 
                          progress_start: int = 10, progress_range: int = 50,
                          api_key: str = "", auto_rotate: bool = True,
                          results_folder: str = "results") -> List[str]:
        """處理圖像並儲存結果"""
        
        # 更新進度：開始圖像處理
        self.progress_tracker.update_progress(process_id, "process", progress_start, f"開始處理圖像: {image_name}")
        
        if auto_rotate:
            # 檢查圖片方向
            direction_check_progress = progress_start + int(progress_range * 0.4)  # 40%完成方向檢測準備
            self.progress_tracker.update_progress(process_id, "process", direction_check_progress, f"檢查圖片方向: {image_name}")
            
            # 提取原始的 process_id（移除 _page 或 _file 後綴）以便進度追蹤
            original_process_id = process_id
            if '_page' in process_id:
                original_process_id = process_id.split('_page')[0]
            elif '_file' in process_id:
                original_process_id = process_id.split('_file')[0]
            
            rotation_direction = self.ai_service.check_image_orientation(
                image, api_key, parallel_process=True, process_id=original_process_id
            )
            print(f"檢測到需要旋轉方向: {rotation_direction}")
            direction_done_progress = progress_start + int(progress_range * 0.6)  # 60%完成方向檢測
            self.progress_tracker.update_progress(process_id, "process", direction_done_progress, f"方向檢測完成: {rotation_direction}")
        else:
            print(f"自動校正方向已停用，跳過方向檢查: {image_name}")
            rotation_direction = "正確"
            direction_done_progress = progress_start + int(progress_range * 0.6)
            self.progress_tracker.update_progress(process_id, "process", direction_done_progress, "跳過方向檢測")
        
        # 創建臨時目錄進行處理
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 使用原始圖片進行處理（不旋轉）
            print("使用原始圖片進行區塊分割處理...")
            segment_start_progress = progress_start + int(progress_range * 0.65)
            self.progress_tracker.update_progress(process_id, "process", segment_start_progress, "執行區塊分割處理")
            
            # 使用執行緒池來執行 CPU 密集型任務，避免阻塞伺服器
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(original_process_image, image, temp_dir, image_name)
                future.result()  # 等待圖像處理完成
            
            segment_done_progress = progress_start + int(progress_range * 0.8)
            self.progress_tracker.update_progress(process_id, "process", segment_done_progress, "區塊分割處理完成")
            
            # 將處理結果儲存到本地檔案系統
            
            # 創建此次處理的結果目錄
            # 提取原始process_id（去除_page或_file後綴）
            base_process_id = process_id
            if '_page' in process_id:
                base_process_id = process_id.split('_page')[0]
            elif '_file' in process_id:
                base_process_id = process_id.split('_file')[0]
            
            process_result_dir = os.path.join(results_folder, base_process_id, process_id)
            os.makedirs(process_result_dir, exist_ok=True)
            
            # 遍歷臨時目錄中的所有圖片檔案
            processed_files = []
            total_files = len([f for f in os.listdir(temp_dir) if f.endswith(('.jpg', '.jpeg', '.png'))])
            processed_count = 0
            
            file_process_start_progress = progress_start + int(progress_range * 0.85)
            self.progress_tracker.update_progress(process_id, "process", file_process_start_progress, f"處理 {total_files} 個輸出檔案")
            
            for filename in os.listdir(temp_dir):
                if filename.endswith(('.jpg', '.jpeg', '.png')):
                    file_path = os.path.join(temp_dir, filename)
                    
                    # 讀取圖片
                    processed_image = cv2.imread(file_path)
                    if processed_image is not None:
                        # 對處理後的圖片應用旋轉
                        rotated_image = self.ai_service.apply_rotation_to_image(processed_image, rotation_direction)
                        
                        # 將旋轉後的圖片保存到結果目錄
                        result_file_path = os.path.join(process_result_dir, filename)
                        cv2.imwrite(result_file_path, rotated_image)
                        
                        # 獲取檔案大小（不再生成 base64）
                        file_size = os.path.getsize(result_file_path)
                        
                        # 只儲存檔案路徑和元數據（移除 base64 以節省記憶體）
                        self.storage.store_image(process_id, filename, {
                            'file_path': result_file_path,
                            'format': 'jpg',
                            'size': file_size
                        })
                        processed_files.append(filename)
                        processed_count += 1
                        
                        # 立即釋放圖像記憶體
                        del processed_image, rotated_image
                        
                        # 更新進度
                        file_process_progress = file_process_start_progress + int((processed_count / total_files) * (progress_range * 0.15))
                        self.progress_tracker.update_progress(process_id, "process", file_process_progress, f"已處理 {processed_count}/{total_files} 個檔案")
                    else:
                        print(f"無法讀取處理後的圖片: {filename}")
            
            print(f"處理完成，共處理了 {len(processed_files)} 張圖片")
            final_progress = progress_start + progress_range
            if rotation_direction != "正確":
                print(f"所有圖片已根據檢測結果進行旋轉: {rotation_direction}")
                self.progress_tracker.update_progress(process_id, "process", final_progress, f"圖片旋轉完成: {rotation_direction}")
            else:
                print("圖片方向正確，無需旋轉")
                self.progress_tracker.update_progress(process_id, "process", final_progress, "圖片處理完成")
            
            # 強制垃圾回收以釋放記憶體
            del image  # 明確刪除原始圖像
            gc.collect()
            print(f"圖像處理完成，已執行記憶體清理")
            
            return processed_files
            
        finally:
            # 清理臨時目錄
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def analyze_images_batch(self, process_id: str, image_names: List[str], 
                           api_key: str, already_processed: int = 0, 
                           total_global_images: Optional[int] = None,
                           parallel_process: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """批量分析多張圖片"""
        
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
        self.progress_tracker.update_progress(process_id, "analyze", 60, f"開始 AI 分析 {len(image_names)} 張圖片")
        
        if parallel_process:
            print(f"開始並行處理 {len(image_names)} 張圖片的描述...")
            start_time = time.time()
            
            # 使用並行處理
            
            # 創建部分函數，固定參數
            analyze_func = partial(self._analyze_single_image, api_key, process_id)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(image_names))) as executor:
                # 提交所有任務
                future_to_image = {
                    executor.submit(analyze_func, image_name): image_name
                    for image_name in image_names
                }
                
                results = {}
                completed_count = 0
                
                # 收集結果
                for future in concurrent.futures.as_completed(future_to_image):
                    completed_count += 1
                    try:
                        image_name, description = future.result()
                        results[image_name] = description
                        
                        # 更新 AI 分析進度 (60-95%) - 使用全局進度
                        global_completed = already_processed + completed_count
                        progress = 60 + int((global_completed / total_global_images) * 35)
                        self.progress_tracker.update_progress(process_id, "analyze", progress, f"已分析 {global_completed}/{total_global_images} 張圖片")
                        
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
                self.progress_tracker.update_progress(process_id, "analyze", progress, f"分析圖片 {global_completed}/{total_global_images}: {image_name}")
                
                try:
                    image_name, description = self._analyze_single_image(api_key, process_id, image_name)
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
        self.progress_tracker.update_progress(process_id, "analyze", 95, "AI 分析完成")
        
        # 強制垃圾回收以釋放 AI 分析過程中的記憶體
        gc.collect()
        print(f"AI 分析完成，已執行記憶體清理")
        
        return results
    
    def _analyze_single_image(self, api_key: str, process_id: str, image_name: str) -> tuple:
        """分析單張圖片 - 內部方法"""
        
        # 檢查圖片是否存在
        image_data = self.storage.get_image(process_id, image_name)
        if not image_data:
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
            # 使用檔案路徑進行分析，傳遞 process_id 以支援重試機制
            if 'file_path' in image_data and os.path.exists(image_data['file_path']):
                # 提取原始的 process_id（移除 _page 或 _file 後綴）以便進度追蹤
                original_process_id = process_id
                if '_page' in process_id:
                    original_process_id = process_id.split('_page')[0]
                elif '_file' in process_id:
                    original_process_id = process_id.split('_file')[0]
                    
                description = self.ai_service.analyze_job_from_image(
                    api_key, 
                    image_data['file_path'], 
                    original_process_id  # 傳遞 process_id 以支援進度更新和重試
                )
            else:
                return image_name, [{
                    "工作": "無法讀取圖片",
                    "行業": "", "時間": "", "薪資": "",
                    "地點": "", "聯絡方式": "", "其他": "圖片檔案不存在"
                }]
            
            print(f"處理完成圖片: {image_name}, 找到 {len(description)} 個工作")
            return image_name, description
            
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

# 創建全域圖像處理服務實例
image_processing_service = ImageProcessingService() 