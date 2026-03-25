#!/bin/bash
# 团队开发环境配置脚本
# 一键安装 Code Reviewer 和 Auto Tester

set -e

echo "🦞 OpenClaw 团队开发环境配置"
echo "================================"
echo ""

# 检测操作系统
OS="$(uname -s)"
case "$OS" in
    Darwin*)
        IDEA_DIR="$HOME/Library/Application Support/JetBrains"
        ;;
    Linux*)
        IDEA_DIR="$HOME/.local/share/JetBrains"
        ;;
    MINGW*|MSYS*|CYGWIN*)
        IDEA_DIR="$APPDATA/JetBrains"
        ;;
    *)
        echo "❌ 不支持的操作系统：$OS"
        exit 1
        ;;
esac

echo "📱 操作系统：$OS"
echo "📂 IDEA 配置目录：$IDEA_DIR"
echo ""

# 查找最新的 IDEA 版本
IDEA_VERSION=""
if [ -d "$IDEA_DIR" ]; then
    IDEA_VERSION=$(ls -t "$IDEA_DIR" 2>/dev/null | grep -E "IntelliJIdea|IdeaIC|IdeaIU" | head -1)
fi

if [ -z "$IDEA_VERSION" ]; then
    echo "⚠️  未找到 IDEA 安装"
    echo ""
    echo "请先安装 IntelliJ IDEA，然后重新运行此脚本"
    echo "下载地址：https://www.jetbrains.com/idea/download/"
    echo ""
    echo "或者手动配置："
    echo "1. 找到 IDEA 配置目录"
    echo "2. 创建 tools 目录"
    echo "3. 复制 code-reviewer.xml 到 tools 目录"
    echo "4. 重启 IDEA"
    exit 1
fi

echo "✅ 找到 IDEA 版本：$IDEA_VERSION"
echo ""

# 创建 tools 目录
TOOLS_DIR="$IDEA_DIR/$IDEA_VERSION/tools"
echo "📁 创建 tools 目录：$TOOLS_DIR"
mkdir -p "$TOOLS_DIR"

# 复制 Code Reviewer 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "📋 复制 Code Reviewer 配置..."
cp "$SCRIPT_DIR/skills/code-reviewer/idea-plugin/code-reviewer.xml" "$TOOLS_DIR/"

echo ""
echo "✅ Code Reviewer 配置完成！"
echo ""

# 验证 Python 环境
echo "🔍 检查 Python 环境..."
if command -v python3 &> /dev/null; then
    PYTHON_PATH=$(which python3)
    echo "✅ Python3 已安装：$PYTHON_PATH"
else
    echo "⚠️  Python3 未找到，请安装 Python 3.8+"
    echo "   下载地址：https://www.python.org/downloads/"
fi

echo ""
echo "================================"
echo "🎉 配置完成！"
echo "================================"
echo ""
echo "下一步："
echo "1. 重启 IntelliJ IDEA"
echo "2. 右键项目 → External Tools → 应看到 Code Reviewer 菜单"
echo "3. 阅读详细文档：docs/idea-plugin-setup.md"
echo ""
echo "Auto Tester 使用说明："
echo "  生成测试：python3 skills/auto-tester/scripts/auto-tester.py /path/to/project --generate"
echo "  执行测试：python3 skills/auto-tester/scripts/auto-tester.py /path/to/project --execute --type regression"
echo ""
