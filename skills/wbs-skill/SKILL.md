# wbs-skill - WBS 任务自动分解技能

**版本**: v3.0 (生产级)  
**创建时间**: 2026-04-16  
**更新时间**: 2026-04-27  
**目标**: 输入技术方案文档 → 自动分解后端开发任务 → 越用越聪明

---

## 🚀 快速开始

```bash
# 一键生成 WBS（默认数字编号模板）
python3 generate_wbs.py /path/to/技术方案.pdf

# 指定章节模板
python3 generate_wbs.py 技术方案.pdf --section-template chinese

# 查看统计
python3 generate_wbs.py --stats

# 导出白名单分享给团队
python3 generate_wbs.py --export my_whitelist.yaml
```

---

## 📁 默认输出路径

**默认**：`./output/`（当前目录下的 output 文件夹）

**示例**：
```bash
cd skills/wbs-skill
python3 generate_wbs.py 技术方案.pdf
# 输出：skills/wbs-skill/output/WBS_技术方案_xxx.xlsx
```

---

## 📚 核心特性

| 特性 | 说明 |
|------|------|
| **多格式支持** | 支持 PDF、DOCX、Markdown |
| **多章节模板** | 数字编号/中文编号/Markdown/混合编号 |
| **表格解析** | 自动识别接口表格，提取接口任务 |
| **一键生成** | 输入文档，输出 Excel 任务分解 |
| **用户白名单** | 用户自定义白名单，git pull 不丢失 |
| **团队共享** | 支持导出/导入白名单，团队识别率共同提升 |
| **精准定位** | 任务来源精确到章节 + 行号 |
| **自动清理** | 输出目录自动保留最新 10 份 |

---

## 📋 章节识别模板

支持多种章节编号规则，通过 `--section-template` 参数切换：

| 模板 | 说明 | 示例 |
|------|------|------|
| `numeric` | 数字编号 | 1.2.1 接口定义 |
| `chinese` | 中文编号 | 一、需求分析 → (一) 功能需求 → 1. 用户管理 |
| `markdown` | Markdown 标题 | ## 接口定义 |
| `mixed` | 混合编号 | 一、需求分析 → 1.1 功能需求 |

```bash
# 使用默认模板（numeric）
python3 generate_wbs.py 技术方案.pdf

# 使用中文编号模板
python3 generate_wbs.py 技术方案.pdf --section-template chinese
```

---

## 📁 文件结构

```
wbs-skill/
├── generate_wbs.py                 # 一键生成器（主入口）
├── .gitignore                      # 保护用户数据
├── README_USAGE.md                 # 详细使用文档
├── SKILL.md                        # 本文件
├── test_phase1.py                  # Phase 1 单元测试
├── config/
│   ├── section_rules.yaml          # 章节识别模板配置
│   └── mode.yaml                   # 运行模式配置
├── data/
│   ├── whitelist.yaml              # 官方白名单
│   └── user_whitelist.yaml         # 用户白名单（.gitignore 保护）
└── src/
    ├── section_engine.py           # 章节推断引擎
    ├── table_extractor.py          # 表格解析器（多引擎 fallback）
    ├── document_parser.py          # 多格式文档解析
    ├── whitelist_manager.py        # 白名单管理器
    ├── decomposer_v3.py            # 任务分解器
    ├── parser.py                   # PDF 解析（兼容旧版）
    ├── rules.py                    # 规则定义
    ├── templates.py                # 验收标准模板
    └── output.py                   # Excel 输出
```

---

## 🎯 使用场景

| 场景 | 使用方式 |
|------|----------|
| **新方案首次使用** | 一键生成 → 人工补充 → 保存到用户白名单 |
| **类似方案复用** | 一键生成（自动使用用户白名单） |
| **团队共享** | 导出白名单 → 团队成员导入 |
| **换电脑** | 复制 user_whitelist.yaml 即可 |

---

## 📊 输出格式

**Excel 包含 7 列**：
1. 任务模块
2. 任务 ID
3. 任务内容
4. 任务来源（精确到章节 + 行号）
5. 依赖
6. 可验收标准（精确可执行）
7. 任务类型（🆕新增/🔄更新/📋普通）

---

## 💡 白名单机制（方案 C）

### 两种白名单

| 类型 | 文件 | 说明 | git 管理 |
|------|------|------|----------|
| **官方白名单** | `data/whitelist.yaml` | 官方维护的通用规则 | ✅ 纳入版本控制 |
| **用户白名单** | `data/user_whitelist.yaml` | 用户自定义的学习成果 | ❌ .gitignore 忽略 |

### 工作原理

```
生成 WBS 时：
    ↓
加载官方白名单 + 用户白名单
    ↓
自动合并（用户优先）
    ↓
生成完整任务分解
```

### 优势

- ✅ **git pull 不丢失**：用户白名单被 .gitignore 保护
- ✅ **换电脑可迁移**：复制 user_whitelist.yaml 即可
- ✅ **团队可共享**：导出白名单分享给团队成员

---

## 🔧 高级用法

### 导出/导入白名单

```bash
# 导出用户白名单（分享给团队）
python3 generate_wbs.py --export my_whitelist.yaml

# 导入团队白名单
python3 generate_wbs.py --import team_whitelist.yaml

# 显示统计信息
python3 generate_wbs.py --stats
```

### 不使用用户白名单

```bash
# 仅使用自动提取（测试用）
python3 generate_wbs.py 技术方案.pdf --no-user
```

---

## 📈 学习机制

```
用户使用 wbs-skill
    ↓
自动生成 + 手动补充
    ↓
保存到 user_whitelist.yaml（学习成果）
    ↓
下次使用时自动加载
    ↓
识别率越来越高 📈
```

---

## 📖 详细文档

查看 `README_USAGE.md` 获取完整使用指南。

---

**wbs-skill - 越用越聪明的 WBS 生成器**
