#!/bin/bash
# TeamClaw 代码审查工具 - 打包脚本
# 用于生成团队分发的安装包

set -e

echo "📦 TeamClaw 代码审查工具 - 打包脚本"
echo "===================================="
echo ""

# 配置
VERSION="1.0.3"
PACKAGE_NAME="teamclaw-code-reviewer-v${VERSION}"
WORKSPACE_DIR="$HOME/.openclaw/workspace"
DIST_DIR="$WORKSPACE_DIR/distribution"
PACKAGE_DIR="$DIST_DIR/$PACKAGE_NAME"

# 清理旧包
echo "[1/4] 清理旧包..."
rm -rf "$PACKAGE_DIR"
rm -f "$DIST_DIR/${PACKAGE_NAME}.zip"
rm -f "$DIST_DIR/${PACKAGE_NAME}.tar.gz"
mkdir -p "$PACKAGE_DIR"
echo "✅ 已清理"
echo ""

# 复制文件
echo "[2/4] 复制文件..."

# 创建目录结构
mkdir -p "$PACKAGE_DIR/scripts"
mkdir -p "$PACKAGE_DIR/idea-plugin"
mkdir -p "$PACKAGE_DIR/docs"

# 复制核心脚本
cp "$WORKSPACE_DIR/scripts/code-reviewer.py" "$PACKAGE_DIR/scripts/" 2>/dev/null && echo "  ✅ code-reviewer.py" || echo "  ⚠️  code-reviewer.py (未找到)"
cp "$WORKSPACE_DIR/scripts/code-review-multi-agent.py" "$PACKAGE_DIR/scripts/" 2>/dev/null && echo "  ✅ code-review-multi-agent.py" || echo "  ⚠️  code-review-multi-agent.py (未找到)"

# 复制 IDEA 配置
cp "$WORKSPACE_DIR/idea-plugin/code-reviewer-external-tools.xml" "$PACKAGE_DIR/idea-plugin/" 2>/dev/null && echo "  ✅ code-reviewer-external-tools.xml" || echo "  ⚠️  code-reviewer-external-tools.xml (未找到)"

# 复制文档
cp "$WORKSPACE_DIR/docs/code-review-quickstart.md" "$PACKAGE_DIR/docs/" 2>/dev/null && echo "  ✅ code-review-quickstart.md" || echo "  ⚠️  code-review-quickstart.md (未找到)"
cp "$WORKSPACE_DIR/docs/idea-plugin-setup.md" "$PACKAGE_DIR/docs/" 2>/dev/null && echo "  ✅ idea-plugin-setup.md" || echo "  ⚠️  idea-plugin-setup.md (未找到)"

# 复制安装脚本
cp "$DIST_DIR/install.bat" "$PACKAGE_DIR/" && echo "  ✅ install.bat"
cp "$DIST_DIR/install.sh" "$PACKAGE_DIR/" && echo "  ✅ install.sh"

# 创建 README
echo "[3/4] 创建 README..."
cat > "$PACKAGE_DIR/README.md" << EOF
# TeamClaw 代码审查工具 v${VERSION}

自动化代码安全审计和质量检查工具，支持 Java 和 Python 项目。

## 🚀 快速开始

### Windows 用户

1. 双击 \`install.bat\` 运行安装向导
2. 按提示完成安装
3. 重启 IntelliJ IDEA
4. 右键代码文件 → External Tools → Code Review (Multi-Agent)

### macOS / Linux 用户

\`\`\`bash
# 1. 赋予执行权限
chmod +x install.sh

# 2. 运行安装
./install.sh

# 3. 重启 IntelliJ IDEA

# 4. 右键代码文件 → External Tools → Code Review (Multi-Agent)
\`\`\`

## 📋 系统要求

- **Python:** 3.8 或更高版本
- **操作系统:** 
  - Windows 10 或更高版本
  - macOS 10.15 (Catalina) 或更高版本
  - Linux (Ubuntu 18.04+, CentOS 7+)
- **IDE:** IntelliJ IDEA 2020.1 或更高版本（可选）

## 🎯 使用方法

### 命令行使用

\`\`\`bash
# 审查单个文件
python scripts/code-review-multi-agent.py src/main/java/com/example/UserService.java

# 审查整个项目
python scripts/code-review-multi-agent.py . --multi-agent

# 只检查安全问题
python scripts/code-review-multi-agent.py . --focus security

# 查看帮助
python scripts/code-review-multi-agent.py --help
\`\`\`

### IDEA 集成

安装后，在 IDEA 中右键代码文件，选择：
- **Code Review (Multi-Agent)** - 多代理并行审查（推荐）
- **Code Review (Single Agent)** - 单代理串行审查
- **Code Review (Security Only)** - 仅安全检查
- **Code Review (Full Project)** - 审查整个项目

## 📂 目录结构

\`\`\`
teamclaw-code-reviewer/
├── README.md              # 本文件
├── install.bat            # Windows 安装脚本
├── install.sh             # Mac/Linux 安装脚本
├── scripts/
│   ├── code-reviewer.py           # 核心审查引擎
│   └── code-review-multi-agent.py # 多代理协调器
├── idea-plugin/
│   └── code-reviewer-external-tools.xml  # IDEA 外部工具配置
└── docs/
    ├── code-review-quickstart.md  # 快速开始指南
    └── idea-plugin-setup.md       # IDEA 配置详解
\`\`\`

## 📊 检测规则

### 安全漏洞 (🔴 严重 / 🟠 高危)
- SQL 注入
- 命令注入
- 路径遍历
- 硬编码敏感信息（密码、密钥）
- 不安全随机数
- XSS 漏洞
- 不安全 SSL 配置

### 代码规范 (🟡 中危 / 🟢 低危)
- 命名规范（类、方法、变量、常量）
- 方法/类长度
- 注释完整性
- 魔法值
- 缩进/格式

### 性能问题 (🟠 高危 / 🟡 中危)
- 字符串拼接性能
- 未关闭资源
- 低效集合操作
- 空 catch/except 块
- N+1 查询问题

## 📖 详细文档

- 快速开始：docs/code-review-quickstart.md
- IDEA 配置：docs/idea-plugin-setup.md
- 多代理架构：docs/code-review-multi-agent.md

## 🛠️ 自定义规则

编辑 \`scripts/code-reviewer.py\` 添加团队自定义规则：

\`\`\`python
CUSTOM_RULES = [
    {
        "id": "TEAM-001",
        "name": "禁止使用 System.out.println",
        "pattern": r"System\\.out\\.println",
        "severity": "MEDIUM",
        "message": "请使用日志框架代替 System.out"
    }
]
\`\`\`

## 📞 技术支持

- **项目地址:** https://github.com/zhanquanhong/openclaw-skills
- **问题反馈:** https://github.com/zhanquanhong/openclaw-skills/issues
- **文档:** https://docs.openclaw.ai

## 📄 许可证

MIT License

---

**版本:** v${VERSION}  
**发布日期:** $(date +%Y-%m-%d)  
**维护者:** TeamClaw
EOF

echo "✅ README.md"
echo ""

# 压缩打包
echo "[4/4] 压缩打包..."
cd "$DIST_DIR"

# Windows ZIP
zip -r "${PACKAGE_NAME}.zip" "$PACKAGE_NAME" > /dev/null
echo "✅ ${PACKAGE_NAME}.zip ($(du -h "${PACKAGE_NAME}.zip" | cut -f1))"

# Mac/Linux TAR.GZ
tar -czf "${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME"
echo "✅ ${PACKAGE_NAME}.tar.gz ($(du -h "${PACKAGE_NAME}.tar.gz" | cut -f1))"

echo ""
echo "===================================="
echo "✅ 打包完成！"
echo "===================================="
echo ""
echo "📦 安装包位置："
echo "   $DIST_DIR/${PACKAGE_NAME}.zip"
echo "   $DIST_DIR/${PACKAGE_NAME}.tar.gz"
echo ""
echo "📤 分发方式："
echo ""
echo "  方式 1 - 团队共享目录："
echo "    cp ${PACKAGE_NAME}.zip /shared/team-tools/"
echo ""
echo "  方式 2 - GitHub Releases："
echo "    gh release create v${VERSION} ${PACKAGE_NAME}.zip ${PACKAGE_NAME}.tar.gz"
echo ""
echo "  方式 3 - 直接发送："
echo "    通过邮件或即时通讯工具发送给团队成员"
echo ""
echo "===================================="
echo ""
