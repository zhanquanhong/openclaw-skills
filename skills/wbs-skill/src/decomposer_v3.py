"""任务分解器 v3 - 生产级（白名单模式）"""

import re
import yaml
import sys
sys.path.insert(0, '/home/admin/.openclaw/workspace/skills/wbs-skill')

from src.parser import parse_pdf, clean_text
from src.templates import get_acceptance_criteria
from src.output import export_to_excel
from typing import List, Dict


def load_whitelist(whitelist_path: str) -> Dict[str, List[str]]:
    """加载白名单配置"""
    with open(whitelist_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def extract_module_from_text(text: str) -> str:
    """从文本中提取当前模块"""
    SECTION_MODULE_MAP = {
        '1.2.1': '技能中心',
        '1.2.2': '推荐区',
        '1.2.3': '对话管理',
        '1.2.4': '对话管理',
        '1.2.5': '渠道模块',
        '1.2.6': '定时任务模块',
        '1.2.7': 'mClaw 模块',
        '1.3': '外放接口模块',
    }
    
    for section, module in SECTION_MODULE_MAP.items():
        if text.startswith(section):
            return module
    return '未分类'


def decompose(pdf_path: str, whitelist_path: str, output_path: str = None) -> List[Dict]:
    """
    分解后端开发任务（生产级 - 白名单模式）
    
    Args:
        pdf_path: PDF 文件路径
        whitelist_path: 白名单 YAML 路径
        output_path: Excel 输出路径
        
    Returns:
        list: 任务列表
    """
    # 1. 加载白名单
    whitelist = load_whitelist(whitelist_path)
    
    # 2. 解析 PDF
    raw_text = parse_pdf(pdf_path)
    text = clean_text(raw_text)
    
    # 3. 按白匹配匹配任务
    tasks = []
    task_id = 1
    seen = set()
    
    # 按模块分组处理
    for module, interfaces in whitelist.items():
        module_tasks = []
        
        for item in interfaces:
            # 支持两种格式：字符串或字典（包含任务内容和任务来源）
            if isinstance(item, dict):
                task_content = item.get('任务内容', '')
                task_source = item.get('任务来源', '')
            else:
                task_content = item
                task_source = ''
            
            # 提取接口名称（去掉 API 路径部分）
            iface_name = task_content.split(' (')[0] if ' (' in task_content else task_content
            
            task = {
                "任务模块": module,
                "任务 ID": f"T{task_id:03d}",
                "任务内容": task_content,
                "任务来源": task_source,
                "依赖": "无" if not module_tasks else module_tasks[-1]["任务 ID"],
                "可验收标准": get_acceptance_criteria('REST_API', iface_name)
            }
            module_tasks.append(task)
            task_id += 1
        
        tasks.extend(module_tasks)
    
    # 4. 输出 Excel
    if output_path:
        export_to_excel(tasks, output_path)
    
    return tasks


import os
from datetime import datetime

def cleanup_old_files(output_dir: str, keep_count: int = 10):
    """清理旧文件，保留最新的 N 份"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        return
    
    # 获取所有 xlsx 文件
    files = []
    for f in os.listdir(output_dir):
        if f.endswith('.xlsx'):
            filepath = os.path.join(output_dir, f)
            files.append((filepath, os.path.getmtime(filepath)))
    
    # 按修改时间排序
    files.sort(key=lambda x: x[1], reverse=True)
    
    # 删除旧文件
    for filepath, _ in files[keep_count:]:
        os.remove(filepath)
        print(f'🗑️ 已删除：{os.path.basename(filepath)}')

if __name__ == '__main__':
    pdf_path = '/home/admin/.openclaw/workspace/test-data/云端OpenClaw三期技术方案.pdf'
    whitelist_path = '/home/admin/.openclaw/workspace/skills/wbs-skill/data/whitelist.yaml'
    
    # 输出目录
    output_dir = '/home/admin/.openclaw/workspace/test-data/output'
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成带时间戳的文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = os.path.join(output_dir, f'WBS_{timestamp}.xlsx')
    
    tasks = decompose(pdf_path, whitelist_path, output_path)
    
    # 清理旧文件
    cleanup_old_files(output_dir, keep_count=10)
    
    print(f'✅ v3 白名单版：{len(tasks)} 个任务')
    print()
    for t in tasks:
        print(f"  {t['任务 ID']}: [{t['任务模块']}] {t['任务内容']}")
    print()
    print('模块统计:')
    modules = {}
    for t in tasks:
        m = t['任务模块']
        modules[m] = modules.get(m, 0) + 1
    for m, c in sorted(modules.items(), key=lambda x: -x[1]):
        print(f'  {m}: {c}个')
    print(f'\n输出文件：{output_path}')
