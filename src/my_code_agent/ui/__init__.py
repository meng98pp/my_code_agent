"""终端交互。"""

from .cli import main
from .sink import ConsoleSink

__all__ = ["ConsoleSink", "main"]
