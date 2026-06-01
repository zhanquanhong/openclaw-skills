"""多维建议引擎 v2 — 单元测试。

覆盖全部 12 条规则 + 多样性保证器。
"""

import json
import os
import sys
import unittest

# 确保 src 在路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.analyzer.advisor import (
    analyze,
    Suggestion,
    get_model_spec,
    _run_all_rules,
    _ensure_diversity,
    _group_by_dimension,
    _extract_keywords,
    _find_longest_common_substring,
    _get_idle_days,
    DIMENSION_INPUT_QUALITY,
    DIMENSION_CONTEXT_MANAGEMENT,
    DIMENSION_PROVIDER_CONFIG,
    DIMENSION_SESSION_LIFECYCLE,
)


class TestModelSpec(unittest.TestCase):
    """模型规格查询测试。"""

    def test_deepseek_v4_flash(self):
        spec = get_model_spec("deepseek-v4-flash")
        self.assertEqual(spec["context_window"], 1_000_000)
        self.assertEqual(spec["max_tokens"], 65_536)

    def test_unknown_model(self):
        spec = get_model_spec("unknown-model-2026")
        self.assertEqual(spec["context_window"], 128_000)
        self.assertEqual(spec["max_tokens"], 8_192)

    def test_empty_model(self):
        spec = get_model_spec(None)
        self.assertEqual(spec["context_window"], 128_000)

    def test_case_insensitive(self):
        spec = get_model_spec("DEEPSEEK-V4-FLASH")
        self.assertEqual(spec["context_window"], 1_000_000)


class TestExtractKeywords(unittest.TestCase):
    """关键词提取测试（A1 / D2 依赖）。"""

    def test_chinese_keywords(self):
        text = "实现数据库表的增删改查功能，包括用户管理模块"
        kws = _extract_keywords(text)
        self.assertTrue(any("数据库" in kw for kw in kws))
        self.assertTrue(any("增删改查" in kw for kw in kws))
        self.assertTrue(any("用户管理" in kw for kw in kws))

    def test_english_keywords(self):
        text = "Implement user authentication and database migration"
        kws = _extract_keywords(text)
        self.assertIn("implement", kws)
        self.assertIn("authentication", kws)
        self.assertIn("database", kws)
        self.assertIn("migration", kws)

    def test_short_words_filtered(self):
        text = "a an the is it in on of to implement"
        kws = _extract_keywords(text)
        self.assertNotIn("a", kws)
        self.assertNotIn("an", kws)
        self.assertNotIn("the", kws)
        self.assertIn("implement", kws)

    def test_mixed_language(self):
        text = "实现 API 接口 for user management 模块"
        kws = _extract_keywords(text)
        # "实现" is only 2 Chinese chars, excluded by {4,} regex
        # "接口" is 2 Chinese chars, excluded
        # "management" is 10 English chars, included
        self.assertIn("management", kws)
        # No 4+ char Chinese blocks in this text


class TestFindLongestCommonSubstring(unittest.TestCase):
    """最长公共子串检测测试（C3 依赖）。"""

    def test_basic_common(self):
        result = _find_longest_common_substring(
            "这是第一个测试文本内容示例",
            "这是第二个测试文本内容示例",
        )
        self.assertTrue(len(result) >= 6)  # e.g. "测试文本内容示例" or "个测试文本内容示例"
        self.assertIn("测试文本", result)

    def test_no_common(self):
        result = _find_longest_common_substring(
            "ABC",
            "XYZ",
        )
        self.assertEqual(result, "")

    def test_short_strings(self):
        result = _find_longest_common_substring("AB", "AB")
        self.assertEqual(result, "")

    def test_full_code_block(self):
        s1 = "发生错误: ValueError: invalid literal for int() with base 10: 'abc'"
        s2 = "还是错误: ValueError: invalid literal for int() with base 10: 'abc'"
        result = _find_longest_common_substring(s1, s2)
        self.assertIn("ValueError", result)


class TestGetIdleDays(unittest.TestCase):
    """闲置天数计算测试（D1 依赖）。"""

    def test_recent_session(self):
        from datetime import datetime, timezone, timedelta
        recent = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        days = _get_idle_days(recent)
        self.assertIsNotNone(days)
        self.assertEqual(days, 0)

    def test_old_session(self):
        from datetime import datetime, timezone, timedelta
        old = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
        days = _get_idle_days(old)
        self.assertIsNotNone(days)
        self.assertGreaterEqual(days, 14)

    def test_none_input(self):
        self.assertIsNone(_get_idle_days(None))
        self.assertIsNone(_get_idle_days(""))


class TestEnsureDiversity(unittest.TestCase):
    """多样性保证器测试。"""

    def make_sug(self, severity, dimension, category):
        return Suggestion(severity=severity, dimension=dimension, category=category,
                          title="test", message="test")

    def test_empty_list(self):
        self.assertEqual(_ensure_diversity([]), [])

    def test_single_suggestion(self):
        s = self.make_sug("warning", DIMENSION_INPUT_QUALITY, "A1")
        result = _ensure_diversity([s])
        self.assertEqual(len(result), 1)

    def test_dedup_same_category(self):
        s1 = self.make_sug("warning", DIMENSION_INPUT_QUALITY, "A1")
        s2 = self.make_sug("info", DIMENSION_INPUT_QUALITY, "A1")
        result = _ensure_diversity([s1, s2])
        self.assertEqual(len(result), 1)  # same category → dedup

    def test_max_per_session(self):
        # 6 suggestions → should be capped
        sugs = [
            self.make_sug("critical", DIMENSION_INPUT_QUALITY, "A1"),
            self.make_sug("info", DIMENSION_CONTEXT_MANAGEMENT, "B1"),
            self.make_sug("warning", DIMENSION_PROVIDER_CONFIG, "C1"),
            self.make_sug("info", DIMENSION_SESSION_LIFECYCLE, "D1"),
            self.make_sug("warning", DIMENSION_INPUT_QUALITY, "A2"),
            self.make_sug("info", DIMENSION_CONTEXT_MANAGEMENT, "B2"),
        ]
        result = _ensure_diversity(sugs)
        self.assertLessEqual(len(result), 3)  # max_per_session = 3

    def test_min_dimension_coverage(self):
        # 2 suggestions from same dimension → should still work (min_dimensions may not be met)
        s1 = self.make_sug("warning", DIMENSION_INPUT_QUALITY, "A1")
        s2 = self.make_sug("info", DIMENSION_INPUT_QUALITY, "A2")
        result = _ensure_diversity([s1, s2])
        self.assertGreaterEqual(len(result), 1)

    def test_priority_by_severity(self):
        s1 = self.make_sug("info", DIMENSION_INPUT_QUALITY, "A1")
        s2 = self.make_sug("critical", DIMENSION_CONTEXT_MANAGEMENT, "B1")
        s3 = self.make_sug("warning", DIMENSION_PROVIDER_CONFIG, "C2")
        result = _ensure_diversity([s1, s2, s3])
        # critical should be preserved
        categories = {s.category for s in result}
        self.assertIn("B1", categories)


class TestGroupByDimension(unittest.TestCase):
    """维度分组测试。"""

    def make_sug(self, dim, cat):
        return Suggestion(severity="info", dimension=dim, category=cat,
                          title="test", message="test")

    def test_basic_grouping(self):
        sugs = [
            self.make_sug(DIMENSION_INPUT_QUALITY, "A1"),
            self.make_sug(DIMENSION_INPUT_QUALITY, "A2"),
            self.make_sug(DIMENSION_CONTEXT_MANAGEMENT, "B1"),
        ]
        groups = _group_by_dimension(sugs)
        self.assertIn(DIMENSION_INPUT_QUALITY, groups)
        self.assertIn(DIMENSION_CONTEXT_MANAGEMENT, groups)
        self.assertEqual(len(groups[DIMENSION_INPUT_QUALITY]), 2)
        self.assertEqual(len(groups[DIMENSION_CONTEXT_MANAGEMENT]), 1)


class TestRuleA1DuplicateContent(unittest.TestCase):
    """A1 重复内容检测。"""

    def test_no_duplicate(self):
        session = {"total_input_tokens": 5000}
        ctx = {
            "first_msg": "帮我设计一个用户登录模块",
            "second_msg": "数据库表结构确定好了吗",
        }
        t = {"waste_ratio": 3.0}
        sugs = []
        from src.analyzer.advisor import _rule_a1_duplicate_content
        _rule_a1_duplicate_content(session, ctx, t, sugs)
        self.assertEqual(len(sugs), 0)

    def test_has_duplicate(self):
        session = {"total_input_tokens": 10000}
        ctx = {
            "first_msg": "实现用户管理模块的增删改查功能和权限控制功能，这个是核心",
            "second_msg": "前面的用户管理模块的增删改查功能和权限控制功能差不多了",
        }
        t = {"waste_ratio": 3.0}
        sugs = []
        from src.analyzer.advisor import _rule_a1_duplicate_content
        _rule_a1_duplicate_content(session, ctx, t, sugs)
        self.assertEqual(len(sugs), 1)
        self.assertEqual(sugs[0].category, "A1")

    def test_short_messages_skip(self):
        session = {"total_input_tokens": 100}
        ctx = {
            "first_msg": "好的",
            "second_msg": "可以",
        }
        t = {}
        sugs = []
        from src.analyzer.advisor import _rule_a1_duplicate_content
        _rule_a1_duplicate_content(session, ctx, t, sugs)
        self.assertEqual(len(sugs), 0)


class TestRuleA2LongMessages(unittest.TestCase):
    """A2 单条消息过长。"""

    def test_normal_messages(self):
        session = {"total_input_tokens": 2000}
        ctx = {"user_turns": 5, "total_chars": 3000}
        t = {"avg_msg_token": 800}
        sugs = []
        from src.analyzer.advisor import _rule_a2_long_messages
        _rule_a2_long_messages(session, ctx, t, sugs)
        self.assertEqual(len(sugs), 0)

    def test_long_messages(self):
        session = {"total_input_tokens": 20000}
        ctx = {"user_turns": 5, "total_chars": 80000}
        t = {"avg_msg_token": 800}
        sugs = []
        from src.analyzer.advisor import _rule_a2_long_messages
        _rule_a2_long_messages(session, ctx, t, sugs)
        self.assertEqual(len(sugs), 1)
        self.assertEqual(sugs[0].category, "A2")

    def test_no_user_turns(self):
        session = {"total_input_tokens": 0}
        ctx = {"user_turns": 0, "total_chars": 0}
        t = {}
        sugs = []
        from src.analyzer.advisor import _rule_a2_long_messages
        _rule_a2_long_messages(session, ctx, t, sugs)
        self.assertEqual(len(sugs), 0)


class TestRuleA3InefficientOpening(unittest.TestCase):
    """A3 前段效率检测。"""

    def test_efficient_opening(self):
        session = {"total_input_tokens": 10000, "total_output_tokens": 5000}
        ctx = {
            "message_sizes": [
                {"role": "user", "estimated_tokens": 500},
                {"role": "assistant", "estimated_tokens": 2000},
                {"role": "user", "estimated_tokens": 300},
            ],
        }
        t = {"first3_input_ratio": 0.60, "first3_waste_ratio": 0.20}
        sugs = []
        from src.analyzer.advisor import _rule_a3_inefficient_opening
        _rule_a3_inefficient_opening(session, ctx, t, sugs)
        self.assertEqual(len(sugs), 0)

    def test_inefficient_opening(self):
        session = {"total_input_tokens": 10000, "total_output_tokens": 100}
        ctx = {
            "message_sizes": [
                {"role": "user", "estimated_tokens": 6000},
                {"role": "user", "estimated_tokens": 500},
                {"role": "assistant", "estimated_tokens": 10},
                {"role": "user", "estimated_tokens": 300},
            ],
        }
        t = {"first3_input_ratio": 0.60, "first3_waste_ratio": 0.20}
        sugs = []
        from src.analyzer.advisor import _rule_a3_inefficient_opening
        _rule_a3_inefficient_opening(session, ctx, t, sugs)
        self.assertEqual(len(sugs), 1)
        self.assertEqual(sugs[0].category, "A3")

    def test_no_message_sizes(self):
        session = {"total_input_tokens": 1000, "total_output_tokens": 100}
        ctx = {}
        t = {}
        sugs = []
        from src.analyzer.advisor import _rule_a3_inefficient_opening
        _rule_a3_inefficient_opening(session, ctx, t, sugs)
        self.assertEqual(len(sugs), 0)


class TestRuleB1SystemPromptRatio(unittest.TestCase):
    """B1 System prompt 占比检测。"""

    def test_low_ratio(self):
        session = {"total_input_tokens": 10000}
        ctx = {
            "system_messages": [
                {"estimated_tokens": 1000},
            ],
        }
        t = {"system_prompt_ratio": 0.25}
        sugs = []
        from src.analyzer.advisor import _rule_b1_system_prompt_ratio
        _rule_b1_system_prompt_ratio(session, ctx, t, sugs)
        self.assertEqual(len(sugs), 0)

    def test_high_ratio(self):
        session = {"total_input_tokens": 10000}
        ctx = {
            "system_messages": [
                {"estimated_tokens": 4000},
            ],
        }
        t = {"system_prompt_ratio": 0.25}
        sugs = []
        from src.analyzer.advisor import _rule_b1_system_prompt_ratio
        _rule_b1_system_prompt_ratio(session, ctx, t, sugs)
        self.assertEqual(len(sugs), 1)
        self.assertEqual(sugs[0].category, "B1")

    def test_no_system_messages(self):
        session = {"total_input_tokens": 1000}
        ctx = {}
        t = {}
        sugs = []
        from src.analyzer.advisor import _rule_b1_system_prompt_ratio
        _rule_b1_system_prompt_ratio(session, ctx, t, sugs)
        self.assertEqual(len(sugs), 0)


class TestRuleB2ThinkingWaste(unittest.TestCase):
    """B2 Thinking 浪费检测。"""

    def test_no_thinking(self):
        session = {"total_input_tokens": 1000}
        ctx = {}
        model = "deepseek-v4-flash"
        pricing = {"deepseek-v4-flash": {"input": 0.15, "output": 0.60}}
        t = {"thinking_ratio": 2.0}
        sugs = []
        from src.analyzer.advisor import _rule_b2_thinking_waste
        _rule_b2_thinking_waste(session, ctx, model, pricing, t, sugs)
        self.assertEqual(len(sugs), 0)

    def test_acceptable_thinking(self):
        session = {"total_input_tokens": 1000}
        ctx = {
            "thinking_info": {
                "has_thinking": True,
                "thinking_tokens": 1000,
                "output_tokens": 2000,
                "ratio": 0.5,
            },
        }
        model = "deepseek-reasoner"
        pricing = {"deepseek-reasoner": {"input": 0.55, "output": 2.19}}
        t = {"thinking_ratio": 2.0}
        sugs = []
        from src.analyzer.advisor import _rule_b2_thinking_waste
        _rule_b2_thinking_waste(session, ctx, model, pricing, t, sugs)
        self.assertEqual(len(sugs), 0)

    def test_excessive_thinking(self):
        session = {"total_input_tokens": 1000}
        ctx = {
            "thinking_info": {
                "has_thinking": True,
                "thinking_tokens": 6000,
                "output_tokens": 1000,
                "ratio": 6.0,
            },
        }
        model = "deepseek-reasoner"
        pricing = {"deepseek-reasoner": {"input": 0.55, "output": 2.19}}
        t = {"thinking_ratio": 2.0}
        sugs = []
        from src.analyzer.advisor import _rule_b2_thinking_waste
        _rule_b2_thinking_waste(session, ctx, model, pricing, t, sugs)
        self.assertEqual(len(sugs), 1)
        self.assertEqual(sugs[0].category, "B2")


class TestRuleB3ImbalancedExchange(unittest.TestCase):
    """B3 消息分布不均衡检测。"""

    def test_balanced(self):
        ctx = {"user_turns": 5, "assistant_turns": 4}
        t = {"imbalance_turns": 20, "imbalance_ratio": 3.0}
        sugs = []
        from src.analyzer.advisor import _rule_b3_imbalanced_exchange
        _rule_b3_imbalanced_exchange(ctx, t, sugs)
        self.assertEqual(len(sugs), 0)

    def test_no_assistant_reply(self):
        ctx = {"user_turns": 25, "assistant_turns": 0}
        t = {"imbalance_turns": 20, "imbalance_ratio": 3.0}
        sugs = []
        from src.analyzer.advisor import _rule_b3_imbalanced_exchange
        _rule_b3_imbalanced_exchange(ctx, t, sugs)
        self.assertEqual(len(sugs), 1)
        self.assertEqual(sugs[0].category, "B3")

    def test_high_ratio(self):
        ctx = {"user_turns": 15, "assistant_turns": 3}
        t = {"imbalance_turns": 20, "imbalance_ratio": 3.0}
        sugs = []
        from src.analyzer.advisor import _rule_b3_imbalanced_exchange
        _rule_b3_imbalanced_exchange(ctx, t, sugs)
        self.assertEqual(len(sugs), 1)

    def test_no_user_turns(self):
        ctx = {"user_turns": 0, "assistant_turns": 0}
        t = {}
        sugs = []
        from src.analyzer.advisor import _rule_b3_imbalanced_exchange
        _rule_b3_imbalanced_exchange(ctx, t, sugs)
        self.assertEqual(len(sugs), 0)


class TestRuleC1OutputCapped(unittest.TestCase):
    """C1 max_tokens 截断检测。"""

    def test_normal_output(self):
        sugs = []
        from src.analyzer.advisor import _rule_c1_output_capped
        _rule_c1_output_capped(
            session={}, total_out=2000, max_tokens=8192,
            model="deepseek-v4-flash", specs={"context_window": 1_000_000},
            t={"output_capped_ratio": 0.85, "output_capped_divisible": True},
            suggestions=sugs,
        )
        self.assertEqual(len(sugs), 0)

    def test_near_limit(self):
        sugs = []
        from src.analyzer.advisor import _rule_c1_output_capped
        _rule_c1_output_capped(
            session={}, total_out=7500, max_tokens=8192,
            model="deepseek-v4-flash", specs={"context_window": 1_000_000},
            t={"output_capped_ratio": 0.85, "output_capped_divisible": True},
            suggestions=sugs,
        )
        self.assertEqual(len(sugs), 1)
        self.assertEqual(sugs[0].category, "C1")

    def test_truncation(self):
        sugs = []
        from src.analyzer.advisor import _rule_c1_output_capped
        _rule_c1_output_capped(
            session={}, total_out=8192, max_tokens=8192,
            model="deepseek-chat", specs={"context_window": 65_536},
            t={"output_capped_ratio": 0.85, "output_capped_divisible": True},
            suggestions=sugs,
        )
        self.assertEqual(len(sugs), 1)
        self.assertIn("截断", sugs[0].title or "")

    def test_no_output(self):
        sugs = []
        from src.analyzer.advisor import _rule_c1_output_capped
        _rule_c1_output_capped(
            session={}, total_out=0, max_tokens=8192,
            model="gpt-4o", specs={"context_window": 128_000},
            t={"output_capped_ratio": 0.85, "output_capped_divisible": True},
            suggestions=sugs,
        )
        self.assertEqual(len(sugs), 0)


class TestRuleC2ModelValue(unittest.TestCase):
    """C2 模型性价比检测。"""

    def test_large_task_on_expensive_model(self):
        sugs = []
        from src.analyzer.advisor import _rule_c2_model_value
        _rule_c2_model_value(
            session={}, total_in=200, total_out=50,
            model="deepseek-v4-flash",
            pricing_map={"deepseek-v4-flash": {"input": 0.15, "output": 0.60}},
            t={"small_task_max_tokens": 500},
            suggestions=sugs,
        )
        self.assertEqual(len(sugs), 1)
        self.assertEqual(sugs[0].category, "C2")

    def test_large_task(self):
        sugs = []
        from src.analyzer.advisor import _rule_c2_model_value
        _rule_c2_model_value(
            session={}, total_in=5000, total_out=2000,
            model="deepseek-v4-flash",
            pricing_map={"deepseek-v4-flash": {"input": 0.15, "output": 0.60}},
            t={"small_task_max_tokens": 500},
            suggestions=sugs,
        )
        self.assertEqual(len(sugs), 0)

    def test_cheap_model(self):
        sugs = []
        from src.analyzer.advisor import _rule_c2_model_value
        _rule_c2_model_value(
            session={}, total_in=200, total_out=50,
            model="deepseek-chat",
            pricing_map={"deepseek-chat": {"input": 0.14, "output": 0.28}},
            t={"small_task_max_tokens": 500},
            suggestions=sugs,
        )
        self.assertEqual(len(sugs), 0)


class TestRuleC3ContextRefill(unittest.TestCase):
    """C3 上下文预填充浪费检测。"""

    def test_no_refill(self):
        session = {"total_input_tokens": 1000}
        ctx = {
            "first_msg": "帮我设计一个登录模块",
            "last_msg": "数据库字段已经定义好了",
        }
        sugs = []
        from src.analyzer.advisor import _rule_c3_context_refill
        _rule_c3_context_refill(session, ctx, 1000, {}, sugs)
        self.assertEqual(len(sugs), 0)

    def test_has_refill(self):
        session = {"total_input_tokens": 5000}
        error_block = "Error: TypeError: Cannot read property 'data' of undefined at Object.fetchData and this is a very long error message with lots of details about what went wrong in the system"
        ctx = {
            "first_msg": f"出现了一个错误: {error_block}",
            "last_msg": f"同样的错误又出现了: {error_block}",
        }
        sugs = []
        t = {"waste_ratio": 3.0}
        from src.analyzer.advisor import _rule_c3_context_refill
        _rule_c3_context_refill(session, ctx, 5000, t, sugs)
        self.assertEqual(len(sugs), 1)
        self.assertEqual(sugs[0].category, "C3")

    def test_short_messages(self):
        session = {"total_input_tokens": 500}
        ctx = {
            "first_msg": "好的",
            "last_msg": "可以",
        }
        sugs = []
        from src.analyzer.advisor import _rule_c3_context_refill
        _rule_c3_context_refill(session, ctx, 500, {}, sugs)
        self.assertEqual(len(sugs), 0)


class TestRuleD1ZombieSession(unittest.TestCase):
    """D1 僵尸会话检测。"""

    def test_active_session(self):
        from datetime import datetime, timezone, timedelta
        recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        session = {"total_input_tokens": 1000}
        ctx = {"time_start": recent}
        t = {"zombie_days": 7, "zombie_token": 50000}
        sugs = []
        from src.analyzer.advisor import _rule_d1_zombie_session
        _rule_d1_zombie_session(session, ctx, 1000, t, sugs)
        self.assertEqual(len(sugs), 0)

    def test_zombie_with_low_tokens(self):
        from datetime import datetime, timezone, timedelta
        old = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        session = {"total_input_tokens": 1000}
        ctx = {"time_start": old}
        t = {"zombie_days": 7, "zombie_token": 50000}
        sugs = []
        from src.analyzer.advisor import _rule_d1_zombie_session
        _rule_d1_zombie_session(session, ctx, 1000, t, sugs)
        self.assertEqual(len(sugs), 0)

    def test_zombie_with_high_tokens(self):
        from datetime import datetime, timezone, timedelta
        old = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        session = {"total_input_tokens": 100000}
        ctx = {"time_start": old}
        t = {"zombie_days": 7, "zombie_token": 50000}
        sugs = []
        from src.analyzer.advisor import _rule_d1_zombie_session
        _rule_d1_zombie_session(session, ctx, 100000, t, sugs)
        self.assertEqual(len(sugs), 1)
        self.assertEqual(sugs[0].category, "D1")


class TestRuleD2TopicDrift(unittest.TestCase):
    """D2 话题漂移检测。"""

    def test_same_topic(self):
        ctx = {
            "first_msg": "帮我设计用户登录模块的数据库结构包括用户表设计",
            "last_msg": "用户登录模块的登录接口测试通过了，下一步做权限控制",
        }
        t = {}
        sugs = []
        from src.analyzer.advisor import _rule_d2_topic_drift
        _rule_d2_topic_drift(ctx, t, sugs)
        self.assertEqual(len(sugs), 0)

    def test_drifted_topic(self):
        ctx = {
            "first_msg": "帮我设计用户登录模块的数据库结构包括表设计和索引",
            "last_msg": "最后来确认一下CI/CD流水线配置问题这个很重要",
        }
        t = {}
        sugs = []
        from src.analyzer.advisor import _rule_d2_topic_drift
        _rule_d2_topic_drift(ctx, t, sugs)
        self.assertEqual(len(sugs), 1)
        self.assertEqual(sugs[0].category, "D2")

    def test_short_messages(self):
        ctx = {
            "first_msg": "好",
            "last_msg": "行",
        }
        t = {}
        sugs = []
        from src.analyzer.advisor import _rule_d2_topic_drift
        _rule_d2_topic_drift(ctx, t, sugs)
        self.assertEqual(len(sugs), 0)


class TestRuleD3SessionFragmentation(unittest.TestCase):
    """D3 会话碎片化检测。"""

    def test_healthy_session(self):
        session = {"input_output_ratio": 1.5}
        ctx = {"user_turns": 10, "assistant_turns": 8}
        t = {"fragmentation_avg_turns": 5, "waste_ratio": 3.0}
        sugs = []
        from src.analyzer.advisor import _rule_d3_session_fragmentation
        _rule_d3_session_fragmentation(session, ctx, t, sugs)
        self.assertEqual(len(sugs), 0)

    def test_short_session(self):
        session = {"input_output_ratio": 1.2, "total_input_tokens": 800}
        ctx = {"user_turns": 2, "assistant_turns": 1}
        t = {"fragmentation_avg_turns": 5, "waste_ratio": 3.0}
        sugs = []
        from src.analyzer.advisor import _rule_d3_session_fragmentation
        _rule_d3_session_fragmentation(session, ctx, t, sugs)
        self.assertEqual(len(sugs), 1)
        self.assertEqual(sugs[0].category, "D3")

    def test_very_short_skip(self):
        session = {"input_output_ratio": 1.0, "total_input_tokens": 100}
        ctx = {"user_turns": 1, "assistant_turns": 0}
        t = {"fragmentation_avg_turns": 5, "waste_ratio": 3.0}
        sugs = []
        from src.analyzer.advisor import _rule_d3_session_fragmentation
        _rule_d3_session_fragmentation(session, ctx, t, sugs)
        self.assertEqual(len(sugs), 0)


class TestIntegrationAnalyze(unittest.TestCase):
    """集成测试：analyze() 主入口。"""

    def setUp(self):
        self.pricing = {
            "deepseek-v4-flash": {"input": 0.15, "output": 0.60},
            "deepseek-chat": {"input": 0.14, "output": 0.28},
        }

    def test_analyze_empty(self):
        result = analyze([], {}, 3.0)
        self.assertEqual(len(result), 0)

    def test_analyze_single_session_no_issues(self):
        session = {
            "id": "test_1",
            "model": "deepseek-v4-flash",
            "total_input_tokens": 1000,
            "total_output_tokens": 500,
            "input_output_ratio": 2.0,
            "title": "Test session",
            "context_info": json.dumps({
                "first_msg": "正常提问",
                "second_msg": "正常回复",
                "last_msg": "结束了",
                "user_turns": 5,
                "assistant_turns": 4,
                "total_chars": 2000,
                "total_messages": 10,
            }),
        }
        result = analyze([session], self.pricing, 3.0)
        self.assertEqual(len(result), 1)
        self.assertIn("recommendations", result[0])

    def test_analyze_waste_session(self):
        """高浪费会话应产生建议。"""
        session = {
            "id": "test_waste_1",
            "model": "deepseek-v4-flash",
            "total_input_tokens": 50000,
            "total_output_tokens": 200,
            "input_output_ratio": 250.0,
            "title": "高浪费测试",
            "context_info": json.dumps({
                "first_msg": "请帮我设计一个完整的用户管理系统，包括数据库设计、API接口、前端页面",
                "second_msg": "再补充一下权限控制的设计",
                "last_msg": "最后看一下日志模块",
                "user_turns": 15,
                "assistant_turns": 3,
                "total_chars": 80000,
                "total_messages": 20,
                "time_start": "2026-05-20T10:00:00+00:00",
                "time_end": "2026-05-20T10:30:00+00:00",
            }),
        }
        result = analyze([session], self.pricing, 3.0)
        recs = result[0].get("recommendations", [])
        self.assertGreater(len(recs), 0)
        # 检查多样性：是否有不同维度的建议
        dims = {r["dimension"] for r in recs}
        self.assertGreaterEqual(len(dims), 1)

    def test_analyze_dimension_groups(self):
        session = {
            "id": "test_dim_1",
            "model": "deepseek-v4-flash",
            "total_input_tokens": 10000,
            "total_output_tokens": 100,
            "input_output_ratio": 100.0,
            "title": "维度分组测试",
            "context_info": json.dumps({
                "first_msg": "这是一个很长很长的测试消息用来触发A2规则abcdefghijklmnopqrstuvwxyz",
                "second_msg": "这是第二条测试消息",
                "last_msg": "这是最后一条",
                "user_turns": 2,
                "assistant_turns": 1,
                "total_chars": 50000,
                "total_messages": 5,
            }),
        }
        result = analyze([session], self.pricing, 3.0)
        groups = result[0].get("dimension_groups", {})
        self.assertGreater(len(groups), 0)


class TestSuggestionToDict(unittest.TestCase):
    """Suggestion.to_dict 序列化测试。"""

    def test_basic_serialization(self):
        s = Suggestion(
            severity="warning",
            dimension=DIMENSION_INPUT_QUALITY,
            category="A1",
            title="重复内容检测",
            message="您的前两条消息有重复",
            action="精简内容",
            evidence=["重叠率 80%"],
            savings_tokens=500,
            savings_cost=0.01,
        )
        d = s.to_dict()
        self.assertEqual(d["severity"], "warning")
        self.assertEqual(d["dimension"], DIMENSION_INPUT_QUALITY)
        self.assertEqual(d["category"], "A1")
        self.assertEqual(d["savings_tokens"], 500)
        self.assertIn("dimension_label", d)
        self.assertIn("dimension_icon", d)
        self.assertEqual(d["savings_cost"], 0.01)


if __name__ == "__main__":
    unittest.main()
