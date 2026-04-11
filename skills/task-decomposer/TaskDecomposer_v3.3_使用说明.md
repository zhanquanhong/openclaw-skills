# AgenticX TaskDecomposer v3.3 使用说明

## 🎯 版本更新亮点

**v3.3 核心改进：交互式资源配置收集**

之前的版本（v3.2）硬编码假设"3 个后端 +1 个测试"，导致甘特图与实际团队配置不符。

v3.3 通过交互式问答收集真实资源配置，生成更准确的甘特图和排期。

---

## 📋 使用流程

### 方式 1：交互式问答（推荐）

```python
from agenticx.collaboration.workforce import TaskDecomposer

# 创建 TaskDecomposer 实例
decomposer = TaskDecomposer(
    task_agent=task_agent,
    llm_provider=llm_provider,
)

# 步骤 1：交互式收集资源配置
config = decomposer.collect_resource_config_interactive()

# 步骤 2：基于配置进行任务分解和甘特图演算
# ... 后续处理逻辑
```

**交互示例：**

```
============================================================
📋 AgenticX TaskDecomposer v3.3 - 资源配置收集
============================================================

1️⃣  后端投入几人？ [直接回复数字，或"不确定"]: 3
   后端每人可用时间？ [默认 100%，直接回车跳过]: 

2️⃣  测试投入几人？ [直接回复数字，或"不确定"]: 1
   测试每人可用时间？ [默认 100%，直接回车跳过]: 

3️⃣  有期望完工日期吗？ [可选，如"2026-06-30"，直接回车跳过]: 2026-06-30

4️⃣  有固定里程碑吗？ [可选，用逗号分隔，直接回车跳过]: 国庆前上线

5️⃣  团队技能水平？ [average/senior/mixed，默认 average]: average

6️⃣  前端投入几人？ [默认 0]: 0

7️⃣  产品几人？ [默认 0]: 1

============================================================
✅ 资源配置已收集完成！
============================================================
```

---

### 方式 2：编程方式设置

```python
# 通过字典直接设置配置
config = decomposer.set_resource_config({
    "backend_count": 3,
    "backend_availability": 100.0,
    "test_count": 1,
    "test_availability": 100.0,
    "target_date": "2026-06-30",
    "skill_level": "average",
})
```

---

### 方式 3：多场景对比（人数不确定时）

```python
# 当用户说"不确定"时，生成多个场景对比
scenarios = decomposer.generate_scenarios()

for scenario in scenarios:
    print(f"场景：{scenario['name']}")
    print(f"配置：{scenario['config']}")
    print(f"预估工期：{scenario['estimated_weeks']}")
    print(f"说明：{scenario['notes']}")
    print()
```

**输出示例：**

```
场景：精简版
配置：ResourceConfig(backend_count=2, test_count=1, ...)
预估工期：12 周
说明：适合小团队，工期较长但人员压力小

场景：标准版
配置：ResourceConfig(backend_count=3, test_count=1, ...)
预估工期：9 周
说明：推荐配置，工期和负载平衡

场景：加速版
配置：ResourceConfig(backend_count=4, test_count=2, ...)
预估工期：6 周
说明：适合紧急项目，需要更多人力资源
```

---

## 📊 资源配置对象结构

```python
class ResourceConfig(BaseModel):
    backend_count: Optional[int] = None        # 后端开发人数
    backend_availability: float = 100.0        # 后端可用时间百分比（0-100）
    test_count: Optional[int] = None           # 测试人数
    test_availability: float = 100.0           # 测试可用时间百分比（0-100）
    frontend_count: int = 0                    # 前端开发人数
    product_count: int = 0                     # 产品人数
    target_date: Optional[str] = None          # 期望完工日期（YYYY-MM-DD）
    milestones: Optional[List[str]] = None     # 固定里程碑列表
    skill_level: str = "average"               # 团队技能水平：average/senior/mixed
```

---

## 🔄 甘特图演算逻辑

收集资源配置后，TaskDecomposer 会：

1. **计算总工作量** - 基于任务分解结果（人天）
2. **计算每周可用工时** - 基于人数 × 可用时间百分比
3. **分配任务到周** - 考虑依赖关系和关键路径
4. **生成甘特图** - 按责任人分组显示
5. **输出负载统计** - 识别峰值负载周次

**计算公式：**

```
每周可用工时 = 人数 × 5 天 × 可用时间百分比

总工期（周） = 总工作量（人天） / 每周可用工时

峰值负载周 = max(每周工作量)
```

---

## 🎯 使用场景

### 场景 1：人数确定

→ 使用 **交互式问答** 或 **编程方式** 设置配置
→ 生成 **精确甘特图**

### 场景 2：人数不确定

→ 使用 **多场景对比** 模式
→ 输出 2-3 个场景供决策
→ 支持 What-if 分析

### 场景 3：有固定截止日期

→ 设置 `target_date`
→ 倒推需要的人数配置
→ 给出人员建议

---

## 📁 输出文件

TaskDecomposer v3.3 生成的 Excel 文件包含：

1. **接口级任务拆分** - 26 个接口，10 列
2. **DAG 依赖关系图** - 接口依赖 + 可并行接口
3. **甘特图 - 后端 1** - 按责任人分组
4. **甘特图 - 后端 2** - 按责任人分组
5. **甘特图 - 后端 3** - 按责任人分组
6. **甘特图 - 测试 1** - 按责任人分组
7. **周负载统计** - 各角色工作量分布
8. **可并行接口清单** - 每周可同时开发的接口
9. **汇总统计** - 关键指标汇总

---

## 🚀 未来计划（v3.4+）

- [ ] 支持前端角色甘特图
- [ ] 支持动态调整（人数变化后一键重算）
- [ ] 导出 Project/MPP 格式
- [ ] 与项目管理工具集成（Jira、TAPD 等）
- [ ] 自动化更新（定期同步实际进度）

---

## 📝 版本历史

- **v3.3** (2026-04-10) - 新增交互式资源配置收集
- **v3.2** (2026-04-09) - 按责任人分组的甘特图
- **v3.1** (2026-04-08) - DAG 依赖关系图增强
- **v3.0** (2026-04-07) - 初始版本

---

**作者：** AgenticX Team  
**License:** Apache 2.0
