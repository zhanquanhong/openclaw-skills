# IDEA 插件配置指南

> Code Reviewer + Auto Tester 团队集成方案

**适用对象：** Java 开发团队  
**配置时间：** 10 分钟/人  
**维护成本：** 低

---

## 📋 目录

1. [Code Reviewer - IDEA 集成](#1-code-reviewer---idea-集成)
2. [Auto Tester - 使用方式](#2-auto-tester---使用方式)
3. [团队分发方案](#3-团队分发方案)
4. [常见问题](#4-常见问题)

---

## 1️⃣ Code Reviewer - IDEA 集成

### 方式 A：自动安装（推荐）

如果 IDEA 已安装在本机，运行：

```bash
cd /home/admin/.openclaw/workspace/skills/code-reviewer/idea-plugin
bash install-idea-plugin.sh
```

### 方式 B：手动安装

#### 步骤 1：找到 IDEA 配置目录

| 操作系统 | 配置目录 |
|---------|---------|
| **Windows** | `%USERPROFILE%\AppData\Roaming\JetBrains\<version>\` |
| **macOS** | `~/Library/Application Support/JetBrains/<version>/` |
| **Linux** | `~/.local/share/JetBrains/<version>/` |

**<version>** 示例：
- `IntelliJIdea2024.1`
- `IdeaIC2023.3`（社区版）
- `IdeaIU2024.2`（旗舰版）

#### 步骤 2：创建 tools 目录

```bash
# Linux/macOS
mkdir -p ~/.local/share/JetBrains/IntelliJIdea2024.1/tools

# Windows (PowerShell)
New-Item -ItemType Directory -Force "$env:APPDATA\JetBrains\IntelliJIdea2024.1\tools"
```

#### 步骤 3：复制配置文件

```bash
# Linux/macOS
cp /home/admin/.openclaw/workspace/skills/code-reviewer/idea-plugin/code-reviewer.xml \
   ~/.local/share/JetBrains/IntelliJIdea2024.1/tools/

# Windows (PowerShell)
Copy-Item "C:\path\to\skills\code-reviewer\idea-plugin\code-reviewer.xml" \
          "$env:APPDATA\JetBrains\IntelliJIdea2024.1\tools\"
```

#### 步骤 4：重启 IDEA

完全关闭 IDEA 后重新打开。

#### 步骤 5：验证安装

在 IDEA 中：
1. 右键任意项目或文件
2. 选择 **External Tools** → 应看到 **Code Reviewer** 子菜单
3. 包含三个选项：
   - **Code Reviewer - Full Scan** - 完整扫描整个项目
   - **Code Reviewer - Security Only** - 仅安全检查
   - **Code Reviewer - Current File** - 扫描当前打开的文件

---

### ⚙️ 自定义配置

如果脚本路径需要调整，编辑 `code-reviewer.xml`：

```xml
<!-- 修改 program 标签中的路径 -->
<program>/your/custom/path/code-reviewer.py</program>
```

**常用路径变量：**
- `$PROJECT_DIR$` - 项目根目录
- `$FilePath$` - 当前文件完整路径
- `$FileDir$` - 当前文件所在目录
- `$FileName$` - 当前文件名

---

### 📊 使用示例

#### 场景 1：提交前检查

1. 右键项目 → **External Tools** → **Code Reviewer - Full Scan**
2. 等待扫描完成（通常 10-30 秒）
3. 在项目根目录查看 `code-review-report.md`
4. 修复发现的问题后再提交

#### 场景 2：Code Review 辅助

1. 打开同事的代码文件
2. 右键 → **External Tools** → **Code Reviewer - Current File**
3. 查看 `review-report.md` 中的问题
4. 在 CR 中提出具体建议

#### 场景 3：安全审计

1. 右键项目 → **External Tools** → **Code Reviewer - Security Only**
2. 查看 `security-review-report.md`
3. 重点关注 🔴 严重和 🟠 高危问题

---

## 2️⃣ Auto Tester - 使用方式

> Auto Tester 主要通过命令行和 CI/CD 集成使用，暂无 IDEA 插件

### 方式 A：命令行使用

#### 生成测试模板

```bash
cd /home/admin/.openclaw/workspace/skills/auto-tester

# 分析项目并生成测试
python3 scripts/auto-tester.py /path/to/your/project --generate
```

#### 执行回归测试

```bash
python3 scripts/auto-tester.py /path/to/your/project \
  --execute \
  --type regression \
  --coverage \
  --output test-report.html
```

#### 执行 API 测试

```bash
python3 scripts/auto-tester.py /path/to/your/project \
  --execute \
  --type api \
  --base-url http://localhost:8080 \
  --output api-report.html
```

---

### 方式 B：CI/CD 集成

#### GitHub Actions 示例

在项目根目录创建 `.github/workflows/auto-test.yml`：

```yaml
name: Auto Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Java
        uses: actions/setup-java@v3
        with:
          java-version: '17'
          distribution: 'temurin'
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Generate Tests
        run: |
          python3 /home/admin/.openclaw/workspace/skills/auto-tester/scripts/auto-tester.py \
            . --generate
      
      - name: Run Tests
        run: |
          mvn test
          # 或 gradle test
      
      - name: Run Regression
        run: |
          python3 /home/admin/.openclaw/workspace/skills/auto-tester/scripts/auto-tester.py \
            . --execute --type regression --output test-report.html
      
      - name: Upload Report
        uses: actions/upload-artifact@v3
        with:
          name: test-report
          path: test-report.html
```

#### Jenkins Pipeline 示例

```groovy
pipeline {
    agent any
    
    stages {
        stage('Generate Tests') {
            steps {
                sh '''
                    python3 /home/admin/.openclaw/workspace/skills/auto-tester/scripts/auto-tester.py \
                        . --generate
                '''
            }
        }
        
        stage('Run Tests') {
            steps {
                sh 'mvn test'
            }
        }
        
        stage('Regression Check') {
            steps {
                sh '''
                    python3 /home/admin/.openclaw/workspace/skills/auto-tester/scripts/auto-tester.py \
                        . --execute --type regression --output test-report.html
                '''
            }
            post {
                always {
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: '.',
                        reportFiles: 'test-report.html',
                        reportName: 'Auto Test Report'
                    ])
                }
            }
        }
    }
}
```

---

### 方式 C：IDEA 外部工具（手动配置）

虽然 Auto Tester 没有预置插件，但可以手动添加到 IDEA：

#### 步骤 1：打开 IDEA 外部工具配置

**File** → **Settings** → **Tools** → **External Tools** → **+**

#### 步骤 2：添加配置

| 字段 | 值 |
|------|-----|
| **Name** | Auto Tester - Generate Tests |
| **Program** | `/usr/bin/python3` |
| **Arguments** | `/home/admin/.openclaw/workspace/skills/auto-tester/scripts/auto-tester.py --generate $ProjectFileDir$` |
| **Working directory** | `$ProjectFileDir$` |

#### 步骤 3：添加执行配置

重复步骤 1-2，创建第二个工具：

| 字段 | 值 |
|------|-----|
| **Name** | Auto Tester - Run Regression |
| **Program** | `/usr/bin/python3` |
| **Arguments** | `/home/admin/.openclaw/workspace/skills/auto-tester/scripts/auto-tester.py --execute --type regression $ProjectFileDir$` |
| **Working directory** | `$ProjectFileDir$` |

---

## 3️⃣ 团队分发方案

### 方案 A：Git 子模块（推荐）

将技能目录作为 Git 子模块添加到团队项目：

```bash
# 在项目根目录
git submodule add https://your-repo/skills.git skills
git submodule update --init
```

团队成拉取项目后自动获取技能。

### 方案 B：统一配置脚本

创建团队配置脚本 `setup-dev-env.sh`：

```bash
#!/bin/bash
# 团队开发环境配置脚本

echo "🦞 配置 Code Reviewer..."
cp skills/code-reviewer/idea-plugin/code-reviewer.xml \
   ~/.local/share/JetBrains/IntelliJIdea2024.1/tools/

echo "✅ 配置完成！请重启 IDEA"
```

团队成员运行一次即可。

### 方案 C：文档 + 自助配置

将本指南保存到团队 Wiki，成员按文档自行配置。

---

## 4️⃣ 常见问题

### Q1: IDEA 中找不到 External Tools？

**A:** 确保：
1. 已完全重启 IDEA（不是关闭窗口，是退出程序）
2. `code-reviewer.xml` 已正确复制到 `tools` 目录
3. XML 文件格式正确（可以用浏览器打开验证）

---

### Q2: 运行时报错 "python3: command not found"？

**A:** 修改 `code-reviewer.xml` 中的 program 路径：

```xml
<!-- Windows -->
<program>C:\Python39\python.exe</program>

<!-- macOS -->
<program>/usr/local/bin/python3</program>

<!-- Linux -->
<program>/usr/bin/python3</program>
```

查找 Python 路径：
```bash
which python3
```

---

### Q3: 扫描报告是乱码？

**A:** 确保 IDEA 使用 UTF-8 编码打开报告文件：
1. **File** → **Settings** → **Editor** → **File Encodings**
2. 设置 **Default encoding** 为 `UTF-8`

---

### Q4: 如何排除特定目录（如 build、target）？

**A:** 修改 `code-reviewer.xml` 的 parameters：

```xml
<parameters>--language auto --exclude build,target,node_modules --output markdown $PROJECT_DIR$</parameters>
```

---

### Q5: 团队使用不同版本的 IDEA？

**A:** 每个成员需要配置到自己 IDEA 版本的目录：
- `IntelliJIdea2023.3`
- `IntelliJIdea2024.1`
- `IntelliJIdea2024.2`

配置文件是通用的，只需复制对应版本目录。

---

### Q6: 可以在 Windows 上使用吗？

**A:** 可以！两个技能都支持全平台：
- Windows 需安装 Python 3.8+
- IDEA 配置路径使用 Windows 格式
- 脚本路径使用反斜杠或正斜杠均可

---

## 📞 技术支持

配置遇到问题？联系：
- 技能文档：`/home/admin/.openclaw/workspace/skills/*/SKILL.md`
- 示例报告：`/home/admin/.openclaw/workspace/skills/*/reports/`

---

*最后更新：2026-03-25*
