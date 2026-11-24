"""每轮注入的 AgentDeps。会话级 ReadFileState 由 App 持有，这里只打包。"""

from __future__ import annotations

from my_code_agent.interfaces.tools import AgentDeps

__all__ = ["AgentDeps"]
