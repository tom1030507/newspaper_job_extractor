// 全局變量
let imageData = {};

// 初始化函數
document.addEventListener('DOMContentLoaded', function() {
    // 從JSON script標籤中讀取圖片資料
    const imageDataScript = document.getElementById('imageDataScript');
    if (imageDataScript) {
        imageData = JSON.parse(imageDataScript.textContent);
    }
    
    // 當 Google Spreadsheet 模態框顯示時重置表單
    document.getElementById('spreadsheetModal').addEventListener('show.bs.modal', function () {
        resetSpreadsheetModal();
    });
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

// Google Spreadsheet 相關函數
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
    const appsScriptUrl = document.getElementById('appsScriptUrl').value.trim();
    
    // 隱藏錯誤訊息
    document.getElementById('errorMessage').classList.add('d-none');
    
    // 顯示發送狀態
    showSendingStatus();
    
    try {
        const processId = window.processId || '{{ process_id }}';
        const response = await fetch(`/send_to_spreadsheet/${processId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                apps_script_url: appsScriptUrl || ''
            })
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            showSendResult(true, result.message, result);
        } else {
            showSendResult(false, result.error || '發送失敗', result);
        }
        
    } catch (error) {
        console.error('發送錯誤:', error);
        showSendResult(false, '網路錯誤：' + error.message);
    }
}

function showSendingStatus() {
    // 隱藏主要內容區域
    document.getElementById('mainContent').classList.add('d-none');
    
    // 顯示發送狀態
    document.getElementById('sendingStatus').classList.remove('d-none');
    
    // 禁用發送按鈕
    const sendBtn = document.getElementById('sendToSpreadsheetBtn');
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> 創建中...';
}

function showSendResult(success, message, data = null) {
    // 隱藏發送狀態
    document.getElementById('sendingStatus').classList.add('d-none');
    
    if (success) {
        // 顯示成功結果
        const resultDiv = document.getElementById('sendResult');
        resultDiv.classList.remove('d-none');
        
        let successHtml = `
            <div class="alert alert-success">
                <i class="bi bi-check-circle"></i>
                <strong>創建成功！</strong><br>
                ${message}
                ${data && data.jobs_sent ? `<br><small class="text-muted">已添加 ${data.jobs_sent} 筆職缺資料</small>` : ''}
        `;
        
        // 如果有 Google Sheet URL，顯示連結
        if (data && data.spreadsheet_url) {
            successHtml += `
                <div class="success-actions mt-3">
                    <div class="actions-title">
                        <i class="bi bi-file-earmark-spreadsheet"></i>
                        Google Spreadsheet 已創建
                    </div>
                    <div class="d-grid gap-2">
                        <a href="${data.spreadsheet_url}" target="_blank" class="btn btn-success">
                            <i class="bi bi-box-arrow-up-right"></i> 開啟 Google Spreadsheet
                        </a>
                        <button class="btn btn-outline-secondary" onclick="copyToClipboard('${data.spreadsheet_url}')">
                            <i class="bi bi-clipboard"></i> 複製連結
                        </button>
                    </div>
                    <div class="spreadsheet-link mt-2" onclick="selectAllText(this)" title="點擊選取全部連結">
                        ${data.spreadsheet_url}
                    </div>
                </div>
        `;
        }
        
        successHtml += `</div>`;
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
        // 顯示錯誤訊息在頁腳
        const errorDiv = document.getElementById('errorMessage');
        errorDiv.innerHTML = `
            <div class="alert">
                <i class="bi bi-exclamation-triangle"></i>
                <strong>創建失敗！</strong> ${message}
                <br><small class="mt-1 d-block">請檢查網路連線或稍後再試。如果問題持續，請聯繫系統管理員。</small>
            </div>
        `;
        errorDiv.classList.remove('d-none');
        
        // 重新啟用發送按鈕
        const sendBtn = document.getElementById('sendToSpreadsheetBtn');
        sendBtn.disabled = false;
        sendBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> 重新嘗試';
        
        // 顯示主要內容讓用戶可以使用高級選項
        document.getElementById('mainContent').classList.remove('d-none');
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