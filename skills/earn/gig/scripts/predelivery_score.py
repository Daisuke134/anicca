#!/usr/bin/env python3
"""Score a deliverable against the buyer's own requirements, before it ships.

★ Not a second judge. ★ ``artifact_judge.refuse_unless_deliverable`` already asks one
binary question -- "is this the thing the buyer bought, at all" -- immediately before the
send, and this module runs right after it, on the same artifact, for the same order. That
question stays a yes/no on purpose (31-gig-todo10 §2.2 "still one question, asked once").
This one is different in kind: it produces a number, so a later pass (E4, 26-gig-loop §CC'
段E) can correlate the score against what the buyer actually says once they have the
artifact in hand (E2's buyer-outcomes ledger). A score is not a gate design in itself --
it becomes one only with a conservative floor, and only until E4 has real correlation data
to calibrate it against.

Reuses ``artifact_judge``'s own machinery rather than re-deriving it: ``order_identity_text``
for what the buyer asked for, ``artifact_body`` for what the artifact contains (including the
OOXML text extraction and the elision rules), and the same ``agent_runner.py`` subprocess
boundary on the same read-only ``diagnostic-agent`` task class. Judgment -- what a good score
looks like on this specific order -- is the model's; this file only orchestrates the call,
parses the answer, enforces the floor, and writes it down.

★ Fails OPEN on a scoring outage. ★ This is the opposite direction from
``artifact_judge``, and deliberately so. The binary judge exists to stop a wrong artifact from
ever reaching a buyer, so an unreachable judge must not wave one through. A *quality* score
is calibration, not a correctness gate -- an unreachable scorer has an opinion about nothing,
and treating "I could not score this" as "this scores near zero" would turn a scoring-provider
outage into a full delivery outage. ``score=None`` is recorded and the delivery proceeds; only
a determinate score under the floor blocks.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from artifact_judge import DEFAULT_RUNNER, artifact_body, order_identity_text  # noqa: E402
import project_ledger  # noqa: E402

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
SCHEMA_PATH = SKILL_ROOT / "schemas" / "predelivery_score.schema.json"

TASK_CLASS = "diagnostic-agent"  # read-only, same reason as artifact_judge: a scorer that
# can write is a scorer that can start "fixing" the thing it was asked to grade.
TASK_LABEL = "gig-PREDELIVERY-SCORE"

# ★ Conservative on purpose (26-gig-loop §CC' 段E note). ★ E4 has not run yet -- there is no
# correlation data between this score and a real buyer's reaction -- so the floor only catches
# what is confidently bad rather than trying to be precise. A single named constant so the
# next pass (E4) has exactly one place to move it.
SCORE_FLOOR = 40

ERROR_PREDELIVERY_SCORE_LOW = "predelivery_score_low"

RUNNER_GRACE_SECONDS = 30

RECORD_NAME = "predelivery-score.json"
LEDGER_EVENT = "PREDELIVERY_SCORED"


def build_prompt(order_text: str, artifact_name: str, artifact_size: int, body: str) -> str:
    """The rubric. Three suggested dimensions; the model is free to name its own."""
    return f"""あなたは納品直前の採点者です。この成果物が、買い手の要件にどれだけ合っているかを採点してください。

0〜100点の総合スコア（score）と、採点の内訳（dimensions、1件以上）を返してください。
各 dimensions の要素は name（観点名）・score（0〜100）・reason（日本語1行、120文字以内）を持ちます。

参考にすべき観点（この名前を使う必要はありません。合わない場合は独自の観点で構いません）:
- 種類の一致: 買い手が注文した成果物の種類（企画・台本・デザイン・コード・記事など）と一致しているか
- 網羅性: 買い手が求めた内容をどれだけ満たしているか
- 形式の一致: 買い手が指定した納品形式・体裁に合っているか

★これは合否判定ではありません。★ deliverable かどうかの判定は別の仕組み（artifact_judge）が
既に行っています。ここでは「どれだけ良い出来か」を数値で採点してください。

--- 買い手の注文に関する記録 ---
{order_text}
--- ここまで ---

--- 成果物 ---
ファイル名: {artifact_name}
サイズ: {artifact_size} バイト
{body}
--- ここまで ---

スキーマに一致する JSON だけを返してください。
"""


def _score_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if 0 <= value <= 100 else None


def parse_score(payload: Any) -> dict[str, Any] | None:
    """The score dict, or ``None`` when the answer cannot be trusted.

    ★ Fails toward ``None``, not toward a number. ★ Anything short of a well-formed score
    (right types, each score in range, at least one dimension) is treated exactly like a
    scorer that could not be reached -- see the module docstring for why that means "deliver
    unscored", not "deliver refused".
    """
    if not isinstance(payload, dict):
        return None
    score = _score_int(payload.get("score"))
    if score is None:
        return None
    dimensions_raw = payload.get("dimensions")
    if not isinstance(dimensions_raw, list) or not dimensions_raw:
        return None
    dimensions: list[dict[str, Any]] = []
    for item in dimensions_raw:
        if not isinstance(item, dict):
            return None
        name = str(item.get("name") or "").strip()
        dim_score = _score_int(item.get("score"))
        if not name or dim_score is None:
            return None
        reason = str(item.get("reason") or "").strip().replace("\n", " ")[:300]
        dimensions.append({"name": name, "score": dim_score, "reason": reason})
    return {"score": score, "dimensions": dimensions}


def _read_runner_result(evidence_dir: Path) -> dict[str, Any] | None:
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
    return parse_score(payload)


def run_score(
    order_text: str,
    artifact_path: str | Path,
    body: str,
    artifact_name: str,
    artifact_size: int,
    *,
    runner: str | Path | None = None,
    schema: str | Path | None = None,
    evidence_dir: str | Path,
    timeout_seconds: int = 180,
) -> dict[str, Any] | None:
    """Ask a separate read-only session for the score. Never raises; ``None`` on any doubt."""
    runner_path = Path(
        str(runner or os.environ.get("GIG_PREDELIVERY_SCORE_RUNNER") or DEFAULT_RUNNER)
    ).expanduser()
    schema_path = Path(str(schema or SCHEMA_PATH)).expanduser()
    evidence = Path(evidence_dir).expanduser()

    if not runner_path.is_file() or not schema_path.is_file():
        return None

    prompt = build_prompt(order_text, artifact_name, artifact_size, body)
    try:
        evidence.mkdir(parents=True, exist_ok=True)
        prompt_path = evidence / "predelivery-score.prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
    except OSError:
        return None

    with tempfile.TemporaryDirectory(prefix="gig-predelivery-score-") as neutral_workdir:
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


Scorer = Callable[..., "dict[str, Any] | None"]


def default_scorer(
    project_root: str | Path, artifact_path: str | Path,
    requirements_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """Score this artifact against the buyer's own record of what they ordered.

    ``None`` (not scored) for exactly the two cases ``artifact_judge`` already treats as
    "nothing to read": an opaque binary package (zip/mp4/png -- 51 of 57 real artifacts,
    measured in artifact_judge.py) and an order with no buyer text on record at all. Scoring
    those would either invent a number from a file name or block a majority of real
    deliveries on an empty rubric -- see artifact_judge's own reasoning for the same split.
    """
    order_text = order_identity_text(project_root, requirements_path)
    if not order_text.strip():
        return None
    kind, body = artifact_body(artifact_path)
    if kind in ("binary", "unreadable"):
        return None
    artifact = Path(str(artifact_path)).expanduser()
    try:
        size = artifact.stat().st_size
    except OSError:
        return None
    evidence_dir = (
        Path(os.environ.get("GIG_PREDELIVERY_SCORE_STATE") or (Path.home() / ".local" / "state" / "anicca" / "gig" / "predelivery-score"))
        .expanduser() / uuid.uuid4().hex
    )
    return run_score(order_text, artifact, body, artifact.name, size, evidence_dir=evidence_dir)


def _record_path(project_root: Path) -> Path:
    return project_root / "acceptance" / RECORD_NAME


def score_predelivery(
    project_root: str | Path,
    artifact_path: str | Path,
    requirements_path: str | Path | None = None,
    *,
    scorer: Scorer | None = None,
) -> dict[str, Any]:
    """Score, persist, record on the ledger, and raise only below the floor.

    ★ Blocking is the exception, not the rule. ★ A determinate score at or above
    ``SCORE_FLOOR`` returns normally with the score recorded. A determinate score below it
    raises ``ValueError("predelivery_score_low:<reason>")`` -- the same shape as
    ``artifact_judge``'s refusals, so it is caught by the identical ``except ValueError``
    block already sitting at both delivery call sites and follows the same routing: askable
    refusals become a buyer question, everything else re-raises and the pass records a
    failed attempt and retries later. No new blocking mechanism was built; this reuses the
    one the judge already has.
    """
    scorer = scorer or default_scorer
    try:
        result = scorer(project_root, artifact_path, requirements_path)
    except Exception:  # noqa: BLE001 - a scorer that crashes has scored nothing
        result = None

    root = Path(str(project_root)).expanduser()
    score = result.get("score") if isinstance(result, dict) else None
    dimensions = result.get("dimensions", []) if isinstance(result, dict) else []
    record = {
        "score": score,
        "dimensions": dimensions,
        "scored_at": time.time(),
        "model": TASK_LABEL,
        "floor": SCORE_FLOOR,
    }

    try:
        record_path = _record_path(root)
        record_path.parent.mkdir(parents=True, exist_ok=True)
        record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass  # best-effort evidence; the ledger line below is the record that must land

    try:
        project_ledger.append(
            root,
            {
                "predelivery_score": score,
                "predelivery_score_dimensions": dimensions,
                "predelivery_scored_at": record["scored_at"],
            },
            LEDGER_EVENT,
        )
    except (ValueError, OSError):
        pass  # an uninitialized/unwritable project must not turn a score into a crash

    if score is not None and score < SCORE_FLOOR:
        worst = min(dimensions, key=lambda d: d.get("score", 0), default=None)
        reason = (worst or {}).get("reason") or f"score {score} below floor {SCORE_FLOOR}"
        raise ValueError(f"{ERROR_PREDELIVERY_SCORE_LOW}:{reason}")

    return record


def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--requirements", type=Path)
    args = parser.parse_args()
    try:
        record = score_predelivery(args.project_root, args.artifact, args.requirements)
    except ValueError as blocked:
        print(json.dumps({"ok": False, "error": str(blocked)}, ensure_ascii=False))
        return 1
    print(json.dumps({"ok": True, "record": record}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
