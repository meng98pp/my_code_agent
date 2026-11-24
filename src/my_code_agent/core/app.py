"""一轮输入的编排：斜杠命令或交给 Agent。L3a 接入 read_file，仍无压缩 / @ / 记忆 / jsonl。"""

from __future__ import annotations

import uuid
from typing import Literal

from my_code_agent.agent import PydanticAgentRunner, build_agent
from my_code_agent.config import AppPaths, Settings
from my_code_agent.interfaces.events import EventSink
from my_code_agent.interfaces.session_types import Session
from my_code_agent.interfaces.tools import AgentDeps
from my_code_agent.tool import ReadFileState, bootstrap_tools

TurnAction = Literal["ok", "exit", "continue"]

HELP_TEXT = """可用命令（L3a）：
  /help   显示本说明
  /exit   退出
本层可用工具：read_file（读工作区文件，带行号）。写入、命令、记忆仍未开放。
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
        self._read_file_state = ReadFileState()
        registry = bootstrap_tools() #注册tool
        self._runner = PydanticAgentRunner(
            build_agent(settings, tools=registry.as_pydantic_tools()),
            sink=sink,
        )

    async def handle_line(self, raw: str) -> TurnAction:
        text = raw.strip()
        if not text:
            return "continue"
        if text.startswith("/"):
            return self._handle_command(text)
        ctx = AgentDeps(
            session_id=self.session.session_id,
            read_file_state=self._read_file_state,
        )
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
