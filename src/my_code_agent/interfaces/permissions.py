"""权限判定结果。纯数据，不含弹窗或 HTTP。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PermissionAction = Literal["allow", "ask", "deny"]
PermissionMode = Literal["default", "acceptEdits", "plan", "auto", "bypass"]

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
