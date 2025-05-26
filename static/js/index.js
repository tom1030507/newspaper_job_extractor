// 文件上傳處理
document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const loadingContainer = document.getElementById('loading-container');
    const fileInput = document.getElementById('file');

    // 表單提交處理
    uploadForm.addEventListener('submit', function(e) {
        const file = fileInput.files[0];
        
        // 檢查是否選擇了文件
        if (!file) {
            e.preventDefault();
            alert('請選擇要上傳的檔案！');
            return;
        }
        
        // 檢查文件類型
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf'];
        if (!allowedTypes.includes(file.type)) {
            e.preventDefault();
            alert('請選擇支持的檔案格式：JPG, JPEG, PNG, PDF');
            return;
        }
        
        // 檢查文件大小 (限制為50MB)
        const maxSize = 50 * 1024 * 1024; // 50MB in bytes
        if (file.size > maxSize) {
            e.preventDefault();
            alert('檔案大小不能超過50MB！');
            return;
        }
        
        // 顯示載入畫面
        showLoadingScreen();
    });
    
    // 檔案選擇變化處理
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            console.log('選擇的檔案:', file.name, '大小:', formatFileSize(file.size), '類型:', file.type);
        }
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