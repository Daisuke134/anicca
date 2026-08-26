from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


AnswerKind = Literal["exact", "derived", "generated", "conservative"]


def _normalize_question(value: str) -> str:
    return re.sub(r"[^\w]+", " ", value.casefold(), flags=re.UNICODE).strip()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _atomic_private(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_canonical(value) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@dataclass(frozen=True, slots=True)
class AnswerRecordV1:
    concept: str
    revision: int
    kind: AnswerKind
    answer: Any
    provenance: tuple[str, ...]
    created_at: str


class AnswerMemory:
    def __init__(self, path: Path) -> None:
        self._path = path

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"schema_version": 1, "aliases": {}, "records": {}}
        value = json.loads(self._path.read_text(encoding="utf-8"))
        if value.get("schema_version") != 1:
            raise ValueError("unsupported Answer Memory schema")
        if not isinstance(value.get("aliases"), dict) or not isinstance(value.get("records"), dict):
            raise ValueError("invalid Answer Memory")
        return value

    def lookup(self, concept: str) -> AnswerRecordV1 | None:
        revisions = self._load()["records"].get(concept, [])
        if not revisions:
            return None
        value = revisions[-1]
        return AnswerRecordV1(
            concept, value["revision"], value["kind"], value["answer"],
            tuple(value["provenance"]), value["created_at"],
        )

    def concept_for_question(self, question: str) -> str | None:
        normalized = _normalize_question(question)
        return self._load()["aliases"].get(normalized)

    def remember(
        self,
        *,
        concept: str,
        answer: Any,
        kind: AnswerKind,
        provenance: tuple[str, ...],
        question_variants: tuple[str, ...],
    ) -> dict[str, Any]:
        if not concept.strip() or kind not in {"exact", "derived", "generated", "conservative"}:
            raise ValueError("invalid semantic answer")
        if answer is None or not provenance or not question_variants:
            raise ValueError("answer, provenance, and question variants are required")
        value = self._load()
        aliases = value["aliases"]
        normalized_variants = {_normalize_question(item) for item in question_variants}
        if "" in normalized_variants:
            raise ValueError("question variant is empty")
        for variant in normalized_variants:
            existing = aliases.get(variant)
            if existing is not None and existing != concept:
                raise RuntimeError("question alias is already bound to another concept")
        revisions = value["records"].setdefault(concept, [])
        comparable = {"answer": answer, "kind": kind, "provenance": list(provenance)}
        changed = not revisions or any(revisions[-1].get(key) != item for key, item in comparable.items())
        if changed:
            revisions.append(
                {
                    "revision": len(revisions) + 1,
                    **comparable,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        for variant in normalized_variants:
            aliases[variant] = concept
        _atomic_private(self._path, value)
        current = revisions[-1]
        answer_sha = hashlib.sha256(_canonical(current["answer"])).hexdigest()
        return {
            "schema_version": 1,
            "concept_sha256": hashlib.sha256(concept.encode()).hexdigest(),
            "revision": current["revision"],
            "answer_sha256": answer_sha,
            "changed": changed,
        }
