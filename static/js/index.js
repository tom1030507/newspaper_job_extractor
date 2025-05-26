// 文件上傳處理
document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const loadingContainer = document.getElementById('loading-container');
    const fileInput = document.getElementById('files');
    const fileListContainer = document.getElementById('file-list');

    // 表單提交處理
    uploadForm.addEventListener('submit', function(e) {
        const files = fileInput.files;
        
        // 檢查是否選擇了文件
        if (!files || files.length === 0) {
            e.preventDefault();
            alert('請選擇要上傳的檔案！');
            return;
        }
        
        // 檢查文件數量限制 (最多10個檔案)
        const maxFiles = 10;
        if (files.length > maxFiles) {
            e.preventDefault();
            alert(`一次最多只能選擇 ${maxFiles} 個檔案！`);
            return;
        }
        
        // 檢查每個文件
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf'];
        const maxSize = 50 * 1024 * 1024; // 50MB in bytes
        let totalSize = 0;
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            
            // 檢查文件類型
            if (!allowedTypes.includes(file.type)) {
                e.preventDefault();
                alert(`檔案「${file.name}」的格式不支援。請選擇支持的檔案格式：JPG, JPEG, PNG, PDF`);
                return;
            }
            
            // 檢查單個文件大小
            if (file.size > maxSize) {
                e.preventDefault();
                alert(`檔案「${file.name}」大小超過50MB限制！`);
                return;
            }
            
            totalSize += file.size;
        }
        
        // 檢查總文件大小 (限制為200MB)
        const maxTotalSize = 200 * 1024 * 1024; // 200MB in bytes
        if (totalSize > maxTotalSize) {
            e.preventDefault();
            alert('所有檔案的總大小不能超過200MB！');
            return;
        }
        
        // 顯示載入畫面
        showLoadingScreen();
    });
    
    // 檔案選擇變化處理
    fileInput.addEventListener('change', function(e) {
        const files = e.target.files;
        updateFileList(files);
    });
});

// 顯示載入畫面
function showLoadingScreen() {
    const loadingContainer = document.getElementById('loading-container');
    if (loadingContainer) {
        loadingContainer.classList.add('show');
        
        // 禁用頁面滾動
        document.body.style.overflow = 'hidden';
        
        // 添加鍵盤事件監聽，防止用戶意外關閉
        document.addEventListener('keydown', preventDefaultKeys);
    }
}

// 隱藏載入畫面
function hideLoadingScreen() {
    const loadingContainer = document.getElementById('loading-container');
    if (loadingContainer) {
        loadingContainer.classList.remove('show');
        
        // 恢復頁面滾動
        document.body.style.overflow = '';
        
        // 移除鍵盤事件監聽
        document.removeEventListener('keydown', preventDefaultKeys);
    }
}

// 防止某些按鍵操作
function preventDefaultKeys(e) {
    // 防止F5刷新、Ctrl+R等
    if (e.key === 'F5' || (e.ctrlKey && e.key === 'r')) {
        e.preventDefault();
        return false;
    }
}

// 更新檔案列表顯示
function updateFileList(files) {
    const fileListContainer = document.getElementById('file-list');
    
    if (!files || files.length === 0) {
        fileListContainer.innerHTML = '';
        return;
    }
    
    let html = '<div class="selected-files"><h6>已選擇的檔案：</h6><ul class="list-group list-group-flush">';
    let totalSize = 0;
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        totalSize += file.size;
        
        // 判斷檔案圖示
        let icon = '📄';
        if (file.type.includes('image')) {
            icon = '🖼️';
        } else if (file.type.includes('pdf')) {
            icon = '📑';
        }
        
        html += `
            <li class="list-group-item d-flex justify-content-between align-items-center py-2">
                <div>
                    <span>${icon}</span>
                    <span class="ms-2">${file.name}</span>
                </div>
                <span class="badge bg-secondary rounded-pill">${formatFileSize(file.size)}</span>
            </li>
        `;
    }
    
    html += '</ul>';
    html += `<div class="mt-2 text-muted small">總共 ${files.length} 個檔案，總大小：${formatFileSize(totalSize)}</div>`;
    html += '</div>';
    
    fileListContainer.innerHTML = html;
    
    console.log(`選擇了 ${files.length} 個檔案，總大小：${formatFileSize(totalSize)}`);
}

// 格式化檔案大小顯示
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 檢查瀏覽器支援
function checkBrowserSupport() {
    // 檢查FileReader API支援
    if (!window.FileReader) {
        console.warn('您的瀏覽器不支援FileReader API');
        return false;
    }
    
    // 檢查FormData API支援
    if (!window.FormData) {
        console.warn('您的瀏覽器不支援FormData API');
        return false;
    }
    
    return true;
}

// 頁面載入完成後檢查瀏覽器支援
document.addEventListener('DOMContentLoaded', function() {
    if (!checkBrowserSupport()) {
        alert('您的瀏覽器版本過舊，可能無法正常使用所有功能。建議升級到最新版本的Chrome、Firefox或Safari。');
    }
}); 