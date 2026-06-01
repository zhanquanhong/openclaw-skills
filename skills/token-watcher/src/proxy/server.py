"""OpenAI 兼容 API 代理服务器。

实现反向代理 + token 用量采集，支持：
- 流式（SSE）和非流式 API 调用
- 三通道渠道识别（Header / 端口 / User-Agent）
- 多端口监听（一个端口一个渠道）
- 实时响应转发（不阻塞客户端）
"""

import asyncio
import json
import logging
import os
import re
import ssl
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Any
from urllib.parse import urlparse

import aiohttp
from aiohttp import web

from ..config import config as app_config
from ..database import Database
from ..tokenizer.models import get_pricing
from ..tokenizer.engine import TokenCounter

logger = logging.getLogger(__name__)

# ── User-Agent → 渠道映射规则 ──────────────────────────

UA_CHANNEL_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"OpenClaw", re.I), "OpenClaw"),
    (re.compile(r"openai[-/]python", re.I), "Python"),
    (re.compile(r"python-requests|python-urllib", re.I), "Python"),
    (re.compile(r"curl[/\s]", re.I), "curl"),
    (re.compile(r"langchain", re.I), "LangChain"),
    (re.compile(r"litellm", re.I), "LiteLLM"),
    (re.compile(r"Apache-HttpClient|OkHttp|Java", re.I), "Java"),
    (re.compile(r"Go-http-client", re.I), "Go"),
    (re.compile(r"node-fetch|axios|undici", re.I), "Node.js"),
    (re.compile(r"Continue", re.I), "Continue"),
    (re.compile(r"LobeChat|ChatGPT-Next-Web", re.I), "ChatUI"),
    (re.compile(r"Cursor|Windsurf", re.I), "IDE"),
    (re.compile(r"vscode", re.I), "VSCode"),
]

# ── 请求头过滤 ─────────────────────────────────────────

# 不需要透传给上游的响应头（注意：Transfer-Encoding 需要保留给客户端解析流式）
_REMOVE_RESPONSE_HEADERS = {
    "content-encoding", "content-length",
    "connection", "keep-alive", "proxy-authenticate",
    "proxy-authorization", "trailer",
}


def _filter_response_headers(headers: dict[str, str]) -> dict[str, str]:
    """过滤响应头，移除不允许转发给客户端的字段。"""
    return {
        k: v for k, v in headers.items()
        if k.lower() not in _REMOVE_RESPONSE_HEADERS
    }


def _prepare_forward_headers(request: web.Request) -> dict[str, str]:
    """准备转发请求头。

    只透传白名单内和自定义的请求头，去除 Host/Connection/X-Channel 等内部头。

    Args:
        request: 原始请求

    Returns:
        转发用的请求头字典
    """
    headers: dict[str, str] = {}
    # 白名单（小写）
    pass_through_lower = {h.lower() for h in app_config.proxy_pass_through_headers}

    for key, value in request.headers.items():
        key_lower = key.lower()
        if key_lower in ("host", "connection", "content-length",
                         "transfer-encoding", "x-channel"):
            continue
        if key_lower in pass_through_lower:
            headers[key] = value
        elif key.startswith("X-") or key.startswith("x-"):
            headers[key] = value
    return headers


# ── 渠道解析器 ─────────────────────────────────────────

class ChannelResolver:
    """从请求中识别渠道来源。"""

    def __init__(self, port_mappings: dict[int, str]) -> None:
        self.port_mappings = dict(port_mappings)

    def resolve(self, request: web.Request) -> str:
        """从请求中解析渠道名。

        优先级：
          1. X-Channel 请求头
          2. 监听端口映射
          3. User-Agent 自动匹配
          4. "unknown"

        Args:
            request: aiohttp 请求对象

        Returns:
            渠道名称
        """
        # 1. 请求头显式指定
        channel = request.headers.get("X-Channel", "").strip()
        if channel:
            return channel

        # 2. 端口映射
        port = self._get_local_port(request)
        if port is not None and port in self.port_mappings:
            return self.port_mappings[port]

        # 3. User-Agent
        ua = request.headers.get("User-Agent", "")
        for pattern, name in UA_CHANNEL_RULES:
            if pattern.search(ua):
                return name

        return "unknown"

    @staticmethod
    def _get_local_port(request: web.Request) -> Optional[int]:
        """获取请求来源的本地端口。"""
        try:
            transport = request.transport
            if transport is None:
                return None
            sockname = transport.get_extra_info("sockname")
            if sockname and len(sockname) >= 2:
                return int(sockname[1])
        except (TypeError, ValueError, AttributeError):
            pass
        return None

    def get_port_config_summary(self) -> str:
        """返回端口映射的可读摘要。"""
        if not self.port_mappings:
            return "未配置端口映射"
        parts = [f"{p}={ch}" for p, ch in sorted(self.port_mappings.items())]
        return ", ".join(parts)


# ── Token 用量提取器 ──────────────────────────────────

class UsageExtractor:
    """从 AI API 响应中提取 token 用量。"""

    @staticmethod
    def from_body(body: bytes) -> Optional[dict[str, int]]:
        """从非流式响应 JSON 体中提取 usage。

        Args:
            body: 完整的响应体

        Returns:
            {"prompt_tokens": N, "completion_tokens": N, "total_tokens": N}
            或 None（未找到 usage 字段）
        """
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

        usage = data.get("usage")
        if isinstance(usage, dict):
            return {
                "prompt_tokens": usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0) or usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }
        return None

    @staticmethod
    def from_stream_chunk(chunk: bytes) -> Optional[dict[str, int]]:
        """从流式 SSE 数据块中提取 usage。

        标准 OpenAI 兼容格式的流式响应会在最后一条 data 中包含 usage：
          data: {"choices":[{"delta":{}}],"usage":{"prompt_tokens":10,"completion_tokens":20}}

        提取时寻找包含 "usage" 的 SSE 行。

        Args:
            chunk: 流式数据块（原始字节）

        Returns:
            usage 字典，或 None
        """
        if b'"usage"' not in chunk:
            return None

        try:
            text = chunk.decode("utf-8")
        except UnicodeDecodeError:
            return None

        for line in text.split("\n"):
            line = line.strip()
            if not line.startswith("data: "):
                continue
            payload = line[6:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                continue
            usage = data.get("usage")
            if isinstance(usage, dict):
                return {
                    "prompt_tokens": usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0) or usage.get("output_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                }

        return None


# ── 请求转发器 ─────────────────────────────────────────

class RequestForwarder:
    """转发请求到上游 AI API，并提取 token 用量。"""

    def __init__(self, db: Database, resolver: ChannelResolver) -> None:
        self.db = db
        self.resolver = resolver
        self._session: Optional[aiohttp.ClientSession] = None
        # 流式响应的用量（由 _forward_stream 写入，handle 读取）
        self._stream_usage: Optional[dict[str, int]] = None

    async def get_session(self) -> aiohttp.ClientSession:
        """获取或创建 aiohttp 会话。"""
        if self._session is None or self._session.closed:
            # 构建 SSL context（内网自签名证书兼容）
            ssl_context = _build_ssl_context()
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=app_config.proxy_request_timeout),
            )
        return self._session

    async def close(self) -> None:
        """关闭 aiohttp 会话。"""
        if self._session and not self._session.closed:
            await self._session.close()

    # ── 主处理入口 ──────────────────────────────────────

    async def handle(self, request: web.Request) -> web.StreamResponse:  # noqa: C901
        """处理一个代理请求。

        Args:
            request: 原始客户端请求

        Returns:
            转发后的响应（流式或非流式）
        """
        start_time = time.monotonic()
        request_id = str(uuid.uuid4())[:8]
        body = await request.read()
        model = self._extract_model(body)
        channel = self.resolver.resolve(request)

        upstream_url = self._build_upstream_url(request.path)
        headers = _prepare_forward_headers(request)

        logger.debug("[%s] %s %s -> %s (channel=%s, model=%s)",
                     request_id, request.method, request.path,
                     upstream_url, channel, model or "unknown")

        session = await self.get_session()
        usage_info: Optional[dict[str, int]] = None

        try:
            async with session.request(
                method=request.method,
                url=upstream_url,
                headers=headers,
                data=body,
            ) as upstream_resp:
                is_stream = _is_streaming_response(body, upstream_resp)

                if is_stream:
                    self._stream_usage = None
                    resp = await self._forward_stream(request, upstream_resp)
                    usage_info = self._stream_usage
                else:
                    resp_data = await upstream_resp.read()
                    resp = web.Response(
                        body=resp_data,
                        status=upstream_resp.status,
                        headers=_filter_response_headers(dict(upstream_resp.headers)),
                    )
                    usage_info = UsageExtractor.from_body(resp_data)

        except (aiohttp.ClientError, asyncio.TimeoutError,
                ConnectionError) as e:
            logger.error("[%s] 上游请求失败: %s", request_id, e)
            raise web.HTTPBadGateway(text=json.dumps({
                "error": {"message": f"Proxy error: {e}", "type": "proxy_error"},
            }), content_type="application/json")

        if usage_info:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            self._save_usage(
                model=model,
                channel=channel,
                request_id=request_id,
                input_tokens=usage_info.get("prompt_tokens", 0),
                output_tokens=usage_info.get("completion_tokens", 0),
                total_tokens=usage_info.get("total_tokens", 0),
                response_time_ms=elapsed_ms,
                is_stream=is_stream,
            )

        return resp

    # ── 上游 URL 构建 ───────────────────────────────────

    @staticmethod
    def _build_upstream_url(path: str) -> str:
        """将请求路径拼接到上游 API URL。

        Args:
            path: 请求路径，如 "/v1/chat/completions"

        Returns:
            完整上游 URL: upstream_base + path
        """
        upstream = app_config.proxy_upstream_url.rstrip("/")
        if not path.startswith("/"):
            path = "/" + path
        return upstream + path

    # ── 流式转发 ────────────────────────────────────────

    async def _forward_stream(
        self,
        request: web.Request,
        upstream_resp: aiohttp.ClientResponse,
    ) -> web.StreamResponse:
        """流式响应：逐 chunk 转发，并从数据中提取 usage。

        SSE 格式：
          data: {"choices":[{"delta":{"content":"..."}}]}
          ...
          data: {"choices":[{"delta":{}}],"usage":{...}}
          data: [DONE]

        Args:
            request: 原始请求
            upstream_resp: 上游响应

        Returns:
            StreamResponse
        """
        resp_headers = _filter_response_headers(dict(upstream_resp.headers))
        response = web.StreamResponse(
            status=upstream_resp.status,
            headers=resp_headers,
        )
        await response.prepare(request)

        last_usage_chunk: Optional[bytes] = None

        try:
            async for chunk in upstream_resp.content.iter_chunked(65536):
                if chunk:
                    await response.write(chunk)
                    if b'"usage"' in chunk:
                        last_usage_chunk = chunk
                        usage = UsageExtractor.from_stream_chunk(chunk)
                        if usage:
                            self._stream_usage = usage

        except (asyncio.TimeoutError, ConnectionResetError,
                ConnectionAbortedError):
            logger.warning("流式响应中断")

        # 兜底：流结束时没找到 usage，从最后一 data 块尝试
        if self._stream_usage is None and last_usage_chunk:
            usage = UsageExtractor.from_stream_chunk(last_usage_chunk)
            if usage:
                self._stream_usage = usage

        return response

    # ── 工具方法 ────────────────────────────────────────

    @staticmethod
    def _extract_model(body: bytes) -> str:
        """从请求体中提取模型名。"""
        if not body:
            return ""
        try:
            data = json.loads(body)
            return str(data.get("model", ""))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return ""

    def _save_usage(self, model: Optional[str], channel: str,
                    request_id: str, input_tokens: int,
                    output_tokens: int, total_tokens: int,
                    response_time_ms: int,
                    is_stream: bool = False) -> None:
        """将 token 用量写入数据库。

        同时写入 proxy_logs 表（详细记录）和 conversations 表（聚合统计）。
        """
        inp_price, out_price = get_pricing(model or "", app_config.model_pricing)
        cost = TokenCounter.estimate_cost(input_tokens, output_tokens,
                                          inp_price, out_price)

        # 写入 proxy_logs 明细
        self.db.insert_proxy_log({
            "request_id": request_id,
            "model": model or "",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost": round(cost, 8),
            "stream": 1 if is_stream else 0,
            "channel": channel,
            "response_time_ms": response_time_ms,
        })

        # 写入 conversations 表（便于 Dashboard 统览）
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        conv_id = f"proxy_{request_id}"
        context_info = json.dumps({
            "channel": channel,
            "response_time_ms": response_time_ms,
            "request_id": request_id,
        }, ensure_ascii=False)

        self.db.upsert_conversation({
            "id": conv_id,
            "source": "proxy",
            "source_id": request_id,
            "title": f"代理请求 ({channel})",
            "model": model or "",
            "total_input_tokens": input_tokens,
            "total_output_tokens": output_tokens,
            "cost_estimate": round(cost, 6),
            "accuracy": "real",
            "start_time": ts,
            "end_time": ts,
            "message_count": 1,
            "context_info": context_info,
        })

        if input_tokens > 0 or output_tokens > 0:
            logger.info("代理用量: %s | model=%s | input=%d | output=%d | "
                        "cost=%.6f | channel=%s | %dms",
                        request_id, model or "-", input_tokens, output_tokens,
                        cost, channel, response_time_ms)


# ── 全局函数（供外部调用） ────────────────────────────

def _is_streaming_response(body: bytes,
                           upstream_resp: aiohttp.ClientResponse) -> bool:
    """判断本次响应是否为流式。

    两个判断依据：
      1. 请求 body 中 stream=true
      2. 响应头 Transfer-Encoding: chunked

    Args:
        body: 请求体字节
        upstream_resp: 上游响应

    Returns:
        True 表示流式响应
    """
    te = upstream_resp.headers.get("Transfer-Encoding", "")
    if "chunked" in te.lower():
        return True

    if body:
        try:
            req_data = json.loads(body)
            if req_data.get("stream", False):
                return True
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    return False


# ── 多端口服务器 ───────────────────────────────────────

class MultiPortProxyServer:
    """支持多端口监听的 API 代理服务器。

    每个端口可映射到不同渠道，方便区分客户端来源。
    """

    def __init__(self, db: Database) -> None:
        self.db = db
        self.resolver = ChannelResolver(app_config.proxy_port_mappings)
        self.forwarder = RequestForwarder(db, self.resolver)
        self._runners: list[web.AppRunner] = []

    async def _create_app(self) -> web.Application:
        """创建 aiohttp 应用。"""
        app = web.Application()

        # 健康检查
        app.router.add_get("/health", self._handle_health)

        # 所有 HTTP 方法 → 代理转发
        for method in ("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"):
            app.router.add_route(method, "/{tail:.*}", self._handle_proxy)

        app.on_shutdown.append(self._on_shutdown)

        return app

    async def _handle_health(self, request: web.Request) -> web.Response:  # noqa: ARG002
        """健康检查端点。"""
        return web.json_response({
            "status": "ok",
            "version": "token-watcher-proxy/1.0",
            "channel_mappings": self.resolver.get_port_config_summary(),
        })

    async def _handle_proxy(self, request: web.Request) -> web.StreamResponse:
        """处理所有代理请求。"""
        return await self.forwarder.handle(request)

    async def _on_shutdown(self, app: web.Application) -> None:  # noqa: ARG002
        """应用关闭时清理。"""
        await self.forwarder.close()

    async def start(self) -> list[int]:
        """启动所有端口的监听服务。

        Returns:
            实际监听的端口列表
        """
        app = await self._create_app()

        ports = list(app_config.proxy_port_mappings.keys())
        if not ports:
            ports = [app_config.proxy_port]

        self._runners.clear()
        for port in ports:
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, app_config.proxy_host, port)
            await site.start()
            self._runners.append(runner)
            channel_name = app_config.proxy_port_mappings.get(port, "default")
            logger.info("代理端口 %d = %s", port, channel_name)

        return ports

    async def stop(self) -> None:
        """停止所有端口。"""
        for runner in self._runners:
            try:
                await runner.cleanup()
            except Exception as e:
                logger.warning("关闭代理端口失败: %s", e)
        self._runners.clear()
        await self.forwarder.close()


def _build_ssl_context() -> Optional[ssl.SSLContext]:
    """构建 SSL 上下文。

    内部网络如果使用自签名证书，可通过环境变量跳过验证：
      PROXY_SSL_VERIFY_NONE=1

    Returns:
        SSLContext（不验证时）或 None（默认验证）
    """
    if os.environ.get("PROXY_SSL_VERIFY_NONE") == "1":
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return None  # 默认使用标准 SSL 验证
