"""显式装配内置工具。core 只调用这里，不散落 import 各工具模块。"""

from __future__ import annotations

from . import file as file_tools
from . import monitor as monitor_tools
from . import shell as shell_tools
from .registry import ToolRegistry


def bootstrap_tools() -> ToolRegistry:
    registry = ToolRegistry()
    file_tools.register(registry)
    shell_tools.register(registry)
    monitor_tools.register(registry)
    return registry
