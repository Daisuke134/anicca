from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass
class PageOwnership:
    baseline: set[str]
    receipt_path: Path
    lease_id: str
    fence: int
    created: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.baseline = set(self.baseline)
        if not self.lease_id or self.fence <= 0:
            raise ValueError("page ownership requires a live fenced lease")
        if not all(isinstance(value, str) and value for value in self.baseline):
            raise ValueError("baseline target IDs must be non-empty strings")
        self._write_receipt()

    def register_created(self, target_id: str) -> None:
        if not isinstance(target_id, str) or not target_id:
            raise ValueError("created target ID must be a non-empty string")
        if target_id in self.baseline:
            raise ValueError("baseline target cannot be adopted")
        self.created.add(target_id)
        self._write_receipt()

    def closable(self, current: set[str]) -> list[str]:
        return sorted((self.created & set(current)) - self.baseline)

    async def close_owned(self, session: object, current: set[str]) -> list[str]:
        closed: list[str] = []
        for target_id in self.closable(current):
            result = await session.send("Target.closeTarget", {"targetId": target_id})
            if isinstance(result, dict) and result.get("success") is False:
                continue
            closed.append(target_id)
        return closed

    def _write_receipt(self) -> None:
        value = {
            "version": 1,
            "fence": self.fence,
            "lease_sha256": _digest(self.lease_id),
            "baseline_count": len(self.baseline),
            "baseline_sha256": sorted(_digest(target) for target in self.baseline),
            "created_sha256": sorted(_digest(target) for target in self.created),
        }
        path = Path(self.receipt_path)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
