"""记忆存储协议。实现放在 memory 包；路径来自 config，不在此写死。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class MemoryHeader:
    """一条记忆的元信息，召回阶段不必读全文。"""

    filename: str
    path: Path
    mtime: float
    name: str
    description: str
    type: str


class MemoryStore(Protocol):
    """长期记忆目录与扫描。"""

    def memory_dir(self) -> Path:
        """当前项目的记忆根（已 resolve）。"""
        ...

    def ensure_memory_dir(self) -> None:
        """目录不存在则创建。"""
        ...

    def scan_headers(self) -> list[MemoryHeader]:
        """按 mtime 新到旧返回条目（不含索引文件）。"""
        ...
