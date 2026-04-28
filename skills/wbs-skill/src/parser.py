"""PDF 解析模块（兼容旧版 API）

注意：此模块保留旧版 API 以兼容现有代码。
新功能请使用 src.document_parser.DocumentParser。
"""

import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False


def parse_pdf(pdf_path: str) -> str:
    """解析 PDF 文件，提取文本（兼容旧版 API）

    Args:
        pdf_path: PDF 文件路径

    Returns:
        提取的文本内容
    """
    text = ""

    if HAS_PDFPLUMBER:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ''
                    text += page_text + "\n"
        except Exception as e:
            logger.warning(f'pdfplumber 解析失败：{e}')

    if not text and HAS_PYPDF2:
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text() or ''
                    text += page_text + "\n"
        except Exception as e:
            logger.warning(f'PyPDF2 解析失败：{e}')

    if not text:
        raise RuntimeError('PDF 解析失败：未安装 pdfplumber 或 PyPDF2，或 PDF 为空')

    return fix_line_breaks(text)


def fix_line_breaks(text: str) -> str:
    """修复 PDF 换行截断

    Args:
        text: 原始文本

    Returns:
        修复后的文本
    """
    # 合并被换行截断的中文词汇
    text = re.sub(r'([\u4e00-\u9fa5])\n([\u4e00-\u9fa5])', r'\1\2', text)
    # 合并被换行截断的 REST API 路径
    text = re.sub(r'(/api/[\w-]+)\n([\w/-]+)', r'\1\2', text)
    # 移除多余空行
    text = re.sub(r'\n\s*\n', '\n', text)
    return text


def clean_text(text: str) -> str:
    """清理文本中的乱码和特殊字符

    Args:
        text: 原始文本

    Returns:
        清理后的文本
    """
    if not text:
        return ''

    # 移除控制字符
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # 替换常见乱码字符
    replacements = {
        '⼿': '手', '⽤': '用', '⼾': '户', '⼆': '二', '⼭': '山',
        '⼝': '口', '⼥': '女', '⼦': '子', '⽂': '文', '⽅': '方',
        '⽆': '无', '⽇': '日', '⽉': '月', '⽊': '木', '⽔': '水',
        '⽕': '火', '⼟': '土', '⾦': '金', '⽽': '而', '⼏': '几',
        '⽬': '目', '⽴': '立', '⽵': '竹', '⽶': '米',
        '⻔': '门', '⻋': '车', '⾛': '走', '⾜': '足', '⾷': '食',
        '⾔': '言', '⻓': '长', '⻄': '西', '⻨': '麦', '⻩': '黄',
    }

    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)

    # 移除重复词
    text = re.sub(
        r'(列表|管理|功能|配置|接口|任务|开发|逻辑|技能|模块|查询|删除|安装|搜索)\1',
        r'\1', text
    )

    # 移除多余空格和制表符（保留换行）
    text = re.sub(r'[ \t]+', ' ', text)

    return text


def extract_lines(text: str) -> List[str]:
    """提取文本行（过滤空行）

    Args:
        text: 文本内容

    Returns:
        文本行列表
    """
    return [line.strip() for line in text.split('\n') if line.strip()]
