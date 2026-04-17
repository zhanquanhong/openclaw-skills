#!/usr/bin/env python3
"""WBS 一键生成器 - 方案 C 生产级（支持用户白名单学习）"""

import sys
import os
import re
import json
from datetime import datetime

sys.path.insert(0, '/home/admin/.openclaw/workspace/skills/wbs-skill')

from src.whitelist_manager import UserWhitelistManager, load_whitelist
from src.output import export_to_excel
from src.templates import get_acceptance_criteria
from src.decomposer_v3 import cleanup_old_files


def generate_wbs(pdf_path: str, output_dir: str = None, use_user_whitelist: bool = True):
    """
    一键生成 WBS 任务分解
    
    Args:
        pdf_path: PDF 文件路径
        output_dir: 输出目录（默认：test-data/output）
        use_user_whitelist: 是否使用用户白名单（默认 True）
    """
    # 1. 检查文件
    if not os.path.exists(pdf_path):
        print(f'❌ 文件不存在：{pdf_path}')
        sys.exit(1)
    
    # 2. 设置输出目录
    if not output_dir:
        output_dir = '/home/admin/.openclaw/workspace/test-data/output'
    os.makedirs(output_dir, exist_ok=True)
    
    # 3. 加载白名单
    print(f'📄 分析文件：{os.path.basename(pdf_path)}')
    
    if use_user_whitelist:
        print('📚 加载白名单（官方 + 用户）...')
        whitelist = load_whitelist()
        
        # 显示统计
        manager = UserWhitelistManager()
        stats = manager.get_stats()
        print(f'   官方：{stats["official_tasks"]} 个任务')
        print(f'   用户：{stats["user_tasks"]} 个任务（学习成果）')
    else:
        print('🔍 自动提取任务（不使用白名单）...')
        from src.whitelist_extractor_v7 import extract_tasks_with_auto_labels
        whitelist_raw = extract_tasks_with_auto_labels(pdf_path)
        
        # 转换为标准格式
        whitelist = {}
        for module, items in whitelist_raw.items():
            whitelist[module] = []
            for item in items:
                task_content = item.get('任务内容', '')
                # 跳过章节标题
                if re.match(r'^\d+\.\d+\.\d+', task_content) and len(task_content) < 50:
                    continue
                whitelist[module].append(item)
    
    # 4. 生成任务列表
    tasks = []
    task_id = 1
    
    for module, items in whitelist.items():
        module_tasks = []
        for item in items:
            if isinstance(item, dict):
                task_content = item.get('任务内容', '')
                task_source = item.get('任务来源', '')
                task_type = item.get('任务类型', '普通任务')
            else:
                task_content = str(item)
                task_source = ''
                task_type = '普通任务'
            
            task = {
                "任务模块": module,
                "任务 ID": f"T{task_id:03d}",
                "任务内容": task_content,
                "任务来源": task_source,
                "任务类型": task_type,
                "依赖": "无" if not module_tasks else module_tasks[-1]["任务 ID"],
                "可验收标准": get_acceptance_criteria('REST_API' if '接口' in task_content else 'FEATURE', task_content)
            }
            module_tasks.append(task)
            task_id += 1
        tasks.extend(module_tasks)
    
    # 5. 输出 Excel
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    pdf_name = os.path.basename(pdf_path).replace('.pdf', '')
    output_path = os.path.join(output_dir, f'WBS_{pdf_name}_{timestamp}.xlsx')
    
    print(f'📊 生成任务分解：{len(tasks)} 个任务')
    export_to_excel(tasks, output_path)
    
    # 6. 清理旧文件
    cleanup_old_files(output_dir, keep_count=10)
    
    # 7. 输出统计
    print()
    print('=' * 80)
    print('✅ WBS 生成完成！')
    print('=' * 80)
    print(f'📁 输出文件：{output_path}')
    print(f'📊 任务总数：{len(tasks)} 个')
    
    # 任务类型统计
    type_stats = {}
    for t in tasks:
        tt = t.get('任务类型', '普通任务')
        type_stats[tt] = type_stats.get(tt, 0) + 1
    
    print()
    print('📋 任务类型统计:')
    for tt, c in sorted(type_stats.items(), key=lambda x: -x[1]):
        icon = '🆕' if '新增' in tt else '🔄' if '更新' in tt else '📋'
        print(f'  {icon} {tt}: {c}个')
    
    print()
    print('💡 提示：')
    print('  - 文件已保存到输出目录，自动保留最新 10 份')
    print('  - 用户白名单自动保存，git pull 不会丢失')
    print('  - 使用 --export 导出白名单分享给团队')
    print('=' * 80)
    
    return output_path


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
    
    parser = argparse.ArgumentParser(description='WBS 一键生成器')
    parser.add_argument('pdf', nargs='?', help='PDF 文件路径')
    parser.add_argument('-o', '--output', help='输出目录')
    parser.add_argument('--no-user', action='store_true', help='不使用用户白名单（仅自动提取）')
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
        print('  # 生成 WBS（使用用户白名单）')
        print('  python3 generate_wbs.py /path/to/技术方案.pdf')
        print()
        print('  # 生成 WBS（不使用用户白名单，仅自动提取）')
        print('  python3 generate_wbs.py /path/to/技术方案.pdf --no-user')
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
    
    generate_wbs(args.pdf, args.output, not args.no_user)
