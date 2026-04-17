"""WBS 白名单提取器 v7 - 生产级（自动识别新增/更新标注）"""

import PyPDF2
import re
import json
import sys
import os
from typing import Dict, List, Tuple

sys.path.insert(0, '/home/admin/.openclaw/workspace/skills/wbs-skill')


def extract_tasks_with_auto_labels(pdf_path: str) -> Dict[str, List[Dict]]:
    """
    从 PDF 提取任务，自动识别「新增」「更新」标注的关键任务
    
    Args:
        pdf_path: PDF 文件路径
        
    Returns:
        dict: {模块名：[{任务内容，任务来源，任务类型}]}
    """
    # 1. 解析 PDF
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        full_text = ''
        for page in reader.pages:
            page_text = page.extract_text() or ''
            full_text += page_text + '\n'
    
    # 2. 清理乱码
    replacements = {'⼿': '手', '⽤': '用', '⼾': '户', '⼆': '二', '⼭': '山', '⼝': '口',
                    '⼥': '女', '⼦': '子', '⽂': '文', '⽅': '方', '⽆': '无', '⽇': '日',
                    '⽉': '月', '⽊': '木', '⽔': '水', '⽕': '火', '⼟': '土', '⾦': '金',
                    '⽽': '而', '⼏': '几', '⽬': '目', '⽴': '立', '⽵': '竹', '⽶': '米'}
    for wrong, correct in replacements.items():
        full_text = full_text.replace(wrong, correct)
    
    # 3. 按行分割，保留行号
    lines = full_text.split('\n')
    
    # 4. 提取任务（自动识别新增/更新标注）
    tasks_by_module = {}
    current_module = ''
    current_section = ''
    current_subsection = ''
    
    # 关键任务标识词
    label_keywords = ['新增', '更新', '设计并实现', '批量获取']
    
    for line_num, line in enumerate(lines, 1):
        line_raw = line
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # 识别大章节（1.2.1 提取模型的文件 ID）
        if re.match(r'^\d+\.\d+\.\d+', line_stripped) and len(line_stripped) < 100:
            current_section = line_stripped
            current_subsection = ''
            # 根据章节号设置模块名
            if '1.2.1' in line_stripped:
                current_module = '1.2.1 提取模型的文件 ID'
            elif '1.2.2' in line_stripped:
                current_module = '1.2.2 批量获取对话详情'
            elif '1.2.3' in line_stripped:
                current_module = '1.2.3 批量获取对话的文件详情'
        
        # 识别小章节
        if re.match(r'^\d+\.', line_stripped) and '1.2.' in line_stripped and len(line_stripped) < 80:
            if '1.2.1' not in line_stripped and '1.2.2' not in line_stripped and '1.2.3' not in line_stripped:
                current_subsection = line_stripped
        
        # 识别任务行（包含关键词）
        is_task_line = False
        task_desc = ''
        task_type = '普通任务'
        
        # 检查是否包含关键任务标识
        has_label = any(kw in line_stripped for kw in label_keywords)
        
        if has_label:
            # 提取任务描述
            if '任务：' in line_stripped:
                task_desc = line_stripped.split('任务：')[1].strip()
            else:
                task_desc = line_stripped
            
            # 识别任务类型
            if '【新增】' in line_stripped or ('新增' in line_stripped and '接口' in line_stripped):
                task_type = '新增接口'
            elif '【更新】' in line_stripped or ('更新' in line_stripped and '接口' in line_stripped):
                task_type = '更新接口'
            elif '设计并实现' in line_stripped:
                task_type = '新增接口'
            elif '批量获取' in line_stripped:
                task_type = '批量接口'
            else:
                task_type = '普通任务'
            
            is_task_line = True
        
        # 保存任务（带任务类型标注）
        if is_task_line and current_module:
            # 构建任务来源（精确复制原文）
            source_parts = []
            if current_section:
                source_parts.append(current_section)
            if current_subsection:
                source_parts.append(current_subsection)
            source_parts.append(f'第{line_num}行')
            
            source = ' | '.join(source_parts)
            
            # 避免重复
            task_key = f'{current_module}:{task_desc}'
            if current_module not in tasks_by_module:
                tasks_by_module[current_module] = []
            
            if not any(t['任务内容'] == task_desc for t in tasks_by_module[current_module]):
                tasks_by_module[current_module].append({
                    '任务内容': task_desc,
                    '任务来源': source,
                    '任务类型': task_type
                })
    
    return tasks_by_module


def save_whitelist(tasks: Dict[str, List[Dict]], output_path: str):
    """保存白名单到 JSON 文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    # 找到 OpenClaw分享技术方案
    test_data_dir = '/home/admin/.openclaw/workspace/test-data'
    pdf_files = [f for f in os.listdir(test_data_dir) if 'OpenClaw分享' in f and f.endswith('.pdf')]
    if not pdf_files:
        print('❌ 未找到 OpenClaw分享技术方案')
        sys.exit(1)
    
    pdf_path = os.path.join(test_data_dir, pdf_files[0])
    output_path = '/home/admin/.openclaw/workspace/skills/wbs-skill/data/openclaw_share_whitelist_auto.json'
    
    tasks = extract_tasks_with_auto_labels(pdf_path)
    save_whitelist(tasks, output_path)
    
    print(f'✅ 自动提取完成（带任务类型标注）')
    print()
    
    # 统计任务类型
    type_stats = {}
    for module, items in tasks.items():
        for item in items:
            task_type = item.get('任务类型', '普通任务')
            type_stats[task_type] = type_stats.get(task_type, 0) + 1
    
    print('📋 任务类型统计:')
    for t, c in sorted(type_stats.items(), key=lambda x: -x[1]):
        print(f'  {t}: {c}个')
    print()
    
    for module, items in sorted(tasks.items()):
        if items:
            print(f'【{module}】({len(items)}个)')
            for i, item in enumerate(items, 1):
                task_type = item.get('任务类型', '普通任务')
                type_icon = '🆕' if '新增' in task_type else '🔄' if '更新' in task_type else '📋'
                print(f'  {type_icon} {i}. {item["任务内容"][:60]}...')
                print(f'     来源：{item["任务来源"]}')
                print(f'     类型：{task_type}')
            print()
    
    print(f'输出文件：{output_path}')
