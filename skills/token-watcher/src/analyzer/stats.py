"""统计分析模块。"""

from typing import Any

from .tokenizer.engine import TokenCounter
from .tokenizer.models import get_pricing


class StatsAnalyzer:
    """会话统计分析。"""

    def __init__(self, pricing_map: dict[str, dict[str, float]]) -> None:
        self.pricing_map = pricing_map

    @staticmethod
    def calc_conversation_stats(
        conv: dict[str, Any],
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """计算单会话的统计指标。

        Args:
            conv: 会话基本信息
            messages: 消息列表（已含 token_count）

        Returns:
            增强后的会话 dict
        """
        total_in = sum(
            m.get("token_count", 0)
            for m in messages
            if m.get("role") in ("user", "system")
        )
        total_out = sum(
            m.get("token_count", 0)
            for m in messages
            if m.get("role") == "assistant"
            and m.get("content_type", "text") == "text"
        )
        ratio = round(total_in / total_out, 2) if total_out > 0 else 0.0

        model = conv.get("model", "")
        inp_price, out_price = get_pricing(model, self.pricing_map)
        cost = TokenCounter.estimate_cost(total_in, total_out,
                                          inp_price, out_price)

        return {
            **conv,
            "total_input_tokens": total_in,
            "total_output_tokens": total_out,
            "input_output_ratio": ratio,
            "message_count": len(messages),
            "cost_estimate": round(cost, 6),
        }
