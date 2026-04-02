#!/usr/bin/env python3
"""
代码走读工具 - Code Reviewer
支持 Java/Python 代码安全漏洞、规范问题、代码质量检查
可集成到 IDEA 作为外部工具

用法:
    python code-reviewer.py <项目路径> [选项]
    
选项:
    --language java|python|auto  指定语言（默认 auto 自动检测）
    --output report.md|json      输出格式（默认 markdown）
    --rules all|security|style|performance  规则集（默认 all）
    --exclude 排除的目录（逗号分隔）
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum


# ==================== 问题严重性等级 ====================

class Severity(Enum):
    CRITICAL = "🔴 严重"
    HIGH = "🟠 高危"
    MEDIUM = "🟡 中危"
    LOW = "🟢 低危"
    INFO = "⚪ 提示"


# ==================== 问题类型 ====================

class IssueType(Enum):
    SECURITY = "安全漏洞"
    STYLE = "代码规范"
    PERFORMANCE = "性能问题"
    MAINTAINABILITY = "可维护性"
    BUG = "潜在缺陷"


# ==================== 问题定义 ====================

@dataclass
class CodeIssue:
    id: str
    type: str
    severity: str
    file: str
    line: int
    column: int
    code: str
    message: str
    suggestion: str
    cwe: str = ""
    rule_id: str = ""


# ==================== Java 规则库 ====================

JAVA_SECURITY_RULES = [
    {
        "id": "JAVA-SEC-001",
        "name": "SQL 注入漏洞",
        "pattern": r"(?:Statement|createStatement|executeQuery|executeUpdate)\s*\([^)]*\+[^)]*\)",
        "severity": Severity.CRITICAL,
        "type": IssueType.SECURITY,
        "message": "可能存在 SQL 注入漏洞，使用字符串拼接构建 SQL",
        "suggestion": "使用 PreparedStatement 和参数化查询",
        "cwe": "CWE-89",
        "example_bad": "stmt.executeQuery(\"SELECT * FROM users WHERE id = \" + userId);",
        "example_good": "PreparedStatement ps = conn.prepareStatement(\"SELECT * FROM users WHERE id = ?\"); ps.setInt(1, userId);"
    },
    {
        "id": "JAVA-SEC-002",
        "name": "命令注入漏洞",
        "pattern": r"(?:Runtime\.getRuntime|ProcessBuilder)\s*\([^)]*\+[^)]*\)",
        "severity": Severity.CRITICAL,
        "type": IssueType.SECURITY,
        "message": "可能存在命令注入漏洞，用户输入直接传递给系统命令",
        "suggestion": "避免使用 Runtime.exec，使用 ProcessBuilder 并验证输入",
        "cwe": "CWE-78",
        "example_bad": "Runtime.getRuntime().exec(\"ping \" + userInput);",
        "example_good": "ProcessBuilder pb = new ProcessBuilder(\"ping\", validatedInput);"
    },
    {
        "id": "JAVA-SEC-003",
        "name": "路径遍历漏洞",
        "pattern": r"(?:FileInputStream|FileOutputStream|Files\.(?:read|write)|Path\.of)\s*\([^)]*\+[^)]*\)",
        "severity": Severity.HIGH,
        "type": IssueType.SECURITY,
        "message": "可能存在路径遍历漏洞，用户输入直接用于文件路径",
        "suggestion": "验证文件路径，使用白名单或规范化路径",
        "cwe": "CWE-22",
        "example_bad": "new FileInputStream(\"/data/\" + userInput);",
        "example_good": "Path path = Paths.get(\"/data/\", userInput).normalize(); if (!path.startsWith(\"/data/\")) throw new SecurityException();"
    },
    {
        "id": "JAVA-SEC-004",
        "name": "硬编码敏感信息",
        "pattern": r"(?:password|passwd|pwd|secret|api[_-]?key|token|auth)\s*=\s*\"[^\"]+\"",
        "severity": Severity.HIGH,
        "type": IssueType.SECURITY,
        "message": "可能存在硬编码的敏感信息（密码、密钥等）",
        "suggestion": "使用环境变量或配置文件，将敏感信息从代码中分离",
        "cwe": "CWE-798",
        "example_bad": "String password = \"admin123\";",
        "example_good": "String password = System.getenv(\"DB_PASSWORD\");"
    },
    {
        "id": "JAVA-SEC-005",
        "name": "不安全的随机数",
        "pattern": r"\bRandom\s+\w+\s*=\s*new\s+Random\s*\(\s*\)",
        "severity": Severity.MEDIUM,
        "type": IssueType.SECURITY,
        "message": "使用 java.util.Random 生成安全相关的随机数",
        "suggestion": "安全场景使用 SecureRandom",
        "cwe": "CWE-330",
        "example_bad": "Random rand = new Random(); String token = String.valueOf(rand.nextInt());",
        "example_good": "SecureRandom rand = new SecureRandom(); byte[] token = new byte[16]; rand.nextBytes(token);"
    },
    {
        "id": "JAVA-SEC-006",
        "name": "XSS 漏洞",
        "pattern": r"(?:setInnerHTML|document\.write|appendChild\s*\([^)]*innerHTML)\s*\(",
        "severity": Severity.HIGH,
        "type": IssueType.SECURITY,
        "message": "可能存在 XSS 漏洞，未转义的用户输入直接渲染到 HTML",
        "suggestion": "对用户输入进行 HTML 转义，使用安全的方法如 textContent",
        "cwe": "CWE-79",
        "example_bad": "element.innerHTML = userInput;",
        "example_good": "element.textContent = userInput; // 或使用转义库"
    },
    {
        "id": "JAVA-SEC-007",
        "name": "不安全的 SSL 配置",
        "pattern": r"(?:setHostnameVerifier|TrustManager|SSLContext)\s*\([^)]*(?:ALLOW_ALL|TRUST_ALL|NO_VERIFY)",
        "severity": Severity.HIGH,
        "type": IssueType.SECURITY,
        "message": "禁用了 SSL/TLS 证书验证",
        "suggestion": "启用 SSL 验证，使用有效的 CA 证书",
        "cwe": "CWE-295",
        "example_bad": "HostnameVerifier allowAll = (s, sslSession) -> true;",
        "example_good": "使用默认 HostnameVerifier 或配置正确的证书"
    },
]

JAVA_STYLE_RULES = [
    {
        "id": "JAVA-STYLE-001",
        "name": "类名命名规范",
        "pattern": r"^public\s+class\s+[a-z][a-zA-Z0-9]*",
        "severity": Severity.LOW,
        "type": IssueType.STYLE,
        "message": "类名应该以大写字母开头（驼峰命名）",
        "suggestion": "使用 PascalCase 命名类，如 UserService",
        "rule_id": "阿里规范 3.1.1"
    },
    {
        "id": "JAVA-STYLE-002",
        "name": "方法名命名规范",
        "pattern": r"^\s*(?:public|private|protected)?\s*(?:static)?\s*\w+\s+[a-z][a-zA-Z0-9]*\s*\(",
        "severity": Severity.LOW,
        "type": IssueType.STYLE,
        "message": "方法名应该以小写字母开头（驼峰命名）",
        "suggestion": "使用 camelCase 命名方法，如 getUserInfo",
        "rule_id": "阿里规范 3.1.2"
    },
    {
        "id": "JAVA-STYLE-003",
        "name": "常量命名规范",
        "pattern": r"public\s+static\s+final\s+[a-z_]+\s+=",
        "severity": Severity.LOW,
        "type": IssueType.STYLE,
        "message": "常量名应该全部大写，单词间用下划线分隔",
        "suggestion": "使用 UPPER_SNAKE_CASE 命名常量，如 MAX_RETRY_COUNT",
        "rule_id": "阿里规范 3.1.3"
    },
    {
        "id": "JAVA-STYLE-004",
        "name": "方法过长",
        "pattern": r"^\s*(?:public|private|protected)?\s*(?:static)?\s*\w+\s+\w+\s*\([^)]*\)\s*\{",
        "severity": Severity.MEDIUM,
        "type": IssueType.MAINTAINABILITY,
        "message": "方法可能过长（超过 80 行）",
        "suggestion": "将长方法拆分为多个小方法，每个方法只做一件事",
        "rule_id": "阿里规范 4.1.1"
    },
    {
        "id": "JAVA-STYLE-005",
        "name": "类过长",
        "pattern": r"^public\s+class\s+\w+",
        "severity": Severity.MEDIUM,
        "type": IssueType.MAINTAINABILITY,
        "message": "类可能过长（超过 1500 行）",
        "suggestion": "将大类拆分为多个小类，遵循单一职责原则",
        "rule_id": "阿里规范 4.1.2"
    },
    {
        "id": "JAVA-STYLE-006",
        "name": "缺少注释",
        "pattern": r"^public\s+class\s+\w+",
        "severity": Severity.INFO,
        "type": IssueType.MAINTAINABILITY,
        "message": "公共类应该有 Javadoc 注释",
        "suggestion": "为公共类和方法添加 Javadoc 注释",
        "rule_id": "阿里规范 4.2.1"
    },
    {
        "id": "JAVA-STYLE-007",
        "name": "魔法值",
        "pattern": r"(?:if|while|switch)\s*\([^)]*\b(?:[0-9]{2,}|\"[^\"]+\")\b[^)]*\)",
        "severity": Severity.LOW,
        "type": IssueType.MAINTAINABILITY,
        "message": "代码中存在魔法值（硬编码的数字或字符串）",
        "suggestion": "将魔法值定义为有意义的常量",
        "rule_id": "阿里规范 4.3.1"
    },
]

JAVA_PERFORMANCE_RULES = [
    {
        "id": "JAVA-PERF-001",
        "name": "字符串拼接性能",
        "pattern": r"\+\s*\"[^\"]*\"\s*\+\s*\"[^\"]*\"\s*\+",
        "severity": Severity.MEDIUM,
        "type": IssueType.PERFORMANCE,
        "message": "循环中使用 + 拼接字符串效率低",
        "suggestion": "使用 StringBuilder 或 StringBuffer 进行字符串拼接",
        "example_bad": "String result = \"\"; for (String s : list) { result += s; }",
        "example_good": "StringBuilder sb = new StringBuilder(); for (String s : list) { sb.append(s); }"
    },
    {
        "id": "JAVA-PERF-002",
        "name": "未关闭资源",
        "pattern": r"(?:FileInputStream|FileOutputStream|BufferedReader|Connection)\s+\w+\s*=\s*new",
        "severity": Severity.HIGH,
        "type": IssueType.BUG,
        "message": "资源可能未正确关闭，导致资源泄露",
        "suggestion": "使用 try-with-resources 自动关闭资源",
        "cwe": "CWE-404",
        "example_bad": "FileInputStream fis = new FileInputStream(file); // 手动关闭",
        "example_good": "try (FileInputStream fis = new FileInputStream(file)) { ... }"
    },
    {
        "id": "JAVA-PERF-003",
        "name": "低效的集合操作",
        "pattern": r"(?:ArrayList|LinkedList|HashMap)\s*\([^)]*\)\s*\.(?:get|contains)\s*\(",
        "severity": Severity.LOW,
        "type": IssueType.PERFORMANCE,
        "message": "可能存在低效的集合操作",
        "suggestion": "根据场景选择合适的集合类型，避免在 LinkedList 中随机访问",
        "example_bad": "LinkedList<String> list = new LinkedList<>(); String s = list.get(i);",
        "example_good": "ArrayList<String> list = new ArrayList<>(); String s = list.get(i);"
    },
    {
        "id": "JAVA-PERF-004",
        "name": "空 catch 块",
        "pattern": r"}\s*catch\s*\([^)]*\)\s*{\s*}",
        "severity": Severity.HIGH,
        "type": IssueType.BUG,
        "message": "空的 catch 块会吞掉异常，导致问题难以排查",
        "suggestion": "记录异常日志或重新抛出异常",
        "example_bad": "try { ... } catch (Exception e) {}",
        "example_good": "try { ... } catch (Exception e) { log.error(\"Error\", e); }"
    },
    {
        "id": "JAVA-PERF-005",
        "name": "N+1 查询问题",
        "pattern": r"(?:for|while)\s*\([^)]*\)\s*\{[^}]*executeQuery",
        "severity": Severity.MEDIUM,
        "type": IssueType.PERFORMANCE,
        "message": "循环中执行数据库查询，可能导致 N+1 问题",
        "suggestion": "使用批量查询或 JOIN 优化",
        "example_bad": "for (User u : users) { stmt.executeQuery(\"SELECT * FROM orders WHERE user_id = \" + u.id); }",
        "example_good": "SELECT * FROM orders WHERE user_id IN (...)"
    },
]


# ==================== Python 规则库 ====================

PYTHON_SECURITY_RULES = [
    {
        "id": "PY-SEC-001",
        "name": "SQL 注入漏洞",
        "pattern": r"(?:execute|cursor\.execute)\s*\([^)]*(?:\%|\.format|f['\"]|\+)[^)]*(?:SELECT|INSERT|UPDATE|DELETE)",
        "severity": Severity.CRITICAL,
        "type": IssueType.SECURITY,
        "message": "可能存在 SQL 注入漏洞，使用字符串格式化构建 SQL",
        "suggestion": "使用参数化查询",
        "cwe": "CWE-89",
        "example_bad": "cursor.execute(f\"SELECT * FROM users WHERE id = {user_id}\")",
        "example_good": "cursor.execute(\"SELECT * FROM users WHERE id = %s\", (user_id,))"
    },
    {
        "id": "PY-SEC-002",
        "name": "命令注入漏洞",
        "pattern": r"(?:os\.system|subprocess\.(?:call|run|Popen)|os\.popen)\s*\([^)]*(?:\%|\.format|f['\"]|\+)",
        "severity": Severity.CRITICAL,
        "type": IssueType.SECURITY,
        "message": "可能存在命令注入漏洞，用户输入直接传递给系统命令",
        "suggestion": "使用 subprocess 的列表参数形式，避免 shell=True",
        "cwe": "CWE-78",
        "example_bad": "os.system(f\"ping {host}\")",
        "example_good": "subprocess.run([\"ping\", host])"
    },
    {
        "id": "PY-SEC-003",
        "name": "路径遍历漏洞",
        "pattern": r"(?:open|Path|os\.path\.join)\s*\([^)]*(?:\.\./|\.\.\\\\|\$|\{)",
        "severity": Severity.HIGH,
        "type": IssueType.SECURITY,
        "message": "可能存在路径遍历漏洞",
        "suggestion": "验证文件路径，使用 pathlib 并规范化路径",
        "cwe": "CWE-22",
        "example_bad": "open(\"/data/\" + user_input)",
        "example_good": "from pathlib import Path; path = (Path(\"/data\") / user_input).resolve()"
    },
    {
        "id": "PY-SEC-004",
        "name": "硬编码敏感信息",
        "pattern": r"(?:password|passwd|pwd|secret|api[_-]?key|token|auth)\s*=\s*['\"][^'\"]+['\"]",
        "severity": Severity.HIGH,
        "type": IssueType.SECURITY,
        "message": "可能存在硬编码的敏感信息",
        "suggestion": "使用环境变量或配置文件",
        "cwe": "CWE-798",
        "example_bad": "password = \"admin123\"",
        "example_good": "import os; password = os.environ.get('PASSWORD')"
    },
    {
        "id": "PY-SEC-005",
        "name": "不安全的反序列化",
        "pattern": r"\bpickle\.(?:load|loads)\s*\(",
        "severity": Severity.HIGH,
        "type": IssueType.SECURITY,
        "message": "使用 pickle 加载不可信数据可能导致代码执行",
        "suggestion": "避免使用 pickle 处理不可信数据，使用 JSON",
        "cwe": "CWE-502",
        "example_bad": "data = pickle.load(untrusted_file)",
        "example_good": "import json; data = json.load(file)"
    },
    {
        "id": "PY-SEC-006",
        "name": "eval/exec 危险使用",
        "pattern": r"\b(?:eval|exec)\s*\(",
        "severity": Severity.HIGH,
        "type": IssueType.SECURITY,
        "message": "使用 eval/exec 可能执行恶意代码",
        "suggestion": "避免使用 eval/exec，使用 ast.literal_eval 或安全方法",
        "cwe": "CWE-95",
        "example_bad": "result = eval(user_input)",
        "example_good": "import ast; result = ast.literal_eval(user_input)"
    },
    {
        "id": "PY-SEC-007",
        "name": "弱随机数",
        "pattern": r"\brandom\.(?:random|randint|choice|shuffle)\s*\(",
        "severity": Severity.MEDIUM,
        "type": IssueType.SECURITY,
        "message": "使用伪随机数生成器，不适合安全相关用途",
        "suggestion": "安全场景使用 secrets 模块",
        "cwe": "CWE-330",
        "example_bad": "token = random.randint(100000, 999999)",
        "example_good": "import secrets; token = secrets.token_hex(16)"
    },
    {
        "id": "PY-SEC-008",
        "name": "SSL 验证禁用",
        "pattern": r"(?:requests\.(?:get|post)|urlopen)\s*\([^)]*verify\s*=\s*False",
        "severity": Severity.HIGH,
        "type": IssueType.SECURITY,
        "message": "禁用了 SSL/TLS 证书验证",
        "suggestion": "启用 SSL 验证",
        "cwe": "CWE-295",
        "example_bad": "requests.get(url, verify=False)",
        "example_good": "requests.get(url, verify=True)"
    },
]

PYTHON_STYLE_RULES = [
    {
        "id": "PY-STYLE-001",
        "name": "PEP8 缩进问题",
        "pattern": r"^(    )*\t",
        "severity": Severity.LOW,
        "type": IssueType.STYLE,
        "message": "使用 Tab 缩进，不符合 PEP8 规范",
        "suggestion": "使用 4 个空格进行缩进",
        "rule_id": "PEP8 E101"
    },
    {
        "id": "PY-STYLE-002",
        "name": "行过长",
        "pattern": r"^.{120,}$",
        "severity": Severity.LOW,
        "type": IssueType.STYLE,
        "message": "行超过 120 个字符",
        "suggestion": "将长行拆分为多行",
        "rule_id": "PEP8 E501"
    },
    {
        "id": "PY-STYLE-003",
        "name": "函数过长",
        "pattern": r"^def\s+\w+\s*\(",
        "severity": Severity.MEDIUM,
        "type": IssueType.MAINTAINABILITY,
        "message": "函数可能过长（超过 50 行）",
        "suggestion": "将长函数拆分为多个小函数",
        "rule_id": "PEP8"
    },
    {
        "id": "PY-STYLE-004",
        "name": "缺少文档字符串",
        "pattern": r"^def\s+\w+\s*\([^)]*\)\s*:",
        "severity": Severity.INFO,
        "type": IssueType.MAINTAINABILITY,
        "message": "公共函数应该有文档字符串",
        "suggestion": "为函数添加 docstring",
        "rule_id": "PEP8 D103"
    },
    {
        "id": "PY-STYLE-005",
        "name": "导入顺序不规范",
        "pattern": r"^import\s+\w+.*\nfrom\s+\w+",
        "severity": Severity.LOW,
        "type": IssueType.STYLE,
        "message": "导入顺序不符合规范",
        "suggestion": "按标准库、第三方库、本地模块顺序导入",
        "rule_id": "PEP8 E402"
    },
    {
        "id": "PY-STYLE-006",
        "name": "变量命名不规范",
        "pattern": r"^\s*(?:[A-Z]{2,}|[a-z][A-Z])\s*=",
        "severity": Severity.LOW,
        "type": IssueType.STYLE,
        "message": "变量命名不符合 snake_case 规范",
        "suggestion": "使用 snake_case 命名变量",
        "rule_id": "PEP8 N806"
    },
]

PYTHON_PERFORMANCE_RULES = [
    {
        "id": "PY-PERF-001",
        "name": "低效的列表拼接",
        "pattern": r"(?:for|while)\s+.*:\s*\n\s+.*\+=\s*\[",
        "severity": Severity.MEDIUM,
        "type": IssueType.PERFORMANCE,
        "message": "循环中使用 += 拼接列表效率低",
        "suggestion": "使用列表推导式或 append",
        "example_bad": "result = []; for i in range(n): result += [i]",
        "example_good": "result = [i for i in range(n)]"
    },
    {
        "id": "PY-PERF-002",
        "name": "未关闭文件",
        "pattern": r"(?:open|io\.open)\s*\([^)]*\)(?!\s*with)",
        "severity": Severity.HIGH,
        "type": IssueType.BUG,
        "message": "文件可能未正确关闭",
        "suggestion": "使用 with 语句自动管理文件",
        "example_bad": "f = open('file.txt'); data = f.read()",
        "example_good": "with open('file.txt') as f: data = f.read()"
    },
    {
        "id": "PY-PERF-003",
        "name": "低效的成员检查",
        "pattern": r"(?:if|while).*in\s+\[",
        "severity": Severity.LOW,
        "type": IssueType.PERFORMANCE,
        "message": "使用 list 进行成员检查效率低（O(n)）",
        "suggestion": "使用 set 进行成员检查（O(1)）",
        "example_bad": "if x in [1, 2, 3, 4, 5]:",
        "example_good": "if x in {1, 2, 3, 4, 5}:"
    },
    {
        "id": "PY-PERF-004",
        "name": "空 except 块",
        "pattern": r"except\s*:",
        "severity": Severity.HIGH,
        "type": IssueType.BUG,
        "message": "空的 except 块会吞掉所有异常",
        "suggestion": "捕获特定异常并记录日志",
        "example_bad": "try: ... except: pass",
        "example_good": "try: ... except SpecificError as e: log.error(e)"
    },
    {
        "id": "PY-PERF-005",
        "name": "全局变量滥用",
        "pattern": r"^\s*global\s+\w+",
        "severity": Severity.MEDIUM,
        "type": IssueType.MAINTAINABILITY,
        "message": "滥用全局变量会降低代码可维护性",
        "suggestion": "使用类或函数参数传递状态",
        "rule_id": "PEP8"
    },
]


# ==================== 代码分析器 ====================

class CodeAnalyzer:
    def __init__(self, language: str = "auto"):
        self.language = language
        self.issues: List[CodeIssue] = []
        self.files_scanned = 0
        self.lines_scanned = 0
        
    def get_file_extension(self) -> str:
        """获取文件扩展名"""
        if self.language == "java":
            return ".java"
        elif self.language == "python":
            return ".py"
        return ""
    
    def get_rules(self, rule_type: str) -> List[Dict]:
        """获取规则列表"""
        if self.language == "java":
            if rule_type == "security":
                return JAVA_SECURITY_RULES
            elif rule_type == "style":
                return JAVA_STYLE_RULES
            elif rule_type == "performance":
                return JAVA_PERFORMANCE_RULES
        elif self.language == "python":
            if rule_type == "security":
                return PYTHON_SECURITY_RULES
            elif rule_type == "style":
                return PYTHON_STYLE_RULES
            elif rule_type == "performance":
                return PYTHON_PERFORMANCE_RULES
        return []
    
    def scan_file(self, file_path: Path, rules: List[Dict]) -> List[CodeIssue]:
        """扫描单个文件"""
        issues = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            self.files_scanned += 1
            self.lines_scanned += len(lines)
            content = ''.join(lines)
            
            for rule in rules:
                pattern = rule['pattern']
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line, re.IGNORECASE if rule['type'] != IssueType.STYLE else 0):
                        # 排除注释
                        if self.is_comment(line):
                            continue
                        
                        issues.append(CodeIssue(
                            id=f"{rule['id']}-{i}",
                            type=rule['type'].value,
                            severity=rule['severity'].value,
                            file=str(file_path),
                            line=i,
                            column=0,
                            code=line.strip()[:100],
                            message=rule['message'],
                            suggestion=rule['suggestion'],
                            cwe=rule.get('cwe', ''),
                            rule_id=rule.get('rule_id', '')
                        ))
        except Exception as e:
            print(f"  ⚠️  无法读取文件：{file_path} - {e}")
        
        return issues
    
    def is_comment(self, line: str) -> bool:
        """判断是否为注释"""
        stripped = line.strip()
        if self.language == "java":
            return stripped.startswith('//') or stripped.startswith('*') or stripped.startswith('/*')
        elif self.language == "python":
            return stripped.startswith('#')
        return False
    
    def scan_directory(self, dir_path: Path, exclude_dirs: List[str] = None) -> List[CodeIssue]:
        """扫描目录"""
        if exclude_dirs is None:
            exclude_dirs = ['node_modules', '.git', 'build', 'dist', 'venv', '__pycache__', '.idea', 'target']
        
        all_issues = []
        ext = self.get_file_extension()
        
        print(f"🔍 开始扫描 {dir_path} (语言：{self.language})")
        
        for file_path in dir_path.rglob(f"*{ext}"):
            # 排除目录
            if any(exclude in str(file_path) for exclude in exclude_dirs):
                continue
            
            print(f"  📄 扫描：{file_path.relative_to(dir_path)}")
            
            # 获取所有规则
            all_rules = []
            for rule_type in ["security", "style", "performance"]:
                all_rules.extend(self.get_rules(rule_type))
            
            # 扫描文件
            issues = self.scan_file(file_path, all_rules)
            all_issues.extend(issues)
        
        return all_issues
    
    def analyze(self, path: str, exclude_dirs: List[str] = None) -> Dict:
        """执行分析"""
        target_path = Path(path)
        
        if not target_path.exists():
            raise ValueError(f"路径不存在：{path}")
        
        # 自动检测语言
        if self.language == "auto":
            if (target_path / "pom.xml").exists() or (target_path / "build.gradle").exists():
                self.language = "java"
            elif (target_path / "requirements.txt").exists() or (target_path / "setup.py").exists():
                self.language = "python"
            elif target_path.suffix == ".java":
                self.language = "java"
            elif target_path.suffix == ".py":
                self.language = "python"
            else:
                # 根据文件数量判断
                java_files = len(list(target_path.rglob("*.java")))
                python_files = len(list(target_path.rglob("*.py")))
                self.language = "java" if java_files >= python_files else "python"
            
            print(f"🔍 自动检测语言：{self.language}")
        
        # 执行扫描
        if target_path.is_file():
            all_rules = []
            for rule_type in ["security", "style", "performance"]:
                all_rules.extend(self.get_rules(rule_type))
            self.issues = self.scan_file(target_path, all_rules)
        else:
            self.issues = self.scan_directory(target_path, exclude_dirs)
        
        # 生成报告
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """生成报告"""
        severity_order = {Severity.CRITICAL.value: 0, Severity.HIGH.value: 1, 
                         Severity.MEDIUM.value: 2, Severity.LOW.value: 3, Severity.INFO.value: 4}
        
        # 排序
        sorted_issues = sorted(self.issues, key=lambda i: severity_order.get(i.severity, 5))
        
        # 统计
        stats = {}
        for issue in self.issues:
            stats[issue.severity] = stats.get(issue.severity, 0) + 1
        
        by_type = {}
        for issue in self.issues:
            by_type[issue.type] = by_type.get(issue.type, 0) + 1
        
        return {
            "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "language": self.language,
            "files_scanned": self.files_scanned,
            "lines_scanned": self.lines_scanned,
            "total_issues": len(self.issues),
            "statistics": stats,
            "by_type": by_type,
            "issues": [asdict(i) for i in sorted_issues]
        }


# ==================== 报告生成器 ====================

def generate_markdown_report(report: Dict) -> str:
    """生成 Markdown 报告"""
    md = f"""# 🔍 代码走读报告

**扫描时间:** {report['scan_time']}  
**语言:** {report['language'].upper()}  
**扫描文件数:** {report['files_scanned']}  
**扫描代码行数:** {report['lines_scanned']}  
**问题总数:** {report['total_issues']}

---

## 📊 问题统计

### 按严重程度

| 严重程度 | 数量 |
|---------|------|
| 🔴 严重 | {report['statistics'].get('🔴 严重', 0)} |
| 🟠 高危 | {report['statistics'].get('🟠 高危', 0)} |
| 🟡 中危 | {report['statistics'].get('🟡 中危', 0)} |
| 🟢 低危 | {report['statistics'].get('🟢 低危', 0)} |
| ⚪ 提示 | {report['statistics'].get('⚪ 提示', 0)} |

### 按问题类型

| 类型 | 数量 |
|------|------|
"""
    
    for issue_type, count in report['by_type'].items():
        md += f"| {issue_type} | {count} |\n"
    
    md += "\n---\n\n## 🚨 问题详情\n\n"
    
    if not report['issues']:
        md += "✅ **恭喜！未发现任何问题！**\n\n"
    else:
        # 按文件分组
        by_file = {}
        for issue in report['issues']:
            file = issue['file']
            if file not in by_file:
                by_file[file] = []
            by_file[file].append(issue)
        
        for file, issues in by_file.items():
            md += f"### 📄 {file}\n\n"
            
            for issue in issues:
                md += f"#### {issue['severity']} [{issue['type']}] {issue['rule_id']}\n\n"
                md += f"- **位置:** 第 {issue['line']} 行\n"
                if issue.get('cwe'):
                    md += f"- **CWE:** {issue['cwe']}\n"
                md += f"- **问题:** {issue['message']}\n"
                md += f"- **代码:**\n```java\n{issue['code']}\n```\n" if report['language'] == 'java' else f"```python\n{issue['code']}\n```\n"
                md += f"- **建议:** {issue['suggestion']}\n\n"
                md += "---\n\n"
    
    md += """## ✅ 改进建议

### 安全方面
1. 优先修复所有严重和高危安全问题
2. 使用参数化查询防止 SQL 注入
3. 避免硬编码敏感信息
4. 正确验证和清理用户输入

### 代码规范
1. 遵循命名规范（类名 PascalCase，方法/变量 camelCase/snake_case）
2. 为公共类和方法添加文档注释
3. 避免魔法值，使用有意义的常量

### 性能优化
1. 使用 StringBuilder 拼接字符串
2. 使用 try-with-resources/with 语句管理资源
3. 选择合适的集合类型
4. 避免 N+1 查询问题

---

*报告由 Code Reviewer 生成*
"""
    
    return md


def generate_json_report(report: Dict) -> str:
    """生成 JSON 报告"""
    return json.dumps(report, indent=2, ensure_ascii=False)


# ==================== 主函数 ====================

def main():
    parser = argparse.ArgumentParser(description='代码走读工具 - Code Reviewer')
    parser.add_argument('path', help='要扫描的项目路径或文件')
    parser.add_argument('--language', choices=['java', 'python', 'auto'], default='auto',
                       help='指定语言（默认 auto 自动检测）')
    parser.add_argument('--output', choices=['markdown', 'json'], default='markdown',
                       help='输出格式（默认 markdown）')
    parser.add_argument('--output-file', '-o', help='输出文件路径（默认输出到控制台）')
    parser.add_argument('--exclude', help='排除的目录（逗号分隔）')
    
    args = parser.parse_args()
    
    # 解析排除目录
    exclude_dirs = args.exclude.split(',') if args.exclude else None
    
    # 创建分析器
    analyzer = CodeAnalyzer(args.language)
    
    # 执行分析
    try:
        report = analyzer.analyze(args.path, exclude_dirs)
    except Exception as e:
        print(f"❌ 分析失败：{e}")
        sys.exit(1)
    
    # 生成报告
    if args.output == 'json':
        output = generate_json_report(report)
    else:
        output = generate_markdown_report(report)
    
    # 输出报告
    if args.output_file:
        with open(args.output_file, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"✅ 报告已保存：{args.output_file}")
    else:
        print(output)
    
    # 退出码（有问题则返回非零）
    if report['statistics'].get('🔴 严重', 0) > 0 or report['statistics'].get('🟠 高危', 0) > 0:
        print("\n⚠️  发现严重或高危问题，建议立即修复!")
        sys.exit(2)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
