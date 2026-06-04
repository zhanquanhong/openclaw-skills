"""wbs-skill v5 工作量估算 — 单元测试"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

# 确保可导入 src
SKILL_DIR = Path(__file__).parent.parent.absolute()
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from src.estimator.rules import (
    score_content,
    calculate_recommended_days,
    get_fallback_baseline,
)
from src.estimator.calibrator import (
    compute_calibration_factors,
    get_factor,
    get_precision,
    add_calibration_records,
    get_stats,
    CALIBRATION_FILE,
    MIN_RECORDS_FOR_CALIBRATION,
)
from src.estimator.engine import estimate_tasks

# ═══════════════════════════════════════════════════════════════
# rules.py 测试
# ═══════════════════════════════════════════════════════════════


class TestEntityScoring:

    def test_standard_interface(self):
        """标准接口 → 2.0 天"""
        scores = score_content('新增用户查询接口')
        assert scores['entity_score'] == 2.0, f'预期 2.0, 实际 {scores["entity_score"]}'
        assert '标准接口' in scores['matched_entities']

    def test_simple_interface(self):
        """简单接口 → 1.0 天"""
        scores = score_content('查询用户列表接口')
        assert scores['entity_score'] == 1.0, f'预期 1.0, 实际 {scores["entity_score"]}'
        assert '简单接口' in scores['matched_entities']

    def test_single_table(self):
        """单表设计 → 0.5 天"""
        scores = score_content('新增用户表')
        assert scores['entity_score'] == 0.5, f'预期 0.5, 实际 {scores["entity_score"]}'
        assert '单表设计' in scores['matched_entities']

    def test_page_ui(self):
        """页面/UI → 2.0 天"""
        scores = score_content('新增用户管理页面')
        assert scores['entity_score'] == 2.0, f'预期 2.0, 实际 {scores["entity_score"]}'
        assert '页面/UI' in scores['matched_entities']

    def test_config_task(self):
        """配置/设置 → 0.5 天"""
        scores = score_content('配置数据库连接池参数')
        assert scores['entity_score'] == 0.5, f'预期 0.5, 实际 {scores["entity_score"]}'
        assert '配置/设置' in scores['matched_entities']

    def test_data_migration(self):
        """数据迁移 → 2.5 天"""
        scores = score_content('历史订单数据迁移脚本')
        assert scores['entity_score'] == 2.5, f'预期 2.5, 实际 {scores["entity_score"]}'
        assert '数据迁移' in scores['matched_entities']

    def test_scheduled_task(self):
        """定时任务 → 1.5 天"""
        scores = score_content('新增每日数据同步定时任务')
        assert scores['entity_score'] == 1.5, f'预期 1.5, 实际 {scores["entity_score"]}'
        assert '定时任务' in scores['matched_entities']

    def test_middleware(self):
        """中间件/缓存 → 1.5 天"""
        scores = score_content('接入Redis缓存热点数据')
        assert scores['entity_score'] == 1.5, f'预期 1.5, 实际 {scores["entity_score"]}'
        assert '中间件/缓存' in scores['matched_entities']

    def test_workflow_approval(self):
        """工作流/审批 → 2.0 天"""
        scores = score_content('新增审批工作流')
        assert scores['entity_score'] == 2.0, f'预期 2.0, 实际 {scores["entity_score"]}'
        assert '工作流/审批' in scores['matched_entities']


class TestSpecialLogic:

    def test_distributed_bonus(self):
        """分布式 → +1.5"""
        scores = score_content('实现分布式定时任务锁')
        assert scores['special_bonus'] == 1.5, f'预期 1.5, 实际 {scores["special_bonus"]}'
        assert '分布式/高并发' in scores['matched_specials']

    def test_transaction_bonus(self):
        """事务 → +1.0"""
        scores = score_content('实现分布式事务补偿')
        assert scores['special_bonus'] >= 1.0
        assert '事务/补偿' in scores['matched_specials']

    def test_third_party_bonus(self):
        """第三方集成 → +1.5"""
        scores = score_content('对接微信支付回调接口')
        assert scores['special_bonus'] >= 1.5
        assert '第三方集成' in scores['matched_specials']

    def test_batch_bonus(self):
        """批量 → +1.0"""
        scores = score_content('批量导入历史用户数据')
        assert scores['special_bonus'] >= 1.0
        assert '批量操作' in scores['matched_specials']

    def test_permission_bonus(self):
        """权限 → +0.5"""
        scores = score_content('新增RBAC权限判断')
        assert scores['special_bonus'] >= 0.5
        assert '权限/安全' in scores['matched_specials']

    def test_multiple_bonuses_accumulate(self):
        """多个特殊逻辑加分累加"""
        scores = score_content('批量第三方数据迁移+分布式事务')

        # 应该匹配多个
        specials = set(scores['matched_specials'])
        assert len(specials) >= 2, f'匹配到: {specials}'
        # 批量操作 + 至少一个加分
        assert scores['special_bonus'] >= 1.0


class TestIterationFactor:

    def test_new_dev(self):
        """新建 → ×1.0"""
        scores = score_content('新增用户查询接口')
        assert scores['iteration_factor'] == 1.0

    def test_iteration(self):
        """修改 → ×0.5"""
        scores = score_content('修改订单查询接口')
        assert scores['iteration_factor'] == 0.5, f'预期 0.5, 实际 {scores["iteration_factor"]}'

    def test_delete(self):
        """删除 → ×0.3"""
        scores = score_content('删除过期日志任务')
        assert scores['iteration_factor'] == 0.3

    def test_default_new_dev(self):
        """兜底 → ×1.0（保守）"""
        scores = score_content('用户信息管理功能')
        assert scores['iteration_factor'] == 1.0


class TestCalculateRecommended:

    def test_standard_interface_new_dev(self):
        """新接口 新建 → 2.0天"""
        days, factor = calculate_recommended_days('新增用户查询接口', '接口任务')
        assert days == 2.0, f'预期 2.0, 实际 {days}'

    def test_simple_interface_iteration(self):
        """简单接口 修改 → 0.5 天 (1.0 × 0.5)"""
        days, factor = calculate_recommended_days('修改订单查询接口', '接口任务')
        assert days == 0.5, f'预期 0.5, 实际 {days}'

    def test_complex_task(self):
        """复杂任务：第三方+批量（无标准接口关键词）"""
        days, factor = calculate_recommended_days('批量导入第三方数据接口', '接口任务')
        # 无实体匹配，特殊加分: 第三方(+1.5) + 批量(+1.0) = 2.5 × 1.0
        assert days == 2.5, f'预期 2.5, 实际 {days}'

    def test_empty_content_fallback(self):
        """空内容回退到兜底基线"""
        scores = score_content('')
        assert scores['raw_score'] == 0, '空内容特征分应为 0'
        baseline = get_fallback_baseline('接口任务')
        assert baseline == 1.5, f'接口任务兜底基线预期 1.5, 实际 {baseline}'

    def test_with_calibration(self):
        """带校准因子"""
        days, factor = calculate_recommended_days('新增用户查询接口', '接口任务', calibration_factor=0.9)
        assert days == 1.8, f'预期 1.8 (2.0×0.9), 实际 {days}'

    def test_minimum_floor(self):
        """下限 0.3 天"""
        days, factor = calculate_recommended_days('删除一个简单配置', '配置任务')
        # 无任何实体匹配 → 回退 0.3 兜底 × 0.3 迭代系数 = 0.09 → 取 0.3
        assert days >= 0.3

    def test_no_match_fallback(self):
        """无特征匹配→回退到 task_type"""
        days, factor = calculate_recommended_days('做一些系统优化', '前端任务')
        assert days == 1.0, f'预期 1.0 (前端兜底 2.0 × 0.5 迭代), 实际 {days}'


# ═══════════════════════════════════════════════════════════════
# calibrator.py 测试
# ═══════════════════════════════════════════════════════════════


class TestCalibrator:
    def setup_method(self):
        """每个测试前备份并清空校准文件"""
        self._backup = None
        if CALIBRATION_FILE.exists():
            self._backup = CALIBRATION_FILE.read_text()
            CALIBRATION_FILE.unlink()

    def teardown_method(self):
        """恢复原始校准文件"""
        if self._backup:
            CALIBRATION_FILE.parent.mkdir(parents=True, exist_ok=True)
            CALIBRATION_FILE.write_text(self._backup)
        elif CALIBRATION_FILE.exists():
            CALIBRATION_FILE.unlink()

    def test_empty_no_factors(self):
        """无数据 → 空因子"""
        factors = compute_calibration_factors()
        assert factors == {}, f'无数据预期空字典, 实际 {factors}'

    def test_add_records(self):
        """添加记录"""
        records = [
            {'task_content': '新增用户接口', 'task_type': '接口任务',
             'predicted_days': 2.0, 'actual_days': 2.5},
        ]
        success, skipped = add_calibration_records(records)
        assert success == 1
        assert skipped == 0

    def test_insufficient_records(self):
        """不足 3 条 → 不校准"""
        records = [
            {'task_content': f'任务{i}', 'task_type': '接口任务',
             'predicted_days': 2.0, 'actual_days': 2.0}
            for i in range(MIN_RECORDS_FOR_CALIBRATION - 1)
        ]
        add_calibration_records(records)
        factor = get_factor('接口任务')
        assert factor == 1.0, f'不足3条预期因子=1.0, 实际 {factor}'

    def test_sufficient_records_median(self):
        """足够记录 → 中位数因子"""
        records = [
            {'task_content': f'任务{i}', 'task_type': '接口任务',
             'predicted_days': 2.0, 'actual_days': 2.0}  # ratio=1.0
            for i in range(MIN_RECORDS_FOR_CALIBRATION)
        ]
        records.extend([
            {'task_content': '额外任务', 'task_type': '接口任务',
             'predicted_days': 2.0, 'actual_days': 4.0},  # ratio=2.0
            {'task_content': '额外任务2', 'task_type': '接口任务',
             'predicted_days': 2.0, 'actual_days': 2.5},  # ratio=1.25
        ])
        add_calibration_records(records)
        factor = get_factor('接口任务')
        assert factor == 1.0, f'中位数预期 1.0, 实际 {factor}'

    def test_multiple_types(self):
        """不同类型各算各的"""
        records = [
            {'task_content': '接口A', 'task_type': '接口任务',
             'predicted_days': 2.0, 'actual_days': 1.5},
            {'task_content': '接口B', 'task_type': '接口任务',
             'predicted_days': 2.0, 'actual_days': 1.8},
            {'task_content': '接口C', 'task_type': '接口任务',
             'predicted_days': 2.0, 'actual_days': 1.7},
            {'task_content': '前端A', 'task_type': '前端任务',
             'predicted_days': 3.0, 'actual_days': 4.0},
            {'task_content': '前端B', 'task_type': '前端任务',
             'predicted_days': 3.0, 'actual_days': 3.5},
            {'task_content': '前端C', 'task_type': '前端任务',
             'predicted_days': 3.0, 'actual_days': 3.0},
        ]
        add_calibration_records(records)
        factors = compute_calibration_factors()

        interface_factor = factors['接口任务']['factor']
        assert abs(interface_factor - 0.85) < 0.01, f'接口因子预期 0.85, 实际 {interface_factor}'

        frontend_factor = factors['前端任务']['factor']
        assert abs(frontend_factor - 1.17) < 0.02, f'前端因子预期 ~1.17, 实际 {frontend_factor}'

    def test_duplicate_records_skipped(self):
        """重复记录 → 跳过"""
        records = [
            {'task_content': '新增接口', 'task_type': '接口任务',
             'predicted_days': 2.0, 'actual_days': 2.5},
        ]
        add_calibration_records(records)
        success, skipped = add_calibration_records(records)
        assert success == 0, f'重复应跳过, 实际成功 {success}'
        assert skipped >= 1, f'跳过应 >= 1, 实际 {skipped}'

    def test_invalid_record_skipped(self):
        """无效记录 → 跳过"""
        records = [
            {'task_content': '', 'actual_days': 2.5},
            {'task_content': '有效', 'actual_days': -1},
            {'task_content': '有效2', 'actual_days': 'abc'},
        ]
        success, skipped = add_calibration_records(records)
        assert success == 0, '应全部跳过'
        assert skipped == 3


class TestPrecision:
    def test_no_records(self):
        assert get_precision(0) == 0.50

    def test_three_records(self):
        assert get_precision(3) == 0.30

    def test_six_records(self):
        assert get_precision(6) == 0.20

    def test_twenty_plus(self):
        assert get_precision(20) == 0.15
        assert get_precision(100) == 0.15


# ═══════════════════════════════════════════════════════════════
# engine.py 测试
# ═══════════════════════════════════════════════════════════════


class TestEngine:
    def test_estimate_tasks_adds_fields(self):
        """estimate_tasks 追加字段"""
        tasks = [
            {'任务模块': '用户管理', '任务内容': '新增用户查询接口', '任务类型': '接口任务',
             '任务来源': '章节2.1', '依赖': '无', '可验收标准': '', '验证状态': 'PASS'},
            {'任务模块': '权限系统', '任务内容': '设计用户角色权限表', '任务类型': '数据库任务',
             '任务来源': '章节3.2', '依赖': 'T001', '可验收标准': '', '验证状态': 'PASS'},
        ]
        result = estimate_tasks(tasks)
        for task in result:
            assert '推荐人天数' in task, f'缺少推荐人天数: {task}'
            assert '估算范围' in task, f'缺少估算范围: {task}'
            assert isinstance(task['推荐人天数'], (int, float))
            assert isinstance(task['估算范围'], str)
            assert '~' in task['估算范围']

    def test_estimate_tasks_sum(self):
        """估算合计"""
        tasks = [
            {'任务模块': 'M1', '任务内容': '新增用户查询接口', '任务类型': '接口任务',
             '任务来源': '', '依赖': '', '可验收标准': '', '验证状态': 'PASS'},
        ]
        result = estimate_tasks(tasks)
        assert result[0]['推荐人天数'] == 2.0, f'预期 2.0, 实际 {result[0]["推荐人天数"]}'

    def test_empty_tasks(self):
        """空任务列表"""
        result = estimate_tasks([])
        assert result == []

    def test_missing_content(self):
        """缺少任务内容"""
        tasks = [
            {'任务模块': 'M1', '任务类型': '接口任务',
             '任务来源': '', '依赖': '', '可验收标准': '', '验证状态': 'PASS'},
        ]
        result = estimate_tasks(tasks)
        # 空内容回退到兜底
        assert result[0]['推荐人天数'] >= 0.3
