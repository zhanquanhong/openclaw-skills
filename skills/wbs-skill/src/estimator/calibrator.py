"""校准系统 - 基于历史实际工时的自我校准

职责：
1. 读取/写入校准记录（JSON）
2. 按 task_type 计算校准因子（median 抗离群）
3. 批量录入实际工时
4. 输出校准统计
"""

import json
import logging
import os
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 校准数据路径
CALIBRATION_DIR = Path.home() / '.wbs-skill'
CALIBRATION_FILE = CALIBRATION_DIR / 'calibration_data.json'
MIN_RECORDS_FOR_CALIBRATION = 3  # 最少记录数才启用校准


def _ensure_dir():
    """确保校准目录存在"""
    CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)


def _load_records() -> List[Dict]:
    """加载校准记录

    Returns:
        记录列表，文件不存在或不合法时返回空列表
    """
    if not CALIBRATION_FILE.exists():
        return []

    try:
        with open(CALIBRATION_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        records = data.get('records', [])
        if not isinstance(records, list):
            logger.warning('校准文件格式异常：records 不是列表')
            return []
        return records
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f'校准文件读取出错: {e}，备份后重建')
        _backup_and_reset()
        return []


def _save_records(records: List[Dict]):
    """保存校准记录

    Args:
        records: 记录列表
    """
    _ensure_dir()
    data = {
        'version': 1,
        'updated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'records': records,
    }
    # 写临时文件再重命名，防止写入中断导致文件损坏
    tmp_path = CALIBRATION_FILE.with_suffix('.tmp')
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp_path.replace(CALIBRATION_FILE)


def _backup_and_reset():
    """备份损坏的校准文件后重建"""
    if CALIBRATION_FILE.exists():
        backup_path = CALIBRATION_FILE.with_suffix('.bak')
        try:
            CALIBRATION_FILE.rename(backup_path)
            logger.info(f'校准文件已备份到: {backup_path}')
        except OSError:
            pass
    _save_records([])


def compute_calibration_factors() -> Dict[str, Dict]:
    """计算每种 task_type 的校准因子

    Returns:
        {
            '接口任务': {
                'factor': 0.92,
                'record_count': 5,
                'ratios': [0.8, 0.9, 1.0, 1.1, ...],
            },
            ...
        }
    """
    records = _load_records()
    if not records:
        return {}

    # 按 task_type 分组
    by_type: Dict[str, List[float]] = {}
    for rec in records:
        task_type = rec.get('task_type', '功能任务')
        predicted = rec.get('predicted_days', 1.0)
        actual = rec.get('actual_days', 1.0)
        if predicted <= 0:
            continue
        ratio = actual / predicted
        if task_type not in by_type:
            by_type[task_type] = []
        by_type[task_type].append(ratio)

    result = {}
    for task_type, ratios in by_type.items():
        record_count = len(ratios)
        if record_count >= MIN_RECORDS_FOR_CALIBRATION:
            factor = round(statistics.median(ratios), 2)
        else:
            factor = 1.0

        result[task_type] = {
            'factor': factor,
            'record_count': record_count,
            'ratios': ratios,
        }

    return result


def get_factor(task_type: str) -> float:
    """获取指定 task_type 的校准因子

    Args:
        task_type: 任务类型

    Returns:
        校准因子（无历史数据时返回 1.0）
    """
    factors = compute_calibration_factors()
    info = factors.get(task_type, {})
    count = info.get('record_count', 0)
    if count >= MIN_RECORDS_FOR_CALIBRATION:
        return info['factor']
    return 1.0


def get_precision(record_count: int) -> float:
    """根据记录数计算精度（用于范围）

    | 记录数 | 精度 |
    |--------|------|
    | 0      | 0.50 |
    | 3~5    | 0.30 |
    | 6~20   | 0.20 |
    | >20    | 0.15 |

    Args:
        record_count: 该类型的校准记录数

    Returns:
        精度值（如 0.50 表示 ±50%）
    """
    if record_count >= 20:
        return 0.15
    elif record_count >= 6:
        return 0.20
    elif record_count >= 3:
        return 0.30
    else:
        return 0.50


def add_calibration_records(records: List[Dict]) -> Tuple[int, int]:
    """批量添加校准记录

    Args:
        records: 校准记录列表，每条需含 task_content 和 actual_days
                 可选含 task_type, predicted_days, module

    Returns:
        (成功数, 跳过数)
    """
    existing = _load_records()
    success = 0
    skipped = 0

    for rec in records:
        content = rec.get('task_content', '').strip()
        actual = rec.get('actual_days')

        if not content or actual is None or not isinstance(actual, (int, float)):
            skipped += 1
            continue

        if actual <= 0:
            skipped += 1
            continue

        # 查找是否已有同内容的记录（防止重复录入）
        is_dup = any(
            r.get('task_content', '') == content and
            r.get('actual_days') == actual
            for r in existing
        )
        if is_dup:
            skipped += 1
            continue

        record = {
            'task_content': content,
            'task_type': rec.get('task_type', '功能任务'),
            'module': rec.get('module', ''),
            'predicted_days': rec.get('predicted_days', 1.0),
            'actual_days': round(float(actual), 1),
            'recorded_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        existing.append(record)
        success += 1

    _save_records(existing)
    return success, skipped


def get_stats() -> Dict:
    """获取校准统计信息

    Returns:
        {
            'total_records': int,
            'by_type': { ... },      # compute_calibration_factors() 的结果
            'last_updated': str,
        }
    """
    records = _load_records()
    factors = compute_calibration_factors()

    stats = {
        'total_records': len(records),
        'by_type': {},
        'last_updated': '',
    }

    for task_type, info in factors.items():
        count = info['record_count']
        factor = info['factor']
        precision = get_precision(count)
        min_ratio = round(min(info['ratios']), 2) if info['ratios'] else 0
        max_ratio = round(max(info['ratios']), 2) if info['ratios'] else 0

        if count >= MIN_RECORDS_FOR_CALIBRATION:
            direction = '偏高' if factor < 1.0 else '偏低'
            note = f'因子={factor} → 预测{direction} {abs(round((1-factor)*100))}%'
        else:
            note = '数据不足，未校准'

        stats['by_type'][task_type] = {
            'record_count': count,
            'factor': factor,
            'precision': precision,
            'min_ratio': min_ratio,
            'max_ratio': max_ratio,
            'note': note,
        }

    # 文件更新时间
    if CALIBRATION_FILE.exists():
        try:
            with open(CALIBRATION_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            stats['last_updated'] = data.get('updated_at', '')
        except (json.JSONDecodeError, IOError):
            pass

    return stats
