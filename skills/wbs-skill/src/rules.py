"""任务识别规则模块"""

import re
from typing import List, Dict, Tuple


# 任务识别规则（生产级 - 外放接口增强版）
# 格式：(正则表达式，任务类型，任务内容模板)
TASK_PATTERNS = [
    # ========== 外放接口识别（优先级最高）==========
    # REST API 接口（精确匹配）
    (r'(GET|POST|PUT|DELETE|PATCH)\s+(/api/[\w/-]+)', 'REST_API', '实现 REST API：{method} {path}'),
    (r'HTTP\s*接⼝', 'REST_API', '实现 HTTP 接口'),
    
    # 外放接口关键词（多种描述方式）
    (r'外放接⼝', 'EXTERNAL_API', '实现外放接口'),
    (r'对外接⼝', 'EXTERNAL_API', '实现对外接口'),
    (r'开放接⼝', 'EXTERNAL_API', '实现开放接口'),
    (r'开放平台接⼝', 'EXTERNAL_API', '实现开放平台接口'),
    (r'第三⽅接⼝', 'EXTERNAL_API', '实现第三方接口'),
    (r'API 接⼝', 'EXTERNAL_API', '实现 API 接口'),
    (r'1\.3', 'EXTERNAL_API', '实现 1.3 外放接口'),
    
    # 接口服务能力描述
    (r'提供.*接⼝.*服务', 'EXTERNAL_API', '实现接口服务'),
    (r'提供.*API.*服务', 'EXTERNAL_API', '实现 API 服务'),
    (r'⽀持.*调⽤', 'EXTERNAL_API', '实现调用支持'),
    (r'供.*调⽤', 'EXTERNAL_API', '实现供调用'),
    (r'对外提供', 'EXTERNAL_API', '实现对外提供'),
    (r'后台的接⼝', 'EXTERNAL_API', '实现后台接口'),
    (r'需后端接⼝', 'EXTERNAL_API', '实现后端接口'),
    
    # ========== 标准接口开发任务 ==========
    (r'(.+接口)', 'INTERFACE', '实现{target}接口开发'),
    (r'(.+接⼝)', 'INTERFACE', '实现{target}接口开发'),
    (r'新增接⼝', 'INTERFACE', '实现新增接口'),
    (r'创建接⼝', 'INTERFACE', '实现创建接口'),
    
    # ========== 功能开发任务 ==========
    (r'(.+功能)', 'FEATURE', '实现{target}功能开发'),
    (r'实现.*功能', 'FEATURE', '实现功能开发'),
    (r'提供.*功能', 'FEATURE', '提供功能开发'),
    
    # ========== 逻辑开发任务 ==========
    (r'(.+逻辑)', 'LOGIC', '实现{target}逻辑开发'),
    (r'后端处理逻辑', 'LOGIC', '实现后端处理逻辑开发'),
    (r'业务逻辑', 'LOGIC', '实现业务逻辑开发'),
    
    # ========== 配置调整任务 ==========
    (r'(.+配置)', 'CONFIG', '调整{target}配置'),
    (r'配置\s*(.+)', 'CONFIG', '配置{target}'),
    (r'Nacos 配置', 'CONFIG', '调整 Nacos 配置'),
    
    # ========== 查询/管理任务 ==========
    (r'(.+查询)', 'FEATURE', '实现{target}查询功能'),
    (r'(.+管理)', 'FEATURE', '实现{target}管理功能'),
    (r'(.+列表)', 'FEATURE', '实现{target}列表功能'),
]

# 模块识别规则（增强版 - 外放接口）
MODULE_PATTERNS = [
    # 技能中心
    (r'技能中心 | 技能管理 | 技能模块', '技能中心'),
    (r'1\.2\.1|1\.2\.1\.\d+', '技能中心'),
    
    # 对话管理
    (r'对话管理 | 会话管理 | 聊天管理', '对话管理'),
    (r'1\.2\.2|1\.2\.2\.\d+', '对话管理'),
    
    # 渠道模块
    (r'渠道模块 | 渠道管理 | 第三方渠道', '渠道模块'),
    (r'1\.2\.3|1\.2\.3\.\d+', '渠道模块'),
    
    # mClaw 模块
    (r'mClaw|mclaw|MCLAW|M-Claw', 'mClaw 模块'),
    (r'1\.2\.4|1\.2\.4\.\d+', 'mClaw 模块'),
    
    # 定时任务模块
    (r'定时任务 | 任务调度 | 定时器 | 调度任务', '定时任务模块'),
    (r'1\.2\.5|1\.2\.5\.\d+', '定时任务模块'),
    
    # 代理模块
    (r'代理 | 大模型 |LLM|AI 代理', '代理模块'),
    (r'1\.2\.6|1\.2\.6\.\d+', '代理模块'),
    
    # 用户中心
    (r'用户中心 | 用户管理 | 个人中心', '用户中心'),
    
    # 云盘模块
    (r'云盘 | 云存储 | 存储管理', '云盘模块'),
    
    # 实例查询
    (r'实例查询 | 实例管理', '实例查询模块'),
    
    # 全局配置
    (r'全局配置 | 系统配置', '全局配置模块'),
    
    # 外放接口模块（新增）
    (r'外放接⼝ | 对外接⼝ | 开放接⼝ | 开放平台', '外放接口模块'),
    (r'HTTP 接⼝ | API 接⼝ | REST 接⼝', '外放接口模块'),
    (r'1\.3|1\.3\.\d+', '外放接口模块'),
]


def extract_tasks(text: str) -> List[Dict]:
    """
    从文本中提取任务
    
    Args:
        text: 技术方案文本
        
    Returns:
        list: 任务列表
    """
    tasks = []
    lines = text.split('\n')
    
    current_module = '未分类'
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 识别模块
        for pattern, module in MODULE_PATTERNS:
            if re.search(pattern, line):
                current_module = module
                break
        
        # 识别任务
        for pattern, task_type, template in TASK_PATTERNS:
            match = re.search(pattern, line)
            if match:
                # 处理多个捕获组的情况
                if match.lastindex and match.lastindex >= 1:
                    target = match.group(1)
                else:
                    target = match.group(0)
                
                # 处理 REST API 特殊情况
                if task_type == 'REST_API':
                    method = match.group(1)
                    path = match.group(2)
                    task_content = template.replace('{method}', method).replace('{path}', path)
                else:
                    task_content = template.replace('{target}', target)
                
                task = {
                    '任务模块': current_module,
                    '任务类型': task_type,
                    '任务内容': task_content,
                    '原始描述': line
                }
                tasks.append(task)
                break  # 匹配到一个规则就停止
    
    return tasks


def get_task_pattern(task_type: str) -> str:
    """
    获取任务类型的正则表达式
    
    Args:
        task_type: 任务类型
        
    Returns:
        str: 正则表达式
    """
    for pattern, t_type, _ in TASK_PATTERNS:
        if t_type == task_type:
            return pattern
    return None


def clean_task_content(content: str) -> str:
    """
    清理任务内容（去除重复和特殊字符）
    
    Args:
        content: 原始任务内容
        
    Returns:
        str: 清理后的任务内容
    """
    import re
    
    if not content:
        return ''
    
    # 移除"•"、"-"、"*"等符号（任意位置）
    content = re.sub(r'[•\-\*]', '', content)
    
    # 移除重复的"实现"
    content = re.sub(r'实现\s*实现', '实现', content)
    
    # 特殊处理："XX 功能功能开发"→"XX 功能开发"、"XX 逻辑逻辑开发"→"XX 逻辑开发"
    content = re.sub(r'功能功能开发', r'功能开发', content)
    content = re.sub(r'逻辑逻辑开发', r'逻辑开发', content)
    content = re.sub(r'配置配置', r'配置', content)
    content = re.sub(r'接口接口', r'接口', content)
    content = re.sub(r'任务任务', r'任务', content)
    content = re.sub(r'渠道配置配置', r'渠道配置', content)
    content = re.sub(r'模块模块', r'模块', content)
    
    # 移除"列表列表"、"查询查询"、"管理管理"等重复词
    content = re.sub(r'列表列表', r'列表', content)
    content = re.sub(r'查询查询', r'查询', content)
    content = re.sub(r'管理管理', r'管理', content)
    content = re.sub(r'技能技能', r'技能', content)
    content = re.sub(r'功能功能', r'功能', content)
    content = re.sub(r'接口接口', r'接口', content)
    content = re.sub(r'任务任务', r'任务', content)
    content = re.sub(r'配置配置', r'配置', content)
    content = re.sub(r'用户用户', r'用户', content)
    content = re.sub(r'数据数据', r'数据', content)
    
    # 移除"逻辑逻辑"、"功能功能"、"配置配置"等重复（多次替换）
    for _ in range(5):
        content = re.sub(r'(逻辑 | 功能 | 配置 | 接口 | 任务 | 渠道 | 开发 | 模型 | 技能 | 模块 | 表 | 列表 | 查询 | 管理)\1', r'\1', content)
    
    # 移除章节号前缀（如 1.2.1.2.1）
    content = re.sub(r'^\d+\.\d+\.\d+\.\d+\s*', '', content)
    
    # 移除"表中的"等冗余词
    content = re.sub(r'表中的', '', content)
    
    # 移除"实现"前缀
    content = re.sub(r'^实现\s*', '', content)
    
    # 移除"调整"前缀（保留核心内容）
    content = re.sub(r'^调整\s*', '', content)
    
    # 移除多余的空格
    content = re.sub(r'\s+', ' ', content).strip()
    
    # 精简任务内容（去除冗余描述）
    content = re.sub(r'^打开 (.+)', r'\1', content)
    content = re.sub(r'^返回 (.+)', r'\1', content)
    content = re.sub(r'^查询 (.+)', r'\1', content)
    content = re.sub(r'^提供 (.+)', r'\1', content)
    content = re.sub(r'^业务目标：', '', content)
    content = re.sub(r'^实现逻辑：', '', content)
    content = re.sub(r'^触发条件：', '', content)
    
    # 移除"功能"后缀的冗余
    content = re.sub(r'功能功能$', '功能', content)
    
    # 移除过长的技术细节描述（保留核心任务）
    if len(content) > 60:
        # 提取核心部分（第一个句号前或前 60 字）
        if '。' in content:
            content = content.split('.')[0]
        else:
            content = content[:60]
    
    return content
