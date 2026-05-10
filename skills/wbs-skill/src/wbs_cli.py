#!/usr/bin/env python3
"""WBS CLI 统一入口

作为 wbs.sh / wbs.bat 的 Python 调用入口，
负责意图解析、参数转换、调用核心引擎。

使用方式：
    python3 src/wbs_cli.py --file 技术方案.pdf
    python3 src/wbs_cli.py --file 技术方案.pdf --intent "按周分解"

错误码：
    0: 成功
    1: 环境检查失败
    2: 文件不存在或格式不支持
    3: 文档解析失败
    4: Excel 输出失败
"""

import argparse
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# 确保能导入兄弟模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.intent_parser import IntentParser
from src.env_checker import EnvChecker
from src.document_parser import DocumentParser
from src.table_extractor import TableExtractor
from src.whitelist_manager import UserWhitelistManager, load_whitelist
from src.output import export_to_excel
from src.templates import get_acceptance_criteria
from src.decomposer_v3 import cleanup_old_files
from generate_wbs import (
    extract_tasks_from_document,
    smart_merge_tasks,
    learn_new_tasks,
    _split_large_modules,
    _sort_tasks_by_module,
    _check_content_quality,
)

logger = logging.getLogger(__name__)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)


def _apply_intent_filters(tasks: List[Dict], intent_info: Dict) -> List[Dict]:
    """根据意图参数过滤任务

    在生成完整任务列表后，根据用户意图进行后置过滤。

    过滤顺序：
    1. 排除过滤（先去掉不需要的）
    2. 聚焦过滤（只保留重点关注的）
    3. 类型过滤（按任务类型筛选）

    Args:
        tasks: 原始任务列表
        intent_info: 意图解析结果

    Returns:
        过滤后的任务列表
    """
    filtered = list(tasks)
    original_count = len(filtered)

    # 排除过滤：去掉包含排除关键词的任务
    exclude = intent_info.get('exclude_keywords', [])
    if exclude:
        before = len(filtered)
        filtered = [
            t for t in filtered
            if not any(kw in t.get('任务内容', '') for kw in exclude)
        ]
        removed = before - len(filtered)
        if removed > 0:
            print(f'🔽 排除过滤：移除 {removed} 个任务（关键词：{", ".join(exclude)}）')

    # 聚焦过滤：只保留包含聚焦关键词的任务
    focus = intent_info.get('focus_modules', [])
    if focus:
        before = len(filtered)
        filtered = [
            t for t in filtered
            if any(
                kw in t.get('任务内容', '') or
                kw in t.get('任务模块', '')
                for kw in focus
            )
        ]
        if len(filtered) < before:
            print(f'🔽 聚焦过滤：保留 {len(filtered)} 个任务（聚焦：{", ".join(focus)}）')

    # 类型过滤：只保留指定类型的任务
    types = intent_info.get('task_types', [])
    if types:
        type_keyword_map = {
            'backend': ['后端', '服务端', 'Service', 'Controller', 'Manager', 'Impl'],
            'frontend': ['前端', '页面', 'Vue', 'React', 'H5', '小程序', 'UI'],
            'api': ['接口', 'API', 'REST', 'HTTP', 'RPC', 'POST', 'GET', 'PUT', 'DELETE'],
            'database': ['数据库', '表', 'SQL', 'DDL', '建表', '索引', '字段'],
            'devops': ['部署', 'Docker', 'K8s', '运维', 'CI', 'CD', '容器', '脚本'],
        }
        keywords = []
        for t in types:
            keywords.extend(type_keyword_map.get(t, []))

        if keywords:
            before = len(filtered)
            filtered = [
                t for t in filtered
                if any(kw in t.get('任务内容', '') for kw in keywords)
            ]
            if len(filtered) < before:
                print(f'🔽 类型过滤：保留 {len(filtered)} 个任务（类型：{", ".join(types)}）')

    # 输出过滤统计
    if len(filtered) != original_count:
        print(f'📊 过滤结果：{original_count} → {len(filtered)} 个任务')

    return filtered


def _get_output_dir() -> str:
    """获取默认输出目录

    优先级：
    1. 环境变量 WBS_OUTPUT_DIR
    2. wbs-skill/output/
    3. 当前目录/output/

    Returns:
        输出目录路径
    """
    # 优先级 1：环境变量
    env_dir = os.environ.get('WBS_OUTPUT_DIR')
    if env_dir:
        return env_dir

    # 优先级 2：wbs-skill/output/
    skill_dir = Path(__file__).parent.parent
    output_dir = skill_dir / 'output'

    # 优先级 3：当前目录/output/
    if not output_dir.exists():
        output_dir = Path.cwd() / 'output'

    return str(output_dir)


def generate_wbs_with_intent(
    file_path: str,
    output_dir: str,
    section_template: str = 'numeric',
    auto_learn: bool = True,
    require_confirm: bool = True,
    intent_info: Dict = None,
) -> str:
    """生成 WBS 任务分解（支持意图过滤）

    复用 generate_wbs.py 的核心逻辑，但允许在生成 Excel 前进行意图过滤。

    Args:
        file_path: 文档文件路径
        output_dir: 输出目录
        section_template: 章节识别模板
        auto_learn: 是否自动学习新任务
        require_confirm: 学习前是否需要确认
        intent_info: 意图解析结果（可选）

    Returns:
        输出文件路径

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 文件格式不支持
        Exception: 文档解析或输出失败
    """
    SKILL_DIR = Path(__file__).parent.parent

    # 1. 检查文件
    if not os.path.exists(file_path):
        raise FileNotFoundError(f'文件不存在：{file_path}')

    # 2. 解析文档
    print(f'📄 分析文件：{os.path.basename(file_path)}')
    print(f'📋 章节模板：{section_template}')

    try:
        parser = DocumentParser()
        document = parser.parse(file_path, section_template=section_template)
    except Exception as e:
        raise Exception(f'文档解析失败：{e}')

    print(f'   文本：{document.line_count} 行')
    print(f'   章节：{document.section_count} 个')
    print(f'   表格：{document.table_count} 个')

    # 3. 加载白名单
    print('📚 加载白名单（官方 + 用户）...')
    whitelist = load_whitelist()

    manager = UserWhitelistManager()
    stats = manager.get_stats()
    print(f'   官方：{stats["official_tasks"]} 个任务')
    print(f'   用户：{stats["user_tasks"]} 个任务（学习成果）')

    # 4. 从文档提取任务
    print('🔍 从文档提取任务...')
    pdf_tasks_raw = extract_tasks_from_document(document)

    task_count = sum(len(items) for items in pdf_tasks_raw.values())
    print(f'   提取到 {task_count} 个任务')

    # 5. 智能融合
    print('🔄 智能融合（白名单标准化 + 文档来源）...')
    tasks, new_tasks = smart_merge_tasks(whitelist, pdf_tasks_raw)

    print(f'   ✅ 匹配白名单：{len(tasks) - len(new_tasks)} 个任务')
    print(f'   🆕 新学习任务：{len(new_tasks)} 个任务')

    # 6. 内容质量检查
    print('🔍 内容质量检查...')
    quality_issues = _check_content_quality(tasks)
    if quality_issues:
        print(f'   ⚠️ 发现 {len(quality_issues)} 个问题：')
        for issue in quality_issues[:5]:
            print(f'   - {issue}')
        if len(quality_issues) > 5:
            print(f'   ... 还有 {len(quality_issues) - 5} 个问题')
    else:
        print('   ✅ 无质量问题')

    # 7. 大模块拆分
    tasks = _split_large_modules(tasks)

    # 8. 按模块分组排序
    tasks = _sort_tasks_by_module(tasks)

    # 9. 意图过滤（新增）
    if intent_info:
        intent_parser = IntentParser()
        if intent_parser.has_filters(intent_info):
            print()
            print('🔽 应用意图过滤...')
            tasks = _apply_intent_filters(tasks, intent_info)

            if not tasks:
                print('⚠️ 过滤后没有任务，请检查过滤条件')
                print('提示：可以尝试不加引号参数，生成完整任务分解')
                sys.exit(0)

    # 10. 生成任务 ID 和依赖
    task_id = 1
    module_last_task = {}

    for task in tasks:
        task["任务 ID"] = f"T{task_id:03d}"
        module = task["任务模块"]

        if module in module_last_task:
            task["依赖"] = module_last_task[module]
        else:
            task["依赖"] = "无"

        task["可验收标准"] = get_acceptance_criteria(
            'REST_API' if '接口' in task["任务内容"] else 'FEATURE',
            task["任务内容"]
        )

        module_last_task[module] = task["任务 ID"]
        task_id += 1

    # 11. 输出 Excel
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_name = Path(file_path).stem
    output_path = os.path.join(output_dir, f'WBS_{file_name}_{timestamp}.xlsx')

    try:
        export_to_excel(tasks, output_path)
    except Exception as e:
        raise Exception(f'Excel 输出失败：{e}')

    # 12. 清理旧文件
    cleanup_old_files(output_dir, keep_count=10)

    # 13. 学习新任务
    if new_tasks and auto_learn:
        learn_new_tasks(new_tasks, require_confirm)

    # 14. 输出统计
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


def main():
    """CLI 入口主函数"""
    parser = argparse.ArgumentParser(
        description='WBS 任务分解器 v3.2',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 默认模式
  python3 src/wbs_cli.py --file 技术方案.pdf

  # 自然语言模式
  python3 src/wbs_cli.py --file 技术方案.pdf --intent "按周分解，重点标出接口任务"

  # 指定输出目录
  python3 src/wbs_cli.py --file 技术方案.pdf --output ./my-output

  # 禁用自动学习
  python3 src/wbs_cli.py --file 技术方案.pdf --no-learn

支持的格式：PDF、DOCX、Markdown (.md)
        """,
    )

    parser.add_argument('--file', required=True, help='文档文件路径')
    parser.add_argument('--intent', default=None, help='自然语言需求描述')
    parser.add_argument('--output', default=None, help='输出目录')
    parser.add_argument('--no-learn', action='store_true', help='禁用自动学习')

    args = parser.parse_args()

    # ========== 步骤 1：环境检查 ==========
    print('🔍 检查环境...')
    checker = EnvChecker()
    ok, msg = checker.check()
    if not ok:
        print(f'❌ 环境检查失败：{msg}')
        sys.exit(1)
    print(f'✅ {msg}')

    # ========== 步骤 2：意图解析 ==========
    section_template = 'numeric'
    intent_info = {}

    if args.intent:
        print(f'💬 解析意图：{args.intent}')
        intent_parser = IntentParser()
        intent_info = intent_parser.parse(args.intent)
        section_template = intent_info.get('section_template', 'numeric')

        if intent_parser.has_filters(intent_info):
            print('📌 检测到过滤条件，将在生成后进行过滤')
    else:
        print('📌 默认模式：生成完整任务分解')

    # ========== 步骤 3：调用核心引擎 ==========
    output_dir = args.output if args.output else _get_output_dir()
    print(f'📁 输出目录：{output_dir}')
    print()

    try:
        output_path = generate_wbs_with_intent(
            file_path=args.file,
            output_dir=output_dir,
            section_template=section_template,
            auto_learn=not args.no_learn,
            require_confirm=not args.no_learn,
            intent_info=intent_info if args.intent else None,
        )
    except FileNotFoundError:
        print(f'❌ 文件不存在：{args.file}')
        sys.exit(2)
    except ValueError as e:
        print(f'❌ 文件格式不支持：{e}')
        sys.exit(2)
    except Exception as e:
        print(f'❌ 处理失败：{e}')
        sys.exit(3)


if __name__ == '__main__':
    main()
