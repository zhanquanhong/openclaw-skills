"""输入内容分段分析。

将用户输入拆分为：系统提示词、对话历史、代码片段、普通文本。
"""

import re
from typing import Optional


class ContentSegmenter:
    """输入内容分段器。"""

    # 代码块正则：```lang 包裹的内容
    CODE_BLOCK_RE = re.compile(r"```[\w]*\n(.*?)\n```", re.DOTALL)

    @classmethod
    def segment_user_input(cls, text: str) -> dict[str, int]:
        """将用户输入内容分段，返回各段占用字数（非 token）。

        Args:
            text: 用户输入文本

        Returns:
            {"code": int, "text": int}
        """
        code_chars = 0
        for match in cls.CODE_BLOCK_RE.finditer(text):
            code_chars += len(match.group(0))
        text_chars = len(text) - code_chars
        return {
            "code": code_chars,
            "text": text_chars,
        }

    @classmethod
    def segment_conversation_for_report(
        cls,
        messages: list[dict],
        system_prompt_threshold: int = 0,
    ) -> list[dict]:
        """将会话消息分段，用于报告展示。

        Args:
            messages: 消息列表（含 token_count）
            system_prompt_threshold: 系统提示词阈值字符数

        Returns:
            分段列表，每项 {label, tokens, type, detail}
        """
        segments: list[dict] = []

        # 统计各角色 token
        user_tokens = 0
        assistant_tokens = 0
        system_tokens = 0
        thinking_tokens = 0

        for msg in messages:
            role = msg.get("role", "")
            tokens = msg.get("token_count", 0)
            content_type = msg.get("content_type", "text")

            if content_type == "thinking":
                thinking_tokens += tokens
            elif role == "system":
                system_tokens += tokens
            elif role == "user":
                user_tokens += tokens
            elif role == "assistant":
                assistant_tokens += tokens

        if system_tokens > 0:
            segments.append({
                "label": "系统提示词",
                "tokens": system_tokens,
                "type": "system",
                "detail": f"{system_tokens} tokens",
            })

        if user_tokens > 0:
            segments.append({
                "label": "用户输入",
                "tokens": user_tokens,
                "type": "user",
                "detail": f"{user_tokens} tokens",
            })

        if assistant_tokens > 0:
            segments.append({
                "label": "助手输出",
                "tokens": assistant_tokens,
                "type": "assistant",
                "detail": f"{assistant_tokens} tokens",
            })

        if thinking_tokens > 0:
            segments.append({
                "label": "内部思考",
                "tokens": thinking_tokens,
                "type": "thinking",
                "detail": f"{thinking_tokens} tokens",
            })

        return segments
