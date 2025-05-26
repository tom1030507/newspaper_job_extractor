/**
 * Google Apps Script - 自動創建 Google Sheet 接收職缺資料
 * 
 * 部署說明：
 * 1. 複製此代碼到 Google Apps Script (script.google.com)
 * 2. 部署為網路應用程式
 * 3. 執行身分：我自己
 * 4. 有權存取的使用者：任何人
 * 5. 複製網路應用程式 URL 並更新 app.py 中的 apps_script_url
 */

function doPost(e) {
  // 添加詳細的日誌記錄
  console.log('=== doPost 開始執行 ===');
  console.log('請求類型:', typeof e);
  console.log('postData 存在:', !!e.postData);
  console.log('postData.contents 存在:', !!(e.postData && e.postData.contents));
  
  try {
    // 檢查是否有 postData
    if (!e.postData || !e.postData.contents) {
      console.error('沒有收到 postData 或 contents');
      return ContentService
        .createTextOutput(JSON.stringify({
          'error': '沒有收到請求資料',
          'received': e
        }))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    console.log('原始請求內容:', e.postData.contents);
    
    // 解析請求資料
    const requestData = JSON.parse(e.postData.contents);
    console.log('解析後的請求資料:', requestData);
    
    const action = requestData.action;
    console.log('執行動作:', action);
    
    if (action === 'addJobs') {
      console.log('開始處理 addJobs');
      return handleAddJobs(requestData);
    }
    
    console.log('未知的動作:', action);
    return ContentService
      .createTextOutput(JSON.stringify({
        'error': '未知的操作',
        'action': action
      }))
      .setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    console.error('處理請求時發生錯誤:', error);
    console.error('錯誤堆疊:', error.stack);
    return ContentService
      .createTextOutput(JSON.stringify({
        'error': '處理請求時發生錯誤: ' + error.toString(),
        'stack': error.stack,
        'received_data': e.postData ? e.postData.contents : 'no postData'
      }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function handleAddJobs(requestData) {
  console.log('=== handleAddJobs 開始執行 ===');
  
  try {
    const jobs = requestData.jobs;
    const metadata = requestData.metadata;
    
    console.log('工作資料:', jobs);
    console.log('元資料:', metadata);
    console.log('工作資料類型:', typeof jobs);
    console.log('工作資料是陣列:', Array.isArray(jobs));
    console.log('工作資料長度:', jobs ? jobs.length : 'undefined');
    
    if (!jobs || !Array.isArray(jobs)) {
      console.error('無效的職缺資料 - jobs:', jobs);
      throw new Error('無效的職缺資料');
    }
    
    if (jobs.length === 0) {
      console.error('職缺資料為空');
      throw new Error('沒有職缺資料可處理');
    }
    
    console.log('準備創建 Google Sheet...');
    
    // 創建新的 Google Sheet
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const sheetName = `報紙職缺提取_${timestamp}`;
    console.log('工作表名稱:', sheetName);
    
    const spreadsheet = SpreadsheetApp.create(sheetName);
    console.log('Google Sheet 創建成功，ID:', spreadsheet.getId());
    
    const sheet = spreadsheet.getActiveSheet();
    
    // 設置工作表標題
    sheet.setName('職缺資料');
    console.log('工作表標題設置完成');
    
    // 定義標題行
    const headers = [
      '編號', '工作', '行業', '時間', '薪資', '地點', 
      '聯絡方式', '其他', '來源圖片', '頁碼', '工作編號', '提取時間'
    ];
    
    // 設置標題行
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    console.log('標題行設置完成');
    
    // 設置標題行格式
    const headerRange = sheet.getRange(1, 1, 1, headers.length);
    headerRange.setBackground('#4285f4');
    headerRange.setFontColor('white');
    headerRange.setFontWeight('bold');
    headerRange.setHorizontalAlignment('center');
    console.log('標題行格式設置完成');
    
    // 添加職缺資料
    const dataRows = [];
    jobs.forEach((job, index) => {
      console.log(`處理第 ${index + 1} 筆工作資料:`, job);
      const row = [
        index + 1,  // 編號
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
        new Date().toLocaleString('zh-TW')  // 提取時間
      ];
      dataRows.push(row);
    });
    
    console.log('資料行數量:', dataRows.length);
    
    // 寫入資料到工作表
    if (dataRows.length > 0) {
      console.log('開始寫入資料到工作表...');
      sheet.getRange(2, 1, dataRows.length, headers.length).setValues(dataRows);
      console.log('資料寫入完成');
      
      // 自動調整欄寬
      sheet.autoResizeColumns(1, headers.length);
      console.log('欄寬調整完成');
      
      // 設置資料格式
      const dataRange = sheet.getRange(2, 1, dataRows.length, headers.length);
      dataRange.setVerticalAlignment('top');
      dataRange.setWrap(true);
      console.log('資料格式設置完成');
      
      // 設置邊框
      const allDataRange = sheet.getRange(1, 1, dataRows.length + 1, headers.length);
      allDataRange.setBorder(true, true, true, true, true, true);
      console.log('邊框設置完成');
  }
    
    console.log('開始創建摘要工作表...');
    
    // 創建摘要工作表
    const summarySheet = spreadsheet.insertSheet('處理摘要');
    const summaryData = [
      ['項目', '值'],
      ['處理ID', metadata ? metadata.process_id || '' : ''],
      ['總職缺數', jobs.length],
      ['處理時間', new Date().toLocaleString('zh-TW')],
      ['資料來源', metadata ? metadata.source || '' : ''],
      ['', ''],
      ['行業分布', ''],
  ];
  
    // 統計行業分布
    const industryCount = {};
    jobs.forEach(job => {
      const industry = job['行業'] || '未分類';
      industryCount[industry] = (industryCount[industry] || 0) + 1;
    });
    
    Object.entries(industryCount).forEach(([industry, count]) => {
      summaryData.push([industry, count]);
    });
    
    summarySheet.getRange(1, 1, summaryData.length, 2).setValues(summaryData);
    console.log('摘要資料寫入完成');
  
    // 設置摘要工作表格式
    const summaryHeaderRange = summarySheet.getRange(1, 1, 1, 2);
    summaryHeaderRange.setBackground('#34a853');
    summaryHeaderRange.setFontColor('white');
    summaryHeaderRange.setFontWeight('bold');
    
    summarySheet.autoResizeColumns(1, 2);
    console.log('摘要工作表格式設置完成');
    
    // 設置工作表保護（防止意外修改標題）
    const protection = sheet.getRange(1, 1, 1, headers.length).protect();
    protection.setDescription('標題行保護');
    protection.setWarningOnly(true);
    console.log('工作表保護設置完成');
    
    // 獲取 Google Sheet URL
    const spreadsheetUrl = spreadsheet.getUrl();
    const spreadsheetId = spreadsheet.getId();
    console.log('Google Sheet URL:', spreadsheetUrl);
    console.log('Google Sheet ID:', spreadsheetId);
    
    // 設置 Google Sheet 為公開檢視（可選）
    try {
      DriveApp.getFileById(spreadsheetId).setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
      console.log('分享權限設置完成');
  } catch (error) {
      console.log('無法設置檔案分享權限:', error);
}

  const response = {
      'success': true,
      'message': `成功創建 Google Sheet 並添加 ${jobs.length} 筆職缺資料`,
      'spreadsheet_url': spreadsheetUrl,
      'spreadsheet_id': spreadsheetId,
      'sheet_name': sheetName,
      'jobs_added': jobs.length,
      'timestamp': new Date().toISOString()
  };
  
    console.log('準備返回回應:', response);
  
  return ContentService
    .createTextOutput(JSON.stringify(response))
    .setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    console.error('處理職缺資料時發生錯誤:', error);
    console.error('錯誤堆疊:', error.stack);
    const errorResponse = {
      'error': '處理職缺資料時發生錯誤: ' + error.toString(),
      'stack': error.stack,
      'timestamp': new Date().toISOString()
    };
    console.log('錯誤回應:', errorResponse);
    return ContentService
      .createTextOutput(JSON.stringify(errorResponse))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// 測試函數（僅用於開發測試）
function testCreateSheet() {
  const testData = {
    action: 'addJobs',
    jobs: [
      {
        '工作': '測試職位',
        '行業': '測試行業',
        '時間': '9:00-18:00',
        '薪資': '30000',
        '地點': '台北市',
        '聯絡方式': '02-1234-5678',
        '其他': '測試備註',
        '來源圖片': 'test.jpg',
        '頁碼': '1',
        '工作編號': '1'
      }
    ],
    metadata: {
      process_id: 'test-123',
      total_jobs: 1,
      timestamp: new Date().toISOString(),
      source: 'test'
    }
  };
  
  const result = handleAddJobs(testData);
  console.log(result.getContent());
} 