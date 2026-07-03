# Verification Architecture — clip-clawrouter-instance-provision (Phase 1b) — REV 1

## Purity boundary map

This feature is almost entirely PROVISIONING (wallet generation, account creation, file writes,
browser launch) — genuinely impure, real-world side effects by design (a real wallet must exist, a
real IG account must exist). There is no new pure decision logic to extract; the ONLY pure-function
surface this feature touches is verifying it did NOT accidentally duplicate any of
`clip-post-verify-hardening`'s existing pure functions (`reel_verify.py`'s 5 functions,
`count_posts.py`'s `count_confirmed_posts`) — it must call them, never reimplement them, exactly as
that feature's own purity audit already established.

| Step | Purity | Verification method |
|---|---|---|
| Wallet keypair generation | impure (real crypto RNG + file write) | REQ-101: direct pubkey inequality check against `myclaude-solana.json` |
| IG account creation | impure (real network signup + real Gmail OTP read) | REQ-102: real live profile URL fetch, handle inequality check |
| `clip-accounts-clawrouter.json` write | impure (file write) | REQ-103: JSON schema + port-uniqueness check (real `lsof`/curl scan) |
| CloakBrowser launch + login | impure (real subprocess + real browser + real network) | REQ-104: real account-guard check (same pattern as `post_reel.py:107`) |
| Path isolation demonstration | impure (real subprocess invocation of already-shipped, already-pure-audited code) | REQ-105: real `EARN_MODE=discover` run + before/after hash comparison of claude-p's own files |
| Genesis-loop env wiring | pure DOCUMENTATION (no code change) | REQ-106: cite exact file+line read during implementation |
| Live E2E post | impure (real IG post + real independent re-verification) | REQ-107: mirrors `clip-post-verify-hardening` PROP-008(a) exactly — same method, new account |

No new pure functions are introduced by this feature. `reel_verify.py`/`count_posts.py`/
`self_heal.py`/`run.sh`/`monitor.sh`/`post_reel.py` are used AS-IS (imported/invoked, never
reimplemented) — this is directly checkable via `diff`/`git log` showing zero modifications to
those files from this feature's commits.

## Proof obligations

| ID | Requirement | Tier | Required (lean) | Verification method |
|---|---|---|---|---|
| PROP-101 | REQ-101 (new distinct wallet) | 3 (real artifact check) | true | Read both `~/.cloak/myclaude-solana.json` and the new `~/.cloak/clawrouter-clip-solana.json`, assert `pubkey` fields are non-empty strings and NOT equal. Assert `chmod 600` via `stat`. |
| PROP-102 | REQ-102 (new distinct live IG account) | 3 (real network check) | true | Fetch the new account's live public profile page (e.g. via a real browser navigation or a public HTTP HEAD to `instagram.com/<handle>/`), assert HTTP 200 / page renders, assert `<handle>` != `aiclipsvault`. Assert profile icon is non-default (not IG's grey silhouette placeholder) and bio is non-empty, per REQ-102's "COMPLETE account" bar. |
| PROP-103 | REQ-103 (account file schema + port uniqueness) | 1 (unit, JSON schema) + 3 (real port scan) | true | `json.load` the new file, assert exactly 1 entry with required keys; separately, real `lsof -i :<port>` (or curl liveness check) against ports 9222/9223/`<new-port>` confirming `<new-port>` was free BEFORE this feature bound it and is now correctly serving the NEW CloakBrowser instance (not colliding with 9222/9223). |
| PROP-104 | REQ-104 (isolated browser login confirmed) | 3 (real CDP check) | true | Real `curl http://localhost:<new-port>/json/list` returns a page whose `url` contains `instagram.com/<handle>`; real CDP `evaluate` call confirms the account-guard's active-handle read equals `<handle>` (same JS expression `post_reel.py:107` already uses). |
| PROP-105 | REQ-105 (path isolation, real files) | 2/3 (integration, real subprocess) | true | Run real `ANICCA_INSTANCE=clawrouter EARN_MODE=discover bash run.sh` + `bash monitor.sh`; assert (via `echo`/print statements inserted temporarily or via reading `_instance_paths.sh`'s resolved values directly) that all 5 `CLIP_*` vars carry the `-clawrouter` suffix AND that claude-p's own 5 unsuffixed files' `mtime`/byte-content are IDENTICAL before and after this run (a real `md5`/`stat` before/after diff, not "no error seen"). |
| PROP-106 | REQ-106 (genesis-loop env wiring documented) | 1 (doc citation) | true | The completion report cites the EXACT real file path + line (or "no such file exists yet, here's where it must be created") for where `ANICCA_INSTANCE=clawrouter` needs to live for the genesis loop process; this citation is checked by a fresh-context adversary re-reading the SAME real file and confirming the citation is accurate (not fabricated). |
| PROP-107 | REQ-107 (live E2E post + independent verify + cleanup) | 3 (E2E, no-mock) | true | Mirrors `clip-post-verify-hardening` PROP-008(a)'s already-proven method exactly: real clip queued → real `EARN_MODE=execute bash run.sh` (with `ANICCA_INSTANCE=clawrouter`) → `outcome="published"` → SEPARATE fresh browser navigation independently confirms the new href is present on the new account's live profile → ledger confirms `status:"posted"` at the `-clawrouter`-suffixed ledger path → test post deleted afterward, re-confirmed via another fresh navigation, ledger annotated (identical pattern to the already-shipped precedent). |

## Verification tiers legend

- Tier 1: schema/file-content checks (no browser/network required for THIS specific assertion,
  though the artifact being checked was itself produced by a real network operation).
- Tier 2: real subprocess invocation of already-shipped, already-tested deterministic code
  (`run.sh`/`monitor.sh`), no new logic under test — the NEW thing being verified is that REAL
  provisioned data flows through correctly, not the logic itself (already proved by
  `clip-loop-dual-instance-earn` and `clip-post-verify-hardening`'s own test suites).
- Tier 3: real, live, no-mock verification against real external systems (Solana network for
  wallet validity if applicable, real Instagram for account/post checks) — executed by the main
  agent, per HARD RULE 0.24/0.31, mirroring the two-gate design (adversary reviews the
  documentation/citations; main agent runs the actual live checks — adversary has no browser or
  wallet access).

## Gate

Phase 3 (adversarial review, fresh-context Sonnet-5) confirms: (a) REQ-101 through REQ-106 are
genuinely and specifically documented with real, checkable citations (file paths, line numbers,
command outputs) — not vague claims; (b) zero modification to any already-shipped file
(`_instance_paths.sh`, `run.sh`, `monitor.sh`, `self_heal.py`, `reel_verify.py`, `count_posts.py`,
`post_reel.py`, `runtime/loop/index.mjs`) — a real `git diff`/`diff` check; (c) no secret
(`secret_bytes`, IG password, session cookie) is ever written in plaintext to any spec, task list,
commit message, or log file this feature produces. PROP-107 (live E2E) is executed by the MAIN
AGENT after Phase 3 PASS, never by the adversary (no browser/wallet access) — same two-gate split
already established by `clip-post-verify-hardening`.
