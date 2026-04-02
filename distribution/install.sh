#!/bin/bash
# TeamClaw 代码审查工具 - 安装脚本 (Mac/Linux)
# 版本：v1.0.0
# 改进版：自动检测所有 IDEA 版本 + Cursor 配置

set -e

echo "=========================================="
echo "   TeamClaw 代码审查工具 - 安装向导"
echo "   版本：v1.0.0"
echo "=========================================="
echo ""

# 检测操作系统
OS="$(uname -s)"
case "$OS" in
    Linux*)
        OPEN_CMD="xdg-open"
        PACKAGE_MANAGER="apt/yum/dnf"
        ;;
    Darwin*)
        OPEN_CMD="open"
        PACKAGE_MANAGER="brew"
        ;;
    *)
        echo "❌ 不支持的操作系统：$OS"
        echo "   支持：macOS, Linux"
        exit 1
        ;;
esac

echo "📱 检测到系统：$OS"
echo ""

# 检查 Python
echo "[1/6] 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo ""
    echo "❌ 未检测到 Python3"
    echo ""
    echo "请先安装 Python 3.8 或更高版本："
    echo "  macOS: brew install python3"
    echo "  Ubuntu: sudo apt install python3 python3-pip"
    echo "  CentOS: sudo yum install python3 python3-pip"
    echo ""
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ 已检测到 Python $PYTHON_VERSION"

# 检查版本 (3.8+)
python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Python 版本过低，需要 3.8 或更高版本"
    echo "   当前版本：$PYTHON_VERSION"
    exit 1
fi
echo "✅ Python 版本符合要求 (3.8+)"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$HOME/.openclaw/workspace"

# 创建工作目录
echo "[2/6] 创建工作目录..."
mkdir -p "$WORKSPACE_DIR/scripts"
mkdir -p "$WORKSPACE_DIR/code-reports"
mkdir -p "$WORKSPACE_DIR/idea-plugin"
mkdir -p "$WORKSPACE_DIR/cursor-tasks"
mkdir -p "$WORKSPACE_DIR/docs"
echo "✅ 工作目录：$WORKSPACE_DIR"
echo ""

# 复制脚本文件
echo "[3/6] 复制脚本文件..."
if [ -d "$SCRIPT_DIR/scripts" ]; then
    cp -r "$SCRIPT_DIR/scripts/"*.py "$WORKSPACE_DIR/scripts/" 2>/dev/null || true
    echo "✅ 已复制脚本到：$WORKSPACE_DIR/scripts"
else
    echo "⚠️  未找到 scripts 目录，跳过..."
fi

if [ -d "$SCRIPT_DIR/idea-plugin" ]; then
    cp -r "$SCRIPT_DIR/idea-plugin/"*.xml "$WORKSPACE_DIR/idea-plugin/" 2>/dev/null || true
    echo "✅ 已复制 IDEA 配置到：$WORKSPACE_DIR/idea-plugin"
else
    echo "⚠️  未找到 idea-plugin 目录，跳过..."
fi

if [ -d "$SCRIPT_DIR/cursor-tasks" ]; then
    cp -r "$SCRIPT_DIR/cursor-tasks/"*.json "$WORKSPACE_DIR/cursor-tasks/" 2>/dev/null || true
    echo "✅ 已复制 Cursor 配置到：$WORKSPACE_DIR/cursor-tasks"
else
    echo "⚠️  未找到 cursor-tasks 目录，跳过..."
fi

if [ -d "$SCRIPT_DIR/docs" ]; then
    cp -r "$SCRIPT_DIR/docs/"*.md "$WORKSPACE_DIR/docs/" 2>/dev/null || true
    echo "✅ 已复制文档到：$WORKSPACE_DIR/docs"
fi
echo ""

# 创建启动脚本
echo "[4/6] 创建启动脚本..."
cat > "$WORKSPACE_DIR/code-review.sh" << EOF
#!/bin/bash
# TeamClaw 代码审查工具 - 启动脚本
exec python3 "$WORKSPACE_DIR/scripts/code-review-multi-agent.py" "\$@"
EOF

chmod +x "$WORKSPACE_DIR/code-review.sh"
echo "✅ 已创建启动脚本：$WORKSPACE_DIR/code-review.sh"
echo ""

# 配置 IDEA - 自动检测所有版本
echo "[5/6] 配置 IntelliJ IDEA..."
echo ""

IDEA_CONFIGURED=0

# 检测 IDEA 配置目录
IDEA_DIRS=(
    "$HOME/Library/Application Support/JetBrains/IntelliJIdea*"
    "$HOME/Library/Application Support/JetBrains/IdeaIC*"
    "$HOME/.local/share/JetBrains/IntelliJIdea*"
    "$HOME/.local/share/JetBrains/IdeaIC*"
)

for pattern in "${IDEA_DIRS[@]}"; do
    for idea_dir in $pattern; do
        if [ -d "$idea_dir" ]; then
            echo "📁 检测到 IDEA: $(basename "$idea_dir")"
            
            # 创建 tools 目录
            mkdir -p "$idea_dir/tools"
            
            # 复制配置文件
            if cp "$WORKSPACE_DIR/idea-plugin/code-reviewer-external-tools.xml" "$idea_dir/tools/" 2>/dev/null; then
                echo "   ✅ 配置已添加到：$idea_dir/tools/"
                IDEA_CONFIGURED=1
            else
                echo "   ⚠️  复制配置失败"
            fi
            echo ""
        fi
    done
done

if [ $IDEA_CONFIGURED -eq 0 ]; then
    echo "⚠️  未检测到 IDEA 安装"
    echo ""
    echo "请手动配置："
    echo "  1. 打开 IDEA"
    echo "  2. File → Settings → Tools → External Tools"
    echo "  3. 点击导入图标"
    echo "  4. 选择：$WORKSPACE_DIR/idea-plugin/code-reviewer-external-tools.xml"
    echo ""
else
    echo "✅ IDEA 配置完成！"
    echo ""
    echo "📝 下一步："
    echo "  请重启所有已打开的 IntelliJ IDEA"
    echo "  右键代码文件 → External Tools → Code Review (Multi-Agent)"
    echo ""
fi

# 配置 Cursor
echo "[6/6] 配置 Cursor..."
echo ""

# 检测 Cursor 配置目录
case "$OS" in
    Darwin*)
        CURSOR_CONFIG="$HOME/Library/Application Support/Cursor/User"
        ;;
    Linux*)
        CURSOR_CONFIG="$HOME/.config/Cursor/User"
        ;;
esac

if [ -d "$CURSOR_CONFIG" ]; then
    echo "📁 检测到 Cursor 配置目录"
    
    # 创建 tasks 目录
    mkdir -p "$CURSOR_CONFIG/tasks"
    
    # 复制任务配置
    if cp "$WORKSPACE_DIR/cursor-tasks/code-review.json" "$CURSOR_CONFIG/tasks/" 2>/dev/null; then
        echo "   ✅ 任务配置已添加到：$CURSOR_CONFIG/tasks/"
        echo ""
        echo "✅ Cursor 配置完成！"
        echo ""
        echo "📝 使用方法："
        echo "  1. 打开 Cursor"
        echo "  2. Ctrl+Shift+P → Tasks: Run Task → Code Review"
        echo "  3. 或右键文件 → Run Task → Code Review"
        echo ""
    else
        echo "   ⚠️  复制任务配置失败"
    fi
else
    echo "⚠️  未检测到 Cursor 安装"
    echo ""
    echo "Cursor 配置路径：$WORKSPACE_DIR/cursor-tasks/code-review.json"
    echo "如使用 Cursor，请手动复制配置到："
    echo "  macOS: ~/Library/Application Support/Cursor/User/tasks/"
    echo "  Linux: ~/.config/Cursor/User/tasks/"
    echo ""
fi

# 添加到 PATH (可选)
if [[ ":$PATH:" != *":$WORKSPACE_DIR:"* ]]; then
    echo "💡 提示：可以将以下行添加到 ~/.bashrc 或 ~/.zshrc："
    echo "   export PATH=\"\$PATH:$WORKSPACE_DIR\""
    echo ""
    read -p "是否现在添加到 ~/.bashrc？(y/N): " add_to_path
    if [[ "$add_to_path" =~ ^[Yy]$ ]]; then
        echo "" >> ~/.bashrc 2>/dev/null || true
        echo "# TeamClaw Code Reviewer" >> ~/.bashrc 2>/dev/null || true
        echo "export PATH=\"\$PATH:$WORKSPACE_DIR\"" >> ~/.bashrc 2>/dev/null || true
        echo "✅ 已添加到 ~/.bashrc，请运行 'source ~/.bashrc' 生效"
    fi
fi
echo ""

# 完成
echo "=========================================="
echo "   ✅ 安装完成！"
echo "=========================================="
echo ""
echo "🎯 使用方法："
echo ""
echo "  【IntelliJ IDEA】"
echo "    重启 IDEA 后，右键代码 → External Tools → Code Review"
echo ""
echo "  【Cursor】"
echo "    Ctrl+Shift+P → Tasks: Run Task → Code Review"
echo ""
echo "  【命令行】"
echo "    cd $WORKSPACE_DIR"
echo "    ./code-review.sh 你的代码文件路径"
echo "    或直接：code-review.sh (如果已添加到 PATH)"
echo ""
echo "📂 报告位置："
echo "    $WORKSPACE_DIR/code-reports/"
echo ""
echo "📖 详细文档："
echo "    $WORKSPACE_DIR/docs/code-review-quickstart.md"
echo ""
echo "=========================================="
echo ""

# 询问是否打开报告目录
read -p "是否现在打开报告目录？(y/N): " open_reports
if [[ "$open_reports" =~ ^[Yy]$ ]]; then
    mkdir -p "$WORKSPACE_DIR/code-reports"
    $OPEN_CMD "$WORKSPACE_DIR/code-reports"
fi

echo ""
echo "感谢使用 TeamClaw 代码审查工具！"
echo ""
