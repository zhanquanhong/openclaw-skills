# TeamClaw 代码审查工具 v1.0.1

自动化代码安全审计和质量检查工具，支持 Java 和 Python 项目。

## 🚀 快速开始

### Windows 用户

1. 双击 `install.bat` 运行安装向导
2. 按提示完成安装
3. 重启 IntelliJ IDEA
4. 右键代码文件 → External Tools → Code Review (Multi-Agent)

### macOS / Linux 用户

```bash
# 1. 赋予执行权限
chmod +x install.sh

# 2. 运行安装
./install.sh

# 3. 重启 IntelliJ IDEA

# 4. 右键代码文件 → External Tools → Code Review (Multi-Agent)
```

## 📋 系统要求

- **Python:** 3.8 或更高版本
- **操作系统:** 
  - Windows 10 或更高版本
  - macOS 10.15 (Catalina) 或更高版本
  - Linux (Ubuntu 18.04+, CentOS 7+)
- **IDE:** IntelliJ IDEA 2020.1 或更高版本（可选）

## 🎯 使用方法

### 命令行使用

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

### IDEA 集成

安装后，在 IDEA 中右键代码文件，选择：
- **Code Review (Multi-Agent)** - 多代理并行审查（推荐）
- **Code Review (Single Agent)** - 单代理串行审查
- **Code Review (Security Only)** - 仅安全检查
- **Code Review (Full Project)** - 审查整个项目

## 📂 目录结构

```
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
```

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

## 📞 技术支持

- **项目地址:** https://github.com/zhanquanhong/openclaw-skills
- **问题反馈:** https://github.com/zhanquanhong/openclaw-skills/issues
- **文档:** https://docs.openclaw.ai

## 📄 许可证

MIT License

---

**版本:** v1.0.1  
**发布日期:** 2026-04-02  
**维护者:** TeamClaw
