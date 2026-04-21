# SKILL_REGISTRY.md - 技能注册表

_自动生成的技能清单。新增技能时更新此文件。_

## 技能清单

### 按功能分类

#### 📊 WBS 任务分解
| 技能 | 版本 | 输出 | 使用场景 | 状态 |
|------|------|------|---------|------|
| `wbs-skill` | v2.0 | 单 sheet Excel | 快速分解，白名单学习 | ✅ 活跃 |
| `task-decomposer` | v3.3 | 任务列表（文本） | 日常任务分解 | ✅ 活跃 |
| `wbs-validator` | v1.0 | 验证报告 | WBS 质量验证 | ✅ 活跃 |
| `java-wbs-decomposition` | v3.2 | 6 个 sheet Excel | 正式项目，完整分工 | ⚠️ 已归档（目录不存在） |

#### 🤖 AI 辅助
| 技能 | 版本 | 输出 | 使用场景 |
|------|------|------|---------|
| `ai-news-generator` | v1.0 | Markdown/Word/PDF | AI 新闻软文生成 |
| `tech-doc-validator` | v1.0 | 验证报告 | 技术方案规范性验证 |
| `code-reviewer` | v1.0 | Markdown/JSON | 代码安全漏洞检测 |
| `ocr-text-extractor` | v1.0 | 文本 | 图片文字识别 |

#### 📈 投资分析
| 技能 | 版本 | 输出 | 使用场景 |
|------|------|------|---------|
| `investment-analyzer` | v1.0 | 分析报告 | 股票/基金/ETF 分析 |
| `fed-policy-tracker` | v1.0 | 双周报告 | 美联储政策跟踪 |

#### 🛠️ 工具
| 技能 | 版本 | 输出 | 使用场景 |
|------|------|------|---------|
| `company-color-scheme` | v1.0 | 色值规范 | 公司品牌色调 |
| `image-to-3d` | v1.0 | 3D 效果图片 | 图片转 3D |
| `daily-news-digest` | v1.0 | Markdown | 每日新闻简报 |
| `searxng` | v1.0 | 搜索结果 | 隐私搜索 |

---

## 技能元数据标准

每个技能必须包含 `skill.json`：

```json
{
  "name": "技能名称",
  "version": "版本号",
  "category": "功能分类",
  "input": ["支持的输入格式"],
  "output": "输出格式说明",
  "use_cases": ["使用场景 1", "使用场景 2"],
  "conflicts": ["可能混淆的技能名称"],
  "last_updated": "最后更新日期"
}
```

---

## 技能识别规则

### 自动识别流程

1. **扫描技能目录** - 读取所有 `skill.json`
2. **构建技能树** - 按功能分类
3. **检测冲突** - 找出功能相似的技能
4. **生成对比表** - 自动输出区别

### 冲突检测示例

```
⚠️ 检测到功能相似的技能：
- java-wbs-decomposition
- wbs-skill

区别：
- 输出格式不同（6 个 sheet vs 单 sheet）
- 使用场景不同（正式项目 vs 快速分解）
- 白名单学习（不支持 vs 支持）
```

---

## 更新流程

### 新增技能时

1. 在技能目录创建 `skill.json`
2. 更新 `SKILL_REGISTRY.md`
3. 记录到 `MEMORY.md` 的"项目追踪"

### 技能优化时

1. 更新 `skill.json` 的 `version`
2. 更新 `SKILL_REGISTRY.md` 的 `last_updated`
3. 记录优化内容到 `MEMORY.md` 的"技术决策"

---

## 快速选择指南

### 需要 WBS 任务分解？
- **正式项目，需要完整分工** → `java-wbs-decomposition`
- **快速分解，需要白名单学习** → `wbs-skill`
- **验证 WBS 质量** → `wbs-validator`

### 需要技术方案验证？
- **验证规范性** → `tech-doc-validator`
- **生成 WBS** → `java-wbs-decomposition` 或 `wbs-skill`

### 需要代码相关？
- **代码审查** → `code-reviewer`
- **OCR 文字提取** → `ocr-text-extractor`

### 需要新闻/报告？
- **AI 技术新闻** → `ai-news-generator`
- **每日新闻简报** → `daily-news-digest`
- **美联储政策** → `fed-policy-tracker`

---

_此文件由 OpenClaw 自动维护，新增技能时更新。_
_最后更新：2026-04-21_
