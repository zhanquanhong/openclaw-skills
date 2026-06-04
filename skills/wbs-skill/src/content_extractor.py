"""内容提取引擎 - v4.1.1

从来源原文中提取标准化任务内容。

核心能力：
1. 去除冗余前缀（"需要"、"我们要"）
2. 按句号分句保留第一句（离线兜底；在线时由 LLM 做语义概括）
3. 提取接口路径（POST/GET/PUT/DELETE + URL）
4. 去重检查（与已有任务对比）

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

    # 复合行拆分模式
    # 1. 包含 ；第N步：的复合行 → 步骤续行
    # 2. 包含 ；[a-z]. 的复合行 → 枚举续行（如"；c.后续内容"）
    COMPOUND_STEP_PATTERN = re.compile(r'[；;]\s*第\s*\d+\s*步[：:]')
    COMPOUND_ENUM_PATTERN = re.compile(r'[；;]\s*[a-z]\.\s*')

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

        # Step 5.5: 识别步骤标题（原始行以 第N步 开头，跳过包含关系去重）
        is_step_title = bool(re.match(r'^第[0-9一二三四五六七八九十百]+[步、]', raw))

        # Step 6: 去重检查
        if self._is_duplicate(content, is_step_title=is_step_title):
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

    def extract_all(self, source: SourceInfo) -> List[TaskContent]:
        """从来源信息中提取所有任务内容（支持复合行拆分）

        如果来源行包含 ";第N步：" 等复合分隔符，拆分为多个独立任务。
        否则返回单一任务。

        Args:
            source: 来源定位信息

        Returns:
            任务内容列表，可能为空
        """
        results = []
        parts = self._split_compound(source.raw_text)
        for part in parts:
            # 为每个拆分部分创建独立的新 SourceInfo（避免 copy.copy 共享状态）
            part_source = SourceInfo(
                raw_text=part,
                section_path=source.section_path,
                page=source.page,
                line_num=source.line_num,
                context_before=source.context_before,
                context_after=source.context_after,
                file_type=source.file_type,
                is_table_row=source.is_table_row,
                table_index=source.table_index,
                table_row_index=source.table_row_index,
            )
            result = self.extract(part_source)
            if result:
                results.append(result)
        return results

    def _split_compound(self, raw_text: str) -> List[str]:
        """拆分复合行

        将包含 ";第N步：" 或 "；[a-z]. " 分隔符的复合行拆分为多个独立文本。

        示例：
            "新增接口A；第2步：直接查询数据库" → ["新增接口A", "直接查询数据库"]
            "第1步：创建接口；第2步：查询数据库" → ["创建接口", "查询数据库"]

        Args:
            raw_text: 原始文本

        Returns:
            拆分后的文本列表
        """
        text = raw_text.strip()
        if not text:
            return []

        # 检查是否有复合分隔符
        if self.COMPOUND_STEP_PATTERN.search(text):
            parts = self.COMPOUND_STEP_PATTERN.split(text)
        elif self.COMPOUND_ENUM_PATTERN.search(text):
            parts = self.COMPOUND_ENUM_PATTERN.split(text)
        else:
            return [text]

        # 清理空部分
        parts = [p.strip() for p in parts if p.strip()]
        return parts if parts else [text]

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
        """截断过长句子（离线兜底模式）

        在线时由 LLM 做语义概括，此方法仅作为 LLM 不可用时的回退。
        回退策略：按句号分句，保留第一句完整内容。
        不再使用逗号/分号/硬字符截断，避免出现"成开关开启"等残句。

        Args:
            text: 文本

        Returns:
            截断后的文本
        """
        # 策略：按句号分句，保留第一句
        for sep in ['。', '.', '！', '!', '？', '?']:
            idx = text.find(sep)
            if 0 < idx < len(text) - 1:
                # 保留到第一个句号
                text = text[:idx + 1]
                break

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

    def _is_duplicate(self, content: str, is_step_title: bool = False) -> bool:
        """去重检查

        去重策略：
        1. 完全相同
        2. 包含关系（短内容在长内容中，步骤标题跳过此项）
        3. 编辑距离 ≤ 3（短内容）

        Args:
            content: 任务内容
            is_step_title: 是否步骤标题（第N步开头），跳过包含关系去重

        Returns:
            是否为重复
        """
        # 策略 1：完全相同
        if content in self.seen_contents:
            return True

        for seen in self.seen_contents:
            # 策略 2：包含关系（步骤标题不参与，避免被同片段长文本误杀）
            # 增加长度比约束：短内容长度至少达到长内容的 50%，避免"直接查询数据库"被
            # "提供分页查询备份记录列表接口，每次请求直接查询数据库"这类长文本误杀
            if not is_step_title and (content in seen or seen in content):
                shorter = content if len(content) <= len(seen) else seen
                longer = seen if len(content) <= len(seen) else content
                if len(shorter) / len(longer) >= 0.5:
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