"""scope_guard.py — the SOLE structural enforcement of REQ-DL1's denylist and the EVOLVE-BLOCK
scope boundary (INV-3).

openevolve itself provides NO enforcement of this boundary — verified directly against the real
algorithmicsuperintelligence/openevolve source (behavioral-spec.md "Scope of the strategy
program"): `controller.py::_load_initial_program()` reads the WHOLE file; `prompt/templates.py`
shows the LLM the ENTIRE `current_program` with no marker-respecting instruction; the diff path's
`apply_diff()` matches against the whole `parent.code`; full-rewrite mode sets
`child_code = new_code` (the entire file, zero scoping); `parse_evolve_blocks()` exists but is
dead code, never called from the real generation/evaluation path. `# EVOLVE-BLOCK-START/END`
markers are therefore an LLM-facing PROMPT CONVENTION ONLY, never a technical boundary.

100% of the actual enforcement is THIS module, operating on the ACTUAL resulting candidate file
text (`child_code`), compared against the frozen baseline file — never a defensive second check on
top of any openevolve-native guarantee, because none exists.

Public entrypoint: check(candidate_code, baseline_code) -> (ok: bool, reason: str).
"""
from __future__ import annotations

import hashlib
from typing import Tuple

from lib import gate_math

# REQ-DL1 denylist — kept verbatim in sync with behavioral-spec.md REQ-DL1 (PROP-SI-DL1 asserts
# this list matches the spec). Wallet private keys/files, any .env file, the ledger-write module
# and its exported functions, spend-cap constants, the harness/runner's own files, and the
# separate anicca-agent-economy feature's ownership. Also covers the concrete
# order-execution/network/subprocess surface REQ-RH3/EV7 require to be unreachable from the
# EVOLVE-BLOCK.
DENYLIST_MODULES = (
    # wallet private keys / key files (resolve-identity.mjs's documented resolution order)
    "ANICCA_SOLANA_PRIVATE_KEY",
    "ANICCA_EVM_PRIVATE_KEY",
    ".automaton/wallet.json",
    ".automaton/solana.json",
    ".blockrun/.solana-session",
    # any .env file
    ".env",
    # ledger-write path (skills/_shared/lib/ledger.mjs) and its exported symbols
    "ledger.mjs",
    "appendLedger",
    "isProfitable",
    "readLedger",
    "deriveLine",
    # spend caps / money-safety constants (mirrors genome.mjs::FORBIDDEN_CAP_KEYS)
    "SOL_TRADE_MAX_SPEND",
    "MAX_BET_SIZE",
    "MAX_PASS_SPEND",
    "POLY_MIN_ORDER",
    # the harness/runner itself
    "openevolve-run.py",
    "config.yaml",
    # a separate feature's ownership — never touched by this feature's tooling
    "anicca-agent-economy",
    # live order-execution / network / process-spawn surface (REQ-RH3, REQ-EV7)
    "place_order",
    "execute_swap",
    "subprocess",
    "socket",
    "urllib",
    "requests",
    "os.system",
)


def compute_checksum(text: str) -> str:
    """Effectful only in the sense that hashing is a computation over externally-sourced text;
    deterministic and side-effect-free itself. Actual file reads happen in the caller."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fixed_region_text(code_text: str, evolve_range: Tuple[int, int]) -> str:
    """Fixed-region text = every line strictly before START and strictly after END, using the
    given file's OWN marker range. Used for the REQ-DL3 checksum pre-check (a fast hash-based
    corroboration of the same fixed-region text REQ-DL2's diff_in_scope compares in full)."""
    lines = code_text.splitlines()
    start, end = evolve_range
    prefix = lines[: start - 1]
    suffix = lines[end:]
    return "\n".join(prefix + suffix)


def check(candidate_code: str, baseline_code: str) -> Tuple[bool, str]:
    """The full REQ-DL2 (diff-scope) -> REQ-DL3 (checksum) -> REQ-DL4 (import-scan) check chain,
    in order, fail-closed on the first violation. Returns (ok, reason).

    `candidate_code` MUST be the ACTUAL resulting file text (child_code) — whether openevolve
    produced it via diff-based `apply_diff()` or full-rewrite `child_code = new_code` — never the
    LLM's raw diff/SEARCH-REPLACE text, which is not even a line-scoped object in full-rewrite
    mode.
    """
    base_lines = baseline_code.splitlines()
    baseline_markers = gate_math.marker_lines(base_lines)
    if baseline_markers is None:
        # The frozen baseline itself must have exactly one well-formed EVOLVE-BLOCK pair. If it
        # doesn't, nothing can be safely evaluated — fail closed rather than guess a boundary.
        return False, "baseline-malformed-evolve-block"

    # REQ-DL2: whole-file diff-scope check (handles the block legitimately growing/shrinking).
    diff_result = gate_math.diff_in_scope(candidate_code, baseline_code, baseline_markers)
    if not diff_result.in_scope:
        return False, f"out-of-scope-edit: lines {diff_result.out_of_scope_lines} differ outside EVOLVE-BLOCK"

    # REQ-DL3: fixed-region checksum, a fast pre-check over the same fixed-region text REQ-DL2
    # just diffed in full. By construction this can only mismatch if diff_in_scope's own line
    # comparison missed something (defense-in-depth, not a redundant no-op: it is a genuinely
    # independent computation path over the same inputs).
    cand_markers = gate_math.marker_lines(candidate_code.splitlines())
    # cand_markers is guaranteed non-None here: diff_in_scope already returned in_scope=True,
    # which is only possible when marker_lines(candidate) succeeded.
    before_hash = compute_checksum(_fixed_region_text(baseline_code, baseline_markers))
    after_hash = compute_checksum(_fixed_region_text(candidate_code, cand_markers))
    if not gate_math.checksums_match(before_hash, after_hash):
        return False, "fixed-region-checksum-mismatch"

    # REQ-DL4: static import/path scan of the EVOLVE-BLOCK content only (candidate's own marker
    # positions — the block may have grown/shrunk relative to baseline).
    cand_lines = candidate_code.splitlines()
    c_start, c_end = cand_markers
    block_text = "\n".join(cand_lines[c_start - 1 : c_end])
    hits = gate_math.scan_denylisted_imports(block_text, DENYLIST_MODULES)
    if hits:
        return False, f"denylisted-reference-in-evolve-block: {hits}"

    return True, "scope-guard-pass"
