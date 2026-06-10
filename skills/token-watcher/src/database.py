"""SQLite 数据库模型。存储会话、消息、采集记录。"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, Any

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    id            TEXT PRIMARY KEY,
    source        TEXT    NOT NULL,   -- openclaw / proxy / extension
    source_id     TEXT,               -- 原始会话 ID
    title         TEXT,
    model         TEXT,
    total_input_tokens   INTEGER DEFAULT 0,
    total_output_tokens  INTEGER DEFAULT 0,
    input_output_ratio   REAL    DEFAULT 0,
    message_count        INTEGER DEFAULT 0,
    cost_estimate        REAL    DEFAULT 0,
    accuracy      TEXT    DEFAULT 'estimated',  -- real / estimated / rough
    context_info  TEXT    DEFAULT '{}',          -- JSON: 首句/轮次/时长等
    start_time    TEXT,
    end_time      TEXT,
    created_at    TEXT    DEFAULT (datetime('now', 'localtime')),
    updated_at    TEXT    DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT    NOT NULL,
    role            TEXT    NOT NULL,   -- user / assistant / system / tool
    content         TEXT    NOT NULL,
    token_count     INTEGER DEFAULT 0,
    content_type    TEXT    DEFAULT 'text',  -- text / thinking / tool_call / tool_result
    message_index   INTEGER DEFAULT 0,
    timestamp       TEXT,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS proxy_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id      TEXT,
    model           TEXT,
    input_tokens    INTEGER DEFAULT 0,
    output_tokens   INTEGER DEFAULT 0,
    total_tokens    INTEGER DEFAULT 0,
    cost            REAL    DEFAULT 0,
    stream          INTEGER DEFAULT 0,
    channel         TEXT    DEFAULT '',
    response_time_ms INTEGER DEFAULT 0,
    timestamp       TEXT    DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_conv_source   ON conversations(source);
CREATE INDEX IF NOT EXISTS idx_conv_start    ON conversations(start_time);
CREATE INDEX IF NOT EXISTS idx_msg_conv      ON messages(conversation_id);
"""

# 新增列的迁移列表：需要给已有表增加的列
MIGRATIONS = [
    "ALTER TABLE conversations ADD COLUMN context_info TEXT DEFAULT '{}'",
    "ALTER TABLE conversations ADD COLUMN total_cache_read_tokens INTEGER DEFAULT 0",
    "ALTER TABLE conversations ADD COLUMN api_call_count INTEGER DEFAULT 0",
    "ALTER TABLE proxy_logs ADD COLUMN channel TEXT DEFAULT ''",
    "ALTER TABLE proxy_logs ADD COLUMN response_time_ms INTEGER DEFAULT 0",
]


class Database:
    """SQLite 数据库封装。"""

    def __init__(self, db_path: str = "token_watcher.db") -> None:
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()

    # ── 连接管理 ──────────────────────────────────────────

    def _connect(self) -> None:
        """连接数据库并初始化表结构。"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.executescript(SCHEMA_SQL)
            self.conn.commit()
            # 执行数据库迁移
            self._run_migrations()
            logger.info("数据库已连接: %s", self.db_path)
        except sqlite3.Error as e:
            logger.error("数据库连接失败: %s", e)
            raise

    def _run_migrations(self) -> None:
        """执行数据库迁移，添加新增列。"""
        for sql in MIGRATIONS:
            try:
                self.conn.execute(sql)
                self.conn.commit()
                logger.info("数据库迁移完成: %s", sql[:60])
            except sqlite3.OperationalError as e:
                # "duplicate column name" 说明已存在，忽略
                if "duplicate column" not in str(e).lower():
                    logger.warning("数据库迁移失败: %s", e)
                # 否则列已存在，不需要迁移

    def close(self) -> None:
        """关闭数据库连接。"""
        if self.conn:
            self.conn.close()
            self.conn = None

    # ── 会话操作 ──────────────────────────────────────────

    def upsert_conversation(self, conv: dict[str, Any]) -> None:
        """插入或更新一个会话记录。

        Args:
            conv: 会话数据字典，必须包含 id
        """
        context_info = conv.get("context_info", "{}")
        if isinstance(context_info, dict):
            context_info = json.dumps(context_info, ensure_ascii=False)

        # 新 context_info 为空（{}）时保留旧值，防止 transcript 被轮转后数据漂移
        _is_new_ctx_empty = context_info.strip() in ("{}", "", "null")

        update_cols = [
            "model                    = excluded.model",
            "title                    = excluded.title",
            "source_id                = excluded.source_id",
            "total_input_tokens        = excluded.total_input_tokens",
            "total_output_tokens       = excluded.total_output_tokens",
            "total_cache_read_tokens   = excluded.total_cache_read_tokens",
            "api_call_count            = excluded.api_call_count",
            "input_output_ratio        = excluded.input_output_ratio",
            "cost_estimate             = excluded.cost_estimate",
            "accuracy                  = excluded.accuracy",
            "end_time                  = excluded.end_time",
            "updated_at                = datetime('now', 'localtime')",
        ]
        if not _is_new_ctx_empty:
            update_cols.insert(7, "message_count = excluded.message_count")
            update_cols.insert(9, "context_info  = excluded.context_info")

        set_clause = ",\n            ".join(update_cols)
        sql = f"""
        INSERT INTO conversations
            (id, source, source_id, title, model,
             total_input_tokens, total_output_tokens, total_cache_read_tokens,
             api_call_count,
             input_output_ratio, message_count,
             cost_estimate, accuracy,
             context_info, start_time, end_time, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
        ON CONFLICT(id) DO UPDATE SET
            {set_clause};
        """
        ratio = 0.0
        total_out = conv.get("total_output_tokens", 0)
        total_in = conv.get("total_input_tokens", 0)
        if total_out > 0:
            ratio = round(total_in / total_out, 2)
        self.conn.execute(sql, (
            conv["id"],
            conv.get("source", "openclaw"),
            conv.get("source_id"),
            conv.get("title", ""),
            conv.get("model", ""),
            total_in,
            total_out,
            conv.get("total_cache_read_tokens", 0),
            conv.get("api_call_count", 0),
            ratio,
            conv.get("message_count", 0),
            conv.get("cost_estimate", 0.0),
            conv.get("accuracy", "estimated"),
            context_info,
            conv.get("start_time"),
            conv.get("end_time"),
        ))
        self.conn.commit()

    def delete_conversation(self, conv_id: str) -> None:
        """删除会话及其所有消息。"""
        self.conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        self.conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        self.conn.commit()

    def get_conversation(self, conv_id: str) -> Optional[dict[str, Any]]:
        """按 ID 获取单个会话。"""
        row = self.conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conv_id,)
        ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_conversations(self, limit: int = 100, offset: int = 0,
                           source: Optional[str] = None) -> list[dict[str, Any]]:
        """列出会话，按时间倒序。"""
        if source:
            rows = self.conn.execute(
                "SELECT * FROM conversations WHERE source = ? ORDER BY start_time DESC LIMIT ? OFFSET ?",
                (source, limit, offset),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM conversations ORDER BY start_time DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_total_stats(self) -> dict[str, Any]:
        """获取全局统计汇总。"""
        row = self.conn.execute("""
            SELECT
                COUNT(*)                          AS total_conversations,
                COALESCE(SUM(total_input_tokens), 0)   AS total_input,
                COALESCE(SUM(total_output_tokens), 0)  AS total_output,
                COALESCE(SUM(total_cache_read_tokens), 0) AS total_cache_read,
                COALESCE(SUM(api_call_count), 0)        AS total_api_calls,
                COALESCE(SUM(cost_estimate), 0)        AS total_cost,
                COALESCE(SUM(message_count), 0)        AS total_messages
            FROM conversations
        """).fetchone()
        return dict(row)

    def get_high_waste_conversations(self, threshold: float = 3.0,
                                     limit: int = 20) -> list[dict[str, Any]]:
        """获取高浪费对话（输入/输出比例高于阈值），按时间倒序。"""
        rows = self.conn.execute("""
            SELECT * FROM conversations
            WHERE input_output_ratio > ?
            ORDER BY start_time DESC
            LIMIT ?
        """, (threshold, limit)).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_daily_trends(self, days: int = 30) -> list[dict[str, Any]]:
        """获取每日 token 趋势。"""
        rows = self.conn.execute("""
            SELECT
                DATE(start_time) AS day,
                SUM(total_input_tokens)  AS input_tokens,
                SUM(total_output_tokens) AS output_tokens,
                SUM(cost_estimate)       AS cost
            FROM conversations
            WHERE start_time >= DATE('now', '-' || ? || ' days')
            GROUP BY DATE(start_time)
            ORDER BY day
        """, (days,)).fetchall()
        return [dict(r) for r in rows]

    def get_source_breakdown(self) -> list[dict[str, Any]]:
        """按来源统计（含代理渠道）。"""
        rows = self.conn.execute("""
            SELECT
                source,
                COUNT(*)                       AS count,
                COALESCE(SUM(total_input_tokens), 0)  AS input_tokens,
                COALESCE(SUM(total_output_tokens), 0) AS output_tokens,
                COALESCE(SUM(cost_estimate), 0)       AS cost
            FROM conversations
            GROUP BY source
        """).fetchall()
        return [dict(r) for r in rows]

    def get_proxy_logs(self, limit: int = 200,
                       channel: Optional[str] = None) -> list[dict[str, Any]]:
        """获取代理调用日志明细。

        Args:
            limit: 最大返回条数
            channel: 可选，按渠道过滤

        Returns:
            代理调用日志列表
        """
        if channel:
            rows = self.conn.execute("""
                SELECT * FROM proxy_logs
                WHERE channel = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (channel, limit)).fetchall()
        else:
            rows = self.conn.execute("""
                SELECT * FROM proxy_logs
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_proxy_channel_breakdown(self) -> list[dict[str, Any]]:
        """按代理渠道统计用量。"""
        rows = self.conn.execute("""
            SELECT
                COALESCE(NULLIF(channel, ''), 'unknown') AS channel,
                COUNT(*)                                  AS count,
                COALESCE(SUM(input_tokens), 0)            AS input_tokens,
                COALESCE(SUM(output_tokens), 0)           AS output_tokens,
                COALESCE(SUM(total_tokens), 0)            AS total_tokens,
                COALESCE(SUM(cost), 0)                    AS cost
            FROM proxy_logs
            GROUP BY channel
            ORDER BY total_tokens DESC
        """).fetchall()
        return [dict(r) for r in rows]

    # ── 消息操作 ──────────────────────────────────────────

    def insert_messages(self, conv_id: str,
                        messages: list[dict[str, Any]]) -> None:
        """批量插入消息。先删旧消息再写新消息。"""
        self.conn.execute(
            "DELETE FROM messages WHERE conversation_id = ?", (conv_id,)
        )
        sql = """
        INSERT INTO messages
            (conversation_id, role, content, token_count,
             content_type, message_index, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        rows = []
        for idx, msg in enumerate(messages):
            rows.append((
                conv_id,
                msg.get("role", ""),
                msg.get("content", ""),
                msg.get("token_count", 0),
                msg.get("content_type", "text"),
                idx,
                msg.get("timestamp", datetime.now().isoformat()),
            ))
        self.conn.executemany(sql, rows)
        self.conn.commit()

    def get_messages(self, conv_id: str) -> list[dict[str, Any]]:
        """获取会话的所有消息。"""
        rows = self.conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY message_index",
            (conv_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── 代理日志 ──────────────────────────────────────────

    def insert_proxy_log(self, log: dict[str, Any]) -> None:
        """插入一条代理调用日志。"""
        self.conn.execute("""
            INSERT INTO proxy_logs
                (request_id, model, input_tokens, output_tokens,
                 total_tokens, cost, stream, channel, response_time_ms,
                 timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log.get("request_id"),
            log.get("model"),
            log.get("input_tokens", 0),
            log.get("output_tokens", 0),
            log.get("total_tokens", 0),
            log.get("cost", 0.0),
            1 if log.get("stream") else 0,
            log.get("channel", ""),
            log.get("response_time_ms", 0),
            log.get("timestamp", datetime.now().isoformat()),
        ))
        self.conn.commit()

    # ── 工具方法 ──────────────────────────────────────────

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        """将 sqlite3.Row 转为普通 dict。"""
        d = dict(row)
        # 格式化为空时给个空字符串
        if d.get("context_info") is None:
            d["context_info"] = "{}"
        return d
