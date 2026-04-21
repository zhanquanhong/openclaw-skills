# -*- coding: utf-8 -*-
"""PDF 解析器 - 生产级"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PDFParser:
    """PDF 解析器 - 生产级"""
    
    def __init__(self):
        self.pdfplumber = None
        self._import_pdfplumber()
    
    def _import_pdfplumber(self):
        """延迟导入 pdfplumber"""
        try:
            import pdfplumber
            self.pdfplumber = pdfplumber
            logger.info("pdfplumber 导入成功")
        except ImportError:
            logger.warning("pdfplumber 未安装，PDF 解析功能不可用")
    
    def extract(self, pdf_path: str) -> Optional[str]:
        """提取 PDF 文本内容"""
        if not self.pdfplumber:
            logger.error("pdfplumber 未安装")
            return None
        
        try:
            logger.info(f"开始解析 PDF: {pdf_path}")
            
            with self.pdfplumber.open(pdf_path) as pdf:
                text_parts = []
                for i, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text() or ''
                    if page_text.strip():
                        text_parts.append(f"--- 第{i}页 ---\n{page_text}")
                
                full_text = '\n'.join(text_parts)
                logger.info(f"PDF 解析完成：{len(pdf.pages)}页，{len(full_text)}字符")
                return full_text
                
        except Exception as e:
            logger.error(f"PDF 解析失败：{e}", exc_info=True)
            return None
    
    def is_available(self) -> bool:
        """检查 PDF 解析功能是否可用"""
        return self.pdfplumber is not None
