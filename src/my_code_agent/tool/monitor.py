"""monitor：把命令的非空输出行当作运行期事件。完成通知接线留到 L6。"""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.exceptions import ModelRetry

from my_code_agent.interfaces.tools import ToolSpec
from my_code_agent.safety.command_policy import evaluate_command

from .registry import ToolRegistry
from .shell import run_command_self_check


async def monitor(
    ctx: RunContext[Any],
    command: str,
    description: str,
    timeout: int = 300,
    persistent: bool = False,
) -> str:
    """启动后台 monitor：非空输出行稍后以 <monitor-event> 送达。不要轮询等待。

    只需一次「完成」通知时，优先用 run_command(run_in_background=True)。
    每次发生都要知道才用本工具。

    Args:
        command: 要监控的 shell 命令
        description: 几个词说明在监控什么
        timeout: 多少秒后停掉
        persistent: 忽略 timeout，跑到会话结束
    """
    if timeout <= 0:
        raise ModelRetry("timeout 必须是正整数")
    verdict = evaluate_command(command)
    if verdict.action == "deny":
        return f"拒绝执行：{verdict.reason}"
    jobs = ctx.deps.job_registry
    if jobs is None:
        raise ModelRetry("当前会话没有 job 注册表，无法启动 monitor")
    job = await jobs.spawn_monitor(command, description, None if persistent else float(timeout))
    return (
        f"monitor 已启动，job id: {job.id}\n"
        f"输出日志：{job.log_path}（随时可用 read_file 查看已记录输出）\n"
        "非空输出行会通过 <monitor-event> 通知送达。不要原地等待；用 job_kill 可以随时停掉它。"
    )


def register(registry: ToolRegistry) -> None:
    registry.add(
        ToolSpec(
            name="monitor",
            handler=monitor,
            self_check=run_command_self_check,
            description="监控命令输出事件流。",
        )
    )
