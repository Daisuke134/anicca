# Verification Architecture — clip-clawrouter-instance-provision (Phase 1b) — REV 5 (post iteration-3 FAIL: dropped broken genesis-loop registry path, hardened REQ-103 port validation)

## Purity boundary map

This feature is almost entirely WIRING (a single prompt-text update to `clip-cli.sh` — ★ NOT a
registry entry, per iteration-3 FIND-006: the registry/ClawRouter-genesis-loop path is confirmed
mechanically broken and dropped entirely ★) plus the downstream, agent-driven side effects that
wiring enables (account creation, file writes, browser launch) — genuinely impure, real-world side
effects by design. ★ No wallet work of any kind is in scope (2nd scope-pivot correction: ClawRouter
already has its own wallets; PROP-101 is VOID, see below) ★. There is no new pure decision logic to
extract; the ONLY pure-function surface this feature touches is verifying it did NOT accidentally
duplicate any of `clip-post-verify-hardening`'s existing pure functions (`reel_verify.py`'s 5
functions, `count_posts.py`'s `count_confirmed_posts`) — it must call them, never reimplement them,
exactly as that feature's own purity audit already established.

| Step | Purity | Verification method |
|---|---|---|
| claude-p prompt wiring (`clip-cli.sh`'s `STARTUP` string) | pure DOCUMENTATION/PROMPT edit (a text string) | REQ-102(a): real `diff` of the edited file |
| IG account creation (BY CLAUDE-P ITSELF, not this session) | impure (real network signup + real Gmail OTP read, executed by an independent headless `claude` process) | REQ-102(b): real live profile URL fetch, handle inequality check, AND confirmation the creating process was claude-p's own bounded pass (tool-call/cron output), not a hand-driven session |
| `clip-accounts-clawrouter.json` write | impure (file write) | REQ-103: JSON schema + port-uniqueness check (real `lsof`/curl scan) |
| CloakBrowser launch + login | impure (real subprocess + real browser + real network) | REQ-104: real account-guard check (same pattern as `post_reel.py:118`) |
| Path isolation demonstration | impure (real subprocess invocation of already-shipped, already-pure-audited code) | REQ-105: real `EARN_MODE=discover` run + before/after hash comparison of claude-p's own files |
| Genesis-loop env wiring | impure (real plist file edit + real `launchctl` reload) | REQ-106: real `plutil` before/after diff of `com.anicca.daemon.plist` + real launchctl reload, zero `.mjs` code change |
| Live E2E post | impure (real IG post + real independent re-verification) | REQ-107: mirrors `clip-post-verify-hardening` PROP-008(a) exactly — same method, new account |

No new pure functions are introduced by this feature. `reel_verify.py`/`count_posts.py`/
`self_heal.py`/`run.sh`/`monitor.sh`/`post_reel.py` are used AS-IS (imported/invoked, never
reimplemented) — this is directly checkable via `diff`/`git log` showing zero modifications to
those files from this feature's commits.

## Proof obligations

| ID | Requirement | Tier | Required (lean) | Verification method |
|---|---|---|---|---|
| PROP-101 | ★ VOID (2nd scope-pivot correction) — no new wallet is provisioned by this feature. ClawRouter's existing `~/.automaton/wallet.json` (EVM) and on-demand `ensure-solana-wallet.mjs` (Solana) are reused as-is if ever needed; the previously-generated `~/.cloak/clawrouter-clip-solana.json` has been deleted from disk. | n/a | false | n/a |
| PROP-102 | REQ-102 (claude-p-only prompt wiring, THEN agent-driven live account creation — ★ REDESIGNED after iteration-3 FIND-006/007: the registry.json/ClawRouter-genesis-loop path is confirmed mechanically broken (`resolveSkillPath()` hardcodes `<slot>/run.sh`, never reads `registry.slots[slot].entrypoint`) and DROPPED entirely ★) | 3 (real process-provenance check) | true | (a) `diff` of `clip-cli.sh`'s `STARTUP` string before/after shows the new self-provisioning instruction genuinely added; (b) trigger claude-p's own existing "run ONE pass now" mechanism against an `ANICCA_INSTANCE` with no ready account; fetch the new account's live public profile page (real browser navigation or HTTP HEAD to `instagram.com/<handle>/`), assert HTTP 200 / page renders, assert `<handle>` != `aiclipsvault`, profile icon non-default + bio non-empty per REQ-102's "COMPLETE account" bar; (c) claude-p's own tool-call/cron output for that pass is captured as evidence that the DECISION to invoke `ig-account-create`'s flow was the agent's own, not the main session's. |
| PROP-103 | REQ-103 (account file schema + port uniqueness + VALIDATION — ★ HARDENED after iteration-3 FIND-008: `run.sh:49`'s `x.get("port",9222)` silently defaults a missing port to Dais's own daily-driver port 9222, confirmed by direct read ★) | 1 (unit, JSON schema) + 3 (real port scan) | true | `json.load` the new file, assert exactly 1 entry with required keys (`handle`,`profile`,`port`,`lang`,`status`) AND assert `port` is present (not defaulted) and is neither `9222` nor `9223`; separately, real `lsof -i :<port>` (or curl liveness check) against ports 9222/9223/`<new-port>` confirming `<new-port>` was free BEFORE this feature bound it and is now correctly serving the NEW CloakBrowser instance (not colliding with 9222/9223). The validation step itself (per REQ-103's new explicit requirement) is checked by confirming it genuinely runs BEFORE `run.sh` is retried in `clip-cli.sh`'s updated STARTUP flow, not merely documented as a suggestion. |
| PROP-104 | REQ-104 (isolated browser login confirmed) | 3 (real CDP check) | true | Real `curl http://localhost:<new-port>/json/list` returns a page whose `url` contains `instagram.com/<handle>`; real CDP `evaluate` call confirms the account-guard's active-handle read equals `<handle>` (same JS/Python expression `post_reel.py:117-118` already uses — ★ CORRECTED after iteration-1 FIND-003, was cited as line 107 which is the wrong, unrelated check ★). |
| PROP-105 | REQ-105 (path isolation, real files) | 2/3 (integration, real subprocess) | true | Run real `ANICCA_INSTANCE=clawrouter EARN_MODE=discover bash run.sh` + `bash monitor.sh`; assert (via `echo`/print statements inserted temporarily or via reading `_instance_paths.sh`'s resolved values directly) that all 5 `CLIP_*` vars carry the `-clawrouter` suffix AND that claude-p's own 5 unsuffixed files' `mtime`/byte-content are IDENTICAL before and after this run (a real `md5`/`stat` before/after diff, not "no error seen"). Pre-existing debug/test artifacts from prior VCSDD sessions (e.g. `~/.cloak/clip-accounts-vcsdd-*.json`, `~/.openclaw/state/clip-earn-ledger-vcsdd-*.jsonl` — noted per iteration-1 FIND-004) are OUT OF SCOPE for this comparison; only claude-p's canonical unsuffixed 5 files are checked. |
| PROP-106 | REQ-106 (genesis-loop env wiring — REAL edit + reload, not just documentation — ★ REDESIGNED after iteration-1 FIND-001 ★) | 3 (real system-config check) | true | Real `plutil -convert xml1 -o - ~/Library/LaunchAgents/com.anicca.daemon.plist` output, BEFORE and AFTER the edit, showing `ANICCA_INSTANCE`/`clawrouter` genuinely added to the `EnvironmentVariables` dict; real `launchctl unload`+`load` (or `kickstart -k`) executed; real `launchctl list com.anicca.daemon` (or a probe of the reloaded process, e.g. reading `/proc`-equivalent env on macOS is restricted, so verification is via re-reading the reloaded plist + confirming the daemon process restarted — `RunAtLoad`+`KeepAlive` are both `true` per the real plist, so a fresh PID after reload is itself evidence of a genuine restart) confirming the daemon picked up the new plist. This is checked by a fresh-context adversary independently re-running the SAME `plutil` command against the SAME real file and confirming the new key is genuinely present (not fabricated in a report). ★ Note per iteration-2 FIND-005 (informational): a reload also re-triggers `anicca-daemon.sh`'s own startup sequence (self-update git-merge, skill rsync, idempotent ClawRouter + telemetry-poster restart) — independently confirmed safe (no lock file or fragile state that unload/load would disrupt; the script is already restart-idempotent), just worth knowing this happens as a side effect of the reload. ★ |
| PROP-107 | REQ-107 (live E2E post + independent verify + cleanup) | 3 (E2E, no-mock) | true | Mirrors `clip-post-verify-hardening` PROP-008(a)'s already-proven method exactly: real clip queued → real `EARN_MODE=execute bash run.sh` (with `ANICCA_INSTANCE=clawrouter`) → `outcome="published"` → SEPARATE fresh browser navigation independently confirms the new href is present on the new account's live profile → ledger confirms `status:"posted"` at the `-clawrouter`-suffixed ledger path → test post deleted afterward, re-confirmed via another fresh navigation, ledger annotated (identical pattern to the already-shipped precedent). |

## Verification tiers legend

- Tier 1: schema/file-content checks (no browser/network required for THIS specific assertion,
  though the artifact being checked was itself produced by a real network operation).
- Tier 2: real subprocess invocation of already-shipped, already-tested deterministic code
  (`run.sh`/`monitor.sh`), no new logic under test — the NEW thing being verified is that REAL
  provisioned data flows through correctly, not the logic itself (already proved by
  `clip-loop-dual-instance-earn` and `clip-post-verify-hardening`'s own test suites).
- Tier 3: real, live, no-mock verification against real external systems (real Instagram for
  account/post checks; real launchd/`plutil` state for the plist wiring) — executed by the main
  agent, per HARD RULE 0.24/0.31, mirroring the two-gate design (adversary reviews the
  documentation/citations; main agent runs the actual live checks — adversary has no browser
  access). No wallet-related verification applies (PROP-101 void).

## Gate

Phase 3 (adversarial review, fresh-context Sonnet-5) confirms: (a) REQ-102 through REQ-106 are
genuinely and specifically documented with real, checkable citations (file paths, line numbers,
command outputs) — not vague claims; (b) zero modification to any already-shipped file
(`_instance_paths.sh`, `run.sh`, `monitor.sh`, `self_heal.py`, `reel_verify.py`, `count_posts.py`,
`post_reel.py`, `runtime/loop/index.mjs`) — a real `git diff`/`diff` check; (c) no secret (IG
password, session cookie) is ever written in plaintext to any spec, task list, commit message, or
log file this feature produces — note: no wallet secret is ever in scope, per PROP-101 being void;
(d) REQ-102's account creation is genuinely traceable to the AGENT's own decision (a real tool-call
log / cron output), not the main session's hand-driven browser actions. PROP-107 (live E2E) is
executed by the MAIN AGENT after Phase 3 PASS, never by the adversary (no browser access) — same
two-gate split already established by `clip-post-verify-hardening`.
