# Google Apps Script 設置說明

本系統使用 Google Apps Script 來自動創建 Google Sheets 並接收職缺資料。

## 快速設置

### 1. 創建 Google Apps Script 專案

1. 開啟 [Google Apps Script](https://script.google.com/)
2. 點擊「新專案」
3. 將 `google_apps_script.js` 中的所有代碼複製到 `Code.gs` 檔案中
4. 將專案命名為「報紙職缺提取器」

### 2. 部署為網路應用程式

1. 點擊右上角的「部署」按鈕
2. 選擇「新增部署」
3. 在「類型」中選擇「網路應用程式」
4. 設定以下參數：
   - **描述**：報紙職缺提取器 API
   - **執行身分**：我（您的 Google 帳號）
   - **有權存取的使用者**：任何人
5. 點擊「部署」
6. 複製「網路應用程式 URL」

### 3. 更新系統設定

將複製的網路應用程式 URL 更新到 `app.py` 中：

```python
# 在 app.py 的 send_to_spreadsheet 函數中找到以下行：
apps_script_url = 'https://script.google.com/macros/s/AKfycbxExample/exec'

# 替換為您的實際 URL：
apps_script_url = 'https://script.google.com/macros/s/YOUR_ACTUAL_SCRIPT_ID/exec'
```

### 4. 測試部署

1. 在 Google Apps Script 編輯器中，選擇 `testCreateSheet` 函數
2. 點擊「執行」按鈕進行測試
3. 第一次執行時需要授權：
   - 點擊「檢閱權限」
   - 選擇您的 Google 帳號
   - 點擊「進階」
   - 點擊「前往 報紙職缺提取器（不安全）」
   - 點擊「允許」

## 詳細說明

### 功能特點

- **自動創建 Google Sheet**：每次請求都會創建新的試算表
- **格式化資料**：自動設定標題行格式和邊框
- **摘要統計**：包含行業分布和處理摘要
- **資料保護**：標題行設定為唯讀保護
- **自動分享**：設定為任何有連結的人都可檢視

### 創建的工作表結構

#### 主要工作表「職缺資料」
| 欄位 | 說明 |
|------|------|
| 編號 | 自動遞增編號 |
| 工作 | 工作職位名稱 |
| 行業 | 行業分類 |
| 時間 | 工作時間 |
| 薪資 | 薪資待遇 |
| 地點 | 工作地點 |
| 聯絡方式 | 聯絡電話或方式 |
| 其他 | 其他備註資訊 |
| 來源圖片 | 原始圖片檔名 |
| 頁碼 | PDF 頁碼（如適用） |
| 工作編號 | 同一圖片中的工作序號 |
| 提取時間 | 資料提取時間戳記 |

#### 摘要工作表「處理摘要」
- 處理 ID
- 總職缺數
- 處理時間
- 資料來源
- 各行業職缺分布統計

### 權限設定

此 Google Apps Script 需要以下權限：
- **Google Sheets API**：創建和編輯試算表
- **Google Drive API**：管理檔案分享權限

### 安全性考量

1. **資料隱私**：每次創建的試算表都是獨立的，不會與其他使用者共享
2. **存取控制**：試算表預設為創建者擁有，可選擇性分享
3. **資料驗證**：系統會驗證傳入的資料格式

### 故障排除

#### 常見問題

1. **404 錯誤**
   - 檢查網路應用程式 URL 是否正確
   - 確認部署狀態為「啟用」

2. **403 權限錯誤**
   - 重新檢閱並授權必要權限
   - 確認執行身分設定為「我」

3. **500 內部錯誤**
   - 檢查 Google Apps Script 代碼是否正確複製
   - 查看 Google Apps Script 執行記錄

#### 除錯方法

1. 在 Google Apps Script 編輯器中查看執行記錄
2. 使用 `testCreateSheet()` 函數進行本地測試
3. 檢查瀏覽器開發者工具的網路請求

### 版本更新

當需要更新 Google Apps Script 代碼時：

1. 修改 `Code.gs` 中的代碼
2. 點擊「部署」→「管理部署」
3. 點擊編輯圖示
4. 選擇「新版本」
5. 點擊「部署」

## 範例回應格式

成功創建時的回應：
```json
{
  "success": true,
  "message": "成功創建 Google Sheet 並添加 5 筆職缺資料",
  "spreadsheet_url": "https://docs.google.com/spreadsheets/d/1ABC...XYZ/edit",
  "spreadsheet_id": "1ABC...XYZ",
  "sheet_name": "報紙職缺提取_2024-01-15T10-30-00",
  "jobs_added": 5,
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

## 聯絡支援

如果遇到設置問題，請：
1. 檢查本說明文件的故障排除章節
2. 查看 Google Apps Script 的執行記錄
3. 確認網路連線和 Google 服務狀態 