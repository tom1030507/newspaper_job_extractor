/**
 * 報紙職缺提取器 - Google Apps Script 接收端
 * 
 * 部署說明：
 * 1. 在 Google Apps Script (script.google.com) 中創建新專案
 * 2. 將此程式碼貼入 Code.gs 檔案
 * 3. 點擊「部署」-> 「新增部署」
 * 4. 類型選擇「網路應用程式」
 * 5. 執行身分選擇「我」
 * 6. 存取權限選擇「任何人」
 * 7. 點擊「部署」並複製網路應用程式 URL
 * 8. 將此 URL 用於 Flask 應用程式的發送功能
 */

// 設定 Google Spreadsheet ID（請替換為您的試算表 ID）
const SPREADSHEET_ID = 'YOUR_SPREADSHEET_ID_HERE';

// 工作表名稱
const SHEET_NAME = '職缺資料';

/**
 * 處理 POST 請求的主函數
 */
function doPost(e) {
  try {
    // 解析請求資料
    const requestData = JSON.parse(e.postData.contents);
    
    // 記錄請求資訊
    console.log('收到請求:', requestData);
    
    // 根據 action 執行不同操作
    switch (requestData.action) {
      case 'addJobs':
        return addJobsToSpreadsheet(requestData);
      case 'test':
        return testConnection();
      default:
        return createResponse(false, '未知的操作類型');
    }
    
  } catch (error) {
    console.error('處理請求時發生錯誤:', error);
    return createResponse(false, '處理請求時發生錯誤: ' + error.toString());
  }
}

/**
 * 將職缺資料添加到 Google Spreadsheet
 */
function addJobsToSpreadsheet(requestData) {
  try {
    const jobs = requestData.jobs;
    const metadata = requestData.metadata;
    
    if (!jobs || !Array.isArray(jobs) || jobs.length === 0) {
      return createResponse(false, '沒有提供有效的職缺資料');
    }
    
    // 開啟試算表
    const spreadsheet = SpreadsheetApp.openById(SPREADSHEET_ID);
    let sheet = spreadsheet.getSheetByName(SHEET_NAME);
    
    // 如果工作表不存在，創建新的工作表
    if (!sheet) {
      sheet = spreadsheet.insertSheet(SHEET_NAME);
      setupSheetHeaders(sheet);
    }
    
    // 檢查是否需要添加標題行
    if (sheet.getLastRow() === 0) {
      setupSheetHeaders(sheet);
    }
    
    // 準備要插入的資料
    const dataToInsert = [];
    
    jobs.forEach(job => {
      const row = [
        new Date(), // 添加時間
        job['工作'] || '',
        job['行業'] || '',
        job['時間'] || '',
        job['薪資'] || '',
        job['地點'] || '',
        job['聯絡方式'] || '',
        job['其他'] || '',
        job['來源圖片'] || '',
        job['頁碼'] || '',
        job['工作編號'] || '',
        job['圖片編號'] || '',
        metadata.process_id || '',
        metadata.source || 'newspaper_job_extractor'
      ];
      dataToInsert.push(row);
    });
    
    // 插入資料到工作表
    if (dataToInsert.length > 0) {
      const startRow = sheet.getLastRow() + 1;
      const range = sheet.getRange(startRow, 1, dataToInsert.length, dataToInsert[0].length);
      range.setValues(dataToInsert);
      
      // 自動調整欄寬
      sheet.autoResizeColumns(1, dataToInsert[0].length);
    }
    
    return createResponse(true, `成功添加 ${jobs.length} 筆職缺資料`, {
      jobsAdded: jobs.length,
      sheetName: SHEET_NAME,
      spreadsheetId: SPREADSHEET_ID,
      processId: metadata.process_id
    });
    
  } catch (error) {
    console.error('添加職缺資料時發生錯誤:', error);
    return createResponse(false, '添加職缺資料時發生錯誤: ' + error.toString());
  }
}

/**
 * 設定工作表標題行
 */
function setupSheetHeaders(sheet) {
  const headers = [
    '添加時間',
    '工作',
    '行業', 
    '時間',
    '薪資',
    '地點',
    '聯絡方式',
    '其他',
    '來源圖片',
    '頁碼',
    '工作編號',
    '圖片編號',
    '處理ID',
    '來源系統'
  ];
  
  // 設定標題行
  const headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setValues([headers]);
  
  // 設定標題行格式
  headerRange.setFontWeight('bold');
  headerRange.setBackground('#4285f4');
  headerRange.setFontColor('white');
  
  // 凍結標題行
  sheet.setFrozenRows(1);
}

/**
 * 測試連接功能
 */
function testConnection() {
  try {
    // 嘗試開啟試算表
    const spreadsheet = SpreadsheetApp.openById(SPREADSHEET_ID);
    const sheetCount = spreadsheet.getSheets().length;
    
    return createResponse(true, '連接測試成功', {
      spreadsheetName: spreadsheet.getName(),
      sheetCount: sheetCount,
      timestamp: new Date().toISOString()
    });
    
  } catch (error) {
    return createResponse(false, '連接測試失敗: ' + error.toString());
  }
}

/**
 * 創建統一的回應格式
 */
function createResponse(success, message, data = null) {
  const response = {
    success: success,
    message: message,
    timestamp: new Date().toISOString()
  };
  
  if (data) {
    response.data = data;
  }
  
  return ContentService
    .createTextOutput(JSON.stringify(response))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * 處理 GET 請求（用於測試）
 */
function doGet(e) {
  return createResponse(true, 'Google Apps Script 運行正常', {
    method: 'GET',
    timestamp: new Date().toISOString()
  });
}

/**
 * 獲取試算表資訊（管理功能）
 */
function getSpreadsheetInfo() {
  try {
    const spreadsheet = SpreadsheetApp.openById(SPREADSHEET_ID);
    const sheet = spreadsheet.getSheetByName(SHEET_NAME);
    
    if (!sheet) {
      return createResponse(false, '找不到指定的工作表');
    }
    
    const lastRow = sheet.getLastRow();
    const lastColumn = sheet.getLastColumn();
    
    return createResponse(true, '成功獲取試算表資訊', {
      spreadsheetName: spreadsheet.getName(),
      sheetName: SHEET_NAME,
      totalRows: lastRow,
      totalColumns: lastColumn,
      dataRows: lastRow > 0 ? lastRow - 1 : 0 // 扣除標題行
    });
    
  } catch (error) {
    return createResponse(false, '獲取試算表資訊時發生錯誤: ' + error.toString());
  }
}

/**
 * 清空工作表資料（保留標題行）
 */
function clearSheetData() {
  try {
    const spreadsheet = SpreadsheetApp.openById(SPREADSHEET_ID);
    const sheet = spreadsheet.getSheetByName(SHEET_NAME);
    
    if (!sheet) {
      return createResponse(false, '找不到指定的工作表');
    }
    
    const lastRow = sheet.getLastRow();
    
    if (lastRow > 1) {
      // 刪除除了標題行以外的所有資料
      sheet.deleteRows(2, lastRow - 1);
    }
    
    return createResponse(true, '成功清空工作表資料');
    
  } catch (error) {
    return createResponse(false, '清空工作表資料時發生錯誤: ' + error.toString());
  }
} 