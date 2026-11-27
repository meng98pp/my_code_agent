"""Agent 向 UI 推送的事件。实现层不得反向依赖 rich / prompt_toolkit。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AgentEvent:
    """一次可观察输出。kind 取值见模块常量。

    delta=True 时 text 是增量片段，UI 应追加打印且不要换行；
    同一段结束后会再发一条 delta=False 的收尾事件（text 可为空）。
    """

    kind: str
    text: str = ""
    tool_name: str = ""
    delta: bool = False


EVENT_THINKING = "thinking"
EVENT_TEXT = "text"
EVENT_TOOL_CALL = "tool_call"
EVENT_TOOL_RESULT = "tool_result"
EVENT_RETRY = "retry"
EVENT_ERROR = "error"
EVENT_REMINDER = "reminder"
EVENT_PERMISSION = "permission"


class EventSink(Protocol):
    """UI 或日志实现此协议；agent 只调用 emit。"""

    def emit(self, event: AgentEvent) -> None:
        """同步投递一条事件。允许空实现（测试用）。"""
        ...
