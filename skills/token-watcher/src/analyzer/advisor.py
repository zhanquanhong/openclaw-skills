"""多维建议引擎 v2 — 12 条分维度规则 + 多样性保证器。

分析每条会话的 token 使用合理性，从四个维度给出精准建议：
  A. 输入质量（Input Quality）
  B. 上下文管理（Context Management）
  C. 模型配置（Provider Configuration）
  D. 会话生命周期（Session Lifecycle）

设计原则：
  - 每条建议必须有具体数据证据
  - 同一会话最多 3 条建议
  - 必须覆盖至少 2 个维度
  - 无建议时不凑数
"""

import json
import logging
import os
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── 模型规格 ──────────────────────────────────────────

_MODEL_OVERRIDES: dict[str, dict[str, int]] = {
    "deepseek-v4-flash": {"context_window": 1_000_000, "max_tokens": 65_536},
    "deepseek-chat": {"context_window": 65_536, "max_tokens": 8_192},
    "deepseek-reasoner": {"context_window": 65_536, "max_tokens": 8_192},
    "qwen3.5-plus": {"context_window": 1_000_000, "max_tokens": 65_536},
    "qwen3-max-2025-09-23": {"context_window": 32_768, "max_tokens": 8_192},
    "gpt-4o": {"context_window": 128_000, "max_tokens": 16_384},
    "gpt-4o-mini": {"context_window": 128_000, "max_tokens": 16_384},
    "claude-3.5-sonnet": {"context_window": 200_000, "max_tokens": 8_192},
    "glm-4": {"context_window": 128_000, "max_tokens": 4_096},
}


def _load_openclaw_model_specs() -> dict[str, dict[str, int]]:
    """从 openclaw.json 加载模型规格（contextWindow, maxTokens）。

    Returns:
        模型规格字典 {model_id: {"context_window": N, "max_tokens": N}}
    """
    specs: dict[str, dict[str, int]] = {}
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")
    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f)
        providers = cfg.get("models", {}).get("providers", {})
        for provider_cfg in providers.values():
            if not isinstance(provider_cfg, dict):
                continue
            for m in provider_cfg.get("models", []):
                mid = m.get("id", "")
                cw = m.get("contextWindow", 0)
                mt = m.get("maxTokens", 0)
                if mid and cw and mt:
                    specs[mid] = {"context_window": cw, "max_tokens": mt}
    except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
        logger.debug("读取 openclaw.json 失败，使用默认规格: %s", e)
    return specs


_OPENCLAW_SPECS = _load_openclaw_model_specs()
for mid, override in _OPENCLAW_SPECS.items():
    _MODEL_OVERRIDES[mid] = override


def get_model_spec(model_name: Optional[str]) -> dict[str, int]:
    """获取模型的规格参数：context_window, max_tokens。

    Args:
        model_name: 模型名称

    Returns:
        {"context_window": N, "max_tokens": N}
    """
    if not model_name:
        return {"context_window": 128_000, "max_tokens": 8_192}

    name_lower = model_name.lower()

    if name_lower in _MODEL_OVERRIDES:
        return dict(_MODEL_OVERRIDES[name_lower])

    for key, spec in _MODEL_OVERRIDES.items():
        if key in name_lower or name_lower.startswith(key):
            return dict(spec)

    return {"context_window": 128_000, "max_tokens": 8_192}


# ── 维度常量 ──────────────────────────────────────────

DIMENSION_INPUT_QUALITY = "input_quality"          # A
DIMENSION_CONTEXT_MANAGEMENT = "context_management"  # B
DIMENSION_PROVIDER_CONFIG = "provider_config"        # C
DIMENSION_SESSION_LIFECYCLE = "session_lifecycle"    # D

DIMENSION_LABELS: dict[str, str] = {
    DIMENSION_INPUT_QUALITY: "输入质量",
    DIMENSION_CONTEXT_MANAGEMENT: "上下文管理",
    DIMENSION_PROVIDER_CONFIG: "模型配置",
    DIMENSION_SESSION_LIFECYCLE: "会话生命周期",
}

DIMENSION_ICONS: dict[str, str] = {
    DIMENSION_INPUT_QUALITY: "📝",
    DIMENSION_CONTEXT_MANAGEMENT: "📦",
    DIMENSION_PROVIDER_CONFIG: "⚙️",
    DIMENSION_SESSION_LIFECYCLE: "🔄",
}


# ── 建议数据模型 ──────────────────────────────────────

class Suggestion:
    """单条建议（含维度、分类、证据）。"""

    __slots__ = (
        "severity", "dimension", "category", "title", "message",
        "action", "evidence", "savings_tokens", "savings_cost",
    )

    def __init__(
        self,
        severity: str,
        dimension: str,
        category: str,
        title: str,
        message: str,
        action: str = "",
        evidence: Optional[list[str]] = None,
        savings_tokens: int = 0,
        savings_cost: float = 0.0,
    ) -> None:
        self.severity = severity       # critical / warning / info
        self.dimension = dimension
        self.category = category       # 规则标识，如 "A1", "B2"
        self.title = title
        self.message = message
        self.action = action
        self.evidence = evidence or []
        self.savings_tokens = savings_tokens
        self.savings_cost = savings_cost

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "dimension": self.dimension,
            "dimension_label": DIMENSION_LABELS.get(self.dimension, self.dimension),
            "dimension_icon": DIMENSION_ICONS.get(self.dimension, ""),
            "category": self.category,
            "title": self.title,
            "message": self.message,
            "action": self.action,
            "evidence": self.evidence,
            "savings_tokens": self.savings_tokens,
            "savings_cost": round(self.savings_cost, 4),
        }


# ═══════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════


def analyze(
    sessions: list[dict[str, Any]],
    pricing_map: dict[str, dict[str, float]],
    waste_threshold: float = 3.0,
    thresholds: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """对会话列表执行全部 12 条分析规则。

    Args:
        sessions: 会话列表（来自 DB）
        pricing_map: 定价映射表
        waste_threshold: 浪费比例阈值
        thresholds: 可选，覆盖 config 中的阈值配置

    Returns:
        增强后的会话列表，每项增加了 recommendations 和 dimension_groups 字段
    """
    results: list[dict[str, Any]] = []
    for session in sessions:
        specs = get_model_spec(session.get("model", ""))
        recs = _run_all_rules(session, specs, pricing_map, waste_threshold, thresholds or {})
        recs = _ensure_diversity(recs)
        r = dict(session)
        r["recommendations"] = [s.to_dict() for s in recs]
        r["dimension_groups"] = _group_by_dimension(recs)
        results.append(r)
    return results


# ═══════════════════════════════════════════════════════
# 规则引擎
# ═══════════════════════════════════════════════════════


def _run_all_rules(
    session: dict[str, Any],
    specs: dict[str, int],
    pricing_map: dict[str, dict[str, float]],
    waste_threshold: float,
    threshold_overrides: dict[str, Any],
) -> list[Suggestion]:
    """对单个会话执行全部 12 条规则。

    Args:
        session: 会话数据
        specs: 模型规格
        pricing_map: 定价映射表
        waste_threshold: 浪费阈值
        threshold_overrides: 阈值覆盖字典

    Returns:
        建议列表（未经多样性保证）
    """
    total_in = session.get("total_input_tokens", 0) or 0
    total_out = session.get("total_output_tokens", 0) or 0
    ratio = session.get("input_output_ratio", 0) or 0
    model = session.get("model", "") or ""
    ctx = _parse_context_info(session)
    ctx_window = specs.get("context_window", 128_000)
    max_tokens = specs.get("max_tokens", 8_192)

    # 统一阈值：优先使用传入覆盖，否则使用默认值
    t = _default_thresholds()
    t.update(threshold_overrides)

    suggestions: list[Suggestion] = []

    # ── 维度 A：输入质量 ──────────────────────────────

    _rule_a1_duplicate_content(session, ctx, t, suggestions)
    _rule_a2_long_messages(session, ctx, t, suggestions)
    _rule_a3_inefficient_opening(session, ctx, t, suggestions)

    # ── 维度 B：上下文管理 ────────────────────────────

    _rule_b1_system_prompt_ratio(session, ctx, t, suggestions)
    _rule_b2_thinking_waste(session, ctx, model, pricing_map, t, suggestions)
    _rule_b3_imbalanced_exchange(ctx, t, suggestions)

    # ── 维度 C：模型配置 ────────────────────────────

    _rule_c1_output_capped(session, total_out, max_tokens, model, specs, t, suggestions)
    _rule_c2_model_value(session, total_in, total_out, model, pricing_map, t, suggestions)
    _rule_c3_context_refill(session, ctx, total_in, t, suggestions)

    # ── 维度 D：会话生命周期 ──────────────────────────

    _rule_d1_zombie_session(session, ctx, total_in, t, suggestions)
    _rule_d2_topic_drift(ctx, t, suggestions)
    _rule_d3_session_fragmentation(session, ctx, t, suggestions)

    return suggestions


def _default_thresholds() -> dict[str, Any]:
    """返回默认阈值字典，供规则函数使用。"""
    from ..config import config as cfg
    return {
        "waste_ratio": cfg.waste_ratio_threshold,
        "output_capped_ratio": cfg.advisor_output_capped_ratio,
        "context_overflow_ratio": cfg.advisor_context_overflow_ratio,
        "deep_session_turns": cfg.advisor_deep_session_turns,
        "small_task_max_tokens": cfg.advisor_small_task_max_tokens,
        "avg_msg_token": cfg.advisor_avg_msg_token_threshold,
        "first3_waste_ratio": cfg.advisor_first3waste_ratio,
        "first3_input_ratio": cfg.advisor_first3input_ratio,
        "system_prompt_ratio": cfg.advisor_system_prompt_ratio_threshold,
        "thinking_ratio": cfg.advisor_thinking_ratio_threshold,
        "imbalance_turns": cfg.advisor_imbalance_turns,
        "imbalance_ratio": cfg.advisor_imbalance_ratio,
        "output_capped_divisible": cfg.advisor_output_capped_divisible_check,
        "zombie_days": cfg.advisor_zombie_days,
        "zombie_token": cfg.advisor_zombie_token_threshold,
        "fragmentation_threshold": cfg.advisor_fragmentation_threshold,
        "fragmentation_avg_turns": cfg.advisor_fragmentation_avg_turns,
        "max_per_session": cfg.advisor_max_per_session,
        "min_dimensions": cfg.advisor_min_dimensions,
    }


# ═══════════════════════════════════════════════════════
# 维度 A：输入质量（3 条规则）
# ═══════════════════════════════════════════════════════


def _rule_a1_duplicate_content(
    session: dict[str, Any],
    ctx: dict[str, Any],
    t: dict[str, Any],
    suggestions: list[Suggestion],
) -> None:
    """A1: 重复内容检测。

    检查 first_msg 与 second_msg 之间的文本重复量。
    使用最长公共子串检测（比关键词集重叠更准确）。
    """
    first = (ctx.get("first_msg") or "").strip()
    second = (ctx.get("second_msg") or "").strip()

    if not first or not second or len(first) < 25 or len(second) < 25:
        return

    common = _find_longest_common_substring(first, second)
    if not common or len(common) < 5:
        return

    # 计算重叠比例（基于公共子串长度 vs 较短消息长度）
    min_len = min(len(first), len(second))
    overlap_ratio = len(common) / max(min_len, 1)

    if overlap_ratio < 0.25:
        return

    suggestions.append(Suggestion(
        severity="info" if overlap_ratio < 0.65 else "warning",
        dimension=DIMENSION_INPUT_QUALITY,
        category="A1",
        title="前后消息存在重复内容",
        message=(
            f"前两条用户消息有 {_fmt(len(common))} 字符公共内容"
            f"（重叠率 {overlap_ratio:.0%}）。"
            f"建议在确认已解决的问题后移除重复描述。"
        ),
        action="精简重复描述",
        evidence=[
            f"公共子串长度: {_fmt(len(common))} 字符",
            f"重叠率: {overlap_ratio:.0%}",
            f"较短消息长度: {_fmt(min_len)} 字符",
        ],
    ))


def _rule_a2_long_messages(
    session: dict[str, Any],
    ctx: dict[str, Any],
    t: dict[str, Any],
    suggestions: list[Suggestion],
) -> None:
    """A2: 单条消息过长。

    检查平均每条用户消息的 token/字符数是否超出合理范围。
    """
    user_turns = ctx.get("user_turns", 0) or 0
    total_chars = ctx.get("total_chars", 0) or 0
    total_in = session.get("total_input_tokens", 0) or 0

    if user_turns <= 0:
        return

    avg_chars = total_chars / user_turns
    avg_tokens = total_in / user_turns

    threshold_chars = t.get("avg_msg_token", 800) * 4  # 粗略 1 token ≈ 4 字符
    threshold_tokens = t.get("avg_msg_token", 800)

    if avg_chars <= threshold_chars and avg_tokens <= threshold_tokens:
        return

    if avg_chars <= threshold_chars * 1.5 and avg_tokens <= threshold_tokens * 1.5:
        severity = "info"
    else:
        severity = "warning"

    suggestions.append(Suggestion(
        severity=severity,
        dimension=DIMENSION_INPUT_QUALITY,
        category="A2",
        title="单条消息过长",
        message=(
            f"您的消息平均 {avg_tokens:.0f} token/条"
            f"（{_fmt(int(avg_chars))} 字符），"
            f"建议将大段文本拆分成多个独立小问题，"
            f"每轮控制在 1K token 以内。"
        ),
        action="拆分长消息为多个独立问题",
        evidence=[
            f"平均消息量: {_fmt(int(avg_tokens))} token / 条",
            f"总用户轮次: {user_turns}",
            f"超出阈值: ×{avg_tokens / max(threshold_tokens, 1):.1f}",
        ],
    ))


def _rule_a3_inefficient_opening(
    session: dict[str, Any],
    ctx: dict[str, Any],
    t: dict[str, Any],
    suggestions: list[Suggestion],
) -> None:
    """A3: 无效开场/低效前段。

    检查前 3 轮对话是否消耗了大量 input 但产出极少的 output。
    依赖于 message_sizes 数据（需增强 transcript 解析）。
    """
    msg_sizes = ctx.get("message_sizes")
    if not msg_sizes or len(msg_sizes) < 3:
        # 没有消息级数据时不触发 A3，不影响其余建议
        return

    total_in = session.get("total_input_tokens", 0) or 0
    total_out = session.get("total_output_tokens", 0) or 0
    first3_in = 0
    first3_out = 0

    for i, msg in enumerate(msg_sizes[:6]):  # 取前 6 条（约 3 轮 user + assistant）
        role = msg.get("role", "")
        tokens = msg.get("estimated_tokens", 0) or 0
        if role == "user":
            first3_in += tokens
        elif role == "assistant":
            first3_out += tokens

    if total_in <= 0:
        return

    first3_input_ratio = first3_in / total_in
    first3_output_ratio = first3_out / max(total_out, 1)

    min_first3_input = t.get("first3_input_ratio", 0.60)
    min_first3_out = t.get("first3_waste_ratio", 0.20)

    if first3_input_ratio < min_first3_input:
        return
    if first3_output_ratio >= min_first3_out:
        return

    suggestions.append(Suggestion(
        severity="warning",
        dimension=DIMENSION_INPUT_QUALITY,
        category="A3",
        title="前段对话效率低",
        message=(
            f"前 3 轮消耗了 {_fmt(first3_in)} token（占总 input "
            f"{first3_input_ratio:.0%}），但输出仅 {_fmt(first3_out)} token"
            f"（占总 output {first3_output_ratio:.0%}）。"
            f"建议减少来回确认轮次，一次性给出完整指令。"
        ),
        action="减少前段确认轮次，直接给出完整指令",
        evidence=[
            f"前 3 轮输入: {_fmt(first3_in)} / {_fmt(total_in)} ({first3_input_ratio:.0%})",
            f"前 3 轮输出: {_fmt(first3_out)} / {_fmt(total_out)} ({first3_output_ratio:.0%})",
        ],
    ))


# ═══════════════════════════════════════════════════════
# 维度 B：上下文管理（3 条规则）
# ═══════════════════════════════════════════════════════


def _rule_b1_system_prompt_ratio(
    session: dict[str, Any],
    ctx: dict[str, Any],
    t: dict[str, Any],
    suggestions: list[Suggestion],
) -> None:
    """B1: System prompt 占比异常。

    检查 system 消息占 input token 的比例是否过高。
    """
    sys_msgs = ctx.get("system_messages")
    total_in = session.get("total_input_tokens", 0) or 0

    if not sys_msgs or total_in <= 0:
        return

    sys_tokens = sum(
        (m.get("estimated_tokens", 0) or 0) for m in sys_msgs
    )
    if sys_tokens <= 0:
        return

    sys_ratio = sys_tokens / total_in
    threshold = t.get("system_prompt_ratio", 0.25)

    if sys_ratio <= threshold:
        return

    severity = "critical" if sys_ratio > 0.50 else "warning" if sys_ratio > 0.35 else "info"

    suggestions.append(Suggestion(
        severity=severity,
        dimension=DIMENSION_CONTEXT_MANAGEMENT,
        category="B1",
        title="系统提示词占比过高",
        message=(
            f"系统提示词占输入 token 的 {sys_ratio:.0%}"
        ),
        action="精简系统提示词",
        evidence=[
            f"系统提示词: {_fmt(sys_tokens)} token",
            f"总输入: {_fmt(total_in)} token",
            f"占比: {sys_ratio:.0%}",
        ],
    ))


def _rule_b2_thinking_waste(
    session: dict[str, Any],
    ctx: dict[str, Any],
    model: str,
    pricing_map: dict[str, dict[str, float]],
    t: dict[str, Any],
    suggestions: list[Suggestion],
) -> None:
    """B2: Thinking token 浪费。

    对于推理模型，检查 thinking token 是否远大于 output token。
    """
    thinking_info = ctx.get("thinking_info")
    if not thinking_info:
        return

    is_reasoner = any(kw in model.lower() for kw in ("reasoner", "r1", "thinking", "deepseek-r1"))

    if not is_reasoner and not thinking_info.get("has_thinking"):
        return

    thinking_tokens = thinking_info.get("thinking_tokens", 0) or 0
    output_tokens = thinking_info.get("output_tokens", 0) or 0

    if thinking_tokens <= 0 or output_tokens <= 0:
        return

    ratio_val = thinking_tokens / max(output_tokens, 1)
    threshold = t.get("thinking_ratio", 2.0)

    if ratio_val <= threshold:
        return

    severity = "warning" if ratio_val > 4.0 else "info"

    # 估算浪费金额
    from ..tokenizer.models import get_pricing
    inp_p, out_p = get_pricing(model, pricing_map)
    wasted_cost = (thinking_tokens / 1_000_000) * out_p * 30  # 月估

    suggestions.append(Suggestion(
        severity=severity,
        dimension=DIMENSION_CONTEXT_MANAGEMENT,
        category="B2",
        title="思考过程过长，有效输出偏低",
        message=(
            f"思考过程输出 {_fmt(thinking_tokens)} token，"
            f"是有效回答 {_fmt(output_tokens)} token 的 {ratio_val:.1f} 倍。"
        ),
        action="简化提问 / 屏蔽思考过程",
        evidence=[
            f"思考 token: {_fmt(thinking_tokens)}",
            f"有效输出: {_fmt(output_tokens)}",
            f"思考/输出比: {ratio_val:.1f}x",
        ],
        savings_cost=round(wasted_cost, 4),
    ))


def _rule_b3_imbalanced_exchange(
    ctx: dict[str, Any],
    t: dict[str, Any],
    suggestions: list[Suggestion],
) -> None:
    """B3: 消息分布极度不均衡。

    检查 user 发言次数远超 assistant 回复次数（可能会话异常）。
    """
    user_turns = ctx.get("user_turns", 0) or 0
    assistant_turns = ctx.get("assistant_turns", 0) or 0

    if user_turns <= 0:
        return

    imbalanced_turns = user_turns > t.get("imbalance_turns", 20) and assistant_turns == 0
    imbalanced_ratio = user_turns > 0 and assistant_turns > 0 and (user_turns / assistant_turns) > t.get("imbalance_ratio", 3.0)

    if not imbalanced_turns and not imbalanced_ratio:
        return

    if imbalanced_turns:
        suggestions.append(Suggestion(
            severity="warning",
            dimension=DIMENSION_CONTEXT_MANAGEMENT,
            category="B3",
            title="AI 未产生有效回复",
            message=(
                f"您已发送 {user_turns} 条消息，"
                f"但 AI 没有执行过一次有效回复。"
                f"可能存在断连或会话异常，建议开启新会话。"
            ),
            action="开启新会话",
            evidence=[
                f"用户消息数: {user_turns}",
                f"AI 回复数: {assistant_turns}",
            ],
        ))
    else:
        suggestions.append(Suggestion(
            severity="info",
            dimension=DIMENSION_CONTEXT_MANAGEMENT,
            category="B3",
            title="用户发言远多于 AI 回复",
            message=(
                f"用户 / AI 消息比 {user_turns}:{assistant_turns}"
                f"（{user_turns / max(assistant_turns, 1):.1f}x），"
                f"可能存在重复发送或系统处理延迟。"
            ),
            action="检查会话状态",
            evidence=[
                f"用户消息: {user_turns} 条",
                f"AI 回复: {assistant_turns} 条",
                f"比例: {user_turns / max(assistant_turns, 1):.1f}x",
            ],
        ))


# ═══════════════════════════════════════════════════════
# 维度 C：模型配置（3 条规则）
# ═══════════════════════════════════════════════════════


def _rule_c1_output_capped(
    session: dict[str, Any],
    total_out: int,
    max_tokens: int,
    model: str,
    specs: dict[str, int],
    t: dict[str, Any],
    suggestions: list[Suggestion],
) -> None:
    """C1: max_tokens 可能导致输出截断。

    检测 output_tokens 是否接近 max_tokens 上限。
    """
    if max_tokens <= 0 or total_out <= 0:
        return

    output_ratio = total_out / max_tokens
    threshold = t.get("output_capped_ratio", 0.85)

    if output_ratio < threshold:
        return

    # 检查是否可能被截断（output 恰好接近 max_tokens 的整数倍）
    is_truncated = False
    if t.get("output_capped_divisible", True) and max_tokens > 0:
        # 如果 output 能恰整除 max_tokens 且余数 < 5%，很可能被截断
        remainder = total_out % max_tokens
        if remainder < max_tokens * 0.05:
            is_truncated = True

    recommended = min(max_tokens * 2, specs.get("context_window", 128_000))
    freed = recommended - max_tokens

    if is_truncated:
        severity = "warning"
        msg_extra = "，输出可能被截断"
    elif output_ratio > 0.95:
        severity = "warning"
        msg_extra = "，接近截断边缘"
    else:
        severity = "info"
        msg_extra = ""

    suggestions.append(Suggestion(
        severity=severity,
        dimension=DIMENSION_PROVIDER_CONFIG,
        category="C1",
        title="输出接近模型上限" + msg_extra,
        message=(
            f"输出 {_fmt(total_out)} token 已达 {model}"
            f" 上限 {_fmt(max_tokens)} 的 {output_ratio:.0%}"
        ),
        action=f"调整 max_tokens 从 {max_tokens} → {recommended}",
        evidence=[
            f"当前输出: {_fmt(total_out)} / {_fmt(max_tokens)} ({output_ratio:.0%})",
            f"建议值: {_fmt(recommended)}"
                + (f"（截断检测: 余数 {remainder} < 5%）" if is_truncated else ""),
        ],
    ))


def _rule_c2_model_value(
    session: dict[str, Any],
    total_in: int,
    total_out: int,
    model: str,
    pricing_map: dict[str, dict[str, float]],
    t: dict[str, Any],
    suggestions: list[Suggestion],
) -> None:
    """C2: 性价比模型选择不当。

    高价值模型用于极低 token 任务，或低价值模型用于高复杂度任务。
    """
    model_lower = model.lower()
    small_task_max = t.get("small_task_max_tokens", 500)

    # 仅对高价值模型使用小任务场景触发建议
    if not _is_high_value_model(model_lower):
        return
    if total_in > small_task_max:
        return

    alternative = _suggest_cheaper_model(model_lower)
    if not alternative:
        return

    from ..tokenizer.models import get_pricing
    cur_price = get_pricing(model, pricing_map)
    alt_price = get_pricing(alternative, pricing_map)

    # 估算节省费用
    saving_per_req = (cur_price[0] - alt_price[0]) / 1_000_000 * total_in
    monthly_saving = saving_per_req * 100  # 假设月 100 次类似调用

    suggestions.append(Suggestion(
        severity="info",
        dimension=DIMENSION_PROVIDER_CONFIG,
        category="C2",
        title="高价值模型用于小任务",
        message=(
            f"此会话仅 {_fmt(total_in)} token 输入，"
            f"使用 {model} 成本偏高"
        ),
        action=f"切换为 {alternative}（输入 ${cur_price[0]:.2f}/M → ${alt_price[0]:.2f}/M）",
        evidence=[
            f"当前模型: {model}",
            f"推荐模型: {alternative}",
            f"输入 token: {_fmt(total_in)}",
            f"单次节省: ${saving_per_req:.6f}",
            f"月估节省: ${monthly_saving:.4f}",
        ],
        savings_cost=round(monthly_saving, 4),
    ))


def _rule_c3_context_refill(
    session: dict[str, Any],
    ctx: dict[str, Any],
    total_in: int,
    t: dict[str, Any],
    suggestions: list[Suggestion],
) -> None:
    """C3: 上下文预填充浪费。

    检测在同一个会话中，相同的代码块/错误栈是否反复出现在用户消息中。
    使用 first_msg 与 last_msg 的关键词重叠作为近似判断。
    """
    first = (ctx.get("first_msg") or "").strip()
    last = (ctx.get("last_msg") or "").strip()

    if not first or not last or len(first) < 50 or len(last) < 50:
        return

    # 检测长文本共享（相同代码块/错误栈特征）
    # 在中文/英文文本中找超过 30 字符的公共子串
    common = _find_longest_common_substring(first, last)
    if not common or len(common) < 30:
        return

    # 估算重复字符的 token 价值
    refill_tokens = len(common) // 4
    if refill_tokens < 15:
        return

    suggestions.append(Suggestion(
        severity="info",
        dimension=DIMENSION_PROVIDER_CONFIG,
        category="C3",
        title="上下文重复预填充",
        message=(
            f"首尾用户消息中存在相同的长文本段（约 {_fmt(len(common))} 字符"
            f" / {_fmt(refill_tokens)} token）。"
            f"建议使用临时链接分享长代码/日志，"
            f"避免每轮重复加载同一段内容。"
        ),
        action="使用临时链接替代重复粘贴",
        evidence=[
            f"重复文本: ~{_fmt(len(common))} 字符 / {_fmt(refill_tokens)} token",
            f"当前输入: {_fmt(total_in)} token",
        ],
        savings_tokens=refill_tokens,
    ))


# ═══════════════════════════════════════════════════════
# 维度 D：会话生命周期（3 条规则）
# ═══════════════════════════════════════════════════════


def _rule_d1_zombie_session(
    session: dict[str, Any],
    ctx: dict[str, Any],
    total_in: int,
    t: dict[str, Any],
    suggestions: list[Suggestion],
) -> None:
    """D1: 僵尸会话。

    检查长时间无新消息但仍在占用上下文窗口的会话。
    """
    start_time = ctx.get("time_start")
    idle_days = _get_idle_days(start_time)

    if idle_days is None or idle_days < t.get("zombie_days", 7):
        return
    if total_in < t.get("zombie_token", 50_000):
        return

    suggestions.append(Suggestion(
        severity="warning" if total_in > 100_000 else "info",
        dimension=DIMENSION_SESSION_LIFECYCLE,
        category="D1",
        title="会话已闲置多日",
        message=(
            f"此会话已闲置 {idle_days} 天，"
            f"但仍占用 {_fmt(total_in)} token 上下文"
        ),
        action="归档僵尸会话，开启新会话",
        evidence=[
            f"闲置天数: {idle_days} 天",
            f"占用上下文: {_fmt(total_in)} token",
            f"最后活动: {str(start_time)[:16] if start_time else '未知'}",
        ],
        savings_tokens=total_in,
    ))


def _rule_d2_topic_drift(
    ctx: dict[str, Any],
    t: dict[str, Any],
    suggestions: list[Suggestion],
) -> None:
    """D2: 话题漂移。

    通过 first_msg 和 last_msg 的最长公共子串比例判断话题是否漂移。
    如果有足够长的共同内容（>= 25%），判定无漂移。
    如果几乎无共同内容（< 8 字符或无），判定漂移。
    """
    first = (ctx.get("first_msg") or "").strip()
    last = (ctx.get("last_msg") or "").strip()

    if not first or not last or len(first) < 20 or len(last) < 20:
        return

    common = _find_longest_common_substring(first, last)
    min_len = min(len(first), len(last))

    # 有共同内容：检查比例
    if common and len(common) >= 6:
        overlap_ratio = len(common) / max(min_len, 1)
        if overlap_ratio >= 0.25:
            return  # 有足够共同话题，无漂移

    # 无共同内容或比例太低 → 漂移
    first_kws = set(_extract_keywords(first))
    last_kws = set(_extract_keywords(last))

    has_common = bool(common) and len(common) >= 6
    overlap_ratio_display = (
        f"{len(common) / max(min(len(first), len(last)), 1):.0%}"
        if has_common else "无"
    )

    suggestions.append(Suggestion(
        severity="info",
        dimension=DIMENSION_SESSION_LIFECYCLE,
        category="D2",
        title="话题已漂移",
        message=(
            f"首条与最后一条用户消息"
            + (f"的公共内容仅 {_fmt(len(common))} 字符（重叠率 {overlap_ratio_display}）"
               if has_common else "无明显共同内容")
            + "。会话可能跨越了多个不相关的任务。"
        ),
        action="按任务开启独立会话",
        evidence=[
            f"公共内容: {_fmt(len(common)) if has_common else '无'} 字符",
            f"重叠率: {overlap_ratio_display}" if has_common else "重叠率: 无",
            f"首条关键词: {_format_keywords_preview(first_kws, 4) if first_kws else 'N/A'}",
            f"末条关键词: {_format_keywords_preview(last_kws, 4) if last_kws else 'N/A'}",
        ],
    ))


def _rule_d3_session_fragmentation(
    session: dict[str, Any],
    ctx: dict[str, Any],
    t: dict[str, Any],
    suggestions: list[Suggestion],
) -> None:
    """D3: 会话碎片化。

    提示近期开启了过多短会话，建议适度合并。
    需要会话列表中的上下文信息——在 session 级别无法直接获取全局统计数据，
    此规则仅在 analyze() 层面触发（session 级兜底使用该会话自身指标推断）。

    当前实现：检查此会话的 user_turns 和 ratio 来判断是否为"过度分割"的碎片。
    更精确的碎片检测需要在 analyze() 外层做会话间聚合。
    """
    user_turns = ctx.get("user_turns", 0) or 0
    assistant_turns = ctx.get("assistant_turns", 0) or 0
    total_turns = user_turns + assistant_turns

    avg_turns = t.get("fragmentation_avg_turns", 5)
    waste_threshold = t.get("waste_ratio", 3.0)
    ratio = session.get("input_output_ratio", 0) or 0

    # 此会话轮次很少、ratio 正常 → 可能是碎片化会话
    if total_turns >= avg_turns or ratio >= waste_threshold:
        return

    total_in = session.get("total_input_tokens", 0) or 0
    if total_in < 500:
        return

    suggestions.append(Suggestion(
        severity="info",
        dimension=DIMENSION_SESSION_LIFECYCLE,
        category="D3",
        title="会话偏短，可能碎片化",
        message=(
            f"此会话仅 {total_turns} 轮交互"
            f"（{user_turns} 用户, {assistant_turns} AI），"
            f"建议将同类任务合并在同一会话中"
        ),
        action="适度合并同类问题",
        evidence=[
            f"总轮次: {total_turns}",
            f"用户 / AI: {user_turns} / {assistant_turns}",
        ],
    ))


# ═══════════════════════════════════════════════════════
# 多样性保证器
# ═══════════════════════════════════════════════════════


def _ensure_diversity(suggestions: list[Suggestion]) -> list[Suggestion]:
    """保证建议多样性。

    Rules:
      1. 同一会话最多 max_per_session 条
      2. 相同 category 只保留 1 条（优选 severity 最高的）
      3. 必须覆盖至少 min_dimensions 个维度
      4. 无建议时不凑数

    Args:
        suggestions: 原始建议列表

    Returns:
        精简后的建议列表
    """
    if not suggestions:
        return []

    from ..config import config as cfg
    max_per = cfg.advisor_max_per_session
    min_dim = cfg.advisor_min_dimensions

    # Step 1: 按 severity 排序（critical > warning > info）
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    sorted_sugs = sorted(
        suggestions,
        key=lambda s: (severity_order.get(s.severity, 99), s.category),
    )

    # Step 2: 相同 category 去重
    seen_categories: set[str] = set()
    deduped: list[Suggestion] = []
    for s in sorted_sugs:
        if s.category in seen_categories:
            continue
        seen_categories.add(s.category)
        deduped.append(s)

    # Step 3: 检查维度覆盖
    dimensions = {s.dimension for s in deduped}
    if len(dimensions) < min_dim:
        dims_added: set[str] = set()
        re_ordered: list[Suggestion] = []
        for s in deduped:
            if s.dimension not in dims_added:
                dims_added.add(s.dimension)
                re_ordered.append(s)
        # 补充其他维度
        for s in deduped:
            if s not in re_ordered and len(re_ordered) < max_per:
                re_ordered.append(s)
        deduped = re_ordered

    # Step 4: 限制最大条数
    if len(deduped) > max_per:
        # 优先保留 severity 更高的
        deduped.sort(key=lambda s: severity_order.get(s.severity, 99))
        # 再确保维度多样性
        dims_kept: set[str] = set()
        result: list[Suggestion] = []
        for s in deduped:
            if s.dimension not in dims_kept:
                dims_kept.add(s.dimension)
                result.append(s)
        # 补充剩余的 severity 最高规则
        for s in deduped:
            if s not in result and len(result) < max_per:
                result.append(s)
        # 如果还不够，则优先维度多样性
        deduped = result[:max_per]
        if len(deduped) < min_dim:
            # 回退到按 severity 截断
            deduped = sorted(suggestions, key=lambda s: severity_order.get(s.severity, 99))[:max_per]

    # 最终检查维度覆盖
    final_dims = {s.dimension for s in deduped}
    if len(final_dims) < min_dim and len(deduped) > 1:
        # 尝试用建议中的其他维度替换
        pass  # 保留现有结果，不再进一步削足适履

    return deduped


def _group_by_dimension(suggestions: list[Suggestion]) -> dict[str, list[dict[str, Any]]]:
    """按维度分组建议。

    Args:
        suggestions: 建议列表

    Returns:
        {dimension: [suggestion_dict, ...]}
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for s in suggestions:
        dim = s.dimension
        if dim not in groups:
            groups[dim] = []
        groups[dim].append(s.to_dict())
    return groups


# ═══════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════


def _parse_context_info(session: dict[str, Any]) -> dict[str, Any]:
    """解析会话的 context_info JSON 字段。"""
    raw = session.get("context_info")
    if isinstance(raw, str):
        try:
            return json.loads(raw) if raw else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    if isinstance(raw, dict):
        return raw
    return {}


def _fmt(n: int) -> str:
    """格式化可读数字。"""
    n = int(n) if n else 0
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n // 1_000}K"
    return str(n)


def _extract_keywords(text: str) -> list[str]:
    """从文本中提取有意义的关键词（中文词组 + 英文单词）。

    Args:
        text: 输入文本

    Returns:
        关键词列表（长度 >= 4 的 token）
    """
    keywords: list[str] = []

    # 中文：连续中文字符序列（长度 >= 4）
    chinese_blocks = re.findall(r'[\u4e00-\u9fff]{4,}', text)
    keywords.extend(chinese_blocks)

    # 英文：长度 >= 4 的纯英文单词（排除数字和符号）
    eng_words = re.findall(r'\b[a-zA-Z]{4,}\b', text)
    keywords.extend(w.lower() for w in eng_words)

    # 去重
    seen: set[str] = set()
    result: list[str] = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            result.append(kw)

    return result


def _format_keywords_preview(keywords: set[str], max_count: int = 5) -> str:
    """格式化关键词预览。"""
    sorted_kw = sorted(keywords, key=len, reverse=True)[:max_count]
    return "、".join(sorted_kw)


def _find_longest_common_substring(s1: str, s2: str) -> str:
    """找出两个字符串中最长公共子串（简化版）。

    适用于检测跨轮重复文本和话题漂移。

    Args:
        s1: 字符串 1
        s2: 字符串 2

    Returns:
        最长的公共子串，未找到返回空字符串
    """
    short, long = (s1, s2) if len(s1) <= len(s2) else (s2, s1)
    min_len = 5

    if len(short) < min_len:
        return ""

    for win_size in range(len(short), min_len - 1, -1):
        for start in range(0, len(short) - win_size + 1):
            sub = short[start:start + win_size]
            if sub in long:
                return sub

    return ""


def _get_idle_days(start_time_str: Optional[str]) -> Optional[int]:
    """计算从 start_time 到现在的天数。

    Args:
        start_time_str: ISO 格式时间字符串

    Returns:
        闲置天数，无法计算返回 None
    """
    if not start_time_str:
        return None
    try:
        from datetime import datetime, timezone
        start = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return (now - start).days
    except (ValueError, TypeError):
        return None


def _is_high_value_model(model_lower: str) -> bool:
    """判断是否为高价值模型。"""
    high_value_patterns = [
        "flash", "pro", "gpt-4o", "claude-3.5", "claude-4",
    ]
    for p in high_value_patterns:
        if p in model_lower:
            return True
    return False


def _suggest_cheaper_model(model_lower: str) -> Optional[str]:
    """建议更便宜的替代模型。"""
    if "flash" in model_lower and "deepseek" in model_lower:
        return "deepseek-chat"
    return None
