"""会话实体。持久化由 session 包实现，这里只有内存形状。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Session:
    """一轮或多轮对话的活状态。history 元素类型由 L2 接到模型 SDK 后再具体化。"""

    session_id: str
    history: list[Any] = field(default_factory=list)
    surfaced_memories: set[str] = field(default_factory=set)
    compact_failures: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    model_name: str = ""
    pending_input: str = ""
