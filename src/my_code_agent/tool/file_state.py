"""会话内「读过哪些文件」的登记。edit/write 在 L3b 才开始强制先读后改。"""

from __future__ import annotations

import os
from typing import Any


class ReadFileState:
    def __init__(self) -> None:
        self._state: dict[str, dict[str, Any]] = {}

    def record(
        self,
        path: str,
        content: str,
        offset: int | None = None,
        limit: int | None = None,
    ) -> None:
        key = os.path.abspath(path)
        self._state[key] = {
            "content": content,
            "timestamp": os.path.getmtime(key),
            "offset": offset,
            "limit": limit,
        }

    def forget(self, path: str) -> None:
        self._state.pop(os.path.abspath(path), None)

    def get(self, path: str) -> dict[str, Any] | None:
        return self._state.get(os.path.abspath(path))

    def paths(self) -> list[str]:
        return list(self._state)

    def stale_paths(self) -> list[str]:
        stale: list[str] = []
        for path, record in self._state.items():
            try:
                if os.path.getmtime(path) > record["timestamp"]:
                    stale.append(path)
            except OSError:
                continue
        return stale
