"""权限判定结果。纯数据，不含弹窗或 HTTP。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, Protocol

PermissionAction = Literal["allow", "ask", "deny"]
PermissionMode = Literal["default", "acceptEdits", "plan", "auto", "bypass"]
ApprovalChoice = Literal["once", "always", "deny"]

MODES: tuple[PermissionMode, ...] = (
    "default",
    "acceptEdits",
    "plan",
    "auto",
    "bypass",
)


@dataclass(frozen=True)
class PermissionDecision:
    """一次工具调用的规则结论。"""

    action: PermissionAction
    rule: str | None = None
    reason: str | None = None


class ApprovalPort(Protocol):
    """人工审批。实现放在 ui，safety/agent 只调 prompt。"""

    async def prompt(self, tool_name: str, args: Mapping[str, Any]) -> ApprovalChoice:
        """返回 once / always / deny。"""
        ...
