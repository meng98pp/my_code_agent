"""read_file：带行号分段读取。图片多模态留到 L6。"""

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


def register(registry: ToolRegistry) -> None:
    registry.add(
        ToolSpec(
            name="read_file",
            handler=read_file,
            readonly=True,
            description="读取文件内容，输出带行号。",
        )
    )
