"""权限决策、命令/路径硬卡口、classifier、审计。

决策应为可单测的纯函数；弹窗与 HTTP 走端口。
"""

from .command_policy import evaluate_command

__all__ = ["evaluate_command"]
