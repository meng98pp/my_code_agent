"""显式工具注册表。禁止只靠 import 副作用完成注册。"""

from __future__ import annotations

from typing import Any

from my_code_agent.interfaces.tools import ToolSpec


class ToolRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}

    def add(self, spec: ToolSpec) -> None:
        if spec.name in self._specs:
            raise ValueError(f"工具重复注册：{spec.name}")
        self._specs[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._specs.get(name)

    def names(self) -> list[str]:
        return list(self._specs)

    def specs(self) -> list[ToolSpec]:
        return list(self._specs.values())

    def self_checks(self) -> dict[str, Any]:
        return {spec.name: spec.self_check for spec in self._specs.values() if spec.self_check}

    def as_pydantic_tools(self) -> list[Any]:
        from pydantic_ai import Tool

        return [
            Tool(spec.handler, sequential=spec.sequential, name=spec.name)
            for spec in self._specs.values()
        ]
