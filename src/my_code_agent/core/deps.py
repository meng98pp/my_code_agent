"""L2 无工具，仍提供符合 ToolContext 协议的空依赖，避免 runner 走特殊分支。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class EmptyToolContext:
    session_id: str
    plan_file: Path | None = None
    last_decision_source: str = ""
    last_op_id: str | None = None
