"""Token Watcher 测试 - 数据库"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database import Database


class TestDatabase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.db = Database(self.db_path)

    def tearDown(self) -> None:
        self.db.close()
        if os.path.isfile(self.db_path):
            os.unlink(self.db_path)

    def test_upsert_and_get_conversation(self) -> None:
        conv = {
            "id": "test_001",
            "source": "openclaw",
            "source_id": "key:test",
            "title": "测试会话",
            "model": "deepseek-v4-flash",
            "total_input_tokens": 1500,
            "total_output_tokens": 500,
            "cost_estimate": 0.001,
            "accuracy": "real",
            "start_time": "2026-05-26T12:00:00",
            "end_time": "2026-05-26T12:30:00",
            "message_count": 10,
        }
        self.db.upsert_conversation(conv)

        got = self.db.get_conversation("test_001")
        assert got is not None
        self.assertEqual(got["title"], "测试会话")
        self.assertEqual(got["total_input_tokens"], 1500)
        self.assertEqual(got["total_output_tokens"], 500)
        self.assertEqual(got["input_output_ratio"], 3.0)  # 1500/500

    def test_delete_conversation(self) -> None:
        conv = {"id": "del_test", "source": "openclaw", "title": "删除测试"}
        self.db.upsert_conversation(conv)
        self.db.insert_messages("del_test", [
            {"role": "user", "content": "你好", "content_type": "text"},
        ])
        self.db.delete_conversation("del_test")
        self.assertIsNone(self.db.get_conversation("del_test"))
        self.assertEqual(len(self.db.get_messages("del_test")), 0)

    def test_insert_and_get_messages(self) -> None:
        conv = {"id": "msg_test", "source": "openclaw", "title": "消息测试"}
        self.db.upsert_conversation(conv)
        messages = [
            {"role": "user", "content": "Hello", "token_count": 10,
             "content_type": "text", "timestamp": "2026-01-01T00:00:00"},
            {"role": "assistant", "content": "World", "token_count": 20,
             "content_type": "text", "timestamp": "2026-01-01T00:00:01"},
        ]
        self.db.insert_messages("msg_test", messages)
        got = self.db.get_messages("msg_test")
        self.assertEqual(len(got), 2)
        self.assertEqual(got[0]["role"], "user")
        self.assertEqual(got[1]["token_count"], 20)

    def test_get_total_stats(self) -> None:
        self.db.upsert_conversation({
            "id": "s1", "source": "openclaw",
            "total_input_tokens": 1000, "total_output_tokens": 200,
            "cost_estimate": 0.01, "message_count": 5,
        })
        self.db.upsert_conversation({
            "id": "s2", "source": "openclaw",
            "total_input_tokens": 2000, "total_output_tokens": 400,
            "cost_estimate": 0.02, "message_count": 10,
        })
        stats = self.db.get_total_stats()
        self.assertEqual(stats["total_conversations"], 2)
        self.assertEqual(stats["total_input"], 3000)
        self.assertEqual(stats["total_output"], 600)
        self.assertEqual(stats["total_messages"], 15)
        self.assertAlmostEqual(stats["total_cost"], 0.03)

    def test_get_high_waste(self) -> None:
        self.db.upsert_conversation({
            "id": "w1", "source": "openclaw",
            "total_input_tokens": 5000, "total_output_tokens": 100,
        })
        self.db.upsert_conversation({
            "id": "w2", "source": "openclaw",
            "total_input_tokens": 100, "total_output_tokens": 100,
        })
        waste = self.db.get_high_waste_conversations(threshold=3.0)
        self.assertEqual(len(waste), 1)
        self.assertEqual(waste[0]["id"], "w1")

    def test_get_source_breakdown(self) -> None:
        self.db.upsert_conversation({
            "id": "b1", "source": "openclaw",
            "total_input_tokens": 100, "total_output_tokens": 50,
        })
        self.db.upsert_conversation({
            "id": "b2", "source": "proxy",
            "total_input_tokens": 200, "total_output_tokens": 100,
        })
        breakdown = self.db.get_source_breakdown()
        sources = {b["source"]: b for b in breakdown}
        self.assertIn("openclaw", sources)
        self.assertIn("proxy", sources)
        self.assertEqual(sources["openclaw"]["count"], 1)


if __name__ == "__main__":
    unittest.main()
