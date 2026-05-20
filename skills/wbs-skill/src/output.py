"""Excel 输出模块"""

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from typing import List, Dict, Optional
import re
import logging

from src.consistency_checker import ValidationResult

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """清理 Excel 不支持的字符"""
    if not text:
        return ''
    # 移除 openpyxl 不支持的控制字符
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', str(text))
    return text


def export_to_excel(
    tasks: List[Dict],
    output_path: str,
    validation_results: Optional[Dict[str, List]] = None,
    timing_info: Optional[Dict[str, float]] = None,
) -> None:
    """
    导出任务到 Excel，包含验证结果 sheet

    Args:
        tasks: 任务列表
        output_path: 输出文件路径
        validation_results: 验证结果（可选），用于"验证结果"sheet
        timing_info: 时序信息（可选），用于统计
    """
    wb = Workbook()

    # ==================== Sheet 1: 任务分解总表 ====================
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

    # 表头（v4.0）
    headers = ['任务模块', '任务 ID', '任务内容', '任务来源',
               '任务类型', '依赖', '可验收标准', '验证状态', '处理时间(ms)']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.alignment = header_alignment
        cell.border = thin_border

    # 验证状态颜色
    green_fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
    yellow_fill = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')
    red_fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')

    # 数据行
    for row_idx, task in enumerate(tasks, 2):
        ws.cell(row=row_idx, column=1, value=clean_text(task.get('任务模块', '未分类'))).alignment = cell_alignment
        ws.cell(row=row_idx, column=2, value=clean_text(task.get('任务 ID', ''))).alignment = cell_alignment
        ws.cell(row=row_idx, column=3, value=clean_text(task.get('任务内容', ''))).alignment = cell_alignment
        ws.cell(row=row_idx, column=4, value=clean_text(task.get('任务来源', ''))).alignment = cell_alignment

        ws.cell(row=row_idx, column=5, value=clean_text(task.get('任务类型', '普通任务'))).alignment = cell_alignment
        ws.cell(row=row_idx, column=6, value=clean_text(task.get('依赖', '无'))).alignment = cell_alignment
        ws.cell(row=row_idx, column=7, value=clean_text(task.get('可验收标准', ''))).alignment = cell_alignment

        # 验证状态列
        validation_status = task.get('验证状态', 'PASS')
        validation_cell = ws.cell(row=row_idx, column=8, value=validation_status)
        validation_cell.alignment = cell_alignment
        if validation_status == 'PASS':
            validation_cell.fill = green_fill
        elif validation_status == 'WARN':
            validation_cell.fill = yellow_fill
        elif validation_status == 'FAIL':
            validation_cell.fill = red_fill

        # 处理时间列
        proc_time = task.get('处理时间(ms)', '')
        ws.cell(row=row_idx, column=9, value=str(proc_time) if proc_time else '').alignment = cell_alignment

        # 应用边框
        for col in range(1, len(headers) + 1):
            ws.cell(row=row_idx, column=col).border = thin_border

    # 调整列宽
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 10
    ws.column_dimensions['C'].width = 50
    ws.column_dimensions['D'].width = 40
    ws.column_dimensions['E'].width = 40
    ws.column_dimensions['F'].width = 15
    ws.column_dimensions['G'].width = 10
    ws.column_dimensions['H'].width = 35
    ws.column_dimensions['I'].width = 12
    ws.column_dimensions['J'].width = 14

    # 自动筛选
    ws.auto_filter.ref = ws.dimensions

    # ==================== Sheet 2: 验证结果 ====================
    if validation_results:
        ws2 = wb.create_sheet("验证结果")

        # 表头
        v_headers = ['验证项', '状态', '任务内容', '详细信息']
        for col, header in enumerate(v_headers, 1):
            cell = ws2.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.alignment = header_alignment
            cell.border = thin_border

        row_idx = 2
        for vtype, vlist in validation_results.items():
            if not vlist:
                continue
            for vresult in vlist:
                if isinstance(vresult, dict):
                    issues = vresult.get('issues', [])
                    status = 'PASS' if vresult.get('is_valid', True) else 'FAIL'
                    content = vresult.get('content', '')
                else:
                    issues = vresult.issues if hasattr(vresult, 'issues') else []
                    status = 'PASS' if vresult.is_valid else 'FAIL'
                    content = vresult.get('content', '') if isinstance(vresult, dict) else ''

                issue_text = '; '.join(issues) if issues else '无'
                ws2.cell(row=row_idx, column=1, value=vtype).alignment = cell_alignment
                ws2.cell(row=row_idx, column=2, value=status).alignment = cell_alignment
                ws2.cell(row=row_idx, column=3, value=clean_text(content)).alignment = cell_alignment
                ws2.cell(row=row_idx, column=4, value=clean_text(issue_text)).alignment = cell_alignment
                for col in range(1, 5):
                    ws2.cell(row=row_idx, column=col).border = thin_border

                # 状态颜色
                status_cell = ws2.cell(row=row_idx, column=2)
                if status == 'FAIL':
                    status_cell.fill = red_fill
                elif status == 'WARN':
                    status_cell.fill = yellow_fill
                else:
                    status_cell.fill = green_fill

                row_idx += 1

        # 调整列宽
        ws2.column_dimensions['A'].width = 20
        ws2.column_dimensions['B'].width = 10
        ws2.column_dimensions['C'].width = 50
        ws2.column_dimensions['D'].width = 60

        # 时序信息（如果有）
        if timing_info:
            row_idx += 1
            ws2.cell(row=row_idx, column=1, value="性能统计").font = Font(bold=True, size=11)
            row_idx += 1
            for key, value in timing_info.items():
                ws2.cell(row=row_idx, column=1, value=key)
                ws2.cell(row=row_idx, column=2, value=f"{value:.1f}ms" if isinstance(value, float) else str(value))
                for col in range(1, 3):
                    ws2.cell(row=row_idx, column=col).border = thin_border
                row_idx += 1

    wb.save(output_path)
    logger.info(f'Excel 导出完成：{output_path}')
