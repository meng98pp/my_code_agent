"""会话 jsonl、文件检查点、任务列表持久化。

数据落在 CODE_AGENT_HOME 下，不落在 C 盘用户主目录。
"""

from .file_history import FileHistory, FileOperation

__all__ = ["FileHistory", "FileOperation"]
