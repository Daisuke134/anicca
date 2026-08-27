#!/usr/bin/env python3
"""Provider-neutral creative judge for grounded, original video hook adaptations."""

from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile
import uuid

import intel_store


HERE = pathlib.Path(__file__).resolve().parent
ENGINE = HERE.parent


class HookJudgmentError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise HookJudgmentError(message)


def _rows(path: pathlib.Path) -> list[dict]:
    return intel_store.read_jsonl(path) if path.exists() else []


def _verify_file(path_value: str, expected_hash: str, label: str) -> pathlib.Path:
    path = pathlib.Path(path_value)
    _require(path.is_file(), f"{label} evidence missing")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    _require(actual == expected_hash, f"{label} evidence hash mismatch")
    return path


def _validate_hook(row: dict, transcript_row: dict, transcript: dict,
                   observed_at: str) -> None:
    try:
        intel_store.VALIDATORS["hook-library"](row)
    except (KeyError, intel_store.StoreError) as exc:
        raise HookJudgmentError(str(exc)) from exc
    _require(row["source_type"] == "video", "hook source_type must be video")
    _require(row["provenance"] == "live_observed", "hook provenance must be live_observed")
    _require(row["source_url"] == transcript_row["native_url"], "hook source URL not grounded")
    _require(row["evidence_url"] == transcript_row["native_url"], "hook evidence URL not grounded")
    _require(row["product_ids"] == transcript_row["product_ids"], "hook product scope mismatch")
    _require(row["language"] == transcript_row["language"], "hook language mismatch")
    _require(row["captured_at"] == observed_at, "hook captured_at mismatch")
    _require(row["status"] == "active" and row["ewma_score"] is None and row["observations"] == 0,
             "new video hook cannot claim measured performance")
    rubric = row["rubric"]
    dimensions = ("hook", "emotional_peak", "conflict", "quotability", "practical_value")
    _require(all(isinstance(rubric[key], (int, float)) and 0 <= rubric[key] <= 10
                 for key in dimensions), "rubric dimension outside 0..10")
    _require(rubric["total"] == sum(rubric[key] for key in dimensions),
             "rubric total does not sum")
    candidate = " ".join(row["text"].casefold().split())
    source_text = " ".join(transcript["text"].casefold().split())
    _require(len(candidate) >= 12, "hook text too short")
    _require(candidate not in source_text, "verbatim competitor hook forbidden")


def _write_transaction(intel_root: pathlib.Path, hook_rows: list[dict], evidence_rows: list[dict],
                       judgment_row: dict) -> int:
    lock_path = intel_root / ".intel.lock"
    lock_path.touch(exist_ok=True)
    with lock_path.open("r+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        hooks_path = intel_root / "hook-library.jsonl"
        evidence_path = intel_root / "hook-evidence.jsonl"
        judged_path = intel_root / "video-hook-judgments.jsonl"
        existing_hooks = _rows(hooks_path)
        existing_evidence = _rows(evidence_path)
        existing_judged = _rows(judged_path)
        by_id = {row["id"]: row for row in existing_hooks}
        additions = []
        for row in hook_rows:
            previous = by_id.get(row["id"])
            if previous is None:
                additions.append(row)
            elif previous != row:
                raise HookJudgmentError(f"conflicting hook replay {row['id']}")
        staged = []
        documents = (
            (hooks_path, existing_hooks + additions),
            (evidence_path, existing_evidence + evidence_rows),
            (judged_path, existing_judged + [judgment_row]),
        )
        try:
            for destination, rows in documents:
                handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=intel_root,
                                                     prefix=f".{destination.name}.", delete=False)
                with handle:
                    for row in rows:
                        handle.write(json.dumps(row, ensure_ascii=False,
                                                separators=(",", ":")) + "\n")
                staged.append((pathlib.Path(handle.name), destination))
            intel_store.validate_store(staged[0][0], "hook-library")
            for temp_path, destination in staged:
                os.replace(temp_path, destination)
        finally:
            for temp_path, _ in staged:
                temp_path.unlink(missing_ok=True)
        return len(additions)


def judge_pending_video_hooks(intel_root: pathlib.Path, evidence_root: pathlib.Path,
                              judge, run_id: str | None = None,
                              observed_at: str | None = None) -> dict:
    intel_root = pathlib.Path(intel_root)
    transcripts = _rows(intel_root / "video-transcripts.jsonl")
    judged = _rows(intel_root / "video-hook-judgments.jsonl")
    judged_ids = {row["transcript_id"] for row in judged}
    pending = [row for row in transcripts if row["id"] not in judged_ids]
    observed_at = observed_at or dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    run_id = run_id or uuid.uuid4().hex
    run_dir = pathlib.Path(evidence_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    if not pending:
        receipt = {"schema_version": "marketing.video-hook-judge-run.v1", "run_id": run_id,
                   "observed_at": observed_at, "status": "skipped",
                   "pending_transcripts": 0, "accepted_hooks": 0}
        (run_dir / "run.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        return receipt
    transcript_row = pending[0]
    transcript_path = _verify_file(transcript_row["transcript_path"],
                                   transcript_row["transcript_sha256"], "transcript")
    _verify_file(transcript_row["media_path"], transcript_row["media_sha256"], "media")
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    manifest = {
        "schema_version": "marketing.video-hook-judge-input.v1",
        "run_id": run_id, "captured_at": observed_at,
        "transcript": transcript_row, "transcript_content": transcript,
        "existing_hooks": [{"id": row["id"], "text": row["text"],
                            "product_ids": row["product_ids"]}
                           for row in _rows(intel_root / "hook-library.jsonl")],
        "judge_evidence_dir": str(run_dir / "agent"),
    }
    result = judge(manifest)
    _require(isinstance(result, dict) and set(result) == {"hooks"},
             "judge output must contain hooks only")
    hooks = result["hooks"]
    _require(isinstance(hooks, list) and len(hooks) <= 3, "judge hooks must be bounded array")
    seen = set()
    for row in hooks:
        _require(isinstance(row, dict), "hook proposal must be object")
        _require(row.get("id") not in seen, "duplicate hook proposal id")
        seen.add(row.get("id"))
        _validate_hook(row, transcript_row, transcript, observed_at)
    evidence_rows = [{
        "schema_version": "marketing.hook-evidence.v1",
        "id": f"evidence.{row['id']}", "hook_id": row["id"],
        "transcript_id": transcript_row["id"], "source_url": transcript_row["native_url"],
        "captured_at": observed_at, "transcript_path": transcript_row["transcript_path"],
        "transcript_sha256": transcript_row["transcript_sha256"],
        "media_path": transcript_row["media_path"], "media_sha256": transcript_row["media_sha256"],
    } for row in hooks]
    judgment_row = {
        "schema_version": "marketing.video-hook-judgment.v1",
        "id": f"judgment.{transcript_row['id']}", "transcript_id": transcript_row["id"],
        "judge_run_id": run_id, "judged_at": observed_at,
        "accepted_hook_ids": [row["id"] for row in hooks],
    }
    accepted = _write_transaction(intel_root, hooks, evidence_rows, judgment_row)
    (run_dir / "judgment.json").write_text(json.dumps(result, ensure_ascii=False,
                                                       sort_keys=True, indent=2) + "\n",
                                            encoding="utf-8")
    receipt = {"schema_version": "marketing.video-hook-judge-run.v1", "run_id": run_id,
               "observed_at": observed_at, "status": "success",
               "pending_transcripts": len(pending) - 1, "accepted_hooks": accepted,
               "transcript_id": transcript_row["id"]}
    (run_dir / "run.json").write_text(json.dumps(receipt, ensure_ascii=False,
                                                  sort_keys=True, indent=2) + "\n",
                                       encoding="utf-8")
    return receipt


def agent_hook_judge(manifest: dict) -> dict:
    schema = HERE / "schemas" / "video-hook-judgment.schema.json"
    prompt = f"""You judge one observed competitor video for the Marketing Engine.

Evidence manifest:
{json.dumps(manifest, ensure_ascii=False, indent=2)}

Return only the schema-valid JSON object.

Create zero to three ORIGINAL hook hypotheses for the declared product and language. Learn the
mechanism, emotional tension, pacing, and practical promise; never copy or lightly edit the source
speaker's wording, identity, claims, or character. A hook is a test hypothesis, not a proven winner.
Score each proposed hook from 0 to 10 on hook strength, emotional peak, conflict, quotability, and
practical value; total must equal their sum. Use status active, ewma_score null, observations 0,
source_type video, provenance live_observed, captured_at {manifest['captured_at']}, and copy the exact
native_url byte-for-byte into both source_url and evidence_url. Use exactly the transcript's language
and product_ids. Omit a hook when you cannot make a meaningfully original, relevant adaptation.
Do not modify files or perform external actions."""
    evidence_dir = pathlib.Path(manifest["judge_evidence_dir"])
    completed = subprocess.run(
        [str(ENGINE / "run_agent.sh"), "--task-class", "marketing-agent",
         "--evidence-dir", str(evidence_dir), "--task-label", "video-hook-judge",
         "--loop", "marketing-intel", "--schema", str(schema), "--print-result"],
        input=prompt, text=True, capture_output=True, timeout=600, check=False,
    )
    if completed.returncode != 0:
        raise HookJudgmentError((completed.stderr or completed.stdout or "agent judge failed")[-2000:])
    return json.loads(completed.stdout)
