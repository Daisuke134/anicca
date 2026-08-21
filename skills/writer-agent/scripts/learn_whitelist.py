#!/usr/bin/env python3
"""Learn a bounded proper-noun whitelist from completed bilingual articles."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from publication_resume import PublicationStore  # noqa: E402
from self_improve_control import (  # noqa: E402
    ensure_repo_synced,
    source_branch,
    update_deployed_commit,
)


TOKEN = re.compile(r"[A-Z][A-Za-z0-9.+-]{2,31}")


def shared_candidates(
    ja: str,
    en: str,
    *,
    existing: set[str],
) -> list[str]:
    ja_tokens = set(TOKEN.findall(ja))
    en_tokens = set(TOKEN.findall(en))
    return sorted(
        token
        for token in (ja_tokens & en_tokens) - existing
        if any(character.isupper() for character in token[1:])
        or any(character.isdigit() or character in ".+-" for character in token)
    )


def validate_whitelist(path: Path) -> list[str]:
    tokens = []
    for number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        1,
    ):
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        if TOKEN.fullmatch(value) is None:
            raise ValueError(
                f"invalid whitelist token on line {number}: {value!r}"
            )
        tokens.append(value)
    if len(tokens) != len(set(tokens)):
        raise ValueError("whitelist contains duplicate tokens")
    if tokens != sorted(tokens):
        raise ValueError("whitelist tokens must be sorted")
    return tokens


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    _atomic_text(
        path,
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _completed_sources(
    skill_dir: Path,
    state_dir: Path | None = None,
) -> list[tuple[str, str, str]]:
    state_root = Path(state_dir) if state_dir is not None else skill_dir / "state"
    ledger = state_root / "articles.jsonl"
    sources = []
    for state_path in sorted(
        state_root.glob("runs/*/gates/publication-state.json")
    ):
        store = PublicationStore(state_path, ledger)
        if store.completion_status() != "complete":
            continue
        state = store.read()
        ja_path = Path(str(state["drafts"]["ja"]["path"]))
        en_path = Path(str(state["drafts"]["en"]["path"]))
        sources.append(
            (
                str(state["run_id"]),
                ja_path.read_text(encoding="utf-8"),
                en_path.read_text(encoding="utf-8"),
            )
        )
    return sources


def _commit(repo: Path, whitelist: Path, count: int) -> str:
    relative = whitelist.resolve().relative_to(repo.resolve())
    status = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "status",
            "--porcelain",
            "--untracked-files=no",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    dirty = {line[3:] for line in status if len(line) > 3}
    if dirty not in ({str(relative)}, set()):
        raise RuntimeError(
            f"whitelist source has unrelated changes: {sorted(dirty)}"
        )
    subject = f"learn(article): add {count} verified whitelist tokens"
    if dirty:
        subprocess.run(
            ["git", "-C", str(repo), "add", "--", str(relative)],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "commit",
                "-m",
                subject,
                "--",
                str(relative),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    else:
        changed = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                "HEAD",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        actual_subject = subprocess.run(
            ["git", "-C", str(repo), "log", "-1", "--format=%s"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if changed != [str(relative)] or actual_subject != subject:
            raise RuntimeError(
                "whitelist recovery commit does not match prepared transition"
            )
    commit = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    branch = source_branch(repo)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "push",
            "origin",
            f"HEAD:refs/heads/{branch}",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    update_deployed_commit(repo, commit)
    return commit


def learn(
    skill_dir: Path,
    *,
    state_dir: Path | None = None,
    commit_changes: bool = True,
) -> dict[str, Any]:
    whitelist = skill_dir / "reference/language-whitelist.txt"
    state_root = Path(state_dir) if state_dir is not None else skill_dir / "state"
    receipt = state_root / "learning/whitelist-receipt.json"
    repo = skill_dir.parents[1]
    try:
        prior = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        prior = {}
    if (
        prior.get("status") in {"PREPARED", "APPLIED"}
        and not prior.get("source_commit")
        and prior.get("proposed_sha256") == _sha256(whitelist)
    ):
        prior["status"] = "APPLIED"
        _atomic_json(receipt, prior)
        if commit_changes:
            relative = str(
                whitelist.resolve().relative_to(repo.resolve())
            )
            ensure_repo_synced(
                repo,
                allowed_dirty={relative},
                allow_ahead=True,
            )
            prior["source_commit"] = _commit(
                repo,
                whitelist,
                len(prior.get("additions", [])),
            )
            _atomic_json(receipt, prior)
        return prior
    existing = set(validate_whitelist(whitelist))
    evidence: dict[str, list[str]] = {}
    for run_id, ja, en in _completed_sources(skill_dir, state_root):
        candidates = shared_candidates(ja, en, existing=existing)
        if candidates:
            evidence[run_id] = candidates
    additions = sorted(
        {
            token
            for candidates in evidence.values()
            for token in candidates
        }
    )[:10]
    result: dict[str, Any] = {
        "status": "UNCHANGED" if not additions else "PREPARED",
        "additions": additions,
        "evidence": evidence,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    if additions:
        if commit_changes:
            ensure_repo_synced(repo)
        values = sorted(existing | set(additions))
        content = (
            "# Evidence-bound proper nouns learned from completed JA/EN "
            "article pairs.\n"
            + "\n".join(values)
            + "\n"
        )
        result["proposed_sha256"] = hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()
        _atomic_json(receipt, result)
        proposed = whitelist.with_name(
            f".{whitelist.name}.{os.getpid()}.proposed"
        )
        try:
            _atomic_text(proposed, content)
            validate_whitelist(proposed)
            subprocess.run(
                [
                    "bash",
                    "-n",
                    str(skill_dir / "scripts/language-purity-gate.sh"),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            os.replace(proposed, whitelist)
        finally:
            proposed.unlink(missing_ok=True)
        result["status"] = "APPLIED"
        _atomic_json(receipt, result)
        if commit_changes:
            result["source_commit"] = _commit(
                repo,
                whitelist,
                len(additions),
            )
    _atomic_json(receipt, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-dir", type=Path, default=SCRIPTS.parent)
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=os.environ.get("ARTICLE_STATE_DIR"),
    )
    parser.add_argument(
        "--test-no-commit",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()
    state_root = Path(args.state_dir) if args.state_dir is not None else args.skill_dir / "state"
    lock_path = state_root / ".whitelist-learning.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with lock_path.open("a+") as lock:
            try:
                fcntl.flock(
                    lock.fileno(),
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
            except BlockingIOError:
                print('{"status":"LOCKED"}')
                return 0
            result = learn(
                args.skill_dir,
                state_dir=state_root,
                commit_changes=not args.test_no_commit,
            )
    except (
        OSError,
        ValueError,
        RuntimeError,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
    ) as error:
        print(f"whitelist learning pending: {error}", file=sys.stderr)
        return 75
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
