"""会话级后台 job：shell / monitor / 预留 agent。日志在 CODE_AGENT_HOME，不写用户主目录。"""

from __future__ import annotations

import asyncio
import os
import random
import signal
import string
import subprocess
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

EVENT_WINDOW = 10.0
MAX_EVENTS_PER_WINDOW = 20
MAX_PENDING_EVENTS = 200
MAX_DROPPED_EVENTS = 100
MAX_EVENT_CHARS = 500

_ID_ALPHABET = string.digits + string.ascii_lowercase

JobStatus = Literal["running", "completed", "failed", "killed"]
JobKind = Literal["shell", "agent", "monitor"]

_STATUS_TEXT = {
    "completed": "执行成功",
    "failed": "执行失败",
    "killed": "已被终止",
}


def _new_job_id(prefix: str) -> str:
    return prefix + "".join(random.choices(_ID_ALPHABET, k=8))


@dataclass
class Job:
    id: str
    kind: JobKind
    description: str
    log_path: Path
    status: JobStatus = "running"
    returncode: int | None = None
    notified: bool = False
    background: bool = True
    kill_func: Callable[[], None] | None = None
    result: str | None = None
    degraded: bool = False
    pending_events: list[str] = field(default_factory=list)
    dropped_events: int = 0
    dropped_total: int = 0
    window_start: float = 0.0
    window_count: int = 0

    def summary(self) -> str:
        detail = _STATUS_TEXT[self.status]
        if self.returncode is not None:
            detail += f"，exit code {self.returncode}"
        noun = "sub agent" if self.kind == "agent" else "后台命令"
        text = f"{noun}「{self.description}」{detail}"
        if self.degraded:
            text += "（已降级）"
        return text

    def push_event(self, line: str) -> None:
        now = time.monotonic()
        if now - self.window_start >= EVENT_WINDOW:
            self.window_start = now
            self.window_count = 0
        self.window_count += 1
        if self.window_count > MAX_EVENTS_PER_WINDOW or len(self.pending_events) >= MAX_PENDING_EVENTS:
            self.dropped_events += 1
            self.dropped_total += 1
            return
        self.pending_events.append(line[:MAX_EVENT_CHARS])


class JobRegistry:
    def __init__(self, session_id: str, root: Path) -> None:
        self.session_id = session_id
        self._jobs: dict[str, Job] = {}
        self._jobs_dir = Path(root) / "jobs" / session_id
        self._watchers: set[asyncio.Task] = set()

    async def spawn_shell(self, command: str, background: bool = True, cwd: str | None = None) -> Job:
        #创建一个后台job，交互式进程
        job_id = _new_job_id("b")
        self._jobs_dir.mkdir(parents=True, exist_ok=True)
        log_path = self._jobs_dir / f"{job_id}.log"
        log_file = open(log_path, "wb")
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=cwd or os.getcwd(),
            **_process_group_kwargs(),
        )#创建一个交互式进程
        pid = proc.pid#获取进程ID
        job = Job(
            id=job_id,
            kind="shell",
            description=command,
            log_path=log_path,
            background=background,
            kill_func=lambda: _kill_process_tree(pid),
        )
        self._jobs[job_id] = job
        watcher = asyncio.create_task(self._watch_shell(job, proc, log_file))#监视进程
        self._watchers.add(watcher)
        watcher.add_done_callback(self._watchers.discard)
        return job

    async def _watch_shell(self, job: Job, proc: asyncio.subprocess.Process, log_file) -> None:
        returncode = await proc.wait()#等待进程结束
        log_file.close()
        if job.status == "killed":
            return
        job.returncode = returncode
        job.status = "completed" if returncode == 0 else "failed"

    async def spawn_agent(self, description: str, run: Callable[[Job], Awaitable[None]]) -> Job:
        job_id = _new_job_id("a")
        self._jobs_dir.mkdir(parents=True, exist_ok=True)
        log_path = self._jobs_dir / f"{job_id}.log"
        log_path.touch()
        job = Job(id=job_id, kind="agent", description=description, log_path=log_path)
        task = asyncio.create_task(run(job))
        job.kill_func = task.cancel
        self._jobs[job_id] = job
        watcher = asyncio.create_task(self._watch_agent(job, task))
        self._watchers.add(watcher)
        watcher.add_done_callback(self._watchers.discard)
        return job

    async def _watch_agent(self, job: Job, task: asyncio.Task) -> None:
        try:
            await task
        except asyncio.CancelledError:
            return
        except Exception as exc:
            job.result = f"sub agent 运行出错：{type(exc).__name__}: {exc}"
            status = "failed"
        else:
            status = "completed"
        if job.status == "running":
            job.status = status

    async def spawn_monitor(self, command: str, description: str, timeout: float | None) -> Job:
        job_id = _new_job_id("m")
        self._jobs_dir.mkdir(parents=True, exist_ok=True)
        log_path = self._jobs_dir / f"{job_id}.log"
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=os.getcwd(),
            limit=1024 * 1024,
            **_process_group_kwargs(),
        )
        pid = proc.pid
        job = Job(
            id=job_id,
            kind="monitor",
            description=description,
            log_path=log_path,
            kill_func=lambda: _kill_process_tree(pid),
        )
        self._jobs[job_id] = job
        watcher = asyncio.create_task(self._pump_monitor(job, proc, timeout))
        self._watchers.add(watcher)
        watcher.add_done_callback(self._watchers.discard)
        return job

    async def _pump_monitor(
        self,
        job: Job,
        proc: asyncio.subprocess.Process,
        timeout: float | None,
    ) -> None:
        timer = asyncio.create_task(self._monitor_timeout(job, timeout)) if timeout is not None else None
        log_file = open(job.log_path, "w", encoding="utf-8", buffering=1)
        try:
            try:
                assert proc.stdout is not None
                async for raw in proc.stdout:
                    line = raw.decode(errors="replace").rstrip("\r\n")
                    log_file.write(line + "\n")
                    if not line:
                        continue
                    job.push_event(line)
                    if job.dropped_total >= MAX_DROPPED_EVENTS:
                        self._stop_monitor(job, "monitor 已停止：输出太多，请用更精确的过滤条件重新挂载")
                        break
            except ValueError:
                self._stop_monitor(job, "monitor 已停止：单行输出过长，请先在命令中截断或过滤")
                await proc.wait()
                return
            returncode = await proc.wait()
            if job.status == "killed":
                return
            job.returncode = returncode
            job.status = "completed" if returncode == 0 else "failed"
            job.notified = True
            job.pending_events.append(f"[monitor 已停止：被监控的命令自己退出了，exit code {returncode}]")
        finally:
            log_file.close()
            if timer:
                timer.cancel()

    async def _monitor_timeout(self, job: Job, timeout: float) -> None:
        await asyncio.sleep(timeout)
        if job.status == "running":
            self._stop_monitor(job, f"monitor 已停止：到了 {int(timeout)} 秒的超时上限，还需要监控就重新挂载")

    def _stop_monitor(self, job: Job, note: str) -> None:
        job.pending_events.append(f"[{note}]")
        self.kill(job.id)

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        return list(self._jobs.values())

    def running(self, background: bool | None = None) -> list[Job]:
        return [
            job
            for job in self._jobs.values()
            if job.status == "running" and (background is None or job.background is background)
        ]

    def move_to_background(self) -> None:
        """把仍在跑的前台命令改成后台。Ctrl+B 键位留到 L6。"""
        for job in self.running(background=False):
            job.background = True

    def kill(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job is None or job.status != "running":
            return False
        job.status = "killed"
        job.notified = True
        if job.kill_func:
            job.kill_func()
        return True

    def pop_unnotified(self) -> list[Job]:
        done = [
            job
            for job in self._jobs.values()
            if job.background and job.status != "running" and not job.notified
        ]
        for job in done:
            job.notified = True
        return done

    def pop_events(self) -> list[tuple[Job, list[str], int]]:
        out: list[tuple[Job, list[str], int]] = []
        for job in self._jobs.values():
            if not job.pending_events and not job.dropped_events:
                continue
            out.append((job, job.pending_events, job.dropped_events))
            job.pending_events = []
            job.dropped_events = 0
        return out

    def shutdown(self) -> int:
        running = self.running()
        for job in running:
            self.kill(job.id)
        return len(running)


def _process_group_kwargs() -> dict:
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _kill_process_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
        return
    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except ProcessLookupError:
        return
