"""PDF 表格解析器 - 多引擎 fallback

从 PDF 中提取表格，支持多种解析引擎自动降级。

使用方式：
    extractor = TableExtractor()
    tables = extractor.extract_tables('技术方案.pdf')
    interface_tables = extractor.extract_interface_tables(tables)
"""

import logging
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Table:
    """表格信息

    Attributes:
        header: 表头列名列表
        rows: 数据行列表（每行是单元格列表）
        title: 表格标题
        page: 所在页码（1-based）
        engine: 使用的解析引擎名称
    """
    header: List[str]
    rows: List[List[str]]
    title: str = ""
    page: int = 0
    engine: str = ""

    @property
    def row_count(self) -> int:
        """数据行数"""
        return len(self.rows)

    @property
    def col_count(self) -> int:
        """列数"""
        return len(self.header)

    def __repr__(self) -> str:
        return f"Table({self.title}: {self.row_count}行×{self.col_count}列, p.{self.page})"


@dataclass
class InterfaceTable:
    """接口定义表格

    Attributes:
        header: 表头列名列表
        rows: 数据行列表
        title: 表格标题
        page: 所在页码
        type: 表格类型（interface/module）
    """
    header: List[str]
    rows: List[List[str]]
    title: str = ""
    page: int = 0
    type: str = "interface"

    @property
    def row_count(self) -> int:
        return len(self.rows)


class TableExtractor:
    """PDF 表格解析器（多引擎 fallback）

    按引擎顺序尝试解析，取第一个成功的结果。

    引擎优先级：
    1. pdfplumber（默认，无需 Java）
    2. camelot（备选，需要 OpenCV）
    3. tabula（备选，需要 Java）

    使用示例：
        extractor = TableExtractor()
        tables = extractor.extract_tables('技术方案.pdf')
        interface_tables = extractor.extract_interface_tables(tables)
    """

    # 接口表格识别关键词
    INTERFACE_KEYWORDS = [
        '接口', 'api', 'url', '路径', 'endpoint', 'http',
        'method', '请求', '请求方式', '请求方法',
    ]

    # 模块表格识别关键词
    MODULE_KEYWORDS = [
        '模块', '功能', '任务', '接口名称', '接口名',
        '功能模块', '功能名称',
    ]

    def __init__(self, engines: List[str] = None):
        """初始化表格解析器

        Args:
            engines: 引擎列表（按优先级排序）
        """
        self.engines = engines or ['pdfplumber']
        self._extractors: Dict[str, Callable] = {
            'pdfplumber': self._extract_pdfplumber,
            'camelot': self._extract_camelot,
            'tabula': self._extract_tabula,
        }

    def extract_tables(self, pdf_path: str) -> List[Table]:
        """从 PDF 提取表格

        按引擎顺序尝试，取第一个成功的结果。

        Args:
            pdf_path: PDF 文件路径

        Returns:
            表格列表

        Raises:
            FileNotFoundError: PDF 文件不存在
        """
        import os
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f'PDF 文件不存在：{pdf_path}')

        all_tables: List[Table] = []

        for engine_name in self.engines:
            extractor = self._extractors.get(engine_name)
            if not extractor:
                logger.warning(f'不支持的解析引擎：{engine_name}（可用：{list(self._extractors.keys())}）')
                continue

            try:
                tables = extractor(pdf_path)
                if tables:
                    for t in tables:
                        t.engine = engine_name
                    all_tables.extend(tables)
                    logger.info(f'{engine_name} 解析成功：{len(tables)} 个表格')
                    break  # 成功就不试后面的
            except ImportError as e:
                logger.warning(f'{engine_name} 未安装，跳过：{e}')
                continue
            except Exception as e:
                logger.warning(f'{engine_name} 解析失败：{e}')
                continue

        if not all_tables:
            logger.warning('所有表格解析引擎均失败')

        return all_tables

    def _extract_pdfplumber(self, pdf_path: str) -> List[Table]:
        """pdfplumber 引擎

        需要安装：pip install pdfplumber

        Args:
            pdf_path: PDF 文件路径

        Returns:
            表格列表

        Raises:
            ImportError: pdfplumber 未安装
        """
        import pdfplumber

        tables: List[Table] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_tables = page.extract_tables()

                for idx, table_data in enumerate(page_tables):
                    if not table_data or len(table_data) < 2:
                        continue

                    # 清理表头
                    header = []
                    for col, h in enumerate(table_data[0]):
                        header.append(str(h).strip() if h else f"列{col + 1}")

                    # 清理数据行
                    rows = []
                    for row in table_data[1:]:
                        cleaned_row = [str(cell).strip() if cell else "" for cell in row]
                        # 跳过全空行
                        if any(cell for cell in cleaned_row):
                            rows.append(cleaned_row)

                    if not rows:
                        continue

                    title = self._find_table_title(page, idx)

                    tables.append(Table(
                        page=page_num,
                        title=title,
                        header=header,
                        rows=rows
                    ))

        return tables

    def _extract_camelot(self, pdf_path: str) -> List[Table]:
        """camelot 引擎（流模式）

        需要安装：pip install 'camelot-py[cv]'

        Args:
            pdf_path: PDF 文件路径

        Returns:
            表格列表

        Raises:
            ImportError: camelot 未安装
        """
        import camelot

        tables = camelot.read_pdf(pdf_path, flavor='stream', pages='all')
        results: List[Table] = []

        for idx, table in enumerate(tables):
            if table.df.empty:
                continue

            header = [str(h).strip() for h in table.df.iloc[0]]
            rows = []
            for _, row in table.df.iloc[1:].iterrows():
                cleaned = [str(cell).strip() for cell in row]
                if any(cell for cell in cleaned):
                    rows.append(cleaned)

            if not rows:
                continue

            results.append(Table(
                page=table.parsing.get('page', idx + 1),
                title=f"表格{idx + 1}",
                header=header,
                rows=rows
            ))

        return results

    def _extract_tabula(self, pdf_path: str) -> List[Table]:
        """tabula 引擎（需要 Java）

        需要安装：pip install tabula-py（同时需要 Java 环境）

        Args:
            pdf_path: PDF 文件路径

        Returns:
            表格列表

        Raises:
            ImportError: tabula 未安装或 Java 不可用
        """
        import tabula

        dfs = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
        results: List[Table] = []

        for idx, df in enumerate(dfs):
            if df.empty:
                continue

            header = [str(h).strip() for h in df.columns]
            rows = []
            for _, row in df.iterrows():
                cleaned = [str(cell).strip() for cell in row]
                if any(cell for cell in cleaned):
                    rows.append(cleaned)

            if not rows:
                continue

            results.append(Table(
                page=idx + 1,
                title=f"表格{idx + 1}",
                header=header,
                rows=rows
            ))

        return results

    def _find_table_title(self, page, table_idx: int) -> str:
        """查找表格标题（表格上方最近文本）

        Args:
            page: pdfplumber Page 对象
            table_idx: 表格在页面中的索引

        Returns:
            表格标题
        """
        try:
            tables = page.find_tables()
            if table_idx < len(tables):
                bbox = tables[table_idx].bbox  # (x0, top, x1, bottom)
                # 提取表格上方的文本
                above_text = page.crop((0, 0, page.width, bbox[1])).extract_text()
                lines = [line.strip() for line in above_text.split('\n') if line.strip()]
                return lines[-1] if lines else f"表格{table_idx + 1}"
        except Exception as e:
            logger.debug(f'查找表格标题失败：{e}')

        return f"表格{table_idx + 1}"

    def extract_interface_tables(self, tables: List[Table]) -> List[InterfaceTable]:
        """从表格中筛选接口定义表

        识别规则：
        - 表头包含接口/API/URL 等关键词 → interface 类型
        - 表头包含模块/功能/接口名称等关键词 → module 类型

        Args:
            tables: 原始表格列表

        Returns:
            接口表格列表
        """
        results: List[InterfaceTable] = []

        for table in tables:
            header_text = ' '.join(table.header).lower()

            if any(kw in header_text for kw in self.INTERFACE_KEYWORDS):
                results.append(InterfaceTable(
                    title=table.title,
                    header=table.header,
                    rows=table.rows,
                    type='interface',
                    page=table.page
                ))
            elif any(kw in header_text for kw in self.MODULE_KEYWORDS):
                results.append(InterfaceTable(
                    title=table.title,
                    header=table.header,
                    rows=table.rows,
                    type='module',
                    page=table.page
                ))

        return results
