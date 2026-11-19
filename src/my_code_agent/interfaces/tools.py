"""工具契约。handler 由 tool 包实现，本模块不执行副作用。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

SelfCheck = Callable[[Mapping[str, Any]], str | None]
ToolHandler = Callable[..., Any | Awaitable[Any]]


@dataclass(frozen=True)
class ToolSpec:
    """一条可注册工具的元数据。"""

    name: str
    handler: ToolHandler
    readonly: bool = False
    sequential: bool = False
    self_check: SelfCheck | None = None
    description: str = ""


class ToolContext(Protocol):
    """工具运行时依赖。由 core 每轮注入，tool 不得自己 new 会话对象。"""

    session_id: str
    plan_file: Path | None
    last_decision_source: str
    last_op_id: str | None
