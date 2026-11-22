#!/usr/bin/env python3
"""Review-only Japanese text repetition audit. NOT a humor or originality score."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import unicodedata
from pathlib import Path


def canonical(text: str) -> str:
    """Unicode NFKC; drop whitespace and punctuation, keep Japanese characters."""
    return "".join(c for c in unicodedata.normalize("NFKC", text)
                   if not c.isspace() and not unicodedata.category(c).startswith(("P", "S")))


def shingles(text: str, size: int = 3) -> set[str]:
    normalized = canonical(text)
    if not normalized:
        return set()
    if len(normalized) < size:
        return {normalized}
    return {normalized[i:i + size] for i in range(len(normalized) - size + 1)}


def similarity(a: str, b: str) -> float:
    x, y = shingles(a), shingles(b)
    if not x or not y:
        return 0.0
    return len(x & y) / len(x | y)


def load(path: Path) -> list[dict]:
    records = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON") from exc
        if not isinstance(row, dict) or not isinstance(row.get("response"), str):
            raise ValueError(f"{path}:{line_no}: response must be a string")
        if not row["response"].strip():
            raise ValueError(f"{path}:{line_no}: empty response; silence tasks are excluded")
        records.append(row)
    return records


def reference(row: dict, source: str, index: int) -> dict:
    return {"file": source, "line": index + 1,
            "task_id": row.get("task_id"), "sample_index": row.get("sample_index"),
            "model": row.get("model")}


def audit(current_path: Path, history_paths: list[Path], threshold: float = 0.70) -> dict:
    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("threshold must be finite and between zero and one")
    current = load(current_path)
    if not current:
        raise ValueError("current response file is empty")
    history = [(p, load(p)) for p in history_paths]
    if any(p.resolve() == current_path.resolve() for p in history_paths):
        raise ValueError("current file cannot also be history")
    flags = []
    highest = 0.0
    for i, row in enumerate(current):
        for j in range(i):
            score = similarity(row["response"], current[j]["response"])
            highest = max(highest, score)
            if score >= threshold:
                flags.append({"kind": "within_run", "similarity": round(score, 6),
                              "current": reference(row, str(current_path), i),
                              "match": reference(current[j], str(current_path), j)})
        for p, rows in history:
            for j, old in enumerate(rows):
                score = similarity(row["response"], old["response"])
                highest = max(highest, score)
                if score >= threshold:
                    flags.append({"kind": "historical", "similarity": round(score, 6),
                                  "current": reference(row, str(current_path), i),
                                  "match": reference(old, str(p), j)})
    return {
        "schema_version": "1.0",
        "method": "NFKC punctuation-insensitive character-3gram Jaccard",
        "threshold": threshold, "current_response_count": len(current),
        "history_response_count": sum(len(rows) for _, rows in history),
        "history_files": [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                          for p, _ in history],
        "current_sha256": hashlib.sha256(current_path.read_bytes()).hexdigest(),
        "highest_pair_similarity": round(highest, 6),
        "within_run_flags": sum(f["kind"] == "within_run" for f in flags),
        "historical_flags": sum(f["kind"] == "historical" for f in flags),
        "review_flags": flags,
        "humor_quality": "NOT_MEASURED", "semantic_originality": "NOT_MEASURED",
        "voice_reproducibility": "NOT_MEASURED",
        "warning": "Similarity is only an editorial review flag. Shared names are allowed; semantic rephrasing may be missed. Zero flags is NOT proof of originality or comedy quality."
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--history", type=Path, action="append", default=[])
    parser.add_argument("--threshold", type=float, default=0.70)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit(args.current, args.history, args.threshold)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")
    print(f"REVIEW_ONLY current={report['current_response_count']} history={report['history_response_count']} within={report['within_run_flags']} historical={report['historical_flags']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
