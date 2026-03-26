#!/bin/bash
# 图片压缩 API 服务启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 默认配置
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8765}
WORKERS=${WORKERS:-4}
MAX_WORKERS=${MAX_WORKERS:-8}

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

# 检查依赖
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "⚠️  正在安装依赖..."
    pip3 install -r requirements.txt
fi

echo "╔══════════════════════════════════════════════════════════╗"
echo "║         Image Compressor API - 启动配置                  ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  主机：$HOST"
echo "║  端口：$PORT"
echo "║  Uvicorn 工作进程：$WORKERS"
echo "║  压缩线程池：$MAX_WORKERS"
echo "╚══════════════════════════════════════════════════════════╝"

# 启动服务
export HOST PORT WORKERS MAX_WORKERS
exec uvicorn server:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --loop uvloop \
    --http httptools \
    --log-level info
