"""L2 最小 REPL：标准输入。完整 prompt_toolkit 键位留到 L6。"""

from __future__ import annotations

import asyncio
import logging
import sys

from my_code_agent.config import ConfigError, load_settings, require_api_key, resolve_paths
from my_code_agent.core import App

from .sink import ConsoleSink


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    try:
        settings = load_settings()
        require_api_key(settings)
        paths = resolve_paths(settings)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc

    print(f"my_code_agent L2  {settings.model}")
    opts = settings.model_request_options()
    if opts:
        bits = "  ".join(f"{k}={v}" for k, v in opts.items())
        print(f"模型参数：{bits}")
    print(f"数据根：{paths.home}")
    print(f"记忆目录（本层不创建）：{paths.memory_dir()}")
    print("输入 /help 查看命令，/exit 退出。\n")
    try:
        asyncio.run(_loop(settings, paths))
    except KeyboardInterrupt:
        print()


async def _loop(settings, paths) -> None:
    app = App(settings, paths, sink=ConsoleSink())
    while True:
        try:
            line = input("❯ ")
        except EOFError:
            print()
            return
        action = await app.handle_line(line)
        if action == "exit":
            return
