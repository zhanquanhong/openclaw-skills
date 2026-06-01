# token-watcher v1.2 — 多维建议引擎设计文档

## 概述

从"3 个阈值判断"升级为"12 条分维度规则 + 多样性保证器"。
每条建议必须有具体数据证据和可执行操作，杜绝万金油建议。

## 核心改动

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `src/analyzer/advisor.py` | 重写 | 12 条规则 + 多样性保证器 + 按维度分组 |
| `src/collector/openclaw.py` | 增强 | 消息级 Token 提取、System prompt 识别、Thinking 检测 |
| `src/config.py` | 修改 | 新增 12 条规则的阈值参数 |
| `templates/dashboard.html` | 修改 | 建议面板按维度分组展示 |
| `src/main.py` | 小幅修改 | API 返回建议的维度字段 |
| `tests/test_advisor.py` | 重写 | 覆盖全部 12 条规则 |

## 架构

```
collector/openclaw.py  →  context_info 扩展字段
         ↓
analyzer/advisor.py    →  12 条规则 + 多样性保证
         ↓
main.py API            →  recommendations 按维度分组
         ↓
dashboard.html         →  4 维度面板展示
```

## 12 条规则摘要

| ID | 维度 | 规则 | 数据依赖 | 现有数据 |
|----|------|------|---------|---------|
| A1 | 输入质量 | 重复内容检测 | first_msg / second_msg | ✅ 已有 |
| A2 | 输入质量 | 单条消息过长 | total_chars / user_turns | ✅ 已有 |
| A3 | 输入质量 | 无效开场/低效前段 | 前 3 轮 token 分布 | ❌ 需增强 |
| B1 | 上下文管理 | System prompt 占比异常 | system 消息 | ❌ 需增强 |
| B2 | 上下文管理 | Thinking token 浪费 | assistant 消息解析 | ❌ 需增强 |
| B3 | 上下文管理 | 消息分布极度不均衡 | user_turns / assistant_turns | ✅ 已有 |
| C1 | 模型配置 | max_tokens 截断 | model_spec + output | ✅ 已有 |
| C2 | 模型配置 | 性价比模型选择 | pricing + 任务复杂度 | ✅ 已有 |
| C3 | 模型配置 | 上下文预填充浪费 | 跨轮重复文本 | ❌ 需增强 |
| D1 | 会话生命周期 | 僵尸会话 | start_time + 闲置天数 | ✅ 已有 |
| D2 | 会话生命周期 | 话题漂移 | first_msg vs last_msg | ✅ 已有 |
| D3 | 会话生命周期 | 会话碎片化 | 30 天会话总数 | ✅ 已有 |

**9 条以现有数据即可运行；3 条(A3/B1/B2)依赖增强后的 transcript 解析**

## context_info 扩展字段

```json
{
  "first_msg": "...",
  "second_msg": "...",
  "last_msg": "...",
  "user_turns": 12,
  "assistant_turns": 8,
  "total_messages": 22,
  "total_chars": 45000,
  "time_start": "...",
  "time_end": "...",
  "system_messages": [{"content": "...", "estimated_tokens": 4200}],
  "message_sizes": [
    {"role": "system", "estimated_tokens": 4200},
    {"role": "user", "estimated_tokens": 1200},
    {"role": "assistant", "estimated_tokens": 800},
    ...
  ],
  "thinking_info": {"has_thinking": true, "thinking_tokens": 8000, "output_tokens": 3000}
}
```

## 多样性保证器

```python
def _ensure_diversity(suggestions, max_per_session=3):
    # 1. 同一会话最多 N 条
    if len(suggestions) > max_per_session:
        # 按 severity 降序, 覆盖最多维度
    # 2. 相同 category 只保留 1 条
    # 3. 必须覆盖 ≥2 个维度
    # 4. 无建议时不凑数
```

## 实施顺序

1. ✅ `<config.py>` — 新增阈值参数（不改已有）
2. ✅ `<advisor.py>` — 重写规则引擎 + 多样性保证器
3. ✅ `<collector/openclaw.py>` — 增强 transcript 解析
4. ✅ `<dashboard.html>` — 维度分组展示
5. ✅ `<main.py>` — API 维度分组响应格式
6. ✅ `<tests/test_advisor.py>` — 65 项测试全覆盖（含 12 条规则 + 集成分组 + 多样性）
7. ✅ 端到端验证 — 81 项测试通过 + 方案-代码一致性核对

## 验证结果

| 维度 | 结果 |
|------|------|
| 12 条规则全部实现 | ✅ |
| 4 个维度全覆盖 | ✅ |
| 多样性保证器 | ✅（单会话 ≤3 条, 去重, 覆盖 ≥2 维度） |
| 维度分组 API | ✅（`dimension_groups` 按 4 维度组织） |
| 前端按维度展示 | ✅（维度标题 + 图标 + 色标） |
| Transcript 增强解析 | ✅（`system_messages`, `message_sizes`, `thinking_info`） |
| 单元测试 | ✅ 65 项新增 + 16 项已有 = 81 项全部通过 |
| 方案-代码一致性 | ✅ |
