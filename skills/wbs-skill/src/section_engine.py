"""章节推断引擎 - 模板选择模式

根据预置模板从文档文本中识别章节结构，支持多种编号规则。

使用方式：
    engine = SectionInferEngine(template='numeric')
    sections = engine.infer(lines)
    section = engine.find_section_by_line(42, sections)
"""

import re
import logging
import yaml
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Section:
    """章节信息

    Attributes:
        title: 章节标题文本
        level: 章节层级（1=一级，2=二级，依此类推）
        line_num: 在文档中的行号（1-based）
    """
    title: str
    level: int
    line_num: int

    def __repr__(self) -> str:
        return f"Section(L{self.level}: {self.title} @行{self.line_num})"


class SectionInferEngine:
    """章节推断引擎

    根据预置模板从文档行中识别章节结构。

    支持的模板：
    - numeric: 数字编号（1.2.1）
    - chinese: 中文编号（一、(一)、1.）
    - markdown: Markdown 标题（#、##）
    - mixed: 混合编号（中文一级 + 数字二级）

    使用示例：
        engine = SectionInferEngine(template='numeric')
        sections = engine.infer(lines)
    """

    def __init__(self, template: str = None, config_path: str = None):
        """初始化章节推断引擎

        Args:
            template: 模板名称（numeric/chinese/markdown/mixed）
            config_path: 配置文件路径（默认：config/section_rules.yaml）

        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 模板名称无效
        """
        self.config = self._load_config(config_path)
        template_name = template or self.config.get('default_template', 'numeric')

        templates = self.config.get('templates', {})
        if template_name not in templates:
            available = list(templates.keys())
            raise ValueError(
                f'未知的章节模板：{template_name}（可用模板：{available}）'
            )

        self.template_name = template_name
        self.template = templates[template_name]
        logger.info(f'使用章节模板：{self.template_name} - {self.template.get("name", "")}')

    def _load_config(self, config_path: Optional[str] = None) -> Dict:
        """加载配置文件

        Args:
            config_path: 配置文件路径

        Returns:
            配置字典

        Raises:
            FileNotFoundError: 配置文件不存在
        """
        # 优先使用指定路径
        if config_path:
            path = Path(config_path)
            if path.exists():
                return self._parse_yaml(path)
            logger.warning(f'指定配置文件不存在：{config_path}')

        # 默认路径：与当前文件同级的 config 目录
        default_path = Path(__file__).parent.parent / 'config' / 'section_rules.yaml'
        if default_path.exists():
            return self._parse_yaml(default_path)

        raise FileNotFoundError(
            f'找不到章节规则配置：{default_path}\n'
            f'请确保 config/section_rules.yaml 存在'
        )

    def _parse_yaml(self, path: Path) -> Dict:
        """解析 YAML 配置文件

        Args:
            path: 文件路径

        Returns:
            配置字典

        Raises:
            yaml.YAMLError: YAML 解析失败
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            if not config or 'templates' not in config:
                raise ValueError(f'配置文件格式错误，缺少 templates 字段：{path}')
            return config
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f'YAML 解析失败：{path}，错误：{e}')

    def infer(self, lines: List[str]) -> List[Section]:
        """按模板推断章节

        Args:
            lines: 文档行列表

        Returns:
            章节列表，按行号排序
        """
        if not lines:
            return []

        template = self.template

        # 规则模式（chinese / mixed）：多条规则
        if 'rules' in template:
            return self._infer_by_rules(lines, template['rules'])

        # 单规则模式（numeric / markdown）：一条规则
        if 'pattern' in template:
            return self._infer_by_single_rule(lines, template)

        logger.warning(f'模板 {self.template_name} 缺少 rules 或 pattern 配置')
        return []

    def _infer_by_rules(self, lines: List[str], rules: List[Dict]) -> List[Section]:
        """按多条规则推断章节

        Args:
            lines: 文档行列表
            rules: 规则列表

        Returns:
            章节列表
        """
        sections = []

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                continue

            for rule in rules:
                pattern = rule.get('pattern')
                if not pattern:
                    continue

                if re.match(pattern, stripped):
                    level = rule.get('level', 1)
                    sections.append(Section(
                        title=stripped,
                        level=level,
                        line_num=line_num
                    ))
                    break  # 匹配到就停止，不重复匹配

        return sections

    def _infer_by_single_rule(self, lines: List[str], template: Dict) -> List[Section]:
        """按单条规则推断章节

        Args:
            lines: 文档行列表
            template: 模板配置

        Returns:
            章节列表
        """
        sections = []
        pattern = template['pattern']
        level_infer = template.get('level_infer')

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                continue

            if re.match(pattern, stripped):
                level = self._infer_level(level_infer, stripped)
                sections.append(Section(
                    title=stripped,
                    level=level,
                    line_num=line_num
                ))

        return sections

    def _infer_level(self, method: Optional[str], line: str) -> int:
        """根据推断方法计算层级

        Args:
            method: 推断方法（count_dots / hash_count）
            line: 文本行

        Returns:
            层级（>=1）
        """
        if method == 'count_dots':
            # 数字编号：点的数量 + 1
            # 1 → level 1, 1.2 → level 2, 1.2.1 → level 3
            return line.count('.') + 1

        if method == 'hash_count':
            # Markdown：# 的数量
            # # → level 1, ## → level 2, ### → level 3
            match = re.match(r'^(#+)', line)
            return len(match.group(1)) if match else 1

        # 默认层级
        return 1

    def find_section_by_line(self, line_num: int, sections: List[Section]) -> Optional[Section]:
        """查找指定行号所属的章节

        返回行号 <= line_num 的最近章节。

        Args:
            line_num: 目标行号（1-based）
            sections: 章节列表（需按行号升序）

        Returns:
            所属章节，未找到返回 None
        """
        result = None
        for section in sections:
            if section.line_num <= line_num:
                result = section
            else:
                break
        return result

    def get_template_info(self) -> Dict:
        """获取当前模板信息

        Returns:
            模板信息字典
        """
        return {
            'name': self.template_name,
            'display_name': self.template.get('name', ''),
            'description': self.template.get('description', ''),
            'example': self.template.get('example', ''),
        }
