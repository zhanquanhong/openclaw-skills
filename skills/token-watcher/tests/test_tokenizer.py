"""Token Watcher 测试 - Token 计数引擎"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.tokenizer.engine import TokenCounter
from src.tokenizer.models import resolve_encoding, get_pricing


class TestTokenizerModels(unittest.TestCase):
    def test_resolve_encoding_exact_match(self) -> None:
        self.assertEqual(resolve_encoding("deepseek-v4-flash"), "cl100k_base")
        self.assertEqual(resolve_encoding("gpt-4o"), "o200k_base")
        self.assertEqual(resolve_encoding("glm-4"), "o200k_base")

    def test_resolve_encoding_keyword_match(self) -> None:
        self.assertEqual(resolve_encoding("deepseek-new-model"), "cl100k_base")
        self.assertEqual(resolve_encoding("gpt-4-turbo"), "cl100k_base")
        self.assertEqual(resolve_encoding("claude-3.5-sonnet"), "cl100k_base")

    def test_resolve_encoding_fallback(self) -> None:
        self.assertEqual(resolve_encoding("unknown-model-xyz"), "cl100k_base")
        self.assertEqual(resolve_encoding(""), "cl100k_base")
        self.assertEqual(resolve_encoding(None), "cl100k_base")

    def test_get_pricing(self) -> None:
        pricing = {
            "deepseek-v4-flash": {"input": 0.15, "output": 0.60},
        }
        inp, out = get_pricing("deepseek-v4-flash", pricing)
        self.assertEqual(inp, 0.15)
        self.assertEqual(out, 0.60)

        # 未找到
        inp, out = get_pricing("unknown", pricing)
        self.assertEqual(inp, 0.0)
        self.assertEqual(out, 0.0)


class TestTokenCounter(unittest.TestCase):
    def test_count_empty(self) -> None:
        self.assertEqual(TokenCounter.count(""), 0)
        self.assertEqual(TokenCounter.count(None), 0)  # type: ignore[arg-type]

    def test_count_simple(self) -> None:
        tokens = TokenCounter.count("Hello, world!", "gpt-4")
        self.assertGreater(tokens, 0)

    def test_count_chinese(self) -> None:
        tokens = TokenCounter.count("你好世界，这是一个测试", "gpt-4")
        self.assertGreater(tokens, 0)

    def test_count_messages(self) -> None:
        messages = [
            {"role": "user", "content": "Hello", "content_type": "text"},
            {"role": "assistant", "content": "World", "content_type": "text"},
            {"role": "assistant", "content": "...", "content_type": "thinking"},
        ]
        result = TokenCounter.count_messages(messages, "gpt-4")
        self.assertEqual(len(result), 3)
        # thinking 类型应该为 0
        self.assertEqual(result[2]["token_count"], 0)
        # user/assistant 有内容
        self.assertGreater(result[0]["token_count"], 0)
        self.assertGreater(result[1]["token_count"], 0)

    def test_estimate_cost(self) -> None:
        cost = TokenCounter.estimate_cost(1000, 500, 0.15, 0.60)
        expected = (1000 / 1_000_000 * 0.15) + (500 / 1_000_000 * 0.60)
        self.assertAlmostEqual(cost, expected)

    def test_rough_estimate(self) -> None:
        text = "Hello" + "你好" * 100
        tokens = TokenCounter._rough_estimate(text)
        self.assertGreater(tokens, 0)


if __name__ == "__main__":
    unittest.main()
