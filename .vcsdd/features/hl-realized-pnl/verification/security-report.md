# Security Hardening Report — hl-realized-pnl (Phase 5)

Scope: `skills/earn/hl-trade/lib/fills.py`, `skills/earn/hl-trade/lib/reconcile.py`,
`skills/earn/hl-trade/hl.py`, `skills/earn/run.sh`, `skills/_shared/lib/ledger.mjs` — the
feature's NEW/MODIFIED files per `specs/verification-architecture.md`'s file table. Worktree
`/Users/anicca/anicca/.worktrees/hl-realized-pnl`, branch `feature/hl-realized-pnl`, clean tree
before and after this sweep — no production files were modified.

## Tooling

| Tool | Version | Scope | Findings |
|---|---|---|---|
| `semgrep --config auto` | 1.168.0 | `fills.py`, `reconcile.py`, `hl.py` (290 rules) | 0 |
| `semgrep --config p/security-audit --config p/secrets` | 1.168.0 | above + `run.sh`, `ledger.mjs` (138 rules) | 0 |
| `bandit -r` | 1.9.4 (installed into a disposable scratch venv for this sweep, not the worktree) | `fills.py`, `reconcile.py`, `hl.py` | 9 (all Low severity / High confidence) |
| Manual checklist | — | subprocess-arg construction, path handling, flock TOCTOU, JSON-parse DoS, secret exposure | see below |

Raw output captured at:
- `verification/security-results/semgrep-auto.stderr.log` (human-readable) + `semgrep-auto.json`
- `verification/security-results/semgrep-security-audit.stderr.log` + `semgrep-security-audit.json`
- `verification/security-results/bandit-report.txt` (human-readable) + `bandit-report.json`

## Bandit findings (9, all Low/High)

| # | Rule | File:Line | Verdict |
|---|---|---|---|
| 1 | B404 subprocess import | `hl.py:25` | Accepted — subprocess is the documented, deliberate IPC mechanism to `resolve-identity.mjs`/`record.mjs`; pre-existing pattern, not introduced by this feature except for `reconcile.py`'s new call site (below). |
| 2 | B607 partial path (`"node"`) | `hl.py:50` | Accepted — pre-existing code (`_key()`), unmodified by this feature. `"node"` resolves via `$PATH`, matching every other `subprocess.run(["node", ...])` call already in this codebase (e.g. `record.mjs` invocations elsewhere); not attacker-influenceable (no env-var-controlled `PATH` hijack surface introduced here). |
| 3 | B603 subprocess without shell=True | `hl.py:50` | Accepted — `shell=True` is correctly AVOIDED (bandit flags the absence of shell as a call-out to double check, not a defect); args passed as a list, no shell metacharacter interpretation possible. |
| 4-6 | B110 try/except/pass (×3) | `hl.py:85`, `hl.py:110`, `hl.py:122` | Out of scope for this feature — these are in `cmd_market`/`cmd_open`, pre-existing code this feature does not touch (verification-architecture.md's file table lists only `cmd_close` and the new `cmd_reconcile` as hl.py changes). Noted for completeness, not a regression. |
| 7 | B404 subprocess import | `reconcile.py:25` | Accepted — same rationale as #1; this is the feature's own new file, and REQ-D1 *requires* routing the ledger mutation through `record.mjs` via subprocess (the alternative — reimplementing the identity-guard/HALT-check logic in Python — is explicitly forbidden by REQ-D1/PROP-015). Subprocess is the correct design, not a smell. |
| 8 | B607 partial path (`"node"`) | `reconcile.py:131` | Accepted — same rationale as #2; `_RECORD_MJS` is an absolute path built from `os.path.dirname(os.path.abspath(__file__))` (PROP-023-compliant, not a literal `/Users/...`), and `"node"` is resolved via `$PATH` consistently with the rest of the codebase's convention. |
| 9 | B603 subprocess without shell=True | `reconcile.py:131` | Accepted — same rationale as #3. **Verified no shell-injection surface**: `record_line`'s argv is `["node", _RECORD_MJS, json.dumps(payload), ledger_path]` — `payload` is JSON-encoded (so any attacker-influenced string inside it, e.g. a fill's `coin` field flowing into `task`, becomes an inert JSON string value, never shell-interpreted) and `ledger_path` is caller-supplied by `hl.py` from a fixed relative-to-`__file__` path, not from remote/API data. |

**Net verdict: 0 exploitable findings.** All 9 are the expected shape of "subprocess exists and
is used correctly" — bandit's low-severity blacklist rules fire on the mere presence of
`subprocess`/partial-path `"node"` regardless of whether shell-injection is actually reachable;
manual review (below) confirms none is reachable here.

## Manual checklist (tools above don't have targeted rules for these; reviewed by reading source)

1. **Subprocess-argument injection in `record_line`** (reconcile.py:111-121, called from
   `_build_payload` at reconcile.py:141-158): payload fields (`fill_tid`, `earn_usdc`,
   `cost_usdc`, `wallet`, `task`, `wake`) are serialized with `json.dumps(payload)` BEFORE being
   placed as a single argv element; `subprocess.run` is called with a list (no `shell=True`), so
   the OS never re-tokenizes or shell-expands the JSON string. Even a maximally adversarial
   `coin` value (fed into `task = f"hl-close {coin} tid={tid}".strip()`) can only ever land
   inside one JSON string field, not escape into a second shell command. **No injection
   possible.**
2. **Path traversal on checkpoint/lock paths**: `checkpoint_path` (`hl.py:155`,
   `os.path.join(here, ".last-fill-ts")`) and `lock_path` (`hl.py:156`, `checkpoint_path +
   ".lock"`) are both derived exclusively from `here = os.path.dirname(os.path.abspath(__file__))`
   — a fixed, non-attacker-controlled location. `ledger_path` (`hl.py:154`) can be overridden via
   the operator-supplied `--ledger` CLI flag, which is trusted operator input (same trust level
   as every other CLI arg in this tool, e.g. `--wake`), not remote/attacker input — there is no
   network-facing surface that feeds `--ledger`. **No traversal vector from an untrusted
   source.**
3. **`fcntl.flock` TOCTOU** (`acquire_lock`, reconcile.py:62-61): the pattern is `open()` then a
   single `fcntl.flock(fh.fileno(), LOCK_EX | LOCK_NB)` call — flock is atomic at the kernel
   level for a given open file descriptor; there is no separate "check-then-lock" step that a
   second process could race between. **No TOCTOU window.** (The lock file itself is created
   with `open(lock_path, "a+")`, which does not truncate/destroy any prior lock-file content —
   irrelevant here since the file's content is never read, only its existence + fd used for
   `flock`.)
4. **JSON-parse DoS** (`already_recorded_tids`, reconcile.py:90-108): reads the WHOLE ledger file
   into memory (`f.read()`) then `json.loads` per line inside a loop, catching `ValueError` per
   line (a single malformed line cannot abort the scan of the rest). Growth is bounded by the
   ledger file's own size (an append-only local file this same instance controls, not remote
   input) — this is the same complexity class as the pre-existing `readLedger` in `ledger.mjs`.
   No unbounded-recursion or decompression-bomb vector (plain JSONL, no nested-array amplification
   pattern is constructed by `_build_payload`). **No DoS vector beyond ordinary O(file-size)
   cost**, which the pre-existing ledger reader already accepts as its baseline.
5. **Secret/key exposure**: `reconcile.py` and `fills.py` never touch `_key()`/signing material
   at all — they receive an already-constructed `info` object from the caller (`hl.py`'s
   `_clients()`), matching REQ-D2/PROP-016. `record_line`'s `subprocess.run(..., capture_output=True,
   text=True, ...)` captures `record.mjs`'s stdout/stderr and returns them in a dict
   (`{"stdout": ..., "stderr": ...}`), which is never printed by `reconcile()` itself — only
   `cmd_reconcile` prints `json.dumps(result)`, where `result` is `reconcile()`'s own
   `{"status", "recorded"}` dict, NOT `record_line`'s return value (that return value is
   discarded by the caller at reconcile.py:200, only used to decide success/failure via the
   raised exception on non-zero exit). **No key material ever reaches a log line, print
   statement, or the ledger payload** (`_build_payload` builds only the REQ-C1 field set — no
   `PKVAR`/private-key field). Confirmed via `grep -n "PKVAR\|private\|_key(" skills/earn/hl-trade/lib/reconcile.py` → 0 matches.

## Summary

- **Total findings requiring a code change: 0.**
- semgrep (auto + security-audit + secrets rulesets, 428 total rule invocations across both
  runs): 0 findings.
- bandit: 9 findings, all Low-severity/High-confidence subprocess-presence flags; all reviewed
  and accepted as correct-by-design (REQ-D1 mandates the subprocess-to-record.mjs pattern; no
  shell-injection, path-traversal, TOCTOU, DoS, or secret-exposure vector is reachable through
  any of the 9 flagged lines).
- Manual checklist (5 items: subprocess injection, path traversal, flock TOCTOU, JSON-parse DoS,
  secret exposure): 0 exploitable findings, all independently re-derived from source rather than
  taken on faith from the static-grep unit tests alone.
