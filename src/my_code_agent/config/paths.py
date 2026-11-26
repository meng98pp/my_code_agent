"""数据根 / 记忆根解析。禁止默认使用 Path.home()。"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from .errors import DataRootOnCDriveError

_SAFE_DIR_CHARS = re.compile(r"[^a-zA-Z0-9]")


def repository_root() -> Path:
    """发行包源码上溯到仓库根：.../src/my_code_agent/config/paths.py → 仓库。"""
    return Path(__file__).resolve().parents[3]


def default_home() -> Path:
    return repository_root() / ".data"


def sanitize_cwd(cwd: Path | None = None) -> str:
    resolved = (cwd or Path.cwd()).resolve()
    return _SAFE_DIR_CHARS.sub("-", str(resolved))


def is_on_c_drive(path: Path) -> bool:
    if os.name != "nt":
        return False
    drive = path.expanduser().resolve().drive
    return drive.upper() == "C:"


def ensure_not_c_drive(path: Path, *, allow_c_drive: bool, label: str) -> None:
    if allow_c_drive or not is_on_c_drive(path):
        return
    raise DataRootOnCDriveError(
        f"{label} 解析为 {path}，位于 C 盘。"
        "请设置 CODE_AGENT_HOME / CODE_AGENT_MEMORY_ROOT 到其他盘，"
        "或仅在测试中设置 CODE_AGENT_ALLOW_C_DRIVE=1。"
    )


@dataclass(frozen=True)
class AppPaths:
    home: Path
    memory_override: Path | None
    allow_c_drive: bool

    def project_dir(self, cwd: Path | None = None) -> Path:
        return self.home / "projects" / sanitize_cwd(cwd)

    def memory_dir(self, cwd: Path | None = None) -> Path:
        key = sanitize_cwd(cwd)
        if self.memory_override is not None:
            return self.memory_override / "projects" / key
        return self.project_dir(cwd) / "memory"

    def file_history_dir(self, session_id: str, cwd: Path | None = None) -> Path:
        return self.project_dir(cwd) / "file-history" / session_id

    def jobs_dir(self, session_id: str) -> Path:
        return self.home / "jobs" / session_id
