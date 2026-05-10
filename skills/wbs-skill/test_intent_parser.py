#!/usr/bin/env python3
"""意图解析器单元测试

测试覆盖：
1. 章节模板检测
2. 分解粒度检测
3. 聚焦关键词检测
4. 排除关键词检测
5. 任务类型检测
6. 组合意图检测
7. 边界条件

运行方式：
    python3 test_intent_parser.py
"""

import sys
import os
from pathlib import Path

# 确保能导入 src 模块
sys.path.insert(0, str(Path(__file__).parent))

from src.intent_parser import IntentParser


def _test(name: str, condition: bool, detail: str = ''):
    """断言辅助函数"""
    status = '✅' if condition else '❌'
    print(f'  {status} {name}')
    if detail and not condition:
        print(f'     详情：{detail}')
    return condition


def test_section_template():
    """测试章节模板检测"""
    parser = IntentParser()
    passed = 0
    total = 5

    # 测试 1：中文编号
    result = parser.parse('用中文编号分解')
    passed += _test(
        '中文编号检测',
        result['section_template'] == 'chinese',
        f'期望 chinese，实际 {result["section_template"]}'
    )

    # 测试 2：Markdown 格式
    result = parser.parse('用 markdown 格式')
    passed += _test(
        'Markdown 检测',
        result['section_template'] == 'markdown',
        f'期望 markdown，实际 {result["section_template"]}'
    )

    # 测试 3：混合编号
    result = parser.parse('用混合编号')
    passed += _test(
        '混合编号检测',
        result['section_template'] == 'mixed',
        f'期望 mixed，实际 {result["section_template"]}'
    )

    # 测试 4：数字编号（默认）
    result = parser.parse('默认分解')
    passed += _test(
        '默认数字编号',
        result['section_template'] == 'numeric',
        f'期望 numeric，实际 {result["section_template"]}'
    )

    # 测试 5：中文编号变体
    result = parser.parse('按一、（一）的格式分解')
    passed += _test(
        '中文编号变体检测',
        result['section_template'] == 'chinese',
        f'期望 chinese，实际 {result["section_template"]}'
    )

    print(f'\n  通过：{passed}/{total}\n')
    return passed == total


def test_granularity():
    """测试分解粒度检测"""
    parser = IntentParser()
    passed = 0
    total = 4

    # 测试 1：按周分解
    result = parser.parse('按周分解')
    passed += _test(
        '按周分解检测',
        result['granularity'] == 'weekly',
        f'期望 weekly，实际 {result["granularity"]}'
    )

    # 测试 2：按天分解
    result = parser.parse('按天分解任务')
    passed += _test(
        '按天分解检测',
        result['granularity'] == 'daily',
        f'期望 daily，实际 {result["granularity"]}'
    )

    # 测试 3：周粒度
    result = parser.parse('用周粒度')
    passed += _test(
        '周粒度检测',
        result['granularity'] == 'weekly',
        f'期望 weekly，实际 {result["granularity"]}'
    )

    # 测试 4：默认粒度
    result = parser.parse('分解任务')
    passed += _test(
        '默认粒度',
        result['granularity'] == 'default',
        f'期望 default，实际 {result["granularity"]}'
    )

    print(f'\n  通过：{passed}/{total}\n')
    return passed == total


def test_focus_keywords():
    """测试聚焦关键词检测"""
    parser = IntentParser()
    passed = 0
    total = 4

    # 测试 1：聚焦接口
    result = parser.parse('重点标出接口任务')
    passed += _test(
        '聚焦接口检测',
        '接口' in result['focus_modules'],
        f'期望包含 接口，实际 {result["focus_modules"]}'
    )

    # 测试 2：聚焦后端
    result = parser.parse('只看后端开发')
    passed += _test(
        '聚焦后端检测',
        '后端' in result['focus_modules'],
        f'期望包含 后端，实际 {result["focus_modules"]}'
    )

    # 测试 3：聚焦 API
    result = parser.parse('关注 API 任务')
    passed += _test(
        '聚焦 API 检测',
        'API' in result['focus_modules'],
        f'期望包含 API，实际 {result["focus_modules"]}'
    )

    # 测试 4：无聚焦
    result = parser.parse('分解任务')
    passed += _test(
        '无聚焦条件',
        len(result['focus_modules']) == 0,
        f'期望空列表，实际 {result["focus_modules"]}'
    )

    print(f'\n  通过：{passed}/{total}\n')
    return passed == total


def test_exclude_keywords():
    """测试排除关键词检测"""
    parser = IntentParser()
    passed = 0
    total = 4

    # 测试 1：排除运维
    result = parser.parse('排除运维相关任务')
    passed += _test(
        '排除运维检测',
        '运维' in result['exclude_keywords'],
        f'期望包含 运维，实际 {result["exclude_keywords"]}'
    )

    # 测试 2：排除监控
    result = parser.parse('去掉监控')
    passed += _test(
        '排除监控检测',
        '监控' in result['exclude_keywords'],
        f'期望包含 监控，实际 {result["exclude_keywords"]}'
    )

    # 测试 3：直接匹配排除词
    result = parser.parse('不要备份')
    passed += _test(
        '排除备份检测',
        '备份' in result['exclude_keywords'],
        f'期望包含 备份，实际 {result["exclude_keywords"]}'
    )

    # 测试 4：无排除条件
    result = parser.parse('分解任务')
    passed += _test(
        '无排除条件',
        len(result['exclude_keywords']) == 0,
        f'期望空列表，实际 {result["exclude_keywords"]}'
    )

    print(f'\n  通过：{passed}/{total}\n')
    return passed == total


def test_task_types():
    """测试任务类型检测"""
    parser = IntentParser()
    passed = 0
    total = 5

    # 测试 1：后端类型
    result = parser.parse('只分解后端开发部分')
    passed += _test(
        '后端类型检测',
        'backend' in result['task_types'],
        f'期望包含 backend，实际 {result["task_types"]}'
    )

    # 测试 2：前端类型
    result = parser.parse('前端页面开发')
    passed += _test(
        '前端类型检测',
        'frontend' in result['task_types'],
        f'期望包含 frontend，实际 {result["task_types"]}'
    )

    # 测试 3：接口类型
    result = parser.parse('接口开发')
    passed += _test(
        '接口类型检测',
        'api' in result['task_types'],
        f'期望包含 api，实际 {result["task_types"]}'
    )

    # 测试 4：数据库类型
    result = parser.parse('数据库表结构设计')
    passed += _test(
        '数据库类型检测',
        'database' in result['task_types'],
        f'期望包含 database，实际 {result["task_types"]}'
    )

    # 测试 5：运维类型
    result = parser.parse('部署和 Docker 配置')
    passed += _test(
        '运维类型检测',
        'devops' in result['task_types'],
        f'期望包含 devops，实际 {result["task_types"]}'
    )

    print(f'\n  通过：{passed}/{total}\n')
    return passed == total


def test_combined_intent():
    """测试组合意图"""
    parser = IntentParser()
    passed = 0
    total = 5

    # 测试 1：多维度组合（3 个子测试）
    result = parser.parse('按周分解，重点标出接口任务，排除运维')
    passed += _test(
        '组合意图：按周',
        result['granularity'] == 'weekly',
        f'期望 weekly，实际 {result["granularity"]}'
    )
    passed += _test(
        '组合意图：聚焦接口',
        '接口' in result['focus_modules'],
        f'期望包含 接口，实际 {result["focus_modules"]}'
    )
    passed += _test(
        '组合意图：排除运维',
        '运维' in result['exclude_keywords'],
        f'期望包含 运维，实际 {result["exclude_keywords"]}'
    )

    # 测试 2：后端 + 接口
    result = parser.parse('只分解后端接口部分')
    passed += _test(
        '后端 + 接口组合',
        'backend' in result['task_types'] and 'api' in result['task_types'],
        f'期望包含 backend 和 api，实际 {result["task_types"]}'
    )

    # 测试 3：空输入
    result = parser.parse('')
    passed += _test(
        '空输入默认参数',
        result['section_template'] == 'numeric' and
        result['granularity'] == 'default' and
        len(result['focus_modules']) == 0 and
        len(result['exclude_keywords']) == 0 and
        len(result['task_types']) == 0,
        f'实际 {result}'
    )

    print(f'\n  通过：{passed}/{total}\n')
    return passed == total


def test_has_filters():
    """测试 has_filters 方法"""
    parser = IntentParser()
    passed = 0
    total = 3

    # 测试 1：有聚焦条件
    result = parser.parse('重点看接口')
    passed += _test(
        '有聚焦条件',
        parser.has_filters(result),
        '期望 True'
    )

    # 测试 2：有排除条件
    result = parser.parse('排除运维')
    passed += _test(
        '有排除条件',
        parser.has_filters(result),
        '期望 True'
    )

    # 测试 3：无过滤条件
    result = parser.parse('按周分解')
    passed += _test(
        '无过滤条件',
        not parser.has_filters(result),
        '期望 False'
    )

    print(f'\n  通过：{passed}/{total}\n')
    return passed == total


def main():
    """运行所有测试"""
    print('=' * 60)
    print('意图解析器单元测试')
    print('=' * 60)

    tests = [
        ('章节模板检测', test_section_template),
        ('分解粒度检测', test_granularity),
        ('聚焦关键词检测', test_focus_keywords),
        ('排除关键词检测', test_exclude_keywords),
        ('任务类型检测', test_task_types),
        ('组合意图检测', test_combined_intent),
        ('has_filters 方法', test_has_filters),
    ]

    total_passed = 0
    total_tests = 0

    for name, test_func in tests:
        print(f'\n📋 {name}')
        print('-' * 40)
        try:
            result = test_func()
            total_passed += 1 if result else 0
            total_tests += 1
        except Exception as e:
            print(f'  ❌ 测试异常：{e}')
            total_tests += 1

    print('\n' + '=' * 60)
    print(f'测试完成：{total_passed}/{total_tests} 通过')
    if total_passed == total_tests:
        print('✅ 全部通过！')
    else:
        print(f'❌ 失败 {total_tests - total_passed} 个')
    print('=' * 60)

    return total_passed == total_tests


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
