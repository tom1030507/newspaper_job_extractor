# ⚙️ 配置與部署指南

## 🐳 Docker 配置

### 開發環境

```yaml
# docker-compose.yml
version: '3.8'
services:
  newspaper-extractor:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./uploads:/app/uploads
      - ./results:/app/results
    environment:
      - FLASK_ENV=development
      - FLASK_DEBUG=1
```

### 生產環境

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  newspaper-extractor:
    image: newspaper-extractor:latest
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - FLASK_ENV=production
      - FLASK_DEBUG=0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
        reservations:
          memory: 2G
          cpus: '1.0'
```

## 🛠️ 系統管理

### 監控與狀態

**健康檢查端點**:
- `/health`: 基本系統狀態
- `/admin/storage`: 存儲使用情況
- `/admin/cleanup/settings`: 清理設定狀態

**Docker 管理指令**:
```bash
# 查看狀態
docker-compose ps

# 查看日誌
docker-compose logs -f newspaper-extractor

# 重啟服務
docker-compose restart

# 停止服務
docker-compose down

# 清理資源
docker system prune -a
```

### 🧹 自動清理

系統內建智能清理機制：

- ⏰ **定時清理**: 每 4 小時自動執行
- 📁 **檔案數量限制**: 最多保留 10 個處理結果
- 🕐 **時間基礎清理**: 超過 4 小時的檔案自動清理
- 🔧 **手動清理**: 管理端點支援手動觸發

## 🔧 環境變數配置

### 完整配置清單

```bash
# ===================
# API 配置
# ===================
GEMINI_API_KEY=your_api_key_here
GOOGLE_APPS_SCRIPT_URL=your_script_url_here

# ===================
# 伺服器配置
# ===================
FLASK_HOST=0.0.0.0
FLASK_PORT=8080
FLASK_ENV=production
FLASK_DEBUG=0

# ===================
# 檔案處理配置
# ===================
MAX_CONTENT_LENGTH=16777216        # 16MB
MAX_FILES_PER_UPLOAD=10
UPLOAD_FOLDER=uploads
RESULTS_FOLDER=results

# ===================
# 清理服務配置
# ===================
CLEANUP_MAX_AGE_HOURS=4
CLEANUP_INTERVAL_HOURS=4
CLEANUP_MAX_FILE_COUNT=10
CLEANUP_ENABLED=true

# ===================
# AI 服務配置
# ===================
AI_MAX_RETRIES=3
AI_RETRY_DELAY=1
AI_TIMEOUT=30
AI_PARALLEL_WORKERS=3

# ===================
# 記憶體管理配置
# ===================
MEMORY_CLEANUP_THRESHOLD=80        # 記憶體使用率閾值 (%)
MEMORY_CLEANUP_ENABLED=true
GC_COLLECTION_ENABLED=true
```

### 配置說明

| 變數名稱 | 預設值 | 說明 |
|----------|--------|------|
| `GEMINI_API_KEY` | - | Google Gemini API 密鑰 |
| `MAX_CONTENT_LENGTH` | 16777216 | 最大檔案大小 (bytes) |
| `MAX_FILES_PER_UPLOAD` | 10 | 單次上傳最大檔案數 |
| `CLEANUP_MAX_AGE_HOURS` | 4 | 檔案保留時間 (小時) |
| `AI_PARALLEL_WORKERS` | 3 | AI 並行處理線程數 |

## 🚀 部署流程

### 1. 準備環境

```bash
# 檢查 Docker 版本
docker --version
docker-compose --version

# 檢查系統資源
free -h
df -h
```

### 2. 配置檔案

```bash
# 複製環境配置
cp .env.example .env

# 編輯配置檔案
nano .env
```

### 3. 建構與部署

```bash
# 開發環境
docker-compose up -d

# 生產環境
docker-compose -f docker-compose.prod.yml up -d
```

### 4. 驗證部署

```bash
# 檢查服務狀態
curl http://localhost:8080/health

# 檢查日誌
docker-compose logs -f
```

## 📊 性能調優

### 記憶體優化

```bash
# Docker 記憶體限制
docker run -m 4g newspaper-extractor

# 系統記憶體監控
docker stats newspaper-extractor
```

### CPU 優化

```bash
# CPU 限制
docker run --cpus="2.0" newspaper-extractor

# 並行處理調整
export AI_PARALLEL_WORKERS=4
```

## 🔒 安全配置

### 容器安全

```dockerfile
# Dockerfile 安全設定
FROM python:3.11-slim

# 創建非 root 用戶
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 設定檔案權限
COPY --chown=appuser:appuser . /app
USER appuser

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1
```

### 網絡安全

```yaml
# docker-compose.yml 網絡配置
version: '3.8'
services:
  newspaper-extractor:
    networks:
      - app-network
    ports:
      - "127.0.0.1:8080:8080"  # 僅本地訪問

networks:
  app-network:
    driver: bridge
    internal: true
```

## 🔍 故障排除

### 常見問題

**1. 容器啟動失敗**
```bash
# 檢查日誌
docker-compose logs newspaper-extractor

# 檢查端口占用
netstat -tulpn | grep 8080
```

**2. 記憶體不足**
```bash
# 增加 Docker 記憶體限制
docker-compose -f docker-compose.prod.yml up -d

# 手動清理記憶體
curl -X POST http://localhost:8080/admin/cleanup
```

**3. API 連接問題**
```bash
# 測試 API 連接
curl -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key=YOUR_API_KEY"
```

### 日誌分析

```bash
# 即時日誌
docker-compose logs -f --tail=100

# 錯誤日誌過濾
docker-compose logs | grep ERROR

# 性能日誌
docker-compose logs | grep "Processing time"
```

## 📈 監控與維護

### 系統監控

```bash
# 資源使用監控
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# 磁碟使用監控
du -sh uploads/ results/
```

### 定期維護

```bash
# 每日清理腳本
#!/bin/bash
# cleanup.sh

# 清理舊檔案
find uploads/ -type f -mtime +1 -delete
find results/ -type f -mtime +1 -delete

# 清理 Docker 資源
docker system prune -f

# 重啟服務 (如需要)
# docker-compose restart
```

### 備份策略

```bash
# 配置備份
tar -czf config-backup-$(date +%Y%m%d).tar.gz .env docker-compose*.yml

# 資料備份
tar -czf data-backup-$(date +%Y%m%d).tar.gz uploads/ results/
``` 