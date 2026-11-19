"""基于 pydantic-ai 的无工具 Agent 循环。不 import ui。"""

from __future__ import annotations

from typing import Any

from pydantic_ai import Agent
from pydantic_graph import End

from my_code_agent.interfaces.events import (
    EVENT_TEXT,
    EVENT_THINKING,
    EVENT_TOOL_CALL,
    EVENT_TOOL_RESULT,
    AgentEvent,
    EventSink,
)
from my_code_agent.interfaces.runner import AgentTurnResult
from my_code_agent.interfaces.session_types import Session
from my_code_agent.interfaces.tools import ToolContext
from my_code_agent.llm import build_chat_model

from .instructions import INSTRUCTIONS, render_project_context


class NullEventSink:
    def emit(self, event: AgentEvent) -> None:
        return None


class PydanticAgentRunner:
    def __init__(self, agent: Agent, sink: EventSink | None = None) -> None:
        self._agent = agent
        self._sink: EventSink = sink or NullEventSink()

    async def run_turn(
        self,
        user_input: str,
        session: Session,
        ctx: ToolContext,
    ) -> AgentTurnResult:
        del ctx
        async with self._agent.iter(
            user_input,
            message_history=session.history,
        ) as run:
            node = run.next_node
            while not isinstance(node, End):
                node = await run.next(node)
                self._emit_node(node)

        result = run.result
        history = list(result.all_messages())
        new_messages = list(result.new_messages())
        session.history = history
        in_tok, out_tok = _usage_tokens(result)
        session.input_tokens += in_tok
        session.output_tokens += out_tok
        return AgentTurnResult(
            history=history,
            new_messages=new_messages,
            input_tokens=in_tok,
            output_tokens=out_tok,
        )

    def _emit_node(self, node: Any) -> None:
        if Agent.is_call_tools_node(node):
            for part in node.model_response.parts:
                self._emit_part(part)
            return
        if Agent.is_model_request_node(node):
            for part in node.request.parts:
                kind = getattr(part, "part_kind", "")
                if kind in ("tool-return", "retry-prompt"):
                    self._emit_part(part)


    def _emit_part(self, part: Any) -> None:
        kind = getattr(part, "part_kind", "")
        if kind == "thinking":
            self._sink.emit(AgentEvent(kind=EVENT_THINKING, text=str(getattr(part, "content", "") or "")))
        elif kind == "text":
            text = str(getattr(part, "content", "") or "").strip()
            if text:
                self._sink.emit(AgentEvent(kind=EVENT_TEXT, text=text))
        elif kind == "tool-call":
            self._sink.emit(
                AgentEvent(
                    kind=EVENT_TOOL_CALL,
                    tool_name=str(getattr(part, "tool_name", "")),
                    text=str(getattr(part, "args", "")),
                )
            )
        elif kind in ("tool-return", "retry-prompt"):
            self._sink.emit(
                AgentEvent(
                    kind=EVENT_TOOL_RESULT,
                    tool_name=str(getattr(part, "tool_name", "")),
                    text=str(getattr(part, "content", "")),
                )
            )


def build_agent(settings) -> Agent:
    model = build_chat_model(settings)
    agent = Agent(model, instructions=INSTRUCTIONS)

    @agent.instructions
    def project_context() -> str:
        return render_project_context()

    return agent


def _usage_tokens(result: Any) -> tuple[int, int]:
    usage = getattr(result, "usage", None)
    if callable(usage):
        usage = usage()
    if usage is None:
        return 0, 0
    return int(getattr(usage, "input_tokens", 0) or 0), int(getattr(usage, "output_tokens", 0) or 0)
