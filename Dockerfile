# 使用官方 Python 3.11 作為基礎映像，使用最新的安全更新版本
FROM python:3.11.10-slim

# 設置工作目錄
WORKDIR /app

# 添加非root用戶以提高安全性
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 安裝系統依賴和安全更新
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgcc-s1 \
    && apt-get upgrade -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 複製 requirements.txt
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY . .

# 創建必要的目錄並設置權限
RUN mkdir -p uploads results static templates \
    && chown -R appuser:appuser /app

# 切換到非root用戶
USER appuser

# 設置環境變數
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8080

# 設置卷掛載點（用於持久化存儲）
VOLUME ["/app/uploads", "/app/results"]

# 啟動命令
CMD ["python", "app.py"] 