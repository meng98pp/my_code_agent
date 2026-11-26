"""一轮输入的编排。L3c 接入 shell / jobs；仍无压缩 / @ / 记忆 / jsonl。"""

from __future__ import annotations

import uuid
from typing import Literal

from my_code_agent.agent import PydanticAgentRunner, build_agent
from my_code_agent.config import AppPaths, Settings
from my_code_agent.interfaces.events import EventSink
from my_code_agent.interfaces.session_types import Session
from my_code_agent.interfaces.tools import AgentDeps
from my_code_agent.session import FileHistory
from my_code_agent.tool import ReadFileState, bootstrap_tools

from .jobs import JobRegistry

TurnAction = Literal["ok", "exit", "continue"]

HELP_TEXT = """可用命令（L3c）：
  /help   显示本说明
  /exit   退出
  /undo   撤销最近一次 write_file / edit_file
  /jobs   列出后台 job
本层可用工具：read_file、edit_file、write_file、run_command、job_kill、monitor。
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
        self._file_history = FileHistory(self.session.session_id, root=paths.project_dir())
        self._job_registry = JobRegistry(self.session.session_id, root=paths.home)
        registry = bootstrap_tools()
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
            file_history=self._file_history,
            job_registry=self._job_registry,
        )
        await self._runner.run_turn(text, self.session, ctx)
        return "ok"

    def close(self) -> None:
        registry = getattr(self, "_job_registry", None)
        if registry is not None:
            registry.shutdown()

    def _handle_command(self, text: str) -> TurnAction:
        from my_code_agent.interfaces.events import EVENT_ERROR, EVENT_TEXT, AgentEvent

        name, _, _args = text[1:].partition(" ")
        if name == "exit":
            self.close()
            return "exit"
        if name == "help":
            self.sink.emit(AgentEvent(kind=EVENT_TEXT, text=HELP_TEXT.strip()))
            return "continue"
        if name == "undo":
            self._undo()
            return "continue"
        if name == "jobs":
            self._jobs()
            return "continue"
        self.sink.emit(
            AgentEvent(
                kind=EVENT_ERROR,
                text=f"未知命令：/{name}，输入 /help 查看可用命令",
            )
        )
        return "continue"

    def _undo(self) -> None:
        from my_code_agent.interfaces.events import EVENT_TEXT, AgentEvent

        op = self._file_history.rollback_last_op()
        if op is None:
            self.sink.emit(AgentEvent(kind=EVENT_TEXT, text="没有可撤销的写文件操作"))
            return
        self._read_file_state.forget(op.path)
        action = "已删除（当时文件不存在）" if op.created else "已恢复调用前内容"
        self.sink.emit(AgentEvent(kind=EVENT_TEXT, text=f"已撤销 {op.tool} → {op.path}（{action}）"))

    def _jobs(self) -> None:
        from my_code_agent.interfaces.events import EVENT_TEXT, AgentEvent

        jobs = [job for job in self._job_registry.list() if job.background]
        if not jobs:
            self.sink.emit(AgentEvent(kind=EVENT_TEXT, text="本会话还没有后台 job"))
            return
        lines = []
        for job in jobs:
            lines.append(f"{job.id} [{job.status}] {job.description}")
            lines.append(f"  日志：{job.log_path}")
        self.sink.emit(AgentEvent(kind=EVENT_TEXT, text="\n".join(lines)))
