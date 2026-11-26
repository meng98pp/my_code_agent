"""read_file / edit_file / write_file。图片多模态留到 L6。"""

from __future__ import annotations

import os
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.exceptions import ModelRetry

from my_code_agent.interfaces.tools import ToolSpec

from .file_state import ReadFileState
from .registry import ToolRegistry

DEFAULT_MAX_LINES = 2000
SKIP_UNCHANGED = "文件内容没有变化，请参考上次 read_file 的结果，不必重复读取"


def _with_line_numbers(content: str, start_line: int = 1) -> str:
    lines = content.splitlines()
    if not lines:
        return "(空文件)"
    width = len(str(start_line + len(lines) - 1))
    return "\n".join(f"{i:>{width}}\t{line}" for i, line in enumerate(lines, start_line))


def read_and_register(
    state: ReadFileState,
    path: str,
    offset: int = 1,
    limit: int | None = None,
) -> str:
    """读文本、按 offset/limit 切片并登记。@ 引用（L6）与 read_file 共用。"""
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    all_lines = raw.splitlines()
    total = len(all_lines)
    start = max(offset, 1) - 1
    if start >= total and total > 0:
        return f"警告：文件只有 {total} 行，但 offset 是 {offset}，没有内容可读"
    span = limit if limit is not None else DEFAULT_MAX_LINES
    end = start + span
    selected = all_lines[start:end]
    selected_content = "\n".join(selected)
    state.record(path, selected_content, offset=offset, limit=limit)
    text = _with_line_numbers(selected_content, start_line=offset)
    if limit is None and end < total:
        text += f"\n\n（文件共 {total} 行，还有 {total - end} 行未显示。用 offset={end + 1} 继续读取）"
    return text


def read_text_file(
    state: ReadFileState,
    path: str,
    offset: int = 1,
    limit: int | None = None,
) -> str:
    """read_file 的纯逻辑：去重、读盘、把常见错误变成 ModelRetry / 错误串。"""
    if os.path.isdir(path):
        raise ModelRetry(f"{path} 是一个目录，请指定目录下的具体文件")
    record = state.get(path)
    if record is not None and record.get("offset") is not None:
        if record["offset"] == offset and record["limit"] == limit:
            try:
                if os.path.getmtime(path) <= record["timestamp"]:
                    return SKIP_UNCHANGED
            except FileNotFoundError:
                pass
    try:
        return read_and_register(state, path, offset, limit)
    except FileNotFoundError as exc:
        raise ModelRetry(f"文件 {path} 不存在，请确认路径或换一个文件") from exc
    except PermissionError as exc:
        raise ModelRetry(f"没有权限读取 {path}，请换一个可读的文件") from exc
    except IsADirectoryError as exc:
        raise ModelRetry(f"{path} 是一个目录，请指定目录下的具体文件") from exc
    except UnicodeDecodeError:
        return f"错误：{path} 不是文本文件，无法读取"
    except OSError as exc:
        return f"错误：无法读取 {path}：{exc}"


def read_file(
    ctx: RunContext[Any],
    path: str,
    offset: int = 1,
    limit: int | None = None,
) -> str:
    """读取文件内容，输出带行号（类似 cat -n）。

    大文件用 offset 和 limit 分段读取。当前层不能看图片；二进制会返回错误说明。
    之后若出现 edit_file，传入的原文不要包含这里的行号前缀。

    Args:
        path: 要读取的文件路径（建议绝对路径）
        offset: 从第几行开始读，从 1 算起（默认 1）
        limit: 读多少行；不传则最多读 2000 行
    """
    return read_text_file(ctx.deps.read_file_state, path, offset, limit)


def _require_fresh_read(state: ReadFileState, path: str, *, overwrite: bool = False) -> dict[str, Any]:
    record = state.get(path)
    if record is None:
        if overwrite:
            raise ModelRetry(f"{path} 已存在，覆盖前请先用 read_file 读一遍，确认不会误删内容")
        raise ModelRetry(f"还没读过 {path}，请先用 read_file 读取它，再基于真实内容编辑")
    try:
        current_mtime = os.path.getmtime(path)
    except FileNotFoundError as exc:
        raise ModelRetry(f"{path} 已不存在，无法写入") from exc
    if current_mtime > record["timestamp"]:
        raise ModelRetry(f"{path} 在你读取之后被改动过，请重新 read_file 再写入")
    return dict(record)


def _commit_write(ctx: RunContext[Any], path: str, content: str, tool: str) -> None:
    history = getattr(ctx.deps, "file_history", None)
    op = None
    if history is not None:
        op = history.begin_op(
            path,
            tool,
            decision_source=str(getattr(ctx.deps, "last_decision_source", "") or ""),
        )
        ctx.deps.last_op_id = op.op_id
    try:
        parent = os.path.dirname(os.path.abspath(path))
        if parent and not os.path.isdir(parent):
            raise FileNotFoundError(parent)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        with open(path, encoding="utf-8") as fh:
            written = fh.read()
        if written != content:
            raise OSError("写入后读回内容不一致")
    except Exception:
        if history is not None and op is not None:
            history.rollback_op(op)
        raise
    if history is not None and op is not None:
        history.commit_op(op)


def edit_file(
    ctx: RunContext[Any],
    path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> str:
    """在文件里精确替换一段字符串，只传改动片段。

    编辑前必须先 read_file。old_string / new_string 不要包含 read_file 的行号前缀。
    多处匹配时补上下文使其唯一，或传 replace_all=true。

    Args:
        path: 要编辑的文件路径
        old_string: 要被替换的原文，必须与文件内容逐字符一致（不含行号）
        new_string: 替换后的内容
        replace_all: 是否替换全部匹配，默认只替换唯一一处
    """
    if old_string == new_string:
        raise ModelRetry("old_string 和 new_string 完全相同，这次编辑没有任何改动")
    state: ReadFileState = ctx.deps.read_file_state
    record = _require_fresh_read(state, path)
    snapshot = str(record.get("content") or "")
    count = snapshot.count(old_string)
    if count == 0:
        raise ModelRetry("old_string 在文件里找不到，请对照 read_file 的输出确认原文")
    if count > 1 and not replace_all:
        raise ModelRetry(
            f"old_string 在文件里出现了 {count} 次，请补充上下文让它唯一，或传 replace_all=true 全部替换"
        )
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    updated = content.replace(old_string, new_string) if replace_all else content.replace(old_string, new_string, 1)
    _commit_write(ctx, path, updated, "edit_file")
    state.record(path, updated)
    n = count if replace_all else 1
    return f"已编辑 {path}（替换 {n} 处）"


def write_file(ctx: RunContext[Any], path: str, content: str) -> str:
    """把内容整文件写入。已有文件会被覆盖。

    覆盖已有文件前必须先 read_file。改局部请用 edit_file；本工具用于新建或整体重写。

    Args:
        path: 要写入的文件路径
        content: 写入后的完整文件内容
    """
    state: ReadFileState = ctx.deps.read_file_state
    if os.path.exists(path):
        _require_fresh_read(state, path, overwrite=True)
    try:
        _commit_write(ctx, path, content, "write_file")
    except FileNotFoundError as exc:
        raise ModelRetry(f"目录不存在，无法写入 {path}，请换一个已存在的目录") from exc
    except PermissionError as exc:
        raise ModelRetry(f"没有权限写入 {path}，请换一个可写的路径") from exc
    except OSError as exc:
        return f"错误：写入 {path} 失败 ({exc})"
    state.record(path, content)
    return f"已写入 {path}"


def register(registry: ToolRegistry) -> None:
    registry.add(
        ToolSpec(
            name="read_file",
            handler=read_file,
            readonly=True,
            description="读取文件内容，输出带行号。",
        )
    )
    # sequential：同一轮多个写操作必须串行，避免基于同一份旧快照互盖
    registry.add(
        ToolSpec(
            name="edit_file",
            handler=edit_file,
            sequential=True,
            description="按字符串片段编辑文件。",
        )
    )
    registry.add(
        ToolSpec(
            name="write_file",
            handler=write_file,
            sequential=True,
            description="整文件写入。",
        )
    )
