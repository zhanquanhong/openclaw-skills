#!/usr/bin/env python3
"""内容提取引擎测试 - v4.0"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.content_extractor import ContentExtractor, TaskContent
from src.source_locator import SourceInfo


class TestContentExtractor(unittest.TestCase):

    def setUp(self):
        self.extractor = ContentExtractor()

    # ==================== 去除冗余前缀 ====================

    def test_remove_need_prefix(self):
        self.assertEqual(
            self.extractor._remove_redundant_prefix("需要新增用户管理接口"),
            "新增用户管理接口"
        )

    def test_remove_we_need_prefix(self):
        self.assertEqual(
            self.extractor._remove_redundant_prefix("我们要实现缓存逻辑"),
            "实现缓存逻辑"
        )

    def test_remove_step_marker(self):
        self.assertEqual(
            self.extractor._remove_redundant_prefix("第1步：设计数据库表结构"),
            "设计数据库表结构"
        )

    def test_remove_numbered_marker(self):
        self.assertEqual(
            self.extractor._remove_redundant_prefix("a. 实现缓存逻辑"),
            "实现缓存逻辑"
        )

    def test_remove_bracket_marker(self):
        self.assertEqual(
            self.extractor._remove_redundant_prefix("【新增】用户查询接口"),
            "用户查询接口"
        )

    def test_no_prefix_to_remove(self):
        self.assertEqual(
            self.extractor._remove_redundant_prefix("新增用户管理接口"),
            "新增用户管理接口"
        )

    def test_remove_symbol_prefix(self):
        """符号前缀清理"""
        self.assertEqual(
            self.extractor._remove_redundant_prefix("◦调用K8sAPI滚动更新Pod"),
            "调用K8sAPI滚动更新Pod"
        )
        self.assertEqual(
            self.extractor._remove_redundant_prefix("•实现缓存逻辑"),
            "实现缓存逻辑"
        )
        self.assertEqual(
            self.extractor._remove_redundant_prefix("→ 配置网关路由"),
            "配置网关路由"
        )

    def test_remove_step_prefix(self):
        """步骤前缀清理"""
        self.assertEqual(
            self.extractor._remove_redundant_prefix("第4步：执行用户备份处理"),
            "执行用户备份处理"
        )
        self.assertEqual(
            self.extractor._remove_redundant_prefix("第 2 步: 实现认证"),
            "实现认证"
        )
        self.assertEqual(
            self.extractor._remove_redundant_prefix("Step 3: 部署服务"),
            "部署服务"
        )

    def test_remove_number_prefix(self):
        """编号前缀清理"""
        self.assertEqual(
            self.extractor._remove_redundant_prefix("1、打包配置目录"),
            "打包配置目录"
        )
        self.assertEqual(
            self.extractor._remove_redundant_prefix("a. 实现缓存逻辑"),
            "实现缓存逻辑"
        )
        self.assertEqual(
            self.extractor._remove_redundant_prefix("【1】新增接口"),
            "新增接口"
        )

    # ==================== 截断长句 ====================

    def test_truncate_at_keyword(self):
        result = self.extractor._truncate_long_sentence(
            "新增用户列表查询接口，支持分页和模糊搜索"
        )
        self.assertEqual(result, "新增用户列表查询接口")

    def test_truncate_at_include(self):
        result = self.extractor._truncate_long_sentence(
            "实现技能中心功能，包括安装、卸载、更新"
        )
        self.assertEqual(result, "实现技能中心功能")

    def test_no_truncate_needed(self):
        result = self.extractor._truncate_long_sentence("新增用户接口")
        self.assertEqual(result, "新增用户接口")

    def test_truncate_by_length(self):
        long_text = "新增用户管理接口包含用户增删改查权限管理角色分配日志记录等所有功能并且需要支持高并发"
        result = self.extractor._truncate_long_sentence(long_text)
        self.assertLess(len(result), 46)

    # ==================== 清理内容 ====================

    def test_clean_extra_spaces(self):
        self.assertEqual(
            self.extractor._clean_content("新增   用户   接口"),
            "新增 用户 接口"  # 多余空格被折叠
        )

    def test_clean_trailing_punctuation(self):
        self.assertEqual(
            self.extractor._clean_content("新增用户接口，"),
            "新增用户接口"
        )
        self.assertEqual(
            self.extractor._clean_content("新增用户接口。"),
            "新增用户接口"
        )

    def test_clean_arrow(self):
        result = self.extractor._clean_content("创建用户 → 返回用户ID")
        self.assertNotIn("→", result)

    # ==================== 提取 API 路径 ====================

    def test_extract_api_with_method(self):
        info = self.extractor._extract_api_path("POST /api/user/create → 创建用户")
        self.assertTrue(info['has_path'])
        self.assertEqual(info['method'], 'POST')
        self.assertEqual(info['path'], '/api/user/create')

    def test_extract_api_in_parentheses(self):
        info = self.extractor._extract_api_path("技能列表查询接口 (POST /api/skill/list)")
        self.assertTrue(info['has_path'])
        self.assertEqual(info['method'], 'POST')
        self.assertEqual(info['path'], '/api/skill/list')

    def test_extract_api_path_only(self):
        info = self.extractor._extract_api_path("调用 /api/v1/health 接口")
        self.assertTrue(info['has_path'])
        self.assertEqual(info['path'], '/api/v1/health')

    def test_no_api_path(self):
        info = self.extractor._extract_api_path("新增用户管理功能")
        self.assertFalse(info['has_path'])

    # ==================== 任务类型推断 ====================

    def test_task_type_api(self):
        self.assertEqual(
            self.extractor._infer_task_type("新增用户查询接口", "POST /api/user"),
            "接口任务"
        )

    def test_task_type_database(self):
        self.assertEqual(
            self.extractor._infer_task_type("设计用户表结构", "包含字段和索引"),
            "数据库任务"
        )

    def test_task_type_config(self):
        self.assertEqual(
            self.extractor._infer_task_type("配置参数设置", "环境变量 config"),
            "配置任务"
        )

    def test_task_type_middleware(self):
        self.assertEqual(
            self.extractor._infer_task_type("实现缓存逻辑", "使用 Redis"),
            "中间件任务"
        )

    def test_task_type_default(self):
        self.assertEqual(
            self.extractor._infer_task_type("新增用户管理功能", ""),
            "功能任务"
        )

    # ==================== 去重 ====================

    def test_duplicate_exact(self):
        self.extractor.seen_contents.add("新增用户接口")
        self.assertTrue(self.extractor._is_duplicate("新增用户接口"))

    def test_duplicate_contains(self):
        self.extractor.seen_contents.add("新增用户查询接口")
        self.assertTrue(self.extractor._is_duplicate("用户查询接口"))

    def test_not_duplicate(self):
        self.extractor.seen_contents.add("新增用户接口")
        self.assertFalse(self.extractor._is_duplicate("删除用户接口"))

    def test_edit_distance_duplicate(self):
        self.extractor.seen_contents.add("用户查询接口")
        self.assertTrue(self.extractor._is_duplicate("用户查询界口"))  # 1 字符差异

    # ==================== 完整提取流程 ====================

    def test_extract_basic(self):
        source = SourceInfo(
            section_path="3.用户中心",
            page=5,
            line_num=42,
            raw_text="新增用户列表查询接口，支持分页和模糊搜索",
            file_type="pdf",
        )
        result = self.extractor.extract(source)
        self.assertIsNotNone(result)
        self.assertEqual(result.content, "新增用户列表查询接口")
        self.assertEqual(result.task_type, "接口任务")

    def test_extract_with_api_path(self):
        source = SourceInfo(
            section_path="3.用户中心",
            line_num=42,
            raw_text="POST /api/user/create → 创建用户",
            file_type="markdown",
        )
        result = self.extractor.extract(source)
        self.assertIsNotNone(result)
        self.assertTrue(result.has_api_path)
        self.assertEqual(result.api_method, 'POST')
        self.assertEqual(result.api_path, '/api/user/create')

    def test_extract_too_short(self):
        source = SourceInfo(
            section_path="3.用户中心",
            line_num=42,
            raw_text="新增",
            file_type="pdf",
        )
        result = self.extractor.extract(source)
        self.assertIsNone(result)

    def test_extract_dedup_in_pipeline(self):
        """在连续提取中去重"""
        sources = [
            SourceInfo(raw_text="新增用户查询接口", line_num=1),
            SourceInfo(raw_text="新增用户查询接口", line_num=2),  # 重复
        ]
        extractor = ContentExtractor()
        results = [extractor.extract(s) for s in sources]

        self.assertIsNotNone(results[0])
        self.assertIsNone(results[1])  # 被去重

    def test_extract_long_content_truncated(self):
        source = SourceInfo(
            section_path="3.用户中心",
            line_num=42,
            raw_text="实现技能中心的缓存逻辑，支持分布式部署和高并发访问",
            file_type="pdf",
        )
        result = self.extractor.extract(source)
        self.assertIsNotNone(result)
        self.assertIn("缓存逻辑", result.content)
        self.assertNotIn("分布式", result.content)


if __name__ == '__main__':
    unittest.main(verbosity=2)
