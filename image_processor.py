import cv2
import numpy as np
import os
import fitz  # PyMuPDF

# Check if one bounding box is contained within another
def is_contained_bbox(bbox1, bbox2, tolerance=10):
    """Check if bbox1 is completely contained within bbox2 (using bounding box coordinates)"""
    x1, y1, w1, h1 = bbox1
    x2, y2, w2, h2 = bbox2
    return (x1 >= (x2 - tolerance) and y1 >= (y2 - tolerance) and
            (x1 + w1) <= (x2 + w2 + tolerance) and (y1 + h1) <= (y2 + h2 + tolerance))

# Calculate intersection area between two rectangles
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

# Function to process a single image (directly receives image data)
def process_image(image, output_folder, image_name):
    """Process image data, extract blocks and save results - always save processing images"""
    if image is None:
        print(f"Image data is empty, cannot process: {image_name}")
        return
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created folder: {output_folder}")

    # 總是保存原始圖像
    original_image_path = os.path.join(output_folder, f"{image_name}_original.jpg")
    cv2.imwrite(original_image_path, image)
    print(f"Saved original image: {original_image_path}")

    print(f"Started processing image: {image_name}, dimensions: {image.shape}")

    # Preprocess image
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 11, 2)
    edges = cv2.Canny(thresh, 100, 200)
    print("Image preprocessing completed")

    # Detect contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"Detected initial contours: {len(contours)}")

    # Filter out oversized contours
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
    print(f"Filtered out {large_contours_count} oversized contours, remaining: {len(filtered_contours_size)}")

    # Filter out small noise and contours with inappropriate aspect ratios
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
    print(f"Filtered out {small_noise_count} undersized contours, {aspect_ratio_fail_count} contours with inappropriate aspect ratios, remaining valid contours: {len(valid_contours_initial)}")

    # First pass to filter containment relationships (only between initial contours)
    blocks_info = []
    contained_count_initial = 0
    initial_blocks_found = 0
    temp_initial_bboxes = [cv2.boundingRect(c) for c in valid_contours_initial]

    for i, contour in enumerate(valid_contours_initial):
        bbox_i = temp_initial_bboxes[i]
        if bbox_i is None:  # Skip already removed bounding boxes
            continue
        is_contained_by_others = False
        for j, other_bbox in enumerate(temp_initial_bboxes):
            if i != j and other_bbox is not None and is_contained_bbox(bbox_i, other_bbox):  # Ensure other_bbox is not None
                # Compare areas of the two bounding boxes, keep the larger one
                area_i = bbox_i[2] * bbox_i[3]
                area_j = other_bbox[2] * other_bbox[3]
                if area_i >= area_j:
                    # Keep bbox_i, remove other_bbox
                    temp_initial_bboxes[j] = None  # Mark as removed
                else:
                    # Keep other_bbox, remove bbox_i
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

    # Remove bounding boxes marked as None
    temp_initial_bboxes = [bbox for bbox in temp_initial_bboxes if bbox is not None]

    print(f"First filtering pass: Filtered out {contained_count_initial} contained contours, recorded {initial_blocks_found} initial block information.")

    initial_block_bboxes = [info[0] for info in blocks_info]

    # Process unfilled areas
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
            print(f"Saved unprocessed mask image: {mask_unprocessed_path}")

            kernel_size = 30
            kernel = np.ones((kernel_size, kernel_size), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=3)
            mask = cv2.erode(mask, kernel, iterations=3)
            
            # 總是保存處理後的遮罩圖像
            mask_processed_path = os.path.join(output_folder, f'{image_name}_mask_processed.jpg')
            cv2.imwrite(mask_processed_path, mask)
            print(f"Saved processed mask image: {mask_processed_path}")

            # Find unfilled areas and check for overlaps
            inv_mask = cv2.bitwise_not(mask)
            missing_contours, _ = cv2.findContours(inv_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            print(f"Detected {len(missing_contours)} potential unfilled area contours in the processed mask.")

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

            print(f"After filtering, recorded {missing_area_found_count} valid unfilled areas.")
            print(f"  Skipped due to size/ratio: {skipped_missing_area_count_filter}.")
            print(f"  Skipped due to overlap > {overlap_threshold*100}% with initial blocks: {skipped_missing_area_count_overlap}.")
        else:
            print("Invalid mask dimensions, skipping unfilled area detection.")
    else:
        print("No initial blocks found, cannot perform unfilled area detection.")

    print("Initial segmentation and unfilled area extraction (with overlap checking) completed!")

    # Final containment check
    print("\nStarting final containment check...")
    all_candidate_regions = blocks_info + missing_areas_info
    print(f"Combined initial blocks and valid unfilled areas, total of {len(all_candidate_regions)} candidate regions.")

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
        print(f"Final check completed, removed {discarded_count} contained regions, remaining {len(final_regions_info)} final regions.")
    else:
        print("No candidate regions available for final check.")

    # Save final block images
    print("\nStarting to save final filtered block images...")
    saved_count_final = 0
    for (x, y, w, h), filename in final_regions_info:
        final_block = image[y:y + h, x:x + w]
        output_path = os.path.join(output_folder, filename)
        if final_block.size > 0:
            cv2.imwrite(output_path, final_block)
            saved_count_final += 1
        else:
            print(f"Warning: Cannot save empty final block, filename {filename}, coordinates (x={x}, y={y}, w={w}, h={h})")
    print(f"Saved {saved_count_final} final block images.")

    # Create final combined image
    print("\nStarting to create final_combined image...")
    if final_regions_info:
        all_final_bboxes = [b[0] for b in final_regions_info]
        all_final_xs = [b[0] for b in all_final_bboxes]
        all_final_ys = [b[1] for b in all_final_bboxes]
        all_final_xws = [b[0] + b[2] for b in all_final_bboxes]
        all_final_yhs = [b[1] + b[3] for b in all_final_bboxes]

        if not all_final_xs:
            print("No final block information, cannot create final_combined image.")
        else:
            min_x_final = min(all_final_xs)
            min_y_final = min(all_final_ys)
            max_x_final = max(all_final_xws)
            max_y_final = max(all_final_yhs)
            final_height = max_y_final - min_y_final
            final_width = max_x_final - min_x_final

            if final_height <= 0 or final_width <= 0:
                print(f"Calculated final combined image dimensions are invalid (h={final_height}, w={final_width}), cannot create combined image.")
            else:
                combined_final = np.zeros((final_height, final_width, 3), dtype=np.uint8)
                print(f"Created final combined image canvas, dimensions: (h={final_height}, w={final_width})")
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
                        print(f"Warning: Extracted block is empty, skipping placement. Filename: {filename}")
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
                                print(f"Error occurred when placing block, filename: {filename}, error: {e}")
                                placement_errors += 1

                if placement_errors > 0:
                    print(f"Encountered {placement_errors} placement errors during composition.")
                
                # 總是保存最終組合圖像
                final_combined_path = os.path.join(output_folder, f'{image_name}_final_combined.jpg')
                cv2.imwrite(final_combined_path, combined_final)
                print(f"Saved final combined image: {final_combined_path}")
    else:
        print("No final filtered block information, cannot create final_combined image.")

    print("\nAll processing steps completed!")

# Main function to process PDF or image input
def main(input_path, output_folder_base, dpi=300):
    if input_path.lower().endswith('.pdf'):
        pdf_document = fitz.open(input_path)
        pdf_base_name = os.path.splitext(os.path.basename(input_path))[0]

        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            # Dynamically adjust DPI
            page_rect = page.rect
            width_inch = page_rect.width / 72
            height_inch = page_rect.height / 72
            suggested_dpi = max(dpi, int(2000 / max(width_inch, height_inch)))
            pix = page.get_pixmap(dpi=suggested_dpi, alpha=False, annots=True)

            # Direct conversion to OpenCV format
            img_array = np.frombuffer(pix.samples, dtype=np.uint8)
            image = img_array.reshape((pix.height, pix.width, pix.n))
            if pix.n == 3:  # RGB
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            elif pix.n == 4:  # RGBA
                image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)

            if image is None:
                print(f"Unable to convert page {page_num + 1} of PDF to image, skipping")
                continue

            image_name = f"{pdf_base_name}_page{page_num + 1}"
            page_output_folder = f"{output_folder_base}_page{page_num + 1}"
            print(f"\nProcessing PDF page {page_num + 1}, dimensions: {image.shape}")
            process_image(image, page_output_folder, image_name)

        pdf_document.close()
    else:
        image = cv2.imread(input_path)
        if image is None:
            print(f"Cannot read image, please check the path! Path: {input_path}")
            return
        image_name = os.path.splitext(os.path.basename(input_path))[0]
        print(f"Successfully read image: {input_path}, dimensions: {image.shape}")
        process_image(image, output_folder_base, image_name)

if __name__ == "__main__":
    input_path = 'newspaper/newspaper1.jpg'
    output_folder_base = input_path + '_blocks'
    main(input_path, output_folder_base, dpi=200)