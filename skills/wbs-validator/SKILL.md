# WBS 验证 Skill（升级版）

## 全名
**WBS 生成验证 Skill**（WBS Validator）

## 定位
质量保障（QA）角色 - WBS 生成系统的"守门员" + "学习者"

## 作用
1. **验证**：在生成 WBS Excel 后自动验证所有数据
2. **学习**：选择性记忆用户有意义的指导和认可的内容
3. **进化**：越用越聪明，支持不同技术方案

---

## 核心功能

### 1. 验证功能（7 个检查项）

| # | 验证项 | 检查内容 | 关键程度 |
|---|--------|----------|----------|
| 1 | Sheet 数量 | 必须 5 个 sheet | ⭐⭐⭐ |
| 2 | 甘特图列数 | 23 列（任务 + 负责人 + 21 天） | ⭐⭐ |
| 3 | 甘特图任务数 | 26 个接口 | ⭐⭐⭐ |
| 4 | **甘特图颜色** | **第 1 周周一/周二必须是灰色** | ⭐⭐⭐⭐⭐ |
| 5 | 表头 | 第 1 周/第 2 周/第 3 周，周一到周日 | ⭐⭐ |
| 6 | 接口级 WBS | ≥28 行 | ⭐⭐ |
| 7 | 任务级 WBS | ≥80 行 | ⭐⭐ |

### 2. 学习功能（选择性记忆）

**记忆原则**:
- ✅ 只记忆**有意义的指导**（包含"应该"、"必须"、"改为"等关键词）
- ✅ 只记忆**修改后认可的**（用户说"✅ 可以了"）
- ❌ 不记忆**闲聊/重复内容**

**记忆触发条件**:
```python
def should_remember(instruction, context):
    # 用户认可
    if context.get('user_approved'):
        return True
    
    # 规则变更
    if context.get('rule_changed'):
        return True
    
    # 包含规则关键词
    keywords = ["应该", "必须", "要", "改为", "颜色", "从...开始"]
    if any(kw in instruction for kw in keywords):
        return True
    
    return False
```

### 3. 配置化验证

**支持的技术方案格式**:
- PDF（`pdfplumber` 解析）
- Markdown（直接读取）
- Word（`python-docx` 解析）

**配置文件结构**（YAML）:
```yaml
# wbs-spec-云端 OpenClaw 三期.yaml
project_name: 云端 OpenClaw 三期

tech_docs:
  - path: "docs/云端 OpenClaw 三期技术方案.pdf"
    type: "pdf"
  - path: "docs/云端 OpenClaw 三期_WBS.md"
    type: "markdown"
  - path: "docs/云端 OpenClaw 三期技术方案.docx"
    type: "word"

wbs_spec:
  interface_count: 26
  task_count: 78
  sheet_count: 5
  gantt:
    columns: 23
    start_weekday: 3  # 从周三开始
    total_weeks: 3
```

---

## 记忆库结构

```yaml
# wbs-validator-memory.yaml
rules:
  - date: 2026-04-11 16:35
    user_instruction: "甘特图应该从周三开始"
    rule_type: "gantt.start_weekday"
    rule_value: 3
    applied_to: ["云端 OpenClaw 三期"]
    user_approved: true
    
  - date: 2026-04-11 16:57
    user_instruction: "每周应该固定从周一到周日显示"
    rule_type: "gantt.display_weekdays"
    rule_value: 7
    applied_to: ["云端 OpenClaw 三期"]
    user_approved: true
    
  - date: 2026-04-11 17:21
    user_instruction: "为什么还有周一周二标蓝色的色块"
    rule_type: "gantt.color.before_start"
    rule_value: "F0F0F0"
    applied_to: ["云端 OpenClaw 三期"]
    user_approved: true
```

---

## 使用示例

### 场景 1：生成 WBS 并验证

```python
# 初始化验证器（带记忆功能）
validator = WBSValidator(
    spec_file="wbs-spec-云端 OpenClaw 三期.yaml",
    memory_file="wbs-validator-memory.yaml"
)

# 生成 WBS
generate_wbs(project="云端 OpenClaw 三期")

# 验证（自动应用记忆库中的规则）
validator.validate(output_path)

# 验证通过 → 发送
# 验证失败 → 提示修复
```

### 场景 2：用户指导后学习

```python
# 用户指导
用户："甘特图应该从周三开始"
→ 修改代码
→ 用户："✅ 可以了"

# 学习（选择性记忆）
validator.learn_from_feedback(
    user_instruction="甘特图应该从周三开始",
    context={'user_approved': True, 'rule_changed': True}
)
# ✅ 已记忆规则：gantt.start_weekday = 3

# 下次验证时自动应用
validator.validate(excel_path)  # ← 自动检查是否从周三开始
```

### 场景 3：闲聊不记忆

```python
# 用户闲聊
用户："你好"

# 不记忆
validator.learn_from_feedback(
    user_instruction="你好",
    context={}
)
# 💬 对话记录，但不记忆为规则
```

---

## 架构设计

```python
class WBSValidator:
    """WBS 验证器（带学习功能）"""
    
    def __init__(self, spec_file, memory_file=None):
        self.spec = load_yaml(spec_file)
        self.memory = load_yaml(memory_file) if memory_file else {}
    
    def validate(self, excel_path):
        """验证 WBS Excel"""
        # 1. 加载记忆库规则
        self.apply_memory_rules()
        
        # 2. 执行 7 项验证
        self.check_sheet_count()
        self.check_gantt_columns()
        self.check_gantt_task_count()
        self.check_gantt_colors()  # 关键！
        self.check_headers()
        self.check_interface_wbs()
        self.check_detailed_wbs()
        
        # 3. 验证通过 → 返回 True
        return True
    
    def learn_from_feedback(self, user_instruction, context):
        """从用户反馈中学习（选择性记忆）"""
        # 1. 判断是否值得记忆
        if not self.should_remember(user_instruction, context):
            return
        
        # 2. 解析规则
        rule = self.parse_instruction(user_instruction)
        
        # 3. 检查是否已存在
        if self.rule_exists(rule):
            return
        
        # 4. 添加到记忆库
        self.memory['rules'].append({
            'date': datetime.now().isoformat(),
            'user_instruction': user_instruction,
            'rule_type': rule['type'],
            'rule_value': rule['value'],
            'applied_to': context.get('project', '通用'),
            'user_approved': context.get('user_approved', False)
        })
        
        # 5. 保存记忆
        self.save_memory()
    
    def should_remember(self, instruction, context):
        """判断是否值得记忆"""
        if context.get('user_approved'):
            return True
        if context.get('rule_changed'):
            return True
        
        keywords = ["应该", "必须", "要", "改为", "颜色", "从...开始"]
        if any(kw in instruction for kw in keywords):
            return True
        
        return False
```

---

## 教训与改进

**教训**（2026-04-11）:
- ❌ 甘特图颜色错误，25 个任务在周一、周二显示蓝色（应该是灰色）
- ❌ 用户发现后才修复，浪费用户时间
- ❌ 硬编码规则，只能用于一个项目

**改进**:
- ✅ 创建 WBS 验证 Skill
- ✅ 每次生成后自动运行 7 项验证
- ✅ 添加选择性记忆功能
- ✅ 配置化规则，支持不同项目
- ✅ 支持 PDF/Markdown/Word 技术方案

---

## 用户画像

| 角色 | 需求 | 使用场景 |
|------|------|----------|
| **项目经理** | 确保 WBS 数据准确 | 生成项目任务分解表后验证 |
| **技术负责人** | 确保甘特图正确 | 检查工期、资源分配是否合理 |
| **AI 助手** | 避免发送错误文件 + 学习用户偏好 | 每次生成 WBS 后自动调用 + 记忆用户指导 |

---

## 版本历史

| 版本 | 日期 | 核心功能 | 状态 |
|------|------|----------|------|
| v1.0 | 2026-04-11 | 基础验证功能（7 个检查项） | ✅ 完成 |
| v2.0 | 2026-04-11 | 添加选择性记忆功能 | ✅ 完成 |
| v3.0 | 未来 | 支持 PDF/Markdown/Word 技术方案解析 | 📋 计划 |
