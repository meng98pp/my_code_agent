"""子 Agent 任务切片、报告形状与熔断。无 I/O、无 SDK。"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, replace

PARENT_SUMMARY_MAX = 500
ANSWER_MAX = 800
MAX_FOCUS_PATHS = 8
MAX_CONSTRAINTS = 8
MAX_EVIDENCE = 8
DEFAULT_MAX_FILE_BYTES = 200_000
MAX_DISPATCHES_PER_GOAL = 2
CIRCUIT_ERROR_LIMIT = 2
CIRCUIT_IDLE_LIMIT = 2

REQUEST_LIMITS: dict[str, int] = {
    "explore": 15,
    "plan": 20,
    "general": 40,
    "review": 15,
}

REPORT_SCHEMAS: dict[str, str] = {
    "explore": (
        '{"answer":"结论≤800字","evidence":[{"path":"...","lines":"12-40","why":"..."}],'
        '"open_questions":[],"files_read":[]}'
    ),
    "plan": '{"plan":"方案概述","steps":["..."],"key_files":["..."],"risks":["..."]}',
    "general": '{"summary":"做了什么","files_changed":["..."],"notes":"..."}',
    "review": (
        '{"summary":"...","findings":[{"severity":"blocker|major|minor","file":"...",'
        '"title":"...","evidence":"失败方式","fix":"最小修复"}],"test_gaps":["..."]}'
    ),
}

_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


class SubagentCircuitOpen(Exception):
    """连续失败或空转后应停止循环并交回降级报告。"""


@dataclass
class TaskSpec:
    """主 Agent 派给子 Agent 的结构化任务。"""

    goal: str
    agent_type: str
    question: str = ""
    focus_paths: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    parent_summary: str = ""
    max_requests: int = 40
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES

    def normalized(self) -> TaskSpec:
        """空白折叠、截断 background、限制路径/约束条数、夹紧请求上限。"""
        goal = " ".join((self.goal or "").split())
        summary = (self.parent_summary or "").strip()
        if len(summary) > PARENT_SUMMARY_MAX:
            summary = summary[:PARENT_SUMMARY_MAX] + "…"
        paths = [p for p in (self.focus_paths or []) if str(p).strip()][:MAX_FOCUS_PATHS]
        constraints = [c for c in (self.constraints or []) if str(c).strip()][:MAX_CONSTRAINTS]
        cap = REQUEST_LIMITS.get(self.agent_type, REQUEST_LIMITS["general"])
        max_requests = min(self.max_requests or cap, cap)
        return replace(
            self,
            goal=goal,
            question=(self.question or "").strip(),
            parent_summary=summary,
            focus_paths=paths,
            constraints=constraints,
            max_requests=max(1, max_requests),
            max_file_bytes=self.max_file_bytes or DEFAULT_MAX_FILE_BYTES,
        )

    def goal_hash(self) -> str:
        return hashlib.sha256(self.goal.strip().lower().encode("utf-8")).hexdigest()[:16]


@dataclass
class SubagentRuntime:
    """一次子 Agent 跑动的熔断计数器。"""

    spec: TaskSpec
    consecutive_errors: int = 0
    consecutive_idle: int = 0
    files_read: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    last_error: str = ""
    degraded: bool = False
    degrade_reason: str = ""
    bytes_read: int = 0

    def note_tool_success(self, tool_name: str) -> None:
        if self.degraded:
            return
        self.consecutive_errors = 0
        self.steps.append(tool_name)

    def note_error(self, message: str) -> bool:
        """返回是否已经熔断。第二次错误触发 tool_errors。"""
        self.consecutive_errors += 1
        self.last_error = message
        if self.consecutive_errors >= CIRCUIT_ERROR_LIMIT:
            self.trip("tool_errors")
        return self.degraded

    def note_read(self, path: str, nbytes: int) -> bool:
        if path:
            self.files_read.append(path)
        self.bytes_read += max(0, nbytes)
        if self.bytes_read > self.spec.max_file_bytes:
            self.trip("file_budget")
        return self.degraded

    def note_model_turn(self, *, has_tools: bool, text: str) -> bool:
        if self.degraded:
            return True
        if has_tools:
            self.consecutive_idle = 0
            return False
        if extract_json(text) is not None:
            self.consecutive_idle = 0
            return False
        if not (text or "").strip():
            return False
        self.consecutive_idle += 1
        if self.consecutive_idle >= CIRCUIT_IDLE_LIMIT:
            self.trip("idle")
        return self.degraded

    def trip(self, reason: str) -> None:
        self.degraded = True
        self.degrade_reason = reason

    def degraded_report(self) -> dict:
        return {
            "degraded": True,
            "reason": self.degrade_reason or "unknown",
            "goal": self.spec.goal,
            "files_read": list(dict.fromkeys(self.files_read)),
            "steps": self.steps[-20:],
            "last_error": self.last_error,
            "hint": "请主 Agent 接手剩余工作，或用 ask_user_question 询问用户；不要用同一个 goal 立刻再派 sub agent。",
        }


class DispatchLedger:
    """同一会话同一 goal 的派发计数。由 core 持有实例，避免模块级可变全局。"""

    def __init__(self) -> None:
        self._counts: dict[tuple[str, str], int] = {}

    def register(self, session_id: str, spec: TaskSpec) -> int:
        key = (session_id or "", spec.goal_hash())
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    def count(self, session_id: str, spec: TaskSpec) -> int:
        return self._counts.get((session_id or "", spec.goal_hash()), 0)

    def clear(self) -> None:
        self._counts.clear()

    def would_exceed(self, session_id: str, spec: TaskSpec) -> bool:
        return self.count(session_id, spec) >= MAX_DISPATCHES_PER_GOAL


def render_prompt(spec: TaskSpec) -> str:
    schema = REPORT_SCHEMAS.get(spec.agent_type, REPORT_SCHEMAS["general"])
    parts = [f"# 任务\n{spec.goal}"]
    if spec.question:
        parts.append(f"\n# 要回答的问题\n{spec.question}")
    if spec.focus_paths:
        parts.append("\n# 焦点路径（自行 read_file，不要指望正文已贴在这里）")
        parts.extend(f"- {p}" for p in spec.focus_paths)
    if spec.constraints:
        parts.append("\n# 约束")
        parts.extend(f"- {c}" for c in spec.constraints)
    if spec.parent_summary:
        parts.append(f"\n# 调用方背景（已截断）\n{spec.parent_summary}")
    parts.append(
        "\n# 最终报告\n"
        "调用方只能看到你最后一条输出。不要输出过程叙述，最后只输出一个 JSON 对象，形状如下：\n"
        f"{schema}"
    )
    return "\n".join(parts)


def extract_json(text: str) -> dict | None:
    if not text or not text.strip():
        return None
    raw = text.strip()
    fenced = _JSON_FENCE.search(raw)
    if fenced:
        raw = fenced.group(1)
    else:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end <= start:
            return None
        raw = raw[start : end + 1]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def normalize_report(
    agent_type: str,
    data: dict,
    files_read: list[str] | None = None,
) -> dict:
    seen = files_read or []
    if agent_type == "explore":
        answer = str(data.get("answer") or data.get("summary") or "")
        if len(answer) > ANSWER_MAX:
            answer = answer[:ANSWER_MAX] + "…"
        evidence = []
        for item in (data.get("evidence") or [])[:MAX_EVIDENCE]:
            if not isinstance(item, dict):
                continue
            evidence.append(
                {
                    "path": str(item.get("path") or ""),
                    "lines": str(item.get("lines") or ""),
                    "why": str(item.get("why") or "")[:200],
                }
            )
        return {
            "answer": answer,
            "evidence": evidence,
            "open_questions": [str(q) for q in (data.get("open_questions") or [])][:8],
            "files_read": [str(p) for p in (data.get("files_read") or seen)][:20],
        }
    if agent_type == "review":
        findings = []
        for item in (data.get("findings") or [])[:20]:
            if not isinstance(item, dict):
                continue
            severity = str(item.get("severity") or "minor")
            if severity not in ("blocker", "major", "minor"):
                severity = "minor"
            findings.append(
                {
                    "severity": severity,
                    "file": str(item.get("file") or ""),
                    "title": str(item.get("title") or "")[:200],
                    "evidence": str(item.get("evidence") or "")[:400],
                    "fix": str(item.get("fix") or "")[:400],
                }
            )
        return {
            "summary": str(data.get("summary") or "")[:ANSWER_MAX],
            "findings": findings,
            "test_gaps": [str(t) for t in (data.get("test_gaps") or [])][:12],
        }
    if agent_type == "plan":
        return {
            "plan": str(data.get("plan") or "")[:ANSWER_MAX],
            "steps": [str(s) for s in (data.get("steps") or [])][:12],
            "key_files": [str(p) for p in (data.get("key_files") or [])][:8],
            "risks": [str(r) for r in (data.get("risks") or [])][:8],
        }
    return {
        "summary": str(data.get("summary") or data.get("answer") or "")[:ANSWER_MAX],
        "files_changed": [str(p) for p in (data.get("files_changed") or [])][:20],
        "notes": str(data.get("notes") or "")[:ANSWER_MAX],
    }


def finalize_output(agent_type: str, raw: str, runtime: SubagentRuntime) -> str:
    if runtime.degraded:
        return json.dumps(runtime.degraded_report(), ensure_ascii=False, indent=2)
    parsed = extract_json(raw or "")
    if parsed is None:
        parsed = {"answer": (raw or "").strip(), "summary": (raw or "").strip()}
    report = normalize_report(agent_type, parsed, runtime.files_read)
    return json.dumps(report, ensure_ascii=False, indent=2)
