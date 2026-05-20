# wbs-skill v4.0 — 通用 WBS 任务分解器

**版本**: v4.0 (生产级)  
**创建时间**: 2026-04-16  
**最后更新**: 2026-05-20  
**输入任意技术方案文档 → 自动分解开发任务 → 来源精准可追溯 → 模块名智能精准化**

---

## v4.0 新特性

- **通用化引擎**：不限项目类型，任意技术方案都能正确分解
- **来源精准溯源**：三级定位（章节路径 + 页码 + 行号 + 原文片段），可直接翻到文档对应位置
- **内容智能提取**：自动去除冗余前缀、截断长句、标注任务类型
- **模块智能归组**：内容关键词 + 章节标题 + 白名单三维匹配，支持精确接口名覆盖泛化模块名
- **一致性验证**：来源 → 内容 → 模块三者一致性检查 + 相邻去重 + 模块平衡 + 来源合理性
- **PDF/DOCX/Markdown** 全格式支持
- **架构图过滤**：自动识别技术方案中的架构图标注行，不混入任务清单
- **输出列精简**：9 列输出（含验证状态、处理时间）

---

## 📊 输出格式

Excel 包含 9 列：
1. 任务模块（精准接口名，不泛化）
2. 任务 ID
3. 任务内容
4. 任务来源（章节 + 页码 + 行号 + 原文）
5. 任务类型
6. 依赖
7. 可验收标准
8. 验证状态（PASS/WARN/FAIL）
9. 处理时间(ms)

另含"验证结果"Sheet，展示所有一致性检测详情。

---

## 🔧 高级用法

### 调试模式

```bash
# 输出每个任务的完整处理链路
python3 generate_wbs.py 技术方案.pdf --debug-json debug.json
```

---

## 🚀 快速开始

### 安装（3 步搞定，只跑一次）

```bash
# 第 1 步：下载
# 从 GitHub 下载 wbs-skill-v4.0.zip，解压到任意目录

# 第 2 步：安装
# Mac/Linux
chmod +x install.sh && ./install.sh

# Windows
双击 install.bat

# 第 3 步：开始使用
./wbs.sh input/技术方案.pdf
```

### 使用

```bash
# 方式 1：文档放在 input/ 目录（最简单）
./wbs.sh input/技术方案.pdf

# 方式 2：文档在任意位置（使用绝对路径）
./wbs.sh ~/Desktop/技术方案V3.pdf
./wbs.sh /data/projects/xxx/方案.docx

# 方式 3：自然语言调用（加需求描述）
./wbs.sh 技术方案.pdf "按周分解，重点标出接口任务"
./wbs.sh 技术方案.pdf "只分解后端开发部分"
./wbs.sh 技术方案.pdf "排除运维相关任务"
```

**Windows 用户**：把 `./wbs.sh` 换成 `wbs.bat` 即可。

### 输出

生成的 Excel 文件自动保存到 `output/` 目录：

```
output/
├── WBS_技术方案_20260519_143022.xlsx  ← 最新结果
├── WBS_旧方案_20260518_101533.xlsx    ← 历史结果（自动保留 10 份）
```

---

## 📋 支持的格式

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| PDF | `.pdf` | 自动提取文本和表格，支持页码映射 |
| Word | `.docx` | 自动提取段落和表格 |
| Markdown | `.md` / `.markdown` | 直接读取，支持 Markdown 表格 |

---

## 💡 使用场景

| 场景 | 使用方式 |
|------|----------|
| **快速分解** | `./wbs.sh 技术方案.pdf` |
| **按周分解** | `./wbs.sh 技术方案.pdf "按周分解"` |
| **只看接口** | `./wbs.sh 技术方案.pdf "重点标出接口任务"` |
| **排除运维** | `./wbs.sh 技术方案.pdf "排除运维相关任务"` |
| **只分解后端** | `./wbs.sh 技术方案.pdf "只分解后端开发部分"` |
| **兼容模式** | `./wbs.sh 技术方案.pdf --mode v3` |

---

## 📁 目录结构

```
wbs-skill/
├── wbs.sh              ← Mac/Linux 入口脚本
├── wbs.bat             ← Windows 入口脚本
├── install.sh          ← Mac/Linux 安装脚本
├── install.bat         ← Windows 安装脚本
│
├── input/              ← 【可选】放文档的目录
├── output/             ← 生成的 Excel 文件
│
├── src/                ← 核心代码
│   ├── source_locator.py      ← v4.0 来源定位引擎
│   ├── content_extractor.py   ← v4.0 内容提取引擎
│   ├── module_grouper.py      ← v4.0 模块归组引擎
│   ├── consistency_checker.py ← v4.0 一致性验证引擎
│   ├── wbs_cli.py             ← CLI 统一入口
│   ├── intent_parser.py       ← 自然语言意图解析
│   ├── env_checker.py         ← 环境检查
│   ├── document_parser.py     ← 多格式文档解析
│   ├── section_engine.py      ← 章节推断
│   ├── table_extractor.py     ← 表格解析
│   └── whitelist_manager.py   ← 白名单管理
│
├── config/             ← 配置
├── data/               ← 白名单数据
└── requirements.txt    ← Python 依赖
```

---

## 🔧 高级用法

### 指定生成模式

```bash
# v4.0 模式（默认）：通用化引擎 + 精准溯源
./wbs.sh 技术方案.pdf

# v4.0 兼容模式：白名单匹配逻辑
./wbs.sh 技术方案.pdf --mode v3
```

### 导出/导入白名单

```bash
# 导出用户白名单（分享给团队）
python3 generate_wbs.py --export my_whitelist.yaml

# 导入团队白名单
python3 generate_wbs.py --import team_whitelist.yaml

# 显示统计信息
python3 generate_wbs.py --stats
```

### 指定章节模板

```bash
# 默认：数字编号（1.2.1）
./wbs.sh 技术方案.pdf

# 中文编号（一、(一)、1.）
./wbs.sh 技术方案.pdf --section-template chinese

# Markdown 标题（#、##）
./wbs.sh 技术方案.md --section-template markdown
```

### 禁用自动学习

```bash
./wbs.sh 技术方案.pdf --no-learn
```

---

## ⚠️ 常见问题

### Q: 提示"虚拟环境不存在"
**A**: 请先运行安装脚本：`./install.sh`（Mac/Linux）或 `install.bat`（Windows）

### Q: 文件找不到
**A**: 
- 把文档放到 `input/` 目录，然后执行：`./wbs.sh input/文档名.pdf`
- 或使用绝对路径：`./wbs.sh /完整/路径/文档.pdf`

### Q: PDF 解析后内容为空
**A**: 可能是扫描版 PDF，建议转换为 DOCX 或使用 OCR 工具预处理

### Q: 自然语言过滤结果不准确
**A**: 当前使用关键词匹配，准确率约 80%。建议先不加引号生成完整结果，再人工筛选

### Q: Windows 下中文乱码
**A**: 确保终端编码为 UTF-8，PowerShell 用户可运行：`[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`

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

## 📊 输出格式

Excel 包含 7 列：
1. 任务模块
2. 任务 ID
3. 任务内容（v4.0 自动标准化）
4. 任务来源（v4.0 三级定位：章节 + 页码 + 行号 + 原文）
5. 依赖
6. 可验收标准（精确可执行）
7. 任务类型（接口/数据库/配置/中间件/前端/算法/功能）

---

## 🔗 相关文档

- 详细使用指南：`README_USAGE.md`
- 技能说明：`SKILL.md`

---

**wbs-skill v4.0 — 下载即用，拖文档出 Excel，通用化 + 精准溯源**
