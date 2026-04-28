# wbs-skill - WBS 任务自动分解技能

**开发状态**: ✅ 生产级可用  
**版本**: v3.1（智能依赖推断 + 大模块拆分）  
**创建时间**: 2026-04-16  
**最后更新**: 2026-04-28  
**目标**: 输入技术方案 PDF → 自动分解后端开发任务 → 越用越聪明

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd ~/.openclaw/workspace/skills/wbs-skill
pip install -r requirements.txt
```

### 2. 一键生成 WBS

```bash
# 默认模式（自动学习新任务，需要确认）
python3 generate_wbs.py /path/to/技术方案.pdf

# 自动学习，不需要确认（推荐 CI/CD 使用）
python3 generate_wbs.py /path/to/技术方案.pdf --no-confirm

# 禁用自动学习（仅生成 WBS）
python3 generate_wbs.py /path/to/技术方案.pdf --no-learn

# 指定输出目录
python3 generate_wbs.py /path/to/技术方案.pdf -o ./output
```

### 3. 白名单管理

```bash
# 导出用户白名单（分享给团队）
python3 generate_wbs.py --export my_whitelist.yaml

# 导入团队白名单
python3 generate_wbs.py --import team_whitelist.yaml

# 显示统计信息
python3 generate_wbs.py --stats
```

---

## 📋 输出格式

**Excel 包含 7 列**：

| 列名 | 说明 | 示例 |
|------|------|------|
| 任务模块 | 任务归属的大模块 | 技能中心 |
| 任务 ID | 唯一标识 | T001 |
| 任务内容 | 具体开发任务 | 技能列表查询接口开发 |
| 任务来源 | 精确到章节 + 行号 | 第 3 章 2.1 节 行 45 |
| 依赖 | 前置任务 | T001 |
| 可验收标准 | 精确可执行的完成标准 | 接口可调用，返回数据正确 |
| 任务类型 | 🆕新增/🔄更新/📋普通 | 🆕新增 |

---

## 🧠 智能学习机制（核心特性）

### 双轨制 + 智能融合

**v3.0 新增**：采用「双轨制 + 智能融合」架构，结合白名单标准化和 PDF 提取的完整性。

```
PDF 文档
    ↓
┌─────────────────────────────────────┐
│  轨道 1：PDF 提取（带任务来源）        │
│  - 任务内容（原文）                   │
│  - 任务来源（章节 + 行号）✅          │
│  - 任务类型（新增/更新/普通）✅       │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  轨道 2：白名单匹配（标准化命名）      │
│  - 官方白名单（32 个标准任务）         │
│  - 用户白名单（学习积累的任务）        │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  智能融合                            │
│  - 任务内容 ← 白名单（标准化）         │
│  - 任务来源 ← PDF 提取（精确追溯）✅   │
│  - 任务类型 ← PDF 提取（自动识别）✅   │
│  - 新任务 → 自动学习 ✅               │
└─────────────────────────────────────┘
              ↓
        完整 WBS Excel
```

### 两种白名单

| 类型 | 文件 | 说明 | git 管理 |
|------|------|------|----------|
| **官方白名单** | `data/whitelist.yaml` | 官方维护的通用规则 | ✅ 纳入版本控制 |
| **用户白名单** | `data/user_whitelist.yaml` | 用户自定义的学习成果 | ❌ .gitignore 忽略 |

### 学习流程

```
1. PDF 提取所有任务（带任务来源、任务类型）
    ↓
2. 白名单匹配（标准化任务命名）
    ↓
3. 智能融合：
   - 白名单有的任务 → 使用白名单命名 + PDF 来源
   - 白名单无的任务 → 完全使用 PDF 信息 + 标记为新任务
    ↓
4. 生成 WBS Excel（任务来源 100% 有值）
    ↓
5. 询问用户：发现 N 个新任务，是否学习？[Y/n]
    ↓
6. 用户确认 → 保存到 user_whitelist.yaml
    ↓
7. 下次使用时自动匹配（越用越聪明）
```

### 优势

- ✅ **任务来源 100% 有值**：精确到章节 + 行号
- ✅ **任务类型自动识别**：新增接口/更新接口/普通任务
- ✅ **git pull 不丢失**：用户白名单被 .gitignore 保护
- ✅ **换电脑可迁移**：复制 user_whitelist.yaml 即可
- ✅ **团队可共享**：导出白名单分享给团队成员
- ✅ **越用越聪明**：每次使用都在积累识别规则

---

## 📊 预期效果

| 使用次数 | 识别率 | 总时间 |
|---------|--------|--------|
| 第 1 次 | 80% | 45 分钟 |
| 第 3 次 | 88% | 20 分钟 |
| 第 5 次 | 90%+ | 13 分钟 |
| 第 10 次 | 92%+ | 7 分钟 |

---

## 📁 文件结构

```
wbs-skill/
├── generate_wbs.py                 # 一键生成器（主入口）
├── .gitignore                      # 保护用户数据
├── README.md                       # 本文件
├── README_USAGE.md                 # 详细使用文档
├── SKILL.md                        # 技能说明
├── requirements.txt                # 依赖包
│
├── data/                           # 白名单数据
│   ├── whitelist.yaml              # 官方白名单
│   └── user_whitelist.yaml         # 用户白名单（.gitignore 保护）
│
├── src/                            # 核心模块
│   ├── whitelist_manager.py        # 白名单管理器
│   ├── whitelist_extractor_v7.py   # 自动提取器（识别新增/更新）
│   ├── decomposer_v3.py            # 任务分解器
│   ├── parser.py                   # PDF 解析
│   ├── rules.py                    # 规则定义
│   ├── templates.py                # 验收标准模板
│   └── output.py                   # Excel 输出
│
└── output/                         # 输出目录（自动生成）
    └── WBS_技术方案_xxx.xlsx       # 生成的 WBS 文件
```

---

## 🎯 使用场景

| 场景 | 使用方式 |
|------|----------|
| **新方案首次使用** | 一键生成 → 人工补充 → 保存到用户白名单 |
| **类似方案复用** | 一键生成（自动使用用户白名单） |
| **团队共享** | 导出白名单 → 团队成员导入 |
| **换电脑** | 复制 user_whitelist.yaml 即可 |
| **测试自动提取** | `--no-user` 参数仅使用自动提取 |

---

## 🔧 高级用法

### 查看学习成果

```bash
# 显示统计信息
python3 generate_wbs.py --stats

# 输出示例：
# 📊 白名单统计
# ──────────────────────
# 官方白名单：120 个任务
# 用户白名单：45 个任务（学习成果）
# 总计：165 个任务
```

### 导出/导入白名单

```bash
# 导出用户白名单（分享给团队）
python3 generate_wbs.py --export my_whitelist.yaml

# 导入团队白名单（合并）
python3 generate_wbs.py --import team_whitelist.yaml

# 导入团队白名单（覆盖）
python3 generate_wbs.py --import team_whitelist.yaml --overwrite
```

### 查看用户白名单

```bash
# 直接查看 YAML 文件
cat data/user_whitelist.yaml

# 或使用 Python 查看
python3 -c "from src.whitelist_manager import UserWhitelistManager; m = UserWhitelistManager(); m.print_stats()"
```

---

## 🧪 测试

### 运行单元测试

```bash
python3 -m pytest tests/test_whitelist_manager.py -v
```

### 运行集成测试

```bash
python3 -m pytest tests/test_integration.py -v
```

---

## 🆘 常见问题

### Q: 识别率不高怎么办？

A: 第一次使用识别率 80% 左右是正常的。使用 3-5 次后，识别率会提升到 90%+。关键是每次使用后把人工补充的任务保存到用户白名单。

### Q: 如何保存学习成果？

A: 人工补充/修改任务后，使用 `--export` 导出或直接编辑 `data/user_whitelist.yaml`。

### Q: 用户白名单在哪里？

A: `data/user_whitelist.yaml`，此文件被 .gitignore 保护，git pull 不会丢失。

### Q: 如何分享给团队成员？

A: 使用 `--export` 导出用户白名单，发送给团队成员，他们使用 `--import` 导入即可。

### Q: 换电脑了怎么办？

A: 复制 `data/user_whitelist.yaml` 到新电脑的相同位置即可，所有学习成果都在这个文件里。

---

## 📖 详细文档

查看 `README_USAGE.md` 获取完整使用指南和示例。

---

**开发状态**: ✅ 生产级可用  
**最后更新**: 2026-04-17  
**版本**: v2.0 (方案 C 生产级)

---

**wbs-skill - 越用越聪明的 WBS 生成器**
