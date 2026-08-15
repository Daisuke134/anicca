from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


# Measured 2026-08-06: eight consecutive passes inspected only 69 unique jobs, 49 of them
# repeatedly, and two consecutive passes overlapped on 30 of 35. Every pass burned its
# 40-slot inspection batch on the same listings and confirmed nothing:
#
#     ineligible 30-35 / submission_* 2-4 / confirmed 0     (ten passes running)
#
# ~25 of those ineligibles were 既応募. The collector DOES exclude already-applied ids, but
# it builds that set from the site's applied-offers page, which is walked one page deep --
# 20 rows. The durable ledger holds 354. So every application older than the last 20 was
# invisible to the exclusion, got re-inspected hourly, and crowded out fresh work.

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load():
    spec = importlib.util.spec_from_file_location(
        "application_parent_ledger_exclusion", SCRIPTS / "application_parent.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_ledger(path: Path, ids) -> None:
    path.write_text(
        "".join(json.dumps({"requestId": i, "status": "applied"}) + "\n" for i in ids),
        encoding="utf-8",
    )


def test_the_ledger_supplies_ids_the_first_page_cannot_show(tmp_path) -> None:
    m = load()
    ledger = tmp_path / "applied.jsonl"
    write_ledger(ledger, [str(91000013 + n) for n in range(354)])
    assert len(m.ledger_applied_ids(ledger)) == 354
    assert "91000013" in m.ledger_applied_ids(ledger)


def test_a_missing_ledger_is_empty_not_an_error(tmp_path) -> None:
    # This runs before every snapshot. A missing or half-written ledger must never take the
    # apply lane down -- it just means the site readback is the only exclusion this pass.
    m = load()
    assert m.ledger_applied_ids(tmp_path / "absent.jsonl") == set()


def test_a_corrupt_line_is_skipped_and_the_rest_still_count(tmp_path) -> None:
    m = load()
    ledger = tmp_path / "applied.jsonl"
    ledger.write_text(
        json.dumps({"requestId": "111"}) + "\nnot json\n" + json.dumps({"request_id": "222"}) + "\n",
        encoding="utf-8",
    )
    assert m.ledger_applied_ids(ledger) == {"111", "222"}


def test_the_effects_exclusion_is_the_union_of_site_and_ledger(tmp_path) -> None:
    # The site page is authoritative for what Coconala currently shows; the ledger is
    # authoritative for what we have ever sent. Neither alone is the full set.
    m = load()
    ledger = tmp_path / "applied.jsonl"
    write_ledger(ledger, ["900", "901"])
    effects = m.CdpParentEffects(
        ws_url="ws://127.0.0.1:9222/devtools/page/T",
        evidence_dir=tmp_path / "evidence",
        ledger_path=ledger,
        pass_id="exclusion-test",
    )
    effects.official_ids_for_snapshot = lambda: ["100", "101"]  # site page 1
    assert set(effects.applied_ids_for_exclusion()) == {"100", "101", "900", "901"}


def test_non_decimal_ids_exclude_but_never_enter_the_snapshot(tmp_path) -> None:
    # The ledger holds 31 non-decimal identities (dm-9978615 and friends: direct-message
    # threads, not 募集). They must still suppress re-inspection, but the snapshot contract
    # requires decimal request ids -- feeding them through produced
    # request_id_must_be_decimal at application_snapshot.py:73 and killed the whole lane.
    m = load()
    ledger = tmp_path / "applied.jsonl"
    ledger.write_text(
        json.dumps({"requestId": "91000085"}) + "\n" + json.dumps({"requestId": "dm-9978615"}) + "\n",
        encoding="utf-8",
    )
    effects = m.CdpParentEffects(
        ws_url="ws://127.0.0.1:9222/devtools/page/T",
        evidence_dir=tmp_path / "evidence",
        ledger_path=ledger,
        pass_id="decimal-test",
    )
    effects.official_ids_for_snapshot = lambda: []
    # Exclusion keeps everything: a dm thread we already answered is not fresh work.
    assert set(effects.applied_ids_for_exclusion()) == {"91000085", "dm-9978615"}
    # The snapshot field keeps only what its contract accepts.
    assert m.snapshot_applied_ids(effects.applied_ids_for_exclusion()) == ["91000085"]


def test_exclusion_survives_a_site_readback_failure(tmp_path) -> None:
    # If the site read fails the lane must still avoid re-applying to everything we have
    # already sent, rather than inspecting 354 duplicates.
    m = load()
    ledger = tmp_path / "applied.jsonl"
    write_ledger(ledger, ["900"])
    effects = m.CdpParentEffects(
        ws_url="ws://127.0.0.1:9222/devtools/page/T",
        evidence_dir=tmp_path / "evidence",
        ledger_path=ledger,
        pass_id="exclusion-test",
    )

    def boom():
        raise RuntimeError("cdp gone")

    effects.official_ids_for_snapshot = boom
    assert set(effects.applied_ids_for_exclusion()) == {"900"}
