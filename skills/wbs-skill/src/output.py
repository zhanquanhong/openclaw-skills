"""Excel 输出模块"""

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from typing import List, Dict
import re


def clean_text(text: str) -> str:
    """清理 Excel 不支持的字符"""
    if not text:
        return ''
    # 移除 openpyxl 不支持的控制字符
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', str(text))
    return text


def export_to_excel(tasks: List[Dict], output_path: str):
    """
    导出任务到 Excel
    
    Args:
        tasks: 任务列表
        output_path: 输出文件路径
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "任务分解总表"
    
    # 样式定义
    header_font = Font(bold=True, size=12)
    header_alignment = Alignment(horizontal='center', vertical='center')
    cell_alignment = Alignment(vertical='center', wrap_text=True)
    
    # 边框
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # 表头（新增任务来源列）
    headers = ['任务模块', '任务 ID', '任务内容', '任务来源', '依赖', '可验收标准']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.alignment = header_alignment
        cell.border = thin_border
    
    # 数据行
    for row_idx, task in enumerate(tasks, 2):
        ws.cell(row=row_idx, column=1, value=clean_text(task.get('任务模块', '未分类'))).alignment = cell_alignment
        ws.cell(row=row_idx, column=2, value=clean_text(task.get('任务 ID', ''))).alignment = cell_alignment
        ws.cell(row=row_idx, column=3, value=clean_text(task.get('任务内容', ''))).alignment = cell_alignment
        ws.cell(row=row_idx, column=4, value=clean_text(task.get('任务来源', ''))).alignment = cell_alignment  # 新增列
        ws.cell(row=row_idx, column=5, value=clean_text(task.get('依赖', '无'))).alignment = cell_alignment
        ws.cell(row=row_idx, column=6, value=clean_text(task.get('可验收标准', ''))).alignment = cell_alignment
        
        # 应用边框
        for col in range(1, 7):
            ws.cell(row=row_idx, column=col).border = thin_border
    
    # 调整列宽
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 10
    ws.column_dimensions['C'].width = 50
    ws.column_dimensions['D'].width = 40  # 任务来源列
    ws.column_dimensions['E'].width = 10
    ws.column_dimensions['F'].width = 35
    
    # 自动筛选
    ws.auto_filter.ref = ws.dimensions
    
    wb.save(output_path)
