"""模型 → tokenizer 编码映射表。

tiktoken 支持的编码：
  - cl100k_base: GPT-4, GPT-3.5, DeepSeek, Claude（近似）
  - o200k_base:  GPT-4o, GLM-4 等新模型
  - p50k_base:   code-davinci-002
  - r50k_base:   davinci
"""

from typing import Optional

ModelEncodingMap = dict[str, str]

# 模型名关键词 → encoding 名
# 按模型名匹配规则：先精确匹配，再关键词匹配（支持通配符 *）
MODEL_ENCODING_RULES: list[tuple[str, str]] = [
    # 精确匹配
    ("deepseek-v4-flash", "cl100k_base"),
    ("deepseek-v4-pro", "cl100k_base"),
    ("deepseek-chat", "cl100k_base"),
    ("deepseek-reasoner", "cl100k_base"),
    # GPT-4o 系列 (o200k_base)
    ("gpt-4o", "o200k_base"),
    # Claude
    ("claude-3", "cl100k_base"),
    ("claude-3.5", "cl100k_base"),
    ("claude-4", "cl100k_base"),
    ("claude-opus", "cl100k_base"),
    ("claude-sonnet", "cl100k_base"),
    ("claude-haiku", "cl100k_base"),
    # GLM
    ("glm-4", "o200k_base"),
    ("glm-4v", "o200k_base"),
    ("glm-3", "cl100k_base"),
    # 关键词匹配
    ("gpt-4", "cl100k_base"),
    ("gpt-3.5", "cl100k_base"),
    ("deepseek", "cl100k_base"),
]

# 默认兜底
DEFAULT_ENCODING = "cl100k_base"

# tiktoken 编码的最大上下文 token 数近似值（用于校验）
ENCODING_MAX_TOKENS: dict[str, int] = {
    "cl100k_base": 128_000,
    "o200k_base": 128_000,
    "p50k_base": 8_192,
    "r50k_base": 4_096,
}


def resolve_encoding(model_name: Optional[str]) -> str:
    """根据模型名解析对应的 tiktoken encoding 名。

    Args:
        model_name: 模型名称，如 "deepseek-v4-flash", "gpt-4o"

    Returns:
        encoding 名称，如 "cl100k_base"

    Example:
        >>> resolve_encoding("deepseek-v4-flash")
        'cl100k_base'
        >>> resolve_encoding("unknown-model")
        'cl100k_base'
    """
    if not model_name:
        return DEFAULT_ENCODING

    name_lower = model_name.lower()

    # 1. 精确匹配
    for rule_name, enc in MODEL_ENCODING_RULES:
        if name_lower == rule_name:
            return enc

    # 2. 关键词包含匹配
    for rule_name, enc in MODEL_ENCODING_RULES:
        if rule_name in name_lower:
            return enc

    return DEFAULT_ENCODING


def get_pricing(model_name: Optional[str],
                pricing_map: dict[str, dict[str, float]]) -> tuple[float, float]:
    """获取模型的输入/输出单价（每百万 token USD）。

    Args:
        model_name: 模型名称
        pricing_map: 定价映射表

    Returns:
        (input_price_per_million, output_price_per_million) 的元组
        找不到时返回 (0, 0)
    """
    if not model_name:
        return (0.0, 0.0)

    name_lower = model_name.lower()

    # 精确匹配
    if name_lower in pricing_map:
        p = pricing_map[name_lower]
        return (p.get("input", 0), p.get("output", 0))

    # 关键词匹配
    for key, price in pricing_map.items():
        if key in name_lower:
            return (price.get("input", 0), price.get("output", 0))

    return (0.0, 0.0)
