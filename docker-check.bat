@echo off
chcp 65001 >nul
echo 🔍 檢查 Docker 環境...

REM 檢查 Docker 版本
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker 未安裝
    echo 📥 請從以下網址下載並安裝 Docker Desktop:
    echo    https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

echo ✅ Docker 已安裝
docker --version

REM 檢查 Docker Compose 版本
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose 未安裝
    echo 📥 請確保安裝了 Docker Desktop（包含 Docker Compose）
    pause
    exit /b 1
)

echo ✅ Docker Compose 已安裝
docker-compose --version

REM 檢查 Docker 是否正在運行
echo 🔄 檢查 Docker 服務狀態...
docker ps >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker 服務未運行
    echo.
    echo 🚀 請啟動 Docker Desktop:
    echo    1. 在 Windows 搜索欄中搜索 "Docker Desktop"
    echo    2. 點擊打開 Docker Desktop 應用程式
    echo    3. 等待 Docker 完全啟動（圖標變為綠色）
    echo    4. 重新運行此腳本驗證
    echo.
    echo 💡 小提示: Docker Desktop 可能需要 1-2 分鐘完全啟動
    echo.
    pause
    exit /b 1
)

echo ✅ Docker 服務正在運行
echo.
echo 🎉 Docker 環境檢查完成！
echo 📂 當前專案目錄檔案:

REM 列出重要檔案
if exist "Dockerfile" (
    echo    ✅ Dockerfile
) else (
    echo    ❌ Dockerfile 缺失
)

if exist "docker-compose.yml" (
    echo    ✅ docker-compose.yml
) else (
    echo    ❌ docker-compose.yml 缺失
)

if exist "requirements.txt" (
    echo    ✅ requirements.txt
) else (
    echo    ❌ requirements.txt 缺失
)

if exist ".env" (
    echo    ✅ .env 檔案已存在
) else (
    echo    ⚠️  .env 檔案不存在，將使用範例建立
)

echo.
echo 🚀 現在可以執行: .\docker-start.bat
echo.
pause 