import cv2
import numpy as np
import os
import fitz

# 檢查一個邊界框是否被另一個邊界框包含
def is_contained_bbox(bbox1, bbox2, tolerance=10):
    """檢查 bbox1 是否完全包含在 bbox2 內（使用邊界框座標）"""
    x1, y1, w1, h1 = bbox1
    x2, y2, w2, h2 = bbox2
    return (x1 >= (x2 - tolerance) and y1 >= (y2 - tolerance) and
            (x1 + w1) <= (x2 + w2 + tolerance) and (y1 + h1) <= (y2 + h2 + tolerance))

# 計算兩個矩形之間的交集面積
def intersection_area(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
    yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])
    inter_width = xB - xA
    inter_height = yB - yA
    if inter_width > 0 and inter_height > 0:
        return inter_width * inter_height
    return 0

# 處理單一圖像的函數（直接接收圖像數據）
def process_image(image, output_folder, image_name):
    """處理圖像數據，提取區塊並保存結果 - 總是保存處理圖像"""
    if image is None:
        print(f"圖像數據為空，無法處理：{image_name}")
        return
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"創建資料夾：{output_folder}")

    # 總是保存原始圖像
    original_image_path = os.path.join(output_folder, f"{image_name}_original.jpg")
    cv2.imwrite(original_image_path, image)
    print(f"保存原始圖像：{original_image_path}")

    print(f"開始處理圖像：{image_name}，尺寸：{image.shape}")

    # 預處理圖像
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 11, 2)
    edges = cv2.Canny(thresh, 100, 200)
    print("圖像預處理完成")

    # 檢測輪廓
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"檢測到初始輪廓：{len(contours)}")

    # 過濾過大的輪廓
    max_area_threshold = 0.2 * image.shape[0] * image.shape[1]
    filtered_contours_size = []
    large_contours_count = 0
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area > max_area_threshold:
            large_contours_count += 1
            continue
        filtered_contours_size.append(contour)
    print(f"過濾掉 {large_contours_count} 個過大輪廓，剩餘：{len(filtered_contours_size)}")

    # 過濾小雜訊和長寬比不合適的輪廓
    valid_contours_initial = []
    small_noise_count = 0
    aspect_ratio_fail_count = 0
    min_dim = 120
    max_aspect_ratio = 5.0
    for contour in filtered_contours_size:
        x, y, w, h = cv2.boundingRect(contour)
        if w > min_dim and h > min_dim:
            if w / h < max_aspect_ratio and h / w < max_aspect_ratio:
                valid_contours_initial.append(contour)
            else:
                aspect_ratio_fail_count += 1
        else:
            small_noise_count += 1
    print(f"過濾掉 {small_noise_count} 個過小輪廓，{aspect_ratio_fail_count} 個長寬比不合適的輪廓，剩餘有效輪廓：{len(valid_contours_initial)}")

    # 第一次過濾包含關係（僅在初始輪廓之間）
    blocks_info = []
    contained_count_initial = 0
    initial_blocks_found = 0
    temp_initial_bboxes = [cv2.boundingRect(c) for c in valid_contours_initial]

    for i, contour in enumerate(valid_contours_initial):
        bbox_i = temp_initial_bboxes[i]
        if bbox_i is None:  # 跳過已移除的邊界框
            continue
        is_contained_by_others = False
        for j, other_bbox in enumerate(temp_initial_bboxes):
            if i != j and other_bbox is not None and is_contained_bbox(bbox_i, other_bbox):  # 確保 other_bbox 不為 None
                # 比較兩個邊界框的面積，保留較大的
                area_i = bbox_i[2] * bbox_i[3]
                area_j = other_bbox[2] * other_bbox[3]
                if area_i >= area_j:
                    # 保留 bbox_i，移除 other_bbox
                    temp_initial_bboxes[j] = None  # 標記為已移除
                else:
                    # 保留 other_bbox，移除 bbox_i
                    is_contained_by_others = True
                    break
        if is_contained_by_others:
            contained_count_initial += 1
            continue
        x, y, w, h = bbox_i
        x = max(0, x)
        y = max(0, y)
        w = min(w, image.shape[1] - x)
        h = min(h, image.shape[0] - y)
        if w > 0 and h > 0:
            blocks_info.append(((x, y, w, h), f'{x}_{y}_{x + w}_{y + h}.jpg'))
            initial_blocks_found += 1

    # 移除標記為 None 的邊界框
    temp_initial_bboxes = [bbox for bbox in temp_initial_bboxes if bbox is not None]

    print(f"第一次過濾：過濾掉 {contained_count_initial} 個被包含的輪廓，記錄了 {initial_blocks_found} 個初始區塊資訊。")

    initial_block_bboxes = [info[0] for info in blocks_info]

    # 處理未填充區域
    missing_areas_info = []
    if blocks_info:
        all_xs = [b[0] for b in initial_block_bboxes]
        all_ys = [b[1] for b in initial_block_bboxes]
        all_xws = [b[0] + b[2] for b in initial_block_bboxes]
        all_yhs = [b[1] + b[3] for b in initial_block_bboxes]

        min_x_overall = min(all_xs)
        min_y_overall = min(all_ys)
        max_x_overall = max(all_xws)
        max_y_overall = max(all_yhs)
        mask_height = max_y_overall - min_y_overall
        mask_width = max_x_overall - min_x_overall

        if mask_height > 0 and mask_width > 0:
            mask = np.zeros((mask_height, mask_width), dtype=np.uint8)
            for (x, y, w, h) in initial_block_bboxes:
                relative_y = y - min_y_overall
                relative_x = x - min_x_overall
                end_y = min(relative_y + h, mask_height)
                end_x = min(relative_x + w, mask_width)
                relative_y = max(0, relative_y)
                relative_x = max(0, relative_x)
                if end_y > relative_y and end_x > relative_x:
                    mask[relative_y:end_y, relative_x:end_x] = 255

            # 總是保存未處理的遮罩圖像
            mask_unprocessed_path = os.path.join(output_folder, f'{image_name}_mask_unprocessed.jpg')
            cv2.imwrite(mask_unprocessed_path, mask)
            print(f"保存未處理的遮罩圖像：{mask_unprocessed_path}")

            kernel_size = 30
            kernel = np.ones((kernel_size, kernel_size), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=3)
            mask = cv2.erode(mask, kernel, iterations=3)
            
            # 總是保存處理後的遮罩圖像
            mask_processed_path = os.path.join(output_folder, f'{image_name}_mask_processed.jpg')
            cv2.imwrite(mask_processed_path, mask)
            print(f"保存處理後的遮罩圖像：{mask_processed_path}")

            # 找到未填充區域並檢查重疊
            inv_mask = cv2.bitwise_not(mask)
            missing_contours, _ = cv2.findContours(inv_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            print(f"在處理後的遮罩中檢測到 {len(missing_contours)} 個潛在未填充區域輪廓。")

            min_area_threshold_missing = 5000
            min_dim_missing = 120
            max_aspect_ratio_missing = 5.0
            overlap_threshold = 0.50

            missing_area_found_count = 0
            skipped_missing_area_count_filter = 0
            skipped_missing_area_count_overlap = 0

            for i, contour in enumerate(missing_contours):
                area = cv2.contourArea(contour)
                if area < min_area_threshold_missing:
                    skipped_missing_area_count_filter += 1
                    continue

                x_rel, y_rel, w_rel, h_rel = cv2.boundingRect(contour)
                orig_x = min_x_overall + x_rel
                orig_y = min_y_overall + y_rel
                orig_w = w_rel
                orig_h = h_rel
                bbox_missing = (orig_x, orig_y, orig_w, orig_h)

                if not (orig_w > min_dim_missing and orig_h > min_dim_missing and
                        orig_w / orig_h < max_aspect_ratio_missing and orig_h / orig_w < max_aspect_ratio_missing):
                    skipped_missing_area_count_filter += 1
                    continue

                orig_x = max(0, orig_x)
                orig_y = max(0, orig_y)
                orig_w = min(orig_w, image.shape[1] - orig_x)
                orig_h = min(orig_h, image.shape[0] - orig_y)
                bbox_missing = (orig_x, orig_y, orig_w, orig_h)

                if orig_w <= 0 or orig_h <= 0:
                    skipped_missing_area_count_filter += 1
                    continue

                total_missing_area = orig_w * orig_h
                if total_missing_area == 0:
                    skipped_missing_area_count_filter += 1
                    continue

                temp_overlap_mask = np.zeros((orig_h, orig_w), dtype=np.uint8)
                for bbox_block in initial_block_bboxes:
                    xA = max(bbox_missing[0], bbox_block[0])
                    yA = max(bbox_missing[1], bbox_block[1])
                    xB = min(bbox_missing[0] + bbox_missing[2], bbox_block[0] + bbox_block[2])
                    yB = min(bbox_missing[1] + bbox_missing[3], bbox_block[1] + bbox_block[3])
                    inter_width = xB - xA
                    inter_height = yB - yA
                    if inter_width > 0 and inter_height > 0:
                        rel_x_start = xA - orig_x
                        rel_y_start = yA - orig_y
                        rel_x_end = rel_x_start + inter_width
                        rel_y_end = rel_y_start + inter_height
                        rel_x_start = max(0, rel_x_start)
                        rel_y_start = max(0, rel_y_start)
                        rel_x_end = min(orig_w, rel_x_end)
                        rel_y_end = min(orig_h, rel_y_end)
                        if rel_x_end > rel_x_start and rel_y_end > rel_y_start:
                            temp_overlap_mask[rel_y_start:rel_y_end, rel_x_start:rel_x_end] = 255

                covered_pixels = cv2.countNonZero(temp_overlap_mask)
                overlap_ratio = covered_pixels / total_missing_area

                if overlap_ratio > overlap_threshold:
                    skipped_missing_area_count_overlap += 1
                    continue

                missing_areas_info.append((bbox_missing, f'missing_{i}_{orig_x}_{orig_y}_{orig_x + orig_w}_{orig_y + orig_h}.jpg'))
                missing_area_found_count += 1

            print(f"過濾後，記錄了 {missing_area_found_count} 個有效的未填充區域。")
            print(f"  因大小/比例跳過：{skipped_missing_area_count_filter}。")
            print(f"  因與初始區塊重疊 > {overlap_threshold*100}% 跳過：{skipped_missing_area_count_overlap}。")
        else:
            print("遮罩尺寸無效，跳過未填充區域檢測。")
    else:
        print("未找到初始區塊，無法執行未填充區域檢測。")

    print("初始分割和未填充區域提取（含重疊檢查）完成！")

    # 最終包含檢查
    print("\n開始最終包含檢查...")
    all_candidate_regions = blocks_info + missing_areas_info
    print(f"合併初始區塊和有效未填充區域，共 {len(all_candidate_regions)} 個候選區域。")

    final_regions_info = []
    if all_candidate_regions:
        indices_to_keep = set(range(len(all_candidate_regions)))
        bboxes_candidate = [r[0] for r in all_candidate_regions]
        for i in range(len(all_candidate_regions)):
            if i not in indices_to_keep:
                continue
            bbox_i = bboxes_candidate[i]
            for j in range(len(all_candidate_regions)):
                if i == j or j not in indices_to_keep:
                    continue
                bbox_j = bboxes_candidate[j]
                if is_contained_bbox(bbox_i, bbox_j):
                    indices_to_keep.discard(i)
                    break
        final_regions_info = [all_candidate_regions[i] for i in sorted(list(indices_to_keep))]
        discarded_count = len(all_candidate_regions) - len(final_regions_info)
        print(f"最終檢查完成，移除了 {discarded_count} 個被包含的區域，剩餘 {len(final_regions_info)} 個最終區域。")
    else:
        print("沒有候選區域可供最終檢查。")

    # 保存最終區塊圖像
    print("\n開始保存最終過濾的區塊圖像...")
    saved_count_final = 0
    for (x, y, w, h), filename in final_regions_info:
        final_block = image[y:y + h, x:x + w]
        output_path = os.path.join(output_folder, filename)
        if final_block.size > 0:
            cv2.imwrite(output_path, final_block)
            saved_count_final += 1
        else:
            print(f"警告：無法保存空的最終區塊，檔名 {filename}，座標 (x={x}, y={y}, w={w}, h={h})")
    print(f"保存了 {saved_count_final} 個最終區塊圖像。")

    # 創建最終組合圖像
    print("\n開始創建 final_combined 圖像...")
    if final_regions_info:
        all_final_bboxes = [b[0] for b in final_regions_info]
        all_final_xs = [b[0] for b in all_final_bboxes]
        all_final_ys = [b[1] for b in all_final_bboxes]
        all_final_xws = [b[0] + b[2] for b in all_final_bboxes]
        all_final_yhs = [b[1] + b[3] for b in all_final_bboxes]

        if not all_final_xs:
            print("沒有最終區塊資訊，無法創建 final_combined 圖像。")
        else:
            min_x_final = min(all_final_xs)
            min_y_final = min(all_final_ys)
            max_x_final = max(all_final_xws)
            max_y_final = max(all_final_yhs)
            final_height = max_y_final - min_y_final
            final_width = max_x_final - min_x_final

            if final_height <= 0 or final_width <= 0:
                print(f"計算的最終組合圖像尺寸無效 (h={final_height}, w={final_width})，無法創建組合圖像。")
            else:
                combined_final = np.zeros((final_height, final_width, 3), dtype=np.uint8)
                print(f"創建最終組合圖像畫布，尺寸：(h={final_height}, w={final_width})")
                placement_errors = 0
                for (x, y, w, h), filename in final_regions_info:
                    x, y, w, h = int(x), int(y), int(w), int(h)
                    if w <= 0 or h <= 0:
                        continue
                    block = image[y:y + h, x:x + w]
                    relative_y = y - min_y_final
                    relative_x = x - min_x_final
                    target_y_start = relative_y
                    target_x_start = relative_x
                    if block.size == 0:
                        print(f"警告：提取的區塊為空，跳過放置。檔名：{filename}")
                        continue
                    slice_h = min(h, final_height - target_y_start)
                    slice_w = min(w, final_width - target_x_start)
                    if slice_h > 0 and slice_w > 0 and target_y_start < final_height and target_x_start < final_width:
                        source_y_offset = 0
                        source_x_offset = 0
                        if target_y_start < 0:
                            source_y_offset = -target_y_start
                            slice_h -= source_y_offset
                            target_y_start = 0
                        if target_x_start < 0:
                            source_x_offset = -target_x_start
                            slice_w -= source_x_offset
                            target_x_start = 0
                        if slice_h > 0 and slice_w > 0:
                            try:
                                target_slice = combined_final[target_y_start:target_y_start + slice_h,
                                                              target_x_start:target_x_start + slice_w]
                                source_slice = block[source_y_offset:source_y_offset + slice_h,
                                                     source_x_offset:source_x_offset + slice_w]
                                if target_slice.shape == source_slice.shape:
                                    combined_final[target_y_start:target_y_start + slice_h,
                                                   target_x_start:target_x_start + slice_w] = source_slice
                                else:
                                    resized_source = cv2.resize(source_slice, (target_slice.shape[1], target_slice.shape[0]))
                                    combined_final[target_y_start:target_y_start + slice_h,
                                                   target_x_start:target_x_start + slice_w] = resized_source
                            except Exception as e:
                                print(f"放置區塊時發生錯誤，檔名：{filename}，錯誤：{e}")
                                placement_errors += 1

                if placement_errors > 0:
                    print(f"組合過程中遇到 {placement_errors} 個放置錯誤。")
                
                # 總是保存最終組合圖像
                final_combined_path = os.path.join(output_folder, f'{image_name}_final_combined.jpg')
                cv2.imwrite(final_combined_path, combined_final)
                print(f"保存最終組合圖像：{final_combined_path}")
    else:
        print("沒有最終過濾的區塊資訊，無法創建 final_combined 圖像。")

    print("\n所有處理步驟完成！")

# 處理 PDF 或圖像輸入的主函數
def main(input_path, output_folder_base, dpi=300):
    if input_path.lower().endswith('.pdf'):
        pdf_document = fitz.open(input_path)
        pdf_base_name = os.path.splitext(os.path.basename(input_path))[0]

        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            # 動態調整 DPI
            page_rect = page.rect
            width_inch = page_rect.width / 72
            height_inch = page_rect.height / 72
            suggested_dpi = max(dpi, int(2000 / max(width_inch, height_inch)))
            pix = page.get_pixmap(dpi=suggested_dpi, alpha=False, annots=True)

            # 直接轉換為 OpenCV 格式
            img_array = np.frombuffer(pix.samples, dtype=np.uint8)
            image = img_array.reshape((pix.height, pix.width, pix.n))
            if pix.n == 3:  # RGB
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            elif pix.n == 4:  # RGBA
                image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)

            if image is None:
                print(f"無法將 PDF 第 {page_num + 1} 頁轉換為圖像，跳過")
                continue

            image_name = f"{pdf_base_name}_page{page_num + 1}"
            page_output_folder = f"{output_folder_base}_page{page_num + 1}"
            print(f"\n處理 PDF 第 {page_num + 1} 頁，尺寸：{image.shape}")
            process_image(image, page_output_folder, image_name)

        pdf_document.close()
    else:
        image = cv2.imread(input_path)
        if image is None:
            print(f"無法讀取圖像，請檢查路徑！路徑：{input_path}")
            return
        image_name = os.path.splitext(os.path.basename(input_path))[0]
        print(f"成功讀取圖像：{input_path}，尺寸：{image.shape}")
        process_image(image, output_folder_base, image_name)

if __name__ == "__main__":
    input_path = 'newspaper/newspaper1.jpg'
    output_folder_base = input_path + '_blocks'
    main(input_path, output_folder_base, dpi=200)