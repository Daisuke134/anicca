"""RED phase — self-improve-real-ledger, Group RL-SAFE (money-safety restated and extended,
REQ-RL19/RL20/RL21).

Traces to behavioral-spec.md REQ-RL19 (finding F-5), REQ-RL20, REQ-RL21; verification-
architecture.md PROP-RL-SAFE1/SAFE2/SAFE3.

PROP-RL-SAFE1's superset+new-entries assertions and its F-5 executable bypass-reproduction are
EXPECTED TO FAIL at RED-phase time (the new entries are not yet in DENYLIST_MODULES). PROP-RL-
SAFE2/SAFE3 are static source-text scans that legitimately ALREADY PASS in the RED baseline
(nothing this feature adds exists yet to violate them) — disclosed explicitly, same category as
test_realized_gate.py's PROP-RL-EVAL2 (a permanent safety net, not a gap-proving test), per
sprint-1.md CRIT-004/CRIT-005.
"""
import os

from lib import gate_math, scope_guard

# Snapshot of scope_guard.DENYLIST_MODULES exactly as it reads BEFORE this feature's edit
# (committed as a literal fixture, per PROP-RL-SAFE1's documented method: "set-difference
# assertion against a snapshot of the pre-feature tuple").
PRE_FEATURE_DENYLIST_SNAPSHOT = (
    "ANICCA_SOLANA_PRIVATE_KEY",
    "ANICCA_EVM_PRIVATE_KEY",
    ".automaton/wallet.json",
    ".automaton/solana.json",
    ".blockrun/.solana-session",
    ".env",
    "ledger.mjs",
    "appendLedger",
    "isProfitable",
    "readLedger",
    "deriveLine",
    "SOL_TRADE_MAX_SPEND",
    "MAX_BET_SIZE",
    "MAX_PASS_SPEND",
    "POLY_MIN_ORDER",
    "openevolve-run.py",
    "config.yaml",
    "anicca-agent-economy",
    "place_order",
    "execute_swap",
    "subprocess",
    "socket",
    "urllib",
    "requests",
    "os.system",
)

# REQ-RL19's new entries, this feature's own harness-file/symbol names.
REQ_RL19_NEW_ENTRIES = (
    "ledger_reader",
    "is_profitable",  # Python snake_case symbol — distinct, under a substring scan, from
                       # the pre-existing JS camelCase "isProfitable" entry above.
    "resolve_ledger_path",
    "is_confirmed",
    "realized_summary",
    "promotion_history",
    "last_promotion_ts",
    "realized_gate",
)


def test_denylist_modules_is_strict_superset_of_pre_feature_snapshot():
    current = set(scope_guard.DENYLIST_MODULES)
    snapshot = set(PRE_FEATURE_DENYLIST_SNAPSHOT)

    assert snapshot.issubset(current), (
        f"pre-feature entries dropped/renamed: {snapshot - current} (INV-RL3: never shrink)"
    )


def test_denylist_modules_contains_every_req_rl19_new_entry():
    current = set(scope_guard.DENYLIST_MODULES)

    missing = [entry for entry in REQ_RL19_NEW_ENTRIES if entry not in current]

    assert missing == [], f"REQ-RL19 new entries not yet in DENYLIST_MODULES: {missing}"


def test_scan_denylisted_imports_catches_f5_bypass_direct_from_import():
    """F-5's exact bypass form: `from lib.ledger_reader import is_profitable` inside an
    EVOLVE-BLOCK. Must be caught once REQ-RL19's new entries land."""
    hits = gate_math.scan_denylisted_imports(
        "from lib.ledger_reader import is_profitable", scope_guard.DENYLIST_MODULES
    )
    assert hits != []


def test_scan_denylisted_imports_catches_f5_bypass_aliased_module_usage():
    """F-5's aliased-import bypass form: `import lib.ledger_reader as lr` then attribute usage."""
    hits = gate_math.scan_denylisted_imports(
        "import lib.ledger_reader as lr\nlr.is_profitable(row)", scope_guard.DENYLIST_MODULES
    )
    assert hits != []


# --- PROP-RL-SAFE2 (REQ-RL20): no new function writes to earn-ledger.jsonl ---
# Disclosed as an expected-pass static invariant (see module docstring) — mirrors the pre-existing
# PROP-SI-EV7 pattern this restates and extends to the Python-side reader.


def test_no_new_module_writes_to_earn_ledger_jsonl():
    self_improve_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    targets = [
        os.path.join(self_improve_dir, "lib", "ledger_reader.py"),
        os.path.join(self_improve_dir, "lib", "promotion_history.py"),
        os.path.join(self_improve_dir, "lib", "gate_math.py"),
    ]
    violations = []
    for path in targets:
        if not os.path.isfile(path):
            continue  # not created yet (e.g. promotion_history.py pre-Phase-2b) — nothing to scan
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        for line in text.splitlines():
            if ("open(" in line and ('"w"' in line or "'w'" in line or '"a"' in line or "'a'" in line)
                    and "earn-ledger" in line):
                violations.append((path, line))

    assert violations == [], f"REQ-RL20 violation (write to earn-ledger.jsonl): {violations}"


# --- PROP-RL-SAFE3 (REQ-RL21): no wallet-key reference in any file this feature touches ---
# Disclosed as an expected-pass static invariant (see module docstring), same category as SAFE2.

FORBIDDEN_KEY_REFERENCES = (
    "ANICCA_EVM_PRIVATE_KEY",
    "ANICCA_SOLANA_PRIVATE_KEY",
    ".automaton/wallet.json",
    ".automaton/solana.json",
    ".blockrun/.solana-session",
)


def test_no_wallet_key_reference_in_any_touched_file():
    # scope_guard.py is deliberately EXCLUDED: its DENYLIST_MODULES tuple is SUPPOSED to contain
    # these exact strings (that is the whole point of REQ-DL1/RL19's denylist) — that is a
    # declarative block-list entry, never a "read, resolve, or reference" of actual key material
    # REQ-RL21 prohibits. PROP-RL-SAFE1 (above) already covers scope_guard.py's own correctness.
    self_improve_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    targets = [
        os.path.join(self_improve_dir, "lib", "ledger_reader.py"),
        os.path.join(self_improve_dir, "lib", "gate_math.py"),
        os.path.join(self_improve_dir, "lib", "promote_gate.py"),
        os.path.join(self_improve_dir, "lib", "promote_gate_run.py"),
        os.path.join(self_improve_dir, "lib", "promotion_history.py"),
    ]
    violations = []
    for path in targets:
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        for forbidden in FORBIDDEN_KEY_REFERENCES:
            if forbidden in text:
                violations.append((path, forbidden))

    assert violations == [], f"REQ-RL21 violation (wallet-key reference): {violations}"
