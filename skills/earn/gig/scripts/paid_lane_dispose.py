#!/usr/bin/env python3
"""Give every open liability a disposition before the pass ends — spec §0.1.6 (P1a-7).

Bookkeeping, not judgement. Which action to take on a customer — ask, extend, cancel, end —
is the model's call. This records what was observably true when the pass finished, so that
"the loop did nothing" becomes "the loop did nothing because X, and here is X".

Why the typed codes matter more than the refusal itself: `no_artifact_yet` written 47 times
against the same project root is not a legitimate wait, it is a structural deadlock, and
`dead_refusals()` below is what turns that repetition into a defect report. A free-text
reason could never be counted — it would be indistinguishable from a shrug.

Precedence is deliberate. A readback outranks everything, because evidence that the buyer
can see something ends the question. Quota outranks artifact state, because with no model
call available the artifact was never going to be built this pass and blaming the project
root would misname the blocker. Only then does the artifact situation decide, and it
distinguishes two failures the old loop conflated: nothing was built (`no_artifact_yet`)
versus something was built and never sent (`awaiting_human_authority`). Calling the second
one "no artifact" is how a finished deliverable sits on disk while the customer waits.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, _HERE / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _has_artifact(project_root: str | None) -> bool:
    if not project_root:
        return False
    artifacts = Path(project_root) / "artifacts"
    return artifacts.is_dir() and any(artifacts.iterdir())


_NO_NEW_VERSION_NAME = "paid-work-no-new-version.json"


def _finished_build(evidence_dir: str | None, talkroom_id: str) -> str | None:
    """The blocker for a project that has nothing new to build, if the pass recorded one.

    validate-promote refuses to promote an artifact whose version is not newer than what the
    project already holds, which is correct — allowing it would let the same file be
    re-delivered as new. When that is why the build stopped, the refusal should say so
    instead of falling back to awaiting_human_authority: both leave the liability open, but
    only one names the real blocker, and dead_refusals is only useful if the code is true.
    """
    if not evidence_dir:
        return None
    for path in Path(evidence_dir).rglob(_NO_NEW_VERSION_NAME):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if str(record.get("talkroom_id") or "") not in ("", str(talkroom_id)):
            continue
        version = str(record.get("artifact_version") or "unknown")
        return f"artifact_version_not_newer_than_project_state:{version}"
    return None


def dispose(
    store: Path | str,
    *,
    pass_id: str,
    readbacks: dict[str, dict[str, Any]] | None = None,
    artifact_roots: dict[str, str] | None = None,
    quota_blocker: str | None = None,
    projects_root: str | None = None,
    evidence_dir: str | None = None,
) -> dict[str, Any]:
    """Close or refuse every liability this pass has not yet answered.

    Given `evidence_dir` and no explicit readbacks, the chain runs itself: what the pass
    observed in each paid room and what it reports having sent are both already on disk, so
    the caller does not have to assemble either. gig_pass.sh passes one flag instead of
    building JSON, which removes the place where the two could drift apart.
    """
    liability = _load("silence_liability")
    readbacks = readbacks or {}
    artifact_roots = artifact_roots or {}

    if evidence_dir and not readbacks:
        reader = _load("paid_lane_read_threads")
        decide = _load("paid_lane_readback")
        thread_states = reader.read_thread_states(evidence_dir)
        by_room = reader.read_intents(evidence_dir)
        # Intents arrive keyed by talkroom; liabilities are keyed by buyer message. Every
        # open liability in a room the pass spoke into inherits that room's intent.
        open_rows = liability.open_liabilities(Path(store))
        intents = {
            row["liability_key"]: by_room[str(row["talkroom_id"])]
            for row in open_rows
            if str(row.get("talkroom_id")) in by_room
        }
        readbacks = decide.decide_readbacks(
            open_rows, thread_states=thread_states, intents=intents
        )

    store = Path(store)
    pending = liability.undisposed(store, pass_id=pass_id)
    rows = {row["liability_key"]: row for row in liability.open_liabilities(store)}

    closed = 0
    refused = 0
    for key in pending:
        talkroom_id = rows.get(key, {}).get("talkroom_id") or key.split(":", 1)[0]
        readback = readbacks.get(key)

        if readback and readback.get("action") in liability.CLOSING_ACTIONS:
            liability.close(
                store,
                key,
                action=readback["action"],
                outbound_readback=readback,
                pass_id=pass_id,
            )
            closed += 1
            continue

        if readback:
            # Something was observed in the room but it carries no action we can name. That
            # is a collector problem, not a customer problem, and it must not be filed as
            # "no artifact" — that would blame the wrong thing forever.
            code, blocker = "buyer_message_unparsed", f"readback:{talkroom_id}"
        elif quota_blocker:
            code, blocker = "quota_exhausted", quota_blocker
        elif (finished := _finished_build(evidence_dir, talkroom_id)) is not None:
            code, blocker = "no_new_work_required", finished
        else:
            root = artifact_roots.get(str(talkroom_id))
            if root is None and projects_root:
                # Derived rather than passed in, so gig_pass.sh does not have to assemble a
                # JSON map of every open talkroom — a second place for the
                # ~/gig/projects/<talkroom_id> convention to drift out of sync. An explicit
                # root still wins, which is what the tests use.
                root = str(Path(projects_root) / str(talkroom_id))
            if _has_artifact(root):
                code, blocker = "awaiting_human_authority", f"{root}/artifacts"
            else:
                code, blocker = "no_artifact_yet", root or f"talkroom:{talkroom_id}"

        liability.refuse(store, key, code=code, blocker_id=blocker, pass_id=pass_id)
        refused += 1

    return {"disposed": closed + refused, "closed": closed, "refused": refused, "pass_id": pass_id}


def dead_refusals(store: Path | str, *, threshold: int = 10) -> list[dict[str, Any]]:
    """Refusal code plus blocker that has repeated without ever producing a close.

    Spec §0.1.6: a code that never resolves is a bug wearing the costume of a state. This is
    the mechanism that would have made `awaiting_human_authority` firing two dozen times
    legible as a defect instead of as patience.
    """
    store = Path(store)
    if not store.is_file():
        return []

    counts: dict[tuple[str, str, str], int] = {}
    closed_keys: set[str] = set()
    for line in store.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        key = event.get("liability_key")
        if event.get("event") == "closed":
            closed_keys.add(key)
        elif event.get("event") == "refused":
            counts[(key, event.get("code"), event.get("blocker_id"))] = (
                counts.get((key, event.get("code"), event.get("blocker_id")), 0) + 1
            )

    defects = []
    for (key, code, blocker), passes in sorted(counts.items(), key=lambda kv: -kv[1]):
        if key in closed_keys or passes < threshold:
            continue
        defects.append(
            {
                "liability_key": key,
                "code": code,
                "blocker_id": blocker,
                "passes": passes,
                "verdict": "this refusal has never resolved — treat it as a defect, not a state",
            }
        )
    return defects


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True)
    parser.add_argument("--pass-id", required=True)
    parser.add_argument("--readbacks", help="JSON object mapping liability_key to readback")
    parser.add_argument("--artifact-roots", help="JSON object mapping talkroom_id to project root")
    parser.add_argument("--quota-blocker", default=None)
    parser.add_argument(
        "--projects-root",
        default=str(Path.home() / "gig" / "projects"),
        help="where <talkroom_id>/artifacts lives, so the caller need not map it",
    )
    parser.add_argument(
        "--evidence-dir",
        default=None,
        help="this pass's evidence dir; observations and send manifests are read from it",
    )
    parser.add_argument("--dead-refusal-threshold", type=int, default=10)
    args = parser.parse_args(argv)

    result = dispose(
        args.store,
        pass_id=args.pass_id,
        readbacks=json.loads(args.readbacks) if args.readbacks else {},
        artifact_roots=json.loads(args.artifact_roots) if args.artifact_roots else {},
        quota_blocker=args.quota_blocker,
        projects_root=args.projects_root,
        evidence_dir=args.evidence_dir,
    )
    result["dead_refusals"] = dead_refusals(args.store, threshold=args.dead_refusal_threshold)
    print(json.dumps(result, ensure_ascii=False))
    # Zero even when everything was refused: a refusal is a valid outcome. The gate decides
    # whether the pass may end, and dead refusals are surfaced for the auditor to escalate.
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
