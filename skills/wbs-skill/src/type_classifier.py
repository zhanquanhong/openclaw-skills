"""任务类型分类器 + 任务内容概括器 + 有效性过滤器 - LLM 批量

职责：
1. 读取配置中的任务类型定义
2. 调用 LLM 批量判断任务有效性 + 任务类型 + 概括任务内容
3. 过滤无效任务（时序图描述、接口响应示例、参数说明等）
4. LLM 不可用时回退到关键词匹配 + 句号分句（不过滤）
5. 不涉及任务模块、任务来源的任何修改
"""

import json
import logging
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_PATH = 'config/type_rules.yaml'


def load_type_config() -> Dict:
    """加载类型配置文件

    Returns:
        包含 'types'、'llm_prompt'、'fallback_keywords' 的字典
    """
    try:
        import yaml
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"加载类型配置失败: {e}，使用内置默认配置")
        return _get_default_config()


def _get_default_config() -> Dict:
    """内置默认配置（当配置文件加载失败时使用）"""
    return {
        'types': [
            {'id': '接口任务', 'description': '新增/更新 API，前后端数据交互'},
            {'id': '数据库任务', 'description': '表结构设计、SQL、索引、DDL、数据迁移'},
            {'id': '前端任务', 'description': '页面、UI 组件、交互'},
            {'id': '中间件任务', 'description': '消息队列、缓存、Redis、MQ、定时任务'},
            {'id': '配置任务', 'description': '参数配置、环境变量、设置'},
            {'id': '运维任务', 'description': '部署、监控、日志、告警、CI/CD'},
            {'id': '架构设计', 'description': '系统架构、模块划分、方案设计'},
            {'id': '数据迁移', 'description': '历史数据迁移、数据清洗'},
            {'id': '权限/安全', 'description': 'RBAC、鉴权、加密'},
            {'id': '功能任务', 'description': '以上均不属于的业务逻辑'},
        ],
        'llm_prompt': (
            '你是一名软件工程任务分析师。请为以下每一条原文做三件事：\n\n'
            '1. 判断是否是一个可执行的任务（valid: true/false）\n'
            '   - valid=false：时序图描述、接口响应示例（alt[xxx]）、参数说明（入参/出参）、交叉引用（详见xxx）、需求背景描述、架构图标注行、枚举项行为说明行（如"当XX时"、"不XXX，仅XXX"）、章节概述标题行\n'
            '   - valid=true：需要开发人员动手实现的开发任务\n'
            '2. 如果 valid=true，判断任务类型（从列出的类型中选择一个）\n'
            '3. 如果 valid=true，概括任务内容（简洁动宾结构，20字以内）\n\n'
            '可选的类型：\n{type_list}\n\n'
            '返回格式为 JSON，key 为任务序号（字符串），value 为对象：\n'
            '{{"1": {{"valid": true, "type": "接口任务", "summary": "新增用户查询接口"}}, "2": {{"valid": false}}, ...}}\n\n'
            '只返回 JSON，不要其他文字。\n\n任务列表：\n{task_list}'
        ),
        'fallback_keywords': {
            '接口任务': ['接口', 'API', 'POST', 'GET', 'PUT', 'DELETE', 'PATCH', 'endpoint', 'http'],
            '数据库任务': ['表', '字段', '索引', 'SQL', '数据库', 'DDL', '建表', 'ALTER', 'CREATE TABLE', 'DROP'],
            '配置任务': ['配置', '设置', '参数', 'config', 'settings', '环境变量'],
            '中间件任务': ['缓存', 'Redis', '队列', 'RabbitMQ', 'Kafka', 'MQ', '定时任务', 'Cron', '消息', 'XXL-Job'],
            '前端任务': ['前端', '页面', 'UI', '组件', '交互', '样式', 'CSS', 'Vue', 'React'],
            '算法任务': ['算法', '模型', '训练', '推理', 'embedding', '相似度', '向量'],
        },
    }


class TypeClassifier:
    """任务类型分类器 + 内容概括器 + 有效性过滤器

    使用 LLM 批量判断任务有效性、任务类型和概括任务内容。
    LLM 不可用时回退到关键词匹配（不过滤）。
    """

    def __init__(
        self,
        config: Optional[Dict] = None,
        batch_size: int = 25,
        model: str = 'deepseek-chat',
    ):
        """初始化类型分类器

        Args:
            config: 类型配置，None 时自动加载
            batch_size: 每批分类的任务数
            model: LLM 模型名称
        """
        self.config = config or load_type_config()
        self.batch_size = batch_size
        self.model = model
        self.type_names = [t['id'] for t in self.config.get('types', [])]
        self.type_ids = set(self.type_names)
        self.fallback_keywords = self.config.get('fallback_keywords', {})

    def classify(
        self, tasks: List[Dict]
    ) -> List[Dict]:
        """对任务列表进行分类、概括和有效性过滤

        不会修改 tasks 中的任务模块、任务来源。
        过滤无效任务（时序图描述、接口响应示例、参数说明等）。
        LLM 概括后对同一模块下内容完全相同的去重。

        Args:
            tasks: 任务字典列表，需要包含 '任务内容' 和 '任务来源' 字段

        Returns:
            过滤后的任务列表，每项更新 '任务类型' 和 '任务内容'（LLM 概括版）
            无效任务被移除。
        """
        if not tasks:
            return tasks

        # 分离步骤派生任务（来源行包含"第N步"或复合拆分产物）
        # 这些任务不应被 LLM 以 valid=false 过滤，但仍可做类型推断
        step_tasks = [t for t in tasks if t.get('_step_derived')]
        normal_tasks = [t for t in tasks if not t.get('_step_derived')]

        if not normal_tasks:
            # 全部是步骤派生任务，只做类型推断
            return self._classify_fallback(step_tasks)

        try:
            result = self._classify_llm(normal_tasks)
            # 后置过滤：LLM 可能漏掉的任务（如"不存在"、"zipb."等短噪声）
            result = self._post_filter(result)
            # LLM 概括后去重：同一模块下内容完全相同的任务只保留第一个
            result = self._deduplicate(result)
            # 合并步骤派生任务（不做有效性过滤，只做类型推断）
            if step_tasks:
                step_result = self._classify_fallback(step_tasks)
                result.extend(step_result)
                # 合并后再次去重
                result = self._deduplicate(result)
            valid_count = len(result)
            logger.info(f"LLM 分类完成：{valid_count} 条任务（步骤派生 {len(step_tasks)} 条豁免过滤）")
            return result
        except Exception as e:
            logger.warning(f"LLM 分类失败: {e}，回退到关键词匹配（不过滤）")
            result = self._classify_fallback(normal_tasks)
            if step_tasks:
                result.extend(self._classify_fallback(step_tasks))
            return result

    # ==================== 后置过滤（LLM 漏网兜底）====================

    def _post_filter(self, tasks: List[Dict]) -> List[Dict]:
        """LLM 过滤后置兜底

        LLM 可能漏掉一些明显无效的任务（如"不存在"、"zipb."等短噪声）。
        这里用规则做二次过滤，作为安全网。

        Args:
            tasks: LLM 已过滤的任务列表

        Returns:
            进一步过滤后的任务列表
        """
        noise_keywords = ['失败', '不存在', '校验通过', '校验不通过', '删除成功']
        # 条件行为描述模式（枚举项说明行，如"b.当开关开启时，调用xxx"）
        # 这些描述系统行为而非开发任务，LLM 可能漏掉，这里做规则兜底
        condition_patterns = [
            r'当\s*[\u4e00-\u9fff]+\s*时[，,]',          # "当XX时，系统做YYY"
            r'(?:不|未)\s*[\u4e00-\u9fff，,]{2,20}[，,]\s*(?:仅|只|等待|保留)',  # "不XX，仅/等待/保留"
            r'若\s*[\u4e00-\u9fff]{2,}[，,]',             # "若XX，系统做YYY"
        ]
        result = []
        for task in tasks:
            content = task.get('任务内容', '').strip()
            raw = task.get('原文片段', '') or task.get('任务来源', '')
            if not content:
                continue

            # 1. 极短内容（<=5字）且不含开发动词 → 噪声
            if len(content) <= 5:
                dev_verbs = ['新增','创建','实现','开发','配置','部署','构建',
                             '迁移','对接','集成','设计','查询','删除','更新','修改']
                has_dev = any(v in content for v in dev_verbs)
                if not has_dev:
                    continue

            # 2. 多个状态词拼接
            noise_count = sum(1 for kw in noise_keywords if kw in content)
            if noise_count >= 2:
                continue

            # 3. 条件行为描述（"当XX时"、"不XX仅XX"、"若XX"）
            #    这些是枚举项行为说明，叙述系统在什么条件下做什么
            #    不是实际开发任务，LLM 可能漏掉，此处规则兜底
            if any(re.search(p, raw) for p in condition_patterns):
                logger.debug(f"后置过滤：条件行为描述「{content[:40]}」")
                continue

            # 4. 段落概述标题（原文=内容，不含步骤标记/开发动词）
            #    如"分页查询备份记录表"这种章节概述，不是具体任务
            #    特征：原文片段与任务内容一致，且不以开发动词开头
            if self._is_section_title(content, raw):
                logger.debug(f"后置过滤：段落概述标题「{content[:40]}」")
                continue

            result.append(task)
        return result

    # ==================== LLM 分类 + 过滤 ====================

    def _classify_llm(self, tasks: List[Dict]) -> List[Dict]:
        """使用 LLM 批量分类、概括和过滤

        分批调用 LLM，每批 batch_size 条。
        过滤 valid=false 的任务。
        """
        result = []

        for batch_start in range(0, len(tasks), self.batch_size):
            batch = tasks[batch_start:batch_start + self.batch_size]
            batch_result = self._classify_batch_llm(batch, batch_start)
            before = len(batch)
            after = len(batch_result)
            if after < before:
                logger.debug(
                    f"批次 {batch_start//self.batch_size + 1}: "
                    f"过滤 {before - after} 条无效任务"
                )
            result.extend(batch_result)

        return result

    # ==================== Prompt 构建 ====================

    def _build_prompt(self, batch: List[Dict], start_idx: int) -> str:
        """构建 LLM prompt

        Args:
            batch: 一批任务
            start_idx: 在原始列表中的起始序号

        Returns:
            LLM prompt 字符串
        """
        prompt_template = self.config.get(
            'llm_prompt',
            _get_default_config()['llm_prompt']
        )

        # 构建类型列表
        type_list = '\n'.join(
            f"  - {t['id']}: {t['description']}"
            for t in self.config.get('types', [])
        )

        # 构建任务序号列表（从 1 开始）
        task_lines = []
        for i, task in enumerate(batch):
            idx = start_idx + i
            content = task.get('任务内容', '').strip()
            source = task.get('任务来源', '')
            # 摘取来源章节信息
            section = source.split('|')[0].strip() if source else '未知'
            # 原文片段
            raw = task.get('原文片段', '')
            task_lines.append(
                f"{idx + 1}. 任务内容：{content}\n"
                f"   来源章节：{section}\n"
                f"   原文：{raw}"
            )

        task_list = '\n\n'.join(task_lines)

        return prompt_template.format(
            type_count=len(self.config.get('types', [])),
            type_list=type_list,
            task_list=task_list
        )

    # ==================== LLM 调用 ====================

    def _call_llm(self, prompt: str) -> Optional[str]:
        """调用 LLM

        先尝试 Gateway API，失败后尝试直连 DeepSeek API。

        Args:
            prompt: 完整 prompt

        Returns:
            LLM 响应文本，失败返回 None
        """
        # 优先尝试 Gateway
        response = self._call_via_gateway(prompt)
        if response:
            return response

        # Gateway 失败，尝试直连 DeepSeek
        response = self._call_via_api(prompt)
        return response

    def _call_via_gateway(self, prompt: str) -> Optional[str]:
        """通过 Gateway 调用 LLM

        Args:
            prompt: 完整 prompt

        Returns:
            LLM 响应文本，失败返回 None
        """
        try:
            import json
            import urllib.request
            import os

            gateway_url = os.environ.get(
                'OPENCLAW_GATEWAY_URL',
                'http://localhost:17999'
            )
            data = json.dumps({
                'model': self.model,
                'messages': [
                    {'role': 'system', 'content': '你是一个经验丰富的软件工程师，负责分析技术方案文档，准确理解任务内容和类型。'},
                    {'role': 'user', 'content': prompt},
                ],
                'temperature': 0.1,
                'max_tokens': 8192,
            }).encode('utf-8')
            req = urllib.request.Request(
                f'{gateway_url}/v1/chat/completions',
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            import ssl
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=180, context=ctx) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result['choices'][0]['message']['content']
        except Exception as e:
            logger.debug(f"Gateway 调用失败: {e}")
            return None

    def _call_via_api(self, prompt: str) -> Optional[str]:
        """直接调用 API（从配置读取 key）

        Args:
            prompt: 完整 prompt

        Returns:
            LLM 响应文本，失败返回 None
        """
        try:
            import json
            import urllib.request
            import os

            # 从配置中读取 API key
            config_path = os.path.expanduser('~/.openclaw/openclaw.json')
            api_key = None
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                # models.providers.xxx.apiKey
                providers = config.get('models', {}).get('providers', {})
                for pname in ('deepseek', 'dashscope', 'openai'):
                    provider = providers.get(pname, {})
                    for k in ('apiKey', 'api_key', 'key'):
                        val = provider.get(k, '')
                        if val and val.startswith('sk-'):
                            api_key = val
                            break
                    if api_key:
                        break

            if not api_key:
                logger.error('未找到 API key 配置')
                return None

            # 使用 DeepSeek API
            url = 'https://api.deepseek.com/chat/completions'
            model = 'deepseek-chat'

            data = json.dumps({
                'model': model,
                'messages': [
                    {'role': 'system', 'content': '你是一个经验丰富的软件工程师，负责分析技术方案文档，准确理解任务内容和类型。返回严格的 JSON 格式。'},
                    {'role': 'user', 'content': prompt},
                ],
                'temperature': 0.1,
                'max_tokens': 8192,
            }).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}',
                },
                method='POST',
            )
            import ssl
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=180, context=ctx) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"API 调用失败: {e}")
            return None

    # ==================== 响应解析 ====================

    def _parse_llm_response(
        self, response: str, batch_size: int
    ) -> Dict[str, Dict]:
        """解析 LLM 返回的 JSON

        新格式：{"1": {"valid": true, "type": "接口任务", "summary": "新增用户查询接口"}, ...}
        兼容旧格式：{"1": {"type": "接口任务", "summary": ...}}（没有 valid 字段）
                或 {"1": "接口任务", ...}（仅返回类型）

        Returns:
            {序号: {"valid": bool, "type": 类型, "summary": 概括内容}}
            valid 默认为 True（旧格式兼容）
        """
        # 提取 JSON 部分
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            raise ValueError(f"未找到 JSON 响应: {response[:200]}")

        text = json_match.group(0)

        # 尝试解析
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            # 尝试修复常见的格式问题
            text = text.replace("'", '"')  # 单引号 → 双引号
            text = re.sub(r',\s*([}\]])', r'\1', text)  # 去掉尾随逗号
            result = json.loads(text)

        # 验证并统一格式
        valid_result = {}
        for key, value in result.items():
            key_str = str(key).strip()

            if isinstance(value, dict):
                # 新格式：{"valid": bool, "type": "...", "summary": "..."}
                # 或旧格式：{"type": "...", "summary": "..."}
                is_valid = value.get('valid', True)  # 默认 True（兼容旧格式）
                if isinstance(is_valid, bool):
                    valid_result[key_str] = {'valid': is_valid}
                else:
                    valid_result[key_str] = {'valid': True}

                if is_valid:
                    task_type = value.get('type', '')
                    summary = value.get('summary', '')
                    if task_type not in self.type_ids:
                        if task_type:
                            logger.warning(f"非法类型 '{task_type}' 在序号 {key_str}，标记为'功能任务'")
                        task_type = '功能任务'
                    valid_result[key_str]['type'] = task_type
                    valid_result[key_str]['summary'] = summary or ''
                else:
                    valid_result[key_str]['type'] = ''
                    valid_result[key_str]['summary'] = ''
            elif isinstance(value, str):
                # 旧格式兼容：直接是类型名称
                if value in self.type_ids:
                    valid_result[key_str] = {'valid': True, 'type': value, 'summary': ''}
                else:
                    logger.warning(f"非法类型 '{value}' 在序号 {key_str}，标记为'功能任务'")
                    valid_result[key_str] = {'valid': True, 'type': '功能任务', 'summary': ''}
            else:
                logger.warning(f"非法格式 '{value}' 在序号 {key_str}，标记为有效任务")
                valid_result[key_str] = {'valid': True, 'type': '功能任务', 'summary': ''}

        return valid_result

    # ==================== 批量分类 ====================

    def _classify_batch_llm(
        self, batch: List[Dict], start_idx: int
    ) -> List[Dict]:
        """对一批任务进行 LLM 分类、概括和有效性过滤

        失败时自适应拆分为更小的子批重试，避免直接回退到不过滤的 fallback。
        核心策略：大批次 → 小批次 → 更小批次 → 规则过滤。
        """
        result = self._classify_batch_with_retry(batch, start_idx)
        return result

    def _classify_batch_with_retry(
        self, batch: List[Dict], start_idx: int, depth: int = 0
    ) -> List[Dict]:
        """递归分类，失败时自动拆分为更小的子批

        Args:
            batch: 一批任务
            start_idx: 起始序号
            depth: 递归深度（每次 +1，最大 2 层）

        Returns:
            分类过滤后的任务列表
        """
        prompt = self._build_prompt(batch, start_idx)
        response = self._call_llm(prompt)

        # 失败重试一次
        if not response:
            logger.warning(
                f"批次 {start_idx//max(self.batch_size,1) + 1} "
                f"LLM 首次调用失败{'（递归深度 '+str(depth)+'）' if depth > 0 else ''}，重试..."
            )
            response = self._call_llm(prompt)

        if not response:
            if depth < 2 and len(batch) >= 4:
                # 自适应拆分：切成两半，分别递归分类
                mid = len(batch) // 2
                logger.warning(
                    f"LLM 重试仍失败，拆分为 2 个子批（{len(batch[:mid])}+{len(batch[mid:])} 条）"
                )
                left = self._classify_batch_with_retry(batch[:mid], start_idx, depth + 1)
                right = self._classify_batch_with_retry(batch[mid:], start_idx + mid, depth + 1)
                return left + right
            else:
                logger.warning("LLM 递归重试仍无响应，该批回退到关键词匹配（基本过滤）")
                return self._classify_fallback(batch)

        parsed = self._parse_llm_response(response, len(batch))

        result = []
        filtered = 0
        valid_items = []  # 收集有效条目用于日志
        for i, task in enumerate(batch):
            key = str(i + 1)
            entry = parsed.get(key, {'valid': True, 'type': '功能任务', 'summary': ''})

            # 有效性过滤：valid=false 的任务跳过
            if not entry.get('valid', True):
                filtered += 1
                content_preview = task.get('任务内容', '')[:50]
                logger.debug(f"过滤无效任务：{content_preview}")
                continue

            task = dict(task)  # 浅拷贝，不修改原对象
            task['任务类型'] = entry.get('type', '功能任务')
            # 如果 LLM 返回了概括内容，替换任务内容
            entry_type = entry.get('type', '功能任务')
            entry_summary = entry.get('summary', '').strip()
            task['任务类型'] = entry_type
            if entry_summary:
                task['任务内容'] = entry_summary
            result.append(task)
            valid_items.append(task)

        if filtered > 0:
            logger.info(f"过滤 {filtered} 条无效任务")

        return result

    # ==================== 回退分类 ====================

    def _classify_fallback(self, tasks: List[Dict]) -> List[Dict]:
        """LLM 不可用时使用关键词回退

        不过滤，全部保留。内容按句号分句保留第一句。
        增加基本过滤：短内容（<5字）或无动词的纯状态词标记为无效。

        Args:
            tasks: 任务列表

        Returns:
            过滤后的任务列表
        """
        result = []
        for task in tasks:
            content = task.get('任务内容', '').strip()

            # 基本过滤：短内容或无动词的纯状态词
            if content:
                # 极短内容（<=5字）且不包含开发动词 → 过滤
                if len(content) <= 5:
                    dev_verbs = ['新增','创建','实现','开发','配置','部署','构建','迁移',
                                 '对接','集成','设计','查询','删除','更新','修改']
                    has_dev = any(v in content for v in dev_verbs)
                    if not has_dev:
                        continue

                # 纯状态描述（"读取失败文件不存在解析失败查询失败"类噪声）
                noise_keywords = ['失败', '不存在', '校验通过', '校验不通过', '删除成功']
                noise_count = sum(1 for kw in noise_keywords if kw in content)
                if noise_count >= 2:
                    # 多个状态词拼接，无完整语义
                    continue

                # "开始 X" 开头 → 步骤启动标记，不是任务
                if content.startswith('开始 '):
                    continue

            task = dict(task)  # 浅拷贝
            task['任务类型'] = self._infer_by_keywords(task)

            # 内容概括：按句号分句保留第一句
            if content and '。' in content:
                first_sentence = content.split('。')[0].strip()
                if first_sentence:
                    task['任务内容'] = first_sentence
            result.append(task)
        return result

    def _infer_by_keywords(self, task: Dict) -> str:
        """通过关键词推断任务类型

        Args:
            task: 任务字典

        Returns:
            推断的任务类型名称，默认 '功能任务'
        """
        content = task.get('任务内容', '')
        if not content:
            return '功能任务'

        content_lower = content.lower()
        scores = {}
        for type_name, keywords in self.fallback_keywords.items():
            score = 0
            for kw in keywords:
                if kw in content or kw.lower() in content_lower:
                    score += 1
            if score > 0:
                scores[type_name] = score

        if scores:
            return max(scores, key=scores.get)
        return '功能任务'

    def _is_section_title(self, content: str, raw: str) -> bool:
        """判断是否为段落概述标题

        特征：
        - 原文片段与任务内容基本一致（不是从复合行中提取的子句）
        - 不以开发动词开头
        - 不含步骤标记（"第N步"）
        - 不含 API 路径标记（POST/GET 等）

        Args:
            content: 任务内容
            raw: 原文片段

        Returns:
            是否为段落概述标题
        """
        # 开发动词开头
        dev_start_verbs = ['新增','创建','实现','开发','配置','部署','构建',
                           '迁移','对接','集成','设计','查询','删除','更新',
                           '修改','提供','接入','编写','搭建','生成','同步',
                           '导入','导出','上传','下载','调用','发起']
        # 条件：内容与原文几乎一致（至少 80% 重叠）
        if len(content) >= 4 and raw.strip():
            # 计算重叠度：内容是否被原文包含，且原文不包含额外开发标记
            if content in raw and abs(len(content) - len(raw.strip())) <= 20:
                # 不含步骤标记
                if re.search(r'第\s*\d+\s*步', raw):
                    return False
                # 不含 API 路径
                if re.search(r'(?:POST|GET|PUT|DELETE|PATCH)\s+/', raw):
                    return False
                # 不以开发动词开头
                if any(content.startswith(v) for v in dev_start_verbs):
                    return False
                # 有明确的条件前缀（a.b.c.d. 等枚举标记）-> 可能是任务
                if re.match(r'^[a-zA-Z][\.\)、]\s*', raw):
                    return False
                return True
        return False

    def get_statistics(self, tasks: List[Dict]) -> Dict[str, int]:
        """获取任务类型统计

        Args:
            tasks: 任务列表

        Returns:
            {类型名称: 数量}
        """
        stats: Dict[str, int] = {}
        for task in tasks:
            t = task.get('任务类型', '功能任务')
            stats[t] = stats.get(t, 0) + 1
        return stats

    def _deduplicate(self, tasks: List[Dict]) -> List[Dict]:
        """LLM 概括后去重：同一模块下内容完全相同的任务只保留第一个"""
        seen: Dict[str, Set[str]] = {}
        result = []
        for task in tasks:
            module = task.get('任务模块', '')
            content = task.get('任务内容', '').strip()
            if not content:
                result.append(task)
                continue
            if module not in seen:
                seen[module] = set()
            if content in seen[module]:
                logger.debug(f"去重：模块'{module[:20]}'中内容相同「{content[:30]}」")
                continue
            seen[module].add(content)
            result.append(task)
        return result


def test():
    """独立测试"""
    logging.basicConfig(level=logging.DEBUG)
    print("=" * 60)
    print("TypeClassifier 独立测试")
    print("=" * 60)

    # 加载配置
    config = load_type_config()
    print(f"\n✅ 加载 {len(config.get('types', []))} 种任务类型")

    # 测试数据
    test_tasks = [
        {
            '任务内容': '查询数据库备份开关状态',
            '任务来源': '1.2.1 备份开关状态',
            '原文片段': '从algorithm_open_claw_user表查询backup_flag字段',
        },
        {
            '任务内容': 'POST更新MClaw备份开关接口',
            '任务来源': '1.2.1 备份开关状态',
            '原文片段': '[backupFlag=0（关闭）]POST更新MClaw备份开关接口',
        },
        {
            '任务内容': '提供备份开关的开启/关闭功能',
            '任务来源': '1.2.1 备份开关状态',
            '原文片段': '提供备份开关的开启/关闭功能',
        },
        {
            '任务内容': '新增接口：学习成果管理接口',
            '任务来源': '2.1 接口设计',
            '原文片段': '新增接口：学习成果管理接口',
        },
        {
            '任务内容': '旧积分升级提示弹窗',
            '任务来源': '2.1 接口设计',
            '原文片段': '旧积分升级提示弹窗',
        },
    ]

    # 实例化分类器
    classifier = TypeClassifier()

    # 测试关键词回退
    print("\n\n🔄 测试关键词回退...")
    fallback_result = classifier._classify_fallback(test_tasks)
    for i, task in enumerate(fallback_result):
        print(f"  [{i+1}] {task['任务内容'][:40]:<42} → {task.get('任务类型', '功能任务')}")
    print(f"  \n📊 类型统计: {classifier.get_statistics(fallback_result)}")

    # 测试 LLM 分类
    print("\n\n🔄 测试 LLM 分类...")
    try:
        result = classifier.classify(test_tasks)
        for i, task in enumerate(result):
            print(
                f"  [{i+1}] {task['任务内容'][:40]:<42} → "
                f"{task.get('任务类型', '功能任务')}"
            )
        print(f"\n✅ LLM 分类成功")
    except Exception as e:
        print(f"\n⚠️ LLM 分类失败: {e}")
        print("  回退到关键词分类...")
        result = classifier._classify_fallback(test_tasks)
        for i, task in enumerate(result):
            print(
                f"  [{i+1}] {task['任务内容'][:40]:<42} → "
                f"{task.get('任务类型', '功能任务')}"
            )

    # 测试统计
    stats = classifier.get_statistics(result)
    print(f"\n📊 类型统计: {stats}")

    print("\n✅ 测试完成")
    return 0


if __name__ == '__main__':
    sys.exit(test())
