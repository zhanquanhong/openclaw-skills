#!/usr/bin/env bash
# wbs-skill v4.0 — 自然语言 WBS 生成器
# Mac/Linux 入口脚本
#
# 使用方式：
#   ./wbs.sh <文件路径>                    # 默认模式
#   ./wbs.sh <文件路径> "需求描述"         # 自然语言模式
#
# 示例：
#   ./wbs.sh input/技术方案.pdf
#   ./wbs.sh ~/Desktop/方案.pdf "按周分解"
#
# 支持格式：PDF、DOCX、Markdown (.md)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python3"

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ========== 环境检查 ==========
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}❌ 虚拟环境不存在，请先运行安装脚本：${NC}"
    echo -e "   ${YELLOW}./install.sh${NC}"
    exit 1
fi

if [ ! -f "$PYTHON" ]; then
    echo -e "${RED}❌ Python 虚拟环境损坏，请重新运行安装脚本${NC}"
    exit 1
fi

# ========== 参数解析 ==========
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}╔══════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  wbs-skill v4.0 — WBS 任务分解器     ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════╝${NC}"
    echo ""
    echo "用法："
    echo "  $0 <文件路径>                    # 默认模式"
    echo "  $0 <文件路径> \"需求描述\"         # 自然语言模式"
    echo "  $0 <文件路径> \"需求描述\" --no-learn  # 禁用学习"
    echo ""
    echo "示例："
    echo "  $0 input/技术方案.pdf"
    echo "  $0 ~/Desktop/方案.pdf \"按周分解\""
    echo ""
    echo "支持的格式：PDF、DOCX、Markdown (.md)"
    exit 0
fi

FILE_PATH="$1"
shift

INTENT=""
EXTRA_ARGS=""
while [ $# -gt 0 ]; do
    case "$1" in
        --*)
            EXTRA_ARGS="$EXTRA_ARGS $1"
            ;;
        *)
            if [ -z "$INTENT" ]; then
                INTENT="$1"
            else
                INTENT="$INTENT $1"
            fi
            ;;
    esac
    shift
done

# ========== 文件路径处理 ==========
if [ ! -f "$FILE_PATH" ]; then
    INPUT_PATH="$SCRIPT_DIR/input/$FILE_PATH"
    if [ -f "$INPUT_PATH" ]; then
        FILE_PATH="$INPUT_PATH"
        echo -e "${YELLOW}📂 从 input/ 目录找到文件${NC}"
    else
        echo -e "${RED}❌ 文件不存在：$FILE_PATH${NC}"
        echo ""
        echo "提示："
        echo "  1. 检查文件路径是否正确"
        echo "  2. 将文件放到 input/ 目录下，然后执行：./wbs.sh $FILE_PATH"
        echo "  3. 使用绝对路径：./wbs.sh /完整/路径/$FILE_PATH"
        exit 2
    fi
fi

# ========== 执行 ==========
echo -e "${GREEN}🚀 开始生成 WBS...${NC}"

CMD="$PYTHON \"$SCRIPT_DIR/src/wbs_cli.py\" --file \"$FILE_PATH\""

if [ -n "$INTENT" ]; then
    CMD="$CMD --intent \"$INTENT\""
fi

if [ -n "$EXTRA_ARGS" ]; then
    CMD="$CMD $EXTRA_ARGS"
fi

eval "$CMD"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ WBS 生成完成！${NC}"
    echo "📁 结果文件在：$SCRIPT_DIR/output/"
else
    echo ""
    echo -e "${RED}❌ WBS 生成失败（错误码：$EXIT_CODE）${NC}"
    case $EXIT_CODE in
        1) echo "可能原因：环境配置问题，请运行 ./install.sh 检查" ;;
        2) echo "可能原因：文件不存在或格式不支持" ;;
        3) echo "可能原因：文档解析失败，检查文档是否为扫描件" ;;
        4) echo "可能原因：Excel 输出失败，检查 output/ 目录权限" ;;
        *) echo "请查看上方错误信息" ;;
    esac
fi

exit $EXIT_CODE
