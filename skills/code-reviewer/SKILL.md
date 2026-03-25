---
name: code-reviewer
description: 代码走读工具。支持 Java/Python 代码安全漏洞检测、代码规范检查、性能问题分析。可独立运行或集成到 IDEA 作为外部工具，一键执行自动化代码走读，生成 Markdown/JSON 格式报告。适用于 Windows/Mac/Linux。
---

# 代码走读工具 - Code Reviewer

自动化代码安全审计和质量检查工具，支持 Java 和 Python 项目。

## 快速开始

### 命令行使用

```bash
# 扫描整个项目
python scripts/code-reviewer.py /path/to/project

# 扫描指定文件
python scripts/code-reviewer.py /path/to/file.java

# 指定语言
python scripts/code-reviewer.py /path/to/project --language java

# 输出 JSON 格式
python scripts/code-reviewer.py /path/to/project --output json

# 保存到文件
python scripts/code-reviewer.py /path/to/project -o report.md

# 排除目录
python scripts/code-reviewer.py /path/to/project --exclude node_modules,build,dist
```

### IDEA 集成

#### 一键安装（推荐）

```bash
# macOS/Linux
chmod +x idea-plugin/install-idea-plugin.sh
./idea-plugin/install-idea-plugin.sh

# Windows (Git Bash)
bash idea-plugin/install-idea-plugin.sh
```

#### 手动安装

1. 找到 IDEA 配置目录：
   - **Windows:** `%USERPROFILE%\AppData\Roaming\JetBrains\<version>\`
   - **macOS:** `~/Library/Application Support/JetBrains/<version>/`
   - **Linux:** `~/.local/share/JetBrains/<version>/`

2. 创建 `tools` 目录（如果不存在）

3. 复制 `code-reviewer.xml` 到 `tools` 目录

4. 重启 IDEA

#### 使用方法

在 IDEA 中：
1. 右键项目或文件
2. 选择 **External Tools** → **Code Reviewer**
3. 选择扫描模式：
   - **Full Scan** - 完整扫描整个项目
   - **Security Only** - 仅安全检查
   - **Current File** - 扫描当前打开的文件

报告将保存到项目根目录。

---

## 检测规则

### 🔴 安全漏洞 (Security)

| ID | 问题 | 语言 | CWE |
|----|------|------|-----|
| JAVA-SEC-001 | SQL 注入 | Java | CWE-89 |
| JAVA-SEC-002 | 命令注入 | Java | CWE-78 |
| JAVA-SEC-003 | 路径遍历 | Java | CWE-22 |
| JAVA-SEC-004 | 硬编码敏感信息 | Java | CWE-798 |
| JAVA-SEC-005 | 不安全随机数 | Java | CWE-330 |
| JAVA-SEC-006 | XSS 漏洞 | Java | CWE-79 |
| JAVA-SEC-007 | 不安全 SSL 配置 | Java | CWE-295 |
| PY-SEC-001 | SQL 注入 | Python | CWE-89 |
| PY-SEC-002 | 命令注入 | Python | CWE-78 |
| PY-SEC-003 | 路径遍历 | Python | CWE-22 |
| PY-SEC-004 | 硬编码敏感信息 | Python | CWE-798 |
| PY-SEC-005 | 不安全反序列化 | Python | CWE-502 |
| PY-SEC-006 | eval/exec 危险使用 | Python | CWE-95 |
| PY-SEC-007 | 弱随机数 | Python | CWE-330 |
| PY-SEC-008 | SSL 验证禁用 | Python | CWE-295 |

### 🟡 代码规范 (Style)

| ID | 问题 | 语言 | 参考 |
|----|------|------|------|
| JAVA-STYLE-001 | 类名命名规范 | Java | 阿里规范 3.1.1 |
| JAVA-STYLE-002 | 方法名命名规范 | Java | 阿里规范 3.1.2 |
| JAVA-STYLE-003 | 常量命名规范 | Java | 阿里规范 3.1.3 |
| JAVA-STYLE-004 | 方法过长 | Java | 阿里规范 4.1.1 |
| JAVA-STYLE-005 | 类过长 | Java | 阿里规范 4.1.2 |
| JAVA-STYLE-006 | 缺少注释 | Java | 阿里规范 4.2.1 |
| JAVA-STYLE-007 | 魔法值 | Java | 阿里规范 4.3.1 |
| PY-STYLE-001 | PEP8 缩进问题 | Python | PEP8 E101 |
| PY-STYLE-002 | 行过长 | Python | PEP8 E501 |
| PY-STYLE-003 | 函数过长 | Python | PEP8 |
| PY-STYLE-004 | 缺少文档字符串 | Python | PEP8 D103 |
| PY-STYLE-005 | 导入顺序不规范 | Python | PEP8 E402 |
| PY-STYLE-006 | 变量命名不规范 | Python | PEP8 N806 |

### 🟢 性能问题 (Performance)

| ID | 问题 | 语言 |
|----|------|------|
| JAVA-PERF-001 | 字符串拼接性能 | Java |
| JAVA-PERF-002 | 未关闭资源 | Java |
| JAVA-PERF-003 | 低效集合操作 | Java |
| JAVA-PERF-004 | 空 catch 块 | Java |
| JAVA-PERF-005 | N+1 查询问题 | Java |
| PY-PERF-001 | 低效列表拼接 | Python |
| PY-PERF-002 | 未关闭文件 | Python |
| PY-PERF-003 | 低效成员检查 | Python |
| PY-PERF-004 | 空 except 块 | Python |
| PY-PERF-005 | 全局变量滥用 | Python |

---

## 输出格式

### Markdown 报告

```markdown
# 🔍 代码走读报告

**扫描时间:** 2026-03-18 13:54:00  
**语言:** JAVA  
**扫描文件数:** 50  
**扫描代码行数:** 10000  
**问题总数:** 15

## 📊 问题统计

### 按严重程度
| 严重程度 | 数量 |
|---------|------|
| 🔴 严重 | 2 |
| 🟠 高危 | 5 |
| 🟡 中危 | 5 |
| 🟢 低危 | 3 |

## 🚨 问题详情
...
```

### JSON 报告

```json
{
  "scan_time": "2026-03-18 13:54:00",
  "language": "java",
  "files_scanned": 50,
  "total_issues": 15,
  "statistics": {...},
  "issues": [...]
}
```

---

## 工作流集成

### CI/CD 集成

```yaml
# GitHub Actions
name: Code Review
on: [push, pull_request]

jobs:
  code-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Code Reviewer
        run: |
          python scripts/code-reviewer.py . -o report.md
      - name: Upload Report
        uses: actions/upload-artifact@v2
        with:
          name: code-review-report
          path: report.md
```

### Git Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
python scripts/code-reviewer.py . -o /tmp/review.md
if [ $? -eq 2 ]; then
    echo "❌ 发现严重或高危问题，请修复后提交"
    exit 1
fi
```

---

## 自定义规则

在脚本中添加新规则：

```python
JAVA_SECURITY_RULES = [
    {
        "id": "JAVA-SEC-XXX",
        "name": "规则名称",
        "pattern": r"正则表达式",
        "severity": Severity.HIGH,
        "type": IssueType.SECURITY,
        "message": "问题描述",
        "suggestion": "修复建议",
        "cwe": "CWE-XXX",
        "example_bad": "错误示例",
        "example_good": "正确示例"
    },
]
```

---

## 参考文档

- 详细规则说明：见 `references/rule-database.md`
- 修复指南：见 `references/fix-guides.md`
- IDEA 配置：见 `idea-plugin/code-reviewer.xml`

---

## 使用场景

- ✅ 代码提交前检查
- ✅ Pull Request 审查
- ✅ 定期安全审计
- ✅ 代码质量评估
- ✅ 新人代码指导
- ✅ 技术债务识别

---

## 限制说明

- 基于静态分析，可能漏报动态漏洞
- 正则匹配可能有误报，需人工确认
- 不检测业务逻辑问题
- 不替代人工代码审查

---

## 系统要求

- **Python:** 3.8+
- **操作系统:** Windows / macOS / Linux
- **IDE:** IntelliJ IDEA (可选，用于插件集成)

---

## 常见问题

### Q: 误报太多？
A: 可以在代码中添加注释排除特定行，或调整规则的正则表达式。

### Q: 如何排除特定目录？
A: 使用 `--exclude` 参数，如 `--exclude node_modules,build,dist`

### Q: IDEA 中找不到 External Tools？
A: 确保已重启 IDEA，配置文件已正确复制到 tools 目录。

### Q: 支持其他语言吗？
A: 目前仅支持 Java 和 Python，可通过添加规则扩展支持。
