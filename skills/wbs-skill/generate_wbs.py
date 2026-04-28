#!/usr/bin/env python3
"""WBS 一键生成器 - v3.0（通用化 + 智能化）

支持多种文档格式（PDF/DOCX/Markdown）和多种章节编号规则。

使用方式：
    # 默认模式（数字编号模板）
    python3 generate_wbs.py 技术方案.pdf

    # 指定章节模板
    python3 generate_wbs.py 技术方案.pdf --section-template chinese

    # 指定输出目录
    python3 generate_wbs.py 技术方案.pdf -o ./output

    # 禁用自动学习
    python3 generate_wbs.py 技术方案.pdf --no-learn
"""

import sys
import os
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 确保能导入 src 模块
SKILL_DIR = Path(__file__).parent.absolute()
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from src.document_parser import DocumentParser, ParsedDocument
from src.table_extractor import TableExtractor, InterfaceTable
from src.whitelist_manager import UserWhitelistManager, load_whitelist
from src.output import export_to_excel
from src.templates import get_acceptance_criteria
from src.decomposer_v3 import cleanup_old_files

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def _split_large_modules(tasks: List[Dict], max_size: int = 10) -> List[Dict]:
    """拆分大模块（>max_size 个任务）

    策略：
    1. 按任务内容关键词拆分
    2. 保持模块层级结构

    Args:
        tasks: 任务列表
        max_size: 最大模块大小

    Returns:
        拆分后的任务列表
    """
    # 按模块分组
    module_groups: Dict[str, List[Dict]] = {}
    for task in tasks:
        module = task.get('任务模块', '')
        if module not in module_groups:
            module_groups[module] = []
        module_groups[module].append(task)

    # 拆分大模块
    for module, group in module_groups.items():
        if len(group) <= max_size:
            continue

        # 按关键词拆分
        sub_modules: Dict[str, List[Dict]] = {}
        for task in group:
            content = task.get('任务内容', '')
            sub_module = _infer_sub_module(module, content)
            if sub_module not in sub_modules:
                sub_modules[sub_module] = []
            sub_modules[sub_module].append(task)

        # 更新任务模块
        for task in group:
            content = task.get('任务内容', '')
            sub_module = _infer_sub_module(module, content)
            task['任务模块'] = sub_module

    return tasks


def _infer_sub_module(module: str, content: str) -> str:
    """推断子模块名

    根据任务内容推断子模块。

    Args:
        module: 父模块名
        content: 任务内容

    Returns:
        子模块名
    """
    # 关键词映射
    keyword_map = {
        '技能': '技能中心',
        '接口': '接口开发',
        '查询': '查询功能',
        '更新': '更新功能',
        '删除': '删除功能',
        '配置': '配置管理',
        '渠道': '渠道配置',
        '模型': '模型管理',
        '对话': '对话管理',
        '会话': '会话管理',
        '推送': '推送功能',
        '通知': '通知功能',
        'MClaw': 'MClaw 模块',
        '容器': '容器管理',
        'K8s': 'K8s 部署',
    }

    for keyword, sub_module in keyword_map.items():
        if keyword in content:
            return f"{module} - {sub_module}"

    return module


def _sort_tasks_by_module(tasks: List[Dict]) -> List[Dict]:
    """按模块分组排序任务

    确保同模块的任务连续排列，便于依赖推断。

    Args:
        tasks: 任务列表

    Returns:
        排序后的任务列表
    """
    # 按模块分组
    module_groups: Dict[str, List[Dict]] = {}
    for task in tasks:
        module = task.get('任务模块', '')
        if module not in module_groups:
            module_groups[module] = []
        module_groups[module].append(task)

    # 按模块名排序
    sorted_modules = sorted(module_groups.keys())

    # 合并结果
    result = []
    for module in sorted_modules:
        result.extend(module_groups[module])

    return result


def _check_content_quality(tasks: List[Dict]) -> List[str]:
    """检查任务内容质量

    检查项：
    1. 内容截断（<20 字符）
    2. 来源字段含噪声
    3. 模块分组过大（>10 个任务）

    Args:
        tasks: 任务列表

    Returns:
        问题列表
    """
    issues = []

    # 检查 1：内容截断
    for task in tasks:
        content = task.get('任务内容', '')
        if len(content) < 20:
            issues.append(f"内容过短（{len(content)} 字符）：{content}")

    # 检查 2：来源字段噪声
    for task in tasks:
        source = task.get('任务来源', '')
        if 'TODO' in source or 'todo' in source:
            issues.append(f"来源含噪声：{source}")

    # 检查 3：模块分组过大
    module_count = {}
    for task in tasks:
        module = task.get('任务模块', '')
        module_count[module] = module_count.get(module, 0) + 1

    for module, count in module_count.items():
        if count > 10:
            issues.append(f"模块过大（{count} 个任务）：{module}")

    return issues


def _infer_dependency(
    current_task: Dict,
    module_last_task: Dict[str, str],
    all_tasks: List[Dict],
    current_index: int
) -> str:
    """智能推断任务依赖

    策略：
    1. 同模块内，按顺序依赖上一个任务
    2. 跨模块不自动依赖（避免错误依赖链）
    3. 特殊语义依赖：根据任务内容关键词推断
    4. 排除明显无关的依赖

    Args:
        current_task: 当前任务
        module_last_task: 每个模块的最后一个任务 ID
        all_tasks: 所有任务列表
        current_index: 当前任务索引

    Returns:
        依赖任务 ID 或 "无"
    """
    module = current_task.get("任务模块", "")
    content = current_task.get("任务内容", "")

    # 策略 1：同模块内依赖上一个任务
    if module in module_last_task:
        return module_last_task[module]

    # 策略 2：跨模块不自动依赖（避免错误依赖链）
    return "无"


def generate_wbs(
    file_path: str,
    output_dir: str = None,
    section_template: str = "numeric",
    auto_learn: bool = True,
    require_confirm: bool = True
) -> str:
    """一键生成 WBS 任务分解

    工作流程：
    1. 解析文档（PDF/DOCX/Markdown）
    2. 从表格和文本中提取任务
    3. 白名单匹配（标准化任务命名）
    4. 智能融合：任务内容←白名单，任务来源←文档
    5. 生成 WBS
    6. 新任务自动学习（可选确认）

    Args:
        file_path: 文档文件路径
        output_dir: 输出目录（默认：test-data/output）
        section_template: 章节识别模板（numeric/chinese/markdown/mixed）
        auto_learn: 是否自动学习新任务
        require_confirm: 学习前是否需要确认

    Returns:
        输出文件路径

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 文件格式不支持
    """
    # 1. 检查文件
    if not os.path.exists(file_path):
        print(f'❌ 文件不存在：{file_path}')
        sys.exit(1)

    # 2. 设置输出目录
    if not output_dir:
        workspace_output = SKILL_DIR.parent.parent / 'test-data' / 'output'
        if workspace_output.exists():
            output_dir = str(workspace_output)
        else:
            output_dir = str(SKILL_DIR / 'output')
    os.makedirs(output_dir, exist_ok=True)

    # 3. 解析文档
    print(f'📄 分析文件：{os.path.basename(file_path)}')
    print(f'📋 章节模板：{section_template}')

    try:
        parser = DocumentParser()
        document = parser.parse(file_path, section_template=section_template)
    except Exception as e:
        print(f'❌ 文档解析失败：{e}')
        sys.exit(1)

    print(f'   文本：{document.line_count} 行')
    print(f'   章节：{document.section_count} 个')
    print(f'   表格：{document.table_count} 个')

    # 4. 加载白名单
    print('📚 加载白名单（官方 + 用户）...')
    whitelist = load_whitelist()

    manager = UserWhitelistManager()
    stats = manager.get_stats()
    print(f'   官方：{stats["official_tasks"]} 个任务')
    print(f'   用户：{stats["user_tasks"]} 个任务（学习成果）')

    # 5. 从文档提取任务（表格 + 文本）
    print('🔍 从文档提取任务...')
    pdf_tasks_raw = extract_tasks_from_document(document)

    task_count = sum(len(items) for items in pdf_tasks_raw.values())
    print(f'   提取到 {task_count} 个任务')

    # 6. 智能融合：白名单 + 文档提取
    print('🔄 智能融合（白名单标准化 + 文档来源）...')
    tasks, new_tasks = smart_merge_tasks(whitelist, pdf_tasks_raw)

    print(f'   ✅ 匹配白名单：{len(tasks) - len(new_tasks)} 个任务')
    print(f'   🆕 新学习任务：{len(new_tasks)} 个任务')

    # 6.5 内容质量检查
    print('🔍 内容质量检查...')
    quality_issues = _check_content_quality(tasks)
    if quality_issues:
        print(f'   ⚠️ 发现 {len(quality_issues)} 个问题：')
        for issue in quality_issues[:5]:
            print(f'   - {issue}')
        if len(quality_issues) > 5:
            print(f'   ... 还有 {len(quality_issues) - 5} 个问题')
    else:
        print(f'   ✅ 无质量问题')

    # 6.6 大模块拆分（>10 个任务自动拆分）
    tasks = _split_large_modules(tasks)

    # 6.7 按模块分组排序（确保同模块任务连续）
    tasks = _sort_tasks_by_module(tasks)

    # 7. 生成任务 ID 和依赖
    task_id = 1
    module_last_task = {}

    for task in tasks:
        task["任务 ID"] = f"T{task_id:03d}"
        module = task["任务模块"]

        # 设置依赖（同模块内依赖上一个任务，跨模块不依赖）
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

    # 8. 输出 Excel
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_name = Path(file_path).stem
    output_path = os.path.join(output_dir, f'WBS_{file_name}_{timestamp}.xlsx')

    export_to_excel(tasks, output_path)

    # 9. 清理旧文件
    cleanup_old_files(output_dir, keep_count=10)

    # 10. 学习新任务
    if new_tasks and auto_learn:
        learn_new_tasks(new_tasks, require_confirm)

    # 11. 输出统计
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


def extract_tasks_from_document(document: ParsedDocument) -> Dict[str, List[Dict]]:
    """从解析后的文档中提取任务

    策略：
    1. 从接口表格提取任务
    2. 从文本中按关键词提取任务

    Args:
        document: 解析后的文档

    Returns:
        {模块名: [{任务内容, 任务来源, 任务类型}]}
    """
    tasks_by_module: Dict[str, List[Dict]] = {}

    # 策略 1：从接口表格提取
    interface_tables = TableExtractor().extract_interface_tables(document.tables)

    for table in interface_tables:
        module_name = table.title or f"表格{table.page}"
        current_section = _find_section_by_page(table.page, document.sections)
        if current_section:
            module_name = current_section.title

        for row in table.rows:
            task_info = _parse_interface_row(table.header, row)
            if task_info:
                task_info['任务来源'] = _clean_source_field(f"{module_name} (表{table.page})")
                _add_task(tasks_by_module, module_name, task_info)

    # 策略 2：从文本按关键词提取
    keyword_tasks = _extract_tasks_by_keywords(document)
    for module_name, task_list in keyword_tasks.items():
        for task_info in task_list:
            _add_task(tasks_by_module, module_name, task_info)

    return tasks_by_module


def _find_section_by_page(page_num: int, sections: List) -> Optional:
    """根据页码查找章节（简化：返回第一个匹配的）"""
    from src.section_engine import Section
    if sections:
        return sections[0]
    return None


def _parse_interface_row(header: List[str], row: List[str]) -> Optional[Dict]:
    """从接口表格行解析任务信息

    Args:
        header: 表头
        row: 数据行

    Returns:
        {任务内容, 任务类型} 或 None
    """
    if not row or not any(cell.strip() for cell in row):
        return None

    # 尝试从常见列名提取接口名
    header_lower = [h.lower() for h in header]

    # 优先使用「接口名称」「接口名」「功能」列
    for col_name in ['接口名称', '接口名', '功能', '功能名称', '接口']:
        if col_name in header_lower:
            idx = header_lower.index(col_name)
            if idx < len(row) and row[idx].strip():
                return {
                    '任务内容': row[idx].strip(),
                    '任务类型': '普通任务'
                }

    # 兜底：使用第一列
    if row[0].strip():
        return {
            '任务内容': row[0].strip(),
            '任务_type': '普通任务'
        }

    return None


def _extract_tasks_by_keywords(document: ParsedDocument) -> Dict[str, List[Dict]]:
    """从文本按关键词提取任务（兜底策略）

    分层匹配策略：
    1. 步骤标记：第N步：新增/更新...
    2. 字母编号：a./b./c. + 新增/更新...
    3. 任务标记：【新增】/【更新】
    4. 动词开头：新增/更新/提供/开发/实现/添加/修改/删除/优化...
    5. 模块名开头：Mclaw/后台/前端 + 新增/更新/提供...
    6. 包含关键词 + 技术关键词：新增/更新 + 接口/功能/模块/表/数据...

    排除规则：
    - 包含「•」「○」等列表符号
    - 包含「业务目标」「实现逻辑」「设计思路」
    - 包含「SC->>DB」「FE-->>U」等时序图标记
    - 包含「TODO」「一期已实现」「不需要新开发」

    Args:
        document: 解析后的文档

    Returns:
        {模块名: [任务列表]}
    """
    import re
    from src.section_engine import SectionInferEngine

    # 排除词：包含这些词的行通常不是任务
    exclude_keywords = [
        '•', '○', '●', '■', '□',  # 列表符号
        '业务目标', '实现逻辑', '设计思路', '背景', '概述',
        '注意事项', '说明', '备注', '提示', '简介',
        'SC->>DB', 'FE-->>U', 'DB-->>SC',  # 时序图标记
        'TODO', '一期已实现', '不需要新开发', '先不用',  # 非任务标记
        '展⽰',  # 常见噪音字（PDF 乱码）
    ]

    # 任务行模式（至少匹配一个）
    task_patterns = [
        # 1. 步骤标记（第N步）
        r'第\d+步[：:].*(?:新增|更新|设计并实现|开发|提供|实现)',

        # 2. 字母编号（a. b. c. ...）
        r'^[a-z]\.[\s ].*(?:新增|更新|设计并实现|开发|提供|实现)',

        # 3. 任务标记（【新增】/【更新】）
        r'【新增】|【更新】',

        # 4. 动词开头 + 技术关键词
        r'^(?:新增|更新|提供|开发|实现|添加|修改|删除|优化|完善|支持|重构|迁移|部署|配置|集成|对接).*(?:接口|功能|模块|表|字段|索引|缓存|队列|定时任务|数据|状态|统计|列表|查询|删除|安装|搜索|开关|同步|关系)',

        # 5. 模块名开头 + 动词
        r'^(?:Mclaw|后台|前端|算法|技能中心|渠道|对话|模型|AI|K8s|sidecar).*(?:新增|更新|提供|开发|实现|添加|修改|删除|优化|支持|配合)',

        # 6. 包含"新增/更新" + 技术关键词
        r'(?:新增|更新).*(?:接口|功能|模块|表|字段|索引|缓存|队列|定时任务|数据|状态|统计|列表|查询|删除|安装|搜索|开关|同步|关系)',
    ]

    tasks_by_module: Dict[str, List[Dict]] = {}

    # 复用引擎实例
    engine = SectionInferEngine.__new__(SectionInferEngine)
    engine.config = {'default_template': 'numeric', 'templates': {}}
    engine.template_name = 'numeric'
    engine.template = {}

    for line_num, line in enumerate(document.lines, 1):
        stripped = line.strip()
        if not stripped or len(stripped) < 8:
            continue

        # 排除规则
        if any(ex in stripped for ex in exclude_keywords):
            continue

        # 任务行匹配
        is_task = any(re.search(pattern, stripped) for pattern in task_patterns)
        if not is_task:
            continue

        # 查找所属章节
        current_section = engine.find_section_by_line(line_num, document.sections)

        module_name = current_section.title if current_section else '未分类'
        source = f"{current_section.title if current_section else ''} 第{line_num}行"

        # 清理来源字段中的噪声（TODO 等）
        source = _clean_source_field(source)
        module_name = _clean_source_field(module_name)

        # 识别任务类型（增强版）
        task_type = '普通任务'

        # 新增接口判断
        if (
            '【新增】' in stripped
            or ('新增' in stripped and '接口' in stripped)
            or re.search(r'提供.*后端接口', stripped)
            or re.search(r'后台.*查询.*接口', stripped)
            or re.search(r'新增.*接口.*POST', stripped)
            or re.search(r'新增.*接口.*GET', stripped)
            or re.search(r'新增.*接口.*PUT', stripped)
            or re.search(r'新增.*接口.*DELETE', stripped)
            or re.search(r'POST.*api.*接口', stripped)
        ):
            task_type = '新增接口'
        # 更新接口判断
        elif (
            '【更新】' in stripped
            or ('更新' in stripped and '接口' in stripped)
            or re.search(r'更新.*接口', stripped)
        ):
            task_type = '更新接口'

        task_info = {
            '任务内容': stripped,
            '任务来源': source,
            '任务类型': task_type
        }

        _add_task(tasks_by_module, module_name, task_info)

    return tasks_by_module


def _add_task(
    tasks_by_module: Dict[str, List[Dict]],
    module_name: str,
    task_info: Dict
) -> None:
    """添加任务到模块（全局去重）

    去重策略：
    1. 完全相同 → 保留一个
    2. 包含关系（如"技能删除接口"和"第1步：新增技能删除接口"）→ 保留长的
    3. 跨模块去重：相同任务只保留一份

    Args:
        tasks_by_module: 任务字典
        module_name: 模块名
        task_info: 任务信息
    """
    if module_name not in tasks_by_module:
        tasks_by_module[module_name] = []

    new_content = task_info.get('任务内容', '').strip()
    if not new_content:
        return

    # 全局去重检查（所有模块）
    for mod_name, mod_tasks in tasks_by_module.items():
        for existing in mod_tasks:
            existing_content = existing.get('任务内容', '').strip()

            # 完全相同
            if new_content == existing_content:
                return

            # 包含关系：保留长的
            if new_content in existing_content or existing_content in new_content:
                if len(new_content) > len(existing_content):
                    mod_tasks.remove(existing)
                    tasks_by_module[module_name].append(task_info)
                return

    # 通过检查，添加任务
    tasks_by_module[module_name].append(task_info)


def _clean_source_field(source: str) -> str:
    """清理来源字段中的噪声

    移除 TODO、一期已实现等非任务标记。

    Args:
        source: 原始来源字段

    Returns:
        清理后的来源字段
    """
    # 移除 TODO 标记
    source = source.replace('TODO', '').replace('todo', '').strip()
    # 移除多余逗号
    source = re.sub(r',+', ',', source)
    source = re.sub(r',\s*$', '', source)
    return source.strip()


def _normalize_content(content: str) -> str:
    """标准化任务内容（用于去重）

    移除控制字符、多余空格，统一格式。
    """
    import re
    # 移除控制字符（\x00-\x1f，\x7f）
    content = re.sub(r'[\x00-\x1f\x7f]', '', content)
    # 移除多余空格
    content = re.sub(r'\s+', ' ', content).strip()
    return content


def smart_merge_tasks(
    whitelist: Dict[str, List],
    pdf_tasks_raw: Dict[str, List[Dict]]
) -> Tuple[List[Dict], List[Dict]]:
    """智能融合：白名单标准化 + 文档来源信息

    Args:
        whitelist: 白名单（官方 + 用户）
        pdf_tasks_raw: 文档提取的原始任务

    Returns:
        (融合后的任务列表，新任务列表)
    """
    final_tasks = []
    new_tasks = []
    seen_normalized = set()  # 用于去重（标准化后的内容）

    # 构建白名单查找表
    whitelist_lookup = {}
    for module, items in whitelist.items():
        for item in items:
            if isinstance(item, dict):
                content = item.get('任务内容', '')
            else:
                content = str(item)

            # 使用标准化后的内容作为 key
            normalized = _normalize_content(content)
            whitelist_lookup[normalized] = {
                '模块': module,
                '标准化名': content,
                '标准化内容': normalized
            }

    # 处理文档提取的任务
    for module, items in pdf_tasks_raw.items():
        for pdf_task in items:
            task_content = pdf_task.get('任务内容', '').strip()
            task_source = pdf_task.get('任务来源', '')
            task_type = pdf_task.get('任务类型', '普通任务')

            if not task_content:
                continue

            # 标准化任务内容
            normalized_content = _normalize_content(task_content)

            # 去重：检查标准化后的内容是否已存在
            if normalized_content in seen_normalized:
                continue

            # 尝试匹配白名单
            matched = None
            for wl_normalized, wl_info in whitelist_lookup.items():
                if wl_normalized in normalized_content or normalized_content in wl_normalized:
                    matched = wl_info
                    break

            if matched:
                standardized_content = matched['标准化名']
                standardized_normalized = matched['标准化内容']

                # 去重：相同标准化内容只保留一份
                if standardized_normalized in seen_normalized:
                    continue
                seen_normalized.add(standardized_normalized)

                final_tasks.append({
                    '任务模块': matched['模块'],
                    '任务内容': standardized_content,
                    '任务来源': task_source,
                    '任务类型': task_type
                })
            else:
                # 去重：检查是否已存在相似内容
                is_duplicate = False
                for seen in seen_normalized:
                    # 包含关系
                    if normalized_content in seen or seen in normalized_content:
                        is_duplicate = True
                        break
                    # 相似度检查（前 20 个字符相同）
                    if len(normalized_content) > 20 and len(seen) > 20:
                        if normalized_content[:20] == seen[:20]:
                            is_duplicate = True
                            break

                if is_duplicate:
                    continue

                seen_normalized.add(normalized_content)

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


def learn_new_tasks(new_tasks: List[Dict], require_confirm: bool = True) -> None:
    """学习新任务并保存到用户白名单

    Args:
        new_tasks: 新任务列表
        require_confirm: 是否需要确认
    """
    if not new_tasks:
        return

    print()
    print('📚 发现新任务，是否学习？')
    for i, task in enumerate(new_tasks[:5], 1):
        print(f'   {i}. {task["任务内容"]}（{task["任务来源"]}）')
    if len(new_tasks) > 5:
        print(f'   ... 还有 {len(new_tasks) - 5} 个任务')

    if require_confirm:
        try:
            confirm = input('\n是否保存到用户白名单？[Y/n]: ').strip().lower()
            if confirm == 'n':
                print('⏭️ 跳过学习')
                return
        except (EOFError, KeyboardInterrupt):
            print('\n⏭️ 跳过学习')
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


def export_whitelist(output_path: str, include_official: bool = False) -> None:
    """导出用户白名单"""
    manager = UserWhitelistManager()
    manager.export(output_path, include_official)


def import_whitelist(input_path: str, merge: bool = True) -> None:
    """导入用户白名单"""
    manager = UserWhitelistManager()
    manager.import_whitelist(input_path, merge)


def show_stats() -> None:
    """显示统计信息"""
    manager = UserWhitelistManager()
    manager.print_stats()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='WBS 一键生成器 v3.0（通用化 + 智能化）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 生成 WBS（默认数字编号模板）
  python3 generate_wbs.py 技术方案.pdf

  # 指定章节模板
  python3 generate_wbs.py 技术方案.pdf --section-template chinese

  # 指定输出目录
  python3 generate_wbs.py 技术方案.pdf -o ./output

  # 禁用自动学习
  python3 generate_wbs.py 技术方案.pdf --no-learn

  # 导出用户白名单
  python3 generate_wbs.py --export user_whitelist.yaml

  # 导入用户白名单
  python3 generate_wbs.py --import team_whitelist.yaml

  # 显示统计信息
  python3 generate_wbs.py --stats

章节模板：
  numeric    数字编号（1.2.1）        默认
  chinese    中文编号（一、(一)、1.）
  markdown   Markdown 标题（#、##）
  mixed      混合编号
        """
    )

    parser.add_argument('pdf', nargs='?', help='文档文件路径（PDF/DOCX/Markdown）')
    parser.add_argument('-o', '--output', help='输出目录')
    parser.add_argument('--section-template', default='numeric',
                        help='章节识别模板：numeric/chinese/markdown/mixed（默认：numeric）')
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
        parser.print_help()
        sys.exit(1)

    generate_wbs(
        args.pdf,
        output_dir=args.output,
        section_template=args.section_template,
        auto_learn=not args.no_learn,
        require_confirm=not args.no_confirm
    )
