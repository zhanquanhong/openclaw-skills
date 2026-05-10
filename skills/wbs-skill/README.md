# wbs-skill v3.2 — 自然语言 WBS 任务分解器

**版本**: v3.2 (生产级)  
**创建时间**: 2026-04-16  
**最后更新**: 2026-05-10  
**输入技术方案文档 → 自动分解后端开发任务 → 越用越聪明**

---

## 🚀 快速开始

### 安装（3 步搞定，只跑一次）

```bash
# 第 1 步：下载
# 从 GitHub 下载 wbs-skill-v3.2.zip，解压到任意目录

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
├── WBS_技术方案_20260510_143022.xlsx  ← 最新结果
├── WBS_旧方案_20260509_101533.xlsx    ← 历史结果（自动保留 10 份）
```

---

## 📋 支持的格式

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| PDF | `.pdf` | 自动提取文本和表格 |
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
│   ├── wbs_cli.py      ← CLI 统一入口
│   ├── intent_parser.py← 自然语言意图解析
│   ├── env_checker.py  ← 环境检查
│   ├── document_parser.py  ← 多格式文档解析
│   ├── section_engine.py   ← 章节推断
│   ├── table_extractor.py  ← 表格解析
│   ├── whitelist_manager.py← 白名单管理
│   └── ...
│
├── config/             ← 配置
├── data/               ← 白名单数据
└── requirements.txt    ← Python 依赖
```

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
3. 任务内容
4. 任务来源（精确到章节 + 行号）
5. 依赖
6. 可验收标准（精确可执行）
7. 任务类型（🆕新增/🔄更新/📋普通）

---

## 🔗 相关文档

- 详细使用指南：`README_USAGE.md`
- 技能说明：`SKILL.md`

---

**wbs-skill v3.2 — 下载即用，拖文档出 Excel**
