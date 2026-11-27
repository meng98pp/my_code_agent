"""L3d 用 stdin 做 once/always/deny。完整 picker 留到 L6。"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from my_code_agent.interfaces.permissions import ApprovalChoice
from my_code_agent.safety.permissions import format_call


class StdinApproval:
    async def prompt(self, tool_name: str, args: Mapping[str, Any]) -> ApprovalChoice:
        question = (
            f"是否允许执行 {format_call(tool_name, args)}？\n"
            "  1. 允许\n"
            f"  2. 允许，且本会话不再询问 {tool_name}\n"
            "  3. 拒绝\n"
            "请输入 1 / 2 / 3（直接回车视为拒绝）："
        )
        try:
            raw = await asyncio.to_thread(input, question)
        except EOFError:
            return "deny"
        text = (raw or "").strip().lower()
        if text in ("1", "once", "y", "yes"):
            return "once"
        if text in ("2", "always"):
            return "always"
        return "deny"
