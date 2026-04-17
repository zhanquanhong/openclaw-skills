"""PDF 解析模块"""

import re
from typing import List, Dict

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
    """
    解析 PDF 文件，提取文本
    
    Args:
        pdf_path: PDF 文件路径
        
    Returns:
        str: 提取的文本内容
    """
    text = ""
    
    # 优先使用 pdfplumber
    if HAS_PDFPLUMBER:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            text = f"pdfplumber 解析失败：{str(e)}"
    
    # 回退到 PyPDF2
    elif HAS_PYPDF2:
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            text = f"PyPDF2 解析失败：{str(e)}"
    else:
        text = "PDF 解析失败：未安装 pdfplumber 或 PyPDF2"
    
    # 修复换行截断
    text = fix_line_breaks(text)
    
    return text


def fix_line_breaks(text: str) -> str:
    """
    修复 PDF 换行截断
    
    Args:
        text: 原始文本
        
    Returns:
        str: 修复后的文本
    """
    # 合并被换行截断的中文词汇
    text = re.sub(r'([\u4e00-\u9fa5])\n([\u4e00-\u9fa5])', r'\1\2', text)
    
    # 合并被换行截断的 REST API 路径
    text = re.sub(r'(/api/[\w-]+)\n([\w/-]+)', r'\1\2', text)
    
    # 移除多余的空行
    text = re.sub(r'\n\s*\n', '\n', text)
    
    return text


def clean_text(text: str) -> str:
    """
    清理文本中的乱码和特殊字符
    
    Args:
        text: 原始文本
        
    Returns:
        str: 清理后的文本
    """
    if not text:
        return ''
    
    # 移除控制字符（0x00-0x1F, 0x7F）
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # 替换常见的乱码字符
    replacements = {
        '⼿': '手',
        '⽤': '用',
        '⼾': '户',
        '⼆': '二',
        '⼭': '山',
        '⼝': '口',
        '⼥': '女',
        '⼦': '子',
        '⼫': '尸',
        '⼭': '山',
        '⽂': '文',
        '⽅': '方',
        '⽆': '无',
        '⽇': '日',
        '⽉': '月',
        '⽊': '木',
        '⽔': '水',
        '⽕': '火',
        '⼟': '土',
        '⾦': '金',
        '⽊': '木',
        '⻘': '青',
        '⻏': '阝',
        '⻓': '长',
        '⻔': '门',
        '⻄': '西',
        '⻧': '龙',
        '⻨': '麦',
        '⻩': '黄',
        '⻮': '齿',
        '⻯': '龙',
        '⻰': '龙',
        '⻱': '龟',
        '⻲': '龟',
        '⻳': '龟',
        '⻴': '页',
        '⻵': '风',
        '⻶': '飞',
        '⻷': '食',
        '⻸': '首',
        '⻹': '香',
        '⻺': '马',
        '⻻': '骨',
        '⻼': '高',
        '⻽': '髟',
        '⻾': '鬥',
        '⻿': '鬯',
        '⼀': '一',
        '⼁': '丨',
        '⼂': '丶',
        '⼃': '丿',
        '⼄': '乙',
        '⼅': '五',
        '⼆': '二',
        '⼆': '二',
        '⼆': '二',
        '⽀': '支',
        '⽂': '文',
        '⽂': '文',
        '⽂': '文',
    }
    
    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)
    
    # 移除重复的词（如"列表列表"→"列表"）
    text = re.sub(r'(列表 | 管理 | 功能 | 配置 | 接口 | 任务 | 开发 | 逻辑 | 技能 | 模块 | 查询 | 删除 | 安装 | 搜索)\1', r'\1', text)
    
    # 移除多余空格和制表符（但保留换行符）
    text = re.sub(r'[ \t]+', ' ', text)
    
    return text


def extract_lines(text: str) -> List[str]:
    """
    提取文本行（过滤空行）
    
    Args:
        text: 文本内容
        
    Returns:
        list: 文本行列表
    """
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if line:
            lines.append(line)
    return lines
