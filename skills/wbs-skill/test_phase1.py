"""Phase 1 单元测试

测试章节推断引擎和表格解析器的核心功能。

运行方式：
    cd skills/wbs-skill
    python3 -m pytest test_phase1.py -v
"""

import unittest
import sys
from pathlib import Path

# 确保能导入 src 模块
SKILL_DIR = Path(__file__).parent.absolute()
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from src.section_engine import SectionInferEngine, Section
from src.table_extractor import TableExtractor, Table, InterfaceTable


class TestSectionEngine(unittest.TestCase):
    """章节推断引擎测试"""

    def test_numeric_template(self):
        """测试数字编号模板"""
        lines = [
            "1.2.1 提取模型的文件 ID",
            "一些正文内容",
            "1.2.2 批量获取对话详情",
            "又一些正文",
            "2.1 另一个章节",
        ]
        engine = SectionInferEngine(template="numeric")
        sections = engine.infer(lines)

        self.assertEqual(len(sections), 3)
        self.assertEqual(sections[0].title, "1.2.1 提取模型的文件 ID")
        self.assertEqual(sections[0].level, 3)
        self.assertEqual(sections[0].line_num, 1)
        self.assertEqual(sections[1].title, "1.2.2 批量获取对话详情")
        self.assertEqual(sections[1].level, 3)
        self.assertEqual(sections[2].title, "2.1 另一个章节")
        self.assertEqual(sections[2].level, 2)

    def test_chinese_template(self):
        """测试中文编号模板"""
        lines = [
            "一、需求分析",
            "正文内容",
            "(一) 功能需求",
            "又一段正文",
            "1. 用户管理",
        ]
        engine = SectionInferEngine(template="chinese")
        sections = engine.infer(lines)

        self.assertEqual(len(sections), 3)
        self.assertEqual(sections[0].level, 1)
        self.assertEqual(sections[1].level, 2)
        self.assertEqual(sections[2].level, 3)

    def test_markdown_template(self):
        """测试 Markdown 模板"""
        lines = [
            "# 标题",
            "正文",
            "## 二级标题",
            "### 三级标题",
        ]
        engine = SectionInferEngine(template="markdown")
        sections = engine.infer(lines)

        self.assertEqual(len(sections), 3)
        self.assertEqual(sections[0].level, 1)
        self.assertEqual(sections[1].level, 2)
        self.assertEqual(sections[2].level, 3)

    def test_find_section_by_line(self):
        """测试按行号查找章节"""
        lines = [
            "1.2.1 第一章",
            "正文1",
            "正文2",
            "1.2.2 第二章",
            "正文3",
        ]
        engine = SectionInferEngine(template="numeric")
        sections = engine.infer(lines)

        # 行号 2 应该在第一章
        section = engine.find_section_by_line(2, sections)
        self.assertIsNotNone(section)
        self.assertEqual(section.title, "1.2.1 第一章")

        # 行号 5 应该在第二章
        section = engine.find_section_by_line(5, sections)
        self.assertIsNotNone(section)
        self.assertEqual(section.title, "1.2.2 第二章")

    def test_empty_lines(self):
        """测试空行列表"""
        engine = SectionInferEngine(template="numeric")
        sections = engine.infer([])
        self.assertEqual(len(sections), 0)

    def test_no_match(self):
        """测试无匹配行"""
        lines = ["正文内容", "又一段正文", "没有章节号"]
        engine = SectionInferEngine(template="numeric")
        sections = engine.infer(lines)
        self.assertEqual(len(sections), 0)

    def test_invalid_template(self):
        """测试无效模板名称"""
        with self.assertRaises(ValueError) as context:
            SectionInferEngine(template="invalid_template")
        self.assertIn("未知的章节模板", str(context.exception))


class TestTableExtractor(unittest.TestCase):
    """表格解析器测试"""

    def test_interface_table_detection(self):
        """测试接口表格识别"""
        table = Table(
            header=["接口名称", "URL", "请求方法"],
            rows=[["用户查询", "/api/user", "GET"]]
        )
        extractor = TableExtractor()
        results = extractor.extract_interface_tables([table])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].type, 'interface')
        self.assertEqual(results[0].title, "")

    def test_module_table_detection(self):
        """测试模块表格识别"""
        table = Table(
            header=["模块", "功能", "接口名称"],
            rows=[["用户模块", "用户管理", "查询用户"]]
        )
        extractor = TableExtractor()
        results = extractor.extract_interface_tables([table])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].type, 'module')

    def test_non_interface_table(self):
        """测试非接口表格过滤"""
        table = Table(
            header=["姓名", "年龄", "地址"],
            rows=[["张三", "25", "北京"]]
        )
        extractor = TableExtractor()
        results = extractor.extract_interface_tables([table])
        self.assertEqual(len(results), 0)

    def test_api_keyword_detection(self):
        """测试 API 关键词识别"""
        table = Table(
            header=["API", "路径", "方法"],
            rows=[["用户接口", "/api/v1/users", "POST"]]
        )
        extractor = TableExtractor()
        results = extractor.extract_interface_tables([table])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].type, 'interface')

    def test_empty_table(self):
        """测试空表格"""
        extractor = TableExtractor()
        results = extractor.extract_interface_tables([])
        self.assertEqual(len(results), 0)

    def test_table_properties(self):
        """测试 Table 属性"""
        table = Table(
            header=["列1", "列2", "列3"],
            rows=[["a", "b", "c"], ["d", "e", "f"]],
            title="测试表格",
            page=5
        )
        self.assertEqual(table.row_count, 2)
        self.assertEqual(table.col_count, 3)
        self.assertIn("测试表格", repr(table))


class TestDocumentParser(unittest.TestCase):
    """文档解析器测试"""

    def test_unsupported_format(self):
        """测试不支持的文件格式"""
        from src.document_parser import DocumentParser
        parser = DocumentParser()

        # 创建临时 txt 文件
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'test content')
            temp_path = f.name

        with self.assertRaises(ValueError) as context:
            parser.parse(temp_path)
        self.assertIn("不支持的文件格式", str(context.exception))

        import os
        os.unlink(temp_path)

    def test_file_not_found(self):
        """测试文件不存在"""
        from src.document_parser import DocumentParser
        parser = DocumentParser()

        with self.assertRaises(FileNotFoundError):
            parser.parse("/nonexistent/file.pdf")


if __name__ == '__main__':
    unittest.main(verbosity=2)
