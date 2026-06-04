# wbs-skill - WBS 任务自动分解技能 + 工作量估算

**版本**: v5.0 (生产级)  
**创建时间**: 2026-04-16  
**更新时间**: 2026-06-05  
**目标**: 输入任意技术方案文档 → 通用化任务分解 → 来源精准可追溯 → 工作量估算

---

## 🎯 定位

**wbs-skill 只做一件事**：将技术方案文档分解为可执行的任务清单（WBS），并支持人天数估算。

**不做的事**：
- ❌ AI 代码生成
- ❌ Git 分支管理
- ❌ PR/MR 创建
- ❌ 自动合并

> 如需 AI 辅助开发流程，应使用独立工具，以 wbs-skill 的输出（任务清单）为输入。

---

## 🚀 快速开始

```bash
# 一键安装（只跑一次）
# Mac/Linux
chmod +x install.sh && ./install.sh

# Windows
双击 install.bat

# 一键生成 WBS（默认数字编号模板）
./wbs.sh input/技术方案.pdf

# 自然语言调用
./wbs.sh 技术方案.pdf "按周分解，重点标出接口任务"

# 启用人天数估算
python3 generate_wbs.py 技术方案.pdf --estimate

# 查看统计
python3 generate_wbs.py --stats

# 导出白名单分享给团队
python3 generate_wbs.py --export my_whitelist.yaml
```

---

## 📁 默认输出路径

**默认**：`./output/`（wbs-skill 目录下的 output 文件夹）

**示例**：
```bash
cd skills/wbs-skill
./wbs.sh input/技术方案.pdf
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
| **自然语言调用** | 加引号传入需求描述，自动解析意图 |
| **用户白名单** | 用户自定义白名单，git pull 不丢失 |
| **团队共享** | 支持导出/导入白名单，团队识别率共同提升 |
| **精准定位** | 任务来源精确到章节 + 行号 |
| **自动清理** | 输出目录自动保留最新 10 份 |
| **工作量估算（v5.0）** | 基于内容特征评分，输出人天数和估算范围 |
| **自我校准（v5.0）** | 录入实际工时自动校准，精度随次数收敛 |

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
./wbs.sh 技术方案.pdf

# 使用中文编号模板
./wbs.sh 技术方案.pdf --section-template chinese
```

---

## 📁 文件结构

```
wbs-skill/
├── wbs.sh                          # Mac/Linux 入口脚本
├── wbs.bat                         # Windows 入口脚本
├── install.sh                      # Mac/Linux 安装脚本
├── install.bat                     # Windows 安装脚本
├── generate_wbs.py                 # 一键生成器（主入口）
├── .gitignore                      # 保护用户数据
├── README.md                       # 使用说明
├── SKILL.md                        # 本文件
├── skill.json                      # 技能注册元数据
├── config/
│   ├── section_rules.yaml          # 章节识别模板配置
│   └── type_rules.yaml             # 类型规则配置
├── data/
│   ├── whitelist.yaml              # 官方白名单
│   └── user_whitelist.yaml         # 用户白名单（.gitignore 保护）
├── src/
│   ├── wbs_cli.py                  # CLI 统一入口
│   ├── intent_parser.py            # 自然语言意图解析
│   ├── env_checker.py              # 环境检查
│   ├── section_engine.py           # 章节推断引擎
│   ├── table_extractor.py          # 表格解析器（多引擎 fallback）
│   ├── document_parser.py          # 多格式文档解析
│   ├── whitelist_manager.py        # 白名单管理器
│   ├── source_locator.py           # v4.0 来源定位引擎
│   ├── content_extractor.py        # v4.0 内容提取引擎
│   ├── module_grouper.py           # v4.0 模块归组引擎
│   ├── consistency_checker.py      # v4.0 一致性验证引擎
│   ├── estimator/                  # v5.0 工作量估算
│   │   ├── engine.py               # 估算引擎
│   │   ├── rules.py                # 内容特征评分规则
│   │   └── calibrator.py           # 校准系统
│   ├── decomposer_v3.py            # v3 兼容分解器
│   ├── parser.py                   # PDF 解析（兼容旧版）
│   ├── type_classifier.py          # 任务类型分类
│   ├── rules.py                    # 规则定义
│   ├── templates.py                # 验收标准模板
│   └── output.py                   # Excel 输出
└── tests/
    ├── test_estimator.py           # v5.0 工作量估算测试
    └── ...（其余测试在根目录）
```

---

## 🎯 使用场景

| 场景 | 使用方式 |
|------|----------|
| **新方案首次使用** | 一键生成 → 人工补充 → 保存到用户白名单 |
| **类似方案复用** | 一键生成（自动使用用户白名单） |
| **团队共享** | 导出白名单 → 团队成员导入 |
| **换电脑** | 复制 user_whitelist.yaml 即可 |
| **自然语言调用** | 加引号传入需求描述 |
| **工作量估算** | 加 --estimate 参数 |

---

## 📊 输出格式

### 基础输出（不加 --estimate）— 9 列
1. 任务模块
2. 任务 ID
3. 任务内容
4. 任务来源（精确到章节 + 行号）
5. 任务类型（LLM 分类 + 关键词回退）
6. 依赖
7. 可验收标准（精确可执行）
8. 验证状态
9. 处理时间(ms)

### 工作量估算（加 --estimate）— 11 列
追加 2 列：
10. **推荐人天数** — 浮点数，保留 1 位小数
11. **估算范围** — 如 "1.4~2.6"，精度随校准数据收敛

底部追加按模块汇总和项目总计行。

---

## 💡 工作量估算（v5.0）

基于任务内容特征评分，不依赖 LLM，零额外成本。

```bash
# 启用人天数估算
python3 generate_wbs.py 技术方案.pdf --estimate

# 批量录入实际工时（校准，提升后续估算精度）
python3 generate_wbs.py --calibrate-file actual_hours.json

# 查看校准统计
python3 generate_wbs.py --calibration-stats
```

估算特征（16 项评分规则）：
| 特征 | 示例 |
|------|------|
| 表设计 | "设计XX表" |
| 接口开发 | "新增查询接口" |
| 页面开发 | "开发管理页面" |
| 中间件集成 | "配置消息队列" |
| 批量操作 | "数据迁移脚本" |
| 第三方集成 | "对接微信支付" |

初始精度 ±50%，校准 20+ 次后收窄到 ±15%。

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

### 自然语言调用

```bash
# 按周分解
./wbs.sh 技术方案.pdf "按周分解"

# 重点标出接口任务
./wbs.sh 技术方案.pdf "重点标出接口任务"

# 排除运维相关任务
./wbs.sh 技术方案.pdf "排除运维相关任务"

# 只分解后端开发部分
./wbs.sh 技术方案.pdf "只分解后端开发部分"
```

### 调试模式

```bash
# 输出每个任务的完整处理链路
python3 generate_wbs.py 技术方案.pdf --debug-json debug.json
```

---

## 📈 学习机制

```
用户使用 wbs-skill
    ↓
自动生成 + 手动补充
    ↓
保存到用户白名单（学习成果）
    ↓
下次使用时自动加载
    ↓
识别率越来越高 📈
```

---

**wbs-skill v5.0 — 下载即用，拖文档出 Excel，通用化 + 精准溯源 + 工作量估算**
