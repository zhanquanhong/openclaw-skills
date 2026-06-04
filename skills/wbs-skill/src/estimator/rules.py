"""内容特征评分规则

基于任务内容的实体/操作/特殊逻辑检测，计算工作量评分。

职责：
1. 检测任务内容中的实体/资源（表、接口、页面等）
2. 检测特殊逻辑（事务、分布式、批量、第三方集成等）
3. 判断新开发/迭代系数
4. 无特征匹配时回退到 task_type 兜底基线
"""

import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─── 实体/资源计分规则 ───────────────────────────────
# 每条规则: (匹配函数, 得分, 名称)
# 匹配函数接收 content(str) 返回 True/False

_RULES_ENTITY: List[Tuple] = []


def _rule(pattern_or_func, score: float, name: str) -> Tuple:
    """构造计分规则"""
    if isinstance(pattern_or_func, str):
        pattern = re.compile(pattern_or_func)
        return (lambda c: bool(pattern.search(c)), score, name)
    return (pattern_or_func, score, name)


def _has_keyword(content: str, *keywords: str) -> bool:
    """检测内容是否包含任一关键词（含中文边界）"""
    content_lower = content.lower()
    for kw in keywords:
        if kw in content_lower:
            return True
    return False


def _contains_table_as_entity(content: str) -> bool:
    """检测内容中'表'字是否表示数据库表概念

    避免将"列表"等复合词中的"表"误识别为数据库表。
    """
    for i, c in enumerate(content):
        if c == '表':
            prev = content[i - 1] if i > 0 else None
            # 排除常见的非表概念复合词
            if prev in ('列', '图', '报', '代', '发', '外'):
                continue
            # '表格' → 不是数据库表
            next_c = content[i + 1] if i + 1 < len(content) else None
            if prev == '表' and next_c == '格':
                continue
            # 表字出现在开头或者前一个字是实体名 → 可能为数据库表
            return True
    return False


def _is_table_task(content: str) -> bool:
    """检测是否为表设计/建表相关"""
    return _contains_table_as_entity(content) and not _has_keyword(content, '多表', '批量表', '全部表')


def _is_multi_table_task(content: str) -> bool:
    """检测是否为多表设计"""
    return _has_keyword(content, '多表', '多张表', '复数表')


# 接口检测
def _is_complex_interface(content: str) -> bool:
    """标准接口：新增/创建 + 接口/API"""
    return (_has_keyword(content, '新增', '创建', '新建')
            and _has_keyword(content, '接口', 'api'))


def _is_simple_interface(content: str) -> bool:
    """简单接口：查询/列表/删除/详情 + 接口/API"""
    return (_has_keyword(content, '查询', '列表', '删除', '详情', '导出', '查看')
            and _has_keyword(content, '接口', 'api'))


# ─── 注册实体计分规则 ──────────────────────────────────
# 优先级：先匹到的先计分，同一组互斥（例如标准接口和简单接口不同时匹配）

_ENTITY_RULES: List[Tuple] = [
    _rule(_is_multi_table_task, 1.0, '多表设计'),
    _rule(_is_table_task, 0.5, '单表设计'),
    _rule(_is_complex_interface, 2.0, '标准接口'),
    # 简单接口与标准接口互斥——如果已匹配标准接口，不再匹配简单接口
    _rule(lambda c: _is_simple_interface(c) and not _is_complex_interface(c), 1.0, '简单接口'),
    _rule(lambda c: _has_keyword(c, '页面', '页面功能', '界面'), 2.0, '页面/UI'),
    _rule(lambda c: _has_keyword(c, '配置', '环境变量', '参数设置'), 0.5, '配置/设置'),
    _rule(lambda c: _has_keyword(c, '数据迁移', '数据清洗', '历史数据'), 2.5, '数据迁移'),
    _rule(lambda c: _has_keyword(c, '定时', '调度', 'xxl-job', 'cron', '定时任务'), 1.5, '定时任务'),
    _rule(lambda c: _has_keyword(c, 'redis', 'mq', 'kafka', '消息队列', '缓存'), 1.5, '中间件/缓存'),
    _rule(lambda c: _has_keyword(c, '工作流', '审批', '审核流程'), 2.0, '工作流/审批'),
]

# ─── 特殊逻辑加分规则 ──────────────────────────────────

_SPECIAL_RULES: List[Tuple] = [
    _rule(lambda c: _has_keyword(c, '分布式', '高并发'), 1.5, '分布式/高并发'),
    _rule(lambda c: _has_keyword(c, '事务', '补偿', '一致性'), 1.0, '事务/补偿'),
    _rule(lambda c: _has_keyword(c, '集成', '对接', '第三方'), 1.5, '第三方集成'),
    _rule(lambda c: _has_keyword(c, '批量'), 1.0, '批量操作'),
    _rule(lambda c: _has_keyword(c, '权限', '安全', '鉴权'), 0.5, '权限/安全'),
]

# ─── 兜底基线（无特征匹配时回退）────────────────────────

_FALLBACK_BASELINE: Dict[str, float] = {
    '接口任务': 1.5,
    '数据库任务': 0.5,
    '前端任务': 2.0,
    '配置任务': 0.3,
    '中间件任务': 1.5,
    '运维任务': 1.0,
    '架构设计': 2.0,
    '数据迁移': 2.5,
    '权限/安全': 1.5,
    '功能任务': 2.0,
}

# ─── 迭代判断关键词（内部使用）─────────────────────────

_ITERATION_KEYWORDS = {
    1.0: ('新增', '新建', '创建', 'create', '设计'),
    0.5: ('修改', '优化', '改造', '重构', '升级', '改进'),
    0.3: ('删除', '废弃', '下线', '移除'),
}

_DEFAULT_ITERATION_FACTOR = 1.0  # 兜底保守


def _get_iteration_factor(content: str) -> float:
    """判断新开发/迭代系数

    Args:
        content: 任务内容

    Returns:
        迭代系数（1.0=新开发, 0.5=迭代, 0.3=清理）
    """
    content_lower = content.lower()
    for factor, keywords in sorted(_ITERATION_KEYWORDS.items(), reverse=True):
        for kw in keywords:
            if kw in content_lower:
                return factor
    return _DEFAULT_ITERATION_FACTOR


def score_content(content: str) -> Dict:
    """对任务内容进行特征评分

    Args:
        content: 任务内容字符串

    Returns:
        {
            'entity_score': float,      # 实体计分
            'special_bonus': float,     # 特殊逻辑加分
            'matched_entities': [str],  # 匹配的实体特征名
            'matched_specials': [str],  # 匹配的特殊特征名
            'iteration_factor': float,  # 迭代系数
            'raw_score': float,         # 原始分（计分+加分）
        }
    """
    matched_entities = []
    entity_score = 0.0

    for matcher, score, name in _ENTITY_RULES:
        if matcher(content):
            # 避免重复计分：同特征多次匹配只计一次
            if name not in matched_entities:
                matched_entities.append(name)
                entity_score += score

    matched_specials = []
    special_bonus = 0.0

    for matcher, score, name in _SPECIAL_RULES:
        if matcher(content):
            if name not in matched_specials:
                matched_specials.append(name)
                special_bonus += score

    iteration_factor = _get_iteration_factor(content)
    raw_score = entity_score + special_bonus

    return {
        'entity_score': entity_score,
        'special_bonus': special_bonus,
        'matched_entities': matched_entities,
        'matched_specials': matched_specials,
        'iteration_factor': iteration_factor,
        'raw_score': raw_score,
    }


def get_fallback_baseline(task_type: str) -> float:
    """获取兜底基线（内容无特征匹配时）

    Args:
        task_type: 任务类型

    Returns:
        兜底人天
    """
    return _FALLBACK_BASELINE.get(task_type, 1.5)


def calculate_recommended_days(
    content: str,
    task_type: str,
    calibration_factor: float = 1.0,
) -> Tuple[float, float]:
    """计算推荐人天数和迭代系数

    Args:
        content: 任务内容
        task_type: 任务类型（兜底用）
        calibration_factor: 校准系数

    Returns:
        (推荐人天, 迭代系数)
    """
    scores = score_content(content)

    if scores['raw_score'] > 0:
        base = scores['raw_score']
    else:
        # 无特征匹配，回退到兜底基线
        base = get_fallback_baseline(task_type)

    iteration_factor = scores['iteration_factor']
    recommended = round(max(0.3, base * iteration_factor * calibration_factor), 1)

    return recommended, iteration_factor
