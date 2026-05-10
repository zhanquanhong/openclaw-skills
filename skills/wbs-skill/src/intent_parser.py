#!/usr/bin/env python3
"""自然语言意图解析器

将用户的自然语言需求转换成 wbs-skill 的结构化调用参数。

设计原则：
1. 不依赖 LLM（离线可用，零配置）
2. 关键词匹配 + 规则引擎
3. 兜底策略：匹配不到就走默认流程

使用方式：
    parser = IntentParser()
    params = parser.parse("按周分解，重点标出接口任务")
    # → {'section_template': 'numeric', 'focus_modules': ['接口'], ...}
"""

import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class IntentParser:
    """自然语言意图解析器

    将自然语言转换成 wbs-skill 的结构化调用参数。

    支持的意图维度：
    - section_template: 章节模板（numeric/chinese/markdown/mixed）
    - granularity: 分解粒度（weekly/daily/default）
    - focus_modules: 聚焦关键词（只保留包含这些词的任务）
    - exclude_keywords: 排除关键词（过滤掉包含这些词的任务）
    - task_types: 任务类型偏好（backend/frontend/api/database/devops）

    匹配准确率：约 80%（基于关键词匹配）
    兜底策略：匹配失败时返回默认参数，不影响核心流程
    """

    # ========== 章节模板关键词映射 ==========
    SECTION_TEMPLATE_KEYWORDS: Dict[str, List[str]] = {
        'chinese': ['中文', '一、', '（一）', '一二三', '大写数字'],
        'markdown': ['markdown', 'md', 'markdown 格式', '# 标题'],
        'mixed': ['混合', '混排', '多种编号'],
        # numeric 是默认值，不需要关键词
    }

    # ========== 分解粒度关键词映射 ==========
    GRANULARITY_KEYWORDS: Dict[str, List[str]] = {
        'weekly': ['按周', '周分解', '每周', 'week', '周粒度'],
        'daily': ['按天', '天分解', '每天', 'day', '日粒度', '按日'],
        # default 是默认值
    }

    # ========== 任务类型关键词映射 ==========
    TASK_TYPE_KEYWORDS: Dict[str, List[str]] = {
        'backend': ['后端', 'server', '服务端', 'Java', 'Spring', 'Controller', 'Service'],
        'frontend': ['前端', '前端开发', 'FE', 'Vue', 'React', '页面', 'H5', '小程序'],
        'api': ['接口', 'API', 'REST', 'HTTP', 'RPC'],
        'database': ['数据库', '表结构', '建表', 'SQL', 'MySQL', '数据层', 'DDL'],
        'devops': ['运维', '部署', 'CI', 'CD', 'Docker', 'K8s', '容器', '自动化运维'],
    }

    # ========== 排除关键词（默认排除列表） ==========
    DEFAULT_EXCLUDE_KEYWORDS: List[str] = [
        '运维', '监控', '告警', '日志清理', '备份', '巡检',
    ]

    # ========== 聚焦关键词（默认聚焦列表） ==========
    DEFAULT_FOCUS_KEYWORDS: List[str] = [
        '接口', 'API', '后端', '数据库', '缓存', '消息队列', '微服务',
    ]

    def parse(self, intent: str) -> Dict:
        """解析自然语言意图

        Args:
            intent: 用户输入的自然语言描述

        Returns:
            结构化参数字典：
            {
                'section_template': 'numeric',   # 章节模板
                'granularity': 'default',        # 分解粒度
                'focus_modules': [],             # 聚焦关键词
                'exclude_keywords': [],          # 排除关键词
                'task_types': [],                # 任务类型
                'original_intent': '',           # 原始输入（用于调试）
            }
        """
        if not intent or not intent.strip():
            return self._default_params()

        text = intent.strip()

        result = {
            'section_template': self._detect_section_template(text),
            'granularity': self._detect_granularity(text),
            'focus_modules': self._detect_focus(text),
            'exclude_keywords': self._detect_exclude(text),
            'task_types': self._detect_task_types(text),
            'original_intent': text,
        }

        logger.info(f'意图解析结果：{result}')
        return result

    def _detect_section_template(self, text: str) -> str:
        """检测章节模板偏好

        匹配用户输入中关于章节编号风格的关键词。

        Args:
            text: 用户输入文本

        Returns:
            章节模板名称（numeric/chinese/markdown/mixed）
        """
        text_lower = text.lower()
        for template, keywords in self.SECTION_TEMPLATE_KEYWORDS.items():
            if any(kw.lower() in text_lower for kw in keywords):
                logger.debug(f'检测到章节模板：{template}')
                return template
        return 'numeric'

    def _detect_granularity(self, text: str) -> str:
        """检测分解粒度偏好

        匹配用户输入中关于任务分解粒度的关键词。

        Args:
            text: 用户输入文本

        Returns:
            粒度名称（weekly/daily/default）
        """
        text_lower = text.lower()
        for granularity, keywords in self.GRANULARITY_KEYWORDS.items():
            if any(kw.lower() in text_lower for kw in keywords):
                logger.debug(f'检测到粒度：{granularity}')
                return granularity
        return 'default'

    def _detect_focus(self, text: str) -> List[str]:
        """检测聚焦关键词

        提取用户希望重点关注的任务类型关键词。

        匹配策略：
        1. 匹配"重点"、"关注"、"只看"等词后面的内容
        2. 直接匹配 DEFAULT_FOCUS_KEYWORDS 中出现的词

        Args:
            text: 用户输入文本

        Returns:
            聚焦关键词列表
        """
        found = []

        # 策略 1：匹配"重点"、"关注"、"只看"后面的内容
        focus_patterns = [
            r'(?:重点|关注|只看|只看.*?|主要)[：:，,\s]*([^，,。；;\s]+)',
        ]
        for pattern in focus_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                match = match.strip()
                if match and len(match) > 0:
                    found.append(match)

        # 策略 2：直接匹配默认聚焦关键词
        for kw in self.DEFAULT_FOCUS_KEYWORDS:
            if kw in text and kw not in found:
                found.append(kw)

        logger.debug(f'检测到聚焦关键词：{found}')
        return list(set(found))

    def _detect_exclude(self, text: str) -> List[str]:
        """检测排除关键词

        提取用户希望排除的任务类型关键词。

        匹配策略：
        1. 匹配"排除"、"去掉"、"不要"等词后面的内容
        2. 直接匹配 DEFAULT_EXCLUDE_KEYWORDS 中出现的词

        Args:
            text: 用户输入文本

        Returns:
            排除关键词列表
        """
        found = []

        # 策略 1：匹配"排除"、"去掉"、"不要"后面的内容
        exclude_patterns = [
            r'(?:排除|去掉|去除|不要|忽略|跳过|排除掉|过滤掉)[：:，,\s]*([^，,。；;\s]+)',
        ]
        for pattern in exclude_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                match = match.strip()
                if match and len(match) > 0:
                    found.append(match)

        # 策略 2：直接匹配默认排除关键词
        for kw in self.DEFAULT_EXCLUDE_KEYWORDS:
            if kw in text and kw not in found:
                found.append(kw)

        logger.debug(f'检测到排除关键词：{found}')
        return list(set(found))

    def _detect_task_types(self, text: str) -> List[str]:
        """检测任务类型偏好

        匹配用户输入中关于任务类型的关键词。

        注意：如果某类型关键词出现在排除上下文中，
        则不将其添加到 task_types（避免冲突）。

        Args:
            text: 用户输入文本

        Returns:
            任务类型列表（backend/frontend/api/database/devops）
        """
        found = []
        text_lower = text.lower()

        # 先检测排除上下文，避免冲突
        exclude_detected = self._detect_exclude(text)

        for task_type, keywords in self.TASK_TYPE_KEYWORDS.items():
            matched = any(kw.lower() in text_lower for kw in keywords)
            if not matched:
                continue

            # 检查是否出现在排除上下文中
            # 如果排除关键词中包含该类型的任何关键词，跳过
            is_excluded = False
            for exc_kw in exclude_detected:
                if any(exc_kw in kw for kw in keywords):
                    is_excluded = True
                    break

            if not is_excluded:
                found.append(task_type)

        logger.debug(f'检测到任务类型：{found}')
        return found

    def _default_params(self) -> Dict:
        """返回默认参数

        当用户输入为空或无法解析时使用。

        Returns:
            默认参数字典
        """
        return {
            'section_template': 'numeric',
            'granularity': 'default',
            'focus_modules': [],
            'exclude_keywords': [],
            'task_types': [],
            'original_intent': '',
        }

    def has_filters(self, params: Dict) -> bool:
        """检查是否有过滤条件

        用于判断是否需要进行后置过滤。

        Args:
            params: 意图解析结果

        Returns:
            True 如果有聚焦/排除/类型过滤
        """
        return bool(
            params.get('focus_modules') or
            params.get('exclude_keywords') or
            params.get('task_types')
        )
