# QuantSeed Dockerfile - 后端 API 服务
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY src/ ./src/
COPY data/ ./data/

# 创建必要目录
RUN mkdir -p /app/logs /app/output

# 设置 Python 路径
ENV PYTHONPATH=/app/src:$PYTHONPATH

# 暴露 API 端口
EXPOSE 8000

# 启动 FastAPI 服务
CMD ["uvicorn", "src.api_server:app", "--host", "0.0.0.0", "--port", "8000"]
