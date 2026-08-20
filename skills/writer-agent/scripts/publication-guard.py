#!/usr/bin/env python3
"""Mandatory publisher boundary around publication_resume + platform reality readback."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from publication_remote import probe
from publication_resume import (
    DORMANT_PAIRS,
    InvariantError,
    PublicationStore,
    SUPPORTED_PAIRS,
)


def store_from_env() -> PublicationStore:
    run_dir = os.environ.get("ARTICLE_RUN_DIR", "")
    state = os.environ.get("ARTICLE_PUBLICATION_STATE", "")
    ledger = os.environ.get("ARTICLE_LEDGER", "")
    if not run_dir or not state or not ledger:
        raise InvariantError(
            "ARTICLE_RUN_DIR, ARTICLE_PUBLICATION_STATE and ARTICLE_LEDGER are mandatory "
            "for managed publication"
        )
    store = PublicationStore(Path(state), Path(ledger))
    store.validate_managed_boundary(Path(run_dir))
    return store


def managed_article_context() -> bool:
    return any((
        os.environ.get("ARTICLE_AUTOPUBLISH") == "1",
        bool(os.environ.get("ARTICLE_RUN_DIR")),
        bool(os.environ.get("ARTICLE_PUBLISH_PAIR")),
        bool(os.environ.get("ARTICLE_PUBLICATION_STATE")),
        bool(os.environ.get("ARTICLE_LEDGER")),
    ))


def manual_or_store() -> PublicationStore | None:
    if not managed_article_context():
        return None
    return store_from_env()


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--pair", required=True, choices=SUPPORTED_PAIRS)
    preflight.add_argument("--target-kind", required=True)
    preflight.add_argument("--target", required=True)
    reconcile = sub.add_parser("reconcile")
    reconcile.add_argument("--pair", required=True, choices=SUPPORTED_PAIRS)
    query = sub.add_parser("query-target")
    query.add_argument("--pair", required=True, choices=SUPPORTED_PAIRS)
    register = sub.add_parser("register-intent")
    register.add_argument("--pair", required=True, choices=SUPPORTED_PAIRS)
    register.add_argument("--target-kind", required=True)
    register.add_argument("--target", required=True)
    dormant_skip = sub.add_parser("register-dormant-skip")
    dormant_skip.add_argument("--pair", required=True, choices=DORMANT_PAIRS)
    dormant_skip.add_argument("--reason", default="dormant-destination")
    correct = sub.add_parser("correct-protected-target")
    correct.add_argument(
        "--pair", required=True, choices=("x-article/ja",)
    )
    correct.add_argument("--target-kind", required=True)
    correct.add_argument("--target", required=True)
    correct.add_argument("--evidence-json", required=True)
    recover = sub.add_parser("recover-ambiguous")
    recover.add_argument(
        "--pair",
        required=True,
        choices=(
            "note/ja",
            "x-article/en",
            "x-article/ja",
            "x-post/ja",
            "devto/en",
            "substack/ja",
            "substack/en",
        ),
    )
    recover_unavailable = sub.add_parser("recover-unavailable")
    recover_unavailable.add_argument(
        "--pair",
        required=True,
        choices=("devto/en",),
    )
    stale_quality = sub.add_parser("recover-stale-quality")
    stale_quality.add_argument(
        "--pair",
        required=True,
        choices=("devto/en", "substack/ja", "substack/en"),
    )
    cleared = sub.add_parser("clear-unavailable")
    cleared.add_argument("--pair", required=True, choices=SUPPORTED_PAIRS)
    unavailable = sub.add_parser("mark-unavailable")
    unavailable.add_argument("--pair", required=True, choices=SUPPORTED_PAIRS)
    unavailable.add_argument("--reason", required=True)
    sub.add_parser("terminalize-invalid-x-post")
    sub.add_parser("plan")
    manual = sub.add_parser("manual-check")
    manual.add_argument("--pair", required=True, choices=SUPPORTED_PAIRS)
    args = parser.parse_args()
    store = manual_or_store()
    if store is None:
        result = {"action": "manual-unmanaged"}
    elif args.command == "manual-check":
        result = {"action": "managed", "pair": args.pair}
    elif args.command == "query-target":
        entry = store.read().get("pairs", {}).get(args.pair)
        result = {"found": bool(entry), "target": entry.get("target") if entry else None}
    elif args.command == "register-intent":
        result = store.register_intent(args.pair, args.target_kind, args.target)
    elif args.command == "register-dormant-skip":
        result = store.register_dormant_skip(args.pair, args.reason)
    elif args.command == "correct-protected-target":
        result = store.correct_protected_target(
            args.pair,
            args.target_kind,
            args.target,
            json.loads(args.evidence_json),
        )
    elif args.command == "recover-ambiguous":
        entry = store.read().get("pairs", {}).get(args.pair)
        if not entry:
            raise InvariantError(
                f"no persisted intent for {args.pair}"
            )
        result = store.recover_ambiguous_intent(
            args.pair,
            probe(args.pair, entry["target"], state=store.read()),
        )
    elif args.command == "recover-unavailable":
        entry = store.read().get("pairs", {}).get(args.pair)
        if not entry:
            raise InvariantError(
                f"no persisted intent for {args.pair}"
            )
        result = store.recover_unavailable_live(
            args.pair,
            probe(args.pair, entry["target"], state=store.read()),
        )
    elif args.command == "recover-stale-quality":
        result = store.recover_stale_quality_receipt(args.pair)
    elif args.command == "clear-unavailable":
        result = store.clear_unavailable(args.pair)
    elif args.command == "mark-unavailable":
        result = store.mark_unavailable(args.pair, args.reason)
    elif args.command == "terminalize-invalid-x-post":
        result = store.terminalize_invalid_x_post_length()
    elif args.command == "plan":
        result = store.plan()
    elif args.command == "preflight":
        if os.environ.get("ARTICLE_REMOTE_FIXTURE"):
            raise InvariantError("production remote fixture injection is forbidden")
        entry = store.read().get("pairs", {}).get(args.pair)
        if not entry:
            raise InvariantError(f"no pre-registered stable intent for {args.pair}")
        if entry.get("target_kind") != args.target_kind or entry.get("target") != args.target:
            raise InvariantError(f"preflight target does not match registered intent for {args.pair}")
        store.assert_ready(args.pair)
        result = store.guard(
            args.pair,
            probe(args.pair, entry["target"], state=store.read()),
        )
    else:
        entry = store.read().get("pairs", {}).get(args.pair)
        if not entry:
            raise InvariantError(f"no persisted intent for {args.pair}")
        result = store.guard(
            args.pair,
            probe(args.pair, entry["target"], state=store.read()),
        )
        if result.get("action") != "skip-live":
            raise InvariantError(f"remote reality is not live after publish for {args.pair}")
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except InvariantError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        raise SystemExit(2)
