# 代码走读规则数据库

## 规则分类

### 安全漏洞 (Security) - 优先级最高

#### SQL 注入 (CWE-89)

**检测模式:**
- Java: `Statement` + 字符串拼接
- Python: `execute` + f-string/format/%

**错误示例:**
```java
// ❌ Java
stmt.executeQuery("SELECT * FROM users WHERE id = " + userId);
```

```python
# ❌ Python
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

**正确示例:**
```java
// ✅ Java
PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?");
ps.setInt(1, userId);
ResultSet rs = ps.executeQuery();
```

```python
# ✅ Python
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

---

#### 命令注入 (CWE-78)

**错误示例:**
```java
// ❌ Java
Runtime.getRuntime().exec("ping " + userInput);
```

```python
# ❌ Python
os.system(f"ping {host}")
```

**正确示例:**
```java
// ✅ Java
ProcessBuilder pb = new ProcessBuilder("ping", validatedInput);
pb.start();
```

```python
# ✅ Python
subprocess.run(["ping", host])
```

---

#### 路径遍历 (CWE-22)

**错误示例:**
```java
// ❌ Java
new FileInputStream("/data/" + userInput);
```

```python
# ❌ Python
open("/data/" + user_input)
```

**正确示例:**
```java
// ✅ Java
Path path = Paths.get("/data/", userInput).normalize();
if (!path.startsWith("/data/")) {
    throw new SecurityException("Invalid path");
}
new FileInputStream(path.toFile());
```

```python
# ✅ Python
from pathlib import Path
path = (Path("/data") / user_input).resolve()
if not str(path).startswith("/data"):
    raise SecurityException("Invalid path")
with open(path) as f:
    ...
```

---

#### 硬编码敏感信息 (CWE-798)

**错误示例:**
```java
// ❌ Java
String password = "admin123";
String apiKey = "sk-1234567890";
```

```python
# ❌ Python
password = "admin123"
API_KEY = "sk-1234567890"
```

**正确示例:**
```java
// ✅ Java
String password = System.getenv("DB_PASSWORD");
String apiKey = System.getProperty("api.key");
```

```python
# ✅ Python
import os
password = os.environ.get('DB_PASSWORD')
API_KEY = os.environ.get('API_KEY')
```

---

### 代码规范 (Style)

#### 命名规范

**Java:**
- 类名：PascalCase (UserService)
- 方法/变量：camelCase (getUserInfo)
- 常量：UPPER_SNAKE_CASE (MAX_RETRY_COUNT)

**Python:**
- 类名：PascalCase (UserService)
- 函数/变量：snake_case (get_user_info)
- 常量：UPPER_SNAKE_CASE (MAX_RETRY_COUNT)

---

#### 代码长度

**建议限制:**
- 方法：≤ 50 行 (Python) / ≤ 80 行 (Java)
- 类：≤ 500 行 (Python) / ≤ 1500 行 (Java)
- 文件：≤ 1000 行

---

### 性能问题 (Performance)

#### 字符串拼接

**错误示例:**
```java
// ❌ Java - O(n²)
String result = "";
for (String s : list) {
    result += s;
}
```

```python
# ❌ Python
result = ""
for s in list:
    result += s
```

**正确示例:**
```java
// ✅ Java - O(n)
StringBuilder sb = new StringBuilder();
for (String s : list) {
    sb.append(s);
}
String result = sb.toString();
```

```python
# ✅ Python
result = "".join(list)
```

---

#### 资源管理

**错误示例:**
```java
// ❌ Java
FileInputStream fis = new FileInputStream(file);
// ... 使用
// 忘记关闭
```

```python
# ❌ Python
f = open('file.txt')
data = f.read()
# 忘记关闭
```

**正确示例:**
```java
// ✅ Java - try-with-resources
try (FileInputStream fis = new FileInputStream(file)) {
    // ... 使用
} // 自动关闭
```

```python
# ✅ Python - with 语句
with open('file.txt') as f:
    data = f.read()
# 自动关闭
```

---

#### 集合操作

**低效示例:**
```java
// ❌ LinkedList 随机访问 - O(n)
LinkedList<String> list = new LinkedList<>();
String s = list.get(i);
```

```python
# ❌ list 成员检查 - O(n)
if x in [1, 2, 3, 4, 5]:
```

**高效示例:**
```java
// ✅ ArrayList 随机访问 - O(1)
ArrayList<String> list = new ArrayList<>();
String s = list.get(i);
```

```python
# ✅ set 成员检查 - O(1)
if x in {1, 2, 3, 4, 5}:
```

---

## 规则优先级

| 优先级 | 类型 | 处理时限 |
|--------|------|---------|
| P0 | 严重安全问题 | 立即修复 |
| P1 | 高危安全问题 | 24 小时内 |
| P2 | 中危问题/性能问题 | 1 周内 |
| P3 | 低危问题/规范问题 | 下次迭代 |
| P4 | 提示信息 | 可选修复 |

---

## 误报处理

### 排除特定行

**Java:**
```java
// code-reviewer: disable=JAVA-SEC-001
String sql = "SELECT * FROM users WHERE id = " + id;
// code-reviewer: enable=JAVA-SEC-001
```

**Python:**
```python
# code-reviewer: disable=PY-SEC-001
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
# code-reviewer: enable=PY-SEC-001
```

### 排除特定文件

在规则配置中添加：
```python
EXCLUDE_FILES = [
    "**/test/**",
    "**/tests/**",
    "**/*Test.java",
    "**/test_*.py",
]
```

---

## 规则扩展

### 添加新规则

```python
JAVA_SECURITY_RULES.append({
    "id": "JAVA-SEC-XXX",
    "name": "新规则名称",
    "pattern": r"正则表达式",
    "severity": Severity.HIGH,
    "type": IssueType.SECURITY,
    "message": "问题描述",
    "suggestion": "修复建议",
    "cwe": "CWE-XXX",
    "example_bad": "错误示例",
    "example_good": "正确示例"
})
```

### 自定义严重性

根据项目需求调整：
```python
# 在配置文件中
SEVERITY_OVERRIDES = {
    "JAVA-SEC-005": Severity.LOW,  # 降级
    "PY-STYLE-002": Severity.MEDIUM,  # 升级
}
```

---

*最后更新：2026-03-18*
