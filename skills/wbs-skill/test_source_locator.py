#!/usr/bin/env python3
"""来源定位引擎测试 - v4.0

测试覆盖：
1. 任务行识别（正例 + 反例）
2. 章节路径构建
3. 上下文提取
4. 来源格式化
5. PDF/MD 定位差异
"""

import sys
import os
import unittest

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.source_locator import SourceLocator, SourceInfo, build_page_map
from src.section_engine import Section


class TestSourceLocator(unittest.TestCase):

    def setUp(self):
        self.locator = SourceLocator(context_lines=1)

    # ==================== 任务行识别 ====================

    def test_task_line_verb_keyword(self):
        """动词开头 + 技术关键词 → 任务行"""
        self.assertTrue(self.locator._is_task_line("新增用户管理接口"))
        self.assertTrue(self.locator._is_task_line("更新技能列表查询功能"))
        self.assertTrue(self.locator._is_task_line("实现缓存逻辑"))
        self.assertTrue(self.locator._is_task_line("提供数据同步接口"))

    def test_task_line_step_marker(self):
        """步骤标记 → 任务行"""
        self.assertTrue(self.locator._is_task_line("第1步：设计数据库表结构"))
        self.assertTrue(self.locator._is_task_line("第 2 步: 实现用户认证"))

    def test_task_line_numbered(self):
        """编号标记 + 动词 → 任务行"""
        self.assertTrue(self.locator._is_task_line("a. 实现缓存逻辑"))
        self.assertTrue(self.locator._is_task_line("b. 新增查询接口"))

    def test_task_line_http_method(self):
        """HTTP 方法 + 路径 → 任务行"""
        self.assertTrue(self.locator._is_task_line("POST /api/user/create → 创建用户"))
        self.assertTrue(self.locator._is_task_line("GET /api/skill/list"))
        self.assertTrue(self.locator._is_task_line("DELETE /api/user/{id}"))

    def test_task_line_bracket_marker(self):
        """【新增】【更新】标记 → 任务行"""
        self.assertTrue(self.locator._is_task_line("【新增】用户查询接口"))
        self.assertTrue(self.locator._is_task_line("【更新】技能安装流程"))
        self.assertTrue(self.locator._is_task_line("【删除】旧版配置接口"))

    def test_task_line_module_verb(self):
        """模块名 + 动词 → 任务行"""
        self.assertTrue(self.locator._is_task_line("技能中心提供查询功能"))
        self.assertTrue(self.locator._is_task_line("渠道模块新增配置接口"))
        self.assertTrue(self.locator._is_task_line("MClaw 支持模型切换"))

    def test_non_task_negation(self):
        """否定前缀 → 非任务行"""
        self.assertFalse(self.locator._is_task_line("不新增用户接口"))
        self.assertFalse(self.locator._is_task_line("不需要开发"))
        self.assertFalse(self.locator._is_task_line("一期已完成"))
        self.assertFalse(self.locator._is_task_line("暂不实现"))

    def test_non_task_markers(self):
        """非任务标记 → 非任务行"""
        self.assertFalse(self.locator._is_task_line("• 用户管理"))
        self.assertFalse(self.locator._is_task_line("业务目标：提升效率"))
        self.assertFalse(self.locator._is_task_line("SC->>DB: 查询数据"))
        self.assertFalse(self.locator._is_task_line("TODO: 待确认"))

    def test_non_task_too_short(self):
        """过短行 → 非任务行"""
        self.assertFalse(self.locator._is_task_line("新增"))
        self.assertFalse(self.locator._is_task_line("1.2"))
        self.assertFalse(self.locator._is_task_line("---"))

    def test_non_task_pure_number(self):
        """纯数字/符号行 → 非任务行"""
        self.assertFalse(self.locator._is_task_line("1.2.1"))
        self.assertFalse(self.locator._is_task_line("123"))
        self.assertFalse(self.locator._is_task_line("1 | 2 | 3"))

    def test_non_task_descriptive_prefix(self):
        """描述性前缀 → 非任务行"""
        self.assertFalse(self.locator._is_task_line("为保障用户数据安全，需要提供备份能力"))
        self.assertFalse(self.locator._is_task_line("为了提升系统性能"))
        self.assertFalse(self.locator._is_task_line("本节描述备份还原的流程"))

    def test_non_task_descriptive_suffix(self):
        """描述性后缀 → 非任务行"""
        self.assertFalse(self.locator._is_task_line("提供备份还原的能力"))
        self.assertFalse(self.locator._is_task_line("备份还原的需求"))
        self.assertFalse(self.locator._is_task_line("系统架构的设计"))

    # ==================== 章节路径 ====================

    def test_section_path_single_level(self):
        """单级章节"""
        sections = [
            Section(title="3.用户中心", level=1, line_num=10),
        ]
        path = self.locator._build_section_path(20, sections)
        self.assertEqual(path, "3.用户中心")

    def test_section_path_two_levels(self):
        """两级章节路径"""
        sections = [
            Section(title="3.用户中心", level=1, line_num=10),
            Section(title="3.1 接口设计", level=2, line_num=15),
        ]
        path = self.locator._build_section_path(25, sections)
        self.assertEqual(path, "3.用户中心 > 3.1 接口设计")

    def test_section_path_no_section(self):
        """无章节"""
        path = self.locator._build_section_path(5, [])
        self.assertEqual(path, "")

    def test_section_path_before_first(self):
        """行号在第一个章节之前"""
        sections = [
            Section(title="1.概述", level=1, line_num=10),
        ]
        path = self.locator._build_section_path(5, sections)
        self.assertEqual(path, "")

    # ==================== 上下文提取 ====================

    def test_context_before(self):
        """提取上文"""
        lines = [
            "这是章节标题",
            "上文第一行内容",
            "",  # 空行跳过
            "当前任务行",
            "下文第一行",
        ]
        before = self.locator._extract_context_before(lines, 3)  # "当前任务行"
        self.assertEqual(before, "上文第一行内容")

    def test_context_after(self):
        """提取下文"""
        lines = [
            "上文",
            "当前任务行",
            "",  # 空行跳过
            "下文第一行内容",
            "下文第二行内容",
        ]
        after = self.locator._extract_context_after(lines, 1, len(lines))
        self.assertEqual(after, "下文第一行内容")

    def test_context_skip_section(self):
        """上下文遇到章节标题停止"""
        lines = [
            "上文内容",
            "1.2 新章节标题",
            "当前任务行",
        ]
        before = self.locator._extract_context_before(lines, 2)  # "当前任务行"
        # 应该停在章节标题，不取到"上文内容"
        self.assertEqual(before, "")

    # ==================== 来源格式化 ====================

    def test_format_excel_pdf(self):
        """PDF 格式（带页码）"""
        source = SourceInfo(
            section_path="3.用户中心",
            page=5,
            line_num=42,
            raw_text="新增用户列表查询接口，支持分页和模糊搜索",
            file_type="pdf",
        )
        result = source.format_for_excel()
        self.assertIn("3.用户中心", result)
        self.assertIn("P5", result)
        self.assertIn("第42行", result)
        self.assertIn("原文", result)
        self.assertIn("新增用户列表查询接口", result)

    def test_format_excel_md(self):
        """MD 格式（无页码）"""
        source = SourceInfo(
            section_path="## 用户中心 > ### 接口设计",
            page=0,
            line_num=42,
            raw_text="POST /api/user/create → 创建用户",
            file_type="markdown",
        )
        result = source.format_for_excel()
        self.assertIn("## 用户中心 > ### 接口设计", result)
        self.assertNotIn("P0", result)  # 页码为 0 时不显示
        self.assertIn("第42行", result)
        self.assertIn("原文", result)

    def test_format_excel_truncate_long_text(self):
        """长文本截断"""
        source = SourceInfo(
            section_path="测试",
            line_num=1,
            raw_text="新增用户列表查询接口，支持分页查询、模糊搜索、批量删除、数据导出、权限控制、操作日志记录等丰富的功能特性，确保系统的可扩展性和可维护性",
        )
        result = source.format_for_excel()
        self.assertIn("...", result)

    # ==================== locate_all ====================

    def test_locate_all_basic(self):
        """基本定位流程"""
        lines = [
            "1.概述",
            "",
            "本项目旨在提升系统性能",  # 非任务行
            "",
            "2.接口设计",
            "",
            "新增用户查询接口",  # 任务行
            "更新用户信息接口",  # 任务行
            "",
            "不需要开发的接口",  # 否定 → 非任务行
        ]
        sections = [
            Section(title="1.概述", level=1, line_num=1),
            Section(title="2.接口设计", level=1, line_num=5),
        ]

        sources = self.locator.locate_all(lines, sections, file_type="markdown")

        # 应该找到 2 个任务行
        self.assertEqual(len(sources), 2)
        self.assertIn("用户查询", sources[0].raw_text)
        self.assertIn("用户信息", sources[1].raw_text)

        # 来源字段应包含章节信息
        self.assertIn("接口设计", sources[0].section_path)

    def test_locate_all_with_page_map(self):
        """PDF 带页码映射"""
        lines = [
            "1.概述",
            "新增用户管理接口",
            "更新技能中心功能",
        ]
        sections = [Section(title="1.概述", level=1, line_num=1)]
        page_map = {1: 1, 2: 2, 3: 2}

        sources = self.locator.locate_all(lines, sections, file_type="pdf", page_map=page_map)

        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0].page, 2)
        self.assertEqual(sources[1].page, 2)

    # ==================== build_page_map ====================

    def test_build_page_map(self):
        """页码映射构建"""
        pdf_pages = [
            (1, "第1页内容\n第二行"),
            (2, "第2页内容\n第二行\n第三行"),
        ]
        page_map = build_page_map(pdf_pages)
        self.assertEqual(page_map[1], 1)
        self.assertEqual(page_map[2], 1)
        self.assertEqual(page_map[3], 2)
        self.assertEqual(page_map[4], 2)
        self.assertEqual(page_map[5], 2)

    # ==================== 代码块过滤 ====================

    def test_code_block_filter(self):
        """代码块内行应被过滤"""
        lines = [
            "```python",
            "def hello():",  # 在代码块内，不是任务行
            "    print('hi')",
            "```",
            "新增用户接口",  # 代码块外，是任务行
        ]
        locator = SourceLocator()
        result = locator.locate_all(lines, [], file_type="markdown")

        # 只有代码块外的行被识别为任务
        self.assertEqual(len(result), 1)
        self.assertIn("新增用户接口", result[0].raw_text)

    # ==================== 扩展关键词测试 ====================

    def test_extended_verbs(self):
        """扩展动词识别"""
        self.assertTrue(self.locator._is_task_line("接入第三方法务接口"))
        self.assertTrue(self.locator._is_task_line("对接用户数据接口"))
        self.assertTrue(self.locator._is_task_line("发送消息通知"))
        self.assertTrue(self.locator._is_task_line("接收回调请求"))
        self.assertTrue(self.locator._is_task_line("导出统计数据"))
        self.assertTrue(self.locator._is_task_line("加密敏感字段"))
        self.assertTrue(self.locator._is_task_line("限流 API 接口"))
        self.assertTrue(self.locator._is_task_line("熔断服务调用"))
        self.assertTrue(self.locator._is_task_line("回滚数据变更"))

    def test_extended_negation(self):
        """扩展否定前缀"""
        self.assertFalse(self.locator._is_task_line("无需新增接口"))
        self.assertFalse(self.locator._is_task_line("不需要修改配置"))
        self.assertFalse(self.locator._is_task_line("已有用户接口"))
        self.assertFalse(self.locator._is_task_line("已实现功能"))
        self.assertFalse(self.locator._is_task_line("已支持导出"))
        self.assertFalse(self.locator._is_task_line("不涉及修改"))
        self.assertFalse(self.locator._is_task_line("依赖已有服务"))
        self.assertFalse(self.locator._is_task_line("沿用现有接口"))

    def test_extended_descriptive(self):
        """扩展描述性前缀"""
        self.assertFalse(self.locator._is_task_line("推荐使用 MySQL 数据库"))
        self.assertFalse(self.locator._is_task_line("建议使用 Redis 缓存"))

    def test_scoring_system_low_score(self):
        """评分系统：低分行（非任务）"""
        self.assertFalse(self.locator._is_task_line("这是一个简单的描述"))
        self.assertFalse(self.locator._is_task_line("系统性能很好"))

    def test_scoring_system_high_score(self):
        """评分系统：高分行（任务）"""
        self.assertTrue(self.locator._is_task_line("POST /api/user/create"))
        self.assertTrue(self.locator._is_task_line("对用户数据进行加密存储"))
        self.assertTrue(self.locator._is_task_line("通过消息队列实现异步通知"))
        self.assertTrue(self.locator._is_task_line("基于 Redis 实现缓存功能"))
        self.assertTrue(self.locator._is_task_line("支持用户批量导入功能"))

    def test_scoring_with_http_method(self):
        """HTTP 方法加分"""
        self.assertTrue(self.locator._is_task_line("调用 GET 接口获取数据"))
        self.assertTrue(self.locator._is_task_line("PUT 更新用户信息"))
        self.assertTrue(self.locator._is_task_line("DELETE 删除缓存数据"))

    def test_scoring_with_bracket_marker(self):
        """【】标记加分"""
        self.assertTrue(self.locator._is_task_line("【新增】用户查询接口"))
        self.assertTrue(self.locator._is_task_line("【更新】技能安装流程"))
        self.assertTrue(self.locator._is_task_line("【修改】配置参数"))

    def test_tech_keywords_extended(self):
        """扩展技术关键词"""
        self.assertTrue(self.locator._is_task_line("配置消息队列 Topic"))
        self.assertTrue(self.locator._is_task_line("创建 Worker 处理任务"))
        self.assertTrue(self.locator._is_task_line("实现 OAuth 授权"))
        self.assertTrue(self.locator._is_task_line("刷新 JWT Token"))
        self.assertTrue(self.locator._is_task_line("配置 SSL 证书"))
        self.assertTrue(self.locator._is_task_line("对接注册中心"))
        self.assertTrue(self.locator._is_task_line("实现服务降级"))
        self.assertTrue(self.locator._is_task_line("配置 Consumer 订阅"))

    def test_scoring_edge_cases(self):
        """评分边界情况"""
        # "对XXX进行YYY" 句式应被识别
        self.assertTrue(self.locator._is_task_line("对用户接口进行安全加固"))
        # "通过XXX实现YYY" 句式
        self.assertTrue(self.locator._is_task_line("通过 API 网关实现限流"))
        # 否定前缀 + 动词 + 技术词 → 不应被识别
        self.assertFalse(self.locator._is_task_line("已支持用户查询接口"))


if __name__ == '__main__':
    unittest.main(verbosity=2)
