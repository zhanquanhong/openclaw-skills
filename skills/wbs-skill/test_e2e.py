"""端到端测试 - wbs-skill v4.0

测试覆盖：
1. MD 文档解析到任务提取全流程
2. v4 完整生成流程（含验证）
3. 调试 JSON 输出
"""

import sys
import os
import json
import pytest
from pathlib import Path
from typing import Dict, List

# 确保能导入 src 模块
SKILL_DIR = Path(__file__).parent.absolute()
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from src.document_parser import DocumentParser, ParsedDocument
from src.source_locator import SourceLocator, SourceInfo


class TestE2E:
    """端到端测试"""

    def test_md_parse_success(self):
        """测试 MD 文档解析成功"""
        parser = DocumentParser()
        doc = parser.parse("testdata/sample.md", section_template="markdown")
        assert doc is not None
        assert doc.line_count > 0
        assert doc.section_count > 0
        assert doc.file_type == "markdown"
        assert doc.table_count > 0  # 包含接口表格

    def test_md_parse_content(self):
        """测试 MD 文档解析内容正确性"""
        parser = DocumentParser()
        doc = parser.parse("testdata/sample.md", section_template="markdown")

        # 检查解析出的文本行数
        assert doc.line_count >= 50, f"Line count too low: {doc.line_count}"

        # 检查章节数（应该有至少 5 个章节/子章节）
        assert doc.section_count >= 5, f"Section count too low: {doc.section_count}"

        # 检查表格数（至少 2 个接口表格）
        assert doc.table_count >= 2, f"Table count too low: {doc.table_count}"

    def test_source_locator_on_sample(self):
        """测试来源定位在 sample.md 上的效果"""
        parser = DocumentParser()
        doc = parser.parse("testdata/sample.md", section_template="markdown")

        locator = SourceLocator(context_lines=1)
        sources = locator.locate_all(
            doc.lines,
            doc.sections,
            file_type=doc.file_type,
        )

        # 应该找到至少 10 个潜在任务行
        assert len(sources) >= 10, f"Found {len(sources)} sources, expected >= 10"

        # 检查任务行包含正确的关键词
        found_new = any("批量导入" in s.raw_text for s in sources)
        assert found_new, "Should find '批量导入' task"

        # 检查没有被错误地识别为任务的非任务行
        non_task_lines = [
            "本项目旨在提升",
            "不需要修改",
            "已部署",
            "已执行",
        ]
        for nt in non_task_lines:
            for s in sources:
                if nt in s.raw_text:
                    pytest.fail(f"Non-task line should not be detected: {s.raw_text}")

    def test_task_extraction_via_content_extractor(self):
        """测试内容提取器的效果"""
        parser = DocumentParser()
        doc = parser.parse("testdata/sample.md", section_template="markdown")

        locator = SourceLocator(context_lines=1)
        sources = locator.locate_all(
            doc.lines,
            doc.sections,
            file_type=doc.file_type,
        )

        from src.content_extractor import ContentExtractor
        extractor = ContentExtractor()

        extracted_count = 0
        for source in sources:
            content = extractor.extract(source)
            if content:
                extracted_count += 1
                # 检查任务内容合理性
                assert len(content.content) >= 3, f"Content too short: {content.content}"
                assert content.task_type in [
                    "接口任务", "数据库任务", "配置任务", "中间件任务",
                    "前端任务", "算法任务", "功能任务"
                ], f"Unknown task type: {content.task_type}"

        assert extracted_count >= 8, f"Extracted {extracted_count} tasks, expected >= 8"

    def test_v4_generate_flow(self):
        """测试 v4 完整生成流程（不含 Excel 输出）"""
        from generate_wbs import generate_wbs_v4
        from src.document_parser import DocumentParser

        parser = DocumentParser()
        doc = parser.parse("testdata/sample.md", section_template="markdown")
        assert doc is not None

        # 使用临时输出目录
        temp_output = os.path.join(SKILL_DIR, "test_output")
        os.makedirs(temp_output, exist_ok=True)

        try:
            result = generate_wbs_v4(
                "testdata/sample.md",
                output_dir=temp_output,
                auto_learn=False,
                require_confirm=False,
                debug_json_path=os.path.join(temp_output, "debug.json"),
            )
            assert result is not None
            assert os.path.exists(result), f"Output file not found: {result}"

            # 检查调试 JSON 是否生成
            debug_path = os.path.join(temp_output, "debug.json")
            if os.path.exists(debug_path):
                with open(debug_path, 'r', encoding='utf-8') as f:
                    debug_data = json.load(f)
                assert "version" in debug_data
                assert debug_data["version"] == "v4.0"
                assert "tasks" in debug_data
                assert "timing" in debug_data
                assert len(debug_data["tasks"]) > 0
        finally:
            # 清理临时文件
            import shutil
            if os.path.exists(temp_output):
                shutil.rmtree(temp_output, ignore_errors=True)

    def test_consistency_validations(self):
        """测试交叉验证是否生效"""
        from src.consistency_checker import ConsistencyChecker

        checker = ConsistencyChecker()

        # 模拟任务列表：用户中心只有 2 个独立任务，触发偏少警告
        mock_tasks = [
            {"任务模块": "用户中心", "任务内容": "新增用户批量导入功能"},
            {"任务模块": "用户中心", "任务内容": "新增用户批量导入功能"},  # 重复
            {"任务模块": "用户中心", "任务内容": "实现用户导出功能"},
            {"任务模块": "权限管理", "任务内容": "配置角色权限"},
        ]

        # 相邻重复检测
        dup_results = checker.check_adjacent_duplicates(mock_tasks)
        assert len(dup_results) == 1, f"Expected 1 duplicate, got {len(dup_results)}"

        # 模块平衡检测
        bal_results = checker.check_module_balance(mock_tasks)
        # 3 < 3, so should be in results
        small_module = [r for r in bal_results if "任务数过少" in str(r.issues)]
        assert len(small_module) == 1, f"Expected 1 small module warning"

        # 来源合理性检测
        reason_results = checker.check_source_reasonability(mock_tasks)
        # No _source_info, should have no issues
        assert len(reason_results) == 0

    def test_whitelist_learn_format(self):
        """测试白名单学习是否保存 v4 格式"""
        from generate_wbs import learn_new_tasks

        mock_new_tasks = [
            {
                "任务模块": "用户中心",
                "任务内容": "新增批量导入功能",
                "任务来源": "3.1 接口设计 | 第42行",
                "任务类型": "功能任务",
                "原文片段": "新增用户批量导入功能",
            }
        ]

        # 学习新任务（不需要确认）
        learn_new_tasks(mock_new_tasks, require_confirm=False)

        # 验证白名单包含了 v4 格式的信息
        from src.whitelist_manager import UserWhitelistManager
        manager = UserWhitelistManager()
        user_wl = manager.load_user()

        found_v4 = False
        for module, items in user_wl.items():
            for item in items:
                if isinstance(item, dict) and item.get('任务内容') == "新增批量导入功能":
                    assert '_version' in item, f"v4 version tag missing"
                    assert item['_version'] == 'v4.0', f"Wrong version: {item['_version']}"
                    found_v4 = True
                    break

        assert found_v4, "v4 format task not found in whitelist after learning"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
