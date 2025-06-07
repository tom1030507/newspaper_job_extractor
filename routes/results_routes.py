"""
結果顯示路由模組
處理結果頁面、圖片查看和下載相關的路由
"""
import os
import io
import csv
import zipfile
import base64
from datetime import datetime
from flask import Blueprint, render_template, send_file, request, jsonify
from config.settings import Config
from models.storage import image_storage
from utils.file_utils import is_valid_job, get_page_sort_key

results_bp = Blueprint('results', __name__)

def generate_base64_from_file(file_path):
    """從檔案路徑動態生成 base64 編碼"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                image_data = f.read()
                return base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        print(f"生成 base64 失敗: {e}")
    return None

@results_bp.route('/results/<process_id>')
def show_results(process_id):
    """顯示處理結果頁面"""
    # 檢查是否有此處理ID的資料
    image_files = []
    debug_files = []
    all_jobs = []  # 統一的工作列表
    is_pdf = False
    
    # 檢查是否為PDF或多檔案（尋找帶有 _page 或 _file 的處理ID）
    pdf_page_keys = [key for key in image_storage._storage.keys() if key.startswith(f"{process_id}_page")]
    multi_file_keys = [key for key in image_storage._storage.keys() if key.startswith(f"{process_id}_file")]
    
    # 收集所有需要處理的圖片和對應的 process_id
    batch_requests = []  # [(process_id, filename, page_num), ...]
    
    if pdf_page_keys:
        is_pdf = True
        # 按頁碼排序
        pdf_page_keys.sort(key=lambda x: int(x.split('_page')[-1]))
        
        for page_key in pdf_page_keys:
            page_num = page_key.split('_page')[-1]
            
            for filename, image_data in image_storage._storage[page_key].items():
                # 檢查是否為偵錯圖像
                if any(debug_type in filename for debug_type in ['_original', '_mask_', '_final_combined']):
                    # 動態生成 base64
                    base64_data = generate_base64_from_file(image_data.get('file_path', ''))
                    if base64_data:
                        debug_files.append({
                            'filename': filename,
                            'page': page_num,
                            'base64': base64_data,
                            'format': image_data['format']
                        })
                else:
                    # 收集需要處理的圖片
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
            
            for filename, image_data in image_storage._storage[file_key].items():
                # 檢查是否為偵錯圖像
                if any(debug_type in filename for debug_type in ['_original', '_mask_', '_final_combined']):
                    # 動態生成 base64
                    base64_data = generate_base64_from_file(image_data.get('file_path', ''))
                    if base64_data:
                        debug_files.append({
                            'filename': filename,
                            'page': file_display,
                            'base64': base64_data,
                            'format': image_data['format']
                        })
                else:
                    # 收集需要處理的圖片
                    batch_requests.append((file_key, filename, file_display, image_data))
    elif process_id in image_storage._storage:
        # 單一圖像處理
        for filename, image_data in image_storage._storage[process_id].items():
            if any(debug_type in filename for debug_type in ['_original', '_mask_', '_final_combined']):
                # 動態生成 base64
                base64_data = generate_base64_from_file(image_data.get('file_path', ''))
                if base64_data:
                    debug_files.append({
                        'filename': filename,
                        'page': '1',
                        'base64': base64_data,
                        'format': image_data['format']
                    })
            else:
                # 收集需要處理的圖片
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
            if process_key in image_storage._storage and filename in image_storage._storage[process_key] and 'description' in image_storage._storage[process_key][filename]:
                description = image_storage._storage[process_key][filename]['description']
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
                # 動態生成 base64
                base64_data = generate_base64_from_file(image_data.get('file_path', ''))
                if base64_data:
                    image_files.append({
                        'filename': filename,
                        'page': page_num,
                        'base64': base64_data,
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
    
    # 先按頁碼排序，再按步驟順序排序
    debug_files.sort(key=lambda x: (get_page_sort_key(x['page']), get_step_order(x)))
    
    return render_template('results.html', 
                          process_id=process_id, 
                          image_files=image_files,
                          debug_files=debug_files,
                          all_jobs=all_jobs,
                          is_pdf=is_pdf,
                          model_name=Config.GEMINI_MODEL_NAME)

@results_bp.route('/view_image/<process_id>/<filename>')
def view_image(process_id, filename):
    """查看指定的圖片"""
    # 檢查是否存在該圖片
    if process_id in image_storage._storage and filename in image_storage._storage[process_id]:
        file_path = image_storage._storage[process_id][filename]['file_path']
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='image/jpeg')
    
    # 檢查PDF頁面
    pdf_page_keys = [key for key in image_storage._storage.keys() if key.startswith(f"{process_id}_page")]
    for page_key in pdf_page_keys:
        if filename in image_storage._storage[page_key]:
            file_path = image_storage._storage[page_key][filename]['file_path']
            if os.path.exists(file_path):
                return send_file(file_path, mimetype='image/jpeg')
    
    # 檢查多檔案
    multi_file_keys = [key for key in image_storage._storage.keys() if key.startswith(f"{process_id}_file")]
    for file_key in multi_file_keys:
        if filename in image_storage._storage[file_key]:
            file_path = image_storage._storage[file_key][filename]['file_path']
            if os.path.exists(file_path):
                return send_file(file_path, mimetype='image/jpeg')
    
    return "圖像不存在", 404

@results_bp.route('/download/<process_id>')
def download_results(process_id):
    """下載處理結果"""
    # 獲取選擇的下載項目
    include_options = request.args.getlist('include')
    if not include_options:
        # 如果沒有指定，默認下載所有內容
        include_options = ['csv', 'sql', 'images', 'descriptions', 'readme']
    
    # 創建ZIP檔案
    memory_file = io.BytesIO()
    
    # 檢查是否為PDF或多檔案
    pdf_page_keys = [key for key in image_storage._storage.keys() if key.startswith(f"{process_id}_page")]
    multi_file_keys = [key for key in image_storage._storage.keys() if key.startswith(f"{process_id}_file")]
    
    if not pdf_page_keys and not multi_file_keys and process_id not in image_storage._storage:
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
            
            for filename, image_data in image_storage._storage[page_key].items():
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
            
            for filename, image_data in image_storage._storage[file_key].items():
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
        for filename, image_data in image_storage._storage[process_id].items():
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
            if process_key in image_storage._storage and \
               filename in image_storage._storage[process_key] and \
               'description' in image_storage._storage[process_key][filename]:
                description = image_storage._storage[process_key][filename]['description']
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
            sql_content = f"""-- 報紙工作廣告提取結果資料庫
-- 生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

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
"""
            
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