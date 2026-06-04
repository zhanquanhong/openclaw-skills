# wbs-skill v5.0 — 通用 WBS 任务分解器 + 工作量估算

**版本**: v5.0 (生产级)  
**创建时间**: 2026-04-16  
**最后更新**: 2026-06-05  
**输入任意技术方案文档 → 自动分解开发任务 → 来源精准可追溯 → 工作量估算**

---

## v5.0 新特性

- **工作量估算**：基于任务内容特征评分（实体/接口/页面/特殊逻辑），每个任务输出推荐人天数和估算范围
- **自我校准**：录入实际工时自动校准，初始 ±50%，校准 20+ 次后收窄到 ±15%
- **内容特征评分**：检测表设计、接口、页面、中间件、批量操作、第三方集成等 16 项特征
- **新开发/迭代区分**：根据"新增/修改/删除"关键词自动判断开发类型，不同系数
- **`--estimate` 开关**：默认不启用，不影响基础输出

## v4.0 核心特性

- **通用化引擎**：不限项目类型，任意技术方案都能正确分解
- **来源精准溯源**：三级定位（章节路径 + 页码 + 行号 + 原文片段），可直接翻到文档对应位置
- **内容智能提取**：自动去除冗余前缀、截断长句、标注任务类型
- **模块智能归组**：关键词 + 章节标题 + 白名单三维匹配
- **一致性验证**：来源 → 内容 → 模块三者一致性检查
- **PDF/DOCX/Markdown** 全格式支持
- **架构图过滤**：自动识别架构图标注行，不混入任务清单

---

## 🚀 快速开始

### 安装（3 步搞定，只跑一次）

```bash
# 第 1 步：下载
# 从 GitHub 下载 wbs-skill-v5.0.zip，解压到任意目录

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

# 方式 4：工作量估算
python3 generate_wbs.py 技术方案.pdf --estimate
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

## 📊 输出格式

### 基础输出（不加 --estimate）— 9 列

1. 任务模块（精准接口名，不泛化）
2. 任务 ID
3. 任务内容（自动标准化）
4. 任务来源（章节 + 页码 + 行号 + 原文）
5. 任务类型
6. 依赖
7. 可验收标准
8. 验证状态（PASS/WARN/FAIL）
9. 处理时间(ms)

### 工作量估算（加 --estimate）— 11 列

追加 2 列：
10. **推荐人天数** — 浮点数，保留 1 位小数
11. **估算范围** — 如 "1.4~2.6"，精度随校准数据收敛

底部追加按模块汇总和项目总计行。另含"验证结果"Sheet。

---

## 💡 使用场景

| 场景 | 使用方式 |
|------|----------|
| **快速分解** | `./wbs.sh 技术方案.pdf` |
| **按周分解** | `./wbs.sh 技术方案.pdf "按周分解"` |
| **只看接口** | `./wbs.sh 技术方案.pdf "重点标出接口任务"` |
| **排除运维** | `./wbs.sh 技术方案.pdf "排除运维相关任务"` |
| **只分解后端** | `./wbs.sh 技术方案.pdf "只分解后端开发部分"` |
| **工作量估算** | `python3 generate_wbs.py 技术方案.pdf --estimate` |
| **兼容模式** | `./wbs.sh 技术方案.pdf --mode v3` |

---

## 📁 目录结构

```
wbs-skill/
├── wbs.sh                  ← Mac/Linux 入口脚本
├── wbs.bat                 ← Windows 入口脚本
├── install.sh              ← Mac/Linux 安装脚本
├── install.bat             ← Windows 安装脚本
├── generate_wbs.py         ← 一键生成器（主入口）
├── skill.json              ← 技能注册元数据
├── requirements.txt        ← Python 依赖
├── input/                  ← 【可选】放文档的目录
├── output/                 ← 生成的 Excel 文件
├── config/
│   ├── section_rules.yaml  ← 章节识别模板
│   └── type_rules.yaml     ← 类型规则
├── data/
│   ├── whitelist.yaml      ← 官方白名单
│   └── user_whitelist.yaml ← 用户白名单
└── src/
    ├── wbs_cli.py           ← CLI 统一入口
    ├── source_locator.py    ← v4.0 来源定位引擎
    ├── content_extractor.py ← v4.0 内容提取引擎
    ├── module_grouper.py    ← v4.0 模块归组引擎
    ├── consistency_checker.py ← v4.0 一致性验证引擎
    ├── estimator/           ← v5.0 工作量估算
    │   ├── engine.py        ← 估算引擎
    │   ├── rules.py         ← 内容特征评分规则
    │   └── calibrator.py    ← 校准系统
    ├── intent_parser.py     ← 自然语言意图解析
    ├── env_checker.py       ← 环境检查
    ├── document_parser.py   ← 多格式文档解析
    ├── section_engine.py    ← 章节推断引擎
    ├── table_extractor.py   ← 表格解析
    ├── type_classifier.py   ← 任务类型分类
    ├── whitelist_manager.py ← 白名单管理
    ├── decomposer_v3.py     ← v3 兼容分解器
    ├── parser.py            ← PDF 解析（兼容旧版）
    ├── rules.py             ← 规则定义
    ├── templates.py         ← 验收标准模板
    └── output.py            ← Excel 输出
```

---

## 🔧 高级用法

### 工作量估算（v5.0）

```bash
# 启用人天数估算
python3 generate_wbs.py 技术方案.pdf --estimate

# 批量录入实际工时（校准，提升后续估算精度）
python3 generate_wbs.py --calibrate-file actual_hours.json

# 查看校准统计
python3 generate_wbs.py --calibration-stats
```

`actual_hours.json` 格式：
```json
[
  {"task_content": "新增用户查询接口", "actual_days": 2.5},
  {"task_content": "设计用户订单表", "actual_days": 0.5}
]
```

### 导出/导入白名单

```bash
python3 generate_wbs.py --export my_whitelist.yaml   # 导出分享
python3 generate_wbs.py --import team_whitelist.yaml  # 导入团队
python3 generate_wbs.py --stats                       # 统计信息
```

### 指定章节模板

```bash
./wbs.sh 技术方案.pdf --section-template chinese       # 中文编号
./wbs.sh 技术方案.md --section-template markdown       # Markdown 标题
```

### 调试模式

```bash
python3 generate_wbs.py 技术方案.pdf --debug-json debug.json
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
**A**: 把文档放到 `input/` 目录，或使用绝对路径：`./wbs.sh /完整/路径/文档.pdf`

### Q: PDF 解析后内容为空
**A**: 可能是扫描版 PDF，建议转换为 DOCX 或使用 OCR 工具预处理

### Q: 自然语言过滤结果不准确
**A**: 当前使用关键词匹配，准确率约 80%。建议先不加引号生成完整结果，再人工筛选

### Q: Windows 下中文乱码
**A**: 确保终端编码为 UTF-8：`[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`

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

## 🔗 相关文档

- 技能说明：`SKILL.md`
- 交付指南：`WBS_DELIVERY_GUIDE.md`
- 端到端测试：`test_e2e.py`

---

**wbs-skill v5.0 — 下载即用，拖文档出 Excel，通用化 + 精准溯源 + 工作量估算**
