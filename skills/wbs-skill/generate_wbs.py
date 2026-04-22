#!/usr/bin/env python3
"""WBS 一键生成器 - 生产级（双轨制 + 智能融合）"""

import sys
import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, '/home/admin/.openclaw/workspace/skills/wbs-skill')

from src.whitelist_manager import UserWhitelistManager, load_whitelist
from src.output import export_to_excel
from src.templates import get_acceptance_criteria
from src.decomposer_v3 import cleanup_old_files


def generate_wbs(
    pdf_path: str,
    output_dir: str = None,
    auto_learn: bool = True,
    require_confirm: bool = True
):
    """
    一键生成 WBS 任务分解（双轨制 + 智能融合）
    
    工作流程：
    1. PDF 提取所有任务（带任务来源、任务类型）
    2. 白名单匹配（标准化任务命名）
    3. 智能融合：任务内容←白名单，任务来源←PDF
    4. 生成 WBS
    5. 新任务自动学习（可选确认）
    
    Args:
        pdf_path: PDF 文件路径
        output_dir: 输出目录（默认：test-data/output）
        auto_learn: 是否自动学习新任务（默认 True）
        require_confirm: 学习前是否需要确认（默认 True）
    """
    # 1. 检查文件
    if not os.path.exists(pdf_path):
        print(f'❌ 文件不存在：{pdf_path}')
        sys.exit(1)
    
    # 2. 设置输出目录
    if not output_dir:
        workspace_output = Path(__file__).parent.parent.parent / 'test-data' / 'output'
        if workspace_output.exists():
            output_dir = str(workspace_output)
        else:
            output_dir = './output'
    os.makedirs(output_dir, exist_ok=True)
    
    # 3. 加载白名单
    print(f'📄 分析文件：{os.path.basename(pdf_path)}')
    print('📚 加载白名单（官方 + 用户）...')
    whitelist = load_whitelist()
    
    manager = UserWhitelistManager()
    stats = manager.get_stats()
    print(f'   官方：{stats["official_tasks"]} 个任务')
    print(f'   用户：{stats["user_tasks"]} 个任务（学习成果）')
    
    # 4. PDF 提取所有任务（带完整信息）
    print('🔍 从 PDF 提取任务（带任务来源）...')
    from src.whitelist_extractor_v7 import extract_tasks_with_auto_labels
    pdf_tasks_raw = extract_tasks_with_auto_labels(pdf_path)
    
    # 5. 智能融合：白名单 + PDF 提取
    print('🔄 智能融合（白名单标准化 + PDF 来源）...')
    tasks, new_tasks = smart_merge_tasks(whitelist, pdf_tasks_raw)
    
    print(f'   ✅ 匹配白名单：{len(tasks) - len(new_tasks)} 个任务')
    print(f'   🆕 新学习任务：{len(new_tasks)} 个任务')
    
    # 6. 生成任务 ID 和依赖
    task_id = 1
    module_last_task = {}  # 模块→最后一个任务 ID
    
    for task in tasks:
        task["任务 ID"] = f"T{task_id:03d}"
        module = task["任务模块"]
        
        # 设置依赖
        if module in module_last_task:
            task["依赖"] = module_last_task[module]
        else:
            task["依赖"] = "无"
        
        # 设置验收标准
        task["可验收标准"] = get_acceptance_criteria(
            'REST_API' if '接口' in task["任务内容"] else 'FEATURE',
            task["任务内容"]
        )
        
        module_last_task[module] = task["任务 ID"]
        task_id += 1
    
    # 7. 输出 Excel
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    pdf_name = os.path.basename(pdf_path).replace('.pdf', '')
    output_path = os.path.join(output_dir, f'WBS_{pdf_name}_{timestamp}.xlsx')
    
    export_to_excel(tasks, output_path)
    
    # 8. 清理旧文件
    cleanup_old_files(output_dir, keep_count=10)
    
    # 9. 学习新任务
    if new_tasks and auto_learn:
        learn_new_tasks(new_tasks, require_confirm)
    
    # 10. 输出统计
    print()
    print('=' * 80)
    print('✅ WBS 生成完成！')
    print('=' * 80)
    print(f'📁 输出文件：{output_path}')
    print(f'📊 任务总数：{len(tasks)} 个')
    
    # 任务类型统计
    task_types = {}
    for task in tasks:
        t = task.get("任务类型", "普通任务")
        task_types[t] = task_types.get(t, 0) + 1
    
    print()
    print('📋 任务类型统计:')
    for t, count in sorted(task_types.items()):
        print(f'  {t}: {count}个')
    
    print()
    print('💡 提示：')
    print('  - 文件已保存到输出目录，自动保留最新 10 份')
    print('  - 新任务已自动学习，git pull 不会丢失')
    print('  - 使用 --no-learn 禁用自动学习')
    print('=' * 80)
    
    return output_path


def smart_merge_tasks(
    whitelist: Dict[str, List],
    pdf_tasks_raw: Dict[str, List[Dict]]
) -> Tuple[List[Dict], List[Dict]]:
    """
    智能融合：白名单标准化 + PDF 来源信息
    
    Args:
        whitelist: 白名单（官方 + 用户）
        pdf_tasks_raw: PDF 提取的原始任务
        
    Returns:
        tuple: (融合后的任务列表，新任务列表)
    """
    final_tasks = []
    new_tasks = []
    
    # 构建白名单查找表（任务内容→标准化信息）
    whitelist_lookup = {}
    for module, items in whitelist.items():
        for item in items:
            if isinstance(item, dict):
                content = item.get('任务内容', '')
                whitelist_lookup[content] = {
                    '模块': module,
                    '标准化名': content
                }
            else:
                # 字符串格式
                whitelist_lookup[str(item)] = {
                    '模块': module,
                    '标准化名': str(item)
                }
    
    # 处理 PDF 提取的任务
    for module, items in pdf_tasks_raw.items():
        for pdf_task in items:
            task_content = pdf_task.get('任务内容', '')
            task_source = pdf_task.get('任务来源', '')
            task_type = pdf_task.get('任务类型', '普通任务')
            
            # 尝试匹配白名单
            matched = None
            for wl_content, wl_info in whitelist_lookup.items():
                if wl_content in task_content or task_content in wl_content:
                    matched = wl_info
                    break
            
            if matched:
                # 融合：白名单命名 + PDF 来源
                final_tasks.append({
                    '任务模块': matched['模块'],
                    '任务内容': matched['标准化名'],
                    '任务来源': task_source,
                    '任务类型': task_type
                })
            else:
                # 新任务：完全使用 PDF 信息
                final_tasks.append({
                    '任务模块': module,
                    '任务内容': task_content,
                    '任务来源': task_source,
                    '任务类型': task_type
                })
                new_tasks.append({
                    '任务模块': module,
                    '任务内容': task_content,
                    '任务来源': task_source,
                    '任务类型': task_type
                })
    
    return final_tasks, new_tasks


def learn_new_tasks(new_tasks: List[Dict], require_confirm: bool = True):
    """
    学习新任务并保存到用户白名单
    
    Args:
        new_tasks: 新任务列表
        require_confirm: 是否需要确认
    """
    if not new_tasks:
        return
    
    print()
    print('📚 发现新任务，是否学习？')
    for i, task in enumerate(new_tasks[:5], 1):  # 只显示前 5 个
        print(f'   {i}. {task["任务内容"]}（{task["任务来源"]}）')
    if len(new_tasks) > 5:
        print(f'   ... 还有 {len(new_tasks) - 5} 个任务')
    
    if require_confirm:
        confirm = input('\n是否保存到用户白名单？[Y/n]: ').strip().lower()
        if confirm == 'n':
            print('⏭️ 跳过学习')
            return
    
    # 保存到用户白名单
    manager = UserWhitelistManager()
    user_whitelist = manager.load_user()
    
    for task in new_tasks:
        module = task['任务模块']
        if module not in user_whitelist:
            user_whitelist[module] = []
        
        # 检查是否已存在
        existing = False
        for item in user_whitelist[module]:
            if isinstance(item, dict) and item.get('任务内容') == task['任务内容']:
                existing = True
                break
            elif isinstance(item, str) and item == task['任务内容']:
                existing = True
                break
        
        if not existing:
            user_whitelist[module].append({
                '任务内容': task['任务内容'],
                '任务来源': task['任务来源'],
                '任务类型': task['任务类型']
            })
    
    manager.save_user(user_whitelist)
    print(f'✅ 已学习 {len(new_tasks)} 个新任务到用户白名单')


def export_whitelist(output_path: str, include_official: bool = False):
    """导出用户白名单"""
    manager = UserWhitelistManager()
    manager.export(output_path, include_official)


def import_whitelist(input_path: str, merge: bool = True):
    """导入用户白名单"""
    manager = UserWhitelistManager()
    manager.import_whitelist(input_path, merge)


def show_stats():
    """显示统计信息"""
    manager = UserWhitelistManager()
    manager.print_stats()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='WBS 一键生成器（双轨制 + 智能融合）')
    parser.add_argument('pdf', nargs='?', help='PDF 文件路径')
    parser.add_argument('-o', '--output', help='输出目录')
    parser.add_argument('--no-learn', action='store_true', help='禁用自动学习')
    parser.add_argument('--no-confirm', action='store_true', help='学习时不需要确认')
    parser.add_argument('--export', help='导出用户白名单到指定路径')
    parser.add_argument('--import', dest='import_path', help='导入用户白名单')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    
    args = parser.parse_args()
    
    if args.stats:
        show_stats()
        sys.exit(0)
    
    if args.export:
        export_whitelist(args.export)
        sys.exit(0)
    
    if args.import_path:
        import_whitelist(args.import_path)
        sys.exit(0)
    
    if not args.pdf:
        print('Usage: python3 generate_wbs.py <PDF 文件路径> [选项]')
        print()
        print('示例:')
        print('  # 生成 WBS（自动学习新任务）')
        print('  python3 generate_wbs.py /path/to/技术方案.pdf')
        print()
        print('  # 生成 WBS（禁用自动学习）')
        print('  python3 generate_wbs.py /path/to/技术方案.pdf --no-learn')
        print()
        print('  # 生成 WBS（自动学习，不需要确认）')
        print('  python3 generate_wbs.py /path/to/技术方案.pdf --no-confirm')
        print()
        print('  # 导出用户白名单（分享给团队）')
        print('  python3 generate_wbs.py --export user_whitelist.yaml')
        print()
        print('  # 导入用户白名单（从团队获取）')
        print('  python3 generate_wbs.py --import team_whitelist.yaml')
        print()
        print('  # 显示统计信息')
        print('  python3 generate_wbs.py --stats')
        sys.exit(1)
    
    generate_wbs(
        args.pdf,
        args.output,
        auto_learn=not args.no_learn,
        require_confirm=not args.no_confirm
    )
