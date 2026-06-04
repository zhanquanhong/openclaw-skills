"""工作量估算引擎

整合 rules（特征评分）和 calibrator（校准因子），对 v4 task dict 列表进行估算。

职责：
1. 遍历任务列表，估算每个任务的人天数
2. 向 task dict 追加 推荐人天数 + 估算范围 字段
3. 不修改任何已有字段
"""

import logging
from typing import Dict, List, Tuple

from src.estimator.rules import calculate_recommended_days, score_content, get_fallback_baseline
from src.estimator.calibrator import get_factor, get_precision, get_stats as _calibrator_stats

logger = logging.getLogger(__name__)

# 单人天上限，超过时标记
MAX_DAYS_WARNING = 20


def estimate_tasks(tasks: List[Dict]) -> List[Dict]:
    """对任务列表进行工作量估算

    向每个 task dict 追加：
        '推荐人天数': float
        '估算范围': str (例如 "1.4~2.6")

    Args:
        tasks: v4 任务列表（每项含 任务模块、任务内容、任务类型 等）

    Returns:
        追加了估算字段的任务列表
    """
    if not tasks:
        return tasks

    # 预加载校准因子
    calibration_cache = {}

    for task in tasks:
        content = task.get('任务内容', '') or ''
        task_type = task.get('任务类型', '功能任务')

        # 获取校准因子（带缓存）
        if task_type not in calibration_cache:
            calibration_cache[task_type] = get_factor(task_type)
        calibration_factor = calibration_cache[task_type]

        # 计算推荐人天
        recommended, iteration_factor = calculate_recommended_days(
            content=content,
            task_type=task_type,
            calibration_factor=calibration_factor,
        )

        # 获取记录数用于精度
        # 简化：从 calibration_cache 判断是否有校准数据
        if calibration_factor != 1.0:
            record_count = 3  # 有校准因子的说明有 3+ 记录
        else:
            record_count = 0

        precision = get_precision(record_count)

        # 计算范围
        lower = round(recommended * (1 - precision), 1)
        upper = round(recommended * (1 + precision), 1)
        range_str = f'{lower}~{upper}'

        # 写入 task dict（不修改已有字段）
        task['推荐人天数'] = recommended
        task['估算范围'] = range_str

        # 超过上限警告
        if recommended > MAX_DAYS_WARNING:
            logger.warning(
                f"任务 {task.get('任务 ID', '')} 推荐 {recommended}人天，"
                f"建议拆分: {content[:50]}"
            )
            task['估算范围'] = f'{lower}~{upper} ⚠️建议拆分'

    logger.info(
        f'工作量估算完成: {len(tasks)} 个任务, '
        f'合计 {sum(t.get("推荐人天数", 0) for t in tasks):.1f} 人天'
    )

    return tasks


def get_calibration_stats() -> Dict:
    """获取校准统计（透传 calibrator.get_stats）"""
    return _calibrator_stats()
