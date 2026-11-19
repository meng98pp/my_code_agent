"""Agent 向 UI 推送的事件。实现层不得反向依赖 rich / prompt_toolkit。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AgentEvent:
    """一次可观察输出。kind 取值见模块常量。"""

    kind: str
    text: str = ""
    tool_name: str = ""


EVENT_THINKING = "thinking"
EVENT_TEXT = "text"
EVENT_TOOL_CALL = "tool_call"
EVENT_TOOL_RESULT = "tool_result"
EVENT_RETRY = "retry"
EVENT_ERROR = "error"
EVENT_REMINDER = "reminder"


class EventSink(Protocol):
    """UI 或日志实现此协议；agent 只调用 emit。"""

    def emit(self, event: AgentEvent) -> None:
        """同步投递一条事件。允许空实现（测试用）。"""
        ...
