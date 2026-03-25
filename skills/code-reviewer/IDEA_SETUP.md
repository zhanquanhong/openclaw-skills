# Code Reviewer IDEA 集成完整指南

> 详细配置步骤、验证方法、常见问题排查和使用技巧

**适用版本:** IntelliJ IDEA 2020.1+ (Ultimate/Community)  
**更新时间:** 2026-03-18

---

## 📋 目录

1. [三种集成方式](#三种集成方式)
2. [方式一：一键安装脚本](#方式一一键安装脚本)
3. [方式二：手动配置](#方式二手动配置)
4. [方式三：IDEA 内部配置](#方式三idea-内部配置)
5. [验证安装](#验证安装)
6. [常见问题排查](#常见问题排查)
7. [使用技巧](#使用技巧)
8. [卸载方法](#卸载方法)

---

## 三种集成方式

| 方式 | 难度 | 灵活性 | 推荐场景 |
|------|------|--------|---------|
| 一键安装脚本 | ⭐ 简单 | ⭐⭐ 中等 | 新手首选 |
| 手动配置 | ⭐⭐ 中等 | ⭐⭐⭐ 高 | 脚本失败时 |
| IDEA 内部配置 | ⭐⭐⭐ 复杂 | ⭐⭐⭐⭐ 最高 | 需要自定义 |

---

## 方式一：一键安装脚本

### Windows (Git Bash)

```bash
# 1. 打开 Git Bash
# 2. 进入技能目录
cd /home/admin/.openclaw/workspace/skills/code-reviewer

# 3. 运行安装脚本
bash idea-plugin/install-idea-plugin.sh
```

### macOS / Linux

```bash
# 1. 打开终端
cd /home/admin/.openclaw/workspace/skills/code-reviewer

# 2. 添加执行权限并运行
chmod +x idea-plugin/install-idea-plugin.sh
./idea-plugin/install-idea-plugin.sh
```

### 安装成功输出示例

```
🦞 Code Reviewer - IDEA 插件安装
================================
📱 检测到操作系统：mac
📂 IDEA 配置目录：/Users/username/Library/Application Support/JetBrains
✨ 找到 IDEA 版本：IntelliJIdea2024.1
📁 创建 tools 目录：.../IntelliJIdea2024.1/tools
📋 复制配置文件...

✅ 安装完成！

📝 使用说明：
1. 重启 IntelliJ IDEA
2. 在项目中右键 → External Tools → Code Reviewer
3. 选择扫描模式：
   - Full Scan: 扫描整个项目
   - Security Only: 仅安全检查
   - Current File: 扫描当前文件

📄 报告将保存到项目根目录
```

### 安装失败处理

如果脚本失败，会显示手动安装步骤：

```
⚠️  未找到 IDEA 安装，请手动配置

手动安装步骤：
1. 找到 IDEA 配置目录：
   - Windows: %USERPROFILE%\AppData\Roaming\JetBrains\<version>\
   - macOS: ~/Library/Application Support/JetBrains/<version>/
   - Linux: ~/.local/share/JetBrains/<version>/

2. 创建 tools 目录（如果不存在）
3. 复制 code-reviewer.xml 到 tools 目录
4. 重启 IDEA
```

---

## 方式二：手动配置

### 步骤 1：找到 IDEA 配置目录

#### Windows

```
%USERPROFILE%\AppData\Roaming\JetBrains\<版本>\

示例：
C:\Users\YourName\AppData\Roaming\JetBrains\IntelliJIdea2024.1\
```

**快速访问方法：**
1. 按 `Win + R`
2. 输入 `%APPDATA%\JetBrains`
3. 回车打开目录
4. 找到对应的 IDEA 版本文件夹

#### macOS

```
~/Library/Application Support/JetBrains/<版本>/

示例：
/Users/username/Library/Application Support/JetBrains/IntelliJIdea2024.1/
```

**快速访问方法：**
1. 打开 Finder
2. 按 `Cmd + Shift + G`
3. 输入 `~/Library/Application Support/JetBrains/`
4. 找到对应的 IDEA 版本文件夹

#### Linux

```
~/.local/share/JetBrains/<版本>/

示例：
/home/username/.local/share/JetBrains/IntelliJIdea2024.1/
```

**快速访问方法：**
```bash
cd ~/.local/share/JetBrains/
ls -la  # 查看版本目录
```

### 步骤 2：创建 tools 目录

#### Windows (PowerShell)

```powershell
cd "$env:APPDATA\JetBrains\IntelliJIdea2024.1\"
New-Item -ItemType Directory -Force -Path tools
```

#### macOS / Linux

```bash
cd ~/Library/Application\ Support/JetBrains/IntelliJIdea2024.1/
mkdir -p tools
```

### 步骤 3：复制配置文件

从技能目录复制 `code-reviewer.xml` 到 tools 目录：

#### Windows (PowerShell)

```powershell
Copy-Item "C:\path\to\code-reviewer\idea-plugin\code-reviewer.xml" `
          "$env:APPDATA\JetBrains\IntelliJIdea2024.1\tools\"
```

#### macOS / Linux

```bash
cp /path/to/code-reviewer/idea-plugin/code-reviewer.xml \
   ~/Library/Application\ Support/JetBrains/IntelliJIdea2024.1/tools/
```

### 步骤 4：修改配置路径（重要）

编辑 `code-reviewer.xml`，修改 `<program>` 路径为实际位置：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<toolSet name="Code Reviewer">
  <tool name="Code Reviewer - Full Scan" ...>
    <!-- 修改这里 - Windows 示例 -->
    <program>C:/Users/YourName/.openclaw/workspace/skills/code-reviewer/scripts/code-reviewer.py</program>
    
    <!-- 修改这里 - macOS/Linux 示例 -->
    <program>/home/admin/.openclaw/workspace/skills/code-reviewer/scripts/code-reviewer.py</program>
    
    <parameters>--language auto --output markdown --output-file $PROJECT_DIR$/code-review-report.md $PROJECT_DIR$</parameters>
    <workingDirectory>$PROJECT_DIR$</workingDirectory>
  </tool>
</toolSet>
```

### 步骤 5：重启 IDEA

完全关闭 IDEA（不是最小化），然后重新打开。

---

## 方式三：IDEA 内部配置（最灵活）

### 步骤 1：打开 External Tools 配置

#### Windows / Linux

1. 点击菜单 `File` → `Settings`
2. 左侧导航：`Tools` → `External Tools`

#### macOS

1. 点击菜单 `IntelliJ IDEA` → `Preferences`
2. 左侧导航：`Tools` → `External Tools`

**快捷键：**
- Windows/Linux: `Ctrl + Alt + S`
- macOS: `Cmd + ,`

### 步骤 2：添加新工具

点击工具列表右上角的 `+` 号，添加以下配置：

#### 配置 1：Full Scan（完整扫描）

```
Name: Code Reviewer - Full Scan
Description: 代码走读 - 完整扫描整个项目
Program: /home/admin/.openclaw/workspace/skills/code-reviewer/scripts/code-reviewer.py
Arguments: --language auto --output markdown --output-file $PROJECT_DIR$/code-review-report.md $PROJECT_DIR$
Working directory: $PROJECT_DIR$
```

**字段说明：**
| 字段 | 说明 | 示例 |
|------|------|------|
| Name | 工具名称（显示在菜单中） | Code Reviewer - Full Scan |
| Description | 工具描述 | 代码走读 - 完整扫描整个项目 |
| Program | Python 脚本路径 | `/path/to/code-reviewer.py` |
| Arguments | 命令行参数 | `--language auto ...` |
| Working directory | 工作目录 | `$PROJECT_DIR$` |

**宏变量：**
| 宏 | 说明 |
|----|------|
| `$PROJECT_DIR$` | 项目根目录 |
| `$FilePath$` | 当前文件完整路径 |
| `$FileDir$` | 当前文件所在目录 |
| `$FileName$` | 当前文件名 |

#### 配置 2：Current File（当前文件）

```
Name: Code Reviewer - Current File
Description: 代码走读 - 当前文件
Program: /home/admin/.openclaw/workspace/skills/code-reviewer/scripts/code-reviewer.py
Arguments: --language auto --output markdown --output-file $FileDir$/review-report.md $FilePath$
Working directory: $FileDir$
```

#### 配置 3：Security Only（仅安全检查）

```
Name: Code Reviewer - Security Only
Description: 代码走读 - 仅安全检查
Program: /home/admin/.openclaw/workspace/skills/code-reviewer/scripts/code-reviewer.py
Arguments: --language auto --output markdown --output-file $PROJECT_DIR$/security-report.md $PROJECT_DIR$
Working directory: $PROJECT_DIR$
```

### 步骤 3：指定 Python 解释器（重要）

如果系统有多个 Python 版本，需要指定 Python 3.8+：

#### 找到 Python 路径

```bash
# macOS/Linux
which python3
# 输出：/usr/bin/python3 或 /opt/homebrew/bin/python3

# Windows
where python
# 输出：C:\Python39\python.exe
```

#### 修改 Program 配置

**方式 A：直接指定 Python**

```
Program: /usr/bin/python3  # macOS/Linux
Program: C:\Python39\python.exe  # Windows

Arguments: /path/to/code-reviewer.py --language auto ...
```

**方式 B：使用脚本 shebang（推荐）**

确保脚本第一行有正确的 shebang：
```python
#!/usr/bin/env python3
```

然后 Program 直接指向脚本：
```
Program: /path/to/code-reviewer.py
```

### 步骤 4：测试配置

1. 点击 `OK` 保存配置
2. 在配置列表中选中刚添加的工具
3. 点击 `Test` 按钮（如果有）
4. 查看是否报错

### 步骤 5：添加到右键菜单（可选）

在 External Tools 配置界面：
1. 选中工具
2. 勾选 `Show in Editor menu`（编辑器右键菜单）
3. 勾选 `Show in Project View menu`（项目视图右键菜单）
4. 勾选 `Show in Favorites menu`（收藏夹菜单）

---

## 验证安装

### 验证 1：检查配置是否生效

1. 打开任意 Java 或 Python 项目
2. 在项目视图中右键任意文件
3. 查看菜单底部是否有 **External Tools** 选项
4. 展开后应看到 **Code Reviewer - Full Scan** 等选项

### 验证 2：测试运行

1. 右键项目根目录
2. 选择 **External Tools** → **Code Reviewer - Full Scan**
3. 观察 IDEA 底部状态栏

**预期输出：**
```
Running: Code Reviewer - Full Scan
🔍 开始扫描 /path/to/project (语言：JAVA)
  📄 扫描：src/main/java/com/example/Main.java
  📄 扫描：src/test/java/com/example/Test.java
✅ 报告已保存：/path/to/project/code-review-report.md
```

### 验证 3：查看生成的报告

1. 在项目视图中刷新（`Ctrl+Shift+A` → 输入 `Reload from Disk`）
2. 找到 `code-review-report.md` 文件
3. 双击打开
4. 查看是否有内容

**报告示例：**
```markdown
# 🔍 代码走读报告

**扫描时间:** 2026-03-18 14:00:00  
**语言:** JAVA  
**扫描文件数:** 50  
**问题总数:** 15

## 📊 问题统计
...
```

### 验证 4：检查日志

如果运行失败，查看 IDEA 日志：

1. `Help` → `Show Log in Explorer/Finder`
2. 打开 `idea.log`
3. 搜索 `External Tools` 或 `Code Reviewer`

---

## 常见问题排查

### Q1: 找不到 External Tools 菜单？

**可能原因：**
- 配置未保存到正确目录
- IDEA 未重启
- 配置目录权限问题

**解决方法：**

1. **确认配置目录正确**
   ```bash
   # macOS/Linux
   ls ~/Library/Application\ Support/JetBrains/IntelliJIdea2024.1/tools/
   
   # Windows
   dir %APPDATA%\JetBrains\IntelliJIdea2024.1\tools\
   ```

2. **重启 IDEA**
   - 完全关闭（不是最小化）
   - 重新打开

3. **检查文件权限**
   ```bash
   # macOS/Linux
   chmod 644 ~/Library/Application\ Support/JetBrains/IntelliJIdea2024.1/tools/code-reviewer.xml
   
   # Windows - 以管理员身份运行 IDEA
   ```

4. **手动在 IDEA 中配置**（方式三）

---

### Q2: 运行时报错 "Permission denied"？

**可能原因：**
- 脚本没有执行权限
- 工作目录没有写权限

**解决方法：**

1. **添加执行权限**
   ```bash
   chmod +x /path/to/code-reviewer.py
   ```

2. **使用 Python 解释器运行**
   ```
   Program: /usr/bin/python3
   Arguments: /path/to/code-reviewer.py ...
   ```

3. **Windows - 以管理员身份运行 IDEA**
   - 右键 IDEA 图标
   - 选择 `Run as administrator`

---

### Q3: 报 "python: command not found"？

**可能原因：**
- 系统 PATH 中没有 Python
- Python 版本太旧

**解决方法：**

1. **找到 Python 路径**
   ```bash
   # macOS/Linux
   which python3
   # 输出：/usr/bin/python3
   
   # Windows
   where python
   # 输出：C:\Python39\python.exe
   ```

2. **在 IDEA 配置中使用完整路径**
   ```
   Program: /usr/bin/python3  # 而不是 python3
   Arguments: /path/to/code-reviewer.py ...
   ```

3. **检查 Python 版本**
   ```bash
   python3 --version
   # 应显示 Python 3.8+
   ```

4. **Windows - 添加 Python 到 PATH**
   - 右键 `此电脑` → `属性`
   - `高级系统设置` → `环境变量`
   - 编辑 `Path`，添加 Python 安装目录

---

### Q4: 扫描后没有生成报告？

**可能原因：**
- 输出目录没有写权限
- 脚本执行失败
- 参数路径错误

**解决方法：**

1. **手动测试命令**
   ```bash
   cd /path/to/project
   python3 /path/to/code-reviewer.py . -o test-report.md
   ```

2. **检查 IDEA 运行日志**
   - 运行工具后，查看 IDEA 底部窗口
   - 是否有错误信息

3. **检查输出目录权限**
   ```bash
   # 尝试在项目根目录创建文件
   touch /path/to/project/test-write.txt
   ```

4. **使用绝对路径**
   修改 Arguments：
   ```
   --output-file /tmp/code-review-report.md
   ```

---

### Q5: 扫描结果全是误报？

**可能原因：**
- 规则匹配了示例代码
- 需要排除测试目录

**解决方法：**

1. **排除测试目录**
   修改 Arguments：
   ```
   --exclude node_modules,build,dist,test,tests,**/*Test.java
   ```

2. **在代码中添加排除注释**
   ```java
   // code-reviewer: disable=JAVA-SEC-001
   String sql = "SELECT * FROM users WHERE id = " + id;
   // code-reviewer: enable=JAVA-SEC-001
   ```

3. **调整规则严重性**
   编辑 `code-reviewer.py`，修改 `SEVERITY_OVERRIDES`

---

### Q6: IDEA 卡死或无响应？

**可能原因：**
- 扫描大项目耗时过长
- 内存不足

**解决方法：**

1. **增加 IDEA 内存**
   - `Help` → `Change Memory Settings`
   - 调整为 2048 MB 或更高

2. **排除大目录**
   ```
   --exclude node_modules,build,dist,.git,target
   ```

3. **使用 Current File 模式**
   只扫描当前打开的文件，而不是整个项目

---

## 使用技巧

### 技巧 1：添加到右键菜单

配置后可在以下位置使用：

1. **项目视图右键**
   - 右键项目/文件夹 → External Tools → Code Reviewer

2. **编辑器右键**
   - 代码编辑区右键 → External Tools → Code Reviewer

3. **文件右键**
   - 右键单个文件 → External Tools → Code Reviewer - Current File

### 技巧 2：设置快捷键

1. 打开快捷键配置
   - Windows/Linux: `File` → `Settings` → `Keymap`
   - macOS: `IntelliJ IDEA` → `Preferences` → `Keymap`

2. 搜索 External Tools
   - 在搜索框输入 `External Tools`
   - 展开 `External Tools` → `Code Reviewer`

3. 分配快捷键
   - 右键工具 → `Add Keyboard Shortcut`
   - 按下想要的快捷键（如 `Ctrl+Shift+R`）
   - 点击 `OK`

**推荐快捷键：**
| 工具 | Windows/Linux | macOS |
|------|--------------|-------|
| Full Scan | `Ctrl+Shift+R` | `Cmd+Shift+R` |
| Current File | `Ctrl+Alt+R` | `Cmd+Option+R` |

### 技巧 3：配置报告预览

1. **安装 Markdown 插件**
   - `Settings` → `Plugins`
   - 搜索 `Markdown`
   - 安装并重启 IDEA

2. **自动打开报告**
   修改 Arguments，添加后处理命令：
   ```bash
   --output-file report.md && open report.md  # macOS
   --output-file report.md && start report.md  # Windows
   ```

3. **使用分屏查看**
   - 双击报告文件
   - 右键 → `Split Right`（右侧分屏）

### 技巧 4：配置输出位置

修改 `Arguments` 参数改变报告位置：

```bash
# 输出到项目根目录（默认）
--output-file $PROJECT_DIR$/code-review-report.md

# 输出到指定目录
--output-file /tmp/reports/code-review.md

# 输出到文件所在目录
--output-file $FileDir$/review.md

# 输出带时间戳
--output-file $PROJECT_DIR$/review-$(date +%Y%m%d).md
```

### 技巧 5：批量扫描多个项目

创建批处理脚本：

```bash
#!/bin/bash
# scan-all.sh

PROJECTS=(
  "/path/to/project1"
  "/path/to/project2"
  "/path/to/project3"
)

for project in "${PROJECTS[@]}"; do
  echo "🔍 扫描：$project"
  python3 code-reviewer.py "$project" -o "$project/report.md"
done

echo "✅ 所有项目扫描完成！"
```

### 技巧 6：集成到 Git Hook

创建 `.git/hooks/pre-commit`：

```bash
#!/bin/bash
# 代码提交前自动检查

echo "🔍 运行代码走读..."
python3 scripts/code-reviewer.py . -o /tmp/review.md

if [ $? -eq 2 ]; then
  echo "❌ 发现严重或高危问题，请修复后提交"
  cat /tmp/review.md
  exit 1
fi

echo "✅ 代码检查通过"
exit 0
```

添加执行权限：
```bash
chmod +x .git/hooks/pre-commit
```

---

## 卸载方法

### 方式一：使用卸载脚本（如提供）

```bash
./idea-plugin/uninstall-idea-plugin.sh
```

### 方式二：手动删除

1. **找到配置目录**
   ```bash
   # macOS/Linux
   cd ~/Library/Application\ Support/JetBrains/IntelliJIdea2024.1/tools/
   
   # Windows
   cd %APPDATA%\JetBrains\IntelliJIdea2024.1\tools\
   ```

2. **删除配置文件**
   ```bash
   rm code-reviewer.xml
   ```

3. **重启 IDEA**

### 方式三：在 IDEA 中移除

1. `Settings` → `Tools` → `External Tools`
2. 选中 Code Reviewer 相关工具
3. 点击 `-` 号删除
4. 点击 `OK` 保存

---

## 附录：各版本 IDEA 配置目录

| IDEA 版本 | Windows | macOS | Linux |
|----------|---------|-------|-------|
| 2024.1 | `%APPDATA%\JetBrains\IntelliJIdea2024.1\` | `~/Library/.../IntelliJIdea2024.1/` | `~/.local/.../IntelliJIdea2024.1/` |
| 2023.3 | `%APPDATA%\JetBrains\IntelliJIdea2023.3\` | `~/Library/.../IntelliJIdea2023.3/` | `~/.local/.../IntelliJIdea2023.3/` |
| 2023.2 | `%APPDATA%\JetBrains\IntelliJIdea2023.2\` | `~/Library/.../IntelliJIdea2023.2/` | `~/.local/.../IntelliJIdea2023.2/` |
| Community | `%APPDATA%\JetBrains\IdeaIC2024.1\` | `~/Library/.../IdeaIC2024.1/` | `~/.local/.../IdeaIC2024.1/` |

**快速查找命令：**
```bash
# macOS/Linux
find ~/Library/Application\ Support/JetBrains -name "tools" -type d

# Windows (PowerShell)
Get-ChildItem -Path "$env:APPDATA\JetBrains" -Recurse -Filter "tools" -Directory
```

---

## 更多帮助

- **官方文档:** https://www.jetbrains.com/help/idea/external-tools.html
- **GitHub Issues:** https://github.com/openclaw/openclaw/issues
- **社区论坛:** https://discord.com/invite/clawd

---

*文档创建时间：2026-03-18*  
*适用于 Code Reviewer Skill v1.0*
