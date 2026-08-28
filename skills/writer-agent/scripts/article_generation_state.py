#!/usr/bin/env python3
"""Crash-safe pre-publication generation attempt classification.

The full article prompt may be retried only while the run is mechanically empty of
publication state, ledger rows, and generated/staged artifacts.  The prompt bytes and
run identity are immutable across retries.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = 1
MAX_GENERATION_ATTEMPTS = 3
MAX_EMPTY_INTERRUPTION_RECOVERIES = 1
ALLOWED_PREPUBLICATION_FILES = {
    "article-daily-prompt.txt",
    "git-hash.txt",
    "model-stdout.log",
    "gates/generation-state.json",
    "gates/.generation-state.json.lock",
    "gates/strategy-consumption.json",
    "gates/quality-replacement.json",
    "gates/media-create-required.json",
    # The selected demand route is a durable pre-publication receipt. Keep it
    # in place during an interrupted retry so the owner-fence can restore the
    # exact in-progress card without selecting a second topic.
    "gates/topic-route-input.json",
    "gates/topic-route.json",
    # The wrapper's resume owner-fence is also a durable pre-publication
    # receipt. It records the exact queued card before generation begins and
    # must survive a safe retry boundary without being mistaken for output.
    "gates/topic-card-resume.json",
}

# Wrapper-owned runtime infrastructure inside the run dir. These are never
# generation artifacts and never block a safe resume boundary.
# research-sources/ and research/ are ephemeral research scratch:
# sandbox-free agents npm-install / uv-venv sample repos there, leaving
# symlinks that crash archival. They are never publication artifacts, so
# they are excluded from the interruption manifest entirely.
ALLOWED_PREPUBLICATION_PREFIXES = (
    "gates/judge-broker/",
    "research-sources/",
    "research/",
)


def _is_allowed_prepublication(relative: str) -> bool:
    return relative in ALLOWED_PREPUBLICATION_FILES or relative.startswith(
        ALLOWED_PREPUBLICATION_PREFIXES
    )


class GenerationInvariant(ValueError):
    """The run is not provably safe for a full-prompt generation retry."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_sha256(manifest: list[dict[str, str]]) -> str:
    payload = json.dumps(
        manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _state_path(run_dir: Path) -> Path:
    return run_dir / "gates" / "generation-state.json"


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("version") != VERSION:
        raise GenerationInvariant("invalid generation state")
    return value


def _charged_attempt_count(state: dict[str, Any]) -> int:
    """Count generation attempts while forgiving one zero-artifact interruption.

    A terminated provider invocation that created no publication candidate must
    remain auditable, but charging the only empty interruption against the
    article budget can permanently strand an otherwise untouched daily run.
    Further empty interruptions are charged, keeping recovery bounded.
    """

    attempts = state.get("attempts", [])
    if not isinstance(attempts, list):
        raise GenerationInvariant("generation attempts are invalid")
    empty_interruptions = sum(
        1
        for attempt in attempts
        if isinstance(attempt, dict)
        and attempt.get("status") == "interrupted-safe"
        and attempt.get("archive_manifest") == []
    )
    free_recoveries = int(
        state.get(
            "maximum_empty_interruption_recoveries",
            MAX_EMPTY_INTERRUPTION_RECOVERIES,
        )
    )
    if free_recoveries < 0 or free_recoveries > MAX_EMPTY_INTERRUPTION_RECOVERIES:
        raise GenerationInvariant("empty interruption recovery budget is invalid")
    return len(attempts) - min(empty_interruptions, free_recoveries)


def _failed_before_publication(state: dict[str, Any]) -> bool:
    attempts = state.get("attempts")
    return bool(
        state.get("status") == "provider-failed-ambiguous"
        and isinstance(attempts, list)
        and attempts
        and isinstance(attempts[-1].get("return_code"), int)
        and attempts[-1]["return_code"] != 0
        and attempts[-1].get("boundary") == "prepublication-empty"
    )


def _lock(path: Path):
    lock_path = path.with_name(f".{path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+")
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    return handle


def _validate_boundary(run_dir: Path, run_id: str, prompt_file: Path) -> Path:
    if run_dir.is_symlink() or not run_dir.is_dir():
        raise GenerationInvariant("run directory is missing or symlinked")
    resolved = run_dir.resolve(strict=True)
    if resolved.name != run_id:
        raise GenerationInvariant("run identity does not match its directory")
    expected_prompt = resolved / "article-daily-prompt.txt"
    if prompt_file.is_symlink() or not prompt_file.is_file():
        raise GenerationInvariant("prompt is missing or symlinked")
    if prompt_file.resolve(strict=True) != expected_prompt:
        raise GenerationInvariant("prompt is outside the immutable run")
    return resolved


def _ledger_has_run(ledger: Path, run_id: str) -> bool:
    if not ledger.exists():
        return False
    for line in ledger.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(row, dict) and row.get("run_id") == run_id:
            return True
    return False


def _ledger_has_public_row(ledger: Path, run_id: str) -> bool:
    """A draft-stage bookkeeping row (published false, no live URL) is not a
    public side effect; only published/live rows block a same-prompt resume."""
    if not ledger.exists():
        return False
    for line in ledger.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(row, dict) or row.get("run_id") != run_id:
            continue
        if (
            row.get("published") is True
            or bool(row.get("live_url"))
            or row.get("state") == "live"
            or row.get("reality_gate") == "PASS"
        ):
            return True
    return False


def prepublication_empty(run_dir: Path, run_id: str, ledger: Path) -> tuple[bool, str]:
    if (run_dir / "gates" / "publication-state.json").exists():
        return False, "publication-state-exists"
    if _ledger_has_public_row(ledger, run_id):
        return False, "ledger-row-exists"
    observed = {
        str(path.relative_to(run_dir))
        for path in run_dir.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    unexpected = sorted(
        path for path in observed if not _is_allowed_prepublication(path)
    )
    if unexpected:
        return False, f"generated-or-staged-artifacts:{','.join(unexpected)}"
    return True, "prepublication-empty"


def initialize(run_dir: Path, run_id: str, prompt_file: Path, ledger: Path) -> dict[str, Any]:
    resolved = _validate_boundary(run_dir, run_id, prompt_file)
    state_path = _state_path(resolved)
    prompt_hash = file_sha256(prompt_file)
    with _lock(state_path):
        if state_path.exists():
            state = _load(state_path)
            if (
                state.get("run_id") != run_id
                or state.get("prompt_sha256") != prompt_hash
            ):
                raise GenerationInvariant("generation identity is immutable")
            return state
        safe, reason = prepublication_empty(resolved, run_id, ledger)
        if not safe:
            raise GenerationInvariant(reason)
        state = {
            "version": VERSION,
            "run_id": run_id,
            "run_dir": str(resolved),
            "prompt_path": str(prompt_file.resolve(strict=True)),
            "prompt_sha256": prompt_hash,
            "status": "prepared",
            "maximum_attempts": MAX_GENERATION_ATTEMPTS,
            "maximum_empty_interruption_recoveries": (
                MAX_EMPTY_INTERRUPTION_RECOVERIES
            ),
            "attempts": [],
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        _atomic_write(state_path, state)
        return state


def begin(
    run_dir: Path,
    run_id: str,
    prompt_file: Path,
    ledger: Path,
    owner_pid: int | None = None,
) -> dict[str, Any]:
    resolved = _validate_boundary(run_dir, run_id, prompt_file)
    state_path = _state_path(resolved)
    if not state_path.exists():
        initialize(resolved, run_id, prompt_file, ledger)
    with _lock(state_path):
        state = _load(state_path)
        if state.get("run_id") != run_id or state.get("prompt_sha256") != file_sha256(prompt_file):
            raise GenerationInvariant("prompt or run identity changed")
        safe, reason = prepublication_empty(resolved, run_id, ledger)
        quality_reroute = _quality_reroute_pending(resolved, run_id, ledger)
        if not safe and not quality_reroute:
            raise GenerationInvariant(reason)
        allowed_statuses = {
            "prepared",
            "provider-failed-safe",
            "interrupted-safe",
        }
        if _failed_before_publication(state):
            allowed_statuses.add("provider-failed-ambiguous")
        if quality_reroute:
            allowed_statuses.add("provider-returned")
        if state.get("status") not in allowed_statuses:
            raise GenerationInvariant("generation attempt is not safely resumable")
        if _charged_attempt_count(state) >= int(
            state.get("maximum_attempts", MAX_GENERATION_ATTEMPTS)
        ):
            raise GenerationInvariant("generation attempt limit exhausted")
        attempt = len(state.get("attempts", [])) + 1
        state.setdefault("attempts", []).append(
            {
                "attempt": attempt,
                "started_at": utc_now(),
                "status": "invoking",
                "owner_pid": owner_pid,
            }
        )
        state["status"] = "invoking"
        state["updated_at"] = utc_now()
        _atomic_write(state_path, state)
        return state


def _quality_reroute_pending(
    run_dir: Path, run_id: str, ledger: Path
) -> bool:
    if (run_dir / "gates" / "publication-state.json").exists():
        return False
    if _ledger_has_public_row(ledger, run_id):
        return False
    quality_path = run_dir / "gates" / "quality-self-heal.json"
    try:
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return False
    if not (
        quality
        and quality.get("version") == 2
        and quality.get("attempt") == 1
        and quality.get("action") == "reroute"
    ):
        return False
    records = quality.get("quality")
    if not isinstance(records, dict):
        return False
    for lang in ("ja", "en"):
        article = run_dir / f"article-{lang}.md"
        if (
            not article.is_file()
            or article.is_symlink()
            or records.get(lang, {}).get("article_sha256")
            != file_sha256(article)
        ):
            return False
    return True


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def recover_orphan(
    run_dir: Path,
    run_id: str,
    prompt_file: Path,
    ledger: Path,
    minimum_age_seconds: int = 60,
) -> dict[str, Any]:
    """Archive an invoking attempt only after its recorded owner disappeared."""

    resolved = _validate_boundary(run_dir, run_id, prompt_file)
    state_path = _state_path(resolved)
    with _lock(state_path):
        state = _load(state_path)
        attempts = state.get("attempts", [])
        if (
            state.get("status") != "invoking"
            or not isinstance(attempts, list)
            or not attempts
            or attempts[-1].get("status") != "invoking"
        ):
            raise GenerationInvariant("generation attempt is not invoking")
        owner_pid = attempts[-1].get("owner_pid")
        if isinstance(owner_pid, int) and _pid_is_alive(owner_pid):
            raise GenerationInvariant("generation owner is still alive")
        updated = datetime.fromisoformat(
            str(state.get("updated_at", "")).replace("Z", "+00:00")
        )
        age = (datetime.now(timezone.utc) - updated).total_seconds()
        if age < minimum_age_seconds:
            raise GenerationInvariant("generation orphan lease is not stale")
    return archive_interrupted(
        resolved, run_id, prompt_file, ledger, 143
    )


def record_result(
    run_dir: Path, run_id: str, prompt_file: Path, ledger: Path, return_code: int
) -> dict[str, Any]:
    resolved = _validate_boundary(run_dir, run_id, prompt_file)
    state_path = _state_path(resolved)
    with _lock(state_path):
        state = _load(state_path)
        attempts = state.get("attempts", [])
        if (
            state.get("run_id") != run_id
            or state.get("prompt_sha256") != file_sha256(prompt_file)
            or state.get("status") != "invoking"
            or not isinstance(attempts, list)
            or not attempts
            or attempts[-1].get("status") != "invoking"
        ):
            raise GenerationInvariant("generation result has no matching active attempt")
        safe, reason = prepublication_empty(resolved, run_id, ledger)
        if return_code == 75 and safe:
            status = "provider-failed-safe"
        elif return_code == 0:
            status = "provider-returned"
        else:
            status = "provider-failed-ambiguous"
        attempts[-1].update(
            {
                "finished_at": utc_now(),
                "return_code": return_code,
                "status": status,
                "boundary": reason,
            }
        )
        state["status"] = status
        state["updated_at"] = utc_now()
        _atomic_write(state_path, state)
        return state


def archive_interrupted(
    run_dir: Path,
    run_id: str,
    prompt_file: Path,
    ledger: Path,
    return_code: int,
) -> dict[str, Any]:
    """Archive a terminated prepublication attempt and make the same prompt resumable."""
    # A bounded timeout or SIGINT/SIGTERM archives a still-active attempt; a classified retryable
    # provider failure (75) that only staged artifacts may also archive, so
    # the same immutable prompt can resume instead of stranding the run.
    if return_code in {124, 130, 143}:
        allowed_statuses = {"invoking", "interruption-archiving"}
    elif return_code == 75:
        # provider-failed-ambiguous: retryable failure that staged artifacts.
        # provider-returned: the agent finished without publication (e.g. a
        # fail-closed carry-over); with no public side effect its staged
        # artifacts may archive so the same immutable prompt can re-run.
        allowed_statuses = {
            "provider-failed-ambiguous",
            "provider-returned",
            "interruption-archiving",
        }
    else:
        raise GenerationInvariant(
            "only bounded timeout/SIGINT/SIGTERM interruption or an "
            "ambiguous retryable provider failure can be archived"
        )
    resolved = _validate_boundary(run_dir, run_id, prompt_file)
    state_path = _state_path(resolved)
    with _lock(state_path):
        state = _load(state_path)
        attempts = state.get("attempts", [])
        if (
            state.get("run_id") != run_id
            or state.get("prompt_sha256") != file_sha256(prompt_file)
            or not isinstance(attempts, list)
            or not attempts
            or attempts[-1].get("status") not in allowed_statuses
            or state.get("status") not in allowed_statuses
        ):
            raise GenerationInvariant("generation interruption has no active attempt")
        if (resolved / "gates/publication-state.json").exists():
            raise GenerationInvariant("publication-state-exists")
        if _ledger_has_public_row(ledger, run_id):
            raise GenerationInvariant("ledger-row-exists")

        attempt = attempts[-1]
        archive_root = (
            resolved.parents[1]
            / "interrupted-generation"
            / run_id
            / f"attempt-{attempt['attempt']}"
        )
        if state.get("status") in {
            "invoking",
            "provider-failed-ambiguous",
            "provider-returned",
        }:
            observed = sorted(
                (
                    path
                    for path in resolved.rglob("*")
                    if (path.is_file() or path.is_symlink())
                    and not _is_allowed_prepublication(
                        str(path.relative_to(resolved))
                    )
                ),
                key=lambda path: str(path.relative_to(resolved)),
            )
            manifest: list[dict[str, str]] = []
            for path in observed:
                if path.is_symlink() or not path.is_file():
                    raise GenerationInvariant("interrupted artifact is not a regular file")
                manifest.append(
                    {
                        "path": str(path.relative_to(resolved)),
                        "sha256": file_sha256(path),
                    }
                )
            if state.get("status") == "provider-failed-ambiguous" and return_code == 75:
                attempt["provider_return_code"] = attempt.get("return_code")
            attempt.update(
                {
                    "status": "interruption-archiving",
                    "return_code": return_code,
                    "archive_root": str(archive_root),
                    "archive_manifest": manifest,
                }
            )
            state["status"] = "interruption-archiving"
            state["updated_at"] = utc_now()
            _atomic_write(state_path, state)
        else:
            if attempt.get("return_code") != return_code:
                raise GenerationInvariant("interruption return code changed")
            manifest = attempt.get("archive_manifest")
            if (
                not isinstance(manifest, list)
                or attempt.get("archive_root") != str(archive_root)
            ):
                raise GenerationInvariant("interruption archive journal is invalid")

        archive_root.mkdir(parents=True, exist_ok=True)
        for item in manifest:
            relative = Path(str(item.get("path", "")))
            if (
                not str(relative)
                or relative.is_absolute()
                or ".." in relative.parts
                or not isinstance(item.get("sha256"), str)
            ):
                raise GenerationInvariant("interruption archive entry is invalid")
            source = resolved / relative
            destination = archive_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.exists():
                if source.is_symlink() or not source.is_file():
                    raise GenerationInvariant("interrupted source changed type")
                if file_sha256(source) != item["sha256"]:
                    raise GenerationInvariant("interrupted source bytes changed")
                if destination.exists():
                    raise GenerationInvariant("interruption archive destination conflicts")
                os.replace(source, destination)
            if (
                not destination.is_file()
                or destination.is_symlink()
                or file_sha256(destination) != item["sha256"]
            ):
                raise GenerationInvariant("interruption archive verification failed")

        safe, reason = prepublication_empty(resolved, run_id, ledger)
        if not safe:
            raise GenerationInvariant(reason)
        finished = utc_now()
        attempt.update(
            {
                "finished_at": finished,
                "status": "interrupted-safe",
                "boundary": "archived-prepublication-artifacts",
            }
        )
        state["status"] = "interrupted-safe"
        state["updated_at"] = finished
        _atomic_write(state_path, state)
        # Keep a durable, hash-bound proof outside the prunable run directory.
        # The run state itself is useful during the next tick, but a retention
        # pass may remove it after the archive is complete; the archive proof
        # is what permits a safe new identity without guessing publication.
        _atomic_write(archive_root / "generation-state.json", state)
        _atomic_write(
            archive_root / "generation-exhaustion-receipt.json",
            {
                "schema": "writer.generation-exhaustion-receipt",
                "version": 1,
                "run_id": run_id,
                "attempt": attempt.get("attempt"),
                "status": "interrupted-safe",
                "return_code": return_code,
                "charged_attempts": _charged_attempt_count(state),
                "maximum_attempts": int(
                    state.get("maximum_attempts", MAX_GENERATION_ATTEMPTS)
                ),
                "state_sha256": file_sha256(archive_root / "generation-state.json"),
                "archive_manifest_sha256": manifest_sha256(manifest),
                "publication_state_absent": True,
                "public_ledger_rows": 0,
            },
        )
        return state


def resume_decision(
    run_dir: Path, run_id: str, prompt_file: Path, ledger: Path
) -> dict[str, Any]:
    try:
        resolved = _validate_boundary(run_dir, run_id, prompt_file)
        state_path = _state_path(resolved)
        if not state_path.exists():
            if _ledger_has_run(ledger, run_id):
                return {
                    "resumable": False,
                    "reason": "generation-ledger-row-exists",
                }
            safe, reason = prepublication_empty(resolved, run_id, ledger)
            return {
                "resumable": safe,
                "reason": reason,
                "status": "uninitialized-safe",
            }
        state = _load(state_path)
        if (
            state.get("run_id") != run_id
            or state.get("run_dir") != str(resolved)
            or state.get("prompt_path") != str(prompt_file.resolve(strict=True))
            or state.get("prompt_sha256") != file_sha256(prompt_file)
            or (
                state.get("status")
                not in {"provider-failed-safe", "interrupted-safe"}
                and not _failed_before_publication(state)
            )
        ):
            return {"resumable": False, "reason": "generation-state-not-safe"}
        attempts = state.get("attempts", [])
        maximum = int(
            state.get("maximum_attempts", MAX_GENERATION_ATTEMPTS)
        )
        if not isinstance(attempts, list) or _charged_attempt_count(state) >= maximum:
            return {
                "resumable": False,
                "reason": "generation-attempt-limit-exhausted",
            }
        safe, reason = prepublication_empty(resolved, run_id, ledger)
        return {
            "resumable": safe,
            "reason": reason,
            "status": state.get("status"),
        }
    except (OSError, ValueError, json.JSONDecodeError, GenerationInvariant) as error:
        return {"resumable": False, "reason": f"generation-state-invalid:{error}"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--prompt-file", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init")
    begin_parser = subparsers.add_parser("begin")
    begin_parser.add_argument("--owner-pid", type=int)
    result_parser = subparsers.add_parser("result")
    result_parser.add_argument("--return-code", required=True, type=int)
    interrupted_parser = subparsers.add_parser("archive-interrupted")
    interrupted_parser.add_argument("--return-code", required=True, type=int)
    orphan_parser = subparsers.add_parser("recover-orphan")
    orphan_parser.add_argument(
        "--minimum-age-seconds", type=int, default=60
    )
    subparsers.add_parser("resume-check")
    args = parser.parse_args()
    common = (args.run_dir, args.run_id, args.prompt_file, args.ledger)
    if args.command == "init":
        value = initialize(*common)
    elif args.command == "begin":
        value = begin(*common, owner_pid=args.owner_pid)
    elif args.command == "result":
        value = record_result(*common, args.return_code)
    elif args.command == "archive-interrupted":
        value = archive_interrupted(*common, args.return_code)
    elif args.command == "recover-orphan":
        value = recover_orphan(
            *common,
            minimum_age_seconds=args.minimum_age_seconds,
        )
    else:
        value = resume_decision(*common)
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    return 0 if args.command != "resume-check" or value["resumable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
