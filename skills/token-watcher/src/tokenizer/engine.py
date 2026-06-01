"""Token 计数引擎。

支持两种计数模式：
  - tiktoken 本地估算（按模型编码）
  - 真实值标记（从 API usage 字段获取）
"""

import logging
import tiktoken
from typing import Optional

from .models import resolve_encoding, ENCODING_MAX_TOKENS

logger = logging.getLogger(__name__)


class TokenCounter:
    """Token 计数器，支持多模型编码。"""

    _cache: dict[str, tiktoken.Encoding] = {}

    @classmethod
    def count(cls, text: str, model: Optional[str] = None,
              encoding_name: Optional[str] = None) -> int:
        """统计文本的 token 数。

        Args:
            text: 待统计的文本
            model: 模型名（用于自动解析 encoding）
            encoding_name: 直接指定 encoding 名（优先级高于 model）

        Returns:
            token 数量。发生错误时返回 0 并记录警告。
        """
        if not text:
            return 0

        enc_name = encoding_name or resolve_encoding(model)

        try:
            enc = cls._get_encoding(enc_name)
            return len(enc.encode(text))
        except Exception as e:
            logger.warning("Token 计数失败 (model=%s, enc=%s): %s",
                           model, enc_name, e)
            # 兜底：按字符估算
            return cls._rough_estimate(text)

    @classmethod
    def count_messages(cls, messages: list[dict],
                       model: Optional[str] = None) -> list[dict]:
        """批量统计消息列表的 token 数，返回增强后的消息列表。

        每条消息会新增 token_count 字段。

        Args:
            messages: 消息列表，每项需有 "role" 和 "content" 字段
            model: 模型名

        Returns:
            增加了 token_count 的消息列表
        """
        result = []
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")

            # 对于 assistant 消息，跳过 thinking 和 tool_call 类型
            content_type = msg.get("content_type", "text")
            if content_type in ("thinking", "tool_call"):
                tc = 0
            else:
                tc = cls.count(content, model)

            result.append({**msg, "token_count": tc})

        return result

    @classmethod
    def estimate_cost(cls, input_tokens: int, output_tokens: int,
                      input_price: float, output_price: float) -> float:
        """估算费用。

        Args:
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
            input_price: 每百万输入 token 的价格 (USD)
            output_price: 每百万输出 token 的价格 (USD)

        Returns:
            估算费用 (USD)
        """
        return (input_tokens / 1_000_000 * input_price +
                output_tokens / 1_000_000 * output_price)

    @classmethod
    def _rough_estimate(cls, text: str) -> int:
        """最基础的字符估算（兜底方案）。"""
        # 中文字符约 2 token/字，英文约 4 字符/token
        cn_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        en_chars = len(text) - cn_chars
        return cn_chars // 2 + en_chars // 4 + 1

    @classmethod
    def _get_encoding(cls, name: str) -> tiktoken.Encoding:
        """获取或缓存 Encoding 实例。"""
        if name not in cls._cache:
            cls._cache[name] = tiktoken.get_encoding(name)
        return cls._cache[name]

    @staticmethod
    def _fmt_readable(n: int) -> str:
        """格式化数字为可读形式，如 1500→1.5K, 704908→704K。"""
        n = int(n) if n else 0
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n//1000}K"
        return str(n)
