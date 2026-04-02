# 代码审查多代理系统 - 快速开始

## 🚀 5 分钟上手

### 第一步：测试运行

```bash
cd /home/admin/.openclaw/workspace

# 测试单文件审查
python scripts/code-review-multi-agent.py /path/to/your/file.java

# 测试整个项目
python scripts/code-review-multi-agent.py /path/to/your/project

# 启用多代理模式（并行执行）
python scripts/code-review-multi-agent.py /path/to/your/project --multi-agent
```

### 第二步：查看报告

报告保存在：`~/.openclaw/workspace/code-reports/`

```bash
ls -la ~/.openclaw/workspace/code-reports/

# 查看综合报告
cat ~/.openclaw/workspace/code-reports/code-review-summary.md
```

### 第三步：集成到工作流

#### IDEA 外部工具配置

1. 打开 IDEA → Settings → Tools → External Tools
2. 添加新工具：
   - **Name:** Code Review (Multi-Agent)
   - **Program:** `python`
   - **Arguments:** `scripts/code-review-multi-agent.py $FilePath$ --multi-agent`
   - **Working directory:** `$ProjectFileDir$`

3. 使用时：右键文件 → External Tools → Code Review (Multi-Agent)

#### Git Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
python /home/admin/.openclaw/workspace/scripts/code-review-multi-agent.py --staged

if [ $? -eq 2 ]; then
    echo "❌ 发现严重问题，请修复后提交"
    exit 1
fi
```

---

## 📋 常用命令

```bash
# 审查单个文件
python scripts/code-review-multi-agent.py src/main/java/com/example/UserService.java

# 审查整个模块
python scripts/code-review-multi-agent.py src/main/java/com/example/

# 只审查安全问题
python scripts/code-review-multi-agent.py . --focus security

# 多代理并行审查
python scripts/code-review-multi-agent.py . --multi-agent

# 指定输出文件名
python scripts/code-review-multi-agent.py . -o my-review.md

# 审查 PR（需要配置 GitHub Token）
python scripts/code-review-multi-agent.py --pr 123
```

---

## 🎯 多代理模式说明

### 默认模式（串行）
```
审查开始 → 安全检查 → 规范检查 → 性能分析 → 输出报告
总耗时：约 3-5 分钟
```

### 多代理模式（并行）
```
审查开始 → [安全检查 + 规范检查 + 性能分析] 同时执行 → 汇总报告
总耗时：约 1-2 分钟
```

---

## 📊 报告解读

### 问题严重程度

| 级别 | 标识 | 处理建议 |
|------|------|---------|
| 严重 | 🔴 | 立即修复，阻止发布 |
| 高危 | 🟠 | 优先修复，本周内 |
| 中危 | 🟡 | 计划修复，下次迭代 |
| 低危 | 🟢 | 有空再改 |

### 典型问题示例

**🔴 严重 - SQL 注入**
```java
// ❌ 错误
String sql = "SELECT * FROM users WHERE id = " + userId;

// ✅ 正确
PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?");
ps.setString(1, userId);
```

**🟠 高危 - 硬编码密码**
```java
// ❌ 错误
String password = "admin123";

// ✅ 正确
String password = System.getenv("DB_PASSWORD");
```

**🟡 中危 - 方法过长**
```java
// ❌ 错误：方法超过 80 行
public void processOrder() { ... 100 行代码 ... }

// ✅ 正确：拆分为多个小方法
public void processOrder() {
    validateOrder();
    calculateTotal();
    saveOrder();
    sendNotification();
}
```

---

## 🔧 配置选项

### 排除目录

创建 `.code-review-ignore` 文件：
```
node_modules/
build/
dist/
*.test.java
*.spec.js
```

### 自定义规则

编辑 `scripts/code-reviewer.py`，添加新规则：
```python
CUSTOM_RULES = [
    {
        "id": "CUSTOM-001",
        "name": "禁止使用 System.out.println",
        "pattern": r"System\.out\.println",
        "severity": "MEDIUM",
        "message": "请使用日志框架代替 System.out"
    }
]
```

---

## ❓ 常见问题

### Q: 误报太多怎么办？
A: 在代码中添加注释排除：
```java
// code-review-ignore: JAVA-STYLE-004
public void veryLongMethod() { ... }
```

### Q: 如何跳过某些检查？
A: 使用 `--focus` 参数指定只检查特定类型

### Q: 多代理模式为什么没加速？
A: 如果是小项目，串行已经很快。多代理适合大项目（>100 文件）

### Q: 如何集成到 CI/CD？
A: 参考文档中的 GitHub Actions 示例

---

## 📞 需要帮助？

遇到问题或有建议，联系：
- 文档：`docs/code-review-multi-agent.md`
- 技能目录：`skills/code-reviewer/`
