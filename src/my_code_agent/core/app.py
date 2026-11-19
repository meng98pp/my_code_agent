"""一轮输入的编排：斜杠命令或交给 Agent。L2 不做压缩、@、记忆、jsonl。"""

from __future__ import annotations

import uuid
from typing import Literal

from my_code_agent.agent import PydanticAgentRunner, build_agent
from my_code_agent.config import AppPaths, Settings
from my_code_agent.interfaces.events import EventSink
from my_code_agent.interfaces.session_types import Session

from .deps import EmptyToolContext

TurnAction = Literal["ok", "exit", "continue"]

HELP_TEXT = """可用命令（L2）：
  /help   显示本说明
  /exit   退出
更多命令（/status、/resume、/memory 等）在后续层提供。
"""


class App:
    def __init__(self, settings: Settings, paths: AppPaths, sink: EventSink) -> None:
        self.settings = settings
        self.paths = paths
        self.sink = sink
        self.session = Session(
            session_id=str(uuid.uuid4()),
            model_name=settings.model,
        )
        self._runner = PydanticAgentRunner(build_agent(settings), sink=sink)

    async def handle_line(self, raw: str) -> TurnAction:
        text = raw.strip()
        if not text:
            return "continue"
        if text.startswith("/"):
            return self._handle_command(text)
        ctx = EmptyToolContext(session_id=self.session.session_id)
        await self._runner.run_turn(text, self.session, ctx)
        return "ok"

    def _handle_command(self, text: str) -> TurnAction:
        from my_code_agent.interfaces.events import EVENT_ERROR, EVENT_TEXT, AgentEvent

        name, _, _args = text[1:].partition(" ")
        if name == "exit":
            return "exit"
        if name == "help":
            self.sink.emit(AgentEvent(kind=EVENT_TEXT, text=HELP_TEXT.strip()))
            return "continue"
        self.sink.emit(
            AgentEvent(
                kind=EVENT_ERROR,
                text=f"未知命令：/{name}，输入 /help 查看可用命令",
            )
        )
        return "continue"
