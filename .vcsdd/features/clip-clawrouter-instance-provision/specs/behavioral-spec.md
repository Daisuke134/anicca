# Behavioral Spec — clip-clawrouter-instance-provision (Phase 1a) — REV 2 (post iteration-1 FAIL)

## Context (why this feature exists)

Per `docs/superpowers/specs/2026-07-03-clip-loop-dual-instance-self-improve-design.md` §2.1/§3
(task #3): the clip-earn loop currently runs ONLY as claude-p (human-funded, tmux + Claude Code
subscription, `@aiclipsvault` account, wallet `~/.cloak/myclaude-solana.json`). Per HARD RULE
(`feedback_real_axis_local_vs_cloud_zero_human_loop`): the real behavioral axis is LOCAL vs CLOUD,
not human-funded vs self-funded — both run the IDENTICAL deterministic skill code
(`~/anicca/skills/earn/clip/{run.sh,monitor.sh,producer.sh,self_heal.py,reel_verify.py,
count_posts.py}`), differing ONLY in which wallet/account/ledger/compute-fuel they're bound to.
`feature/clip-loop-dual-instance-earn` (already shipped) built the isolation MECHANISM
(`_instance_paths.sh`'s `ANICCA_INSTANCE` env-suffix pattern — `CLIP_QUEUE`/`CLIP_POSTED`/
`CLIP_ACCTS`/`CLIP_LEDGER`/`CLIP_PENDING_VERIFY`, all suffixed `-${ANICCA_INSTANCE}` when set,
identical unsuffixed default = zero regression for claude-p). This feature PROVISIONS the actual
second identity (real wallet, real IG account, real ledger) and wires it so the genesis
`~/anicca/runtime/loop` (ClawRouter's own agentic loop, self-funded via ClawRouter port-8402
routing) can invoke `earn/clip` with that identity, with ZERO code changes to the already-shipped
isolation mechanism — this is a PROVISIONING feature, not a new mechanism.

## Ground truth (re-verified 2026-07-04, exact facts)

- `~/anicca/skills/earn/clip/_instance_paths.sh` (shipped, `feature/clip-loop-dual-instance-earn`):
  reading `ANICCA_INSTANCE` from env, suffixes `CLIP_QUEUE`/`CLIP_POSTED`/`CLIP_ACCTS`/
  `CLIP_LEDGER`/`CLIP_PENDING_VERIFY` with `-${ANICCA_INSTANCE}`. Already tested
  (`tests/test_n_instance_distinctness.sh` — asserts pairwise distinctness across
  `["", "myclaude", "clawrouter", "clawrouter-2"]`, ALL PASS today). **`"clawrouter"` is already
  one of the tested instance names** — this feature makes that name REAL (a real wallet, a real
  account file, a real ledger with real content) rather than just a test fixture string.
- `~/anicca/runtime/loop/index.mjs:439-461` (`buildSkillEnv`): every skill invocation (including
  `earn/clip/run.sh`) receives `{...scrub(process.env), ANICCA_ARGS, EARN_MODE, EARN_STRATEGY,
  WAKE_ID, ...(config.EARN_LEDGER ? {EARN_LEDGER: config.EARN_LEDGER} : {})}`, and `base =
  scrub(process.env)` reads the REAL OS-level `process.env` of the running node process directly
  (confirmed: `scrubPrivateKeys`'s regex `/(_WALLET_KEY|_PRIVATE_KEY|_PRIV_KEY)$/` does not match
  `ANICCA_INSTANCE`, so a plain instance-name string genuinely passes through unmodified — this
  part of the original claim was correct). ★ CORRECTED after iteration-1 FIND-001 (a real,
  load-bearing error): `~/.anicca/.env`'s TEXT is NOT the source of the actually-running daemon's
  `process.env`. `runtime/loop/config.mjs`'s `loadConfig()` parses that `.env` file's text into a
  LOCAL `dotenvValues` object, then copies ONLY a fixed, small allowlist of named keys
  (`ANICCA_HOME`, `ANICCA_WALLET_ADDRESS`, `ANICCA_BALANCE_OVERRIDE`, `ANICCA_EARN_SKILL`,
  `EARN_LEDGER`, `CLAUDE_BIN`, plus the module's own DEFAULTS) into a separate `config` object — it
  NEVER writes back into `process.env` (confirmed: zero matches anywhere in
  `runtime/loop/*.mjs` for `process.env[`, `Object.assign(process.env`, or `process.env.KEY =`). A
  brand-new key like `ANICCA_INSTANCE` is silently dropped by `loadConfig` and never reaches
  `process.env` this way. The genesis loop actually running on this machine right now is
  `com.anicca.daemon` (confirmed via `launchctl list` → currently loaded, `ANICCA_HOME=
  /Users/anicca/.anicca`); its REAL `process.env` comes from the STATIC
  `<key>EnvironmentVariables</key>` dict inside
  `~/Library/LaunchAgents/com.anicca.daemon.plist` (confirmed via `plutil -convert xml1 -o -`:
  `ANICCA_FREE_MODEL`, `ANICCA_FUNDED_MODEL`, `ANICCA_HOME`, `ANICCA_LEAN_MODEL`, `ANICCA_REPO`,
  `BASE_RPC_URL`, `COMPUTE_RESERVE_USDC`, `HOME`, `PATH`, `YIELD_MIN_DEPLOY_USDC` — `ANICCA_INSTANCE`
  is not there, and this plist dict is a completely separate, static file, NOT dynamically
  populated from `~/.anicca/.env`'s text). `~/anicca/runtime/anicca-daemon.sh` (the daemon's
  `ProgramArguments` entrypoint) does not source `~/.anicca/.env` either (confirmed: no `source
  .env` / `set -a` pattern anywhere in that file; it only explicitly exports `ANICCA_HOME`,
  `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `ANICCA_WALLET_ADDRESS`). ★ The CORRECT mechanism (zero code
  change to any `.mjs` file, matching the original "no code change" intent): add `ANICCA_INSTANCE`
  as a literal new key inside `com.anicca.daemon.plist`'s `<key>EnvironmentVariables</key>` dict,
  then `launchctl unload ~/Library/LaunchAgents/com.anicca.daemon.plist && launchctl load
  ~/Library/LaunchAgents/com.anicca.daemon.plist` (or `launchctl kickstart -k
  gui/$(id -u)/com.anicca.daemon`) so launchd re-reads the plist and the NEW env var reaches the
  daemon's real `process.env` on its next start — genuinely zero `.mjs` code change, but the
  correct target file is the PLIST, not `~/.anicca/.env`. ★
- `~/anicca/skills/registry.json:115-120`: `"earn/clip"` is ALREADY registered
  (`track: A, dir: skills/earn/clip, entrypoint: run.sh, status: live, owner: clip`) — already
  auto-discoverable by ANY genesis loop instance via `liveSlotNames(registry)`
  (`runtime/loop/prompt.mjs`). No registry change needed.
- `~/.cloak/myclaude-solana.json` (claude-p's existing wallet): shape
  `{pubkey, secret_bytes, chain:"solana", owner, created_at, purpose}`. The new wallet for this
  feature MUST be a DIFFERENT keypair, distinct pubkey, own file — sharing a wallet across two
  earner identities is the exact drain/duplicate-post pitfall `_instance_paths.sh`'s own header
  comment already warns against for queue/account/ledger; the SAME principle applies to the wallet.
- `~/.claude/skills/ig-account-create/` (proven E2E 2026-06-29, `@aiclipsvault` created this way,
  zero human, email-plus-address + Gmail OTP auto-read): the canonical, ALREADY-WORKING account
  creation mechanism. This feature REUSES it verbatim for a NEW handle — no new signup code.
- `~/.cloak/clip-accounts.json` (claude-p's existing account list, unsuffixed):
  `[{"handle":"aiclipsvault","profile":"clip-en","port":9223,"lang":"en","status":"ready"}]`. The
  NEW instance's account file (`~/.cloak/clip-accounts-clawrouter.json`, per
  `_instance_paths.sh:16`'s `CLIP_ACCTS="${HOME}/.cloak/clip-accounts${_SFX}.json"`) MUST list a
  DIFFERENT handle, DIFFERENT CloakBrowser profile name, and a DIFFERENT port (port 9223 is already
  bound to `@aiclipsvault`'s isolated CloakBrowser instance — a NEW port avoids CDP-endpoint
  collision, the exact class of bug D-63 already diagnosed once this session for a DIFFERENT
  reason: two processes/profiles must never share one port).
- `~/anicca/skills/earn/clip/producer.sh` (shared, already `ANICCA_INSTANCE`-aware per Task #2):
  its heavy engine dependency
  (`~/.cache/anicca-clones/AI-Youtube-Shorts-Generator/.venv`) is SHARED (one venv, not
  per-instance) — content generation itself is not identity-specific, only WHERE the output lands
  (`$CLIP_QUEUE`, already instance-suffixed) is.

## In scope

- Generate ONE new Solana keypair, distinct from `myclaude-solana.json`, persisted at
  `~/.cloak/clawrouter-clip-solana.json` (same shape: `{pubkey, secret_bytes, chain, owner,
  created_at, purpose}`), file permissions `600`.
- Create ONE new, real, live Instagram account via the existing `ig-account-create` skill
  (email-plus-address + Gmail OTP, zero human), with its OWN profile icon + bio (per that skill's
  "a COMPLETE account" contract), distinct handle from `@aiclipsvault`.
- Provision `~/.cloak/clip-accounts-clawrouter.json` with that new handle, a NEW CloakBrowser
  profile name, and a port distinct from 9223 (and from Dais's daily-driver :9222).
- Launch and confirm login for that new account's isolated CloakBrowser instance (reusing the
  existing pattern already proven for `@aiclipsvault`, at
  `~/anicca-project/.claude/skills/ig-reels-poster/scripts/launch_clip_browser.py` — ★ CORRECTED
  after iteration-1 FIND-002: this file exists ONLY at the PROJECT-level `.claude/skills/` path,
  NOT the GLOBAL `~/.claude/skills/` path where `post_reel.py` itself lives; confirmed by direct
  `find` — a real, pre-existing split between these two skill directories for `ig-reels-poster`
  (the project-level copy also has a STALE, out-of-date `post_reel.py` missing this session's
  `clip-post-verify-hardening` refactor entirely — out of scope to fix here, just noting the
  correct real path for `launch_clip_browser.py` specifically) ★).
- Verify (via real command execution, `ANICCA_INSTANCE=clawrouter`) that `run.sh`/`monitor.sh`
  correctly resolve to the NEW instance's isolated queue/posted/ledger/pending-verify paths, with
  ZERO overlap with claude-p's existing (unsuffixed) state.
- Actually wire `ANICCA_INSTANCE=clawrouter` into `com.anicca.daemon.plist`'s
  `EnvironmentVariables` dict + reload via `launchctl` (per REQ-106) so the REAL genesis-loop
  daemon process's own environment carries it, and a REAL wake of that loop picking `earn/clip`
  would resolve to this new identity — without modifying `runtime/loop/index.mjs`'s
  `buildSkillEnv` (per Ground Truth, no `.mjs` code change is needed there — only the plist).
- A real, live E2E: with `ANICCA_INSTANCE=clawrouter` set, run the REAL `producer.sh` (or a
  manually-queued real clip, matching the precedent set in `clip-post-verify-hardening`'s own
  PROP-008(a) live-verification) → REAL `run.sh` → an actual post lands on the NEW account,
  independently reconfirmed via a fresh browser navigation (not trusting the self-report) — mirrors
  HARD RULE 0.31's bar exactly.

## Out of scope

- Building a SECOND new IG account for this instance beyond the first (multi-account-per-instance
  scaling is a future concern, not this provisioning task).
- The weekly self-improvement scoring loop (task #4 — separate feature).
- The promote.fun Sutando harness (task #5 — separate feature).
- Telegram reporting (task #6 — separate feature).
- Modifying `_instance_paths.sh`, `run.sh`, `monitor.sh`, `self_heal.py`, `reel_verify.py`,
  `count_posts.py`, or `post_reel.py` — ALL of these are ALREADY instance-aware and ALREADY tested
  (Feature 1 + `clip-post-verify-hardening`); this feature provisions REAL DATA/IDENTITY for the
  `"clawrouter"` instance name those files already support, it does not change their code.
- Actually running the genesis `~/anicca/runtime/loop` as a continuously-scheduled daemon (that is
  the broader ClawRouter genesis-instance operational concern, tracked elsewhere) — this feature's
  E2E bar is a manually-invoked, real, `ANICCA_INSTANCE=clawrouter`-scoped run of the clip skill
  scripts themselves, proving the identity + isolation genuinely works end-to-end; wiring a
  perpetual autonomous scheduler for the genesis loop's OWN wake cycle is separate infra work.

## Requirements (EARS)

- **REQ-101 (new wallet)**: THE SYSTEM SHALL generate ONE new Solana keypair via the same
  mechanism/library already used for `myclaude-solana.json` (verified during implementation:
  `solders` is importable in this environment), persist it at
  `~/.cloak/clawrouter-clip-solana.json` with `chmod 600`, and the resulting `pubkey` SHALL be
  provably distinct from `myclaude-solana.json`'s `pubkey` (a direct string-inequality check, not
  an assumption).
- **REQ-102 (new IG account)**: THE SYSTEM SHALL create ONE new, real, live Instagram account via
  the existing `ig-account-create` skill (zero human — email-plus-address signup + Gmail OTP
  auto-read, exactly as already proven for `@aiclipsvault`/`@aiclipper.daily`), complete with a
  distinct profile icon and bio (per that skill's "a COMPLETE account" contract — creation alone is
  NOT sufficient), and the resulting handle SHALL be provably distinct from `aiclipsvault`.
- **REQ-103 (new account file)**: THE SYSTEM SHALL write
  `~/.cloak/clip-accounts-clawrouter.json` (the exact path `_instance_paths.sh:16` resolves for
  `ANICCA_INSTANCE=clawrouter`) containing exactly one entry:
  `{"handle": "<new-handle>", "profile": "<new-profile-name>", "port": <new-port>, "lang": "en",
  "status": "ready"}`, where `<new-port>` is NEITHER `9222` (Dais's daily-driver) NOR `9223`
  (`@aiclipsvault`'s existing isolated instance) NOR any other port already bound by an existing
  CloakBrowser instance on this machine (checked via a real `lsof`/`curl` port-liveness scan at
  implementation time, not assumed free).
- **REQ-104 (isolated browser launch + login)**: THE SYSTEM SHALL launch a NEW, dedicated
  CloakBrowser persistent-profile instance (reusing the existing pattern at
  `~/anicca-project/.claude/skills/ig-reels-poster/scripts/launch_clip_browser.py` — a 14-line
  script: `cloakbrowser.launch_persistent_context(<profile-dir>, headless=False,
  args=["--remote-debugging-port=<port>", "--remote-allow-origins=*"])` + open an initial
  instagram.com tab + keep-alive loop; adapted with the NEW profile dir + `<new-port>`) bound to
  `<new-port>`, log in as the new IG handle, and CONFIRM login via the SAME account-guard check
  pattern `post_reel.py:118` already uses (★ CORRECTED after iteration-1 FIND-003: the real
  comparison is the Python `if active != a.handle:` at line 118, not line 107 — line 107 is the
  unrelated "not logged in" check; `active` itself comes from the `ev(...)` JS read at line 117 ★)
  — not merely "browser process started".
- **REQ-105 (path isolation verified with REAL provisioned files, not just synthetic test
  fixtures)**: WHEN `ANICCA_INSTANCE=clawrouter` is set, THE SYSTEM SHALL demonstrate (via a real,
  executed `EARN_MODE=discover bash run.sh` and `bash monitor.sh`) that `$CLIP_QUEUE`,
  `$CLIP_POSTED`, `$CLIP_ACCTS`, `$CLIP_LEDGER`, `$CLIP_PENDING_VERIFY` all resolve to the
  `-clawrouter`-suffixed paths, that `$CLIP_ACCTS` correctly loads the REQ-103 file (not
  claude-p's), and that claude-p's own (unsuffixed) queue/posted/ledger/accounts files are
  COMPLETELY UNTOUCHED by this run (a before/after content-hash or line-count comparison of
  claude-p's files, not merely "I didn't see an error").
- **REQ-106 (genesis-loop env wiring, no `.mjs` code change — ★ REDESIGNED after iteration-1
  FIND-001, which correctly proved the original `~/.anicca/.env` route does not work: that file's
  text is never loaded back into `process.env` by any code path in `runtime/loop/*.mjs` ★)**: THE
  SYSTEM SHALL add `ANICCA_INSTANCE` = `clawrouter` as a literal new
  `<key>ANICCA_INSTANCE</key><string>clawrouter</string>` entry inside
  `~/Library/LaunchAgents/com.anicca.daemon.plist`'s existing `<key>EnvironmentVariables</key>`
  dict (the file confirmed, via `plutil -convert xml1 -o -`, to be the actual source of the
  currently-running `com.anicca.daemon` genesis-loop process's real `process.env` — NOT
  `~/.anicca/.env`, which nothing loads), THEN reload it via `launchctl unload
  ~/Library/LaunchAgents/com.anicca.daemon.plist && launchctl load
  ~/Library/LaunchAgents/com.anicca.daemon.plist` so launchd re-reads the plist and the daemon's
  next start genuinely has `ANICCA_INSTANCE=clawrouter` in its real OS-level environment — which
  THEN propagates to `earn/clip/run.sh` via `buildSkillEnv`'s `scrub(process.env)` exactly as the
  original Ground Truth analysis of `scrub()`/`buildSkillEnv` correctly described (that specific
  sub-claim was verified accurate by the adversary; only the "where it's set" claim was wrong).
  This genuinely requires ZERO changes to any `.mjs` file (satisfies the original "no code change
  to `runtime/loop`" intent) — the correct target is the plist, not the `.env` text file. This
  requirement is satisfied by ACTUALLY EDITING the real plist + reloading it (a real, checkable
  side effect — `launchctl list` / `plutil` re-read confirming the new key is live), not by merely
  documenting where one COULD edit it, and not by starting a perpetual daemon wake-cycle (out of
  scope — REQ-107's E2E verification uses a manually-exported `ANICCA_INSTANCE=clawrouter` in the
  verifying shell, matching the daemon's own env once reloaded, without requiring an actual
  autonomous wake to fire during this feature's verification window).
- **REQ-107 (live E2E, no dry run — HARD RULE 0.24/0.31)**: THE SYSTEM SHALL, with
  `ANICCA_INSTANCE=clawrouter` genuinely exported in the shell environment (matching how REQ-106
  documents the loop would set it), run the REAL `EARN_MODE=execute bash run.sh` against a REAL
  queued clip and the REAL new IG account, and a post SHALL land — independently reconfirmed via a
  SEPARATE fresh browser navigation to the new account's profile (not trusting `run.sh`'s own
  self-report), mirroring `clip-post-verify-hardening`'s PROP-008(a) precedent exactly. Any test
  artifact posted for this verification SHALL be cleaned up afterward (deleted from the live
  account) exactly as PROP-008(a) did, with a ledger annotation documenting the test + cleanup.

## Non-functional constraints

- No dry runs (HARD RULE 0.24): every claim in this feature's completion report must be backed by
  a real command execution + fresh evidence (new pubkey printed, new IG handle's live profile URL,
  real port-liveness check, real ledger content, real post URL independently reconfirmed).
- Secrets: the new wallet's `secret_bytes` and any new account credentials MUST go through the
  existing `~/.cloak/`/`~/.openclaw/.env` secret-storage conventions (chmod 600, never logged in
  plaintext to any spec/task-list/commit) — same discipline already applied to
  `myclaude-solana.json`.
- Zero regression: claude-p's existing `@aiclipsvault` queue/posted/ledger/accounts/pending-verify
  state must be byte-for-byte unaffected by any step in this feature (REQ-105's explicit
  before/after check enforces this).
