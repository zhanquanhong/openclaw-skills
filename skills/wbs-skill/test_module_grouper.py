#!/usr/bin/env python3
"""模块归组引擎测试 - v4.0"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.module_grouper import ModuleGrouper, ModuleResult


class TestModuleGrouper(unittest.TestCase):

    def setUp(self):
        self.grouper = ModuleGrouper()

    # ==================== 内容关键词匹配 ====================

    def test_match_user_module(self):
        r = self.grouper._match_by_content("新增用户列表查询接口")
        self.assertEqual(r.module_name, "用户中心")
        self.assertGreater(r.confidence, 0.5)
        self.assertEqual(r.match_source, "content")

    def test_match_skill_module(self):
        r = self.grouper._match_by_content("技能列表查询接口")
        self.assertEqual(r.module_name, "技能中心")

    def test_match_channel_module(self):
        r = self.grouper._match_by_content("渠道配置保存接口")
        self.assertEqual(r.module_name, "渠道模块")

    def test_match_dialog_module(self):
        r = self.grouper._match_by_content("对话列表查询接口")
        self.assertEqual(r.module_name, "对话管理")

    def test_match_mclaw_module(self):
        r = self.grouper._match_by_content("MClaw 重命名接口")
        self.assertEqual(r.module_name, "MClaw 模块")

    def test_match_task_module(self):
        r = self.grouper._match_by_content("任务广场搜索接口")
        self.assertEqual(r.module_name, "定时任务模块")

    def test_match_no_keyword(self):
        r = self.grouper._match_by_content("实现一个未知功能")
        self.assertEqual(r.module_name, "")
        self.assertEqual(r.match_source, "none")

    # ==================== 章节标题提取 ====================

    def test_section_simple(self):
        r = self.grouper._match_by_section("3.用户中心")
        self.assertEqual(r.module_name, "用户中心")
        self.assertEqual(r.match_source, "section")

    def test_section_with_suffix(self):
        r = self.grouper._match_by_section("3.1 用户中心接口设计")
        self.assertEqual(r.module_name, "用户中心")

    def test_section_path(self):
        r = self.grouper._match_by_section("3.用户中心 > 3.1 接口设计")
        # 最后一段 '3.1 接口设计' → 去编号 → '接口设计' → 去后缀 → 空
        # fallback 尝试用原始章节名（去编号）
        self.assertIn("接口设计", r.module_name)
        self.assertEqual(r.match_source, "section")

    def test_section_fallback_std_name(self):
        """章节兜底返回标准化名"""
        # 去掉后缀后为空，fallback 用原始去编号名
        r = self.grouper._match_by_section("1.2.3 备份还原处理阶段")
        self.assertIn("备份还原处理", r.module_name)
        self.assertEqual(r.match_source, "section")

    def test_section_empty(self):
        r = self.grouper._match_by_section("")
        self.assertEqual(r.module_name, "")

    def test_section_no_match(self):
        r = self.grouper._match_by_section("99.未知模块")
        self.assertEqual(r.module_name, "未知模块")
        self.assertEqual(r.confidence, 0.5)

    # ==================== 白名单匹配 ====================

    def _make_whitelist_grouper(self):
        whitelist = {
            "技能中心": [
                {"任务内容": "技能列表查询接口"},
                {"任务内容": "技能搜索接口"},
            ],
            "对话管理": [
                {"任务内容": "对话列表查询接口"},
            ],
        }
        return ModuleGrouper(whitelist=whitelist)

    def test_whitelist_match(self):
        grouper = self._make_whitelist_grouper()
        r = grouper._match_by_whitelist("技能列表查询接口")
        self.assertEqual(r.module_name, "技能中心")
        self.assertGreater(r.confidence, 0.3)

    def test_whitelist_partial_match(self):
        grouper = self._make_whitelist_grouper()
        # "技能搜索" 部分匹配白名单中的 "技能搜索接口"
        r = grouper._match_by_whitelist("技能搜索接口开发")
        self.assertEqual(r.module_name, "技能中心")

    def test_whitelist_no_match(self):
        grouper = self._make_whitelist_grouper()
        r = grouper._match_by_whitelist("用户管理功能")
        self.assertEqual(r.module_name, "")

    def test_whitelist_empty(self):
        grouper = ModuleGrouper()
        r = grouper._match_by_whitelist("任意内容")
        self.assertEqual(r.module_name, "")

    # ==================== 综合决策 ====================

    def test_decide_content_wins(self):
        content = ModuleResult("用户中心", 0.9, "content")
        section = ModuleResult("订单模块", 0.5, "section")
        whitelist = ModuleResult("", 0.0, "none")

        r = self.grouper._decide(content, section, whitelist)
        self.assertEqual(r.module_name, "用户中心")
        self.assertTrue(r.conflict)

    def test_decide_consistent(self):
        content = ModuleResult("技能中心", 0.8, "content")
        section = ModuleResult("技能中心", 0.7, "section")
        whitelist = ModuleResult("技能中心", 0.9, "whitelist")

        r = self.grouper._decide(content, section, whitelist)
        self.assertEqual(r.module_name, "技能中心")
        self.assertFalse(r.conflict)

    def test_decide_fallback(self):
        content = ModuleResult("", 0.0, "none")
        section = ModuleResult("", 0.0, "none")
        whitelist = ModuleResult("", 0.0, "none")

        r = self.grouper._decide(content, section, whitelist)
        self.assertEqual(r.module_name, "未分类")
        self.assertEqual(r.match_source, "fallback")

    # ==================== group() 完整流程 ====================

    def test_group_basic(self):
        r = self.grouper.group("新增用户列表查询接口", "3.用户中心")
        self.assertEqual(r.module_name, "用户中心")
        self.assertGreater(r.confidence, 0.5)

    def test_group_no_section(self):
        r = self.grouper.group("新增用户列表查询接口")
        self.assertEqual(r.module_name, "用户中心")

    def test_group_unknown(self):
        r = self.grouper.group("实现一个未知功能", "99.未知章节")
        self.assertIsNotNone(r.module_name)

    # ==================== 模块名标准化 ====================

    def test_normalize_remove_suffix(self):
        self.assertEqual(
            self.grouper.normalize_module_name("用户中心接口设计"),
            "用户中心"
        )

    def test_normalize_remove_number(self):
        self.assertEqual(
            self.grouper.normalize_module_name("3.用户中心"),
            "用户中心"
        )

    def test_normalize_chinese_number(self):
        self.assertEqual(
            self.grouper.normalize_module_name("一、用户中心"),
            "用户中心"
        )

    def test_normalize_path(self):
        # '3.1 接口设计' 去掉编号 → '接口设计' 去掉后缀 → 空 → 未分类
        self.assertEqual(
            self.grouper.normalize_module_name("3.用户中心 > 3.1 接口设计"),
            "未分类"
        )

    def test_normalize_empty(self):
        self.assertEqual(
            self.grouper.normalize_module_name(""),
            "未分类"
        )

    # ==================== 核心词提取 ====================

    def test_extract_core_words(self):
        words = self.grouper._extract_core_words("新增用户列表查询接口")
        self.assertIn("用户列表查询接口", words)

    def test_extract_core_words_with_de(self):
        words = self.grouper._extract_core_words("实现技能中心的缓存逻辑")
        self.assertIn("技能中心", words)
        self.assertIn("缓存逻辑", words)

    def test_extract_core_words_short(self):
        words = self.grouper._extract_core_words("新增接口")
        self.assertEqual(words, ["接口"])


if __name__ == '__main__':
    unittest.main(verbosity=2)
