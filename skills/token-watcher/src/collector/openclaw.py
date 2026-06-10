"""OpenClaw 会话采集器。

直接扫描 session store 目录下所有 .jsonl 会话文件，解析 transcript
中的 usage 字段，用 DeepSeek 公式（input + cacheRead + output）统计
每笔 API 调用的 token 消耗。不再依赖 `openclaw sessions --json` CLI。
"""

import json
import logging
import os
import re
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

    # ── 主采集入口 ─────────────────────────────────────────

    def collect(self) -> list[dict[str, Any]]:
        """执行一次采集。

        扫描 session store 下所有 .jsonl 文件，解析 transcript，
        提取 token 使用数据和对话上下文。

        Returns:
            会话列表
        """
        session_files = self._find_session_files()
        logger.info("找到 %d 个会话文件", len(session_files))

        results: list[dict[str, Any]] = []
        for fpath in session_files:
            try:
                conv = self._process_file(fpath)
                if conv:
                    results.append(conv)
            except Exception as e:
                logger.warning("处理文件 %s 异常: %s",
                               os.path.basename(fpath), e)

        return results

    # ── 文件发现 ──────────────────────────────────────────

    def _find_session_files(self) -> list[str]:
        """扫描 SESSION_STORE_DIR 下所有 .jsonl 文件。

        Returns:
            按文件名排序的完整路径列表
        """
        if not os.path.isdir(SESSION_STORE_DIR):
            logger.warning("会话目录不存在: %s", SESSION_STORE_DIR)
            return []

        files: list[str] = []
        for fname in sorted(os.listdir(SESSION_STORE_DIR)):
            if not fname.endswith(".jsonl"):
                continue
            # 跳过 .reset. / .deleted. 后缀的清理文件
            if ".reset." in fname or ".deleted." in fname:
                continue
            fpath = os.path.join(SESSION_STORE_DIR, fname)
            # 跳过空文件
            if os.path.getsize(fpath) == 0:
                continue
            files.append(fpath)

        return files

    # ── 单文件处理 ─────────────────────────────────────────

    def _process_file(self, fpath: str) -> Optional[dict[str, Any]]:
        """处理单个 session file，提取 token 汇总和上下文。

        Args:
            fpath: .jsonl 文件完整路径

        Returns:
            标准化的会话 dict，无 token 数据的返回 None
        """
        fname = os.path.basename(fpath)
        session_id = fname.replace(".jsonl", "")

        # 计算最小时间戳（多少天内的 API 调用才计入）
        min_ts = None
        if self.history_days > 0:
            from datetime import datetime, timedelta, timezone
            min_dt = datetime.now(timezone.utc) - timedelta(days=self.history_days)
            min_ts = min_dt.isoformat()

        # 解析整个 transcript
        parsed = self._parse_transcript(fpath, min_timestamp=min_ts)
        if not parsed or not parsed["api_calls"]:
            return None

        api_calls = parsed["api_calls"]
        context_info = parsed["context"]

        # 累加 DeepSeek 公式的 token
        total_input_uncached = 0   # usage.input
        total_cache_read = 0       # usage.cacheRead
        total_output = 0           # usage.output
        total_deepseek = 0         # input + cacheRead + output
        first_ts: Optional[str] = None
        last_ts: Optional[str] = None
        session_model = "unknown"
        source_id = ""
        kind = ""

        for call in api_calls:
            total_input_uncached += call["input"]
            total_cache_read += call["cacheRead"]
            total_output += call["output"]
            total_deepseek += call["input"] + call["cacheRead"] + call["output"]
            if call["timestamp"]:
                if first_ts is None:
                    first_ts = call["timestamp"]
                last_ts = call["timestamp"]

        # 从 context 中获取模型/来源信息
        session_model = parsed.get("model", "unknown") or "unknown"
        source_id = parsed.get("source_id", "")
        kind = parsed.get("kind", "direct")
        channel_name = self._detect_channel(source_id)

        # 构建可读标题
        title = self._build_title_from_context(
            channel_name, kind,
            context_info.get("first_msg", ""),
            total_deepseek,
            first_ts,
        )

        # 计算费用（使用 total_deepseek 按 input/output 估算）
        from ..config import config as cfg
        from ..tokenizer.models import get_pricing
        inp_price, out_price = get_pricing(session_model, cfg.model_pricing)
        # 将 cacheRead 按输入价格估算（DeepSeek 缓存输入有折扣）
        cost_input = total_input_uncached * inp_price / 1_000_000
        cost_cache = total_cache_read * inp_price * 0.5 / 1_000_000  # cache 约半价
        cost_output = total_output * out_price / 1_000_000
        total_cost = cost_input + cost_cache + cost_output

        # 构建返回数据
        start_time = first_ts or datetime.now().isoformat()
        end_time = last_ts or start_time

        return {
            "id": f"openclaw_{session_id}",
            "source": "openclaw",
            "source_id": source_id,
            "title": title,
            "model": session_model,
            "total_input_tokens": total_input_uncached + total_cache_read,
            "total_output_tokens": total_output,
            "total_cache_read_tokens": total_cache_read,
            "total_deepseek_tokens": total_deepseek,
            "message_count": context_info.get("total_messages", 0),
            "api_call_count": len(api_calls),
            "cost_estimate": round(total_cost, 6),
            "accuracy": "real",
            "start_time": start_time,
            "end_time": end_time,
            "context_info": json.dumps(context_info, ensure_ascii=False),
        }

    # ── Transcript 解析 ──────────────────────────────────

    def _parse_transcript(self, fpath: str,
                          min_timestamp: Optional[str] = None) -> Optional[dict[str, Any]]:
        """解析 .jsonl 文件，提取所有 API 调用 usage 和上下文。

        Args:
            fpath: .jsonl 文件路径
            min_timestamp: ISO 格式，只统计该时间戳之后的 API 调用

        Returns:
            dict 包含 api_calls 列表和 context/source 元信息
        """
        fname = os.path.basename(fpath)
        try:
            api_calls: list[dict[str, Any]] = []
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
                "system_messages": [],
                "message_sizes": [],
                "thinking_info": {},
            }

            current_model = ""
            current_provider = ""
            source_id = ""
            kind = "direct"
            real_user_messages: list[str] = []
            first_ts: Optional[str] = None
            last_ts: Optional[str] = None

            with open(fpath, encoding="utf-8") as f:
                for line in f:
                    obj = json.loads(line)
                    obj_type = obj.get("type", "")
                    ts = obj.get("timestamp", "")

                    if ts:
                        if first_ts is None:
                            first_ts = ts
                        last_ts = ts

                    # 记录会话级元数据
                    if obj_type == "session":
                        source_id = obj.get("key", "") or source_id
                        kind = obj.get("kind", "direct") or "direct"
                        if not source_id:
                            source_id = obj.get("channel", "")

                    elif obj_type == "model_change":
                        current_model = obj.get("modelId", "") or ""
                        current_provider = obj.get("provider", "") or ""

                    elif obj_type == "custom" and obj.get("customType") == "model-snapshot":
                        snap_model = obj.get("data", {}).get("modelId", "") or ""
                        if snap_model and not current_model:
                            current_model = snap_model

                    elif obj_type == "message":
                        msg = obj.get("message", {})
                        if not isinstance(msg, dict):
                            continue
                        role = msg.get("role", "")
                        content = msg.get("content", "")
                        if not role:
                            continue

                        context["total_messages"] += 1

                        # --- usage → API call 记录 ---
                        usage = msg.get("usage")
                        if usage and isinstance(usage, dict):
                            inp = usage.get("input", 0) or 0
                            out = usage.get("output", 0) or 0
                            cr = usage.get("cacheRead", 0) or 0
                            cw = usage.get("cacheWrite", 0) or 0
                            tt = usage.get("totalTokens", 0) or 0

                            # 只有非零 totalTokens 才视为有效 API 调用
                            if tt > 0:
                                # 时间戳过滤：跳过早于 min_timestamp 的调用
                                if min_timestamp and ts and ts < min_timestamp:
                                    continue
                                # 兜底取 model：message 自带 model 字段优先
                                msg_model = msg.get("model", "") or ""
                                call_model = current_model or msg_model
                                if msg_model and not current_model:
                                    current_model = msg_model
                                api_calls.append({
                                    "input": inp,
                                    "cacheRead": cr,
                                    "cacheWrite": cw,
                                    "output": out,
                                    "totalTokens": tt,
                                    "model": call_model,
                                    "provider": current_provider,
                                    "role": role,
                                    "timestamp": ts,
                                })

                        # --- 上下文提取（原有逻辑） ---
                        if role == "system":
                            raw_text = self._extract_text(content)
                            if raw_text:
                                context["system_messages"].append({
                                    "content": raw_text[:500],
                                    "estimated_tokens": len(raw_text) // 3,
                                })
                                context["message_sizes"].append({
                                    "role": "system",
                                    "estimated_tokens": len(raw_text) // 3,
                                })

                        elif role == "user":
                            raw_text = self._extract_text(content)
                            if raw_text:
                                clean_text = self._strip_system_wrapper(raw_text)
                                if clean_text and not self._is_system_generated(clean_text):
                                    real_user_messages.append(clean_text)
                                    context["user_turns"] += 1
                                    context["total_chars"] += len(clean_text)
                                    context["message_sizes"].append({
                                        "role": "user",
                                        "estimated_tokens": len(clean_text) // 3,
                                    })

                        elif role == "assistant":
                            context["assistant_turns"] += 1
                            raw_text = self._extract_text(content)
                            if raw_text:
                                context["total_chars"] += len(raw_text)
                                thinking_part, output_part = self._split_thinking(raw_text)
                                msg_est = len(raw_text) // 3
                                thinking_est = len(thinking_part) // 3 if thinking_part else 0
                                context["message_sizes"].append({
                                    "role": "assistant",
                                    "estimated_tokens": msg_est,
                                    "thinking_tokens": thinking_est,
                                })

            # 填充上下文
            if real_user_messages:
                context["first_msg"] = real_user_messages[0]
                if len(real_user_messages) > 1:
                    context["second_msg"] = real_user_messages[1]
                context["last_msg"] = real_user_messages[-1]
            if first_ts:
                context["time_start"] = first_ts
            if last_ts:
                context["time_end"] = last_ts
            if len(context["message_sizes"]) > 100:
                context["message_sizes"] = context["message_sizes"][:100]

            # 如果完全没有 API 调用，返回 None
            if not api_calls:
                return None

            return {
                "api_calls": api_calls,
                "context": context,
                "model": current_model or "unknown",
                "source_id": source_id or fname.replace(".jsonl", ""),
                "kind": kind,
            }

        except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
            logger.debug("解析 %s 失败: %s", os.path.basename(fpath), e)
            return None

    # ── 辅助方法 ─────────────────────────────────────────

    def _detect_channel(self, source_id: str) -> str:
        """从 source_id 推断渠道名。"""
        parts = source_id.split(":") if source_id else []
        channel_key = parts[2] if len(parts) >= 3 else ""
        return CHANNEL_NAMES.get(channel_key, channel_key or "其他")

    def _build_title_from_context(
        self,
        channel_name: str,
        kind: str,
        first_msg: str,
        total_tokens: int,
        timestamp: Optional[str] = None,
    ) -> str:
        """构建可读标题。"""
        if first_msg:
            title = re.sub(r"\s+", " ", first_msg).strip()
        else:
            parts = [channel_name]
            if kind and kind != "direct":
                parts.append(kind)
            title = " · ".join(parts)

        if len(title) > 120:
            title = title[:117] + "..."

        if total_tokens > 10000:
            title += f" (输入{TokenCounter._fmt_readable(total_tokens)})"

        return title

    # ── Transcript 文件查找（保留兼容） ──────────────────

    def get_transcript_path(self, session_id: str) -> Optional[str]:
        """获取会话的 transcript 文件路径。

        优先匹配当前 session_id。

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

    # ── 以下为保留的静态工具方法 ─────────────────────────

    @staticmethod
    def _extract_text(content: Any) -> str:
        """从 content 字段中提取纯文本。"""
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
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        return text.strip()

    @staticmethod
    def _strip_system_wrapper(text: str) -> str:
        """剥离 OpenClaw 注入的 System 前缀，提取真实用户消息。"""
        if not text:
            return text

        if text.startswith("System:") or text.startswith("system:"):
            match = re.search(
                r"\] (?:DM|PM|Group|Chat)?\s*(?:from|in)?\s*\S*:\s*(.*)",
                text, re.DOTALL,
            )
            if match:
                text = match.group(1).strip()
                if text.startswith("System:") or text.startswith("system:"):
                    return OpenClawCollector._strip_system_wrapper(text)
            else:
                colon_idx = text.find(":")
                if colon_idx >= 0:
                    text = text[colon_idx + 1:].strip()

        meta_match = re.search(r"\n\nConversation info.*$", text, re.DOTALL)
        if meta_match:
            text = text[: meta_match.start()]

        meta_match = re.search(r"\n\[message_id:", text)
        if meta_match:
            text = text[: meta_match.start()]

        meta_match = re.search(r"\nou_\w{32}: ", text)
        if meta_match:
            text = text[: meta_match.start()]

        return text

    @staticmethod
    def _is_system_generated(text: str) -> bool:
        """判断是否为系统自动生成的消息。"""
        t = text.strip()
        if not t:
            return True
        t_lower = t.lower()

        if t.startswith("System:") or t.startswith("system:"):
            return True
        if t.startswith("/new") or t.startswith("/reset"):
            return True
        if "a new session was started" in t_lower:
            return True
        if t.startswith("[queued messages") or "queued messages while" in t_lower:
            return True
        if t.startswith("[media attached") or t.startswith("media:"):
            return True
        if t.startswith("system: [") or t.startswith("system ["):
            return True
        if "exec completed" in t_lower or "exec failed" in t_lower:
            return True
        if t_lower.startswith("conversation info") or t_lower.startswith("message_id"):
            return True
        if re.match(r"^\[\d{4}", t):
            return True
        if re.match(r"^[\s\W]+$", t):
            return True
        return False

    @staticmethod
    def _split_thinking(text: str) -> tuple[str, str]:
        """分离 thinking 内容和有效回答。"""
        if not text:
            return ("", "")

        thinking_end_markers = [
            "---", "---", "___",
            "\n\n\n答", "\n\n回答", "\n\n回复",
        ]

        thinking_start_patterns = [
            r"<thinking>.*?</thinking>",
            r"<reasoning>.*?</reasoning>",
            r"`*`*`*thinking`*`*`*",
        ]

        for pattern in thinking_start_patterns:
            m = re.search(pattern, text, re.DOTALL)
            if m:
                return (m.group(0), text.replace(m.group(0), "").strip())

        for marker in thinking_end_markers:
            if marker in text:
                idx = text.index(marker)
                thinking = text[:idx].strip()
                output = text[idx + len(marker):].strip()
                if thinking and output:
                    return (thinking, output)

        return ("", text)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """估算文本的 token 数量。"""
        if not text:
            return 0
        return max(1, len(text) // 3)

    @staticmethod
    def _extract_text_preview(content: Any, max_chars: int = 120) -> str:
        """提取文本预览（截断版）。"""
        text = OpenClawCollector._extract_text(content)
        if max_chars > 0 and len(text) > max_chars:
            return text[:max_chars]
        return text
