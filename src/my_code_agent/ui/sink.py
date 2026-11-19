"""把 AgentEvent 打到终端。这是 UI，不是 logging。"""

from __future__ import annotations

from my_code_agent.interfaces.events import (
    EVENT_ERROR,
    EVENT_TEXT,
    EVENT_THINKING,
    EVENT_TOOL_CALL,
    EVENT_TOOL_RESULT,
    AgentEvent,
)


class ConsoleSink:
    def emit(self, event: AgentEvent) -> None:
        if event.kind == EVENT_THINKING:
            body = event.text.strip()
            if body:
                print(f"thinking:\n  {body}")
            return
        if event.kind == EVENT_TEXT:
            print(event.text)
            return
        if event.kind == EVENT_ERROR:
            print(event.text)
            return
        if event.kind == EVENT_TOOL_CALL:
            print(f"tool_call: {event.tool_name}")
            return
        if event.kind == EVENT_TOOL_RESULT:
            print(f"tool_result: {event.tool_name}")
