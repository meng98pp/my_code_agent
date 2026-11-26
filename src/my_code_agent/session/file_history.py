"""调用级写文件备份，供 /undo。检查点 /rewind 留到 L5。"""

from __future__ import annotations

import hashlib
import os
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileOperation:
    op_id: str
    tool: str
    path: str
    ts: float
    mode: str
    decision_source: str
    before_hash: str | None
    after_hash: str | None
    backup_name: str | None
    created: bool
    status: str


class FileHistory:
    def __init__(self, session_id: str, root: Path) -> None:
        self.session_id = session_id
        self.dir = Path(root) / "file-history" / session_id
        self.operations: list[FileOperation] = []

    def begin_op(
        self,
        path: str,
        tool: str,
        mode: str = "",
        decision_source: str = "",
    ) -> FileOperation:
        path = os.path.abspath(path)
        existed = os.path.exists(path)
        digest = self._hash_file(path) if existed else None
        op_id = uuid.uuid4().hex[:12]
        backup_name = None
        if existed:
            backup_name = f"op-{op_id}"
            self.dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, self.dir / backup_name)
        op = FileOperation(
            op_id=op_id,
            tool=tool,
            path=path,
            ts=time.time(),
            mode=mode,
            decision_source=decision_source,
            before_hash=digest,
            after_hash=None,
            backup_name=backup_name,
            created=not existed,
            status="prepared",
        )
        self.operations.append(op)
        return op

    def commit_op(self, op: FileOperation) -> None:
        op.after_hash = self._hash_file(op.path)
        op.status = "committed"

    def rollback_op(self, op: FileOperation) -> None:
        if op.status == "rolled_back":
            return
        if op.created or op.backup_name is None:
            if os.path.exists(op.path):
                os.remove(op.path)
        else:
            shutil.copy2(self.dir / op.backup_name, op.path)
        op.status = "rolled_back"

    def rollback_last_op(self) -> FileOperation | None:
        for op in reversed(self.operations):
            if op.status in ("committed", "prepared"):
                self.rollback_op(op)
                return op
        return None

    def _hash_file(self, path: str) -> str | None:
        try:
            return hashlib.sha256(Path(path).read_bytes()).hexdigest()
        except OSError:
            return None
