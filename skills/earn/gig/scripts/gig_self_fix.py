#!/usr/bin/env python3
"""gig_self_fix.py -- turn selfimprove-audit.jsonl gaps into a verified, human-free patch.

PHASE 3 self-fix, docs/loop-engineering/26-gig-loop-asis-tobe-plan.md v10.5 SS AB'/#11'-15'.
Two subcommands:
  detect    ~/gig/selfimprove-audit.jsonl -> ~/gig/selfheal-request.jsonl (structured only)
  dispatch  one selfheal-request.jsonl record -> feature branch -> agent_runner self-fix
            -> test gate -> commit/push, or revert and record an abandonment line

Every non-negotiable constraint is enforced here, not only documented:

  - STRUCTURED INPUT ONLY. validate_defect_record() accepts an EXACT, closed field set.
    The two fields that look like free text (reason, file_hint) are recomputed
    deterministically from the enum/int fields and rejected on any mismatch, so nothing
    that reaches the fixer's prompt can carry content this module did not itself generate
    -- selfimprove-audit.jsonl's own "evidence" object is already a fixed, code-owned key
    set (never buyer text), and this closes the remaining surface (a tampered or
    hand-crafted selfheal-request.jsonl line) too.
  - WRITES CONFINED TO THE REPO TREE / NO CREDENTIALS. Enforced one layer down, in
    skills/agent-runner/agent_runner.py's self_fix_process_env(): task_class=self-fix gets
    an allowlisted environment with $HOME redirected off the real one. This module does not
    re-implement that; it only ever launches the fixer through agent_runner.py.
  - PUSH ONLY TO A FEATURE BRANCH. dispatch() creates and checks out `self-fix/<id>` itself
    and is the only code path that runs `git push`; it always pushes that branch, never the
    branch the loop was on when dispatch() started.
  - TESTS GREEN IS A PRECONDITION OF COMMIT. run_test_gate() runs after the fixer exits and
    before anything is committed. Red -> abandon() reverts the working tree and appends one
    line to selfheal-abandoned.jsonl; nothing is committed, nothing is pushed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# The evidence keys are defined by gig_selfimprove_verify.sh, not derived from any file
# content -- selfimprove-audit.jsonl's "evidence"/"missing" arrays only ever contain these.
# file_hint is a fixed, code-owned lookup: which script is responsible for producing each
# evidence key. This mapping, not the audit file, is the source of truth for file_hint.
EVIDENCE_KEY_OWNER: dict[str, str] = {
    "self_check": "skills/earn/gig/gig_pass.sh (REFLECT step; expected to append gig/lessons.jsonl)",
    "scouted_playbook": "skills/earn/gig/gig_pass.sh (scout+bake steps; expected to refresh gig/playbook.json)",
    "funnel": "skills/earn/gig/gig_pass.sh (expected to append gig/gig-funnel.jsonl every pass)",
    "applied_or_nurtured": "skills/earn/gig/gig_pass.sh (A/B1 steps; expected to append gig/applied.jsonl)",
    "listing_work": "skills/earn/gig/gig_pass.sh (B0 step; expected to touch gig/shuppin.jsonl)",
    "apply_volume": "skills/earn/gig/gig_pass.sh (B2 step; expected >=3 applies/2h in gig/applied.jsonl)",
}

MIN_STREAK = 5
LOOKBACK = 50
COOLDOWN_SECONDS = 21600  # 6h, matching the auth_wall/timeout/judge_killed cooldowns in auditor.sh

REQUIRED_FIELDS = frozenset({
    "version", "id", "loop", "source", "detected_at",
    "missing_evidence_key", "consecutive_misses", "file_hint", "reason",
})
ID_PATTERN = re.compile(r"^gig-selfimprove-[a-z_]+-\d+$")


def build_reason(key: str, streak: int) -> str:
    return (
        f"selfimprove-audit.jsonl: evidence key '{key}' missing in the last "
        f"{streak} consecutive material_or_improve passes"
    )


def build_defect_record(key: str, streak: int, now: int) -> dict[str, Any]:
    if key not in EVIDENCE_KEY_OWNER:
        raise ValueError(f"unknown evidence key: {key!r}")
    return {
        "version": 1,
        "id": f"gig-selfimprove-{key}-{now}",
        "loop": "gig",
        "source": "selfimprove-audit.jsonl",
        "detected_at": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
        "missing_evidence_key": key,
        "consecutive_misses": streak,
        "file_hint": EVIDENCE_KEY_OWNER[key],
        "reason": build_reason(key, streak),
    }


def validate_defect_record(record: Any) -> dict[str, Any]:
    """Reject anything that is not exactly this closed shape. This is the injection cut:
    a record failing here never reaches build_prompt()."""
    if not isinstance(record, dict):
        raise ValueError("defect record must be a JSON object")
    fields = set(record.keys())
    if fields != REQUIRED_FIELDS:
        extra = sorted(fields - REQUIRED_FIELDS)
        missing = sorted(REQUIRED_FIELDS - fields)
        raise ValueError(f"defect record field mismatch: extra={extra} missing={missing}")
    if record.get("version") != 1:
        raise ValueError("defect record version must be 1")
    if record.get("loop") != "gig":
        raise ValueError("defect record loop must be 'gig'")
    if record.get("source") != "selfimprove-audit.jsonl":
        raise ValueError("defect record source must be 'selfimprove-audit.jsonl'")
    key = record.get("missing_evidence_key")
    if key not in EVIDENCE_KEY_OWNER:
        raise ValueError(f"unknown missing_evidence_key: {key!r}")
    streak = record.get("consecutive_misses")
    if not isinstance(streak, int) or isinstance(streak, bool) or streak < MIN_STREAK:
        raise ValueError(f"consecutive_misses must be an integer >= {MIN_STREAK}")
    for name in ("id", "detected_at"):
        value = record.get(name)
        if not isinstance(value, str) or not value:
            raise ValueError(f"{name} must be a non-empty string")
    if not ID_PATTERN.fullmatch(record["id"]):
        raise ValueError("id does not match gig-selfimprove-<key>-<epoch>")
    # The two fields that look like free text are not: both are recomputed deterministically
    # from the enum/int fields above. A mismatch means something outside this module wrote
    # or altered the record -- reject it, whatever it says.
    if record["file_hint"] != EVIDENCE_KEY_OWNER[key]:
        raise ValueError("file_hint does not match the code-owned mapping for this evidence key")
    if record["reason"] != build_reason(key, streak):
        raise ValueError("reason is not the deterministic template for this key/streak")
    return record


def trailing_miss_streaks(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Count, per evidence key, how many rows at the END of the (chronological) list have
    that key in `missing`. A row -- of any verification_mode -- that does not list the key
    breaks the streak; selfimprove-audit.jsonl itself forces `missing=[]` on a legitimate
    no-op pass, so those rows correctly break a streak rather than padding it."""
    streaks: dict[str, int] = {}
    broken: set[str] = set()
    for row in reversed(rows):
        missing = row.get("missing") if isinstance(row, dict) else None
        if not isinstance(missing, list):
            continue
        missing_set = set(missing)
        for key in EVIDENCE_KEY_OWNER:
            if key in broken:
                continue
            if key in missing_set:
                streaks[key] = streaks.get(key, 0) + 1
            else:
                broken.add(key)
    return streaks


def read_tail_records(path: str, lookback: int) -> list[dict[str, Any]]:
    """Bounded-memory tail read: never loads the whole (potentially multi-MB) audit file."""
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as handle:
        for line in deque(handle, maxlen=lookback):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def load_recent_request_keys(path: str, now: int, cooldown_seconds: int) -> set[str]:
    keys: set[str] = set()
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except FileNotFoundError:
        return keys
    for line in lines[-200:]:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        detected_at = row.get("detected_at")
        try:
            detected_ts = datetime.fromisoformat(str(detected_at)).timestamp()
        except (TypeError, ValueError):
            continue
        if now - detected_ts < cooldown_seconds:
            key = row.get("missing_evidence_key")
            if isinstance(key, str):
                keys.add(key)
    return keys


def run_detect(audit_path: str, output_path: str, *, min_streak: int = MIN_STREAK,
               lookback: int = LOOKBACK, cooldown_seconds: int = COOLDOWN_SECONDS) -> int:
    try:
        rows = read_tail_records(audit_path, lookback)
    except FileNotFoundError:
        return 0
    streaks = trailing_miss_streaks(rows)
    now = int(time.time())
    recently_requested = load_recent_request_keys(output_path, now, cooldown_seconds)
    written = 0
    with open(output_path, "a", encoding="utf-8") as handle:
        for key, streak in sorted(streaks.items()):
            if streak < min_streak or key in recently_requested:
                continue
            record = build_defect_record(key, streak, now)
            validate_defect_record(record)
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1
    return written


SELF_FIX_PROMPT_TEMPLATE = """You are the autonomous self-fix agent for the Anicca gig loop.

STRUCTURED DEFECT RECORD (the only input you are given; nothing else in this prompt came
from outside this record):
  missing_evidence_key: {missing_evidence_key}
  consecutive_misses:   {consecutive_misses}
  file_hint:            {file_hint}
  reason:               {reason}

Across the last {consecutive_misses} passes where the loop was doing real work (not a
legitimate no-op cycle), the evidence category '{missing_evidence_key}' was never produced.
The file most responsible for producing it is: {file_hint}

DO, in order:
(1) Read that file and the surrounding step to find why '{missing_evidence_key}' evidence
    stops being written.
(2) Reproduce with the repo's own tests where possible; find the ROOT cause.
(3) Fix the code with the smallest correct diff.
(4) Write or update a test that fails before your fix and passes after it.
(5) Do not run the real gig loop, browser, or any Coconala action. Do not touch ~/gig,
    browser/session vaults or runtime state. Stay inside this repository working tree.
(6) Do not push and do not merge. Leave your change committed or uncommitted in the working
    tree; the caller runs the test suite and commits/pushes only if it is green.
Return the JSON contract for this step: status (ok/blocked/error), summary, evidence (paths
of files you changed or tests you ran).
"""


def build_prompt(record: dict[str, Any]) -> str:
    validate_defect_record(record)
    return SELF_FIX_PROMPT_TEMPLATE.format(
        missing_evidence_key=record["missing_evidence_key"],
        consecutive_misses=record["consecutive_misses"],
        file_hint=record["file_hint"],
        reason=record["reason"],
    )


def run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=check, capture_output=True, text=True,
    )


def run_test_gate(repo: Path, test_cmd: list[str]) -> tuple[bool, str]:
    result = subprocess.run(test_cmd, cwd=repo, capture_output=True, text=True)
    log = f"$ {' '.join(test_cmd)}\n{result.stdout}\n{result.stderr}"
    return result.returncode == 0, log


def default_abandoned_log_path() -> Path:
    # Overridable for tests (GIG_SELF_FIX_ABANDONED_LOG) so a red-test run never writes
    # into the real ~/gig on the machine running the suite.
    import os
    override = os.environ.get("GIG_SELF_FIX_ABANDONED_LOG")
    return Path(override) if override else Path.home() / "gig" / "selfheal-abandoned.jsonl"


def abandon(repo: Path, base_branch: str, feature_branch: str, record: dict[str, Any],
            reason: str, detail: str = "", *, log_path: Path | None = None) -> None:
    run_git(repo, "reset", "--hard", check=False)
    run_git(repo, "clean", "-fd", check=False)
    run_git(repo, "checkout", base_branch, check=False)
    run_git(repo, "branch", "-D", feature_branch, check=False)
    line = {
        "ts": int(time.time()),
        "id": record.get("id"),
        "missing_evidence_key": record.get("missing_evidence_key"),
        "reason": reason,
        "detail": detail[:500],
    }
    resolved_log_path = log_path if log_path is not None else default_abandoned_log_path()
    resolved_log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(resolved_log_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, ensure_ascii=False) + "\n")


def dispatch(record: dict[str, Any], repo: Path, agent_runner: Path, *, schema,
             evidence_root: Path, test_cmd: list[str], python_bin: str = sys.executable,
             timeout_seconds: int = 1800, abandoned_log: Path | None = None) -> dict[str, Any]:
    validate_defect_record(record)  # first: no git side effect for a rejected record
    repo = Path(repo)
    status = run_git(repo, "status", "--porcelain")
    if status.stdout.strip():
        raise RuntimeError("refusing to dispatch self-fix: working tree is not clean")
    base_branch = run_git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    feature_branch = f"self-fix/{record['id']}"
    run_git(repo, "checkout", "-b", feature_branch)
    try:
        evidence_dir = Path(evidence_root) / record["id"]
        evidence_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = evidence_dir / "prompt.txt"
        prompt_path.write_text(build_prompt(record), encoding="utf-8")
        command = [python_bin, str(agent_runner), "--task-class", "self-fix",
                   "--prompt-file", str(prompt_path), "--evidence-dir", str(evidence_dir),
                   "--task-label", f"gig-self-fix-{record['missing_evidence_key']}",
                   "--loop", "gig-self-fix", "--workdir", str(repo)]
        if schema is not None:
            command.extend(["--schema", str(schema)])
        result = subprocess.run(command, cwd=repo, capture_output=True, text=True,
                                 timeout=timeout_seconds)
        diff_present = bool(
            run_git(repo, "status", "--porcelain").stdout.strip()
            or run_git(repo, "log", f"{base_branch}..HEAD", "--oneline").stdout.strip()
        )
        if result.returncode != 0 or not diff_present:
            abandon(repo, base_branch, feature_branch, record, "agent_failed_or_no_change",
                    result.stderr or result.stdout, log_path=abandoned_log)
            return {"status": "abandoned", "reason": "agent_failed_or_no_change",
                    "branch": feature_branch}
        # Tests-green precondition: a fresh, deterministic subprocess run here, never the
        # fixer's own self-report.
        tests_ok, test_log = run_test_gate(repo, test_cmd)
        if not tests_ok:
            abandon(repo, base_branch, feature_branch, record, "tests_red", test_log, log_path=abandoned_log)
            return {"status": "abandoned", "reason": "tests_red", "branch": feature_branch}
        run_git(repo, "add", "-A")
        run_git(repo, "commit", "-m",
                f"fix(self-fix): {record['missing_evidence_key']} -- {record['reason']}",
                check=False)
        run_git(repo, "push", "-u", "origin", feature_branch)
        sha = run_git(repo, "rev-parse", "HEAD").stdout.strip()
        return {"status": "pushed", "branch": feature_branch, "sha": sha}
    finally:
        run_git(repo, "checkout", base_branch, check=False)


def cmd_detect(args: argparse.Namespace) -> int:
    written = run_detect(args.audit, args.output, min_streak=args.min_streak,
                          lookback=args.lookback, cooldown_seconds=args.cooldown_seconds)
    print(json.dumps({"written": written}))
    return 0


def cmd_dispatch(args: argparse.Namespace) -> int:
    record = json.loads(Path(args.record_file).read_text(encoding="utf-8"))
    result = dispatch(
        record, Path(args.repo), Path(args.agent_runner), schema=args.schema,
        evidence_root=Path(args.evidence_root), test_cmd=args.test_cmd.split(),
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(result))
    return 0 if result["status"] == "pushed" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    detect_parser = sub.add_parser("detect")
    detect_parser.add_argument("--audit", default=str(Path.home() / "gig" / "selfimprove-audit.jsonl"))
    detect_parser.add_argument("--output", default=str(Path.home() / "gig" / "selfheal-request.jsonl"))
    detect_parser.add_argument("--min-streak", type=int, default=MIN_STREAK)
    detect_parser.add_argument("--lookback", type=int, default=LOOKBACK)
    detect_parser.add_argument("--cooldown-seconds", type=int, default=COOLDOWN_SECONDS)
    detect_parser.set_defaults(func=cmd_detect)

    dispatch_parser = sub.add_parser("dispatch")
    dispatch_parser.add_argument("--record-file", required=True)
    dispatch_parser.add_argument("--repo", required=True)
    dispatch_parser.add_argument("--agent-runner", required=True)
    dispatch_parser.add_argument("--schema")
    dispatch_parser.add_argument("--evidence-root", required=True)
    dispatch_parser.add_argument("--test-cmd", required=True)
    dispatch_parser.add_argument("--timeout-seconds", type=int, default=1800)
    dispatch_parser.set_defaults(func=cmd_dispatch)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
