"""主 Agent 循环协议。实现放在 agent 包。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .session_types import Session
from .tools import ToolContext


@dataclass
class AgentTurnResult:
    """一轮结束后的可见结果。message 对象在 L2 与 SDK 对齐。"""

    history: list[Any] = field(default_factory=list)
    new_messages: list[Any] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0


class AgentRunner(Protocol):
    """把 user_input 跑到模型不再要工具为止。"""

    async def run_turn(
        self,
        user_input: str,
        session: Session,
        ctx: ToolContext,
    ) -> AgentTurnResult:
        """执行一轮 ReAct。L2 起实现。"""
        ...
