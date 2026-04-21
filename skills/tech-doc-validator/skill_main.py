#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OpenClaw Skill 主入口 - 生产级"""

import logging
import asyncio
from src.feishu_handler import FeishuSkillHandler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 创建处理器
handler = FeishuSkillHandler(app_id="cli_a93a64c12179dbcb")


async def on_message(event: dict) -> str:
    """OpenClaw 消息处理入口"""
    try:
        logger.info(f"收到消息事件：{event}")
        
        # 提取消息内容
        message = {
            "text": event.get("text", ""),
            "file_path": event.get("file_path"),
            "file_url": event.get("file_url"),
        }
        
        # 处理消息
        response = await handler.handle_message(message)
        
        return response
        
    except Exception as e:
        logger.error(f"处理失败：{e}", exc_info=True)
        return f"❌ 验证失败：{e}"


# 同步包装器
def handle_message(event: dict) -> str:
    """同步消息处理（OpenClaw 调用）"""
    return asyncio.run(on_message(event))


# 测试
if __name__ == "__main__":
    test_event = {
        "text": "/validate",
        "file_path": "/home/admin/.openclaw/workspace/test-data/云端 OpenClaw 分享技术方案.pdf"
    }
    result = handle_message(test_event)
    print(result)
