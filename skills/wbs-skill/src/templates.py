"""验收标准模板 - 生产级（精确可执行）"""

from typing import List, Dict


# 精确可执行的验收标准模板
ACCEPTANCE_CRITERIA = {
    # 接口类任务
    'REST_API': [
        '接口可正常调用（HTTP 200）',
        '请求参数校验完善（必填字段、格式校验）',
        '返回 JSON 格式正确（符合接口文档定义）',
        '错误码规范（符合统一错误码定义）',
        '异常场景处理完善（空数据、超时、并发）',
        '接口响应时间 < 500ms（95% 请求）',
        '接口文档完整（Swagger/YApi 可查）'
    ],
    
    # 功能类任务
    'FEATURE': [
        '功能流程可正常执行',
        '边界条件处理完善（最大值、最小值、空值）',
        '用户体验良好（无明显卡顿、报错）',
        '数据展示正确（与数据库一致）',
        '操作反馈及时（加载提示、成功/失败提示）'
    ],
    
    # 逻辑类任务
    'LOGIC': [
        '业务逻辑正确（符合需求文档）',
        '边界条件处理完善（极端场景）',
        '单元测试覆盖率 > 80%',
        '代码审查通过（无严重漏洞）',
        '性能测试通过（无明显性能问题）'
    ],
    
    # 配置类任务
    'CONFIG': [
        '配置项可正常保存',
        '配置可正确读取',
        '配置变更立即生效（或重启后生效）',
        '配置有默认值',
        '配置变更有日志记录'
    ],
    
    # 数据记录类任务
    'DATA_RECORD': [
        '数据正确写入数据库',
        '数据字段完整（无遗漏）',
        '数据格式正确（类型、长度）',
        '数据可正确查询',
        '数据一致性保证（与源数据一致）'
    ],
    
    # 扣费类任务
    'PAYMENT': [
        '扣费金额计算正确',
        '扣费前余额校验',
        '扣费后余额更新正确',
        '扣费记录完整（时间、金额、类型）',
        '扣费失败有回滚机制',
        '扣费通知发送成功'
    ],
    
    # 轮询类任务
    'POLLING': [
        '轮询间隔正确（如 5 分钟）',
        '轮询超时处理完善',
        '轮询结果正确存储',
        '轮询失败有重试机制',
        '轮询状态可查询'
    ],
    
    # 计算公式类任务
    'CALCULATION': [
        '计算公式正确（符合需求定义）',
        '边界值计算正确（0、负数、极大值）',
        '计算结果精度符合要求',
        '计算性能达标（单次 < 100ms）',
        '计算结果可追溯（有日志）'
    ],
}


def get_acceptance_criteria(task_type: str, task_content: str = '') -> str:
    """
    获取可验收标准（精确可执行）
    
    Args:
        task_type: 任务类型
        task_content: 任务内容（用于智能匹配）
        
    Returns:
        str: 可验收标准（多条用分号分隔）
    """
    # 根据任务内容关键词智能匹配
    content_lower = task_content.lower() if task_content else ''
    
    # 扣费相关
    if any(kw in content_lower for kw in ['扣费', '扣减', 'token 数']):
        criteria = ACCEPTANCE_CRITERIA.get('PAYMENT', [])
        return '；'.join(criteria[:5])
    
    # 接口相关
    if any(kw in content_lower for kw in ['接口', 'api', 'http', '返回']):
        criteria = ACCEPTANCE_CRITERIA.get('REST_API', [])
        return '；'.join(criteria[:5])
    
    # 轮询相关
    if any(kw in content_lower for kw in ['轮询', '等待', '查询结果']):
        criteria = ACCEPTANCE_CRITERIA.get('POLLING', [])
        return '；'.join(criteria[:5])
    
    # 数据记录相关
    if any(kw in content_lower for kw in ['记录', '存储', '写入', '表']):
        criteria = ACCEPTANCE_CRITERIA.get('DATA_RECORD', [])
        return '；'.join(criteria[:5])
    
    # 计算公式相关
    if any(kw in content_lower for kw in ['公式', '计算', 'token 数']):
        criteria = ACCEPTANCE_CRITERIA.get('CALCULATION', [])
        return '；'.join(criteria[:5])
    
    # 配置相关
    if any(kw in content_lower for kw in ['配置', '设置']):
        criteria = ACCEPTANCE_CRITERIA.get('CONFIG', [])
        return '；'.join(criteria[:5])
    
    # 功能类（默认）
    criteria = ACCEPTANCE_CRITERIA.get('FEATURE', [])
    return '；'.join(criteria[:5])


def generate_dependency(task_index: int, all_tasks: List[Dict]) -> str:
    """
    生成依赖关系
    
    Args:
        task_index: 当前任务索引
        all_tasks: 所有任务列表
        
    Returns:
        str: 依赖关系
    """
    if task_index == 0:
        return '无'
    
    # 查找前一个同模块任务
    current_module = all_tasks[task_index].get('任务模块', '未分类')
    for i in range(task_index - 1, -1, -1):
        if all_tasks[i].get('任务模块', '未分类') == current_module:
            return f"T{i+1:03d}"
    
    return '无'
