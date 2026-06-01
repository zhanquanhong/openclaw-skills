"""Token Watcher 全局配置。"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    # 数据库
    db_path: str = "token_watcher.db"

    # OpenClaw 采集
    openclaw_poll_interval_sec: int = 60
    openclaw_history_days: int = 7
    openclaw_session_limit: int = 50
    openclaw_transcript_chars_limit: int = 200_000  # transcript 读取字符上限

    # API 代理
    proxy_host: str = "0.0.0.0"
    proxy_port: int = 8090
    proxy_upstream_url: str = "https://api.deepseek.com"
    proxy_port_mappings: dict = field(default_factory=lambda: {
        8090: "default",
    })
    proxy_pass_through_headers: tuple = (
        "Authorization", "Content-Type", "Accept",
        "User-Agent", "X-Request-Id", "X-Trace-Id",
    )
    proxy_request_timeout: int = 300

    # Dashboard
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8100

    # Token 计费（每百万 token 的 USD 价格）
    model_pricing: dict = field(default_factory=lambda: {
        "deepseek-v4-flash": {"input": 0.15, "output": 0.60},
        "deepseek-chat": {"input": 0.14, "output": 0.28},
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
        "glm-4": {"input": 0.50, "output": 2.00},
    })

    # 浪费阈值：input/output ratio > 此值标记为高浪费
    waste_ratio_threshold: float = 3.0

    # ── v1.0 智能建议阈值（保留兼容） ──
    advisor_output_capped_ratio: float = 0.85
    advisor_context_overflow_ratio: float = 0.7
    advisor_deep_session_turns: int = 10
    advisor_small_task_max_tokens: int = 500

    # ── v1.2 多维建议引擎阈值 ──
    # 维度 A：输入质量
    advisor_avg_msg_token_threshold: int = 800       # 单条消息平均 token 上限
    advisor_first3waste_ratio: float = 0.20           # 前 3 轮输出/输入比下限
    advisor_first3input_ratio: float = 0.60           # 前 3 轮输入占总 input 比上限

    # 维度 B：上下文管理
    advisor_system_prompt_ratio_threshold: float = 0.25  # system prompt 占比上限
    advisor_thinking_ratio_threshold: float = 2.0        # thinking/output 比例上限
    advisor_imbalance_turns: int = 20                    # 用户发言数上限（AI 无回复时）
    advisor_imbalance_ratio: float = 3.0                 # user/assistant 比上限

    # 维度 C：模型配置
    advisor_output_capped_divisible_check: bool = True   # 是否检查 output 能被 max_tokens 整除

    # 维度 D：会话生命周期
    advisor_zombie_days: int = 7                          # 僵尸会话闲置天数
    advisor_zombie_token_threshold: int = 50_000          # 僵尸会话 token 下限
    advisor_fragmentation_threshold: int = 20             # 30 天内会话数上限
    advisor_fragmentation_avg_turns: int = 5              # 平均轮次上限

    # 多样性保证器
    advisor_max_per_session: int = 3                     # 同一会话最多建议数
    advisor_min_dimensions: int = 2                      # 建议覆盖最少维度数

    # Dashboard 访问令牌（空=不验证）
    dashboard_token: str = "tw2026"


# 全局单例
config = Config()
