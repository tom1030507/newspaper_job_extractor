import cv2
import numpy as np
import os

# 檢查一個 Bounding Box 是否被另一個包含
def is_contained_bbox(bbox1, bbox2, tolerance=10):
    """檢查 bbox1 是否完全被 bbox2 包含 (使用 Bounding Box 坐標)"""
    x1, y1, w1, h1 = bbox1
    x2, y2, w2, h2 = bbox2
    return (x1 >= (x2 - tolerance) and y1 >= (y2 - tolerance) and
            (x1 + w1) <= (x2 + w2 + tolerance) and (y1 + h1) <= (y2 + h2 + tolerance))

# --- Function to calculate intersection of two rectangles ---
def intersection_area(boxA, boxB):
    # determine the (x, y)-coordinates of the intersection rectangle
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
    yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])

    # compute the width and height of the intersection rectangle
    inter_width = xB - xA
    inter_height = yB - yA

    # compute the area of intersection rectangle
    if inter_width > 0 and inter_height > 0:
        return inter_width * inter_height
    else:
        return 0

# --- Initial Setup ---
image_name = 'newspaper1'
output_folder = image_name + '_blocks_overlap_checked' # New folder name
if not os.path.exists(output_folder):
    os.makedirs(output_folder)
    print(f"已創建資料夾：{output_folder}")

# --- Load Image, Preprocessing, Contour Detection (Steps 2-6 are the same) ---
# ... (Assume steps 2-6 code is here as in the previous version) ...
# --- Start Relevant Code ---
# 2. 讀取圖片
image_path = image_name + '.jpg'
image = cv2.imread(image_path)
if image is None:
    print(f"無法讀取圖片，請檢查路徑！ Path: {image_path}")
    exit()
print(f"成功讀取圖片：{image_path}, 尺寸：{image.shape}")

# 3. 預處理圖片
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
blurred = cv2.GaussianBlur(gray, (5, 5), 0)
thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY_INV, 11, 2)
edges = cv2.Canny(thresh, 100, 200)
print("圖片預處理完成")

# 4. 檢測輪廓
contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print(f"檢測到初始輪廓數量：{len(contours)}")

# 5. 過濾過大的輪廓
max_area_threshold = 0.3 * image.shape[0] * image.shape[1]
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

# 6. 過濾掉太小的噪點和不合適長寬比的輪廓
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
print(f"過濾掉 {small_noise_count} 個過小輪廓，{aspect_ratio_fail_count} 個長寬比不符輪廓，剩餘有效輪廓：{len(valid_contours_initial)}")

# 7. 第一次過濾包含關係 (僅在初始輪廓之間) 並記錄信息
blocks_info = []
contained_count_initial = 0
initial_blocks_found = 0
temp_initial_bboxes = [cv2.boundingRect(c) for c in valid_contours_initial]

for i, contour in enumerate(valid_contours_initial):
    bbox_i = temp_initial_bboxes[i]
    is_contained_by_others = False
    for j, other_bbox in enumerate(temp_initial_bboxes):
        if i != j:
            if is_contained_bbox(bbox_i, other_bbox):
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
        blocks_info.append(((x, y, w, h), f'{x}_{y}_{x + w}_{y + h}.png')) # Store bbox directly
        initial_blocks_found += 1
print(f"第一次過濾：過濾掉 {contained_count_initial} 個被包含輪廓，記錄 {initial_blocks_found} 個初始區塊信息。")

# Get just the bounding boxes of the confirmed initial blocks
initial_block_bboxes = [info[0] for info in blocks_info]

# 8. 合併所有 *初始* 區塊並處理未填充區域
missing_areas_info = []
if blocks_info:
    # --- Create mask and apply morphology (same as before) ---
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
        for (x, y, w, h) in initial_block_bboxes: # Use the list of bboxes
            relative_y = y - min_y_overall
            relative_x = x - min_x_overall
            end_y = min(relative_y + h, mask_height)
            end_x = min(relative_x + w, mask_width)
            relative_y = max(0, relative_y)
            relative_x = max(0, relative_x)
            if end_y > relative_y and end_x > relative_x:
                 mask[relative_y:end_y, relative_x:end_x] = 255

        mask_unprocessed_path = os.path.join(output_folder, image_name + '_mask_unprocessed.png')
        cv2.imwrite(mask_unprocessed_path, mask)
        print(f"已保存未處理的遮罩圖片：{mask_unprocessed_path}")

        kernel_size = 15
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)
        mask = cv2.erode(mask, kernel, iterations=1)
        print(f"對遮罩進行形態學操作 (膨脹後腐蝕，核心大小 {kernel_size})")
        mask_processed_path = os.path.join(output_folder, image_name + '_mask_processed.png')
        cv2.imwrite(mask_processed_path, mask)
        print(f"已保存形態學處理後的遮罩圖片：{mask_processed_path}")

        # 9. 找出未填充區域並進行重疊檢查
        inv_mask = cv2.bitwise_not(mask)
        missing_contours, _ = cv2.findContours(inv_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        print(f"在處理後的遮罩中檢測到 {len(missing_contours)} 個潛在的未填充區域輪廓。")

        min_area_threshold_missing = 5000
        min_dim_missing = 120
        max_aspect_ratio_missing = 5.0
        overlap_threshold = 0.50 # 50% overlap threshold

        missing_area_found_count = 0
        skipped_missing_area_count_filter = 0 # Skipped by size/aspect ratio
        skipped_missing_area_count_overlap = 0 # Skipped by overlap check

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
            bbox_missing = (orig_x, orig_y, orig_w, orig_h) # Store as tuple

            # --- Basic Size/Aspect Ratio Check ---
            if not (orig_w > min_dim_missing and orig_h > min_dim_missing and \
                    orig_w / orig_h < max_aspect_ratio_missing and orig_h / orig_w < max_aspect_ratio_missing):
                skipped_missing_area_count_filter += 1
                continue

            orig_x = max(0, orig_x)
            orig_y = max(0, orig_y)
            orig_w = min(orig_w, image.shape[1] - orig_x)
            orig_h = min(orig_h, image.shape[0] - orig_y)
            bbox_missing = (orig_x, orig_y, orig_w, orig_h) # Update after clipping

            if orig_w <= 0 or orig_h <= 0:
                 skipped_missing_area_count_filter += 1
                 continue

            # --- START: Overlap Check ---
            total_missing_area = orig_w * orig_h
            if total_missing_area == 0:
                 skipped_missing_area_count_filter +=1 # Treat zero area as filtered out
                 continue

            # Create a temporary mask for the missing area candidate
            temp_overlap_mask = np.zeros((orig_h, orig_w), dtype=np.uint8)

            # Iterate through initial blocks to mark overlaps on the temp mask
            for bbox_block in initial_block_bboxes:
                # Find intersection between missing candidate and the initial block
                xA = max(bbox_missing[0], bbox_block[0])
                yA = max(bbox_missing[1], bbox_block[1])
                xB = min(bbox_missing[0] + bbox_missing[2], bbox_block[0] + bbox_block[2])
                yB = min(bbox_missing[1] + bbox_missing[3], bbox_block[1] + bbox_block[3])

                inter_width = xB - xA
                inter_height = yB - yA

                # If there is an intersection
                if inter_width > 0 and inter_height > 0:
                    # Calculate the intersection's coordinates relative to temp_overlap_mask
                    rel_x_start = xA - orig_x
                    rel_y_start = yA - orig_y
                    rel_x_end = rel_x_start + inter_width
                    rel_y_end = rel_y_start + inter_height

                    # Clip coordinates to be within temp_overlap_mask bounds
                    rel_x_start = max(0, rel_x_start)
                    rel_y_start = max(0, rel_y_start)
                    rel_x_end = min(orig_w, rel_x_end)
                    rel_y_end = min(orig_h, rel_y_end)

                    # Draw the intersection rectangle onto the temp mask
                    if rel_x_end > rel_x_start and rel_y_end > rel_y_start: # Check if valid slice
                         temp_overlap_mask[rel_y_start:rel_y_end, rel_x_start:rel_x_end] = 255

            # Calculate the area covered by initial blocks within the missing area's bounds
            covered_pixels = cv2.countNonZero(temp_overlap_mask)
            overlap_ratio = covered_pixels / total_missing_area

            # Check against the threshold
            if overlap_ratio > overlap_threshold:
                # print(f"未填充區域 {i} (bbox:{bbox_missing}) 與初始區塊重疊率 {overlap_ratio:.2f} > {overlap_threshold}, 跳過...")
                skipped_missing_area_count_overlap += 1
                continue
            # --- END: Overlap Check ---

            # If passes all checks, add to list
            missing_areas_info.append((bbox_missing, f'missing_{i}_{orig_x}_{orig_y}_{orig_x + orig_w}_{orig_y + orig_h}.png'))
            missing_area_found_count += 1

        print(f"過濾後，記錄 {missing_area_found_count} 個有效未填充區域。")
        print(f"  因尺寸/比例跳過: {skipped_missing_area_count_filter} 個。")
        print(f"  因與初始區塊重疊 > {overlap_threshold*100}% 跳過: {skipped_missing_area_count_overlap} 個。")

    else:
        print("遮罩尺寸無效，跳過未填充區域檢測。")
else:
    print("沒有找到任何初始區塊，無法進行未填充區域檢測。")

print("初始分割與未填充區域提取（含重疊檢查）完成！")


# --- Final Containment Check (among remaining initial blocks and valid missing areas) ---
print("\n開始最終包含關係檢查...")
# Combine remaining initial blocks and the VALIDATED missing areas
all_candidate_regions = blocks_info + missing_areas_info # blocks_info already filtered, missing_areas_info is overlap-checked
print(f"合併初始區塊和有效未填充區域，總計 {len(all_candidate_regions)} 個候選區域。")

final_regions_info = []
if all_candidate_regions:
    indices_to_keep = set(range(len(all_candidate_regions)))
    bboxes_candidate = [r[0] for r in all_candidate_regions] # Get all candidate bboxes

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
                # print(f"最終檢查：區域 {i} 被區域 {j} 包含，移除。")
                break # Found container for i

    final_regions_info = [all_candidate_regions[i] for i in sorted(list(indices_to_keep))]
    discarded_count = len(all_candidate_regions) - len(final_regions_info)
    print(f"最終檢查完成，移除了 {discarded_count} 個被包含的區域，剩餘 {len(final_regions_info)} 個最終區域。")
else:
    print("沒有候選區域可供最終檢查。")


# --- Save Final Blocks and Recombine (Steps after final check are the same) ---
# ... (Assume code for saving final blocks and recombining is here as in the previous version) ...
# --- Start Relevant Code ---
# --- 保存最終區塊圖片 ---
print("\n開始保存最終篩選後的區塊圖片...")
saved_count_final = 0
for (x, y, w, h), filename in final_regions_info:
    final_block = image[y:y + h, x:x + w]
    output_path = os.path.join(output_folder, filename)
    if final_block.size > 0:
        cv2.imwrite(output_path, final_block)
        saved_count_final += 1
    else:
        print(f"警告：無法保存空的最終區塊，文件名 {filename}，坐標 (x={x}, y={y}, w={w}, h={h})")
print(f"保存了 {saved_count_final} 個最終區塊圖片。")


# --- 重新合成 final_combined 圖片 (使用最終篩選的區塊) ---
print("\n開始合成 final_combined 圖片 (使用最終篩選的區塊)...")

if final_regions_info:
    all_final_bboxes = [b[0] for b in final_regions_info] # Get final bboxes
    all_final_xs = [b[0] for b in all_final_bboxes]
    all_final_ys = [b[1] for b in all_final_bboxes]
    all_final_xws = [b[0] + b[2] for b in all_final_bboxes]
    all_final_yhs = [b[1] + b[3] for b in all_final_bboxes]


    if not all_final_xs:
         print("沒有最終區塊信息，無法合成 final_combined 圖片。")
    else:
        min_x_final = min(all_final_xs)
        min_y_final = min(all_final_ys)
        max_x_final = max(all_final_xws)
        max_y_final = max(all_final_yhs)

        final_height = max_y_final - min_y_final
        final_width = max_x_final - min_x_final

        if final_height <= 0 or final_width <= 0:
            print(f"計算出的最終合併圖片尺寸無效 (h={final_height}, w={final_width})，無法合成。")
        else:
            combined_final = np.zeros((final_height, final_width, 3), dtype=np.uint8)
            print(f"創建最終合併圖片畫布，尺寸：(h={final_height}, w={final_width})")

            placement_errors = 0
            for (x, y, w, h), filename in final_regions_info: # Iterate through final list
                # Ensure w, h are integers for slicing
                x, y, w, h = int(x), int(y), int(w), int(h)
                if w <= 0 or h <= 0: continue # Skip zero-size blocks

                block = image[y:y + h, x:x + w]
                relative_y = y - min_y_final
                relative_x = x - min_x_final

                target_y_start = relative_y
                target_x_start = relative_x

                if block.size == 0:
                    print(f"警告：提取的區塊為空，跳過放置。文件名: {filename}")
                    continue

                # Determine the slice dimensions, respecting boundaries of both source and target
                slice_h = min(h, final_height - target_y_start)
                slice_w = min(w, final_width - target_x_start)

                # Ensure slice dimensions and target start positions are valid
                if slice_h > 0 and slice_w > 0 and target_y_start < final_height and target_x_start < final_width:
                    # Adjust target start if it's negative (shouldn't happen with min_x/y logic, but safe)
                    source_y_offset = 0
                    source_x_offset = 0
                    if target_y_start < 0:
                        source_y_offset = -target_y_start
                        slice_h = slice_h - source_y_offset # Adjust slice height
                        target_y_start = 0
                    if target_x_start < 0:
                        source_x_offset = -target_x_start
                        slice_w = slice_w - source_x_offset # Adjust slice width
                        target_x_start = 0

                    # Final check on adjusted slice dimensions
                    if slice_h > 0 and slice_w > 0:
                        try:
                            target_slice = combined_final[target_y_start : target_y_start + slice_h,
                                                          target_x_start : target_x_start + slice_w]
                            source_slice = block[source_y_offset : source_y_offset + slice_h,
                                                 source_x_offset : source_x_offset + slice_w]

                            # Ensure shapes match before assignment (can happen with rounding errors)
                            if target_slice.shape == source_slice.shape:
                                combined_final[target_y_start : target_y_start + slice_h,
                                            target_x_start : target_x_start + slice_w] = source_slice
                            else:
                                # If shapes don't match, resize source to fit target (or skip/warn)
                                print(f"警告: 放置區塊時形狀不匹配。文件名: {filename}")
                                print(f"  目標形狀: {target_slice.shape}, 源形狀: {source_slice.shape}")
                                print(f"  嘗試調整大小...")
                                try:
                                    resized_source = cv2.resize(source_slice, (target_slice.shape[1], target_slice.shape[0]))
                                    combined_final[target_y_start : target_y_start + slice_h,
                                                target_x_start : target_x_start + slice_w] = resized_source
                                except Exception as resize_e:
                                     print(f"  調整大小失敗: {resize_e}")
                                     placement_errors += 1

                        except Exception as e: # Catch potential slicing or assignment errors
                            print(f"放置區塊時發生未預期錯誤")
                            print(f"  文件名: {filename}, 原始坐標: (x={x}, y={y}, w={w}, h={h})")
                            print(f"  計算出的切片: h={slice_h}, w={slice_w}, target_y={target_y_start}, target_x={target_x_start}")
                            print(f"  錯誤: {e}")
                            placement_errors += 1
                    else:
                         print(f"警告: 調整後切片尺寸無效，跳過放置。文件名: {filename}")
                else:
                     print(f"警告: 無效的切片尺寸或目標位置，跳過放置。文件名: {filename}")


            if placement_errors > 0:
                 print(f"合成過程中出現 {placement_errors} 次放置錯誤。")

            final_combined_path = os.path.join(output_folder, image_name + '_final_combined.png')
            cv2.imwrite(final_combined_path, combined_final)
            print(f"已保存最終合併圖片：{final_combined_path}")
else:
    print("沒有最終篩選後的區塊信息，無法合成 final_combined 圖片。")

print("\n所有處理步驟完成！")
# --- END Relevant Code ---