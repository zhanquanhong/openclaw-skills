"""Token Watcher 代理通道测试。

测试内容：
  - ChannelResolver 三通道识别
  - UsageExtractor 非流式和流式提取
  - 请求头过滤
  - URL 构建
  - _is_streaming_response 判断
  - 数据库写入
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import config
from src.database import Database
from src.proxy.server import (
    ChannelResolver,
    UsageExtractor,
    RequestForwarder,
    _filter_response_headers,
    _prepare_forward_headers,
    _is_streaming_response,
)


class TestChannelResolver(unittest.TestCase):
    """ChannelResolver 渠道识别测试。"""

    def setUp(self) -> None:
        self.mappings = {8090: "default", 8091: "openclaw", 8092: "java-app"}
        self.resolver = ChannelResolver(self.mappings)

    def _make_request(self, headers: dict | None = None,
                      port: int = 8090,
                      ua: str = "") -> MagicMock:
        """创建模拟的 aiohttp Request 对象。"""
        req = MagicMock()
        req.headers = {}
        if headers:
            req.headers.update(headers)
        if ua:
            req.headers["User-Agent"] = ua
        if "X-Channel" not in req.headers:
            req.headers.pop("X-Channel", None)

        # 模拟 transport
        transport = MagicMock()
        transport.get_extra_info.return_value = ("0.0.0.0", port)
        req.transport = transport
        return req

    def test_header_overrides_port(self) -> None:
        """X-Channel 头的优先级最高。"""
        req = self._make_request(
            headers={"X-Channel": "custom-app"},
            port=8091,
        )
        channel = self.resolver.resolve(req)
        self.assertEqual(channel, "custom-app")

    def test_port_mapping_openclaw(self) -> None:
        """8091 端口映射到 openclaw。"""
        req = self._make_request(port=8091)
        channel = self.resolver.resolve(req)
        self.assertEqual(channel, "openclaw")

    def test_port_mapping_java(self) -> None:
        """8092 端口映射到 java-app。"""
        req = self._make_request(port=8092)
        channel = self.resolver.resolve(req)
        self.assertEqual(channel, "java-app")

    def test_port_mapping_default(self) -> None:
        """8090 端口映射到 default。"""
        req = self._make_request(port=8090)
        channel = self.resolver.resolve(req)
        self.assertEqual(channel, "default")

    def test_unknown_port_falls_back_to_ua(self) -> None:
        """未映射端口 → User-Agent 匹配。"""
        req = self._make_request(port=9999, ua="curl/8.0.0")
        channel = self.resolver.resolve(req)
        self.assertEqual(channel, "curl")

    def test_ua_python_openai_sdk(self) -> None:
        """OpenAI Python SDK User-Agent。"""
        req = self._make_request(port=9999, ua="OpenAI/Python 1.30.0")
        channel = self.resolver.resolve(req)
        self.assertEqual(channel, "Python")

    def test_ua_langchain(self) -> None:
        """LangChain User-Agent。"""
        req = self._make_request(port=9999, ua="langchain-core/0.3.0")
        channel = self.resolver.resolve(req)
        self.assertEqual(channel, "LangChain")

    def test_ua_java_okhttp(self) -> None:
        """Java OkHttp User-Agent。"""
        req = self._make_request(port=9999, ua="OkHttp/4.12.0")
        channel = self.resolver.resolve(req)
        self.assertEqual(channel, "Java")

    def test_ua_litellm(self) -> None:
        """LiteLLM User-Agent。"""
        req = self._make_request(port=9999, ua="LiteLLM/1.50.0")
        channel = self.resolver.resolve(req)
        self.assertEqual(channel, "LiteLLM")

    def test_ua_openclaw(self) -> None:
        """OpenClaw User-Agent。"""
        req = self._make_request(port=9999, ua="OpenClaw/1.0")
        channel = self.resolver.resolve(req)
        self.assertEqual(channel, "OpenClaw")

    def test_no_match_returns_unknown(self) -> None:
        """无任何匹配返回 unknown。"""
        req = self._make_request(port=9999, ua="SomeRandomClient/1.0")
        channel = self.resolver.resolve(req)
        self.assertEqual(channel, "unknown")

    def test_no_transport_returns_unknown(self) -> None:
        """transport 为 None 时返回 unknown。"""
        req = MagicMock()
        req.headers = {}
        req.transport = None
        channel = self.resolver.resolve(req)
        self.assertEqual(channel, "unknown")

    def test_get_port_config_summary(self) -> None:
        """端口映射摘要应包含所有配置项。"""
        summary = self.resolver.get_port_config_summary()
        self.assertIn("8090=default", summary)
        self.assertIn("8091=openclaw", summary)
        self.assertIn("8092=java-app", summary)

    def test_empty_mappings(self) -> None:
        """空映射应正常初始化。"""
        r = ChannelResolver({})
        req = self._make_request(port=8888)
        self.assertEqual(r.resolve(req), "unknown")


class TestUsageExtractor(unittest.TestCase):
    """UsageExtractor 用量提取测试。"""

    def test_from_body_standard(self) -> None:
        """标准 OpenAI 格式的 usage 提取。"""
        body = json.dumps({
            "id": "chatcmpl-123",
            "model": "deepseek-v4-flash",
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 30,
                "total_tokens": 180,
            },
            "choices": [{"message": {"content": "Hello"}}],
        }).encode()
        usage = UsageExtractor.from_body(body)
        self.assertIsNotNone(usage)
        self.assertEqual(usage["prompt_tokens"], 150)
        self.assertEqual(usage["completion_tokens"], 30)
        self.assertEqual(usage["total_tokens"], 180)

    def test_from_body_no_usage(self) -> None:
        """无 usage 字段返回 None。"""
        body = json.dumps({"id": "123", "choices": []}).encode()
        self.assertIsNone(UsageExtractor.from_body(body))

    def test_from_body_invalid_json(self) -> None:
        """无效 JSON 返回 None。"""
        self.assertIsNone(UsageExtractor.from_body(b"not json"))

    def test_from_body_empty(self) -> None:
        """空 body 返回 None。"""
        self.assertIsNone(UsageExtractor.from_body(b""))

    def test_from_stream_standard(self) -> None:
        """标准流式响应最后一条 data 带 usage。"""
        chunk = b'data: {"choices":[{"delta":{}}],"usage":{"prompt_tokens":10,"completion_tokens":20}}\n\n'
        usage = UsageExtractor.from_stream_chunk(chunk)
        self.assertIsNotNone(usage)
        self.assertEqual(usage["prompt_tokens"], 10)
        self.assertEqual(usage["completion_tokens"], 20)

    def test_from_stream_no_usage(self) -> None:
        """流式中间块无 usage → None。"""
        chunk = b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
        self.assertIsNone(UsageExtractor.from_stream_chunk(chunk))

    def test_from_stream_done_marker(self) -> None:
        """[DONE] 标记 → None。"""
        chunk = b"data: [DONE]\n\n"
        self.assertIsNone(UsageExtractor.from_stream_chunk(chunk))

    def test_from_stream_multi_lines(self) -> None:
        """多行 SSE 中提取 usage。"""
        chunk = (
            b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
            b'data: {"choices":[{"delta":{}}],"usage":{"prompt_tokens":5,"completion_tokens":3,"total_tokens":8}}\n\n'
        )
        usage = UsageExtractor.from_stream_chunk(chunk)
        self.assertIsNotNone(usage)
        self.assertEqual(usage["total_tokens"], 8)

    def test_from_stream_non_utf8(self) -> None:
        """非 UTF-8 内容返回 None。"""
        self.assertIsNone(UsageExtractor.from_stream_chunk(b"\xff\xfe"))

    def test_alt_field_names(self) -> None:
        """部分厂商用 input_tokens / output_tokens 替代 prompt/completion。"""
        body = json.dumps({
            "usage": {
                "input_tokens": 200,
                "output_tokens": 50,
                "total_tokens": 250,
            },
        }).encode()
        usage = UsageExtractor.from_body(body)
        self.assertIsNotNone(usage)
        self.assertEqual(usage["prompt_tokens"], 200)
        self.assertEqual(usage["completion_tokens"], 50)


class TestFilterHeaders(unittest.TestCase):
    """响应头过滤测试。"""

    def test_removes_internal_headers(self) -> None:
        headers = {
            "Content-Type": "application/json",
            "Transfer-Encoding": "chunked",
            "Connection": "keep-alive",
            "X-Request-Id": "abc",
        }
        filtered = _filter_response_headers(headers)
        self.assertIn("Content-Type", filtered)
        self.assertIn("X-Request-Id", filtered)
        # Transfer-Encoding 必须保留（客户端需要解析 chunked）
        self.assertIn("Transfer-Encoding", filtered)
        self.assertNotIn("Connection", filtered)

    def test_empty_headers(self) -> None:
        self.assertEqual(_filter_response_headers({}), {})


class TestUpstreamUrl(unittest.TestCase):
    """上游 URL 构建测试。"""

    def setUp(self) -> None:
        # 保存原始配置并在测试后恢复
        self._orig_url = config.proxy_upstream_url

    def tearDown(self) -> None:
        config.proxy_upstream_url = self._orig_url

    def test_simple_path(self) -> None:
        url = RequestForwarder._build_upstream_url("/v1/chat/completions")
        self.assertEqual(url, "https://api.deepseek.com/v1/chat/completions")

    def test_with_channel_prefix(self) -> None:
        url = RequestForwarder._build_upstream_url("/openclaw/v1/chat/completions")
        # 不用自动剥离渠道前缀，用端口/Header/UA 区分渠道
        self.assertEqual(url, "https://api.deepseek.com/openclaw/v1/chat/completions")

    def test_custom_upstream(self) -> None:
        config.proxy_upstream_url = "https://custom-api.com/v1"
        url = RequestForwarder._build_upstream_url("/chat/completions")
        self.assertEqual(url, "https://custom-api.com/v1/chat/completions")
        config.proxy_upstream_url = self._orig_url

    def test_empty_path(self) -> None:
        url = RequestForwarder._build_upstream_url("")
        self.assertEqual(url, "https://api.deepseek.com/")


class TestStreamingDetection(unittest.TestCase):
    """流式响应判断测试。"""

    def test_stream_true_in_body(self) -> None:
        body = json.dumps({"model": "deepseek", "stream": True}).encode()
        resp = MagicMock()
        resp.headers = {}
        result = _is_streaming_response(body, resp)
        self.assertTrue(result)

    def test_stream_false_in_body(self) -> None:
        body = json.dumps({"model": "deepseek", "stream": False}).encode()
        resp = MagicMock()
        resp.headers = {}
        result = _is_streaming_response(body, resp)
        self.assertFalse(result)

    def test_stream_omitted_in_body(self) -> None:
        body = json.dumps({"model": "deepseek"}).encode()
        resp = MagicMock()
        resp.headers = {}
        result = _is_streaming_response(body, resp)
        self.assertFalse(result)

    def test_chunked_transfer_encoding(self) -> None:
        body = b""
        resp = MagicMock()
        resp.headers = {"Transfer-Encoding": "chunked"}
        result = _is_streaming_response(body, resp)
        self.assertTrue(result)

    def test_empty_body(self) -> None:
        resp = MagicMock()
        resp.headers = {}
        result = _is_streaming_response(b"", resp)
        self.assertFalse(result)


class TestExtractModel(unittest.TestCase):
    """模型名提取测试。"""

    def test_normal(self) -> None:
        body = json.dumps({"model": "deepseek-v4-flash"}).encode()
        self.assertEqual(RequestForwarder._extract_model(body), "deepseek-v4-flash")

    def test_no_model(self) -> None:
        body = json.dumps({}).encode()
        self.assertEqual(RequestForwarder._extract_model(body), "")

    def test_invalid_json(self) -> None:
        self.assertEqual(RequestForwarder._extract_model(b"not json"), "")


class TestPrepareHeaders(unittest.TestCase):
    """请求头过滤测试。"""

    def test_pass_through_auth(self) -> None:
        """Authorization 头应透传。"""
        req = MagicMock()
        req.headers = {
            "Authorization": "Bearer sk-test",
            "Content-Type": "application/json",
            "Host": "localhost:8090",
            "User-Agent": "curl/8.0.0",
        }
        headers = _prepare_forward_headers(req)
        self.assertEqual(headers.get("Authorization"), "Bearer sk-test")
        self.assertIn("Content-Type", headers)
        self.assertNotIn("Host", headers)

    def test_strips_x_channel(self) -> None:
        """X-Channel 头不应透传给上游。"""
        req = MagicMock()
        req.headers = {
            "Authorization": "Bearer sk-test",
            "X-Channel": "openclaw",
        }
        headers = _prepare_forward_headers(req)
        self.assertNotIn("X-Channel", headers)

    def test_custom_x_headers_passed(self) -> None:
        """自定义 X- 头透传。"""
        req = MagicMock()
        req.headers = {
            "Authorization": "Bearer sk-test",
            "X-Trace-Id": "abc-123",
        }
        headers = _prepare_forward_headers(req)
        self.assertIn("X-Trace-Id", headers)


class TestDatabaseProxyIntegration(unittest.TestCase):
    """代理数据写入数据库测试。"""

    def setUp(self) -> None:
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.db = Database(self.db_path)

    def tearDown(self) -> None:
        self.db.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_insert_proxy_log_with_channel(self) -> None:
        """插入带 channel 的代理日志。"""
        self.db.insert_proxy_log({
            "request_id": "req-001",
            "model": "deepseek-v4-flash",
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "cost": 0.0005,
            "stream": 0,
            "channel": "openclaw",
            "response_time_ms": 1200,
        })
        logs = self.db.get_proxy_logs(limit=10)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["channel"], "openclaw")
        self.assertEqual(logs[0]["input_tokens"], 100)
        self.assertEqual(logs[0]["output_tokens"], 50)

    def test_insert_proxy_log_defaults(self) -> None:
        """插入默认数据，应使用空字符串和 0。"""
        self.db.insert_proxy_log({})
        logs = self.db.get_proxy_logs(limit=10)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["channel"], "")
        self.assertEqual(logs[0]["response_time_ms"], 0)

    def test_get_proxy_channel_breakdown(self) -> None:
        """渠道用量统计。"""
        self.db.insert_proxy_log({
            "request_id": "r1", "channel": "openclaw",
            "input_tokens": 100, "output_tokens": 50,
            "total_tokens": 150, "cost": 0.001,
        })
        self.db.insert_proxy_log({
            "request_id": "r2", "channel": "java-app",
            "input_tokens": 200, "output_tokens": 100,
            "total_tokens": 300, "cost": 0.002,
        })
        self.db.insert_proxy_log({
            "request_id": "r3", "channel": "openclaw",
            "input_tokens": 50, "output_tokens": 25,
            "total_tokens": 75, "cost": 0.0005,
        })
        breakdown = self.db.get_proxy_channel_breakdown()
        # 按 total_tokens 降序
        self.assertEqual(len(breakdown), 2)
        # openclaw: total = 225, java-app: total = 300
        # 所以 java-app 应排第一
        self.assertEqual(breakdown[0]["channel"], "java-app")
        self.assertEqual(breakdown[0]["count"], 1)
        self.assertEqual(breakdown[1]["channel"], "openclaw")
        self.assertEqual(breakdown[1]["count"], 2)

    def test_get_proxy_logs_filter_channel(self) -> None:
        """按渠道过滤查询。"""
        self.db.insert_proxy_log({
            "request_id": "r1", "channel": "openclaw",
            "input_tokens": 100, "output_tokens": 50,
        })
        self.db.insert_proxy_log({
            "request_id": "r2", "channel": "java-app",
            "input_tokens": 200, "output_tokens": 100,
        })
        filtered = self.db.get_proxy_logs(channel="openclaw")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["channel"], "openclaw")

    def test_upsert_conversation_with_proxy_source(self) -> None:
        """代理来源的会话写入 conversations 表。"""
        context_info = json.dumps({"channel": "openclaw"}, ensure_ascii=False)
        self.db.upsert_conversation({
            "id": "proxy_req-001",
            "source": "proxy",
            "source_id": "req-001",
            "title": "代理请求 (openclaw)",
            "model": "deepseek-v4-flash",
            "total_input_tokens": 100,
            "total_output_tokens": 50,
            "cost_estimate": 0.0005,
            "accuracy": "real",
            "start_time": "2026-05-29T12:00:00",
            "end_time": "2026-05-29T12:00:02",
            "message_count": 1,
            "context_info": context_info,
        })
        conv = self.db.get_conversation("proxy_req-001")
        self.assertIsNotNone(conv)
        self.assertEqual(conv["source"], "proxy")
        self.assertEqual(conv["total_input_tokens"], 100)


if __name__ == "__main__":
    unittest.main()
