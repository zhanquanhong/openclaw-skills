#!/usr/bin/env python3
"""一致性验证引擎测试 - v4.0"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.consistency_checker import ConsistencyChecker, ValidationResult
from src.source_locator import SourceInfo


class TestConsistencyChecker(unittest.TestCase):

    def setUp(self):
        self.checker = ConsistencyChecker()

    # ==================== content_in_source ====================

    def test_exact_match(self):
        self.assertTrue(
            self.checker._content_in_source(
                "新增用户列表查询接口",
                "新增用户列表查询接口，支持分页和模糊搜索"
            )
        )

    def test_core_word_match(self):
        # 去掉动词后匹配
        self.assertTrue(
            self.checker._content_in_source(
                "新增用户列表查询接口",
                "用户列表查询接口已实现"
            )
        )

    def test_substring_match(self):
        # 至少 4 个连续字符匹配
        self.assertTrue(
            self.checker._content_in_source(
                "用户管理功能",
                "系统用户管理功能模块"
            )
        )

    def test_no_match(self):
        self.assertFalse(
            self.checker._content_in_source(
                "新增用户接口",
                "订单模块的支付功能"
            )
        )

    # ==================== module_matches_section ====================

    def test_module_in_section(self):
        self.assertTrue(
            self.checker._module_matches_section(
                "用户中心",
                "3.用户中心 > 3.1 接口设计"
            )
        )

    def test_section_in_module(self):
        self.assertTrue(
            self.checker._module_matches_section(
                "用户中心接口设计",
                "3.用户中心"
            )
        )

    def test_clean_section_match(self):
        # "3.1 接口设计" → 去编号 → "接口设计" → 去后缀 → "" → 不匹配
        # But "3.用户中心" in path should match
        self.assertTrue(
            self.checker._module_matches_section(
                "用户中心",
                "3.用户中心 > 3.1 接口设计"
            )
        )

    def test_no_match(self):
        self.assertFalse(
            self.checker._module_matches_section(
                "订单模块",
                "3.用户中心 > 3.1 接口设计"
            )
        )

    def test_empty_module(self):
        self.assertTrue(
            self.checker._module_matches_section("", "3.用户中心")
        )

    def test_empty_section(self):
        self.assertTrue(
            self.checker._module_matches_section("用户中心", "")
        )

    # ==================== verify() 完整验证 ====================

    def test_verify_valid(self):
        source = SourceInfo(
            section_path="3.用户中心",
            line_num=42,
            raw_text="新增用户列表查询接口，支持分页和模糊搜索",
        )
        task = {
            "任务模块": "用户中心",
            "任务内容": "新增用户列表查询接口",
            "任务来源": "3.用户中心 | 第42行 | 原文：「新增用户列表查询接口...」",
            "_source_info": source,
        }
        result = self.checker.verify(task)
        self.assertTrue(result.is_valid)
        self.assertGreater(result.confidence, 0.8)
        self.assertEqual(len(result.issues), 0)

    def test_verify_content_not_in_source(self):
        source = SourceInfo(
            section_path="3.用户中心",
            line_num=42,
            raw_text="订单模块的支付功能",
        )
        task = {
            "任务模块": "用户中心",
            "任务内容": "新增用户列表查询接口",
            "任务来源": "3.用户中心 | 第42行",
            "_source_info": source,
        }
        result = self.checker.verify(task)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("来源原文" in i for i in result.issues))

    def test_verify_module_mismatch(self):
        source = SourceInfo(
            section_path="3.订单模块",
            line_num=42,
            raw_text="新增用户列表查询接口",
        )
        task = {
            "任务模块": "用户中心",
            "任务_content": "新增用户列表查询接口",
            "任务内容": "新增用户列表查询接口",
            "任务来源": "3.订单模块 | 第42行",
            "_source_info": source,
        }
        result = self.checker.verify(task)
        self.assertTrue(any("不一致" in i for i in result.issues))

    def test_verify_empty_content(self):
        task = {
            "任务模块": "用户中心",
            "任务内容": "",
            "任务来源": "3.用户中心",
        }
        result = self.checker.verify(task)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("为空" in i for i in result.issues))

    def test_verify_short_content(self):
        source = SourceInfo(
            section_path="3.用户中心",
            line_num=42,
            raw_text="新增",
        )
        task = {
            "任务模块": "用户中心",
            "任务内容": "新增",
            "任务来源": "3.用户中心 | 第42行",
            "_source_info": source,
        }
        result = self.checker.verify(task)
        self.assertTrue(any("过短" in i for i in result.issues))


if __name__ == '__main__':
    unittest.main(verbosity=2)
