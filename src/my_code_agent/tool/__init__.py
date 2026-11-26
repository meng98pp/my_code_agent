"""工具实现与注册表、Skill 加载、MCP。

不 import agent 单例；通过 ToolContext 协议取会话状态。
"""

from .bootstrap import bootstrap_tools
from .file import edit_file, read_and_register, read_file, write_file
from .file_state import ReadFileState
from .registry import ToolRegistry

__all__ = [
    "ReadFileState",
    "ToolRegistry",
    "bootstrap_tools",
    "edit_file",
    "read_and_register",
    "read_file",
    "write_file",
]
