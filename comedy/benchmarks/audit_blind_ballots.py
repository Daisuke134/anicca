#!/usr/bin/env python3
"""Audit offline position-balanced A/B ballots without manufacturing humor results.

Reviewers must see exactly one variant. 'human_declared' is an unverified
self-report; 'synthetic' ballots are tests, NEVER audience judgments.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCHEMA = "offline_counterbalanced_review_v1"
CHOICES = {"A", "B", "TIE"}
SOURCES = {"synthetic", "human_declared"}


def packet_sha256(packet: dict) -> str:
    raw = json.dumps(packet, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_packet(packet: dict) -> dict:
    if not isinstance(packet, dict) or packet.get("schema") != SCHEMA:
        raise ValueError("unsupported packet schema")
    if packet.get("task_set") != "original_development_not_fixed_benchmark":
        raise ValueError("not a rights-cleared development packet")
    if packet.get("publish_enabled") is not False or packet.get("auto_reply_enabled") is not False:
        raise ValueError("publishing must be OFF")
    if packet.get("review_status") != "NOT_MEASURED" or packet.get("human_judgments") != 0:
        raise ValueError("packets must be unrated")
    variants = packet.get("variants")
    if not isinstance(variants, dict) or set(variants) != {"v1", "v2"}:
        raise ValueError("exactly v1 and v2 required")
    indexed = {}
    for version, entries in variants.items():
        if not isinstance(entries, list) or not entries:
            raise ValueError("empty or invalid variant")
        by_id = {}
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("pair_id"), str) or not entry["pair_id"]:
                raise ValueError("invalid pair")
            pid = entry["pair_id"]
            if pid in by_id:
                raise ValueError("duplicate pair in variant")
            if any(k in entry for k in ("model", "run_id", "skill_blob_sha", "sample_index")):
                raise ValueError("blinding metadata leak")
            if not all(isinstance(entry.get(k), str) and entry[k].strip()
                       for k in ("prompt", "A", "B", "category")):
                raise ValueError("missing prompt, answer, or category")
            if entry["A"] == entry["B"]:
                raise ValueError("identical candidates")
            rating = entry.get("rating")
            if not isinstance(rating, dict) or rating.get("preferred") != "NOT_MEASURED":
                raise ValueError("ratings pre-filled")
            if set(rating.get("allowed", [])) != CHOICES:
                raise ValueError("invalid allowed choices")
            by_id[pid] = entry
        indexed[version] = by_id
    if set(indexed["v1"]) != set(indexed["v2"]):
        raise ValueError("variant task coverage mismatch")
    if packet.get("pairs") != len(indexed["v1"]) or packet.get("candidate_count") != 2 * len(indexed["v1"]):
        raise ValueError("packet counts mismatch")
    for pid, one in indexed["v1"].items():
        two = indexed["v2"][pid]
        if one["A"] != two["B"] or one["B"] != two["A"]:
            raise ValueError("variant candidate order must be exact inverse")
        if one["prompt"] != two["prompt"] or one["category"] != two["category"]:
            raise ValueError("variant task content mismatch")
    return indexed


def audit(packet: dict, ballots: list[dict]) -> dict:
    indexed = validate_packet(packet)
    if not isinstance(ballots, list):
        raise ValueError("ballots must be a list")
    fingerprint = packet_sha256(packet)
    raters = {}
    used = set()
    by_source = Counter()
    per_pair = defaultdict(lambda: {"v1_A": 0, "v1_B": 0, "TIE": 0,
                                   "human_v1": 0, "human_v2": 0})
    synthetic_v1, synthetic_v2 = 0, 0
    for ballot in ballots:
        if not isinstance(ballot, dict):
            raise ValueError("ballot must be an object")
        rater = ballot.get("rater_id")
        variant = ballot.get("variant")
        pid = ballot.get("pair_id")
        choice = ballot.get("preferred")
        source = ballot.get("source_type")
        if not isinstance(rater, str) or not rater.strip() or len(rater) > 128:
            raise ValueError("invalid pseudonymous rater_id")
        if variant not in indexed or pid not in indexed[variant] or choice not in CHOICES:
            raise ValueError("unknown variant/pair or invalid preference")
        if source not in SOURCES:
            raise ValueError("source_type must be synthetic or human_declared")
        if ballot.get("packet_sha256") != fingerprint:
            raise ValueError("stale or cross-run packet fingerprint")
        if rater in raters and raters[rater] != (variant, source):
            raise ValueError("one rater cannot view both variants or mix sources")
        raters[rater] = (variant, source)
        if (rater, pid) in used:
            raise ValueError("duplicate rater/pair judgment")
        used.add((rater, pid))
        by_source[source] += 1
        if source == "synthetic":
            if variant == "v1":
                synthetic_v1 += 1
            else:
                synthetic_v2 += 1
            continue  # synthetic votes never enter human preference counts
        values = per_pair[pid]
        values["human_" + variant] += 1
        if choice == "TIE":
            values["TIE"] += 1
        elif (variant == "v1" and choice == "A") or (variant == "v2" and choice == "B"):
            values["v1_A"] += 1
        else:
            values["v1_B"] += 1

    human = by_source["human_declared"]
    reviewed = sorted(indexed["v1"])
    counts = {pid: dict(per_pair[pid]) for pid in reviewed}
    fully_counterbalanced = sum(v["human_v1"] > 0 and v["human_v2"] > 0
                                for v in counts.values())
    return {
        "schema": "offline_blind_ballot_audit_v1",
        "packet_sha256": fingerprint,
        "original_development_not_fixed_benchmark": True,
        "integrity": "PASS",
        "total_ballots": len(ballots),
        "synthetic_ballots": by_source["synthetic"],
        "synthetic_variant_counts": {"v1": synthetic_v1, "v2": synthetic_v2},
        "human_declared_ballots": human,
        "human_status": ("NOT_MEASURED" if not human
                         else "SELF_REPORTED_HUMAN_UNVERIFIED"),
        "pairs_with_both_human_orderings": fully_counterbalanced,
        "pair_count": len(reviewed),
        "position_balance_status": ("NOT_MEASURED" if not human
                                    else "BOTH_ORDERS_PER_PAIR" if fully_counterbalanced == len(reviewed)
                                    else "INCOMPLETE"),
        "human_tallies_by_anonymous_v1_position": counts,
        "model_comparison": "NOT_ESTABLISHED",
        "audience_laughter": "NOT_MEASURED",
        "voice_repeatability": "NOT_MEASURED",
        "rear_audibility": "NOT_MEASURED",
        "phone_ai_comprehension": "NOT_MEASURED",
        "stage_human_reaction_effect": "NOT_MEASURED",
        "warning": "A/B votes are not audience laughter. Human-declared ballots are not independently verified. Never infer a model winner without source provenance and comparable model invocations.",
        "publish_enabled": False,
        "auto_reply_enabled": False,
    }


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON on line {lineno}") from exc
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packets", type=Path, required=True)
    parser.add_argument("--ballots", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit(json.loads(args.packets.read_text(encoding="utf-8")),
                       read_jsonl(args.ballots))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    except (ValueError, TypeError, OSError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Ballot integrity PASS, synthetic={report['synthetic_ballots']}, "
          f"human_declared={report['human_declared_ballots']}, "
          f"human_status={report['human_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
