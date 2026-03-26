# 图片压缩 API 服务 Docker 镜像
# 构建：docker build -t image-compressor .
# 运行：docker run -p 8765:8765 image-compressor

FROM registry.cn-hangzhou.aliyuncs.com/acs-repo/python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libtiff-dev \
    libopenjp2-7-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY server.py .
COPY image_compressor.py .

# 创建非 root 用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8765

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8765/health')" || exit 1

# 启动命令
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8765", "--workers", "4"]
