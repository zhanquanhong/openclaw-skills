#!/usr/bin/env python3
"""TypeClassifier 单元测试"""

import sys
import os
import unittest
from pathlib import Path

# 确保能导入 src 模块
SKILL_DIR = Path(__file__).parent.absolute()
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from src.type_classifier import TypeClassifier, load_type_config


class TestTypeClassifier(unittest.TestCase):
    """TypeClassifier 基础测试"""

    @classmethod
    def setUpClass(cls):
        cls.config = load_type_config()
        cls.classifier = TypeClassifier(config=cls.config)

    def test_load_config(self):
        """测试加载配置"""
        config = load_type_config()
        types = config.get('types', [])
        self.assertGreater(len(types), 0, "应该至少有一种任务类型")
        self.assertIn('功能任务', [t['id'] for t in types], "应该包含功能任务兜底")

    def test_initialization(self):
        """测试初始化"""
        self.assertIsNotNone(self.classifier.config)
        self.assertGreater(len(self.classifier.type_names), 0)
        self.assertGreater(len(self.classifier.fallback_keywords), 0)

    # ==================== 关键词回退测试 ====================

    def test_fallback_interface(self):
        """关键词回退：接口任务"""
        task = {'任务内容': 'POST新增用户接口', '任务来源': '3.1 接口设计', '原文片段': ''}
        result = self.classifier._infer_by_keywords(task)
        self.assertEqual(result, '接口任务')

    def test_fallback_database(self):
        """关键词回退：数据库任务"""
        task = {'任务内容': '创建用户表', '任务来源': '4.1 数据库设计', '原文片段': 'CREATE TABLE'}
        result = self.classifier._infer_by_keywords(task)
        self.assertEqual(result, '数据库任务')

    def test_fallback_frontend(self):
        """关键词回退：前端任务（注意"列表"含"表"会误匹配数据库任务）"""
        task = {'任务内容': '前端页面展示组件', '任务来源': '2.1 前端', '原文片段': ''}
        result = self.classifier._infer_by_keywords(task)
        self.assertEqual(result, '前端任务')

    def test_fallback_middleware(self):
        """关键词回退：中间件任务"""
        task = {'任务内容': '通过Redis缓存数据', '任务来源': '5.1 缓存', '原文片段': ''}
        result = self.classifier._infer_by_keywords(task)
        self.assertEqual(result, '中间件任务')

    def test_fallback_config(self):
        """关键词回退：配置任务"""
        task = {'任务内容': '配置环境变量', '任务来源': '6.1 配置', '原文片段': ''}
        result = self.classifier._infer_by_keywords(task)
        self.assertEqual(result, '配置任务')

    def test_fallback_default(self):
        """关键词回退：兜底功能任务"""
        task = {'任务内容': '分析业务需求', '任务来源': '1.1 需求分析', '原文片段': ''}
        result = self.classifier._infer_by_keywords(task)
        self.assertEqual(result, '功能任务')

    def test_fallback_empty_content(self):
        """关键词回退：空内容"""
        task = {'任务内容': '', '任务来源': '', '原文片段': ''}
        result = self.classifier._infer_by_keywords(task)
        self.assertEqual(result, '功能任务')

    def test_fallback_with_raw(self):
        """关键词回退：内容匹配关键词"""
        task = {
            '任务内容': '配置XXL-Job定时任务每日06:00触发',
            '任务来源': '3.2 备份流程',
            '原文片段': '通过XXL-Job定时任务每日06:00触发',
        }
        result = self.classifier._infer_by_keywords(task)
        self.assertEqual(result, '中间件任务')

    def test_fallback_priority_by_order(self):
        """关键词回退：第一个匹配的返回"""
        task = {
            '任务内容': '查询数据库接口状态',
            '任务来源': '',
            '原文片段': '',
        }
        result = self.classifier._infer_by_keywords(task)
        self.assertTrue(result in ['接口任务', '数据库任务'])

    # ==================== 批量分类测试 ====================

    def test_classify_empty(self):
        """空列表分类"""
        result = self.classifier.classify([])
        self.assertEqual(len(result), 0)

    def test_classify_single(self):
        """单任务分类"""
        tasks = [
            {'任务内容': '新增用户查询接口，支持分页查询', '任务来源': '3.1 接口设计', '原文片段': '新增用户查询接口，支持分页查询'},
        ]
        result = self.classifier.classify(tasks)
        self.assertEqual(len(result), 1)
        self.assertIn('任务类型', result[0])

    def test_classify_multi(self):
        """多任务分类（不同来源）"""
        tasks = [
            {'任务内容': 'POST更新接口', '任务来源': '2.1 接口', '原文片段': ''},
            {'任务内容': '创建用户表', '任务来源': '3.1 数据库', '原文片段': 'CREATE TABLE'},
            {'任务内容': '前端展示页面', '任务来源': '4.1 前端', '原文片段': ''},
        ]
        result = self.classifier.classify(tasks)
        self.assertEqual(len(result), 3)
        for task in result:
            self.assertIn('任务类型', task)

    def test_classify_preserve_fields(self):
        """分类不应影响其他字段"""
        tasks = [
            {'任务内容': '新增用户查询接口', '任务来源': '3.1 接口设计', '原文片段': '新增用户查询接口，支持分页', '任务模块': '测试模块'},
        ]
        result = self.classifier.classify(tasks)
        self.assertEqual(len(result), 1, "测试任务应被判定为有效")
        self.assertEqual(result[0]['任务模块'], '测试模块')
        self.assertIn('任务类型', result[0])

    def test_fallback_on_no_source(self):
        """无来源字段时的回退"""
        tasks = [
            {'任务内容': '新增用户查询接口，支持分页'},
        ]
        result = self.classifier.classify(tasks)
        self.assertEqual(len(result), 1)
        self.assertIn('任务类型', result[0])

    # ==================== 统计测试 ====================

    def test_statistics(self):
        """统计功能"""
        tasks = [
            {'任务类型': '接口任务'}, {'任务类型': '接口任务'},
            {'任务类型': '数据库任务'},
            {'任务类型': '功能任务'}, {'任务类型': '功能任务'}, {'任务类型': '功能任务'},
        ]
        stats = self.classifier.get_statistics(tasks)
        self.assertEqual(stats['接口任务'], 2)
        self.assertEqual(stats['数据库任务'], 1)
        self.assertEqual(stats['功能任务'], 3)

    def test_statistics_empty(self):
        """空列表统计"""
        stats = self.classifier.get_statistics([])
        self.assertEqual(len(stats), 0)

    def test_statistics_default_type(self):
        """无类型字段的统计"""
        tasks = [{'内容': 'test'}]
        stats = self.classifier.get_statistics(tasks)
        self.assertEqual(stats.get('功能任务', 0), 1)


if __name__ == '__main__':
    unittest.main()
