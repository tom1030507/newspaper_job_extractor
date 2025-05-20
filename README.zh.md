# 報紙工作區塊提取工具

## 項目概述

此工具自動從掃描的報紙圖像中提取工作廣告區塊，並將每個區塊保存為單獨的圖像文件，以便進一步處理或數字存檔。它適用於單個圖像和 PDF 文件。

## 功能

- 處理報紙圖像和多頁 PDF 文件
- 使用輪廓檢測算法提取單個工作區塊
- 應用智能過濾以識別相關區塊
- 處理嵌套內容區塊以避免重複
- 檢測未填充區域以捕獲可能被主要檢測遺漏的內容
- 生成具有適當命名約定的乾淨單獨區塊圖像

## 示例結果

### 前後對比

#### 原始報紙圖像
<img src="newspaper/newspaper1.jpg" alt="原始報紙" width="400" /><br>

*帶有多個工作廣告的原始掃描報紙*

#### 提取的工作區塊
<div style="display: flex; gap: 10px;">
  <img src="newspaper/newspaper1.jpg_blocks/239_954_927_1513.jpg" alt="提取的區塊 1" width="200" />
  <img src="newspaper/newspaper1.jpg_blocks/929_971_1615_1527.jpg" alt="提取的區塊 2" width="200" />
  <img src="newspaper/newspaper1.jpg_blocks/1618_2084_2284_2360.jpg" alt="提取的區塊 3" width="200" />
</div>

*從報紙中自動提取的單個工作廣告區塊*

提取過程成功地將單個工作廣告從複雜的報紙佈局中分離出來，使其準備好進行進一步的處理，如 OCR 或存檔。

## 要求

- Python 3.6+
- OpenCV (`cv2`)
- NumPy
- PyMuPDF (`fitz`)

## 安裝

```bash
pip install opencv-python numpy pymupdf
```

## 使用方法

```python
# 處理單個圖像文件
python main.py

# 要調整輸入路徑和輸出目錄，請在腳本中修改以下行：
input_path = 'newspaper/newspaper1.jpg'  # 更改為您的輸入文件路徑
output_folder_base = input_path + '_blocks'  # 輸出目錄
```

## 參數

代碼包含幾個可配置的參數：

- `debug`：設置為 1 以保存額外的調試圖像
- `min_dim`：有效區塊的最小尺寸（默認：120px）
- `max_aspect_ratio`：有效區塊的最大縱橫比（默認：5.0）
- `dpi`：PDF 渲染的分辨率（默認：300，根據頁面大小動態調整）

## 工作原理

1. **預處理**：將圖像轉換為灰度，應用高斯模糊以減少噪聲，使用自適應閾值處理不均勻的光照，並運行 Canny 邊緣檢測以找到清晰的邊緣。

2. **初始輪廓檢測**：使用邊緣圖像上的輪廓檢測識別潛在的內容區塊。

3. **智能過濾**：
   - 刪除過大的區塊（>20% 的圖像面積）
   - 過濾噪聲和微小區塊（小於最小尺寸）
   - 消除縱橫比極端的區塊

4. **包含分析**：檢查區塊是否包含在其他區塊內，以避免重複提取。

5. **缺失區域檢測**：通過以下方式識別可能被主要檢測遺漏的區域：
   - 創建檢測到區塊的掩碼
   - 應用形態學操作以優化掩碼
   - 查找可能包含有效內容的未填充區域
   - 檢查與檢測到區塊的重疊

6. **最終過濾**：對所有候選區域進行最終的包含檢查。

7. **輸出生成**：將每個有效區塊保存為單獨的圖像，並創建調試組合圖像（當 debug=1 時）。

### 處理可視化

| (a) 原始圖像 | (b) Canny 邊緣 | (c) 過濾後的輪廓 | (d) 重建的頁面 |
|---------------------|-----------------|-----------------------|-------------------------|
| ![原始](newspaper/newspaper1.jpg_blocks/newspaper1_original.jpg) | ![Canny 邊緣](newspaper/newspaper1.jpg_blocks/newspaper1_mask_unprocessed.jpg) | ![過濾後的輪廓](newspaper/newspaper1.jpg_blocks/newspaper1_mask_processed.jpg) | ![重建的頁面](newspaper/newspaper1.jpg_blocks/newspaper1_final_combined.jpg) |

## 限制

- 可能難以處理非常緊密放置的工作廣告，這些廣告可能被視為單個區塊
- 參數敏感性：不同的報紙佈局可能需要調整參數
- 對旋轉文本區塊的處理有限
- 偶爾可能遺漏對比度差或邊界不清晰的區塊

## 潛在應用

- 報紙/文件數字化預處理
- 內容提取輔助 OCR 系統
- 創建機器學習模型的數據集
- 出版研究的佈局分析

## Web 界面

本工具現在提供了 Flask Web 界面，您可以通過瀏覽器上傳和處理文件。

### 安裝 Web 界面所需的依賴

```bash
pip install -r requirements.txt
```

### 運行 Web 服務器

```bash
python app.py
```

啟動後，打開瀏覽器訪問 http://127.0.0.1:5000 使用 Web 界面。

### Web 界面功能

1. **上傳檔案** - 支持 JPG、PNG 和 PDF 檔案
2. **偵錯模式** - 可選擇保存處理過程中的中間圖像，幫助理解分割過程
3. **查看結果** - 以網格形式顯示提取的區塊
4. **下載結果** - 將提取的所有區塊打包下載為 ZIP 檔案

### 注意事項

- 上傳檔案大小限制為 16MB
- 處理大型檔案可能需要較長時間，請耐心等待
- 為避免佔用過多磁碟空間，系統會自動清理 24 小時前的處理結果

## 詳細報告
[HackMD 連結](https://hackmd.io/@OcvSVmsIRyeNNdWk7tMv2w/H1Zw-65Ckl)

---