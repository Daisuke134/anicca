#!/usr/bin/env python3
"""Mandatory publisher boundary around publication_resume + platform reality readback."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from publication_remote import probe, x_post_effect_uncertain
from publication_resume import (
    DORMANT_PAIRS,
    InvariantError,
    PublicationStore,
    SUPPORTED_PAIRS,
)


def store_from_env(*, validate_boundary: bool = True) -> PublicationStore:
    run_dir = os.environ.get("ARTICLE_RUN_DIR", "")
    state = os.environ.get("ARTICLE_PUBLICATION_STATE", "")
    ledger = os.environ.get("ARTICLE_LEDGER", "")
    if not run_dir or not state or not ledger:
        raise InvariantError(
            "ARTICLE_RUN_DIR, ARTICLE_PUBLICATION_STATE and ARTICLE_LEDGER are mandatory "
            "for managed publication"
        )
    store = PublicationStore(Path(state), Path(ledger))
    if validate_boundary:
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
    quarantine_media = sub.add_parser("quarantine-missing-media")
    quarantine_media.add_argument(
        "--pair", required=True, choices=("x-article/ja", "x-article/en")
    )
    quarantine_media.add_argument("--reason", required=True)
    quarantine_identity = sub.add_parser("quarantine-identity-conflict")
    quarantine_identity.add_argument(
        "--pair", required=True, choices=("substack/en",)
    )
    sub.add_parser("terminalize-invalid-x-post")
    sub.add_parser("plan")
    manual = sub.add_parser("manual-check")
    manual.add_argument("--pair", required=True, choices=SUPPORTED_PAIRS)
    args = parser.parse_args()
    if args.command == "quarantine-identity-conflict":
        # This is the one migration command whose purpose is to repair the
        # legacy equal-identity boundary; the method itself performs the
        # canonical path/layout and remote-proof checks before writing state.
        store = store_from_env(validate_boundary=False)
    else:
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
    elif args.command == "quarantine-missing-media":
        state = store.read()
        entry = state.get("pairs", {}).get(args.pair)
        if not isinstance(entry, dict) or not entry.get("target"):
            raise InvariantError(f"no persisted target for {args.pair}")
        if entry.get("receipt") or entry.get("status") == "live":
            raise InvariantError(
                "missing-media quarantine refuses a receipt or live state"
            )
        if isinstance(entry.get("existing_publication"), dict):
            raise InvariantError(
                "missing-media quarantine refuses a protected publication"
            )
        if entry.get("target_kind") != "x-draft-url":
            raise InvariantError("missing-media quarantine requires an X draft URL")
        if x_post_effect_uncertain(state):
            raise InvariantError(
                "missing-media quarantine refuses uncertain X effect evidence"
            )
        language = args.pair.rsplit("/", 1)[1]
        journal_path = (
            Path(str(state.get("run_dir", "")))
            / "gates"
            / "x-inplace-repair"
            / language
            / "journal.json"
        )
        try:
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            journal = {}
        if isinstance(journal, dict) and (
            journal.get("browser_evidence")
            or journal.get("unpublish_evidence")
            or journal.get("phase") not in {None, "authorized"}
        ):
            raise InvariantError(
                "missing-media quarantine refuses prior X browser-effect evidence"
            )
        remote = probe(args.pair, str(entry["target"]), state=state)
        if not isinstance(remote, dict):
            raise InvariantError("missing-media quarantine received malformed remote proof")
        expected_identity = str(
            state.get("destination_identities", {}).get(args.pair, "")
        ).strip().lstrip("@")
        proof_fields = {
            "status": remote.get("status"),
            "verified": remote.get("verified"),
            "destination_identity": remote.get("destination_identity"),
            "identity_verified": remote.get("identity_verified"),
            "identity_source": remote.get("identity_source"),
            "source": remote.get("source"),
        }
        if not (
            expected_identity
            and remote.get("status") == "not-live"
            and remote.get("verified") is True
            and remote.get("destination_identity") == expected_identity
            and remote.get("identity_verified") is True
            and remote.get("identity_source") == "x-authenticated-edit-url"
            and remote.get("source") == "x-cdp-saved-article-editor"
        ):
            raise InvariantError(
                "missing-media quarantine requires an authenticated exact-editor "
                f"not-live proof: {json.dumps(proof_fields, sort_keys=True)}"
            )
        reason = (
            f"{args.reason}; authenticated exact-editor not-live proof="
            f"{json.dumps(proof_fields, sort_keys=True, separators=(',', ':'))}"
        )
        result = store.mark_unavailable(args.pair, reason)
    elif args.command == "quarantine-identity-conflict":
        entry = store.read().get("pairs", {}).get(args.pair)
        if not isinstance(entry, dict) or not entry.get("target"):
            raise InvariantError(f"no persisted target for {args.pair}")
        remote = probe(args.pair, str(entry["target"]), state=store.read())
        result = store.quarantine_identity_conflict(
            args.pair, str(entry["target"]), remote
        )
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
