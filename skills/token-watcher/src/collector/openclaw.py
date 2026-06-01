"""OpenClaw 会话采集器。

通过 `openclaw sessions --json` CLI 命令获取会话列表和 token 统计。
并从 transcript 文件中提取用户消息和对话上下文信息。
"""

import json
import logging
import os
import re
import subprocess
from datetime import datetime
from typing import Any, Optional

from .base import BaseCollector
from ..tokenizer.engine import TokenCounter

logger = logging.getLogger(__name__)

# session store 路径
SESSION_STORE_DIR: str = os.path.expanduser(
    "~/.openclaw/agents/main/sessions"
)

# 渠道可读名称
CHANNEL_NAMES = {
    "feishu": "飞书",
    "telegram": "Telegram",
    "discord": "Discord",
    "main": "主会话",
    "subagent": "子智能体",
    "openresponses": "API 调用",
}


class OpenClawCollector(BaseCollector):
    """OpenClaw 会话采集器。"""

    def __init__(self, history_days: int = 7, session_limit: int = 50) -> None:
        self.history_days = history_days
        self.session_limit = session_limit

    def name(self) -> str:
        return "openclaw"

    def collect(self) -> list[dict[str, Any]]:
        """执行一次采集。

        通过 openclaw CLI 获取会话列表，再逐会话获取消息历史和上下文。

        Returns:
            会话列表，每项包含 messages、token 统计、上下文信息等
        """
        all_sessions = self._list_sessions()
        logger.info("OpenClaw 会话总数: %d", len(all_sessions))

        results: list[dict[str, Any]] = []
        for s in all_sessions:
            try:
                conv = self._process_session(s)
                if conv:
                    results.append(conv)
            except Exception as e:
                logger.warning("处理会话异常 %s: %s", s.get("sessionId"), e)

        return results

    def _list_sessions(self) -> list[dict[str, Any]]:
        """通过 CLI 列出所有会话。"""
        try:
            result = subprocess.run(
                ["openclaw", "sessions", "--json"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                logger.error("openclaw sessions 命令失败: %s", result.stderr)
                return []

            data = json.loads(result.stdout)
            sessions = data.get("sessions", [])
            return sessions[:self.session_limit]

        except (subprocess.TimeoutExpired, json.JSONDecodeError,
                FileNotFoundError) as e:
            logger.error("获取 OpenClaw 会话列表失败: %s", e)
            return []

    def _process_session(self, s: dict[str, Any]) -> Optional[dict[str, Any]]:
        """处理单条会话，整合 token 数据和对话上下文。

        Args:
            s: openclaw sessions --json 返回的一条会话

        Returns:
            标准化的会话 dict，包含标题和上下文信息
        """
        session_id = s.get("sessionId", "")
        if not session_id:
            return None

        source_id = s.get("key", "")
        model = s.get("model", "unknown")
        input_tokens = s.get("inputTokens") or 0
        output_tokens = s.get("outputTokens") or 0
        total_tokens = s.get("totalTokens") or 0
        updated_ts = s.get("updatedAt")

        # 计算费用
        from ..config import config as cfg
        from ..tokenizer.models import get_pricing
        inp_price, out_price = get_pricing(model, cfg.model_pricing)
        cost = TokenCounter.estimate_cost(input_tokens, output_tokens,
                                          inp_price, out_price)

        # 提取对话上下文信息
        context_info = self._extract_conversation_context(session_id)

        # 生成可读标题（基于真实用户消息）
        title = self._build_title(s, session_id, input_tokens, context_info)

        # 格式化时间
        updated_at = datetime.fromtimestamp(updated_ts / 1000).isoformat() \
            if updated_ts else datetime.now().isoformat()

        # 如果有上下文的时间，使用更精确的会话时间范围
        start_time = updated_at
        end_time = updated_at
        if context_info:
            if context_info.get("time_start"):
                start_time = context_info["time_start"]
            if context_info.get("time_end"):
                end_time = context_info["time_end"]

        return {
            "id": f"openclaw_{session_id}",
            "source": "openclaw",
            "source_id": source_id,
            "title": title,
            "model": model,
            "total_input_tokens": input_tokens,
            "total_output_tokens": output_tokens,
            "message_count": context_info.get("total_messages", 0),
            "cost_estimate": round(cost, 6),
            "accuracy": "real" if s.get("totalTokensFresh") else "estimated",
            "start_time": start_time,
            "end_time": end_time,
            "context_info": json.dumps(context_info, ensure_ascii=False),
        }

    # ── Transcript 文件查找 ──────────────────────────────

    def get_transcript_path(self, session_id: str) -> Optional[str]:
        """获取会话的 transcript 文件路径。

        优先匹配当前 session_id，但不含 .reset. / .deleted. 后缀的文件。

        Args:
            session_id: 会话 ID

        Returns:
            transcript 文件路径，未找到返回 None
        """
        candidates = [
            os.path.join(SESSION_STORE_DIR, f"{session_id}.jsonl"),
        ]
        for p in candidates:
            if os.path.isfile(p):
                return p
        return None

    # ── 标题构建 ─────────────────────────────────────────

    def _build_title(self, s: dict[str, Any], session_id: str,
                     input_tokens: int,
                     context_info: dict[str, Any]) -> str:
        """构建可读标题。

        优先级：
          1. transcript 中提取到的第一条真实用户消息（清除了系统注入）
          2. 渠道名 + 类型 + 日期（含 input token 数）

        Args:
            s: 会话原始数据
            session_id: 会话 ID
            input_tokens: 输入 token 数
            context_info: 对话上下文信息

        Returns:
            可读标题（最长 120 字符）
        """
        source_id = s.get("key", "")
        kind = s.get("kind", "")
        channel = source_id.split(":")[2] if len(source_id.split(":")) >= 3 else ""
        channel_name = CHANNEL_NAMES.get(channel, channel or "其他")

        updated_ts = s.get("updatedAt")
        date_str = ""
        if updated_ts:
            date_str = datetime.fromtimestamp(updated_ts / 1000).strftime("%m-%d")

        # 优先使用 context_info 中的首条消息
        first_msg = context_info.get("first_msg", "") if context_info else ""
        if first_msg:
            # 清洗为单行文本
            title = re.sub(r'\s+', ' ', first_msg).strip()
        else:
            title_parts = [channel_name]
            if kind and kind != "direct":
                title_parts.append(kind)
            if date_str:
                title_parts.append(date_str)
            title = " · ".join(title_parts)

        # 截断到 120 字
        if len(title) > 120:
            title = title[:117] + "..."

        if input_tokens > 10000:
            title += f" (输入{TokenCounter._fmt_readable(input_tokens)})"

        return title

    # ── 对话上下文提取 ───────────────────────────────────

    def _extract_conversation_context(self, session_id: str) -> dict[str, Any]:
        """从 transcript 文件提取对话上下文信息。

        遍历 transcript JSONL，统计消息轮次、提取首条/第二条用户消息、
        计算时间跨度、总字符数。

        ---
        v1.2 增强：
        - system_messages: 系统提示词列表（含 estimated_tokens）
        - message_sizes: 每条消息的 role + estimated_tokens（前 100 条）
        - thinking_info: 推理模型的 thinking 与 output token 比例

        Args:
            session_id: 会话 ID

        Returns:
            上下文信息字典
        """
        transcript_path = self.get_transcript_path(session_id)
        if not transcript_path:
            return {}

        context: dict[str, Any] = {
            "first_msg": "",
            "second_msg": "",
            "last_msg": "",
            "user_turns": 0,
            "assistant_turns": 0,
            "total_messages": 0,
            "time_start": None,
            "time_end": None,
            "total_chars": 0,
            # v1.2 新增字段
            "system_messages": [],
            "message_sizes": [],
            "thinking_info": {},
        }

        try:
            real_user_messages: list[str] = []
            first_ts: Optional[str] = None
            last_ts: Optional[str] = None

            system_msgs: list[dict[str, Any]] = []
            msg_sizes: list[dict[str, Any]] = []
            thinking_tokens_total = 0
            output_tokens_total = 0
            has_thinking_model = False

            with open(transcript_path, encoding="utf-8") as f:
                for line in f:
                    obj = json.loads(line)
                    obj_type = obj.get("type", "")
                    ts = obj.get("timestamp", "")

                    if ts:
                        if first_ts is None:
                            first_ts = ts
                        last_ts = ts

                    if obj_type not in ("message",):
                        continue

                    msg = obj.get("message", {})
                    role = msg.get("role", "")
                    content = msg.get("content", "")

                    if not role or not content:
                        continue

                    context["total_messages"] += 1

                    if role == "system":
                        raw_text = self._extract_text(content)
                        if raw_text:
                            est_tokens = self._estimate_tokens(raw_text)
                            system_msgs.append({
                                "content": raw_text[:500],
                                "estimated_tokens": est_tokens,
                            })
                            # 也计入 message_sizes
                            msg_sizes.append({
                                "role": "system",
                                "estimated_tokens": est_tokens,
                            })

                    elif role == "user":
                        raw_text = self._extract_text(content)
                        if not raw_text:
                            continue
                        clean_text = self._strip_system_wrapper(raw_text)
                        if clean_text and not self._is_system_generated(clean_text):
                            real_user_messages.append(clean_text)
                            context["user_turns"] += 1
                            context["total_chars"] += len(clean_text)
                            est_tokens = self._estimate_tokens(clean_text)
                            msg_sizes.append({
                                "role": "user",
                                "estimated_tokens": est_tokens,
                            })

                    elif role == "assistant":
                        context["assistant_turns"] += 1
                        raw_text = self._extract_text(content)
                        if not raw_text:
                            continue
                        context["total_chars"] += len(raw_text)

                        # 分离 thinking 和 output
                        thinking_part, output_part = self._split_thinking(raw_text)
                        msg_est_tokens = self._estimate_tokens(raw_text)
                        thinking_est = self._estimate_tokens(thinking_part) if thinking_part else 0

                        if thinking_part:
                            has_thinking_model = True
                            thinking_tokens_total += thinking_est
                            output_tokens_total += msg_est_tokens - thinking_est
                        else:
                            output_tokens_total += msg_est_tokens

                        msg_sizes.append({
                            "role": "assistant",
                            "estimated_tokens": msg_est_tokens,
                            "thinking_tokens": thinking_est,
                        })

            # 限制 message_sizes 长度
            context["message_sizes"] = msg_sizes[:100]
            context["system_messages"] = system_msgs

            # Thinking 统计
            if has_thinking_model and thinking_tokens_total > 0:
                context["thinking_info"] = {
                    "has_thinking": True,
                    "thinking_tokens": thinking_tokens_total,
                    "output_tokens": max(output_tokens_total, 1),
                    "ratio": round(thinking_tokens_total / max(output_tokens_total, 1), 2),
                }

            # 取前两条和最后一条真实用户消息
            if real_user_messages:
                context["first_msg"] = real_user_messages[0]
            if len(real_user_messages) > 1:
                context["second_msg"] = real_user_messages[1]
            if real_user_messages:
                context["last_msg"] = real_user_messages[-1]

            if first_ts and last_ts:
                try:
                    t1_str = first_ts.replace("Z", "+00:00")
                    t2_str = last_ts.replace("Z", "+00:00")
                    t1 = datetime.fromisoformat(t1_str)
                    t2 = datetime.fromisoformat(t2_str)
                    context["time_start"] = first_ts
                    context["time_end"] = last_ts
                except ValueError:
                    pass

            return context

        except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
            logger.debug("提取上下文信息失败 %s: %s",
                         session_id[:8], e)
            return {}

    # ── Token 估算 ──────────────────────────────────────

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """估算文本的 token 数量（不使用 tiktoken，纯启发式）。

        适用于没有 tiktoken 或处理大量消息时的快速估算。
        中英文混合场景：中文约 1 token/1.5 字符，英文约 1 token/4 字符。

        Args:
            text: 输入文本

        Returns:
            估算的 token 数
        """
        if not text:
            return 0
        # 粗略估算：中英文混合文本平均 1 token ≈ 2.5 字符
        return max(1, len(text) // 3)

    # ── Thinking 分离 ────────────────────────────────────

    @staticmethod
    def _split_thinking(text: str) -> tuple[str, str]:
        """分离 thinking 内容和有效回答。

        推理模型（如 deepseek-r1）的输出通常包含 thinking 部分：
          思考过程...  --- 分隔符 --- <｜end▁of▁thinking｜>开始

        支持多种 thinking 格式：
        - "我是一个AI..."  (纯回答 → thinking 为空)
        - 标准 OpenAI reasoner 格式的 thinking 内容

        Args:
            text: assistant 消息的完整文本

        Returns:
            (thinking_part, output_part) 元组
        """
        if not text:
            return ("", "")

        # 尝试常见的 thinking 分隔模式
        # 模式1: 以 "思考" 开头的内容块
        # 模式2: reasoning/thinking 标签
        # 模式3: 换行后的第一个回答段落

        # 先检查是否包含分隔标记
        thinking_end_markers = [
            "---", "---", "___",
            "\n\n\n答", "\n\n回答", "\n\n回复",
        ]

        # 检查英文 thinking 标记
        thinking_start_patterns = [
            r'<thinking>.*?</thinking>',
            r'<reasoning>.*?</reasoning>',
            r'`*`*`*thinking`*`*`*',
        ]

        # 检查 XML 类型的 thinking 块
        for pattern in thinking_start_patterns:
            m = re.search(pattern, text, re.DOTALL)
            if m:
                return (m.group(0), text.replace(m.group(0), "").strip())

        # 检查是否有 thinking 分隔线
        for marker in thinking_end_markers:
            if marker in text:
                idx = text.index(marker)
                thinking = text[:idx].strip()
                output = text[idx + len(marker):].strip()
                if thinking and output:
                    return (thinking, output)

        # 没有检测到 thinking → 完整文本为 output
        return ("", text)

    # ── 系统前缀剥离 ────────────────────────────────────

    @staticmethod
    def _strip_system_wrapper(text: str) -> str:
        """剥离 OpenClaw 注入的 System 前缀，提取真实用户消息。

        OpenClaw 在 Feishu/Telegram 等渠道的消息会包装成：
          System: [timestamp] Channel[botname] ... : 真实消息

        同时移除尾部的 Conversation info、message_id 等元数据。

        Args:
            text: 原始文本

        Returns:
            剥离后的真实用户文本
        """
        if not text:
            return text

        # Step 1：剥离 System 前缀
        if text.startswith("System:") or text.startswith("system:"):
            # 模式: "System: [timestamp] Xxx[Xxx] DM from xxx: 消息内容"
            match = re.search(
                r'\] (?:DM|PM|Group|Chat)?\s*(?:from|in)?\s*\S*:\s*(.*)',
                text, re.DOTALL
            )
            if match:
                text = match.group(1).strip()
                # 递归剥离嵌套 System 前缀
                if text.startswith("System:") or text.startswith("system:"):
                    return OpenClawCollector._strip_system_wrapper(text)
            else:
                # fallback: 取第一个 ":" 之后的全部内容
                colon_idx = text.find(":")
                if colon_idx >= 0:
                    text = text[colon_idx + 1:].strip()

        # Step 2：去掉尾部的 Conversation info 元数据块
        meta_match = re.search(r'\n\nConversation info.*$', text, re.DOTALL)
        if meta_match:
            text = text[:meta_match.start()]

        # Step 3：去掉 [message_id: ...] 行
        meta_match = re.search(r'\n\[message_id:', text)
        if meta_match:
            text = text[:meta_match.start()]

        # Step 4：去掉末尾的用户 ID 重复行 (ou_ + 32位hex)
        meta_match = re.search(r'\nou_\w{32}: ', text)
        if meta_match:
            text = text[:meta_match.start()]

        return text

    # ── 文本提取工具 ─────────────────────────────────────

    @staticmethod
    def _extract_text(content: Any) -> str:
        """从 content 字段中提取纯文本（不限长度）。

        Args:
            content: 消息的 content 字段，可以是 str、list 或 None

        Returns:
            提取的纯文本，空字符串表示无内容
        """
        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    t = item.get("text", "").strip()
                    if t:
                        texts.append(t)
            text = " ".join(texts)
        else:
            return ""
        # 清理多余空白但保留原文结构
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
        return text.strip()

    @staticmethod
    def _extract_text_preview(content: Any, max_chars: int = 120) -> str:
        """从 content 字段中提取文本预览（截断版）。

        Args:
            content: 消息的 content 字段
            max_chars: 最大字符数，默认 120

        Returns:
            截断后的文本预览
        """
        text = OpenClawCollector._extract_text(content)
        if max_chars > 0 and len(text) > max_chars:
            return text[:max_chars]
        return text

    # ── 系统消息过滤 ─────────────────────────────────────

    @staticmethod
    def _is_system_generated(text: str) -> bool:
        """判断是否为系统自动生成的消息（非用户实际输入）。

        Args:
            text: 消息文本

        Returns:
            True 表示是系统生成的消息
        """
        t = text.strip()
        if not t:
            return True
        t_lower = t.lower()

        # 系统前缀
        if t.startswith("System:") or t.startswith("system:"):
            return True
        # /new 或 /reset 命令
        if t.startswith("/new") or t.startswith("/reset"):
            return True
        if "a new session was started" in t_lower:
            return True
        if "/new" in t or "/reset" in t:
            return True
        # 队列消息提示
        if t.startswith("[queued messages") or "queued messages while" in t_lower:
            return True
        # 媒体附件
        if t.startswith("[media attached") or t.startswith("media:"):
            return True
        # 系统执行结果
        if t.startswith("system: [") or t.startswith("system ["):
            return True
        if "exec completed" in t_lower or "exec failed" in t_lower:
            return True
        # 消息 ID 元数据
        if t_lower.startswith("conversation info") or t_lower.startswith("message_id"):
            return True
        # 时间戳前缀
        if re.match(r'^\[\d{4}', t):
            return True
        # 只有空白或标点
        if re.match(r'^[\s\W]+$', t):
            return True
        return False
