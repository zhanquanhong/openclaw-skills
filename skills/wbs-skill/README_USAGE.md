# wbs-skill 使用指南

## 🚀 快速开始

### 一键生成 WBS

```bash
# 基本用法（使用用户白名单）
python3 generate_wbs.py /path/to/技术方案.pdf

# 指定输出目录
python3 generate_wbs.py /path/to/技术方案.pdf -o /path/to/output

# 不使用用户白名单（仅自动提取）
python3 generate_wbs.py /path/to/技术方案.pdf --no-user
```

---

## 📚 白名单机制（方案 C）

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

## 📤 白名单导出/导入

### 导出（分享给团队）

```bash
# 导出用户白名单
python3 generate_wbs.py --export my_whitelist.yaml

# 导出合并后的完整白名单（官方 + 用户）
python3 generate_wbs.py --export full_whitelist.yaml --include-official
```

### 导入（从团队获取）

```bash
# 导入并合并到现有用户白名单
python3 generate_wbs.py --import team_whitelist.yaml

# 覆盖用户白名单
python3 generate_wbs.py --import team_whitelist.yaml --no-merge
```

---

## 📊 查看统计

```bash
# 显示白名单统计
python3 generate_wbs.py --stats
```

输出示例：
```
============================================================
📊 wbs-skill 白名单统计
============================================================
📁 官方白名单：3 个模块，18 个任务
👤 用户白名单：5 个模块，32 个任务（学习成果）
💾 用户数据：✅ 已存在
============================================================
```

---

## ✏️ 手动编辑用户白名单

### 白名单格式

```yaml
1.2.1 提取模型的文件 ID:
  - 任务内容：实现从模型返回结果中提取 file_id 的解析逻辑
    任务来源：1.2 技术方案 | 1.2.1 提取模型的文件 ID | 正则表达式提取逻辑
    任务类型：普通任务
  
  - 任务内容：【新增】通过文件 ID 查询图书详情接口
    任务来源：1.2 技术方案 | 1.2.1 提取模型的文件 ID | 图书列表 | 新增接口
    任务类型：新增接口
```

### 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `任务内容` | ✅ | 任务的具体描述 |
| `任务来源` | ✅ | 技术方案中的位置（章节 + 行号） |
| `任务类型` | ⚠️ | 普通任务/新增接口/更新接口 |

---

## 🔄 典型工作流

### 首次使用某类技术方案

```bash
# 1. 一键生成（自动提取）
python3 generate_wbs.py 技术方案.pdf --no-user

# 2. 检查输出，发现遗漏
# 打开 Excel 查看任务分解

# 3. 手动补充用户白名单
vi data/user_whitelist.yaml

# 4. 重新生成（使用用户白名单）
python3 generate_wbs.py 技术方案.pdf
```

### 团队共享最佳实践

```bash
# 用户 A：完成项目后导出白名单
python3 generate_wbs.py --export cloud_project_whitelist.yaml

# 用户 A：提交到团队共享目录
git add cloud_project_whitelist.yaml
git commit -m "贡献云盘项目白名单"
git push

# 用户 B：拉取最新代码
git pull

# 用户 B：导入团队白名单
python3 generate_wbs.py --import cloud_project_whitelist.yaml

# 用户 B：使用增强后的 wbs-skill 生成新项目
python3 generate_wbs.py 新项目.pdf
```

---

## 📁 文件结构

```
wbs-skill/
├── generate_wbs.py              # 一键生成器
├── data/
│   ├── whitelist.yaml           # 官方白名单
│   ├── user_whitelist.yaml      # 用户白名单（.gitignore 保护）
│   └── .merged_whitelist.yaml   # 合并缓存（自动生成）
├── src/
│   ├── whitelist_manager.py     # 白名单管理器
│   └── ...
└── .gitignore                   # 保护用户数据
```

---

## 💡 常见问题

### Q: git pull 后用户白名单会丢失吗？
A: 不会！`user_whitelist.yaml` 被 .gitignore 保护，不会被覆盖。

### Q: 换电脑了怎么办？
A: 复制 `data/user_whitelist.yaml` 到新电脑即可，或者从团队导入。

### Q: 如何让团队使用我的白名单？
A: 导出后提交到团队共享目录，或者发邮件/发消息分享给同事。

### Q: 自动提取不准怎么办？
A: 手动编辑 `user_whitelist.yaml` 补充，下次生成会自动使用。

---

## 🎯 最佳实践

1. **每次项目后回顾**：检查是否有新任务类型，补充到用户白名单
2. **定期导出备份**：防止意外丢失
3. **团队共享**：发现通用规则后分享给团队
4. **注释说明**：在用户白名单中添加注释，说明任务背景

---

**wbs-skill - 越用越聪明的 WBS 生成器**
