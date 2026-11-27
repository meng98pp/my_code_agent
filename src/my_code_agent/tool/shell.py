"""run_command / job_kill。cwd 钉在工作区；前台默认 10 秒超时。"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Mapping
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.exceptions import ModelRetry

from my_code_agent.interfaces.tools import ToolSpec
from my_code_agent.safety.command_policy import evaluate_command

from .registry import ToolRegistry

FOREGROUND_TIMEOUT = 10


def run_command_self_check(args: Mapping[str, Any]) -> str | None:
    """deny 硬拦；只读 allow；其余 None（交给五档模式 / 会话白名单）。"""
    verdict = evaluate_command(str(args.get("command", "")))
    if verdict.action == "deny":
        return "deny"
    if verdict.action == "allow":
        return "allow"
    return None


def _background_notice(job: Any, lead: str) -> str:
    return (
        f"{lead}\n"
        f"输出日志：{job.log_path}（随时可用 read_file 查看）\n"
        "完成后你会收到 <task-notification> 通知，不要原地等待。"
    )


async def run_command(
    ctx: RunContext[Any],
    command: str,
    run_in_background: bool = False,
) -> str:
    """执行一条 shell 命令。默认前台运行并返回输出。

    长任务用 run_in_background=True：立即返回 job id，命令末尾不必加 &。
    结束后会有通知，不要轮询等待；期间可用 read_file 看日志。

    Args:
        command: 要执行的 shell 命令
        run_in_background: 作为后台 job 运行，不等待结束
    """
    verdict = evaluate_command(command)
    if verdict.action == "deny":
        return f"拒绝执行：{verdict.reason}"
    registry = ctx.deps.job_registry#获取job注册表
    if registry is None:
        raise ModelRetry("当前会话没有 job 注册表，无法执行命令")
    job = await registry.spawn_shell(command, background=run_in_background, cwd=os.getcwd())#创建一个后台job，交互式进程
    if run_in_background:
        return _background_notice(job, f"已放入后台运行，job id: {job.id}")

    start = time.monotonic()
    try:
        while job.status == "running" and not job.background:
            if time.monotonic() - start > FOREGROUND_TIMEOUT:
                registry.kill(job.id)
                return (
                    f"[错误] 命令执行超时（{FOREGROUND_TIMEOUT}秒）；"
                    "长驻或耗时命令请改用 run_in_background=True 重新执行"
                )
            await asyncio.sleep(0.05)
    except asyncio.CancelledError:
        registry.kill(job.id)
        raise

    if job.background:
        return _background_notice(job, f"用户把这条命令转入了后台，它作为 job {job.id} 继续运行")

    output = job.log_path.read_text(errors="replace")
    if job.returncode != 0:
        output += f"\n[错误] exit code {job.returncode}"
    return output or "(无输出)"


async def job_kill(ctx: RunContext[Any], job_id: str) -> str:
    """终止一个正在运行的后台 job（整个进程树）。

    Args:
        job_id: 要终止的 job id
    """
    registry = ctx.deps.job_registry
    if registry is None:
        raise ModelRetry("当前会话没有 job 注册表")
    job = registry.get(job_id)
    if job is None:
        raise ModelRetry(f"job {job_id} 不存在")
    if not registry.kill(job_id):
        return f"job {job_id} 已经结束（{job.status}），无需终止"
    return f"job {job_id} 已终止"


def register(registry: ToolRegistry) -> None:
    registry.add(
        ToolSpec(
            name="run_command",
            handler=run_command,
            self_check=run_command_self_check,
            description="执行 shell 命令。",
        )
    )
    registry.add(
        ToolSpec(
            name="job_kill",
            handler=job_kill,
            readonly=True,
            description="终止后台 job。",
        )
    )
