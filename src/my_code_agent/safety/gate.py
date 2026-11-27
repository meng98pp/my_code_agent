"""工具执行前的统一关卡。agent hook 只调用这里，不 import ui。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from my_code_agent.interfaces.events import EVENT_PERMISSION, AgentEvent
from my_code_agent.interfaces.permissions import PermissionDecision
from my_code_agent.safety.permissions import (
    AUTO,
    PermissionState,
    compute_decision,
    denial_message,
)


def _as_dict(args: Any) -> dict[str, Any]:
    if isinstance(args, Mapping):
        return dict(args)
    dump = getattr(args, "model_dump", None)
    if callable(dump):
        return dict(dump())
    return {}


async def apply_tool_permission(
    deps: Any,
    messages: Any,
    tool_name: str,
    args: Any,
    handler: Callable[[Any], Awaitable[Any]],
) -> Any:
    """
    工具执行前的统一关卡。
    Args:
        deps: 依赖对象
        messages: 消息
        tool_name: 工具名
        args: 参数
        handler: 处理函数
    Returns:
        Any: 处理结果
    Raises:
        Exception: 处理过程中发生的异常
    """
    args_map = _as_dict(args)
    state: PermissionState = getattr(deps, "permission_state", None) or PermissionState()
    decision = compute_decision(
        tool_name,
        args_map,
        state,
        plan_file=getattr(deps, "plan_file", None),
        roots=list(getattr(deps, "writable_roots", None) or ()),
        self_checks=getattr(deps, "self_checks", None) or {},
        memory_root=getattr(deps, "memory_root", None),
    )
    sink = getattr(deps, "sink", None)

    if decision.action == "deny":
        return denial_message(tool_name, decision)

    if decision.action == "ask" and state.mode == AUTO:
        _emit(sink, f"正在请 LLM 审查 {tool_name}...")
        classify_fn = getattr(deps, "classifier", None)
        if classify_fn is None:
            verdict = {
                "should_block": True,
                "reason": "classifier 未配置，回退人工审批",
                "error": True,
            }
        else:
            verdict = await classify_fn(
                messages or [],
                tool_name,
                args_map,
                settings=getattr(deps, "settings", None),
            )
        if verdict.get("error"):
            _emit(sink, str(verdict.get("reason") or "classifier 出错，回退人工审批"))
        elif not verdict.get("should_block"):
            _emit(sink, f"放行：{verdict.get('reason', '')}")
            return await _execute(
                deps,
                args,
                handler,
                PermissionDecision("allow", "allow:classifier", verdict.get("reason")),
            )
        else:
            _emit(sink, f"拦截：{verdict.get('reason', '')}")
            return (
                f"安全检查拦截了这次 {tool_name} 调用，没有执行。"
                f"拦截理由：{verdict.get('reason', '')}。"
                "不要尝试绕过拦截，请停下来向用户说明情况，由用户决定接下来该怎么做。"
            )

    if decision.action == "ask":
        port = getattr(deps, "approval", None)#getattr(deps, "approval", None)获取deps对象的approval属性，如果属性不存在，则返回None
        if port is None:
            return denial_message(
                tool_name,
                PermissionDecision("deny", "deny:no_approval", "当前没有审批入口，拒绝执行"),
            )
        choice = await port.prompt(tool_name, args_map)
        if choice == "always":
            state.session_allowed.add(tool_name)
        if choice in ("once", "always"):
            return await _execute(
                deps,
                args,
                handler,
                PermissionDecision("allow", f"allow:human_{choice}", None),
            )
        return (
            f"用户拒绝了对 {tool_name} 的调用，这次调用没有执行。"
            "请停下手上的事，等用户告诉你接下来该怎么做。"
        )

    return await _execute(deps, args, handler, decision)


async def _execute(
    deps: Any,
    args: Any,
    handler: Callable[[Any], Awaitable[Any]],
    decision: PermissionDecision,
) -> Any:
    if hasattr(deps, "last_decision_source"):
        deps.last_decision_source = decision.rule or ""
    return await handler(args)


def _emit(sink: Any, text: str) -> None:
    if sink is None or not text:
        return
    sink.emit(AgentEvent(kind=EVENT_PERMISSION, text=text))
