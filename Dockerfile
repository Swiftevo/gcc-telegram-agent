# Dockerfile — GCC Telegram Agent
# 使用 slim 版本減少 image 大小

FROM python:3.12-slim

# 設定工作目錄
WORKDIR /app

# 先複製 requirements，利用 Docker layer 快取
# （只有 requirements.txt 變動才重新安裝依賴）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製全部程式碼
COPY . .

# 建立資料目錄（Fly.io 持久化磁碟掛載點）
RUN mkdir -p /data

# 設定環境變數預設值（實際值由 Fly.io secrets 注入）
ENV DB_PATH=/data/gcc_agent.db \
    VALUES_PATH=/app/values.yaml \
    PORT=8080 \
    PYTHONUNBUFFERED=1

# 啟動 Bot
CMD ["python", "main.py"]
