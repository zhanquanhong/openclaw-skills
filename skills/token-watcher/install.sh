#!/bin/bash
#
# Token Watcher 一键安装脚本 (Linux/macOS)
#
# 用法:
#   cd skills/token-watcher
#   bash install.sh
#
# 安装完成后:
#   token-watcher dashboard          启动 Web Dashboard (默认端口 8100)
#   token-watcher dashboard --port 8101  指定端口
#   token-watcher stats              查看统计摘要
#   token-watcher report             生成 HTML 报告
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$SCRIPT_DIR"

echo "============================================"
echo "  📦 Token Watcher 一键安装"
echo "============================================"
echo ""

# ── 1. 检测 Python ──────────────────────────────────

PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "❌ 未找到 Python，请先安装 Python 3.8+"
    echo "   https://www.python.org/downloads/"
    exit 1
fi

PY_VER=$("$PYTHON" --version 2>&1 | grep -oP '\d+\.\d+')
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]; }; then
    echo "❌ Python 版本过低: $("$PYTHON" --version)，需要 3.8+"
    exit 1
fi

echo "✅ Python: $("$PYTHON" --version)"

# ── 2. 安装依赖 ─────────────────────────────────────

echo ""
echo "📥 安装 Python 依赖..."

print_label() { printf "  · %-30s " "$1"; }

# tiktoken — 核心依赖，必须安装
print_label "tiktoken (Token 计数)"
if "$PYTHON" -m pip install -q tiktoken --break-system-packages 2>/dev/null; then
    echo "✅"
elif "$PYTHON" -m pip install -q tiktoken 2>/dev/null; then
    echo "✅"
elif command -v uv &>/dev/null && uv pip install --system tiktoken 2>/dev/null; then
    echo "✅"
else
    echo "⚠️ 跳过（token 估算降级）"
fi

# aiohttp — 可选依赖，仅 API 代理模式需要
print_label "aiohttp (API 代理)"
if timeout 120 "$PYTHON" -m pip install -q aiohttp --break-system-packages 2>/dev/null; then
    echo "✅"
elif timeout 120 "$PYTHON" -m pip install -q aiohttp 2>/dev/null; then
    echo "✅"
elif command -v uv &>/dev/null && timeout 120 uv pip install --system aiohttp 2>/dev/null; then
    echo "✅"
else
    echo "⚠️ 跳过（不影响 Dashboard）"
fi

echo "✅ 依赖检查完成"

# ── 3. 创建启动命令 ─────────────────────────────────

LAUNCHER="/usr/local/bin/token-watcher"
LAUNCHER_FALLBACK="$HOME/.local/bin/token-watcher"

# 尝试写入 /usr/local/bin，失败则写入 ~/.local/bin
if [ -d "/usr/local/bin" ] && [ -w "/usr/local/bin" ]; then
    TARGET="$LAUNCHER"
elif [ -d "$HOME/.local/bin" ] && [ -w "$HOME/.local/bin" ]; then
    TARGET="$LAUNCHER_FALLBACK"
else
    # 尝试创建 ~/.local/bin
    mkdir -p "$HOME/.local/bin" 2>/dev/null || true
    if [ -w "$HOME/.local/bin" ]; then
        TARGET="$LAUNCHER_FALLBACK"
    else
        echo ""
        echo "⚠️  无法创建启动命令（无写入权限）"
        echo "   请手动将技能目录加入 PATH："
        echo "   export PATH=\"\$PATH:$SKILL_DIR\""
        echo ""
        echo "   然后使用: python3 -m src.main dashboard"
        exit 0
    fi
fi

cat > "$TARGET" << LAUNCHER_SCRIPT
#!/bin/bash
SKILL_DIR="$SKILL_DIR"
PYTHON="$PYTHON"
cd "\$SKILL_DIR" || exit 1
exec "\$PYTHON" -m src.main "\$@"
LAUNCHER_SCRIPT

chmod +x "$TARGET"

echo ""
echo "✅ 启动命令已创建: $TARGET"

# 检查 PATH 是否包含目标目录
TARGET_DIR="$(dirname "$TARGET")"
if [[ ":$PATH:" != *":$TARGET_DIR:"* ]]; then
    echo ""
    echo "⚠️  $TARGET_DIR 不在 PATH 中"
    echo "   请将以下命令加入 ~/.bashrc 或 ~/.zshrc："
    echo "   export PATH=\"\$PATH:$TARGET_DIR\""
    echo ""
    echo "   或手动执行: export PATH=\"\$PATH:$TARGET_DIR\""
fi

# ── 4. 完成 ─────────────────────────────────────────

echo ""
echo "============================================"
echo "  ✅ Token Watcher 安装完成！"
echo "============================================"
echo ""
echo "快速启动："
echo "  token-watcher dashboard"
echo ""
echo "指定端口："
echo "  token-watcher dashboard --port 8101"
echo ""
echo "查看统计："
echo "  token-watcher stats"
echo ""
echo "生成报告："
echo "  token-watcher report"
echo ""
echo "打开浏览器访问 http://localhost:8100 即可查看"
echo ""
