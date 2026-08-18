#!/usr/bin/env python3
"""buyer_reaction_classify.py -- the model step E2 left open (26-gig-loop §CC'/§EW'
item 4, prerequisite for E4's correlation). ``buyer_outcome_ledger.py`` (E2) appends
every buyer message with ``reaction=null`` on purpose: classifying "does this message
read as satisfied, as a revision request, as a complaint" is judgment, and per
building-agents judgment belongs to a model, never a keyword list. This is that later
step.

Reuses ``predelivery_score.py``'s own machinery rather than re-deriving it: the same
``agent_runner.py`` subprocess boundary, on the same read-only ``diagnostic-agent`` task
class -- a classifier that can write is a classifier that can start replying to the
buyer it was asked to grade.

Batch and bounded (``--limit``, default 20 per run): only rows with ``reaction is None``
are candidates, so an outage classifies nothing and a later run picks up exactly where
this one left off -- the null itself is the queue, no separate cursor file needed.
Model failure on a given row leaves that row's ``reaction`` untouched (fail-open, the
same asymmetry ``predelivery_score.py`` documents: an unreachable classifier has an
opinion about nothing, and a scoring-provider outage must not read as "no reaction" any
more than it should read as "bad reaction").

Rewrite is idempotent and atomic, mirroring ``normalize_applied.py``'s own tmp+rename
discipline: every row is read, at most ``--limit`` null rows are classified, and the
WHOLE file is rewritten in one pass to a temp file that is fsync'd and ``os.replace()``'d
over the original. A row this run does not touch is re-serialized unchanged, and an
unparsable line is kept verbatim rather than dropped -- the row count in must equal the
row count out, always.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from artifact_judge import DEFAULT_RUNNER  # noqa: E402

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
SCHEMA_PATH = SKILL_ROOT / "schemas" / "buyer_reaction.schema.json"

TASK_CLASS = "diagnostic-agent"  # read-only: see module docstring
TASK_LABEL = "gig-BUYER-REACTION-CLASSIFY"

RUNNER_GRACE_SECONDS = 30
DEFAULT_LIMIT = 20

REACTIONS = ("positive", "revision_request", "negative", "neutral", "unclear")


def build_prompt(text: str, attachments_count: int) -> str:
    return f"""あなたは、ココナラの取引ルームで買い手（発注者）が送ったメッセージを分類する採点者です。
このメッセージが、成果物を受け取った買い手の反応として、次のどれに最も近いかを1つ選んでください。

- positive: 満足している・受け入れている（例:「ありがとうございます」「思った通りです」）
- revision_request: 修正・変更を求めている
- negative: 不満・クレーム
- neutral: 感情的な色のない事務連絡（進捗確認、日程の相談など）
- unclear: 上記のどれとも判断できない

--- 買い手のメッセージ（添付ファイル数: {attachments_count}） ---
{text}
--- ここまで ---

スキーマに一致する JSON だけを返してください。reaction は上記5つの値のうちどれか1つです。
"""


def parse_reaction(payload: Any) -> str | None:
    """The reaction string, or ``None`` when the answer cannot be trusted.

    ★ Fails toward ``None``, not toward a guess. ★ Same shape as
    ``predelivery_score.parse_score``: anything outside the fixed enum is treated
    exactly like a classifier that could not be reached.
    """
    if not isinstance(payload, dict):
        return None
    reaction = payload.get("reaction")
    return reaction if reaction in REACTIONS else None


def _read_runner_result(evidence_dir: Path) -> str | None:
    try:
        summary = json.loads((evidence_dir / "summary.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(summary, dict) or summary.get("status") != "success":
        return None
    result_path = summary.get("result_path")
    if not isinstance(result_path, str) or not result_path:
        return None
    try:
        payload = json.loads(Path(result_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return parse_reaction(payload)


def classify_via_runner(
    text: str,
    attachments_count: int,
    *,
    runner: str | Path | None = None,
    schema: str | Path | None = None,
    evidence_dir: str | Path,
    timeout_seconds: int = 180,
) -> str | None:
    """Ask a separate read-only session for the reaction. Never raises; ``None`` on any doubt."""
    runner_path = Path(
        str(runner or os.environ.get("GIG_BUYER_REACTION_RUNNER") or DEFAULT_RUNNER)
    ).expanduser()
    schema_path = Path(str(schema or SCHEMA_PATH)).expanduser()
    evidence = Path(evidence_dir).expanduser()

    if not runner_path.is_file() or not schema_path.is_file():
        return None

    prompt = build_prompt(text, attachments_count)
    try:
        evidence.mkdir(parents=True, exist_ok=True)
        prompt_path = evidence / "buyer-reaction.prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
    except OSError:
        return None

    with tempfile.TemporaryDirectory(prefix="gig-buyer-reaction-") as neutral_workdir:
        command = [
            sys.executable, str(runner_path),
            "--task-class", TASK_CLASS,
            "--prompt-file", str(prompt_path),
            "--schema", str(schema_path),
            "--evidence-dir", str(evidence),
            "--task-label", TASK_LABEL,
            "--loop", "gig",
            "--workdir", neutral_workdir,
            "--timeout-seconds", str(int(timeout_seconds)),
        ]
        try:
            subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds + RUNNER_GRACE_SECONDS,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError, ValueError):
            return None
    return _read_runner_result(evidence)


Classifier = Callable[..., "str | None"]


def default_classifier(text: str, attachments_count: int) -> str | None:
    evidence_dir = (
        Path(
            os.environ.get("GIG_BUYER_REACTION_STATE")
            or (Path.home() / ".local" / "state" / "anicca" / "gig" / "buyer-reaction")
        ).expanduser() / uuid.uuid4().hex
    )
    return classify_via_runner(text, attachments_count, evidence_dir=evidence_dir)


def classify_batch(
    ledger_path: str | Path,
    *,
    classifier: Classifier | None = None,
    limit: int = DEFAULT_LIMIT,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Fill ``reaction`` on up to ``limit`` null rows. Idempotent, never drops a row.

    ``dry_run=True`` classifies nothing and only reports how many rows WOULD be
    attempted -- read-only verification without spending a single model call.
    """
    classifier = classifier or default_classifier
    ledger = Path(ledger_path).expanduser()
    summary: dict[str, Any] = {
        "ledger": str(ledger), "total_rows": 0, "unclassified_before": 0,
        "attempted": 0, "classified": 0, "failed": 0, "dry_run": dry_run,
    }
    if not ledger.is_file():
        return summary

    parsed: list[Any] = []  # dict for a well-formed row, the raw string for anything else
    for line in ledger.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            parsed.append(line)  # kept verbatim -- a torn line must never be dropped

    summary["total_rows"] = len(parsed)
    candidates = [
        i for i, row in enumerate(parsed)
        if isinstance(row, dict) and row.get("reaction") is None and row.get("text")
    ]
    summary["unclassified_before"] = len(candidates)

    attempt_indices = candidates[:limit]
    summary["attempted"] = len(attempt_indices)  # the batch this run WOULD/DOES process

    if dry_run or not candidates:
        return summary

    changed = False
    for i in attempt_indices:
        row = parsed[i]
        try:
            reaction = classifier(str(row.get("text") or ""), int(row.get("attachments_count") or 0))
        except Exception:  # noqa: BLE001 -- a classifier that crashes has classified nothing
            reaction = None
        if reaction in REACTIONS:
            parsed[i] = {**row, "reaction": reaction}
            summary["classified"] += 1
            changed = True
        else:
            summary["failed"] += 1

    if not changed:
        return summary

    tmp = ledger.with_suffix(f".{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for row in parsed:
            if isinstance(row, dict):
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            else:
                handle.write(row + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, ledger)
    return summary


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    default_root = Path(os.environ.get("GIG_STATE_DIR", str(Path.home() / "gig")))
    parser.add_argument("--ledger", type=Path, default=default_root / "buyer-outcomes.jsonl")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    summary = classify_batch(args.ledger, limit=args.limit, dry_run=args.dry_run)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
