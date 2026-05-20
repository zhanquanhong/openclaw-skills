"""一致性验证引擎 - v4.0

验证来源 → 内容 → 模块三者的一致性。

验证项：
1. 任务内容的核心词能否在来源原文中找到？
2. 模块名与来源章节是否一致？
3. 任务内容是否完整（没有被截断关键信息）？
4. 相邻任务是否重复/相似
5. 模块内任务数量是否合理
6. 来源信息的合理性检测

使用方式：
    checker = ConsistencyChecker()
    result = checker.verify(task_dict)
    print(result.is_valid)  # True/False
    print(result.issues)    # ['内容核心词不在来源中']
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """验证结果

    Attributes:
        is_valid: 是否通过验证
        confidence: 置信度 (0.0 - 1.0)
        issues: 问题列表
    """
    is_valid: bool = True
    confidence: float = 1.0
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "is_valid": self.is_valid,
            "confidence": self.confidence,
            "issues": self.issues,
        }


def _edit_distance(s1: str, s2: str) -> float:
    """计算归一化编辑距离（0.0=完全相同，1.0=完全不同）

    Args:
        s1: 字符串 1
        s2: 字符串 2

    Returns:
        归一化编辑距离
    """
    if not s1 and not s2:
        return 0.0
    if not s1 or not s2:
        return 1.0

    # 计算 Levenshtein 距离
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

    # 归一化到 [0, 1]
    max_len = max(len(s1), len(s2))
    return distances[-1] / max_len if max_len > 0 else 0.0


class ConsistencyChecker:
    """一致性验证引擎"""

    def verify(self, task: Dict) -> ValidationResult:
        """验证任务的一致性

        Args:
            task: 任务字典，必须包含：
                - 任务模块
                - 任务内容
                - 任务来源
                - _source_info (SourceInfo 对象，可选)

        Returns:
            验证结果
        """
        result = ValidationResult()

        content = task.get("任务内容", "")
        source = task.get("任务来源", "")
        module = task.get("任务模块", "")

        if not content:
            result.is_valid = False
            result.issues.append("任务内容为空")
            result.confidence = 0.0
            return result

        if not source:
            result.issues.append("任务来源为空")
            result.confidence = max(result.confidence - 0.5, 0.1)

        # 验证 1: 内容核心词在来源原文中（关键验证，权重最高）
        if task.get("_source_info"):
            raw_text = task["_source_info"].raw_text
            if not self._content_in_source(content, raw_text):
                result.issues.append("任务内容无法在来源原文中找到对应")
                result.confidence = max(result.confidence - 0.8, 0.1)

        # 验证 2: 模块名与来源章节相关
        if source and module:
            section_path = task.get("_source_info").section_path if task.get("_source_info") else ""
            if section_path and not self._module_matches_section(module, section_path):
                result.issues.append(f"模块'{module}'与来源章节不一致")
                result.confidence = max(result.confidence - 0.2, 0.1)

        # 验证 3: 内容长度检查
        if len(content) < 4:
            result.issues.append("任务内容过短（<4 字符）")
            result.confidence = max(result.confidence - 0.2, 0.1)

        # 确定是否有效
        result.is_valid = result.confidence >= 0.3

        if result.issues:
            logger.warning(
                f"一致性验证告警 [confidence={result.confidence:.2f}]: "
                f"{content} → {'; '.join(result.issues)}"
            )

        return result

    def check_adjacent_duplicates(self, tasks: List[Dict]) -> List[ValidationResult]:
        """检测相邻任务中的重复/相似内容

        使用归一化编辑距离检测，距离 < 0.3 视为重复。

        Args:
            tasks: 任务列表（按顺序排列）

        Returns:
            验证结果列表
        """
        results: List[ValidationResult] = []

        for i in range(len(tasks) - 1):
            content_a = tasks[i].get("任务内容", "")
            content_b = tasks[i + 1].get("任务内容", "")

            if not content_a or not content_b:
                continue

            distance = _edit_distance(content_a, content_b)
            if distance < 0.3:
                result = ValidationResult(
                    is_valid=False,
                    confidence=1.0 - distance,
                    issues=[(
                        f"相邻任务重复/相似（编辑距离={distance:.2f}）："
                        f"「{content_a}」↔「{content_b}」"
                    )],
                )
                results.append(result)

        return results

    def check_module_balance(self, tasks: List[Dict]) -> List[ValidationResult]:
        """检测模块内任务数量是否合理

        - 一个模块 < 3 个任务 → WARN（可能需要合并）
        - 一个模块 > 15 个任务且没有子模块 → WARN（可能需要拆分）

        Args:
            tasks: 任务列表

        Returns:
            验证结果列表
        """
        results: List[ValidationResult] = []

        # 按模块分组
        module_groups: Dict[str, List[Dict]] = {}
        for task in tasks:
            module = task.get("任务模块", "未分类")
            if module not in module_groups:
                module_groups[module] = []
            module_groups[module].append(task)

        for module, group in module_groups.items():
            count = len(group)

            if count < 3:
                issues = [f"模块'{module}'任务数过少（{count}个，建议≥3）"]
                result = ValidationResult(
                    is_valid=True,
                    confidence=0.7,
                    issues=issues,
                )
                results.append(result)
            elif count > 15:
                issues = [f"模块'{module}'任务数过多（{count}个，建议≤15），考虑拆分为子模块"]
                result = ValidationResult(
                    is_valid=False,
                    confidence=0.5,
                    issues=issues,
                )
                results.append(result)

        return results

    def check_source_reasonability(self, tasks: List[Dict]) -> List[ValidationResult]:
        """检测来源信息的合理性

        检查项：
        - 多个任务来源行号完全一致 → WARN
        - 来源行号为 0 → WARN
        - 来源段落长度异常（原文长度 > 200 字符）→ WARN

        Args:
            tasks: 任务列表（需包含 _source_info 字段）

        Returns:
            验证结果列表
        """
        results: List[ValidationResult] = []

        # 检查行号重复
        line_num_counts: Dict[int, List[str]] = {}
        for task in tasks:
            source_info = task.get("_source_info")
            if source_info and hasattr(source_info, "line_num") and source_info.line_num > 0:
                ln = source_info.line_num
                if ln not in line_num_counts:
                    line_num_counts[ln] = []
                line_num_counts[ln].append(task.get("任务内容", ""))

        for ln, contents in line_num_counts.items():
            if len(contents) > 1:
                result = ValidationResult(
                    is_valid=False,
                    confidence=0.6,
                    issues=[f"多个任务来源行号重复（第{ln}行）：{' | '.join(contents[:3])}"],
                )
                results.append(result)

        # 检查行号 0 和原文异常
        for task in tasks:
            source_info = task.get("_source_info")
            content = task.get("任务内容", "")

            if source_info and hasattr(source_info, "line_num"):
                if source_info.line_num == 0:
                    result = ValidationResult(
                        is_valid=True,
                        confidence=0.6,
                        issues=[f"来源行号为0：{content}"],
                    )
                    results.append(result)

            if source_info and hasattr(source_info, "raw_text"):
                raw_len = len(source_info.raw_text)
                if raw_len > 200:
                    result = ValidationResult(
                        is_valid=True,
                        confidence=0.5,
                        issues=[f"来源原文过长（{raw_len}字符）：{content}"],
                    )
                    results.append(result)

        return results

    def _content_in_source(self, content: str, raw_text: str) -> bool:
        """验证任务内容的核心词能否在来源原文中找到

        Args:
            content: 任务内容
            raw_text: 来源原文

        Returns:
            是否找到
        """
        # 策略 1: 任务内容完整在原文中
        if content in raw_text:
            return True

        # 策略 2: 提取核心词（去掉动词）进行匹配
        verbs = [
            '新增', '更新', '删除', '修改', '实现', '开发', '提供',
            '支持', '集成', '对接', '设计', '构建', '迁移', '优化',
            '重构', '配置', '部署', '查询', '创建',
        ]
        core = content
        for verb in verbs:
            if core.startswith(verb):
                core = core[len(verb):]
                break

        if core and core in raw_text:
            return True

        # 策略 3: 至少 4 个连续字符匹配
        if len(content) >= 4:
            for i in range(len(content) - 3):
                sub = content[i:i+4]
                if sub in raw_text:
                    return True

        return False

    def _module_matches_section(self, module: str, section_path: str) -> bool:
        """验证模块名与来源章节是否一致

        Args:
            module: 模块名
            section_path: 章节路径

        Returns:
            是否一致
        """
        if not module or not section_path:
            return True  # 无法验证，不扣分

        # 模块名在章节路径中
        if module in section_path:
            return True

        # 章节路径的关键词在模块名中
        parts = section_path.split(' > ')
        for part in parts:
            # 去掉编号和后缀
            clean = re.sub(r'^[\d一二三四五六七八九十]+(?:\.[\d]+)*[\.、\s]+', '', part)
            for suffix in ['接口设计', '接口文档', '接口定义', '功能', '设计', '说明', '开发', '实现']:
                if clean.endswith(suffix):
                    clean = clean[:-len(suffix)].strip()
                    break
            if clean and (clean in module or module in clean):
                return True

        return False
