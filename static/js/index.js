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
        // 創建或獲取通知容器
        let notificationContainer = document.getElementById('notification-container');
        if (!notificationContainer) {
            notificationContainer = document.createElement('div');
            notificationContainer.id = 'notification-container';
            notificationContainer.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                width: 350px;
                pointer-events: none;
            `;
            document.body.appendChild(notificationContainer);
        }
        
        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show animate__animated animate__fadeInRight notification-alert" role="alert" style="pointer-events: auto; margin-bottom: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                <i class="bi bi-${type === 'success' ? 'check-circle-fill' : type === 'danger' ? 'exclamation-triangle-fill' : 'info-circle-fill'} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        // 插入到通知容器頂部
        notificationContainer.insertAdjacentHTML('afterbegin', alertHtml);
        
        // 獲取剛插入的通知元素
        const newAlert = notificationContainer.querySelector('.alert');
        
        // 3秒後自動消失
        setTimeout(() => {
            if (newAlert && newAlert.parentNode) {
                                 newAlert.classList.remove('animate__fadeInRight');
                 newAlert.classList.add('animate__fadeOutRight');
                setTimeout(() => {
                    if (newAlert.parentNode) {
                        newAlert.remove();
                    }
                }, 500);
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

    // 初始化 SocketIO 連接
    const socket = io({
        transports: ['websocket', 'polling'],  // 明確指定傳輸方式
        upgrade: true,  // 允許協議升級
        rememberUpgrade: true,  // 記住升級後的協議
        timeout: 20000,  // 連接超時時間
        forceNew: false,  // 不強制新連接
        reconnection: false,  // 停用自動重連
    });
    let currentProcessId = null;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    
    // 添加連接狀態監聽
    socket.on('connect', function() {
        console.log('SocketIO 已連接，ID:', socket.id);
        reconnectAttempts = 0;  // 重置重連計數
        
        // 如果有正在進行的處理，重新加入房間
        if (currentProcessId) {
            socket.emit('join_process', { process_id: currentProcessId });
            // 請求當前進度
            socket.emit('get_progress', { process_id: currentProcessId });
        }
    });
    
    socket.on('disconnect', function(reason) {
        console.log('SocketIO 已斷開連接，原因:', reason);
        
        // 如果是伺服器斷開連接，嘗試重連
        if (reason === 'io server disconnect') {
            socket.connect();
        }
    });
    
    socket.on('connect_error', function(error) {
        console.error('SocketIO 連接錯誤:', error);
        reconnectAttempts++;
        
        if (reconnectAttempts >= maxReconnectAttempts) {
            console.warn('達到最大重連次數，停止重連');
            showNotification('連接伺服器失敗，請刷新頁面重試', 'warning');
        }
    });
    
    socket.on('reconnect', function(attemptNumber) {
        console.log('SocketIO 重連成功，嘗試次數:', attemptNumber);
        showNotification('已重新連接到伺服器', 'success');
    });
    
    // 開始處理
    async function startProcessing() {
        try {
            // 首先獲取 process_id
            const processResponse = await fetch('/create_process_id', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (!processResponse.ok) {
                throw new Error('無法獲取處理ID');
            }
            
            const processData = await processResponse.json();
            currentProcessId = processData.process_id;
            
            // 加入對應的 SocketIO 房間
            socket.emit('join_process', { process_id: currentProcessId });
            
            // 顯示處理模態框
            const processingModal = new bootstrap.Modal(document.getElementById('processingModal'));
            processingModal.show();
            
            const progressBar = document.getElementById('progress-bar');
            const steps = ['step-upload', 'step-process', 'step-analyze', 'step-complete'];
            
            // 重置進度條和步驟狀態
            progressBar.style.width = '0%';
            steps.forEach(step => {
                const element = document.getElementById(step);
                element.classList.remove('active', 'completed');
            });
            
            // 設置初始狀態
            document.getElementById('step-upload').classList.add('active');
            
            // 更新步驟狀態的函數
            function updateStep(stepName, status = 'active') {
                const stepMap = {
                    'upload': 0,
                    'process': 1, 
                    'analyze': 2,
                    'complete': 3,
                    'error': -1
                };
                
                const stepIndex = stepMap[stepName];
                if (stepIndex === -1) return; // 錯誤狀態不更新步驟
                
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
            
            // 清理之前的監聽器
            socket.off('progress_update');
            
            // 監聽進度更新 - 現在只接收屬於當前 process_id 的更新
            socket.on('progress_update', function(data) {
                // 檢查進度更新是否屬於當前的 process_id
                if (data.process_id !== currentProcessId) {
                    return; // 忽略不是自己的進度更新
                }
            // 更新進度條
            progressBar.style.width = Math.max(data.progress, 0) + '%';
            
            // 更新步驟狀態
            updateStep(data.step, 'active');
            
            // 更新描述文字
            const processingText = document.querySelector('.modal-body p');
            if (processingText && data.description) {
                // 檢查是否為 API 限制錯誤重試狀態
                const isRetryStatus = data.description.includes('API 請求頻率超限') || 
                                    data.description.includes('等待') && data.description.includes('秒後');
                const isRetryingStatus = data.description.includes('重新嘗試 API 請求');
                
                // 移除 text-muted 類別，讓文字更明顯
                processingText.classList.remove('text-muted');
                
                if (isRetryStatus) {
                    // API 限制錯誤重試狀態 - 使用警告色
                    processingText.classList.remove('text-primary', 'text-success');
                    processingText.classList.remove('text-warning');
                    processingText.classList.add('fw-bold');
                    processingText.style.color = '#ff9800';
                    processingText.innerHTML = `
                        <i class="bi bi-clock-history me-2"></i>${data.description}
                        <br><small class="text-muted">程式會自動重試，請耐心等待</small>
                    `;
                    
                    // 為進度條添加脈動效果
                    progressBar.classList.add('progress-bar-animated', 'progress-bar-striped');
                    progressBar.style.backgroundColor = '#ff9800'; // 較柔和的橙色
                } else if (isRetryingStatus) {
                    // 重試中狀態 - 使用資訊色
                    processingText.classList.remove('text-primary', 'text-warning');
                    processingText.classList.add('text-info', 'fw-bold');
                    processingText.style.color = ''; // 清除自定義顏色
                    processingText.innerHTML = `
                        <i class="bi bi-arrow-clockwise me-2"></i>${data.description}
                        <br><small class="text-muted">正在重新嘗試 API 請求</small>
                    `;
                    
                    progressBar.style.backgroundColor = '#0dcaf0'; // 資訊色
                } else {
                    // 正常狀態
                    processingText.classList.remove('text-warning', 'text-info');
                    processingText.classList.add('text-primary', 'fw-bold');
                    processingText.style.color = ''; // 清除自定義顏色
                    processingText.innerHTML = data.description + '<br><small class="text-muted">請耐心等待，處理時間取決於文件大小和複雜度</small>';
                    
                    // 恢復正常的進度條樣式
                    progressBar.classList.remove('progress-bar-animated', 'progress-bar-striped');
                    progressBar.style.backgroundColor = ''; // 恢復預設色
                }
            }
            
            console.log(`進度更新: ${data.step} - ${data.progress}% - ${data.description}`);
            
            // 如果處理完成，準備跳轉
            if (data.step === 'complete' && data.progress >= 100) {
                // 恢復正常的進度條樣式
                progressBar.classList.remove('progress-bar-animated', 'progress-bar-striped');
                progressBar.style.backgroundColor = '#198754'; // 成功色
                
                setTimeout(() => {
                    socket.off('progress_update');
                    // 跳轉將由表單回應處理
                }, 500);
            }
            });
            
            // 創建FormData並提交
            const formData = new FormData();
            selectedFiles.forEach(file => {
                formData.append('files', file);
            });
            
            // 添加處理選項和 process_id
            const autoRotate = document.getElementById('auto-rotate').checked;
            const parallelProcess = document.getElementById('parallel-process').checked;
            formData.append('auto_rotate', autoRotate);
            formData.append('parallel_process', parallelProcess);
            formData.append('process_id', currentProcessId);
            
            // 實際提交表單
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                // 確保進度條達到100%
                progressBar.style.width = '100%';
                updateStep('complete', 'completed');
                
                setTimeout(() => {
                    // 清理監聽器和離開房間
                    socket.off('progress_update');
                    socket.emit('leave_process', { process_id: currentProcessId });
                    window.location.href = response.url;
                }, 1000);
            } else {
                throw new Error('處理失敗');
            }
            
        } catch (error) {
            // 清理監聽器和離開房間
            socket.off('progress_update');
            socket.emit('leave_process', { process_id: currentProcessId });
            const processingModal = bootstrap.Modal.getInstance(document.getElementById('processingModal'));
            if (processingModal) {
                processingModal.hide();
            }
            showNotification('處理過程中發生錯誤，請重試', 'danger');
            console.error('Upload error:', error);
        }
    }

    // API密鑰表單處理
    const apiForm = document.querySelector('.api-form');
    if (apiForm) {
        apiForm.addEventListener('submit', function(e) {
            e.preventDefault(); // 阻止默認表單提交
            
            const apiKeyInput = this.querySelector('input[name="api_key"]');
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            
            if (apiKeyInput.value.trim()) {
                submitBtn.innerHTML = '<i class="bi bi-check-lg me-1"></i>保存中...';
                submitBtn.disabled = true;
                
                // 使用 fetch API 提交表單
                const formData = new FormData(this);
                
                fetch('/set_api_key', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json().then(data => ({ status: response.status, data })))
                .then(({ status, data }) => {
                    if (status === 200 && data.success) {
                        // 成功保存
                        submitBtn.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i>已保存';
                        submitBtn.classList.remove('btn-primary');
                        submitBtn.classList.add('btn-success');
                        
                        // 更新頁面上的 API 狀態顯示
                        const apiStatus = document.querySelector('.api-status');
                        if (apiStatus) {
                            const modelBadge = apiStatus.innerHTML.match(/<span class="badge bg-primary.*?<\/span>/)?.[0] || '';
                            apiStatus.innerHTML = '<span class="badge bg-success"><i class="bi bi-check-circle me-1"></i>API 密鑰已設置</span>' + 
                                                 (modelBadge ? ' ' + modelBadge : '');
                        }
                        
                        // 顯示成功通知
                        showNotification(data.message, 'success');
                        
                        // 2秒後恢復按鈕狀態
                        setTimeout(() => {
                            submitBtn.innerHTML = originalBtnText;
                            submitBtn.classList.remove('btn-success');
                            submitBtn.classList.add('btn-primary');
                            submitBtn.disabled = false;
                        }, 2000);
                    } else {
                        throw new Error(data.message || '保存失敗');
                    }
                })
                .catch(error => {
                    console.error('API key save error:', error);
                    showNotification('保存 API 密鑰時發生錯誤，請重試', 'danger');
                    
                    // 恢復按鈕狀態
                    submitBtn.innerHTML = originalBtnText;
                    submitBtn.disabled = false;
                });
            } else {
                showNotification('API密鑰不能為空！', 'warning');
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

    // 允許 Modal 背景滾動的功能
    function enableModalBackgroundScroll() {
        // 監聽所有 Modal 的顯示事件
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('show.bs.modal', function() {
                // 當 Modal 顯示時，移除 body 的 overflow: hidden
                setTimeout(() => {
                    document.body.style.overflow = 'auto';
                    document.body.style.paddingRight = '0px';
                }, 10);
            });
            
            modal.addEventListener('shown.bs.modal', function() {
                // Modal 完全顯示後，確保 body 可以滾動
                document.body.style.overflow = 'auto';
                document.body.style.paddingRight = '0px';
            });
            
            modal.addEventListener('hide.bs.modal', function() {
                // Modal 隱藏時，恢復正常滾動
                document.body.style.overflow = 'auto';
                document.body.style.paddingRight = '0px';
            });
            
            modal.addEventListener('hidden.bs.modal', function() {
                // Modal 完全隱藏後，確保 body 可以滾動
                document.body.style.overflow = 'auto';
                document.body.style.paddingRight = '0px';
            });
        });
    }

    // 啟用 Modal 背景滾動
    enableModalBackgroundScroll();

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