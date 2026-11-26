"""命令硬卡口：deny 对 bypass 仍生效；确认只读则 allow；其余 ask。"""

from __future__ import annotations

import re
import shlex

from my_code_agent.interfaces.permissions import PermissionDecision

SHELL_META = re.compile(r"[;&|<>`$\n]")

READONLY_COMMANDS = {
    "ls",
    "cat",
    "head",
    "tail",
    "grep",
    "egrep",
    "fgrep",
    "wc",
    "pwd",
    "find",
    "rg",
    "dir",
    "type",
    "where",
    "which",
    "echo",
    "git",
}

_GIT_READONLY = {"status", "diff", "log", "show", "rev-parse", "branch"}

_DENY_RULES: list[tuple[str, re.Pattern[str], str]] = [
    ("sudo", re.compile(r"\bsudo\b", re.I), "禁止提权命令 sudo"),
    ("runas", re.compile(r"\brunas\b", re.I), "禁止 Windows 提权 runas"),
    (
        "runas_verb",
        re.compile(r"Start-Process[\s\S]{0,120}-Verb\s+RunAs", re.I),
        "禁止 Start-Process -Verb RunAs",
    ),
    ("iex", re.compile(r"\b(Invoke-Expression|iex)\b", re.I), "禁止 PowerShell 动态执行"),
    (
        "curl_pipe",
        re.compile(
            r"(curl|wget|iwr|Invoke-WebRequest)[\s\S]{0,400}\|\s*(bash|sh|zsh|cmd|iex|Invoke-Expression)",
            re.I,
        ),
        "禁止把下载内容直接交给解释器",
    ),
    ("mkfs", re.compile(r"\bmkfs\w*\b", re.I), "禁止格式化文件系统"),
    ("format_disk", re.compile(r"\bformat\s+[A-Za-z]:", re.I), "禁止 format 磁盘"),
    ("dd", re.compile(r"(?:^|[\s;&|])dd(?:\s|$)", re.I), "禁止 dd 直写磁盘"),
    (
        "shell_delete",
        re.compile(r"(?:^|[\s;&|(])(?:del|erase|rmdir|rd|rm|Remove-Item)\b", re.I),
        "禁止通过 Shell 删除文件或目录",
    ),
    (
        "sys_write",
        re.compile(
            r"(?:>>?|Out-File|Set-Content|Tee-Object)[\s\S]{0,120}(?:C:\\Windows|/etc\b|/usr/)",
            re.I,
        ),
        "禁止写入系统目录",
    ),
    (
        "secret_exfil",
        re.compile(r"(curl|wget|iwr|Invoke-WebRequest)[\s\S]{0,500}(API_KEY|\.env\b)", re.I),
        "禁止把密钥或环境文件经网络发送",
    ),
    ("chmod_777", re.compile(r"\bchmod\s+(?:-R\s+)?0?777\b", re.I), "禁止 chmod 777"),
]


def evaluate_command(command: str) -> PermissionDecision:
    text = command or ""
    for name, pattern, reason in _DENY_RULES:
        if pattern.search(text):
            return PermissionDecision("deny", f"deny:{name}", reason)
    if _is_readonly(text):
        return PermissionDecision("allow", "allow:readonly", "确认只读、无 shell 元字符")
    return PermissionDecision("ask", "ask:default", "无法确认为只读，需要按权限模式继续判定")


def _is_readonly(command: str) -> bool:
    if SHELL_META.search(command):
        return False
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return False
    if not tokens:
        return False
    head = tokens[0].rsplit("\\", 1)[-1].rsplit("/", 1)[-1].lower()
    if head in {"git", "git.exe"}:
        return len(tokens) >= 2 and tokens[1].lstrip("-") in _GIT_READONLY
    if _is_pytest_collect_only(tokens, head):
        return True
    return head in READONLY_COMMANDS and head != "git"


def _is_pytest_collect_only(tokens: list[str], head: str) -> bool:
    if "--collect-only" not in tokens:
        return False
    if head in {"pytest", "pytest.exe"}:
        return True
    if head in {"python", "python3", "python.exe", "py", "py.exe"}:
        return "-m" in tokens and "pytest" in tokens
    return False
