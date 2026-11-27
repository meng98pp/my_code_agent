"""挂在 Agent 上的权限关卡。不 import ui。"""

from __future__ import annotations

from pydantic_ai.capabilities import Hooks

from my_code_agent.safety.gate import apply_tool_permission


def permission_hooks() -> Hooks:
    hooks = Hooks()

    @hooks.on.tool_execute
    async def _check_permission(ctx, *, call, tool_def, args, handler):
        """
        ctx:这一轮 RunContext，里面有 deps、messages
        call: 模型发出的这次 tool call（含 tool_name）
        tool_def: 工具 schema，关卡没用
        args: 已校验的参数
        handler: 下一层执行函数，不是 run_command 本身
        """
        return await apply_tool_permission(
            ctx.deps,
            getattr(ctx, "messages", None),
            call.tool_name,
            args,
            handler,
        )

    @hooks.on.tool_execute_error
    async def _handle_tool_error(ctx, *, call, tool_def, args, error):
        return f"工具执行出错：{type(error).__name__}: {error}"

    return hooks
