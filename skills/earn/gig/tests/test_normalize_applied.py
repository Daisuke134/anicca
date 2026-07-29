"""Tests for normalize_applied. Run: python3 tests/test_normalize_applied.py

The first case is the real row from 2026-07-27: a genuine application that no reader
counted because the agent wrote applied_at instead of ts and omitted status.
"""

import importlib.util
import json
import sys
import tempfile
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "normalize_applied.py"
spec = importlib.util.spec_from_file_location("normalize_applied", SCRIPT)
na = importlib.util.module_from_spec(spec)
spec.loader.exec_module(na)

FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  {detail}" if not ok else ""))
    if not ok:
        FAILURES.append(label)


NOW = 1_785_120_000.0

REAL_ROW = {
    "requestId": "5176621",
    "title": "Remotion動画生成｜AIへの指示書作成者募集",
    "applied_at": "2026-07-27",
    "price_proposed": 8000,
    "deliver_date": "2026-07-30",
}

# --- the row that started this -------------------------------------------------
fixed, changed = na.normalize([dict(REAL_ROW)], {"5176621"}, NOW)
check("a proven application gets status applied", fixed[0].get("status") == "applied",
      str(fixed[0]))
check("ts is derived from applied_at", bool(fixed[0].get("ts")), str(fixed[0].get("ts")))
check("the derived ts lands on the right day",
      time.strftime("%Y-%m-%d", time.localtime(fixed[0]["ts"])) == "2026-07-27",
      time.strftime("%Y-%m-%d", time.localtime(fixed[0]["ts"])))
check("one row changed", changed == 1, str(changed))

# --- the property that matters most: it cannot invent an application -----------
fixed, changed = na.normalize([dict(REAL_ROW)], set(), NOW)
check("without a submission screenshot, status is NOT filled in",
      "status" not in fixed[0], str(fixed[0]))
check("ts is still repaired even without proof", bool(fixed[0].get("ts")), str(fixed[0]))

fixed, _ = na.normalize([{"requestId": "9999", "applied_at": "2026-07-27"}], {"5176621"}, NOW)
check("proof for one request does not promote a different one",
      "status" not in fixed[0], str(fixed[0]))

# --- existing good rows are left alone ------------------------------------------
good = {"requestId": "111", "ts": 1785000000, "status": "applied"}
fixed, changed = na.normalize([dict(good)], {"111"}, NOW)
check("a well-formed row is untouched", fixed[0] == good and changed == 0, str(fixed[0]))

declined = {"requestId": "222", "ts": 1785000000, "status": "declined"}
fixed, _ = na.normalize([dict(declined)], {"222"}, NOW)
check("an existing status is never overwritten", fixed[0]["status"] == "declined",
      str(fixed[0]))

# --- malformed input survives ----------------------------------------------------
fixed, _ = na.normalize([{"_unparsed": "{broken"}], {"5176621"}, NOW)
check("a torn line is preserved, not dropped", fixed[0] == {"_unparsed": "{broken"},
      str(fixed[0]))

fixed, _ = na.normalize([{"requestId": "333", "applied_at": "not a date"}], {"333"}, NOW)
check("an unparseable date does not crash or fabricate a ts", "ts" not in fixed[0],
      str(fixed[0]))

# --- evidence discovery ----------------------------------------------------------
root = Path(tempfile.mkdtemp())
(root / "gig-72130-B2-5176621-submitted.png").write_bytes(b"x")
(root / "gig-72130-B2-5176621-confirm.png").write_bytes(b"x")
ids = na._evidence_ids(root)
check("only the submitted screenshot counts as proof", ids == {"5176621"}, str(ids))
check("a missing evidence dir yields no proof, not an error",
      na._evidence_ids(root / "nope") == set())

# --- end to end, on disk, idempotent ---------------------------------------------
work = Path(tempfile.mkdtemp())
ledger = work / "applied.jsonl"
ledger.write_text(json.dumps(REAL_ROW, ensure_ascii=False) + "\n", encoding="utf-8")
evidence = work / "evidence"
evidence.mkdir()
(evidence / "gig-1-B2-5176621-submitted.png").write_bytes(b"x")

sys.argv = ["x", "--ledger", str(ledger), "--evidence-root", str(evidence)]
na.main()
first = [json.loads(l) for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
check("the row on disk is now countable",
      first[0].get("status") == "applied" and first[0].get("ts"), str(first[0]))

na.main()
second = [json.loads(l) for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
check("a second run changes nothing", first == second, "row mutated on rerun")
check("no temp file is left behind", not list(ledger.parent.glob("*.tmp")),
      str(list(ledger.parent.glob("*.tmp"))))

print()
if FAILURES:
    print(f"{len(FAILURES)} failed: {FAILURES}")
    sys.exit(1)
print("all normalize_applied tests passed")
