#!/bin/bash

# 報紙工作廣告提取系統 Docker 啟動腳本

echo "🐳 啟動報紙工作廣告提取系統..."

# 檢查是否存在 .env 檔案
if [ ! -f ".env" ]; then
    echo "⚠️  警告: 未找到 .env 檔案"
    echo "📝 創建範例 .env 檔案..."
    cat > .env << EOF
# Gemini API 密鑰
GEMINI_API_KEY=your_gemini_api_key_here

# Flask 配置
FLASK_ENV=production
FLASK_DEBUG=False

# 應用程式配置
MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=uploads
RESULTS_FOLDER=results
EOF
    echo "✅ 已創建 .env 檔案，請編輯並添加您的 Gemini API 密鑰"
fi

# 創建資料目錄
echo "📁 創建資料目錄..."
mkdir -p data/uploads data/results

# 檢查是否需要建構映像
if [ "$1" = "build" ] || [ ! "$(docker images -q newspaper-job-extractor 2> /dev/null)" ]; then
    echo "🔨 建構 Docker 映像..."
    docker-compose build --no-cache
fi

# 啟動服務
echo "🚀 啟動服務..."
docker-compose up -d

# 顯示狀態
echo "📊 檢查服務狀態..."
sleep 5
docker-compose ps

# 顯示日誌
echo ""
echo "📄 最近的應用程式日誌:"
docker-compose logs --tail=20 newspaper-extractor

echo ""
echo "✅ 啟動完成！"
echo "🌐 應用程式網址: http://localhost:5000"
echo ""
echo "常用指令:"
echo "  查看日誌: docker-compose logs -f"
echo "  停止服務: docker-compose down"
echo "  重啟服務: docker-compose restart"
echo "  查看狀態: docker-compose ps" 