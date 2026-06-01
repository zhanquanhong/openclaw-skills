"""采集器抽象基类。"""

from abc import ABC, abstractmethod
from typing import Any


class BaseCollector(ABC):
    """所有采集器的基类。"""

    @abstractmethod
    def collect(self) -> list[dict[str, Any]]:
        """执行一次采集，返回会话列表。

        Returns:
            会话列表，每项为 dict，包含:
              - id: str           会话唯一 ID
              - source: str       来源标识
              - title: str        会话标题
              - model: str        使用的模型
              - messages: list    消息列表
              - start_time: str   开始时间
              - end_time: str     结束时间
        """
        ...

    @abstractmethod
    def name(self) -> str:
        """采集器名称。"""
        ...
