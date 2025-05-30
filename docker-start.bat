@echo off
chcp 65001 >nul
echo 🐳 啟動報紙工作廣告提取系統...

REM 檢查是否存在 .env 檔案
if not exist ".env" (
    echo ⚠️  警告: 未找到 .env 檔案
    echo 📝 創建範例 .env 檔案...
    (
        echo # Gemini API 密鑰
        echo GEMINI_API_KEY=your_gemini_api_key_here
        echo.
        echo # Flask 配置
        echo FLASK_ENV=production
        echo FLASK_DEBUG=False
        echo.
        echo # 應用程式配置
        echo MAX_CONTENT_LENGTH=16777216
        echo UPLOAD_FOLDER=uploads
        echo RESULTS_FOLDER=results
    ) > .env
    echo ✅ 已創建 .env 檔案，請編輯並添加您的 Gemini API 密鑰
)

REM 創建資料目錄
echo 📁 創建資料目錄...
if not exist "data" mkdir data
if not exist "data\uploads" mkdir data\uploads
if not exist "data\results" mkdir data\results

REM 檢查是否需要建構映像
set BUILD_REQUIRED=0
if "%1"=="build" set BUILD_REQUIRED=1

REM 檢查映像是否存在
docker images newspaper-job-extractor >nul 2>&1
if errorlevel 1 set BUILD_REQUIRED=1

if %BUILD_REQUIRED%==1 (
    echo 🔨 建構 Docker 映像...
    docker-compose build --no-cache
    if errorlevel 1 (
        echo ❌ 建構失敗
        pause
        exit /b 1
    )
)

REM 啟動服務
echo 🚀 啟動服務...
docker-compose up -d
if errorlevel 1 (
    echo ❌ 啟動失敗
    pause
    exit /b 1
)

REM 顯示狀態
echo 📊 檢查服務狀態...
timeout /t 5 /nobreak >nul
docker-compose ps

REM 顯示日誌
echo.
echo 📄 最近的應用程式日誌:
docker-compose logs --tail=20 newspaper-extractor

echo.
echo ✅ 啟動完成！
echo 🌐 應用程式網址: http://localhost:5000
echo.
echo 常用指令:
echo   查看日誌: docker-compose logs -f
echo   停止服務: docker-compose down
echo   重啟服務: docker-compose restart
echo   查看狀態: docker-compose ps
echo.
pause 