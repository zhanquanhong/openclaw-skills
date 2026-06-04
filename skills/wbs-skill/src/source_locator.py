"""来源定位引擎 - v4.0

为文档中的每行生成精确定位信息，支持 PDF/DOCX/Markdown。

核心能力：
1. 行号 → 页码映射（PDF）
2. 行号 → 章节路径（MD/DOCX）
3. 任务行识别（判断某行是否为潜在任务）
4. 上下文提取（前后各 N 行关键文本）
5. 三级定位：粗定位（章节/页码）→ 精定位（行号）→ 可验证（原文片段）

使用方式：
    locator = SourceLocator()
    sources = locator.locate_all(document)
    source = sources[0]
    print(source.format_for_excel())
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

from src.section_engine import Section

logger = logging.getLogger(__name__)


# 技术关键词常量（跨方法共享）
_TECH_KEYWORDS = [
    '接口', '功能', '模块', '表', '字段', '索引', '缓存', '队列',
    '定时任务', '数据', '状态', '统计', '列表', '查询', '删除',
    '安装', '搜索', '开关', '同步', '关系', '配置', '参数',
    '权限', '角色', '用户', '日志', '监控', '告警', '回调',
    '路由', '网关', '代理', '中间件', '服务', 'API',
    '服务', '任务', '流程', '引擎', '处理器', '调度器', '监听器',
    '工厂', '策略', '适配器', '管道', '过滤器', '拦截器', '切面',
    '中间件', '插件', '扩展', 'SDK', 'Client', 'Provider', 'Consumer',
    'Gateway', 'Proxy', 'Agent', 'Worker', 'Job', 'CRON', 'Mq', 'Queue',
    'Topic', 'Exchange', 'Binding', '路由', '注册中心', '配置中心',
    '端点', '地址', 'URL', 'URI', '参数', 'Body', 'Header', 'Payload',
    'TLS', 'SSL', 'OAuth', 'JWT', 'Token', 'Session', 'Cookie',
]


@dataclass
class SourceInfo:
    """任务来源定位信息

    三级定位体系：
    - L1 粗定位: section_path + page（章节路径 / 页码）
    - L2 精定位: line_num（全局行号）
    - L3 可验证: raw_text + context（原文 + 上下文）
    """
    # L1 粗定位
    section_path: str = ""       # 章节路径，如 "3.用户中心 > 3.1 接口设计"
    page: int = 0                # 页码（PDF 有效，MD/DOCX 为 0）

    # L2 精定位
    line_num: int = 0            # 全局行号（1-based）

    # L3 可验证
    raw_text: str = ""           # 该行原文
    context_before: str = ""     # 上文 1-2 行
    context_after: str = ""      # 下文 1-2 行

    # 元数据
    file_type: str = ""          # pdf / docx / markdown
    is_table_row: bool = False   # 是否为表格行
    table_index: int = -1        # 表格索引（表格行有效）
    table_row_index: int = -1    # 表格内行索引（表格行有效）

    def format_for_excel(self) -> str:
        """格式化为 Excel 来源列展示文本

        格式：
        📍 章节路径 | P5 | 第 42 行
        📝 原文："xxx"
        """
        parts = []

        # L1: 粗定位
        if self.section_path:
            parts.append(self.section_path)
        if self.page > 0:
            parts.append(f"P{self.page}")
        if self.line_num > 0:
            parts.append(f"第{self.line_num}行")

        location = " | ".join(parts) if parts else "未知位置"

        # L3: 原文
        raw = self.raw_text.strip()
        # 截断过长原文（超过 60 字符）
        raw_len = len(raw)
        if raw_len > 60:
            raw = raw[:57] + "..."

        return f"{location}\n原文：「{raw}」"

    def format_for_debug(self) -> str:
        """调试格式"""
        lines = [
            f"来源定位 [{self.file_type}]",
            f"  章节: {self.section_path}",
            f"  页码: P{self.page}" if self.page > 0 else "  页码: N/A",
            f"  行号: 第{self.line_num}行",
            f"  原文: {self.raw_text}",
        ]
        if self.context_before:
            lines.append(f"  上文: {self.context_before}")
        if self.context_after:
            lines.append(f"  下文: {self.context_after}")
        return "\n".join(lines)

    def to_dict(self) -> Dict:
        """转为字典（用于序列化）"""
        return {
            "section_path": self.section_path,
            "page": self.page,
            "line_num": self.line_num,
            "raw_text": self.raw_text,
            "context_before": self.context_before,
            "context_after": self.context_after,
            "file_type": self.file_type,
            "is_table_row": self.is_table_row,
            "table_index": self.table_index,
            "table_row_index": self.table_row_index,
        }


class SourceLocator:
    """来源定位引擎

    输入：ParsedDocument 对象
    输出：SourceInfo 列表（每个潜在任务行一个）
    """

    # 任务行识别关键词（动词开头）
    TASK_VERBS = [
        '新增', '更新', '删除', '修改', '实现', '开发', '提供', '支持',
        '集成', '对接', '设计', '构建', '迁移', '优化', '重构', '配置',
        '部署', '查询', '展示', '列表', '搜索', '同步', '推送', '通知',
        '记录', '统计', '校验', '验证', '处理', '生成', '解析', '转换',
        '创建', '读取', '写入', '缓存', '加载', '初始化', '清理',
        '接入', '对接', '集成', '调用', '请求', '响应', '上传', '下载',
        '发送', '接收', '导入', '导出', '汇总', '计算', '匹配', '过滤',
        '排序', '分页', '合并', '拆分', '加密', '解密', '授权', '认证',
        '注册', '登录', '退出', '重置', '恢复', '备份', '归档', '审计',
        '采集', '清洗', '加载', '预加载', '预计算', '预热', '刷新', '过期',
        '锁定', '解锁', '分配', '回收', '监控', '追踪', '采样', '限流',
        '熔断', '降级', '重试', '补偿', '回滚', '提交', '发布', '订阅',
        '进行', '加固', '接入', '升级', '扩展', '增强', '提升',
    ]

    # 否定前缀（包含这些词的行不是任务）
    NEGATION_PREFIXES = [
        '不新增', '不更新', '不需要', '暂不', '无需', '一期已', '已完成',
        '暂时无需', '本期不做', '暂不实现', '不开发',
        '无需新增', '不需要修改', '已有', '已存在', '已实现', '已支持',
        '不变', '不涉及', '不受影响', '无需改动', '无需处理',
        '依赖已有', '沿用现有', '复用现有', '保持现有',
        '已部署', '已执行', '已完成', '已配置',
    ]

    # 非任务标记
    NON_TASK_MARKERS = [
        '•', '○', '●', '■', '□', '◆',  # 列表符号
        '业务目标', '实现逻辑', '设计思路', '背景', '概述',
        '注意事项', '说明', '备注', '提示', '简介',
        'SC->>DB', 'FE-->>U', 'DB-->>SC',  # 时序图标记
        'TODO', 'FIXME', 'HACK',
    ]

    # 流程图/时序图硬过滤模式（包含这些模式的行直接不是任务）
    # 这些模式是流程图/时序图的特有标记，不可能是开发任务
    DIAGRAM_HARD_FILTERS = [
        r'alt\s*\[',                    # alt [ — 时序图条件分支（含 ]alt [）
        r'状态为:',                      # 状态为:还原中 — 纯状态描述
        r'校验(通过|不通过)',            # 校验通过 / 校验不通过 — 流程分支条件
        r'删除成功[/或]',                # 删除成功/或... — 流程分支结果
        r'⻅\d',                        # ⻅3. — 交叉引用
        r'Key：',                        # Key：backup:delete: — 代码级实现细节
        r'[；;]\s*[a-z]\.\s*$',           # ；c. 或 ;c. — 枚举后缀残留（行尾）
        r'[；;][a-z]\.',                  # ；c. — 枚举后缀（行中，后接任意字符）
        r'^提供[^。，,；;]+功能[。，,；;]',  # 提供...功能。 — 功能散文描述，不是任务
    ]

    # 描述性前缀（以这些词开头的行通常不是任务）
    DESCRIPTIVE_PREFIXES = [
        '为保障', '为了', '旨在', '主要', '核心',
        '本节', '本文', '本方案', '本章', '本期', '本项目',
        '如下图所示', '如下表', '参见', '详见',
        '需要说明', '特别说明', '备注',
        '推荐使用', '建议使用', '优先考虑', '原则上',
        '所有接口', '所有操作', '所有请求',
    ]

    # 描述性前缀 + 任务句式混合（以这些词开头但后续跟动词+技术词时仍是任务）
    # 例如："基于XXX实现YYY" 是有效的任务句式
    MIXED_DESCRIPTIVE_PREFIXES = [
        '对于', '关于', '针对',
        '基于', '根据', '按照',
    ]

    # PDF 表格残留模式（包含这些模式的行是表格拼接残留，不是可读任务）
    # 例如：[backup_flag=1]POST...、a.更新用户...backup_flag=1
    PDF_TABLE_RESIDUE = [
        r'\[[\w_]+=\d+\]',          # [backup_flag=1]
        r'\[\w+Status<\d+\]',       # [backupStatus<2]
        r'\]loop\s*\[',             # ]loop [
        r'\(ShardIndex=',           # (ShardIndex=0
        r'-->>',                     # 时序图标记
        r'->>',                      # 流程标记
    ]

    # 架构图标注行（技术方案中的架构图/技术栈标注行，不是可读任务）
    # 例如："云盘API PVC文件系统 数据库 POD..."、"云盘接口 数据库 备份状态服务 前端"
    ARCH_DIAGRAM_PATTERNS = [
        r'^[^\x00-\xff]+\s(?:API|API[\s\S]*接口|接口)($|\s*(?:[\u4e00-\u9fff]+)(?:\s|$))', # 中文+API+中文
    ]

    # 流程/数据流描述标记（以这些模式的行是流程图/数据流说明，不是开发任务）
    # 例如："返回备份记录列表"（数据流输出）、"作为backupFlag返回"（数据转换）
    # 例外：行中包含"新增/创建/实现/开发/配置/设计"等强开发动词时不降分
    FLOW_DESCRIPTION_PATTERNS = [
        r'作为\w{1,20}返回',            # 作为XX返回（数据流输出）
        r'作为\w{1,20}输出',            # 作为XX输出
        r'^返回\w*(?:列表|记录|数据|结果|信息|对象|数据对象|字段|状态)',  # 返回XX列表/记录（输出描述）
        r'^支持\w*(?:分页|分⻚)',       # 支持分页XX（功能点说明）
    ]

    # 原始变量名模式（行中包含 snake_case/camelCase 变量名且夹杂中文，通常是数据流描述）
    # 例如："查询algorithm_open_claw_user表backup_flag字段"、"user_id回传"
    RAW_VAR_PATTERN = re.compile(
        r'[\u4e00-\u9fff][a-z_][\w]{1,30}|'  # 中文紧接英文变量（中文+变量名）
        r'[a-z]+_\w+[\u4e00-\u9fff]'         # snake_case变量紧接中文（backup_flag字段）
    )

    # 段落合并配置：连续任务行间距 <= 此值则合并为一个复合任务
    PARAGRAPH_MERGE_GAP = 0  # 不进行段落合并（复合拆分由 content_extractor 的；第N步模式处理）

    # 工作流枚举项（a. b. c. d. e. f. 等，只有同时包含技术描述才可能是任务）
    ENUM_PATTERNS = [
        r'^[a-f][\.\)]\s*',        # a. b. c. d.
        r'^◦',                      # ◦ 列表符号
    ]

    # 非任务后缀（以这些词结尾的行通常不是任务）
    NON_TASK_SUFFIXES = [
        '的能力', '的需求', '的目标', '的背景',
        '的方案', '的流程', '的架构', '的原则',
        '的设计', '的实现', '的说明',
    ]

    # Markdown 代码块标记
    CODE_BLOCK_MARKERS = ['```', '~~~']

    def __init__(self, context_lines: int = 1):
        """初始化

        Args:
            context_lines: 上下文行数（前后各 N 行）
        """
        self.context_lines = context_lines
        self._in_code_block = False

    # 流程图区域检测：后N行内有这些模式标记的行为流程图，其内容不纳入任务
    FLOWCHART_ZONE_SCAN_LINES = 8  # 扫描范围（前/后行数）
    FLOWCHART_MARKERS = [
        r'alt\s*\[',                 # alt [ — 时序图条件分支
        r'^\[\w+=\d+\]',             # [backup_flag=1] at line start — 条件标记
        r'-->>',                     # 时序图消息箭头
        r'^时序图：?$',              # 时序图： — 章节标记
        # 数据流输出：仅匹配纯数据流行（行首以"返回"开头，且后接纯数据描述）
        # 不匹配"•业务目标：分页返回..."这类任务描述行
        r'^返回\w*(?:列表|记录|数据|结果|信息|对象)',  # 返回XX — 数据流输出
    ]

    def locate_all(
        self,
        lines: List[str],
        sections: List[Section],
        file_type: str = "",
        page_map: Optional[Dict[int, int]] = None,
    ) -> List[SourceInfo]:
        """定位所有潜在任务行

        Args:
            lines: 文档行列表
            sections: 章节列表（按行号升序）
            file_type: 文件类型（pdf/docx/markdown）
            page_map: 行号 → 页码映射（PDF 有效）

        Returns:
            来源信息列表
        """
        # 预计算流程图区域（行号范围）
        # 检测逻辑：如果某行匹配流程图标记，其前后 FLOWCHART_ZONE_SCAN_LINES 行内
        # 的所有行标记为流程图区域，这些区域内的任务行将被降低权重或过滤
        total_lines = len(lines)
        in_flowchart = [False] * total_lines
        for line_num_0, line in enumerate(lines):
            stripped = line.strip()
            for marker in self.FLOWCHART_MARKERS:
                if re.search(marker, stripped):
                    # 标记前后 N 行为流程图区域
                    start = max(0, line_num_0 - self.FLOWCHART_ZONE_SCAN_LINES)
                    end = min(total_lines, line_num_0 + self.FLOWCHART_ZONE_SCAN_LINES + 1)
                    for i in range(start, end):
                        in_flowchart[i] = True
                    break

        sources = []

        for line_num_0, line in enumerate(lines):
            line_num = line_num_0 + 1  # 1-based
            stripped = line.strip()

            # 跳过空行
            if not stripped:
                continue

            # 跳过代码块
            if self._is_code_block_line(stripped):
                continue

            # 判断是否为任务行
            if not self._is_task_line(stripped):
                continue

            # 流程图区域过滤：在流程图区域内的步骤式行（第N步），且不含开发动词，不纳入任务
            # 例如时序图中的"第1步：接收请求"不是开发任务
            if in_flowchart[line_num_0]:
                strong_dev = ['新增','创建','实现','开发','配置','部署','构建','迁移','对接','集成','设计']
                has_strong_dev = any(v in stripped for v in strong_dev)
                is_step_line = bool(re.search(r'第\s*\d+\s*步', stripped))
                if is_step_line and not has_strong_dev:
                    continue

            # 提取上下文
            before = self._extract_context_before(lines, line_num_0)
            after = self._extract_context_after(lines, line_num_0, len(lines))

            # 查找所属章节
            section = self._find_section(line_num, sections)
            section_path = self._build_section_path(line_num, sections)

            # 页码映射
            page = 0
            if page_map and line_num in page_map:
                page = page_map[line_num]

            source = SourceInfo(
                section_path=section_path,
                page=page,
                line_num=line_num,
                raw_text=stripped,
                context_before=before,
                context_after=after,
                file_type=file_type,
            )

            sources.append(source)

        # 段落级合并：连续包含步骤标记或枚举前缀的相邻行合并为复合任务
        # 避免"第1步：创建接口"、"第2步：查询数据库"等细粒度步骤被拆成多个独立任务
        # 只有当两行都包含步骤标记或枚举前缀时才合并
        if sources:
            merged = [sources[0]]
            for i in range(1, len(sources)):
                prev = merged[-1]
                curr = sources[i]
                gap = curr.line_num - prev.line_num
                same_section = curr.section_path == prev.section_path
                is_step_prev = bool(re.search(r'第\s*\d+\s*步', prev.raw_text)) or bool(re.match(r'^[a-f][\.\)]\s*', prev.raw_text))
                is_step_curr = bool(re.search(r'第\s*\d+\s*步', curr.raw_text)) or bool(re.match(r'^[a-f][\.\)]\s*', curr.raw_text))
                # 两行都是步骤/枚举式且同一章节且行号紧邻 → 合并
                if gap <= self.PARAGRAPH_MERGE_GAP and same_section and (is_step_prev or is_step_curr):
                    prev.raw_text = prev.raw_text + "；" + curr.raw_text
                    prev.context_after = curr.context_after
                else:
                    merged.append(curr)
            sources = merged
            logger.info(f"段落合并后：{len(sources)} 个任务（合并前 {len(merged)} 个）")

        logger.info(f"来源定位完成：找到 {len(sources)} 个潜在任务行")
        return sources

    def _is_task_line(self, line: str) -> bool:
        """判断是否为任务行（基于浮动置信度评分）

        Args:
            line: 文档行（已 strip）

        Returns:
            是否为潜在任务行
        """
        if len(line) < 6:
            return False

        # === 硬性过滤（直接返回 False） ===

        # 1. PDF 表格残留模式
        for pattern in self.PDF_TABLE_RESIDUE:
            if re.search(pattern, line):
                return False

        # 2. 纯枚举项（a. b. c. / ◦ 列表项）
        # 去掉前缀后内容足够且有动词+技术词才算任务，否则是流程步骤描述
        is_enum = any(re.match(p, line) for p in self.ENUM_PATTERNS)
        if is_enum:
            stripped_line = re.sub(r'^[a-f][\.\)]\s*|^◦', '', line).strip()
            if not stripped_line or len(stripped_line) < 6:
                return False
            # 去掉前缀后判断是否有动词和技术词
            has_verb = any(v in stripped_line for v in self.TASK_VERBS)
            has_tech = any(kw.lower() in stripped_line.lower() for kw in _TECH_KEYWORDS)
            if not has_verb and not has_tech:
                return False

        # 3. 否定关键词（纯粹描述性否定 / 已存在）
        for neg_kw in self.NEGATION_PREFIXES:
            # 行首匹配
            if line.startswith(neg_kw):
                return False
            # 行尾匹配
            if line.endswith(neg_kw):
                return False
            # 行中完整词匹配（分隔符后的否定词）
            if re.search(rf'(?:[，,。、；;：:\s]){re.escape(neg_kw)}(?:[，,。、；;：:\s]|$)', line):
                return False

        # 4. 非任务标记
        if any(marker in line for marker in self.NON_TASK_MARKERS):
            return False

        # 4.5 流程图/时序图硬过滤
        for filter_pattern in self.DIAGRAM_HARD_FILTERS:
            if re.search(filter_pattern, line):
                return False

        # 5. 纯数字/纯符号行
        if re.match(r'^[\d\s\.\-\|]+$', line):
            return False

        # 6. 架构图标注行（技术名词堆叠，无谓语结构，如"云盘API PVC 文件系统 数据库 POD"）
        # 检测：连续出现多个技术名词且行中至少 2 个技术词以空格分隔
        tech_nouns_long = ['API', '服务', '数据库', 'Redis', 'MQ', 'K8s', 'POD', 'PVC', 'RocketMQ', 'XXL-Job', '消费者', '生产者', '网关', '代理']
        tech_count_in_line = sum(1 for tn in tech_nouns_long if tn in line)
        # 特征1：技术词 >= 3 且长度 >= 15
        if tech_count_in_line >= 3 and len(line) >= 15:
            return False
        # 特征2：纯技术词堆叠（行以空格分词后技术词占比高）
        words = line.split()
        if len(words) >= 4:
            tech_words = sum(1 for w in words if any(tn in w for tn in tech_nouns_long))
            if tech_words >= 3 and tech_words / len(words) >= 0.4:
                return False

        # 7. 章节标题（非【】标记的编号开头行）
        if re.match(r'^[\d一二三四五六七八九十]+[、\.\s]', line):
            if '【新增】' in line or '【更新】' in line or '【删除】' in line:
                pass  # 有标记的编号行保留
            else:
                return False

        # 7. 非任务后缀
        if any(line.endswith(suffix) for suffix in self.NON_TASK_SUFFIXES):
            return False

        # === 浮动评分 ===
        score = self._score_task_line(line)

        # === 原始变量名检测（必须在 _match_task_pattern 之前，影响 bonus 判定）===
        # 原始变量名：中文 + snake_case/camelCase 变量名同时出现 → 数据流描述
        # 例如："查询algorithm_open_claw_user表backup_flag字段"
        strong_dev_verbs = ['新增', '创建', '实现', '开发', '设计', '配置', '部署', '构建', '迁移', '对接', '集成']
        has_strong_dev = any(v in line for v in strong_dev_verbs)
        has_raw_var = False
        if not has_strong_dev:
            if self.RAW_VAR_PATTERN.search(line):
                has_raw_var = True
                score -= 2

        # 高置信度快速通道：_match_task_pattern 命中直接 +2
        # 但检测到原始变量名时不加分（数据流描述不是任务）
        has_strong_desc = any(line.startswith(p) for p in self.DESCRIPTIVE_PREFIXES)
        if not has_strong_desc and not has_raw_var and self._match_task_pattern(line):
            score += 2

        # 描述性前缀降低分数
        if has_strong_desc:
            score -= 2

        # 混合前缀处理
        mixed_matched = [p for p in self.MIXED_DESCRIPTIVE_PREFIXES if line.startswith(p)]
        if mixed_matched:
            has_verb = any(v in line for v in self.TASK_VERBS)
            has_tech = any(kw.lower() in line.lower() for kw in _TECH_KEYWORDS)
            if has_verb and has_tech:
                score += 1
            else:
                score -= 2

        # 枚举项降分（已经过初步过滤，有动词+技术词时不降分）
        if is_enum:
            stripped_line = re.sub(r'^[a-f][\.\)]\s*|^◦', '', line).strip()
            has_verb = any(v in stripped_line for v in self.TASK_VERBS)
            has_tech = any(kw.lower() in stripped_line.lower() for kw in _TECH_KEYWORDS)
            if not (has_verb and has_tech):
                score -= 1

        # 包含 = 符号（变量赋值）降分
        if '=' in line and not line.strip().startswith('POST') and not line.strip().startswith('GET'):
            # 判断是 URL 查询参数（?page=1，? 在 = 之前）还是 SQL 参数（user_id=?，= 在 ? 之前）
            eq_pos = line.find('=')
            q_pos = line.find('?')
            is_url_param = q_pos >= 0 and q_pos < eq_pos  # ?page=1 模式
            if not is_url_param:
                score -= 2

        # === 流程/数据流描述降分 ===
        # 匹配"作为XX返回"、"返回XX列表"、"支持XX功能"等非任务模式
        # 对于带枚举前缀（a. c. ◦）的项，同时检查剥离前缀后的内容
        # 例如 "c.支持分⻚查询" → 剥离后 "支持分⻚查询" → 匹配 ^支持\w*(?:分页|分⻚)
        if not has_strong_dev:
            if is_enum:
                stripped_for_flow = re.sub(r'^[a-f][\.\)]\s*|^◦', '', line).strip()
            else:
                stripped_for_flow = line
            for flow_pattern in self.FLOW_DESCRIPTION_PATTERNS:
                if re.search(flow_pattern, line) or re.search(flow_pattern, stripped_for_flow):
                    score -= 3
                    break

        return score >= 2

    def _score_task_line(self, line: str) -> int:
        """计算任务行的置信度分数

        评分规则（去重，同一词不重复加分）：
        - 包含动词关键词：+1
        - 包含技术关键词：+1
        - 包含 HTTP 方法：+2
        - 包含【新增】等标记：+2
        - 包含步骤编号：+1

        Args:
            line: 文档行

        Returns:
            置信度分数
        """
        score = 0

        # 1. 包含动词关键词
        # 中文词直接用 in 匹配（中文没有空格分词，中文字符相邻不构成误匹配）
        matched_verbs = {v for v in self.TASK_VERBS if v in line}
        if len(matched_verbs) > 0:
            score += 1
            if len(matched_verbs) >= 3:
                score += 1

        # 2. 包含技术关键词
        matched_tech = {kw for kw in _TECH_KEYWORDS if kw in line}
        if len(matched_tech) > 0:
            score += 1
            if len(matched_tech) >= 3:
                score += 1

        # 3. 包含 HTTP 方法
        if re.search(r'\b(POST|GET|PUT|DELETE|PATCH|HEAD|OPTIONS)\b', line):
            score += 2

        # 4. 包含【新增】等标记
        if '【新增】' in line or '【更新】' in line or '【删除】' in line or '【修改】' in line:
            score += 2

        # 5. 包含步骤编号
        if re.search(r'第\s*\d+\s*步', line):
            score += 1
        if re.search(r'Step\s*\d+', line, re.IGNORECASE):
            score += 1

        return score

    def _match_task_pattern(self, line: str) -> bool:
        """匹配任务行模式

        匹配规则（满足任一即可）：
        1. 动词开头 + 技术名词
        2. 步骤标记（第N步）
        3. HTTP 方法 + 路径
        4. 包含【新增】【更新】标记
        5. 模块名 + 动词

        Args:
            line: 文档行

        Returns:
            是否匹配
        """
        # 规则 1: 动词开头 + 技术关键词
        verb_pattern = '|'.join(self.TASK_VERBS)
        tech_pattern = '|'.join(_TECH_KEYWORDS)
        if re.search(
            rf'^(?:{verb_pattern}).*(?:{tech_pattern})',
            line
        ):
            return True

        # 规则 2: 步骤标记
        if re.search(r'第\s*\d+\s*步[：:]', line):
            return True

        # 规则 3: HTTP 方法 + 路径
        if re.search(r'^[\[\(]?(?:POST|GET|PUT|DELETE|PATCH)\s+', line):
            return True

        # 规则 4: 【新增】【更新】标记
        if '【新增】' in line or '【更新】' in line or '【删除】' in line:
            return True

        # 规则 5: 模块名 + 动词（如 "技能中心提供查询功能"）
        module_keywords = [
            '技能', '渠道', '对话', '模型', '用户', '订单', '支付',
            '消息', '通知', '配置', '权限', '日志', '监控', '定时',
            'Mclaw', 'MClaw', '后台', '前端', '算法', 'AI', 'K8s',
            'MClaw', 'OpenClaw',
        ]
        module_pattern = '|'.join(module_keywords)
        if re.search(
            rf'(?:{module_pattern}).*(?:{verb_pattern})',
            line
        ):
            return True

        return False

    def _extract_context_before(self, lines: List[str], line_idx: int) -> str:
        """提取上文 N 行关键文本

        Args:
            lines: 文档行列表
            line_idx: 当前行索引（0-based）

        Returns:
            上文文本
        """
        context_parts = []
        count = 0

        for i in range(line_idx - 1, -1, -1):
            line = lines[i].strip()
            if not line:
                continue
            # 跳过章节标题（以编号开头）
            if re.match(r'^[\d#一二三四五六七八九十]+[\.、]', line):
                break
            context_parts.append(line)
            count += 1
            if count >= self.context_lines:
                break

        return ' | '.join(reversed(context_parts))

    def _extract_context_after(self, lines: List[str], line_idx: int, total: int) -> str:
        """提取下文 N 行关键文本

        Args:
            lines: 文档行列表
            line_idx: 当前行索引（0-based）
            total: 总行数

        Returns:
            下文文本
        """
        context_parts = []
        count = 0

        for i in range(line_idx + 1, total):
            line = lines[i].strip()
            if not line:
                continue
            # 跳过章节标题
            if re.match(r'^[\d#一二三四五六七八九十]+[\.、]', line):
                break
            context_parts.append(line)
            count += 1
            if count >= self.context_lines:
                break

        return ' | '.join(context_parts)

    def _find_section(self, line_num: int, sections: List[Section]) -> Optional[Section]:
        """查找指定行号所属的章节

        Args:
            line_num: 行号（1-based）
            sections: 章节列表

        Returns:
            所属章节
        """
        result = None
        for section in sections:
            if section.line_num <= line_num:
                result = section
            else:
                break
        return result

    def _build_section_path(self, line_num: int, sections: List[Section]) -> str:
        """构建章节路径（含层级关系）

        示例：
        - 一级章节： "3.用户中心"
        - 有父子关系： "3.用户中心 > 3.1 接口设计"

        Args:
            line_num: 行号（1-based）
            sections: 章节列表

        Returns:
            章节路径字符串
        """
        # 找到 line_num 之前的所有章节
        preceding_sections = [s for s in sections if s.line_num <= line_num]

        if not preceding_sections:
            return ""

        # 找到最近的章节及其层级
        current = preceding_sections[-1]
        current_level = current.level

        # 向上找父级（level < current_level 的最近章节）
        parent = None
        for s in reversed(preceding_sections[:-1]):
            if s.level < current_level:
                parent = s
                break

        if parent:
            return f"{parent.title} > {current.title}"
        return current.title

    def _is_code_block_line(self, line: str) -> bool:
        """判断是否为代码块边界

        Args:
            line: 文档行

        Returns:
            是否在代码块内
        """
        for marker in self.CODE_BLOCK_MARKERS:
            if line.startswith(marker):
                self._in_code_block = not self._in_code_block
                return True
        return self._in_code_block


def build_page_map(pdf_text_with_pages: List[Tuple[int, str]]) -> Dict[int, int]:
    """从带页码的 PDF 文本构建行号 → 页码映射

    Args:
        pdf_text_with_pages: [(页码, 页面文本), ...]

    Returns:
        {行号: 页码}
    """
    page_map = {}
    global_line = 1

    for page_num, page_text in pdf_text_with_pages:
        page_lines = page_text.split('\n')
        for _ in page_lines:
            page_map[global_line] = page_num
            global_line += 1

    return page_map
