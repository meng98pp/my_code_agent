"""把 AgentEvent 打到终端。这是 UI，不是 logging。"""

from __future__ import annotations

from my_code_agent.interfaces.events import (
    EVENT_ERROR,
    EVENT_PERMISSION,
    EVENT_TEXT,
    EVENT_THINKING,
    EVENT_TOOL_CALL,
    EVENT_TOOL_RESULT,
    AgentEvent,
)


class ConsoleSink:
    def __init__(self) -> None:
        self._open_line = False
        self._thinking_open = False

    def emit(self, event: AgentEvent) -> None:
        if event.kind == EVENT_THINKING:
            self._emit_thinking(event)
            return
        if event.kind == EVENT_TEXT:
            self._emit_text(event)
            return
        self._end_open_line()
        if event.kind == EVENT_ERROR:
            print(event.text)
            return
        if event.kind == EVENT_PERMISSION:
            print(f"permission: {event.text}")
            return
        if event.kind == EVENT_TOOL_CALL:
            print(f"tool_call: {event.tool_name}")
            return
        if event.kind == EVENT_TOOL_RESULT:
            print(f"tool_result: {event.tool_name}")

    def _emit_thinking(self, event: AgentEvent) -> None:
        body = event.text
        if event.delta:
            if not body:
                return
            if not self._thinking_open:
                self._end_open_line()
                print("thinking:")
                print("  ", end="", flush=True)
                self._thinking_open = True
                self._open_line = True
            print(body.replace("\n", "\n  "), end="", flush=True)
            return
        self._end_open_line()
        body = body.strip()
        if body:
            print(f"thinking:\n  {body}")

    def _emit_text(self, event: AgentEvent) -> None:
        if event.delta:
            if self._thinking_open:
                print(flush=True)
                self._thinking_open = False
                self._open_line = False
            if event.text:
                print(event.text, end="", flush=True)
                self._open_line = True
            return
        if self._open_line:
            print()
            self._open_line = False
            self._thinking_open = False
            if event.text:
                print(event.text)
            return
        if event.text:
            print(event.text)

    def _end_open_line(self) -> None:
        if self._open_line:
            print()
            self._open_line = False
        self._thinking_open = False
