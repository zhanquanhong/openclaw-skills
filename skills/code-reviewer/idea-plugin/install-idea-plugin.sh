#!/bin/bash
# Code Reviewer IDEA 插件安装脚本
# 支持 Windows (Git Bash), macOS, Linux

set -e

echo "🦞 Code Reviewer - IDEA 插件安装"
echo "================================"

# 检测操作系统
OS="$(uname -s)"
case "$OS" in
    Darwin*)
        OS="mac"
        IDEA_DIR="$HOME/Library/Application Support/JetBrains"
        ;;
    Linux*)
        OS="linux"
        IDEA_DIR="$HOME/.local/share/JetBrains"
        ;;
    MINGW*|MSYS*|CYGWIN*)
        OS="windows"
        IDEA_DIR="$APPDATA/JetBrains"
        ;;
    *)
        echo "❌ 不支持的操作系统：$OS"
        exit 1
        ;;
esac

echo "📱 检测到操作系统：$OS"
echo "📂 IDEA 配置目录：$IDEA_DIR"

# 查找 IDEA 版本
IDEA_VERSION=""
if [ -d "$IDEA_DIR" ]; then
    # 查找最新的 IDEA 版本
    IDEA_VERSION=$(ls -t "$IDEA_DIR" | grep -E "IntelliJIdea|IdeaIC|IdeaIU" | head -1)
fi

if [ -z "$IDEA_VERSION" ]; then
    echo "⚠️  未找到 IDEA 安装，请手动配置"
    echo ""
    echo "手动安装步骤："
    echo "1. 找到 IDEA 配置目录："
    echo "   - Windows: %USERPROFILE%\\AppData\\Roaming\\JetBrains\\<version>\\"
    echo "   - macOS: ~/Library/Application Support/JetBrains/<version>/"
    echo "   - Linux: ~/.local/share/JetBrains/<version>/"
    echo ""
    echo "2. 创建 tools 目录（如果不存在）"
    echo "3. 复制 code-reviewer.xml 到 tools 目录"
    echo "4. 重启 IDEA"
    exit 1
fi

echo "✨ 找到 IDEA 版本：$IDEA_VERSION"
IDEA_CONFIG_DIR="$IDEA_DIR/$IDEA_VERSION"

# 创建 tools 目录
TOOLS_DIR="$IDEA_CONFIG_DIR/tools"
echo "📁 创建 tools 目录：$TOOLS_DIR"
mkdir -p "$TOOLS_DIR"

# 复制配置文件
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "📋 复制配置文件..."
cp "$SCRIPT_DIR/code-reviewer.xml" "$TOOLS_DIR/"

# 设置执行权限（Unix 系统）
if [ "$OS" != "windows" ]; then
    chmod +x "$TOOLS_DIR/code-reviewer.xml"
fi

echo ""
echo "✅ 安装完成！"
echo ""
echo "📝 使用说明："
echo "1. 重启 IntelliJ IDEA"
echo "2. 在项目中右键 → External Tools → Code Reviewer"
echo "3. 选择扫描模式："
echo "   - Full Scan: 扫描整个项目"
echo "   - Security Only: 仅安全检查"
echo "   - Current File: 扫描当前文件"
echo ""
echo "📄 报告将保存到项目根目录："
echo "   - code-review-report.md (完整报告)"
echo "   - security-review-report.md (安全报告)"
echo ""
echo "⚙️  如需自定义配置，编辑："
echo "   $TOOLS_DIR/code-reviewer.xml"
