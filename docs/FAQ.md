# ❓ 常見問題與故障排除

## 🔧 安裝與配置問題

### Q: Docker 容器啟動失敗？

**A: 請檢查以下項目：**

1. **Docker 服務狀態**
   ```bash
   # Windows
   Get-Service docker
   
   # Linux/macOS
   sudo systemctl status docker
   ```

2. **端口占用檢查**
   ```bash
   # Windows
   netstat -ano | findstr :8080
   
   # Linux/macOS
   netstat -tulpn | grep 8080
   ```

3. **詳細錯誤日誌**
   ```bash
   docker-compose logs newspaper-extractor
   ```

4. **常見解決方案**
   - 重啟 Docker 服務
   - 更改端口配置
   - 檢查防火牆設定

### Q: API 密鑰設置無效？

**A: 確認以下設定：**

1. **API 密鑰格式**
   - 確保密鑰完整無誤
   - 檢查是否有多餘的空格或換行

2. **API 權限**
   ```bash
   # 測試 API 連接
   curl -X POST \
     "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key=YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
   ```

3. **網絡連接**
   - 確保可以訪問 Google API
   - 檢查代理設定

### Q: 環境變數不生效？

**A: 檢查配置方式：**

1. **Docker Compose 配置**
   ```yaml
   environment:
     - GEMINI_API_KEY=your_key_here
   ```

2. **.env 檔案**
   ```bash
   # 確保檔案位於專案根目錄
   GEMINI_API_KEY=your_key_here
   ```

3. **重啟容器**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

---

## 🖼️ 圖像處理問題

### Q: 圖片無法正確識別？

**A: 優化建議：**

1. **圖片品質要求**
   - 解析度至少 300 DPI
   - 清晰度良好，無模糊
   - 對比度適中

2. **處理選項**
   - 開啟「自動校正方向」
   - 嘗試不同的圖片格式
   - 檢查圖片是否完整

3. **支援格式確認**
   ```python
   支援格式: JPG, JPEG, PNG, PDF
   最大檔案大小: 16MB
   ```

### Q: PDF 處理失敗？

**A: 檢查以下項目：**

1. **PDF 類型**
   - 確保是掃描版 PDF
   - 檢查 PDF 是否損壞
   - 嘗試用其他軟體開啟

2. **檔案大小**
   ```bash
   # 檢查檔案大小
   ls -lh your_file.pdf
   ```

3. **頁數限制**
   - 建議單個 PDF 不超過 20 頁
   - 大檔案建議分割處理

### Q: 區塊檢測不準確？

**A: 調整策略：**

1. **圖片預處理**
   - 確保圖片方向正確
   - 檢查圖片邊界是否完整
   - 避免圖片過度壓縮

2. **手動調整**
   - 嘗試裁切圖片
   - 調整圖片對比度
   - 移除不必要的邊框

---

## ⚡ 性能優化問題

### Q: 處理速度很慢？

**A: 優化建議：**

1. **並行處理**
   ```bash
   # 調整並行線程數
   export AI_PARALLEL_WORKERS=4
   ```

2. **網絡優化**
   - 確保網絡連接穩定
   - 檢查 API 回應時間
   - 考慮使用 VPN

3. **系統資源**
   ```bash
   # 增加 Docker 記憶體
   docker run -m 4g newspaper-extractor
   ```

4. **分批處理**
   - 避免同時上傳過多檔案
   - 建議每次處理 3-5 個檔案

### Q: 記憶體使用過高？

**A: 記憶體管理：**

1. **監控記憶體使用**
   ```bash
   # 查看記憶體使用
   curl http://localhost:8080/admin/storage
   ```

2. **手動清理**
   ```bash
   # 手動清理記憶體
   curl -X POST http://localhost:8080/admin/cleanup
   ```

3. **配置優化**
   ```bash
   # 調整清理頻率
   CLEANUP_INTERVAL_HOURS=0.5
   CLEANUP_MAX_FILE_COUNT=2
   ```

### Q: Google Sheets 同步失敗？

**A: 檢查項目：**

1. **網絡連接**
   ```bash
   # 測試 Google API 連接
   curl -I https://sheets.googleapis.com
   ```

2. **Apps Script 配置**
   - 確認 Apps Script URL 正確
   - 檢查腳本權限設定
   - 驗證腳本是否部署

3. **API 限制**
   - 檢查是否超過 API 使用限制
   - 等待一段時間後重試

---

## 🐳 Docker 相關問題

### Q: 容器無法訪問？

**A: 網絡檢查：**

1. **端口映射**
   ```bash
   # 檢查端口映射
   docker port newspaper-extractor
   ```

2. **防火牆設定**
   ```bash
   # Windows 防火牆
   netsh advfirewall firewall add rule name="Docker Port 8080" dir=in action=allow protocol=TCP localport=8080
   ```

3. **容器狀態**
   ```bash
   # 檢查容器狀態
   docker-compose ps
   ```

### Q: 容器記憶體不足？

**A: 資源配置：**

1. **增加記憶體限制**
   ```yaml
   # docker-compose.yml
   services:
     newspaper-extractor:
       deploy:
         resources:
           limits:
             memory: 4G
   ```

2. **監控資源使用**
   ```bash
   docker stats newspaper-extractor
   ```

### Q: 檔案權限問題？

**A: 權限設定：**

1. **檢查檔案權限**
   ```bash
   ls -la uploads/ results/
   ```

2. **修正權限**
   ```bash
   # Linux/macOS
   sudo chown -R $USER:$USER uploads/ results/
   chmod -R 755 uploads/ results/
   ```

---

## 🔍 故障診斷工具

### 系統健康檢查

```bash
#!/bin/bash
# health-check.sh

echo "=== 系統健康檢查 ==="

# 1. Docker 狀態
echo "1. Docker 服務狀態:"
docker --version
docker-compose --version

# 2. 容器狀態
echo "2. 容器狀態:"
docker-compose ps

# 3. 端口檢查
echo "3. 端口檢查:"
netstat -tulpn | grep 8080

# 4. 記憶體使用
echo "4. 記憶體使用:"
free -h

# 5. 磁碟空間
echo "5. 磁碟空間:"
df -h

# 6. API 連接測試
echo "6. API 連接測試:"
curl -s http://localhost:8080/health
```

### 日誌分析腳本

```bash
#!/bin/bash
# log-analysis.sh

echo "=== 日誌分析 ==="

# 錯誤日誌
echo "1. 錯誤日誌:"
docker-compose logs | grep -i error | tail -10

# 警告日誌
echo "2. 警告日誌:"
docker-compose logs | grep -i warning | tail -10

# 性能日誌
echo "3. 性能日誌:"
docker-compose logs | grep "Processing time" | tail -5

# API 調用日誌
echo "4. API 調用:"
docker-compose logs | grep "API" | tail -5
```

---
