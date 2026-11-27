"""基于 pydantic-ai 的无工具 Agent 循环。不 import ui。"""

from __future__ import annotations

from collections.abc import Sequence
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
from my_code_agent.interfaces.tools import AgentDeps, ToolContext
from my_code_agent.llm import build_chat_model, build_model_settings

from .hooks import permission_hooks
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
        streamed_model = False
        async with self._agent.iter(
            user_input,
            message_history=session.history,
            deps=ctx,
        ) as run:
            async for node in run:
                if isinstance(node, End):
                    break
                if Agent.is_model_request_node(node):
                    streamed_model = await self._stream_model_request(node, run)
                    continue
                if Agent.is_call_tools_node(node):
                    self._emit_call_tools(node, skip_model_text=streamed_model)
                    streamed_model = False

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

    async def _stream_model_request(self, node: Any, run: Any) -> bool:
        """在 ModelRequestNode 上按 token 推送；成功则返回 True，避免 CallTools 再打一遍全文。"""
        for part in getattr(getattr(node, "request", None), "parts", ()) or ():
            kind = getattr(part, "part_kind", "")
            if kind in ("tool-return", "retry-prompt"):
                self._emit_part(part)

        stream_fn = getattr(node, "stream", None)
        ctx = getattr(run, "ctx", None)
        if stream_fn is None or ctx is None:
            return False

        saw_text = False
        saw_thinking = False
        async with stream_fn(ctx) as stream:
            async for event in stream:
                kind, chunk, extra = _stream_event_chunk(event)
                if not kind or not chunk:
                    continue
                if kind == "thinking":
                    saw_thinking = True
                    self._sink.emit(AgentEvent(kind=EVENT_THINKING, text=chunk, delta=True))
                elif kind == "text":
                    saw_text = True
                    self._sink.emit(AgentEvent(kind=EVENT_TEXT, text=chunk, delta=True))
                elif kind == "tool-call":
                    self._sink.emit(
                        AgentEvent(
                            kind=EVENT_TOOL_CALL,
                            tool_name=extra,
                            text=chunk,
                        )
                    )
        if saw_thinking and not saw_text:
            self._sink.emit(AgentEvent(kind=EVENT_THINKING, text="", delta=False))
        if saw_text:
            self._sink.emit(AgentEvent(kind=EVENT_TEXT, text="", delta=False))
        return True

    def _emit_call_tools(self, node: Any, *, skip_model_text: bool) -> None:
        if skip_model_text:
            return
        for part in node.model_response.parts:
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


def build_agent(settings, tools: Sequence[Any] | None = None) -> Agent:
    model = build_chat_model(settings)
    agent = Agent(
        model,
        instructions=INSTRUCTIONS,
        model_settings=build_model_settings(settings),
        tools=list(tools or ()),
        deps_type=AgentDeps,
        capabilities=[permission_hooks()],
    )#hooks登记

    @agent.instructions
    def project_context() -> str:
        return render_project_context()

    return agent


def _stream_event_chunk(event: Any) -> tuple[str, str, str]:
    """从 pydantic-ai 流事件取出 (kind, text, extra)。未知事件返回空 kind。"""
    part = getattr(event, "part", None)
    if part is not None:
        pk = getattr(part, "part_kind", "")
        if pk == "thinking":
            return "thinking", str(getattr(part, "content", "") or ""), ""
        if pk == "text":
            return "text", str(getattr(part, "content", "") or ""), ""
        if pk == "tool-call":
            return (
                "tool-call",
                str(getattr(part, "args", "") or ""),
                str(getattr(part, "tool_name", "") or ""),
            )
    delta = getattr(event, "delta", None)
    if delta is not None:
        dk = getattr(delta, "part_delta_kind", "")
        if dk == "thinking":
            return "thinking", str(getattr(delta, "content_delta", "") or ""), ""
        if dk == "text":
            return "text", str(getattr(delta, "content_delta", "") or ""), ""
    return "", "", ""


def _usage_tokens(result: Any) -> tuple[int, int]:
    usage = getattr(result, "usage", None)
    if callable(usage):
        usage = usage()
    if usage is None:
        return 0, 0
    return int(getattr(usage, "input_tokens", 0) or 0), int(getattr(usage, "output_tokens", 0) or 0)
