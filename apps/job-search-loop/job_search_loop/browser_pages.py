from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.request
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


def registered_created_target(
    owner_receipt: dict[str, object],
    ownership_receipt: dict[str, object],
    owned_page: dict[str, object],
) -> str:
    target = owned_page.get("target_id")
    lease_id = owner_receipt.get("lease_id")
    fence = owner_receipt.get("fence")
    digest = _digest(str(target)) if isinstance(target, str) and target else ""
    if (
        ownership_receipt.get("version") != 1
        or not isinstance(lease_id, str)
        or not lease_id
        or owned_page.get("lease_id") != lease_id
        or owned_page.get("fence") != fence
        or ownership_receipt.get("lease_sha256") != _digest(lease_id)
        or ownership_receipt.get("fence") != fence
        or digest not in ownership_receipt.get("created_sha256", [])
        or digest in ownership_receipt.get("baseline_sha256", [])
    ):
        raise ValueError("owned page evidence does not authorize cleanup")
    return target


def cleanup_registered_page(
    *, owner_path: Path, ownership_path: Path, owned_page_path: Path
) -> dict[str, object]:
    if not ownership_path.is_file() or not owned_page_path.is_file():
        return {"status": "not_needed", "closed_count": 0}
    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    ownership = json.loads(ownership_path.read_text(encoding="utf-8"))
    owned_page = json.loads(owned_page_path.read_text(encoding="utf-8"))
    target = registered_created_target(owner, ownership, owned_page)
    endpoint = str(owner.get("endpoint") or "").rstrip("/")
    if endpoint != "http://127.0.0.1:9222":
        raise ValueError("owned page cleanup endpoint is invalid")
    current = json.load(urllib.request.urlopen(f"{endpoint}/json/list", timeout=5))
    if target not in {item.get("id") for item in current if item.get("type") == "page"}:
        return {"status": "already_closed", "closed_count": 0}
    urllib.request.urlopen(f"{endpoint}/json/close/{target}", timeout=5).read()
    for _ in range(20):
        current = json.load(urllib.request.urlopen(f"{endpoint}/json/list", timeout=5))
        if target not in {item.get("id") for item in current}:
            return {"status": "closed", "closed_count": 1}
        time.sleep(0.1)
    raise RuntimeError("owned page did not close")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cleanup", nargs="?")
    parser.add_argument("--owner-receipt", type=Path, required=True)
    parser.add_argument("--ownership-receipt", type=Path, required=True)
    parser.add_argument("--owned-page", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(cleanup_registered_page(
        owner_path=args.owner_receipt,
        ownership_path=args.ownership_receipt,
        owned_page_path=args.owned_page,
    ), sort_keys=True))


if __name__ == "__main__":
    main()
