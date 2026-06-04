"""模块归组引擎 - v4.0

根据任务内容关键词推断模块归属，结合来源章节提示，做冲突检测。

核心能力：
1. 内容关键词匹配 → 模块名
2. 章节标题辅助验证
3. 白名单辅助匹配
4. 冲突检测与告警

使用方式：
    grouper = ModuleGrouper(whitelist)
    result = grouper.group("新增用户列表查询接口", "3.用户中心")
    print(result.module_name)  # "用户中心"
    print(result.confidence)   # 0.95
"""

import re
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ModuleResult:
    """模块归组结果

    Attributes:
        module_name: 模块名称
        confidence: 置信度 (0.0 - 1.0)
        match_source: 匹配来源（content/section/whitelist/fallback）
        conflict: 是否存在冲突
        conflict_detail: 冲突详情
    """
    module_name: str
    confidence: float = 0.0
    match_source: str = "fallback"
    conflict: bool = False
    conflict_detail: str = ""

    def to_dict(self) -> Dict:
        return {
            "module_name": self.module_name,
            "confidence": self.confidence,
            "match_source": self.match_source,
            "conflict": self.conflict,
            "conflict_detail": self.conflict_detail,
        }


class ModuleGrouper:
    """模块归组引擎"""

    # 模块关键词映射：关键词 → 模块名
    # 按 specificity 排序（长关键词在前）
    MODULE_KEYWORDS = [
        # 用户相关
        ('用户管理', '用户中心'),
        ('用户列表', '用户中心'),
        ('用户查询', '用户中心'),
        ('用户创建', '用户中心'),
        ('用户权限', '权限中心'),
        ('角色管理', '权限中心'),
        ('权限分配', '权限中心'),
        # 技能相关
        ('技能列表', '技能中心'),
        ('技能搜索', '技能中心'),
        ('技能安装', '技能中心'),
        ('技能中心', '技能中心'),
        # 对话相关
        ('对话列表', '对话管理'),
        ('新建对话', '对话管理'),
        ('历史对话', '对话管理'),
        ('会话管理', '对话管理'),
        ('对话 Hook', '对话管理'),
        # 渠道相关
        ('渠道配置', '渠道模块'),
        ('渠道列表', '渠道模块'),
        ('渠道管理', '渠道模块'),
        # 模型相关
        ('模型列表', '模型管理'),
        ('模型切换', '模型管理'),
        ('模型管理', '模型管理'),
        # MClaw 相关
        ('MClaw', 'MClaw 模块'),
        ('mClaw', 'MClaw 模块'),
        ('mclaw', 'MClaw 模块'),
        # 定时任务相关
        ('定时任务', '定时任务模块'),
        ('任务广场', '定时任务模块'),
        ('任务列表', '定时任务模块'),
        ('任务推送', '定时任务模块'),
        # 推荐相关
        ('推荐', '推荐区'),
        # 订单相关
        ('订单', '订单模块'),
        # 支付相关
        ('支付', '支付模块'),
        ('扣费', '支付模块'),
        # 消息相关
        ('消息', '消息模块'),
        ('通知', '消息模块'),
        ('推送', '消息模块'),
        # 配置相关
        ('配置管理', '配置中心'),
        ('参数配置', '配置中心'),
        ('环境变量', '配置中心'),
        # 日志相关
        ('日志', '日志模块'),
        ('操作日志', '日志模块'),
        # 监控相关
        ('监控', '监控模块'),
        ('告警', '监控模块'),
        # 缓存相关
        ('缓存', '缓存模块'),
        ('Redis', '缓存模块'),
        # 数据库相关
        ('数据库', '数据库模块'),
        ('建表', '数据库模块'),
        ('表结构', '数据库模块'),
        # 前端相关
        ('前端', '前端模块'),
        ('页面', '前端模块'),
        ('UI', '前端模块'),
        # 部署相关
        ('部署', '部署模块'),
        ('K8s', '部署模块'),
        ('k8s', '部署模块'),
        ('容器', '部署模块'),
        # 算法相关
        ('算法', '算法模块'),
        ('模型训练', '算法模块'),
        ('embedding', '算法模块'),
        # 网关/中间件相关
        ('网关', '网关模块'),
        ('中间件', '中间件模块'),
        ('消息队列', '中间件模块'),
        ('Kafka', '中间件模块'),
        ('RabbitMQ', '中间件模块'),
    ]

    # 章节后缀（提取模块名时去掉）
    SECTION_SUFFIXES = [
        '接口设计', '接口文档', '接口定义',
        '功能', '设计', '说明',
        '概述', '详情', '详细描述',
        '开发', '实现', '方案',
    ]

    def __init__(self, whitelist: Optional[Dict] = None):
        """初始化

        Args:
            whitelist: 白名单（模块名 → 任务列表）
        """
        self.whitelist = whitelist or {}
        self._whitelist_keywords: Dict[str, Set[str]] = {}
        self._build_whitelist_keywords()

    def _build_whitelist_keywords(self):
        """从白名单构建关键词索引"""
        for module, tasks in self.whitelist.items():
            keywords = set()
            for task in tasks:
                if isinstance(task, dict):
                    content = task.get('任务内容', '')
                else:
                    content = str(task)
                core = self._extract_core_words(content)
                keywords.update(core)
            self._whitelist_keywords[module] = keywords

    def group(self, task_content: str, section_hint: str = "") -> ModuleResult:
        """根据任务内容推断模块归属"""
        self._last_task_content = task_content
        content_result = self._match_by_content(task_content)
        section_result = self._match_by_section(section_hint)
        whitelist_result = self._match_by_whitelist(task_content)
        return self._decide(content_result, section_result, whitelist_result)

    def _match_by_content(self, content: str) -> ModuleResult:
        """策略 1：内容关键词匹配"""
        for keyword, module in self.MODULE_KEYWORDS:
            if keyword.lower() in content.lower():
                confidence = min(0.5 + len(keyword) * 0.05, 0.95)
                return ModuleResult(
                    module_name=module,
                    confidence=confidence,
                    match_source='content',
                )
        return ModuleResult(module_name='', confidence=0.0, match_source='none')

    def _match_by_section(self, section_hint: str) -> ModuleResult:
        """策略 2：章节标题提取"""
        if not section_hint:
            return ModuleResult(module_name='', confidence=0.0, match_source='none')

        # 去掉层级分隔符，取最后一段
        parts = section_hint.split(' > ')
        last_part = parts[-1].strip()

        # 去掉编号前缀（支持 3.、3.1、3.1.2 等格式，以及中文编号）
        name = re.sub(r'^[\d一二三四五六七八九十]+(?:\.[\d]+)*[\.、\s]+', '', last_part)

        # 去掉后缀
        for suffix in self.SECTION_SUFFIXES:
            if name.endswith(suffix):
                name = name[:-len(suffix)].strip()
                break

        if not name:
            # 处理后为空，尝试用原始章节名（去掉编号）作为 fallback
            fallback = re.sub(r'^[\d一二三四五六七八九十]+(?:\.[\d]+)*[\.、\s]+', '', last_part)
            fallback = fallback.strip('，,。；;：:')
            if fallback and len(fallback) > 2:
                return ModuleResult(
                    module_name=fallback,
                    confidence=0.3,
                    match_source='section',
                )
            return ModuleResult(module_name='', confidence=0.0, match_source='none')

        # 用章节名去关键词映射中匹配
        for keyword, module in self.MODULE_KEYWORDS:
            if keyword in name or name in keyword:
                return ModuleResult(
                    module_name=module,
                    confidence=0.7,
                    match_source='section',
                )

        # 兜底：返回标准化后的章节名
        name = name.strip('，,。；;：:')
        if name:
            return ModuleResult(
                module_name=name,
                confidence=0.5,
                match_source='section',
            )

        return ModuleResult(module_name='', confidence=0.0, match_source='none')

    def _match_by_whitelist(self, content: str) -> ModuleResult:
        """策略 3：白名单匹配（支持子串匹配）"""
        if not self._whitelist_keywords:
            return ModuleResult(module_name='', confidence=0.0, match_source='none')

        content_words = set(self._extract_core_words(content))
        if not content_words:
            return ModuleResult(module_name='', confidence=0.0, match_source='none')

        best_module = ''
        best_score = 0

        for module, keywords in self._whitelist_keywords.items():
            overlap = content_words & keywords
            if overlap:
                score = len(overlap) / len(content_words)
                if score > best_score:
                    best_score = score
                    best_module = module

            # 子串匹配：白名单关键词是内容的子串，或内容是白名单关键词的子串
            # 限制：仅当双方长度相近时触发（长度差 < 50%），防止长文本被短关键词误匹配
            for kw in keywords:
                if len(kw) >= 4:  # 至少 4 字才算有效匹配
                    if kw in content or content in kw:
                        kw_len, content_len = len(kw), len(content)
                        min_len = min(kw_len, content_len)
                        max_len = max(kw_len, content_len)
                        # 长度差超过 50% 不触发子串匹配（避免长文本包含短关键词的误匹配）
                        if max_len > min_len * 1.5:
                            continue
                        sub_score = max(best_score, 0.5)
                        if sub_score > best_score:
                            best_score = sub_score
                            best_module = module

        if best_module and best_score > 0.3:
            return ModuleResult(
                module_name=best_module,
                confidence=min(best_score, 0.9),
                match_source='whitelist',
            )

        return ModuleResult(module_name='', confidence=0.0, match_source='none')

    def _decide(
        self,
        content_result: ModuleResult,
        section_result: ModuleResult,
        whitelist_result: ModuleResult,
    ) -> ModuleResult:
        """综合决策"""
        results = [content_result, section_result, whitelist_result]
        results.sort(key=lambda r: r.confidence, reverse=True)
        best = results[0]

        # 冲突检测
        modules_found = set()
        for r in results:
            if r.module_name and r.confidence > 0.3:
                modules_found.add(r.module_name)

        if len(modules_found) > 1:
            best.conflict = True
            best.conflict_detail = f"冲突：{' vs '.join(modules_found)}，以{best.match_source}为准"
            logger.warning(f"模块冲突：{best.conflict_detail}")

        # 精确覆盖：当最佳模块名是泛化名（标准模块名或短章节名），
        # 且内容中包含更精确的接口/功能名时，用接口名覆盖
        standard_modules = {'MClaw 模块', '数据库模块', '缓存模块', '消息模块', '日志模块', '用户中心', 
                          '前端模块', '部署模块', '定时任务模块', '配置中心', '网关模块', '中间件模块',
                          '监控模块', '算法模块', '订单模块', '支付模块'}
        is_standard = (
            best.module_name in standard_modules
            or (len(best.module_name) <= 3 and best.match_source == 'section')
        )
        if is_standard:
            # 策略 A：section 匹配到有意义的章节名时优先使用
            # 章节名通常比通用模块名更精准（如"1备份开关状态" > "数据库模块"）
            if section_result.module_name and section_result.confidence >= 0.4:
                sec_name = section_result.module_name
                # 只有章节名不是标准模块名且有一定长度时才视为有效
                if sec_name not in standard_modules and len(sec_name) >= 4:
                    old_best = best.module_name
                    best = ModuleResult(
                        module_name=section_result.module_name,
                        confidence=section_result.confidence,
                        match_source=section_result.match_source,
                        conflict=best.conflict,
                        conflict_detail=best.conflict_detail,
                    )
                    logger.debug(f"章节覆盖模块名：{old_best} → {best.module_name}（来源章节）")

            # 策略 B：内容中包含更精确的接口/功能实体名时覆盖
            content_text = getattr(self, '_last_task_content', '')
            entity_match = re.search(
                r'(查询|创建|新增|更新|删除|修改|复用|调用|集成|提供|实现)'
                r'.{4,50}'
                r'(接口|功能|服务)',
                content_text
            )
            if entity_match:
                entity_name = entity_match.group(0)
                # 如果 entity_name 就是 content 本身（没有更精确的信息），不覆盖
                if entity_name == content_text:
                    pass  # 无更精确信息
                elif entity_name not in best.module_name and len(entity_name) > len(best.module_name) + 2:
                    old_best = best.module_name
                    best.module_name = entity_name
                    best.confidence = min(best.confidence + 0.1, 0.95)
                    logger.debug(f"精确覆盖模块名：{old_best} → {entity_name}")

        # 白名单匹配的模块名优先级：仅当白名单置信度显著高于其他结果时才覆盖
        # 降低阈值避免白名单包含关系匹配误覆盖 content/section 结果
        other_results = [r for r in [content_result, section_result]
                        if r.module_name and r.module_name != whitelist_result.module_name]
        max_other = max((r.confidence for r in other_results), default=0)
        if whitelist_result.confidence >= 0.7 and whitelist_result.confidence > max_other:
            best = whitelist_result
            best.conflict = best.conflict or len(modules_found) > 1
            if other_results:
                logger.debug(f"白名单覆盖：'{best.module_name}' > {'/'.join(r.match_source for r in other_results)}")

        # 兜底
        if not best.module_name:
            best.module_name = '未分类'
            best.confidence = 0.1
            best.match_source = 'fallback'

        return best

    def _extract_core_words(self, content: str) -> List[str]:
        """提取核心词（去掉动词和修饰语）"""
        # 去掉动词前缀
        verbs = [
            '新增', '更新', '删除', '修改', '实现', '开发', '提供',
            '支持', '集成', '对接', '设计', '构建', '迁移', '优化',
            '重构', '配置', '部署', '查询', '创建',
        ]
        for verb in verbs:
            if content.startswith(verb):
                content = content[len(verb):]
                break

        # 按常见分隔词拆分
        words = re.split(r'[的及与和或包含支持包括]', content)

        # 过滤空词和短词
        return [w.strip() for w in words if len(w.strip()) >= 2]

    def normalize_module_name(self, module_name: str) -> str:
        """标准化模块名

        顺序：分割 → 去编号 → 去后缀 → 去空
        """
        # Step 1: 去掉层级分隔，取最后一段
        module_name = module_name.split(' > ')[-1].strip()

        # Step 2: 去掉编号前缀（支持 3.、3.1、3.1.2 等）
        module_name = re.sub(
            r'^[\d一二三四五六七八九十]+(?:\.[\d]+)*[\.、\s]+',
            '',
            module_name,
        )

        # Step 3: 去掉后缀
        for suffix in self.SECTION_SUFFIXES:
            if module_name.endswith(suffix):
                module_name = module_name[:-len(suffix)].strip()
                break

        # Step 4: 去空
        module_name = re.sub(r'\s+', '', module_name)

        return module_name or '未分类'
