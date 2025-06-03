# Docker 部署指南

## 快速開始

### 1. 檢查環境
```bash
# Windows
.\docker-check.bat

# Linux/macOS
docker --version && docker-compose --version
```

### 2. 啟動應用程式
```bash
# Windows
.\docker-start.bat

# Linux/macOS
chmod +x docker-start.sh && ./docker-start.sh

# 手動啟動
docker-compose up -d
```

### 3. 訪問應用程式
- 主頁面：http://localhost:8080
- 健康檢查：http://localhost:8080/health

## 基本指令

```bash
# 查看狀態
docker-compose ps

# 查看日誌
docker-compose logs -f

# 停止服務
docker-compose down

# 重啟服務
docker-compose restart
```

## 環境設定

創建 `.env` 檔案：
```bash
GEMINI_API_KEY=your_api_key_here
FLASK_ENV=production
```

## 資料持久化

資料存儲在：
- `./data/uploads/` - 上傳檔案
- `./data/results/` - 處理結果

## 疑難排解

### 端口衝突
修改 `docker-compose.yml` 中的端口：
```yaml
ports:
  - "8081:8080"  # 改為其他端口
```

### 清理資源
```bash
docker system prune -a
```

### 權限問題
```bash
# Windows
icacls data /grant Everyone:F /T

# Linux/macOS
sudo chown -R $USER:$USER data/
```

## 生產部署

使用生產配置：
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 備份資料

```bash
# 備份
tar -czf backup-$(date +%Y%m%d).tar.gz data/

# 恢復
tar -xzf backup-YYYYMMDD.tar.gz
``` 