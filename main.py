import cv2
import numpy as np
import imutils
import os

# 定義旋轉校正函數
def correct_rotation(block):
    """將圖片逆時針旋轉 90 度以校正方向"""
    return imutils.rotate_bound(block, -90)

# 檢查一個輪廓是否被另一個輪廓包含
def is_contained(contour1, contour2):
    """檢查 contour1 是否完全被 contour2 包含"""
    x1, y1, w1, h1 = cv2.boundingRect(contour1)
    x2, y2, w2, h2 = cv2.boundingRect(contour2)
    
    # 檢查 contour1 的四個角落是否都在 contour2 內
    return (x1 >= x2 and y1 >= y2 and 
            (x1 + w1) <= (x2 + w2 + 10) and (y1 + h1) <= (y2 + h2 + 10))

# 1. 創建用於保存分割圖片的資料夾
image_name = 'newspaper1'  # 報紙圖片名稱
output_folder = image_name + '_blocks'
if not os.path.exists(output_folder):
    os.makedirs(output_folder)
    print(f"已創建資料夾：{output_folder}")

# 2. 讀取圖片
image = cv2.imread(image_name + '.jpg')  
if image is None:
    print("無法讀取圖片，請檢查路徑！")
    exit()

# 3. 預處理圖片
# 轉為灰階
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
# 應用高斯模糊去除噪音
blurred = cv2.GaussianBlur(gray, (5, 5), 0)
# 自適應閾值處理，突出邊界
thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                              cv2.THRESH_BINARY_INV, 11, 2)
# 使用 Canny 邊緣檢測
edges = cv2.Canny(thresh, 100, 200)

# 4. 檢測輪廓
contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# 5. 過濾過大的輪廓
max_area_threshold = 0.3 * image.shape[0] * image.shape[1]  # 假設最大面積為圖片總面積的 30%
filtered_contours = []
for contour in contours:
    x, y, w, h = cv2.boundingRect(contour)
    area = w * h
    if area > max_area_threshold:
        print(f"輪廓面積 {area} 過大，跳過...")
        continue
    filtered_contours.append(contour)

# 6. 處理每個輪廓並分割
blocks = []
for i, contour in enumerate(filtered_contours):
    # 獲取輪廓的邊界框
    x, y, w, h = cv2.boundingRect(contour)
    
    # 過濾掉太小的噪點（根據寬高閾值）
    if w > 120 and h > 120 and w / h < 5 and h / w < 5:
        # 檢查是否被其他輪廓包含
        is_contained_by_others = False
        for j, other_contour in enumerate(filtered_contours):
            if i != j:  # 不與自己比較
                if is_contained(contour, other_contour):
                    is_contained_by_others = True
                    break
        
        # 如果被其他輪廓包含，則跳過
        if is_contained_by_others:
            print(f"輪廓 {i} 被其他輪廓包含，跳過...")
            continue
        
        # 裁剪出單獨的欄位
        job_block = image[y:y+h, x:x+w]
        
        # 檢查是否需要旋轉（假設右側欄位需要旋轉）
        if x > image.shape[1] / 2:  # 如果欄位在圖片右半邊，假設需要旋轉
            job_block = correct_rotation(job_block)
        
        # 保存分割後的圖片到指定資料夾，使用 x_y_w_h 命名
        output_path = os.path.join(output_folder, f'{x}_{y}_{w}_{h}.png')
        cv2.imwrite(output_path, job_block)
        print(f"已保存：{output_path}")
        
        # 保存區塊資訊
        blocks.append((x, y, w, h))

# 7. 合併所有區塊並填補缺漏部分
if blocks:
    min_x = min(blocks, key=lambda b: b[0])[0]
    min_y = min(blocks, key=lambda b: b[1])[1]
    max_x = max(blocks, key=lambda b: b[0] + b[2])[0] + max(blocks, key=lambda b: b[0] + b[2])[2]
    max_y = max(blocks, key=lambda b: b[1] + b[3])[1] + max(blocks, key=lambda b: b[1] + b[3])[3]
    
    combined_image = np.zeros((max_y - min_y, max_x - min_x, 3), dtype=np.uint8)
    
    for x, y, w, h in blocks:
        combined_image[y - min_y:y - min_y + h, x - min_x:x - min_x + w] = image[y:y + h, x:x + w]
    
    # 填補缺漏部分
    for y in range(0, combined_image.shape[0], 120):
        for x in range(0, combined_image.shape[1], 120):
            if np.sum(combined_image[y:y + 120, x:x + 120]) == 0:
                # 確保形狀匹配
                h_fill = min(120, combined_image.shape[0] - y)
                w_fill = min(120, combined_image.shape[1] - x)
                combined_image[y:y + h_fill, x:x + w_fill] = image[min_y + y:min_y + y + h_fill, min_x + x:min_x + x + w_fill]
    
    # 保存合併後的圖片
    combined_output_path = os.path.join(output_folder, image_name + '_combined.png')
    cv2.imwrite(combined_output_path, combined_image)
    print(f"已保存合併圖片：{combined_output_path}")

print("分割完成！")