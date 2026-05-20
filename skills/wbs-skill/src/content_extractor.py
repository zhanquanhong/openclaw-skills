"""内容提取引擎 - v4.0

从来源原文中提取标准化任务内容。

核心能力：
1. 去除冗余前缀（"需要"、"我们要"）
2. 截断过长句子（保留动词 + 宾语，截断修饰语）
3. 提取接口路径（POST/GET/PUT/DELETE + URL）
4. 任务类型自动标注（接口/数据库/配置/中间件/功能）
5. 去重检查（与已有任务对比）

使用方式：
    extractor = ContentExtractor()
    result = extractor.extract(source_info)
    print(result.content)  # "新增用户列表查询接口"
    print(result.task_type)  # "接口任务"
"""

import re
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Set

from src.source_locator import SourceInfo

logger = logging.getLogger(__name__)


@dataclass
class TaskContent:
    """提取后的任务内容

    Attributes:
        content: 标准化任务内容
        task_type: 任务类型
        has_api_path: 是否包含 API 路径
        api_path: API 路径（如果有）
        api_method: HTTP 方法（如果有）
    """
    content: str
    task_type: str = "功能任务"
    has_api_path: bool = False
    api_path: str = ""
    api_method: str = ""

    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "task_type": self.task_type,
            "has_api_path": self.has_api_path,
            "api_path": self.api_path,
            "api_method": self.api_method,
        }


class ContentExtractor:
    """内容提取引擎

    从来源原文中提取标准化任务内容。
    """

    # 冗余前缀（需要去除）
    # 注意：较长模式必须排在较短模式前面，避免部分匹配
    REDUNDANT_PREFIXES = [
        r'^需要\s*',
        r'^我们要\s*',
        r'^我们需要\s*',
        r'^计划\s*',
        r'^准备\s*',
        r'^将会\s*',
        r'^负责\s*',
        r'^完成\s*',
        r'^实现\s*一个\s*',
        r'^新增\s*一个\s*',
        r'^开发\s*一个\s*',
        r'^提供\s*一个\s*',
        # 单字前缀放在最后，且后面加负向 lookahead 避免误伤复合词
        r'^应(?!用|该)\s*',
        r'^需(?!求)\s*',
    ]

    # 截断关键词（遇到这些词时截断后面的内容）
    TRUNCATE_KEYWORDS = [
        '，支持', ',支持', '，包括', ',包括', '，包含', ',包含',
        '，确保', ',确保', '，保证', ',保证', '，实现', ',实现',
        '，提供', ',提供', '，采用', ',采用', '，使用', ',使用',
        '，基于', ',基于', '，通过', ',通过', '，以及', ',以及',
        '，并且', ',并且', '，同时', ',同时', '，此外', ',此外',
        '；支持', ';支持', '；包括', ';包括',
    ]

    # 任务类型关键词
    TASK_TYPE_KEYWORDS = {
        '接口任务': ['接口', 'API', 'POST', 'GET', 'PUT', 'DELETE', 'PATCH', 'endpoint', 'http'],
        '数据库任务': ['表', '字段', '索引', 'SQL', '数据库', 'DDL', '建表', 'ALTER', 'CREATE TABLE'],
        '配置任务': ['配置', '设置', '参数', 'config', 'settings', '环境变量'],
        '中间件任务': ['缓存', 'Redis', '队列', 'RabbitMQ', 'Kafka', 'MQ', '定时任务', 'Cron', '消息'],
        '前端任务': ['前端', '页面', 'UI', '组件', '交互', '样式', 'CSS', 'Vue', 'React'],
        '算法任务': ['算法', '模型', '训练', '推理', 'embedding', '相似度', '向量'],
    }

    # 截断长度阈值
    MAX_CONTENT_LENGTH = 45

    def __init__(self, seen_contents: Optional[Set[str]] = None):
        """初始化

        Args:
            seen_contents: 已存在的任务内容集合（用于去重）
        """
        self.seen_contents: Set[str] = seen_contents or set()

    def extract(self, source: SourceInfo) -> Optional[TaskContent]:
        """从来源信息中提取任务内容

        Args:
            source: 来源定位信息

        Returns:
            任务内容，如果无法提取则返回 None
        """
        raw = source.raw_text.strip()
        if not raw or len(raw) < 4:
            return None

        # Step 0: 清理 PDF 控制字符（\x01-\x08 等）
        raw = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw)

        # Step 1: 去除冗余前缀
        content = self._remove_redundant_prefix(raw)

        # Step 2: 截断过长句子
        content = self._truncate_long_sentence(content)

        # Step 3: 清理多余空格和符号
        content = self._clean_content(content)

        # Step 3.5: 保留中文常见任务句式
        content = self._keep_task_sentences(content)

        if not content or len(content) < 3:
            return None

        # Step 4: 提取 API 路径
        api_info = self._extract_api_path(raw)

        # Step 5: 判断任务类型
        task_type = self._infer_task_type(content, raw)

        # Step 6: 去重检查
        if self._is_duplicate(content):
            logger.debug(f"重复任务内容：{content}")
            return None

        # 记录已见内容
        self.seen_contents.add(content)

        # 如果有 API 路径，追加到内容中
        if api_info['has_path']:
            content = self._append_api_path(content, api_info)

        return TaskContent(
            content=content,
            task_type=task_type,
            has_api_path=api_info['has_path'],
            api_path=api_info['path'],
            api_method=api_info['method'],
        )

    def _remove_redundant_prefix(self, text: str) -> str:
        """去除冗余前缀

        Args:
            text: 原始文本

        Returns:
            去除前缀后的文本
        """
        # 符号类前缀（列表符号、箭头等）
        text = re.sub(r'^[◦•●○■□◆▲▶▪▫➤➢►→·]\s*', '', text)

        # 编号类（a. A. i. ii. 1、 1.）
        text = re.sub(r'^[a-zA-Z][\.\)\u3001]\s*', '', text)
        text = re.sub(r'^[ivxIVX]+[\.\)\u3001]\s*', '', text)
        text = re.sub(r'^\d+[、\.]\s*', '', text)

        # 步骤类
        text = re.sub(r'^第\s*\d+\s*步[：:]\s*', '', text)
        text = re.sub(r'^Step\s*\d+[：:.\s]\s*', '', text)

        # 标记类【1】(1) [1]
        text = re.sub(r'^[【\[\(〔〈]\d+[】\]\)〕〉]\s*', '', text)

        # 原有冗余前缀
        for pattern in self.REDUNDANT_PREFIXES:
            text = re.sub(pattern, '', text, count=1)

        # 新增：罗马编号 + 中文编号混合 (一.1. 一、1.1)
        text = re.sub(r'^[一二三四五六七八九十]+[、\.]\s*\d+[、\.]\s*', '', text)

        # 去除【新增】【更新】等括号标记（必须有括号才去）
        text = re.sub(r'^[【\[〈<](?:新增|更新|删除|修改|优化|重构)[】\]〉>]\s*', '', text)

        # 去除编号标记（补充：字母+点）
        text = re.sub(r'^[a-z]\.\s*', '', text)

        return text.strip()

    def _truncate_long_sentence(self, text: str) -> str:
        """截断过长句子

        策略：
        1. 遇到截断关键词时截断
        2. 超过最大长度时按逗号/分号截断

        Args:
            text: 文本

        Returns:
            截断后的文本
        """
        # 策略 1：截断关键词
        for kw in self.TRUNCATE_KEYWORDS:
            idx = text.find(kw)
            if idx > 0:
                text = text[:idx].rstrip('，,；; ')
                break

        # 策略 2：按逗号/分号截断（如果仍然过长）
        if len(text) > self.MAX_CONTENT_LENGTH:
            # 尝试在第一个逗号/分号处截断
            for sep in ['，', ',', '；', ';']:
                idx = text.find(sep)
                if 0 < idx < self.MAX_CONTENT_LENGTH:
                    text = text[:idx]
                    break

            # 如果还是太长，直接截断
            if len(text) > self.MAX_CONTENT_LENGTH:
                text = text[:self.MAX_CONTENT_LENGTH].rstrip('，,；; ')

        return text.strip()

    def _clean_content(self, text: str) -> str:
        """清理多余空格和符号

        Args:
            text: 文本

        Returns:
            清理后的文本
        """
        # 去除多余空格
        text = re.sub(r'\s+', ' ', text).strip()

        # 去除开头/结尾的标点
        text = text.strip('，,。；;：:、！!？?')

        # 去除 → 及其后面的内容（接口路径单独处理）
        if '→' in text:
            text = text.split('→')[0].strip()

        # 去除末尾的标点
        text = text.strip('，,。；;：:、！!？?')

        return text

    def _keep_task_sentences(self, content: str) -> str:
        """保留中文常见任务句式，防止误杀

        以下句式的行通常是任务描述，不应被误杀：
        - "对XXX进行YYY"
        - "通过XXX实现YYY"
        - "基于XXX提供YYY"
        - "支持XXX功能"

        Args:
            content: 清理后的内容

        Returns:
            保留的任务内容
        """
        # 这些句式通常是有效的任务描述，确保不被截断误杀
        keep_patterns = [
            r'对.+(?:进行|实现|提供|配置|设置|修改|更新|删除|新增)',
            r'通过.+(?:实现|提供|支持|完成|达到)',
            r'基于.+(?:提供|实现|支持|设计|开发)',
            r'支持.+(?:功能|接口|能力|配置|查询|搜索|导出|导入)',
        ]
        for pattern in keep_patterns:
            if re.search(pattern, content):
                return content
        return content

    def _extract_api_path(self, text: str) -> Dict:
        """从文本中提取 API 路径

        Args:
            text: 原始文本

        Returns:
            {"has_path": bool, "method": str, "path": str}
        """
        # 匹配：(POST /api/xxx) — 优先匹配括号内，排除 ) 结尾
        match = re.search(r'\((POST|GET|PUT|DELETE|PATCH)\s+(/[^)\s]+)\)', text)
        if match:
            return {
                'has_path': True,
                'method': match.group(1),
                'path': match.group(2),
            }

        # 匹配：POST /api/xxx — 路径不含空格、括号、箭头、右括号、分号、引号
        match = re.search(r'(?:^|[\s(])(POST|GET|PUT|DELETE|PATCH)\s+(/[^\s)→,，;；""]+)', text)
        if match:
            return {
                'has_path': True,
                'method': match.group(1),
                'path': match.group(2),
            }

        # 匹配纯路径
        match = re.search(r'(/\w[\w/\-{}]+)', text)
        if match:
            return {
                'has_path': True,
                'method': '',
                'path': match.group(1),
            }

        return {'has_path': False, 'method': '', 'path': ''}

    def _infer_task_type(self, content: str, raw: str) -> str:
        """推断任务类型

        Args:
            content: 提取后的内容
            raw: 原始文本

        Returns:
            任务类型
        """
        combined = f"{content} {raw}".lower()

        for task_type, keywords in self.TASK_TYPE_KEYWORDS.items():
            if any(kw.lower() in combined for kw in keywords):
                return task_type

        return "功能任务"

    def _is_duplicate(self, content: str) -> bool:
        """去重检查

        去重策略：
        1. 完全相同
        2. 包含关系（短内容在长内容中）
        3. 编辑距离 ≤ 3（短内容）

        Args:
            content: 任务内容

        Returns:
            是否为重复
        """
        # 策略 1：完全相同
        if content in self.seen_contents:
            return True

        for seen in self.seen_contents:
            # 策略 2：包含关系
            if content in seen or seen in content:
                return True

            # 策略 3：编辑距离（仅当内容很短时，阈值 1）
            if len(content) <= 10 and len(seen) <= 10:
                if self._edit_distance(content, seen) <= 1:
                    return True

        return False

    def _append_api_path(self, content: str, api_info: Dict) -> str:
        """将 API 路径追加到内容中

        Args:
            content: 任务内容
            api_info: API 信息

        Returns:
            追加后的内容
        """
        method = api_info['method']
        path = api_info['path']

        if method:
            return f"{content} ({method} {path})"
        return f"{content} ({path})"

    @staticmethod
    def _edit_distance(s1: str, s2: str) -> int:
        """计算编辑距离（简化版）

        Args:
            s1: 字符串 1
            s2: 字符串 2

        Returns:
            编辑距离
        """
        if len(s1) > len(s2):
            s1, s2 = s2, s1

        distances = range(len(s1) + 1)
        for i2, c2 in enumerate(s2):
            distances_ = [i2 + 1]
            for i1, c1 in enumerate(s1):
                if c1 == c2:
                    distances_.append(distances[i1])
                else:
                    distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
            distances = distances_
        return distances[-1]