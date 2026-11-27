"""写路径硬卡口：只允许工作区、配置的数据根、记忆根。resolve 后再比。"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from my_code_agent.interfaces.permissions import PermissionDecision


def writable_roots(
    *,
    workspace: Path | None = None,
    data_home: Path | None = None,
    memory_root: Path | None = None,
) -> list[Path]:
    candidates = [(workspace or Path.cwd()).expanduser()]
    if data_home is not None:
        candidates.append(data_home.expanduser())
    if memory_root is not None:
        candidates.append(memory_root.expanduser())
    roots: list[Path] = []
    seen: set[Path] = set()
    for raw in candidates:
        try:
            resolved = raw.resolve()
        except (OSError, RuntimeError, ValueError):
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        roots.append(resolved)
    return roots


def check_write(
    path: str,
    *,
    roots: Sequence[Path] | None = None,
    workspace: Path | None = None,
    data_home: Path | None = None,
    memory_root: Path | None = None,
) -> PermissionDecision:
    if not (path or "").strip():
        return PermissionDecision("deny", "deny:empty_path", "写入路径为空")
    try:
        resolved = Path(path).expanduser().resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        return PermissionDecision("deny", "deny:unresolvable", f"无法解析路径：{exc}")

    allowed = list(roots) if roots is not None else writable_roots(
        workspace=workspace,
        data_home=data_home,
        memory_root=memory_root,
    )
    for root in allowed:
        try:
            root_resolved = Path(root).expanduser().resolve()
        except (OSError, RuntimeError, ValueError):
            continue
        if _is_within(resolved, root_resolved):
            return PermissionDecision("allow", "allow:writable_root", f"路径位于 {root_resolved} 内")
    return PermissionDecision(
        "deny",
        "deny:outside_workspace",
        f"只允许写入工作区或配置的数据根 / 记忆根，拒绝 {resolved}",
    )


def is_memory_path(path: str, memory_root: Path | None) -> bool:
    """L4 记忆闸门的路径判定；本层只认配置的记忆根，不认用户主目录。"""
    if memory_root is None or not (path or "").strip():
        return False
    try:
        resolved = Path(path).expanduser().resolve()
        root = memory_root.expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return False
    return _is_within(resolved, root)


def _is_within(path: Path, root: Path) -> bool:
    try:
        return path == root or path.is_relative_to(root)
    except (OSError, ValueError):
        return False
