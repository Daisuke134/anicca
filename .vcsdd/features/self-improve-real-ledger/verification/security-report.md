# Security Hardening Report

Feature: `self-improve-real-ledger` (VCSDD Phase 5, formal hardening)

## Tooling

| tool | version | install method | invocation |
|---|---|---|---|
| bandit | 1.9.4 | `python3 -m pip install --user bandit` (test/dev-tooling only, not a production dependency of any `requirements*.txt`) | `env -u ANICCA_HOME /Users/operator/.local/bin/python3 -m bandit lib/ledger_reader.py lib/gate_math.py lib/promotion_history.py lib/promote_gate.py lib/promote_gate_run.py lib/scope_guard.py evaluator.py tests/test_gate_math_property_fuzz.py -f txt` |
| semgrep | (Homebrew-installed, `--config auto`, 290 community rules) | pre-existing at `/opt/homebrew/bin/semgrep`, no install needed | `semgrep --config auto lib/ledger_reader.py lib/gate_math.py lib/promotion_history.py lib/promote_gate.py lib/promote_gate_run.py lib/scope_guard.py evaluator.py tests/test_gate_math_property_fuzz.py` |

Scanned files: every file this feature added or modified in `lib/` + `evaluator.py`, plus the new
property/fuzz test file added during this hardening pass (`tests/test_gate_math_property_fuzz.py`).

Raw output: `security-results/bandit-report.txt`, `security-results/semgrep-report.txt` (+
`security-results/semgrep-report.json` machine-readable form).

## Findings

### bandit — 35 Low-severity, 0 Medium, 0 High

| rule | count | location(s) | triage |
|---|---|---|---|
| B105 `hardcoded_password_string` | 6 | `evaluator.py:138,217,218,230`, `lib/promote_gate.py:53,54` | **False positive.** Bandit's naive heuristic flags any `"<key containing 'pass'>": False`/`True` dict-literal assignment (here, `"stage1_pass": False` / `"stage2_pass": False` / `"stage1_pass": True`) as a possible hardcoded password because the key name contains the substring `pass`. These are boolean gate-result fields (`stage1_pass`/`stage2_pass`), not credentials. No action needed. |
| B404 `blacklist` (subprocess import) | 2 | `lib/promote_gate_run.py:25`, `lib/promotion_history.py:11` | **Accepted risk, by design.** Both modules' own docstrings explicitly document "subprocess deliberately confined to THIS module" (mirroring `lib/promote.py`'s pre-existing convention). Required for `git rev-parse`/`git log` (read-only history queries) and the fresh adversary `claude` CLI invocation. |
| B607 `start_process_with_partial_path` | 2 | `lib/promote_gate_run.py:55` (`git rev-parse`), `lib/promotion_history.py:26` (`git log`) | **Accepted risk.** Both invoke the literal string `"git"`, resolved via the process `PATH` rather than an absolute path. Standard, low-risk practice for a well-known, PATH-stable binary in a dev/CI tooling context (not a network-facing service); `_invoke_adversary`'s own `claude` binary resolution (`_resolve_claude_bin`) already uses `shutil.which(...) or <absolute fallback>` for the higher-stakes LLM call, showing the codebase already applies the stricter pattern where it matters more. |
| B603 `subprocess_without_shell_equals_true` | 3 | `lib/promote_gate_run.py:55,177`, `lib/promotion_history.py:26` | **False positive / non-issue.** This rule fires on any `subprocess.run(list, ...)` regardless of `shell=`; all three call sites here pass a plain argv **list** (never a shell string), so there is no shell-injection surface — this is in fact the SAFE pattern the rule exists to steer people toward, bandit is just flagging subprocess-with-external-input generally (the `--grep=` value is a fixed module constant, `PROMOTION_COMMIT_MESSAGE_PREFIX`, not user input; the adversary prompt is passed via `input=` to stdin, never as a shell-interpolated argument, per that call site's own inline comment explaining exactly this choice). |
| B101 `assert_used` | 22 | `tests/test_gate_math_property_fuzz.py` (every `assert` in the new property/fuzz test file) | **Expected, no action.** `assert` is the correct and required idiom inside pytest test functions; this bandit rule exists to catch `assert` used for *production* runtime validation (which gets compiled away under `-O`), not test assertions. Zero non-test files in this scan have this finding. |

### semgrep — 0 findings

`semgrep --config auto` (290 Community-tier rules, python + multilang) ran clean across all 8
scanned files: **0 findings, 0 blocking.**

## Summary

**Total findings: 35** (bandit only; semgrep: 0). **Severity: 35 Low / 0 Medium / 0 High.** Every
finding was triaged individually above: 6 are bandit false-positives on boolean dict keys
containing the substring "pass", 22 are expected `assert` usage inside a pytest test file (not
production code), and 7 are accepted, by-design, argv-list (non-shell) `subprocess` usage for
read-only `git` queries and the already-safely-invoked adversary CLI call — all already documented
in the feature's own source comments/docstrings as deliberate, confined subprocess boundaries. No
finding requires a code change. No High or Medium severity issues were found by either tool.
