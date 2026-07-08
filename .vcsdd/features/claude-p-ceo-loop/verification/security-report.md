# Security Hardening Report

## Feature: claude-p-ceo-loop | Phase: 5 | Date: 2026-07-08

## Tooling

| Tool | Availability | Used for | Result |
|---|---|---|---|
| `shellcheck` (Homebrew) | available | static analysis of `ceo-pass.sh`, `record-cost-event.sh`, `founder-loop.sh` | 0 findings (clean output on all 3) |
| `bash -n` | available | syntax check of the same 3 scripts | all 3 pass |
| `semgrep` (Homebrew, `--config auto` then `--config p/python`) | available | static security scan of `ceo/*.py` (8 tracked files) | 0 findings, 293 rules run, 0 errors (`--config auto` needed registry login for extra rules but the bundled/offline `p/python` ruleset ran cleanly and independently confirmed 0 findings) |
| live subprocess execution of `run_pass.py` | n/a (custom harness) | `CEO_AGENT_DECISIONS_JSON` injection/malformed-input probing (11 scenarios) | 4 crash scenarios (BLOCKING, see verification-report.md F3), 1 silent-gate-bypass scenario (BLOCKING, F4), rest handled safely — see log |
| live subprocess execution of `founder-loop.sh` | n/a (custom harness) | RC≠0 reachability re-check (PROP-CEO-022 style) with a corrupted `FOUNDER_LEDGER` forcing `RC=1` | PASS — CEO pass ran, `founder-loop.sh`'s own exit code preserved at `1` |
| `grep`/manual code read | n/a | secrets exposure, path-traversal, shell-injection, dangerous-builtin (`os.remove`/`shutil.rmtree`/`eval`/`exec`/`shell=True`/`os.system`), record-earn.mjs non-reference (REQ-CEO-072), deletion-code non-existence (REQ-CEO-033), LLM-judgment non-existence (REQ-CEO-061) | all clean, see Findings below |
| Wycheproof / cryptographic test vectors | not applicable | — | this feature performs no cryptography, no key handling, no signature verification of its own (the founder wallet / on-chain USDC verification lives in `record-earn.mjs`, explicitly out of scope and unmodified by this feature per REQ-CEO-070/072) — Wycheproof is not applicable here and is explicitly noted as such rather than silently skipped |

## Findings

### BLOCKING — see `verification-report.md` Findings F2/F3/F4 for full detail
The three BLOCKING findings below are integrity/availability defects reachable through
externally-influenced input surfaces (JSONL ledger files, the `CEO_AGENT_DECISIONS_JSON` env var, and
a not-yet-deployed range-config file), so they are restated here from a security-hardening lens:

1. **F2 — non-dict JSONL row crash (availability)**: any writer bug or hand-edit that appends a
   syntactically-valid-but-non-dict JSON line to `ceo-cost-events.jsonl` or a per-loop earn ledger
   crashes the entire WEEKLY pass (`AttributeError`, uncaught, no `try/except` in `run_pass.py`'s
   `main()`). This is a denial-of-service against the CEO's own weekly resource-allocation cycle, not
   an authentication/authorization bypass — but it means a single malformed line (accidental or
   otherwise) silently starves the whole company of a WEEKLY allocation pass with no mail alert (the
   crash happens before step 12's best-effort mail send is ever reached).
2. **F3 — `CEO_AGENT_DECISIONS_JSON` wrong-shape crash (availability)**: a file at the path named by
   this environment variable containing a JSON array, bare string, `null`, or a non-dict per-loop value
   crashes `run_pass.py` with an uncaught `AttributeError`. Live-reproduced with 4/11 adversarial
   scenarios (`security-results/ceo_agent_decisions_json_injection_probe.log`).
3. **F4 — allocation range-gate fail-open by default (integrity)**: with no `ceo-allocation-ranges.json`
   deployed (which is the shipped default — no writer for this file exists anywhere in the feature),
   `validate_allocation_ranges()` gates nothing. A negative or otherwise out-of-range allocation value
   proposed via `CEO_AGENT_DECISIONS_JSON` for a field that isn't specifically increase-gated
   (e.g. `fleet_size_target` on a decrease) is written to `loop-registry.json` unmodified. This
   contradicts the spec's own stated Non-functional constraint that allocation anomalies must be
   fail-closed.

### Injection surface analysis (PASS, no vulnerability found)
- **Command injection via `CEO_AGENT_DECISIONS_JSON` content**: probed with a `justification` field
  containing `$(rm -rf /tmp/pwned-marker-'; touch /tmp/pwned-marker-file'; echo done)`. The payload
  reaches `run_pass.py` purely as JSON string data (used only for a `ceo-escalations.jsonl` field and
  dict construction) and is never passed to a shell. Confirmed no marker file was created
  (`security-results/ceo_agent_decisions_json_injection_probe.log`, scenario
  `shell-metachar-in-justification`). Root cause of safety: every `subprocess.run(...)` call in
  `run_pass.py` (`_send_mail_best_effort`) passes a Python **list** of arguments, never `shell=True`;
  `record_cost_event_cli.py` similarly receives `sys.argv` positionally, never `eval`'d or interpolated
  into a shell string. `grep -rn "shell=True|os\.system|eval(|exec(" ceo/*.py ceo/*.sh` → 0 matches.
- **Path traversal via loop name**: probed `budget.build_cost_event(ts, "../../../etc/passwd", 1.0)` —
  the resulting dict's `loop` field is `"../../../etc/passwd"` as inert JSON *data*; it is never used
  as a filesystem path component anywhere in `budget.py`/`allocator.py`. `record_cost_event(path,
  event)` and `write_registry_atomic(path, registry)` both take their target `path` as a caller-supplied
  argument (fixed, not derived from any loop name), so a hostile loop name cannot redirect a write.
- **Shell script injection (`record-cost-event.sh`, `ceo-pass.sh`)**: `shellcheck` clean, `bash -n`
  clean, no `eval`, both scripts pass their arguments to `python3 <script> "$LOOP" "$USD_ESTIMATE"
  "$STATE_DIR"` as normal argv (quoted), never interpolated into a re-executed shell string. Note (INFO,
  not a code defect): the actual *call site* of `record-cost-event.sh` for 3 of the 6 in-scope loops
  (affiliate/gig/bounty) is a natural-language sentence inside each loop's own agent STARTUP prompt
  ("run bash ~/anicca/skills/self/founder-loop/ceo/record-cost-event.sh gig <your own best-effort USD
  cost estimate>") — the deterministic script itself is injection-safe, but the *decision* of what
  shell command to actually type is made by the acting LLM agent per this project's own
  agent-native/no-hardcoded-judgment design philosophy (`building-effective-ai-agents.md`); this is a
  deliberate architectural choice already accepted elsewhere in this codebase for all 6 loop CLIs
  (`loop-report.sh` is called the identical way), not a new gap introduced by this feature.
- **Secrets/credential exposure**: `grep -rniE "api_key|private_key|secret|password|mnemonic|0x[0-9a-f]{40}" ceo/*.py ceo/*.sh` → 0 matches. No wallet keys, API keys, or credentials appear anywhere in
  the `ceo/` module (the founder wallet address itself lives only in `founder-loop.sh`'s comments,
  unmodified by this feature, and in `record-earn.mjs`, out of scope).
- **`ceo-pass.log`/`ceo-cost-events.jsonl` contents**: spot-checked the live E2E log
  (`security-results/founder_loop_rc_nonzero_ceo_pass_still_runs.log`) — no secrets, only
  operational data (timestamps, loop names, budget/allocation numbers).

### Deletion / content-judgment / ledger-writer non-reference checks (all PASS)
- REQ-CEO-033 (no deletion code): `grep -rniE "os\.remove|shutil\.rmtree|unlink" ceo/*.py` → 0 matches.
- REQ-CEO-061 (no LLM/content-judgment code): `grep -rniE "llm|claude --model|anthropic\." ceo/*.py` → 0
  matches.
- REQ-CEO-072 (`record-earn.mjs` never imported/called by the CEO): `grep -rl "record-earn"
  ceo/*.py ceo/*.sh` → 4 hits, all confirmed by manual read to be docstring/comment prose describing
  the *pattern* being reused ("same atomic-write pattern as record-earn.mjs"), zero actual
  import/require/subprocess-call sites.
- `founder-loop.sh` diff vs pre-feature `main`: 8 lines added (`git diff main -- founder-loop.sh`),
  insertion is a single `bash "$HERE/ceo/ceo-pass.sh" || true` placed immediately before
  `exit "$RC"`, with `$RECORD`/`$LEDGER`/the money-wake block completely untouched — REQ-CEO-070
  compliant, `|| true` guarantees `ceo-pass.sh`'s own exit status can never change `$RC`.
- Live re-check (fresh evidence, not merely a diff read): `founder-loop.sh` run with `FOUNDER_TEST=1`
  and a deliberately-corrupted `FOUNDER_LEDGER` (invalid JSON) forced `RC=1` via the harness's own
  `LEDGER UNREADABLE` fail-safe. `ceo/ceo-pass.sh` still ran (its own marker line is present in
  `ceo-pass.log`), the full WEEKLY sequence completed (`loop-registry.json`, `ceo-verification.jsonl`,
  `ceo-bandit-state.json`, `ceo-budget-pacer-state.json`, `ceo-rollback.json`, `ceo-miss-streak.json`
  all freshly written), and `founder-loop.sh`'s own final exit code was `1` — matching the forced `$RC`,
  confirming INV-H6 is preserved even with a live CEO-pass side effect in between.
  Full log: `security-results/founder_loop_rc_nonzero_ceo_pass_still_runs.log`.

### `loop-registry.json` single-write-point / no shared-mutable-accumulator (INV-CEO-2, PASS)
`grep -rn "loop-registry.json" ceo/*.py` shows the only `open(...)` call that targets this path is
inside `allocator.write_registry_atomic`, and `run_pass.py` calls that function exactly once (step 9).
`grep -rn "registry_updates" ceo/*.py` → 0 matches (the B9 accumulator-removal fix holds).

## Summary
- Tools attempted: shellcheck, bash -n, semgrep (auto + p/python), live subprocess injection probing,
  manual grep-based static review. All ran successfully; none were unavailable.
- Raw results: `verification/security-results/ceo_agent_decisions_json_injection_probe.log`,
  `verification/security-results/founder_loop_rc_nonzero_ceo_pass_still_runs.log`,
  `verification/security-results/run_injection_probe.sh` (the probe script itself),
  `verification/security-results/semgrep_ceo_dir.json` (0 findings), `verification/proof-harnesses/adversarial_boundary_probe.output.log`.
- Findings: **3 BLOCKING** (F2 non-dict-row crash / availability, F3 `CEO_AGENT_DECISIONS_JSON`
  wrong-shape crash / availability, F4 allocation range-gate fail-open-by-default / integrity — all
  three detailed in `verification-report.md`), **0 command-injection / path-traversal / secrets-leak /
  shell-injection vulnerabilities found** (all actively probed, all clean).
- Cryptographic checks (Wycheproof or equivalent): **not applicable** — this feature has no
  cryptographic surface of its own; on-chain wallet verification is entirely delegated to
  `record-earn.mjs`, which is out of scope and unmodified.
