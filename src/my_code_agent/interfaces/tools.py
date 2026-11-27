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


class ReadFileStatePort(Protocol):
    """会话级已读文件登记。实现放在 tool 包。"""

    def record(
        self,
        path: str,
        content: str,
        offset: int | None = None,
        limit: int | None = None,
    ) -> None: ...

    def get(self, path: str) -> Mapping[str, Any] | None: ...

    def forget(self, path: str) -> None: ...

    def paths(self) -> list[str]: ...

    def stale_paths(self) -> list[str]: ...


class ToolContext(Protocol):
    """工具运行时依赖。由 core 每轮注入，tool 不得自己 new 会话对象。"""

    session_id: str
    read_file_state: ReadFileStatePort
    plan_file: Path | None
    last_decision_source: str
    last_op_id: str | None


@dataclass
class AgentDeps:
    """每轮注入给 pydantic-ai 的依赖。L3a 先对齐字段；tasks/jobs 等后续切片再填实现。"""

    session_id: str
    read_file_state: Any
    plan_file: Path | None = None
    last_decision_source: str = ""
    last_op_id: str | None = None
    tasks_store: Any = None
    file_history: Any = None
    job_registry: Any = None
    subagent_job: Any = None
    subagent_runtime: Any = None
    permission_state: Any = None
    approval: Any = None
    writable_roots: Any = None
    memory_root: Path | None = None
    self_checks: Any = None
    settings: Any = None
    sink: Any = None
    classifier: Any = None
