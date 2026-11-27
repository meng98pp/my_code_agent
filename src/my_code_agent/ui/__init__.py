"""终端交互。"""

from .approval import StdinApproval
from .cli import main
from .sink import ConsoleSink

__all__ = ["ConsoleSink", "StdinApproval", "main"]
