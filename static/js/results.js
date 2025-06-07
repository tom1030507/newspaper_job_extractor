// 全局變量
let imageData = {};

// 測試函數 - 確保函數可以被正常調用
function testSpreadsheetFunction() {
    console.log('🧪 測試函數被調用！');
    alert('測試成功！函數可以正常調用。');
}

// 我們將在初始化後設置全域函數

window.testSpreadsheetFunction = testSpreadsheetFunction;

// 初始化函數
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Results page 初始化中...');
    
    // 從JSON script標籤中讀取圖片資料
    const imageDataScript = document.getElementById('imageDataScript');
    if (imageDataScript) {
        imageData = JSON.parse(imageDataScript.textContent);
        console.log('✅ 圖片資料載入完成，共 ' + Object.keys(imageData).length + ' 張圖片');
    }
    
    // 檢查重要的DOM元素
    console.log('🔍 檢查 DOM 元素...');
    const appsScriptUrl = document.getElementById('appsScriptUrl');
    const errorMessage = document.getElementById('errorMessage');
    const sendBtn = document.getElementById('sendToSpreadsheetBtn');
    const processIdElement = window.processId;
    
    console.log('📄 appsScriptUrl 元素:', appsScriptUrl ? '✅ 存在' : '❌ 不存在');
    console.log('📄 errorMessage 元素:', errorMessage ? '✅ 存在' : '❌ 不存在');
    console.log('📄 sendBtn 元素:', sendBtn ? '✅ 存在' : '❌ 不存在');
    console.log('📄 processId:', processIdElement || '❌ 未設置');
    
    // 初始化現代化功能
    initModernFeatures();
    
    // 初始化圖片檢視功能
    initImageViewing();
    
    // 初始化下載模態框
    initDownloadModal();
    
    // 初始化 Google Sheets 模態框
    initSpreadsheetModal();
    
    // 初始化表格互動功能
    initTableInteractions();
    
    // 初始化表格排序功能
    initTableSorting();
    
    // 禁用頁面動畫
    // initPageAnimations();
    
    // 初始化鍵盤快捷鍵
    initKeyboardShortcuts();
    
    // 初始化通知系統
    initNotificationSystem();
    
    // 當 Google Sheets 模態框顯示時重置表單
    const spreadsheetModal = document.getElementById('spreadsheetModal');
    if (spreadsheetModal) {
        spreadsheetModal.addEventListener('show.bs.modal', function () {
            console.log('📋 Spreadsheet 模態框正在打開，重置表單...');
            resetSpreadsheetModal();
        });
    }
    
    // 測試按鈕事件
    if (sendBtn) {
        sendBtn.addEventListener('click', function(e) {
            console.log('🖱️ sendToSpreadsheetBtn 被點擊了！');
            console.log('📍 事件對象:', e);
        });
    }
    
    console.log('🎉 Results page 初始化完成!');
    
    // 將 sendToSpreadsheet 函數暴露到全域作用域，以供HTML onclick 使用
    window.sendToSpreadsheet = sendToSpreadsheet;
    console.log('🌍 sendToSpreadsheet 函數已暴露到全域作用域');
    
    // 設置全域錯誤處理器
    window.addEventListener('error', function(event) {
        console.error('🚨 全域 JavaScript 錯誤:', event.error);
        showNotification('發生未預期的錯誤，請重新載入頁面或聯繫支援', 'error', 10000);
    });
    
    window.addEventListener('unhandledrejection', function(event) {
        console.error('🚨 未處理的 Promise 拒絕:', event.reason);
        showNotification('操作失敗，請重試', 'error', 8000);
    });
    
    // 顯示歡迎通知
    setTimeout(() => {
        showNotification(
            '頁面載入完成！您可以查看分析結果、下載資料或創建 Google Sheets。',
            'success',
            5000
        );
    }, 1000);
});

// 圖片相關函數
function showImageModal(imageId) {
    console.log('嘗試顯示圖片:', imageId);
    console.log('可用的圖片:', Object.keys(imageData));
    
    // 顯示模態框
    const imageModal = new bootstrap.Modal(document.getElementById('imageModal'));
    imageModal.show();
    
    // 設置模態框標題
    const modalTitle = document.getElementById('imageModalLabel');
    modalTitle.textContent = '圖片預覽 - ' + imageId;
    
    // 顯示載入狀態
    const loadingDiv = document.getElementById('imageLoading');
    const modalImage = document.getElementById('modalImage');
    const errorDiv = document.getElementById('imageError');
    
    loadingDiv.classList.remove('d-none');
    modalImage.classList.add('d-none');
    errorDiv.classList.add('d-none');
    
    // 從JavaScript資料中獲取圖片
    const imgData = imageData[imageId];
    
    if (imgData && imgData.src) {
        // 預載圖片
        const preloadImage = new Image();
        preloadImage.onload = function() {
            // 圖片載入成功
            modalImage.src = imgData.src;
            loadingDiv.classList.add('d-none');
            modalImage.classList.remove('d-none');
        };
        preloadImage.onerror = function() {
            // 圖片載入失敗
            loadingDiv.classList.add('d-none');
            errorDiv.classList.remove('d-none');
            errorDiv.querySelector('p').textContent = '圖片載入失敗';
        };
        preloadImage.src = imgData.src;
        
        // 設置詳細描述按鈕的功能
        const viewDetailBtn = document.getElementById('viewImageDetailBtn');
        viewDetailBtn.onclick = function() {
            // 關閉模態框
            const modal = bootstrap.Modal.getInstance(document.getElementById('imageModal'));
            modal.hide();
            
            // 切換到圖片描述標籤並滾動到對應圖片
            switchToImageTab(imageId);
        };
    } else {
        // 找不到圖片資料
        loadingDiv.classList.add('d-none');
        errorDiv.classList.remove('d-none');
        errorDiv.querySelector('p').textContent = '找不到對應的圖片資料';
        console.log('可用的圖片ID:', Object.keys(imageData));
        console.log('請求的圖片ID:', imageId);
    }
}

function switchToImageTab(imageId) {
    console.log('切換到圖片標籤，目標圖片ID:', imageId);
    
    // 切換到圖片描述標籤
    const imageTab = document.getElementById('images-tab');
    const jobsTab = document.getElementById('jobs-tab');
    const imagesPanel = document.getElementById('images');
    const jobsPanel = document.getElementById('jobs');
    
    // 移除當前標籤的active狀態
    jobsTab.classList.remove('active');
    jobsTab.setAttribute('aria-selected', 'false');
    jobsPanel.classList.remove('show', 'active');
    
    // 啟用圖片標籤
    imageTab.classList.add('active');
    imageTab.setAttribute('aria-selected', 'true');
    imagesPanel.classList.add('show', 'active');
    
    // 尋找對應的圖片容器並滾動到該位置
    // 使用重試機制，因為標籤切換可能需要時間
    function findAndScrollToImage(retryCount = 0) {
        console.log(`尋找目標圖片元素... (嘗試 ${retryCount + 1})`);
        // 只在圖片描述標籤中尋找，避免找到工作列表中的按鈕
        const targetImage = document.querySelector(`#images [data-image-id="${imageId}"]`);
        console.log('找到的目標圖片元素:', targetImage);
        
        if (targetImage) {
            // 找到包含該圖片的最近的圖片容器
            const imageContainer = targetImage.closest('.col') || targetImage.closest('.block-image');
            console.log('找到的圖片容器:', imageContainer);
            
            if (imageContainer) {
                // 尋找容器內的圖片元素
                const imageElement = imageContainer.querySelector('img');
                console.log('找到的圖片元素:', imageElement);
                
                if (imageElement) {
                    // 滾動到圖片位置，讓圖片顯示時上方有適當間距
                    imageElement.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'center' 
                    });
                    
                    // 添加高亮效果到圖片
                    imageElement.style.border = '3px solid #0d6efd';
                    imageElement.style.borderRadius = '8px';
                    imageElement.style.transition = 'all 0.3s ease';
                    imageElement.style.boxShadow = '0 0 15px rgba(13, 110, 253, 0.5)';
                    
                    // 3秒後移除高亮效果
                    setTimeout(function() {
                        imageElement.style.border = '';
                        imageElement.style.borderRadius = '';
                        imageElement.style.boxShadow = '';
                    }, 3000);
                } else {
                    // 如果沒找到圖片元素，則滾動到容器中央
                    imageContainer.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'center' 
                    });
                    
                    // 添加高亮效果到容器
                    imageContainer.style.border = '3px solid #0d6efd';
                    imageContainer.style.borderRadius = '8px';
                    imageContainer.style.transition = 'all 0.3s ease';
                    
                    // 3秒後移除高亮效果
                    setTimeout(function() {
                        imageContainer.style.border = '';
                        imageContainer.style.borderRadius = '';
                    }, 3000);
                }
                
                console.log('成功滾動到目標圖片');
                return;
            } else {
                console.log('未找到圖片容器');
            }
        } else {
            console.log('未找到目標圖片元素');
            // 列出所有可用的data-image-id
            const allImageElements = document.querySelectorAll('[data-image-id]');
            console.log('所有可用的圖片元素:', Array.from(allImageElements).map(el => el.getAttribute('data-image-id')));
            
            // 如果還沒找到且重試次數少於3次，則重試
            if (retryCount < 3) {
                setTimeout(() => findAndScrollToImage(retryCount + 1), 200);
                return;
            }
        }
        
        console.log('無法找到或滾動到目標圖片');
    }
    
    setTimeout(findAndScrollToImage, 100);
}

function showStepImageModal(filename, stepNumber, base64Data, format) {
    // 顯示處理步驟圖像模態框
    const stepImageModal = new bootstrap.Modal(document.getElementById('stepImageModal'));
    stepImageModal.show();
    
    // 設置模態框標題
    const modalTitle = document.getElementById('stepImageModalLabel');
    const stepNames = {
        '1': '原始圖像',
        '2': '初始區塊檢測',
        '3': '區塊優化處理',
        '4': '最終結果展示'
    };
    modalTitle.textContent = `步驟 ${stepNumber}: ${stepNames[stepNumber] || '處理圖像'}`;
    
    // 設置圖像
    const stepModalImage = document.getElementById('stepModalImage');
    stepModalImage.src = `data:image/${format};base64,${base64Data}`;
}

// 下載相關函數
function downloadSelected() {
    // 獲取選中的選項
    const checkboxes = document.querySelectorAll('input[name="include"]:checked');
    const selectedOptions = Array.from(checkboxes).map(cb => cb.value);
    
    if (selectedOptions.length === 0) {
        alert('請至少選擇一個下載項目！');
        return;
    }
    
    // 構建下載URL
    const processId = window.processId || '{{ process_id }}';
    const params = selectedOptions.map(option => `include=${option}`).join('&');
    const downloadUrl = `/download/${processId}?${params}`;
    
    // 關閉模態框
    const modal = bootstrap.Modal.getInstance(document.getElementById('downloadModal'));
    modal.hide();
    
    // 開始下載
    window.location.href = downloadUrl;
}

// Google Sheets 相關函數
function resetSpreadsheetModal() {
    // 顯示主要內容區域
    document.getElementById('mainContent').classList.remove('d-none');
    
    // 重置表單
    document.getElementById('spreadsheetForm').reset();
    
    // 隱藏狀態和結果顯示
    document.getElementById('sendingStatus').classList.add('d-none');
    document.getElementById('sendResult').classList.add('d-none');
    
    // 隱藏錯誤訊息
    document.getElementById('errorMessage').classList.add('d-none');
    
    // 啟用發送按鈕
    const sendBtn = document.getElementById('sendToSpreadsheetBtn');
    sendBtn.disabled = false;
    sendBtn.innerHTML = '<i class="bi bi-plus-circle"></i> 立即創建';
}

async function sendToSpreadsheet() {
    console.log('📤 開始發送到 Google Sheets...');
    
    // 檢查必要的DOM元素是否存在
    const appsScriptUrlElement = document.getElementById('appsScriptUrl');
    const errorMessageElement = document.getElementById('errorMessage');
    
    if (!appsScriptUrlElement) {
        console.error('❌ 找不到 appsScriptUrl 輸入框');
        alert('系統錯誤：找不到輸入框元素，請重新載入頁面');
        return;
    }
    
    if (!errorMessageElement) {
        console.error('❌ 找不到 errorMessage 元素');
        alert('系統錯誤：找不到錯誤訊息元素，請重新載入頁面');
        return;
    }
    
    const appsScriptUrl = appsScriptUrlElement.value.trim();
    console.log('📝 Apps Script URL:', appsScriptUrl || '(使用預設)');
    
    // 隱藏錯誤訊息
    errorMessageElement.classList.add('d-none');
    
    // 顯示發送狀態
    showSendingStatus();
    
    try {
        const processId = window.processId;
        console.log('🔍 Process ID:', processId);
        
        if (!processId) {
            throw new Error('找不到處理程序 ID');
        }
        
        const requestData = {
            apps_script_url: appsScriptUrl || ''
        };
        console.log('📦 請求資料:', requestData);
        
        const response = await fetch(`/send_to_spreadsheet/${processId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });
        
        console.log('📡 回應狀態:', response.status, response.statusText);
        
        const result = await response.json();
        console.log('📊 回應資料:', result);
        
        if (response.ok && result.success) {
            console.log('✅ 發送成功');
            showSendResult(true, result.message, result);
        } else {
            console.log('❌ 發送失敗:', result.error);
            showSendResult(false, result.error || '發送失敗', result);
            
            // 額外顯示通知
            showNotification('Google Sheets 創建失敗：' + (result.error || '未知錯誤'), 'error', 8000);
        }
        
    } catch (error) {
        console.error('💥 發送錯誤:', error);
        const errorMessage = '網路錯誤：' + error.message;
        showSendResult(false, errorMessage);
        
        // 額外顯示通知
        showNotification('無法連接到伺服器，請檢查網路連線', 'error', 8000);
    }
}

function showSendingStatus() {
    console.log('🔄 顯示發送狀態...');
    
    // 隱藏主要內容區域
    const mainContent = document.getElementById('mainContent');
    if (mainContent) {
        mainContent.classList.add('d-none');
    } else {
        console.error('❌ 找不到 mainContent 元素');
    }
    
    // 顯示發送狀態
    const sendingStatus = document.getElementById('sendingStatus');
    if (sendingStatus) {
        sendingStatus.classList.remove('d-none');
    } else {
        console.error('❌ 找不到 sendingStatus 元素');
        showNotification('正在創建 Google Sheets...', 'info', 3000);
    }
    
    // 禁用發送按鈕
    const sendBtn = document.getElementById('sendToSpreadsheetBtn');
    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> 創建中...';
    } else {
        console.error('❌ 找不到 sendToSpreadsheetBtn 元素');
    }
}

function showSendResult(success, message, data = null) {
    // 隱藏發送狀態
    document.getElementById('sendingStatus').classList.add('d-none');
    
    if (success) {
        // 顯示成功結果
        const resultDiv = document.getElementById('sendResult');
        resultDiv.classList.remove('d-none');
        
        let successHtml = `
            <div class="spreadsheet-success-card">
                <div class="success-header">
                    <div class="success-icon">
                        <i class="bi bi-check-circle-fill"></i>
                    </div>
                    <div class="success-info">
                                    <h4 class="success-title">Google Sheets 已成功創建</h4>
            <p class="success-subtitle">您的職缺資料已完整匯出到 Google Sheets</p>
                    </div>
                </div>
                
                <div class="spreadsheet-details">
                    <div class="detail-item">
                        <i class="bi bi-table"></i>
                        <span>已匯出 ${data && data.sent_jobs ? data.sent_jobs : (data && data.jobs_sent ? data.jobs_sent : '0')} 筆職缺資料</span>
                    </div>
                    <div class="detail-item">
                        <i class="bi bi-clock"></i>
                        <span>創建時間：${new Date().toLocaleString('zh-TW')}</span>
                    </div>
                </div>
                
                <div class="action-buttons-grid">
                    <a href="${data && data.spreadsheet_url ? data.spreadsheet_url : '#'}" target="_blank" class="primary-action-btn">
                        <i class="bi bi-box-arrow-up-right"></i>
                        <span>開啟 Google Sheets</span>
                    </a>
                    <button class="secondary-action-btn" onclick="copyToClipboard('${data && data.spreadsheet_url ? data.spreadsheet_url : ''}')">
                        <i class="bi bi-clipboard"></i>
                        <span>複製連結</span>
                    </button>
                </div>
            </div>
        `;
        resultDiv.innerHTML = successHtml;
        
        // 更新按鈕為關閉
        const sendBtn = document.getElementById('sendToSpreadsheetBtn');
        sendBtn.disabled = false;
        sendBtn.innerHTML = '<i class="bi bi-check"></i> 完成';
        sendBtn.onclick = function() {
            const modal = bootstrap.Modal.getInstance(document.getElementById('spreadsheetModal'));
            modal.hide();
        };
        
    } else {
        // 顯示錯誤訊息
        const errorDiv = document.getElementById('errorMessage');
        
        if (!errorDiv) {
            console.error('❌ 找不到 errorMessage 元素');
            // 如果找不到錯誤顯示元素，使用通知系統
            showNotification('創建失敗：' + message, 'error', 10000);
            alert('創建失敗：' + message);
        } else {
            errorDiv.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i>
                    <strong>創建失敗！</strong> ${message}
                    <br><small class="mt-1 d-block">請檢查網路連線或稍後再試。如果問題持續，請聯繫系統管理員。</small>
                </div>
            `;
            errorDiv.classList.remove('d-none');
        }
        
        // 重新啟用發送按鈕
        const sendBtn = document.getElementById('sendToSpreadsheetBtn');
        if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> 重新嘗試';
        }
        
        // 顯示主要內容讓用戶可以使用高級選項
        const mainContent = document.getElementById('mainContent');
        if (mainContent) {
            mainContent.classList.remove('d-none');
        }
    }
}

// 複製到剪貼簿相關函數
function copyToClipboard(text) {
    // 先嘗試使用現代的 Clipboard API
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(function() {
            showCopySuccess();
        }).catch(function(err) {
            console.error('Clipboard API 失敗: ', err);
            fallbackCopyToClipboard(text);
        });
    } else {
        // 使用備用方法
        fallbackCopyToClipboard(text);
    }
}

function fallbackCopyToClipboard(text) {
    // 創建一個臨時的 textarea 元素
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    
    try {
        textArea.focus();
        textArea.select();
        
        // 嘗試使用 execCommand
        const successful = document.execCommand('copy');
        if (successful) {
            showCopySuccess();
        } else {
            showCopyError();
        }
    } catch (err) {
        console.error('備用複製方法失敗: ', err);
        showCopyError();
    } finally {
        document.body.removeChild(textArea);
    }
}

function showCopySuccess() {
    // 顯示頁面提示
    showPageSuccessMessage();
    
    // 顯示按鈕狀態變化（如果有事件對象的話）
    if (typeof event !== 'undefined' && event.target) {
        const button = event.target.closest('button');
        if (button) {
            const originalText = button.innerHTML;
            button.innerHTML = '<i class="bi bi-check"></i> 已複製';
            button.classList.remove('btn-outline-secondary');
            button.classList.add('btn-success');
            
            // 2秒後恢復按鈕狀態
            setTimeout(function() {
                button.innerHTML = originalText;
                button.classList.remove('btn-success');
                button.classList.add('btn-outline-secondary');
            }, 2000);
        }
    }
}

function showPageSuccessMessage() {
    const successMessage = document.getElementById('copySuccessMessage');
    
    if (!successMessage) {
        console.error('找不到 copySuccessMessage 元素');
        return;
    }
    
    console.log('顯示複製成功提示');
    
    // 移除之前可能存在的隱藏類別
    successMessage.classList.remove('d-none');
    
    // 重置動畫
    successMessage.style.animation = 'none';
    successMessage.offsetHeight; // 觸發重排
    successMessage.style.animation = 'slideInRight 0.4s ease-out';
    
    // 3秒後自動隱藏
    setTimeout(function() {
        successMessage.style.animation = 'slideOutRight 0.4s ease-out';
        setTimeout(function() {
            successMessage.classList.add('d-none');
            successMessage.style.animation = '';
        }, 400);
    }, 3000);
}

// 測試函數 - 可以在瀏覽器控制台中調用
function testCopySuccess() {
    showPageSuccessMessage();
}

function showCopyError() {
    // 顯示複製失敗的提示，並提供手動複製的選項
    if (typeof event !== 'undefined' && event.target) {
        const button = event.target.closest('button');
        if (button) {
            const originalText = button.innerHTML;
            
            // 暫時顯示失敗狀態
            button.innerHTML = '<i class="bi bi-x"></i> 複製失敗';
            button.classList.remove('btn-outline-secondary');
            button.classList.add('btn-warning');
            
            // 2秒後恢復原狀
            setTimeout(function() {
                button.innerHTML = originalText;
                button.classList.remove('btn-warning');
                button.classList.add('btn-outline-secondary');
            }, 2000);
        }
    }
    
    // 顯示提示訊息
    alert('無法自動複製連結。請手動選取上方的連結並複製。\n\n提示：您可以點擊連結框中的文字，然後使用 Ctrl+A 全選，再按 Ctrl+C 複製。');
}

function selectAllText(element) {
    // 選取元素中的所有文字
    if (window.getSelection && document.createRange) {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(element);
        selection.removeAllRanges();
        selection.addRange(range);
    } else if (document.selection && document.body.createTextRange) {
        // IE 支援
        const range = document.body.createTextRange();
        range.moveToElementText(element);
        range.select();
    }
}

function isValidUrl(string) {
    try {
        new URL(string);
        return true;
    } catch (_) {
        return false;
    }
}

// 重複的初始化已移除，統一在主初始化函數中處理

// 現代化功能初始化
function initModernFeatures() {
    // 添加平滑滾動
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // 添加工具提示
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl, {
            trigger: 'hover focus'
        });
    });
    
    // 添加彈出框
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

// 圖片查看功能
function initImageViewing() {
    const imageModal = document.getElementById('imageModal');
    const modalImage = document.getElementById('modalImage');
    const modalImageTitle = imageModal ? imageModal.querySelector('.modal-title') : null;
    
    // 為所有圖片查看按鈕添加事件監聽器
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('view-image-btn')) {
            e.preventDefault();
            
            const imageName = e.target.getAttribute('data-image');
            const imageTitle = e.target.getAttribute('data-title') || imageName;
            
            if (modalImage && imageName) {
                // 添加載入動畫
                showImageLoadingState(modalImage);
                
                // 設置圖片源
                modalImage.src = `/view_image/${getProcessId()}/${imageName}`;
                modalImage.alt = imageTitle;
                
                // 設置標題
                if (modalImageTitle) {
                    modalImageTitle.textContent = imageTitle;
                }
                
                // 圖片載入完成後移除載入狀態
                modalImage.onload = function() {
                    hideImageLoadingState(modalImage);
                    addImageZoomFeature(modalImage);
                };
                
                modalImage.onerror = function() {
                    showImageError(modalImage, '圖片載入失敗');
                };
                
                // 高亮對應的圖片區塊
                highlightCorrespondingImage(imageName);
            }
        }
    });
    
    // 模態框關閉時清理
    if (imageModal) {
        imageModal.addEventListener('hidden.bs.modal', function() {
            if (modalImage) {
                modalImage.src = '';
                modalImage.style.transform = 'scale(1)';
                modalImage.style.cursor = 'default';
            }
            clearImageHighlight();
        });
    }
}

// 顯示圖片載入狀態
function showImageLoadingState(img) {
    const container = img.parentElement;
    container.style.position = 'relative';
    
    const loader = document.createElement('div');
    loader.className = 'image-loader';
    loader.innerHTML = `
        <div class="d-flex justify-content-center align-items-center h-100">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">載入中...</span>
            </div>
        </div>
    `;
    loader.style.cssText = `
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(2px);
        border-radius: 10px;
        z-index: 10;
    `;
    
    container.appendChild(loader);
}

// 隱藏圖片載入狀態
function hideImageLoadingState(img) {
    const container = img.parentElement;
    const loader = container.querySelector('.image-loader');
    if (loader) {
        loader.remove();
    }
}

// 顯示圖片錯誤
function showImageError(img, message) {
    hideImageLoadingState(img);
    img.style.display = 'none';
    
    const container = img.parentElement;
    const errorDiv = document.createElement('div');
    errorDiv.className = 'image-error text-center p-5';
    errorDiv.innerHTML = `
        <i class="bi bi-exclamation-triangle text-warning display-4 mb-3"></i>
        <h5 class="text-muted">${message}</h5>
    `;
    
    container.appendChild(errorDiv);
}

// 添加圖片縮放功能
function addImageZoomFeature(img) {
    let isZoomed = false;
    
    img.style.cursor = 'zoom-in';
    img.style.transition = 'transform 0.3s ease';
    
    img.onclick = function() {
        if (!isZoomed) {
            img.style.transform = 'scale(1.5)';
            img.style.cursor = 'zoom-out';
            isZoomed = true;
        } else {
            img.style.transform = 'scale(1)';
            img.style.cursor = 'zoom-in';
            isZoomed = false;
        }
    };
}

// 高亮對應的圖片區塊
function highlightCorrespondingImage(imageName) {
    const imageBlocks = document.querySelectorAll('.block-image');
    imageBlocks.forEach(block => {
        const img = block.querySelector('img');
        if (img && img.src.includes(imageName)) {
            block.classList.add('highlighted-image');
            
            // 滾動到對應位置
            setTimeout(() => {
                block.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            }, 100);
        }
    });
}

// 清除圖片高亮
function clearImageHighlight() {
    document.querySelectorAll('.highlighted-image').forEach(element => {
        element.classList.remove('highlighted-image');
    });
}

// 下載模態框功能
function initDownloadModal() {
    const downloadModal = document.getElementById('downloadModal');
    const downloadBtn = document.getElementById('confirmDownload');
    
    if (downloadBtn) {
        downloadBtn.addEventListener('click', function() {
            const selectedOptions = getSelectedDownloadOptions();
            
            if (selectedOptions.length === 0) {
                showNotification('請至少選擇一個下載項目', 'warning');
                return;
            }
            
            // 顯示下載進度
            showDownloadProgress();
            
            // 構建下載 URL
            const params = new URLSearchParams();
            selectedOptions.forEach(option => {
                params.append('include', option);
            });
            
            const downloadUrl = `/download/${getProcessId()}?${params.toString()}`;
            
            // 創建隱藏的下載鏈接
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = '';
            link.style.display = 'none';
            
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // 隱藏模態框
            const modal = bootstrap.Modal.getInstance(downloadModal);
            modal.hide();
            
            // 顯示成功通知
            setTimeout(() => {
                hideDownloadProgress();
                showNotification('下載已開始，請檢查瀏覽器下載資料夾', 'success');
            }, 1000);
        });
    }
    
    // 全選/取消全選功能
    const selectAllBtn = document.getElementById('selectAllDownload');
    const deselectAllBtn = document.getElementById('deselectAllDownload');
    
    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', function() {
            document.querySelectorAll('#downloadModal input[type="checkbox"]').forEach(checkbox => {
                checkbox.checked = true;
            });
            updateDownloadPreview();
        });
    }
    
    if (deselectAllBtn) {
        deselectAllBtn.addEventListener('click', function() {
            document.querySelectorAll('#downloadModal input[type="checkbox"]').forEach(checkbox => {
                checkbox.checked = false;
            });
            updateDownloadPreview();
        });
    }
    
    // 監聽選項變化
    document.addEventListener('change', function(e) {
        if (e.target.type === 'checkbox' && e.target.closest('#downloadModal')) {
            updateDownloadPreview();
        }
    });
}

// 獲取選中的下載選項
function getSelectedDownloadOptions() {
    const checkboxes = document.querySelectorAll('#downloadModal input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

// 更新下載預覽
function updateDownloadPreview() {
    const selectedOptions = getSelectedDownloadOptions();
    const previewDiv = document.getElementById('downloadPreview');
    
    if (previewDiv) {
        if (selectedOptions.length > 0) {
            const optionNames = {
                'csv': 'CSV 工作資料表',
                'sql': 'SQL 資料庫檔案',
                'images': '工作區塊圖片',
                'descriptions': 'AI 分析描述',
                'processing_steps': '處理步驟圖片',
                'readme': '說明文件'
            };
            
            const selectedNames = selectedOptions.map(opt => optionNames[opt] || opt);
            previewDiv.innerHTML = `
                <div class="alert alert-info mb-0">
                    <i class="bi bi-info-circle me-2"></i>
                    將下載：${selectedNames.join('、')}
                </div>
            `;
        } else {
            previewDiv.innerHTML = `
                <div class="alert alert-warning mb-0">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    請至少選擇一個項目
                </div>
            `;
        }
    }
}

// 顯示下載進度
function showDownloadProgress() {
    const progressDiv = document.createElement('div');
    progressDiv.id = 'downloadProgress';
    progressDiv.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center';
    progressDiv.style.cssText = `
        background: rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(5px);
        z-index: 9999;
    `;
    
    progressDiv.innerHTML = `
        <div class="bg-white p-4 rounded-3 text-center shadow-lg">
            <div class="spinner-border text-primary mb-3" role="status">
                <span class="visually-hidden">下載中...</span>
            </div>
            <h5>正在準備下載檔案...</h5>
            <p class="text-muted mb-0">請稍候</p>
        </div>
    `;
    
    document.body.appendChild(progressDiv);
}

// 隱藏下載進度
function hideDownloadProgress() {
    const progressDiv = document.getElementById('downloadProgress');
    if (progressDiv) {
        progressDiv.remove();
    }
}

// Google Sheets 模態框功能 - 簡化版本，使用主要的sendToSpreadsheet函數
function initSpreadsheetModal() {
    const modal = document.getElementById('spreadsheetModal');
    
    // 重置模態框狀態
    if (modal) {
        modal.addEventListener('show.bs.modal', function() {
            console.log('📋 初始化 Spreadsheet 模態框...');
            resetSpreadsheetModal();
        });
    }
}

// 這些函數已經在前面定義過了，移除重複定義以避免衝突

// 複製到剪貼簿功能
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showCopySuccessMessage();
    }).catch(function(err) {
        // 備用方法
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.opacity = '0';
        document.body.appendChild(textArea);
        textArea.select();
        
        try {
            document.execCommand('copy');
            showCopySuccessMessage();
        } catch (err) {
            showNotification('複製失敗，請手動選取並複製', 'error');
        }
        
        document.body.removeChild(textArea);
    });
}

// 顯示複製成功訊息
function showCopySuccessMessage() {
    // 移除舊的訊息
    const existingMessage = document.getElementById('copySuccessMessage');
    if (existingMessage) {
        existingMessage.remove();
    }
    
    // 創建新的成功訊息
    const message = document.createElement('div');
    message.id = 'copySuccessMessage';
    message.innerHTML = `
        <div class="success-icon">
            <i class="bi bi-check-circle-fill"></i>
        </div>
        <div>
            <div class="success-text">複製成功！</div>
            <div class="success-subtext">連結已複製到剪貼簿</div>
        </div>
    `;
    
    document.body.appendChild(message);
    
    // 3秒後自動移除
    setTimeout(() => {
        if (message.parentNode) {
            message.classList.add('hide');
            setTimeout(() => {
                if (message.parentNode) {
                    message.remove();
                }
            }, 300);
        }
    }, 3000);
}

// 表格交互功能
function initTableInteractions() {
    // 表格行懸停效果
    const tableRows = document.querySelectorAll('.jobs-table tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.01)';
        });
        
        row.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
    
    // 表格排序功能（如果需要）
    initTableSorting();
}

// 表格排序功能
function initTableSorting() {
    const headers = document.querySelectorAll('.jobs-table th[data-sort]');
    
    headers.forEach(header => {
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            const column = this.getAttribute('data-sort');
            const table = this.closest('table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            
            // 確定排序方向
            const isAscending = !this.classList.contains('sort-asc');
            
            // 移除所有排序類別
            headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
            
            // 添加新的排序類別
            this.classList.add(isAscending ? 'sort-asc' : 'sort-desc');
            
            // 排序行
            rows.sort((a, b) => {
                const aValue = a.cells[getColumnIndex(column)].textContent.trim();
                const bValue = b.cells[getColumnIndex(column)].textContent.trim();
                
                if (isAscending) {
                    return aValue.localeCompare(bValue, 'zh-Hant');
                } else {
                    return bValue.localeCompare(aValue, 'zh-Hant');
                }
            });
            
            // 重新插入排序後的行
            rows.forEach(row => tbody.appendChild(row));
        });
    });
}

// 獲取欄位索引
function getColumnIndex(columnName) {
    const columnMap = {
        'job': 0,
        'industry': 1,
        'time': 2,
        'salary': 3,
        'location': 4,
        'contact': 5,
        'other': 6,
        'source': 7
    };
    return columnMap[columnName] || 0;
}

// 頁面動畫初始化
function initPageAnimations() {
    // 禁用滾動動畫以避免干擾
    /*
    // 添加滾動動畫
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate__animated', 'animate__fadeInUp');
            }
        });
    }, observerOptions);
    
    // 觀察所有需要動畫的元素
    document.querySelectorAll('.card, .block-image, .stat-card').forEach(el => {
        observer.observe(el);
    });
    
    // 添加浮動動畫到統計卡片
    addFloatingAnimation();
    */
    
    // 僅保留按鈕波紋效果
    addButtonRippleEffect();
}

// 禁用浮動動畫
function addFloatingAnimation() {
    // 浮動動畫已禁用
    /*
    const statCards = document.querySelectorAll('.stat-card');
    
    statCards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.2}s`;
        card.classList.add('animate__animated', 'animate__fadeInUp');
    });
    */
}

// 添加按鈕波紋效果
function addButtonRippleEffect() {
    document.querySelectorAll('.btn, .action-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            const rect = this.getBoundingClientRect();
            const ripple = document.createElement('span');
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                left: ${x}px;
                top: ${y}px;
                background: rgba(255, 255, 255, 0.5);
                border-radius: 50%;
                transform: scale(0);
                animation: ripple 0.6s linear;
                pointer-events: none;
            `;
            
            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);
            
            setTimeout(() => {
                if (ripple.parentNode) {
                    ripple.remove();
                }
            }, 600);
        });
    });
    
    // 添加 CSS 動畫（如果不存在）
    if (!document.getElementById('ripple-animation')) {
        const style = document.createElement('style');
        style.id = 'ripple-animation';
        style.textContent = `
            @keyframes ripple {
                to {
                    transform: scale(4);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
}

// 鍵盤快捷鍵
function initKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Escape - 關閉所有模態框
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal.show').forEach(modal => {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) {
                    modalInstance.hide();
                }
            });
        }
    });
}

// 通知系統
function initNotificationSystem() {
    // 創建通知容器（如果不存在）
    if (!document.getElementById('notification-container')) {
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 350px;
        `;
        document.body.appendChild(container);
    }
}

// 顯示通知
function showNotification(message, type = 'info', duration = 4000) {
    const container = document.getElementById('notification-container');
    if (!container) return;
    
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show mb-2`;
    notification.style.cssText = `
        animation: slideInRight 0.3s ease;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        border: none;
        border-radius: 10px;
        backdrop-filter: blur(10px);
    `;
    
    const icons = {
        success: 'check-circle-fill',
        error: 'exclamation-triangle-fill',
        warning: 'exclamation-circle-fill',
        info: 'info-circle-fill'
    };
    
    notification.innerHTML = `
        <i class="bi bi-${icons[type]} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.appendChild(notification);
    
    // 自動移除
    setTimeout(() => {
        if (notification.parentNode) {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }
    }, duration);
}

// 工具函數
function getProcessId() {
    const pathSegments = window.location.pathname.split('/');
    return pathSegments[pathSegments.length - 1];
}

// 格式化檔案大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 格式化時間
function formatTime(date) {
    return new Intl.DateTimeFormat('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    }).format(date);
}

// 導出到全域作用域（為了向後兼容）
window.copyToClipboard = copyToClipboard;
window.showNotification = showNotification;
window.showImageModal = showImageModal;
window.switchToImageTab = switchToImageTab;
window.showStepImageModal = showStepImageModal;
window.downloadSelected = downloadSelected;
window.sendToSpreadsheet = sendToSpreadsheet;

// 版本信息
console.log('📊 Results.js v2.0 - 現代化版本已載入');
console.log('🎨 功能包括: 現代化UI、動畫效果、鍵盤快捷鍵、通知系統、表格排序');
console.log('⌨️ 快捷鍵: ESC (關閉模態框)');

// 性能監控
if (typeof performance !== 'undefined' && performance.mark) {
    performance.mark('results-js-loaded');
} 