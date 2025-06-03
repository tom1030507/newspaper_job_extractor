@echo off
chcp 65001 >nul
echo 🧪 Docker 自動化測試開始...
echo.

REM 檢查 Docker 環境
echo 📋 步驟 1: 檢查 Docker 環境
call .\docker-check.bat
if errorlevel 1 (
    echo ❌ Docker 環境檢查失敗
    exit /b 1
)

echo.
echo 📋 步驟 2: 清理舊容器（如果存在）
docker-compose down >nul 2>&1

echo.
echo 📋 步驟 3: 建構 Docker 映像
echo 🔨 正在建構映像，這可能需要幾分鐘...
docker-compose build
if errorlevel 1 (
    echo ❌ 映像建構失敗
    exit /b 1
)
echo ✅ 映像建構成功

echo.
echo 📋 步驟 4: 啟動服務
docker-compose up -d
if errorlevel 1 (
    echo ❌ 服務啟動失敗
    exit /b 1
)
echo ✅ 服務啟動成功

echo.
echo 📋 步驟 5: 等待服務就緒
echo ⏳ 等待 30 秒讓服務完全啟動...
timeout /t 30 /nobreak >nul

echo.
echo 📋 步驟 6: 檢查服務狀態
docker-compose ps
echo.

echo 📋 步驟 7: 健康檢查
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8080/health' -TimeoutSec 10; if ($response.StatusCode -eq 200) { Write-Host '✅ 健康檢查通過' } else { Write-Host '❌ 健康檢查失敗' } } catch { Write-Host '❌ 無法連接到應用程式' }"

echo.
echo 📋 步驟 8: API 狀態檢查
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8080/api/status' -TimeoutSec 10; if ($response.StatusCode -eq 200) { Write-Host '✅ API 狀態正常' } else { Write-Host '❌ API 狀態異常' } } catch { Write-Host '❌ 無法連接到 API' }"

echo.
echo 📋 步驟 9: 檢查日誌
echo 📄 最近的應用程式日誌:
docker-compose logs --tail=10 newspaper-extractor

echo.
echo 📋 步驟 10: 檢查資料目錄
if exist "data" (
    echo ✅ 資料目錄已創建
    dir data
) else (
    echo ⚠️ 資料目錄不存在
)

echo.
echo 📋 步驟 11: 資源使用檢查
echo 💻 容器資源使用情況:
timeout /t 3 /nobreak >nul
powershell -Command "docker stats newspaper-job-extractor --no-stream --format 'CPU: {{.CPUPerc}} | 記憶體: {{.MemUsage}} | 網路: {{.NetIO}}'"

echo.
echo 🎉 測試完成！
echo.
echo 📊 測試結果摘要:
echo ===============================
echo 🌐 應用程式網址: http://localhost:8080
echo 📁 資料目錄: .\data\
echo 🔍 健康檢查: http://localhost:8080/health
echo 📊 API 狀態: http://localhost:8080/api/status
echo.
echo 🛠️ 常用指令:
echo   查看日誌: docker-compose logs -f
echo   停止服務: docker-compose down
echo   重啟服務: docker-compose restart
echo.

REM 詢問是否要打開瀏覽器
set /p choice="是否要打開瀏覽器測試應用程式？(y/n): "
if /i "%choice%"=="y" (
    start http://localhost:8080
    echo 🌐 瀏覽器已打開，請手動測試應用程式功能
)

echo.
echo 💡 測試提示:
echo   1. 在瀏覽器中設置 Gemini API 密鑰
echo   2. 上傳測試圖片或 PDF 檔案
echo   3. 檢查處理結果是否正確
echo   4. 測試下載功能
echo.
pause 