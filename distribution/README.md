# TeamClaw 代码审查工具 v1.0.0

自动化代码安全审计和质量检查工具，支持 Java 和 Python 项目。

## 🚀 快速开始

### Windows 用户

1. 下载并解压 zip
2. **双击 `install.bat`**（自动配置 IDEA 和 Cursor）
3. 重启 IDEA/Cursor
4. 右键代码 → External Tools / Tasks → Code Review

### macOS / Linux 用户

```bash
# 1. 下载并解压
tar -xzf teamclaw-code-reviewer-v1.0.0.tar.gz
cd teamclaw-code-reviewer-v1.0.0

# 2. 运行安装（自动配置 IDEA 和 Cursor）
chmod +x install.sh
./install.sh

# 3. 重启 IDEA/Cursor
```

---

## 📋 系统要求

- **Python:** 3.8 或更高版本
- **操作系统:** 
  - Windows 10 或更高版本
  - macOS 10.15 (Catalina) 或更高版本
  - Linux (Ubuntu 18.04+, CentOS 7+)
- **IDE:** 
  - IntelliJ IDEA 2020.1+ (可选，自动配置)
  - Cursor (可选，自动配置)

---

## 🎯 使用方法

### IntelliJ IDEA

**安装后自动配置**，重启 IDEA 后：

1. 右键代码文件
2. 选择 `External Tools`
3. 点击 `Code Review (Multi-Agent)`

**支持的审查模式：**
- Code Review (Multi-Agent) - 多代理并行（推荐）
- Code Review (Single Agent) - 单代理串行
- Code Review (Security Only) - 仅安全检查
- Code Review (Full Project) - 审查整个项目

---

### Cursor

**安装后自动配置**，打开 Cursor 后：

1. 按 `Ctrl+Shift+P` (macOS: `Cmd+Shift+P`)
2. 输入 `Tasks: Run Task`
3. 选择 `Code Review (Multi-Agent)`

**或右键文件：**
- 右键代码文件
- 选择 `Run Task` → `Code Review (Multi-Agent)`

---

### 命令行

```bash
# 审查单个文件
python scripts/code-review-multi-agent.py src/main/java/com/example/UserService.java

# 审查整个项目
python scripts/code-review-multi-agent.py . --multi-agent

# 只检查安全问题
python scripts/code-review-multi-agent.py . --focus security

# 查看帮助
python scripts/code-review-multi-agent.py --help
```

---

## 📂 目录结构

```
teamclaw-code-reviewer/
├── README.md              # 本文件
├── install.bat            # Windows 安装脚本（自动配置）
├── install.sh             # Mac/Linux 安装脚本（自动配置）
├── scripts/
│   ├── code-reviewer.py           # 核心审查引擎
│   └── code-review-multi-agent.py # 多代理协调器
├── idea-plugin/
│   └── code-reviewer-external-tools.xml  # IDEA 外部工具配置
├── cursor-tasks/
│   └── code-review.json           # Cursor 任务配置
└── docs/
    ├── code-review-quickstart.md  # 快速开始指南
    └── idea-plugin-setup.md       # IDEA 配置详解
```

---

## 📊 检测规则

### 安全漏洞 (🔴 严重 / 🟠 高危)
- SQL 注入
- 命令注入
- 路径遍历
- 硬编码敏感信息（密码、密钥）
- 不安全随机数
- XSS 漏洞
- 不安全 SSL 配置
- 不安全反序列化

### 代码规范 (🟡 中危 / 🟢 低危)
- 命名规范（类、方法、变量、常量）
- 方法/类长度
- 注释完整性
- 魔法值
- 缩进/格式
- 导入顺序

### 性能问题 (🟠 高危 / 🟡 中危)
- 字符串拼接性能
- 未关闭资源
- 低效集合操作
- 空 catch/except 块
- N+1 查询问题
- 全局变量滥用

---

## 📖 详细文档

- 快速开始：docs/code-review-quickstart.md
- IDEA 配置：docs/idea-plugin-setup.md
- 多代理架构：docs/code-review-multi-agent.md
- 团队分发：docs/team-distribution-plan.md

---

## 🛠️ 自定义规则

编辑 `scripts/code-reviewer.py` 添加团队自定义规则：

```python
CUSTOM_RULES = [
    {
        "id": "TEAM-001",
        "name": "禁止使用 System.out.println",
        "pattern": r"System\.out\.println",
        "severity": "MEDIUM",
        "message": "请使用日志框架代替 System.out"
    }
]
```

---

## ❓ 常见问题

### Q: 安装后 IDEA/Cursor 没有自动配置？
A: 检查是否看到 "检测到 IDEA/Cursor" 的提示。如未检测到，请手动配置：
- **IDEA:** File → Settings → Tools → External Tools → 导入配置
- **Cursor:** 复制 `cursor-tasks/code-review.json` 到配置目录

### Q: 多个 IDEA 版本都会配置吗？
A: 是的，安装脚本会自动检测并配置所有 IDEA 版本。

### Q: Python 版本过低？
A: Windows 用户从 python.org 下载 3.8+，Mac 用户 `brew install python3`

### Q: 审查速度慢？
A: 大项目建议使用 `--focus` 参数只检查特定类型，或排除不重要的目录

### Q: 误报太多？
A: 在代码中添加 `// code-review-ignore: RULE-ID` 注释，或调整规则

### Q: 如何更新到新版本？
A: 重新运行安装脚本，会自动覆盖旧版本

---

## 📞 技术支持

- **项目地址:** https://github.com/zhanquanhong/openclaw-skills
- **问题反馈:** https://github.com/zhanquanhong/openclaw-skills/issues
- **文档:** https://docs.openclaw.ai

---

## 📄 许可证

MIT License

---

**版本:** v1.0.0  
**发布日期:** 2026-04-01  
**维护者:** TeamClaw
