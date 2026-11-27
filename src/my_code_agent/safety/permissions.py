"""五档权限：纯规则。硬卡口优先于 bypass；弹窗与 HTTP 不在本模块。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from my_code_agent.interfaces.permissions import MODES, PermissionDecision, PermissionMode
from my_code_agent.interfaces.tools import SelfCheck
from my_code_agent.safety.command_policy import evaluate_command
from my_code_agent.safety.path_policy import check_write, is_memory_path

DEFAULT: PermissionMode = "default"
ACCEPT_EDITS: PermissionMode = "acceptEdits"
PLAN: PermissionMode = "plan"
AUTO: PermissionMode = "auto"
BYPASS: PermissionMode = "bypass"

READONLY_TOOLS = {
    "read_file",
    "load_skill",
    "ask_user_question",
    "task_create",
    "task_list",
    "task_get",
    "task_update",
    "job_kill",
    "run_agent",
    "review_code",
    "enter_plan_mode",
    "exit_plan_mode",
}
EDIT_TOOLS = {"write_file", "edit_file"}

MODE_LABELS: dict[PermissionMode, str] = {
    "default": "默认（写文件和命令需确认）",
    "acceptEdits": "自动接受编辑",
    "plan": "规划（只读探索，仅允许写 plan 文件）",
    "auto": "自动审查（ask 交给 classifier）",
    "bypass": "跳过确认（硬卡口仍生效）",
}


@dataclass
class PermissionState:
    """模式跨会话保持；session_allowed 在 /new 时应清空（L5）。"""

    mode: PermissionMode = DEFAULT
    pre_plan_mode: PermissionMode = DEFAULT
    session_allowed: set[str] = field(default_factory=set)

    def set_mode(self, mode: str) -> PermissionMode:
        if mode not in MODES:
            raise ValueError(f"未知权限模式：{mode}")
        typed: PermissionMode = mode  # type: ignore[assignment]
        if typed == PLAN and self.mode != PLAN:
            self.pre_plan_mode = self.mode
        self.mode = typed
        return self.mode

    def cycle_mode(self) -> PermissionMode:
        index = MODES.index(self.mode)
        return self.set_mode(MODES[(index + 1) % len(MODES)])

    def clear_session_allowed(self) -> None:
        self.session_allowed.clear()


def compute_decision(
    tool_name: str,
    args: Mapping[str, Any],
    state: PermissionState,
    *,
    plan_file: Path | None = None,
    roots: list[Path] | None = None,
    self_checks: Mapping[str, SelfCheck] | None = None,
    memory_root: Path | None = None,
) -> PermissionDecision:
    """当前模式下对一次调用给出 allow / ask / deny。硬卡口 deny 永远最先。"""
    mapped = dict(args)
    hard = _hard_policy(tool_name, mapped, roots)
    if hard is not None:
        return hard

    check = (self_checks or {}).get(tool_name)
    verdict = check(mapped) if check else None
    if verdict == "deny":
        return PermissionDecision("deny", "deny:self_check", "工具自检拒绝执行")

    if state.mode == BYPASS:
        return PermissionDecision("allow", "bypass", "bypass 跳过询问（硬卡口仍生效）")

    if state.mode == PLAN:
        if tool_name in EDIT_TOOLS:
            if plan_file and _is_same_file(str(mapped.get("path", "")), plan_file):
                return PermissionDecision("allow", "allow:plan_file", "plan 模式仅允许写 plan 文件")
            return PermissionDecision(
                "deny",
                "deny:plan_mode",
                f"plan 模式除了 plan 文件（{plan_file}）不能修改任何文件",
            )
        if tool_name in READONLY_TOOLS or verdict == "allow":
            return PermissionDecision("allow", "allow:plan_readonly", None)
        return PermissionDecision("ask", "ask:plan", None)

    if verdict == "ask":
        return PermissionDecision("ask", "ask:self_check", "工具自检要求审批")
    if verdict == "allow":
        return PermissionDecision("allow", "allow:self_check", "工具自检确认安全")
    if tool_name in state.session_allowed:
        return PermissionDecision("allow", "allow:session", "本会话已选择不再询问该工具")
    if tool_name in READONLY_TOOLS:
        return PermissionDecision("allow", "allow:readonly_tool", None)
    if tool_name in EDIT_TOOLS and is_memory_path(str(mapped.get("path", "")), memory_root):
        return PermissionDecision("allow", "allow:memory_dir", None)
    if state.mode in (ACCEPT_EDITS, AUTO) and tool_name in EDIT_TOOLS:
        return PermissionDecision("allow", f"allow:{state.mode}_edit", None)
    return PermissionDecision("ask", "ask:default", None)


def denial_message(tool_name: str, decision: PermissionDecision) -> str:
    detail = decision.reason or "策略拒绝"
    rule = f"规则：{decision.rule}。" if decision.rule else ""
    if decision.rule == "deny:plan_mode":
        return (
            f"{detail}，这次 {tool_name} 调用没有执行。"
            "请继续只读地探索，把方案写进 plan 文件。"
        )
    return (
        f"安全策略拒绝了这次 {tool_name} 调用，没有执行。{rule}{detail}。"
        "不要尝试绕过拦截，请换一种安全的方式，或向用户说明。"
    )


def format_call(tool_name: str, args: Mapping[str, Any]) -> str:
    bulky = {"content", "old_string", "new_string"}

    def show(key: str, value: Any) -> str:
        text = " ".join(str(value).split())
        if key in bulky and len(text) > 60:
            return text[:60] + "..."
        return text

    inner = ", ".join(f"{key}={show(key, value)}" for key, value in args.items())
    return f"{tool_name}({inner})"


def _hard_policy(
    tool_name: str,
    args: dict[str, Any],
    roots: list[Path] | None,
) -> PermissionDecision | None:
    if tool_name in ("run_command", "monitor"):
        verdict = evaluate_command(str(args.get("command", "")))
        if verdict.action == "deny":
            return PermissionDecision("deny", verdict.rule, verdict.reason)
        if verdict.action == "allow":
            return PermissionDecision("allow", verdict.rule, verdict.reason)
    if tool_name in EDIT_TOOLS:
        verdict = check_write(str(args.get("path", "")), roots=roots)
        if verdict.action == "deny":
            return PermissionDecision("deny", verdict.rule, verdict.reason)
    return None


def _is_same_file(path: str, target: Path) -> bool:
    if not path:
        return False
    try:
        return Path(path).expanduser().resolve() == target.expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return False
