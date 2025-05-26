// 文件上傳處理
document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('files');
    const fileList = document.getElementById('file-list');
    const submitBtn = document.getElementById('submit-btn');
    const uploadArea = document.getElementById('upload-area');
    const processingOptions = document.getElementById('processing-options');
    
    let selectedFiles = [];
    let isDragging = false;

    // 文件類型圖標映射
    const fileIcons = {
        'pdf': 'bi-file-earmark-pdf-fill',
        'jpg': 'bi-file-earmark-image-fill',
        'jpeg': 'bi-file-earmark-image-fill',
        'png': 'bi-file-earmark-image-fill'
    };

    // 格式化文件大小
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // 獲取文件圖標
    function getFileIcon(filename) {
        const extension = filename.split('.').pop().toLowerCase();
        return fileIcons[extension] || 'bi-file-earmark';
    }

    // 顯示文件列表
    function displayFiles() {
        if (selectedFiles.length === 0) {
            fileList.innerHTML = '';
            submitBtn.disabled = true;
            processingOptions.classList.add('d-none');
            return;
        }

        processingOptions.classList.remove('d-none');
        submitBtn.disabled = false;

        const html = selectedFiles.map((file, index) => `
            <div class="file-item" data-index="${index}">
                <div class="file-info">
                    <div class="file-icon">
                        <i class="${getFileIcon(file.name)}"></i>
                    </div>
                    <div class="file-details">
                        <h6>${file.name}</h6>
                        <div class="file-size">${formatFileSize(file.size)}</div>
                    </div>
                </div>
                <div class="file-actions">
                    <button type="button" class="btn btn-outline-danger btn-sm" onclick="removeFile(${index})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');

        fileList.innerHTML = html;

        // 更新文件統計
        const totalSize = selectedFiles.reduce((sum, file) => sum + file.size, 0);
        const statsHtml = `
            <div class="file-stats mt-3 p-3 bg-light rounded">
                <div class="row text-center">
                    <div class="col">
                        <strong>${selectedFiles.length}</strong>
                        <div class="text-muted small">文件數量</div>
                    </div>
                    <div class="col">
                        <strong>${formatFileSize(totalSize)}</strong>
                        <div class="text-muted small">總大小</div>
                    </div>
                    <div class="col">
                        <strong class="text-success">
                            <i class="bi bi-check-circle"></i>
                        </strong>
                        <div class="text-muted small">已準備</div>
                    </div>
                </div>
            </div>
        `;
        fileList.insertAdjacentHTML('beforeend', statsHtml);
    }

    // 移除文件
    window.removeFile = function(index) {
        selectedFiles.splice(index, 1);
        displayFiles();
        
        // 如果沒有文件了，重置文件輸入
        if (selectedFiles.length === 0) {
            fileInput.value = '';
        }
        
        // 添加移除動畫
        const fileItems = document.querySelectorAll('.file-item');
        if (fileItems[index]) {
            fileItems[index].style.transform = 'translateX(-100%)';
            fileItems[index].style.opacity = '0';
        }
    };

    // 驗證文件
    function validateFiles(files) {
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf'];
        const maxSize = 16 * 1024 * 1024; // 16MB
        const maxFiles = 10;
        
        const errors = [];
        
        if (files.length > maxFiles) {
            errors.push(`最多只能選擇 ${maxFiles} 個文件`);
            return { valid: false, errors };
        }
        
        for (let file of files) {
            if (!allowedTypes.includes(file.type)) {
                errors.push(`不支持的文件格式: ${file.name}`);
            }
            if (file.size > maxSize) {
                errors.push(`文件 ${file.name} 超過大小限制 (${formatFileSize(maxSize)})`);
            }
        }
        
        return { valid: errors.length === 0, errors };
    }

    // 處理文件選擇
    function handleFiles(files) {
        const validation = validateFiles(files);
        
        if (!validation.valid) {
            showNotification(validation.errors.join('<br>'), 'danger');
            return;
        }
        
        selectedFiles = Array.from(files);
        displayFiles();
        
        // 添加成功動畫
        uploadArea.style.borderColor = '#28a745';
        uploadArea.style.background = 'rgba(40, 167, 69, 0.1)';
        setTimeout(() => {
            uploadArea.style.borderColor = '#dee2e6';
            uploadArea.style.background = 'rgba(248, 249, 250, 0.8)';
        }, 1000);
        
        showNotification(`成功選擇 ${files.length} 個文件`, 'success');
    }

    // 顯示通知
    function showNotification(message, type = 'info') {
        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show animate__animated animate__fadeInDown" role="alert">
                <i class="bi bi-${type === 'success' ? 'check-circle-fill' : type === 'danger' ? 'exclamation-triangle-fill' : 'info-circle-fill'} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        // 插入到頁面頂部
        const container = document.querySelector('.container');
        const firstChild = container.firstElementChild;
        firstChild.insertAdjacentHTML('afterend', alertHtml);
        
        // 3秒後自動消失
        setTimeout(() => {
            const alert = container.querySelector('.alert');
            if (alert) {
                alert.classList.add('animate__fadeOutUp');
                setTimeout(() => alert.remove(), 500);
            }
        }, 3000);
    }

    // 文件輸入改變事件
    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            handleFiles(e.target.files);
        }
    });

    // 拖拽事件處理
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // 拖拽進入和移動
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, highlight, false);
    });

    // 拖拽離開
    uploadArea.addEventListener('dragleave', unhighlight, false);

    function highlight() {
        if (!isDragging) {
            isDragging = true;
            uploadArea.classList.add('dragover');
        }
    }

    function unhighlight() {
        isDragging = false;
        setTimeout(() => {
            if (!isDragging) {
                uploadArea.classList.remove('dragover');
            }
        }, 100);
    }

    // 處理文件拖放
    uploadArea.addEventListener('drop', function(e) {
        unhighlight();
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFiles(files);
        }
    });

    // 點擊上傳區域選擇文件
    uploadArea.addEventListener('click', function(e) {
        if (e.target.tagName !== 'BUTTON') {
            fileInput.click();
        }
    });

    // 表單提交處理
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (selectedFiles.length === 0) {
            showNotification('請先選擇文件', 'warning');
            return;
        }
        
        // 檢查API密鑰
        const apiKeyInput = document.querySelector('input[name="api_key"]');
        if (!apiKeyInput || !apiKeyInput.value.trim()) {
            showNotification('請先設置 Gemini API 密鑰', 'warning');
            return;
        }
        
        startProcessing();
    });

    // 開始處理
    function startProcessing() {
        // 顯示處理模態框
        const processingModal = new bootstrap.Modal(document.getElementById('processingModal'));
        processingModal.show();
        
        // 模擬進度更新
        const progressBar = document.getElementById('progress-bar');
        const steps = ['step-upload', 'step-process', 'step-analyze', 'step-complete'];
        let currentStep = 0;
        let progress = 0;
        
        // 更新步驟狀態
        function updateStep(stepIndex, status = 'active') {
            steps.forEach((step, index) => {
                const element = document.getElementById(step);
                element.classList.remove('active', 'completed');
                
                if (index < stepIndex) {
                    element.classList.add('completed');
                } else if (index === stepIndex) {
                    element.classList.add(status);
                }
            });
        }
        
        // 進度模擬
        const progressInterval = setInterval(() => {
            if (currentStep < steps.length - 1) {
                progress += Math.random() * 15 + 5;
                
                if (progress >= (currentStep + 1) * 25) {
                    progress = (currentStep + 1) * 25;
                    updateStep(currentStep, 'completed');
                    currentStep++;
                    updateStep(currentStep, 'active');
                }
                
                progressBar.style.width = Math.min(progress, 95) + '%';
            }
        }, 500);
        
        // 創建FormData並提交
        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files', file);
        });
        
        // 實際提交表單
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            clearInterval(progressInterval);
            
            if (response.ok) {
                // 完成最後步驟
                progressBar.style.width = '100%';
                updateStep(steps.length - 1, 'completed');
                
                setTimeout(() => {
                    window.location.href = response.url;
                }, 1000);
            } else {
                throw new Error('處理失敗');
            }
        })
        .catch(error => {
            clearInterval(progressInterval);
            processingModal.hide();
            showNotification('處理過程中發生錯誤，請重試', 'danger');
            console.error('Upload error:', error);
        });
    }

    // API密鑰表單處理
    const apiForm = document.querySelector('.api-form');
    if (apiForm) {
        apiForm.addEventListener('submit', function(e) {
            const apiKeyInput = this.querySelector('input[name="api_key"]');
            const submitBtn = this.querySelector('button[type="submit"]');
            
            if (apiKeyInput.value.trim()) {
                submitBtn.innerHTML = '<i class="bi bi-check-lg me-1"></i>保存中...';
                submitBtn.disabled = true;
                
                // 表單提交後會重新加載頁面，所以不需要恢復按鈕狀態
            }
        });
    }

    // 添加鍵盤快捷鍵
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + O 打開文件選擇器
        if ((e.ctrlKey || e.metaKey) && e.key === 'o') {
            e.preventDefault();
            fileInput.click();
        }
        
        // ESC 關閉模態框
        if (e.key === 'Escape') {
            const modal = bootstrap.Modal.getInstance(document.getElementById('processingModal'));
            if (modal) {
                modal.hide();
            }
        }
    });

    // 添加視覺反饋效果
    function addVisualEffects() {
        // 卡片懸停效果
        const cards = document.querySelectorAll('.card');
        cards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-5px) scale(1.02)';
            });
            
            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0) scale(1)';
            });
        });

        // 按鈕點擊波紋效果
        const buttons = document.querySelectorAll('.btn');
        buttons.forEach(button => {
            button.addEventListener('click', function(e) {
                const ripple = document.createElement('span');
                const rect = this.getBoundingClientRect();
                const size = Math.max(rect.width, rect.height);
                const x = e.clientX - rect.left - size / 2;
                const y = e.clientY - rect.top - size / 2;
                
                ripple.style.cssText = `
                    position: absolute;
                    border-radius: 50%;
                    transform: scale(0);
                    animation: ripple 0.6s linear;
                    background-color: rgba(255, 255, 255, 0.6);
                    width: ${size}px;
                    height: ${size}px;
                    left: ${x}px;
                    top: ${y}px;
                    pointer-events: none;
                `;
                
                this.style.position = 'relative';
                this.style.overflow = 'hidden';
                this.appendChild(ripple);
                
                setTimeout(() => {
                    ripple.remove();
                }, 600);
            });
        });
    }

    // 添加CSS動畫
    const style = document.createElement('style');
    style.textContent = `
        @keyframes ripple {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
        
        .file-item {
            transform: translateX(0);
            transition: all 0.3s ease;
        }
        
        .processing-animation {
            animation: processing-pulse 2s infinite ease-in-out;
        }
        
        @keyframes processing-pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
    `;
    document.head.appendChild(style);

    // 初始化視覺效果
    addVisualEffects();

    // 頁面加載動畫
    function initPageAnimations() {
        const animatedElements = document.querySelectorAll('.animate__animated');
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.animationDelay = '0s';
                    entry.target.style.animationDuration = '0.8s';
                }
            });
        });

        animatedElements.forEach(el => observer.observe(el));
    }

    initPageAnimations();

    // 工具提示初始化
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    console.log('📄 報紙工作廣告提取工具已初始化');
    console.log('💡 提示：您可以使用 Ctrl+O (或 Cmd+O) 快速打開文件選擇器');
}); 