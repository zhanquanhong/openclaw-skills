#!/usr/bin/env bash
# wbs-skill v3.2 — 一键安装脚本
# Mac/Linux
#
# 使用方式：
#   chmod +x install.sh && ./install.sh
#
# 安装内容：
#   1. 检查 Python 3.8+ 环境
#   2. 创建虚拟环境 .venv
#   3. 安装所有依赖
#   4. 创建 input/ output/ 目录
#   5. 设置执行权限

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  wbs-skill v3.2 — 安装向导               ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

# ========== 步骤 1：检查 Python ==========
echo -n "📦 步骤 1/5：检查 Python 环境... "

if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1)
    echo -e "${GREEN}✅ $PY_VERSION${NC}"
else
    echo -e "${RED}❌ 未找到 Python3${NC}"
    echo ""
    echo "请先安装 Python 3.8+："
    echo "  Mac:    brew install python3"
    echo "  Ubuntu: sudo apt install python3 python3-venv"
    echo "  CentOS: sudo yum install python3 python3-pip"
    echo "  或下载：https://www.python.org/downloads/"
    exit 1
fi

# 检查 Python 版本 >= 3.8
PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]); then
    echo -e "${RED}❌ Python 版本过低：$PY_VERSION（需要 3.8+）${NC}"
    exit 1
fi

# ========== 步骤 2：创建虚拟环境 ==========
echo -n "📦 步骤 2/5：创建虚拟环境... "

if [ -d ".venv" ]; then
    echo -e "${YELLOW}⏭️ 已存在，跳过${NC}"
else
    python3 -m venv .venv
    echo -e "${GREEN}✅ 完成${NC}"
fi

# ========== 步骤 3：安装依赖 ==========
echo -n "📦 步骤 3/5：安装依赖（约 30 秒）... "

if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ requirements.txt 不存在${NC}"
    exit 1
fi

.venv/bin/pip install --upgrade pip -q 2>/dev/null
.venv/bin/pip install -r requirements.txt -q 2>&1
INSTALL_EXIT=$?

if [ $INSTALL_EXIT -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ 依赖安装失败${NC}"
    echo ""
    echo "尝试手动安装："
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

echo -e "${GREEN}✅ 完成${NC}"

# ========== 步骤 4：创建目录 ==========
echo -n "📦 步骤 4/5：创建 input/ output/ 目录... "

mkdir -p input output
echo -e "${GREEN}✅ 完成${NC}"

# ========== 步骤 5：设置权限 ==========
echo -n "📦 步骤 5/5：设置执行权限... "

chmod +x wbs.sh 2>/dev/null || true
chmod +x install.sh 2>/dev/null || true
echo -e "${GREEN}✅ 完成${NC}"

# ========== 完成 ==========
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ 安装完成！                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo "使用方法："
echo "  1. 把技术方案文档放到 input/ 目录"
echo "  2. 执行：./wbs.sh input/技术方案.pdf"
echo ""
echo "或者直接使用绝对路径："
echo "  ./wbs.sh ~/Desktop/技术方案.pdf"
echo ""
echo "支持自然语言："
echo "  ./wbs.sh 技术方案.pdf \"按周分解，重点标出接口任务\""
echo ""
