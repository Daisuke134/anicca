# Behavioral Spec — clip-clawrouter-instance-provision (Phase 1a) — REV 3 (SCOPE PIVOT, post Phase 1c PASS)

## ★★★ SCOPE PIVOT (Dais 2026-07-04 verbatim correction, mid-implementation) ★★★

Dais, after seeing me (the main Claude Code session) start MANUALLY driving IG account signup by
hand (opened an isolated browser context, was about to fill the signup form myself): "why are YOU
doing the acc creation and not the loop?? ... the loop should include setting ig account -> posting
clips -> improving with metrics -> earning money right? ... i dont understand why they not doing
it ... the thing should be inside of the shit right?? inside of the loop i think."

★ This is a HARD correction of this feature's original design, not a minor tweak ★. Original REV
1/2 scope was: I (this dev session) manually provision ONE new wallet + ONE new IG account by hand
for the ClawRouter identity. **This is now REJECTED as the wrong shape of work.** Reasons (per
Dais's own words + this project's own standing architecture rules):
- A hand-provisioned account is a ONE-TIME artifact — it doesn't scale (account #2, #3 would again
  require a human/dev session), and it defeats the entire point of an autonomous, self-improving
  earn loop (per `feedback_real_axis_local_vs_cloud_zero_human_loop`: "ZERO human in the loop is a
  HARD INVARIANT" — a human/dev session hand-driving IG signup for the loop IS a human-in-the-loop
  violation, even if it happens to be Claude Code doing the clicking instead of Dais).
- Per HARD RULE #0 (`feedback_skills_give_tool_not_decision`): a skill gives the AGENT a
  tool+onboarding; it does not hardcode the DECISION of when to use it. The actual gap found (via
  real investigation, not guessing) is: `ig-account-create` is NOT registered anywhere in
  `~/anicca/skills/registry.json` (confirmed: `grep -n '"ig-account-create"' registry.json` →
  zero matches, only `"earn/clip"` matches), so the ClawRouter genesis loop's `activeSkillSlots`
  (derived from that registry) can never even SEE `ig-account-create` as a pickable action — the
  model literally cannot decide to run it, because it isn't offered as an option. Separately,
  claude-p's own cron prompt (`clip-cli.sh`'s `STARTUP` string) explicitly instructs it to run
  `run.sh`/`monitor.sh` ONLY, with a passive note "only posts when ... a ready logged-in clip
  account ... exist" — it never instructs the agent that, when no ready account exists, the
  correct next action is to invoke `ig-account-create` itself.
- **This IS the actual root cause of "why don't they just do it themselves"**: not a technical
  limitation, but a genuine WIRING gap — the tool exists (proven, working, `ig-account-create`
  skill) but neither loop has ever been told it exists / can pick it.

**REVISED scope of this feature**: instead of hand-provisioning ONE account, this feature WIRES
`ig-account-create` (and, by the same pattern, the wallet-generation step) as genuinely
AGENT-INVOKABLE actions inside the SAME earn/clip cycle, for BOTH loops (claude-p AND the
ClawRouter genesis loop — per `feedback_real_axis_local_vs_cloud_zero_human_loop`, both share the
identical skill library and should behave identically), so that a REAL, LIVE wake of either loop —
finding it has no ready clip-earn account for its own `ANICCA_INSTANCE` — autonomously decides to
invoke `ig-account-create` and provisions its own identity, with ZERO human or dev-session hand
execution. The already-generated wallet (`~/.cloak/clawrouter-clip-solana.json`, see Ground Truth)
is treated as a legitimate one-time infra bootstrap artifact (analogous to how the ClawRouter
genesis instance itself got its OWN wallet via `identity.mjs`'s `assignIdentity` on first spawn —
that's also a one-time bootstrap, not something re-derived every wake) — it stays, but the
ACCOUNT + POSTING + IMPROVING cycle must genuinely run inside the loop's own agentic decision-making
from here on, never hand-driven again.

## Context (why this feature exists, ORIGINAL — superseded in framing by the pivot above, retained for history)

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

## In scope (REVISED per the pivot)

- **REQ-101 (unchanged, one-time infra bootstrap, already done)**: the new Solana keypair,
  `~/.cloak/clawrouter-clip-solana.json`, distinct from `myclaude-solana.json` — kept as a
  legitimate one-time identity-bootstrap artifact (analogous to the ClawRouter genesis instance's
  OWN wallet, generated once via `identity.mjs`).
- **Register `ig-account-create` as a genuinely agent-invokable action** in
  `~/anicca/skills/registry.json` (the SAME registry `earn/clip` is already in), so the ClawRouter
  genesis loop's `activeSkillSlots` (derived from that registry via `liveSlotNames`) actually
  OFFERS it as a pickable `run_skill` tool — closing the real, confirmed gap (zero registry entry
  today).
- **Update claude-p's own onboarding instructions** (`clip-cli.sh`'s `STARTUP` cron-registration
  prompt) to explicitly tell the agent: when `EARN_MODE=discover bash run.sh` reports no ready
  account for its `ANICCA_INSTANCE`, the correct next action is to invoke `ig-account-create`
  itself (with a fresh Gmail plus-address tag) — not to silently no-op forever. This is guidance IN
  NATURAL LANGUAGE (per HARD RULE #0 — the agent decides HOW/WHEN, this only tells it the action
  EXISTS and is appropriate here), not a hardcoded deterministic branch inside `run.sh` itself.
- **The SAME onboarding update applies to the ClawRouter genesis loop's own skill catalog summary**
  (`skillCatalog[name]` in `runtime/loop/index.mjs:110`, sourced from `registry.slots[name].summary`
  — a real, existing field the loop already surfaces to the model) — the `earn/clip` registry
  entry's own `summary` field (or a sibling note) should mention that a missing ready account is
  resolved by invoking `ig-account-create`, so BOTH loops (human-funded and self-funded, sharing
  the identical skill library per `feedback_real_axis_local_vs_cloud_zero_human_loop`) get the same
  guidance from the same source of truth.
- **A REAL, LIVE demonstration**: with the above wiring in place, trigger a REAL wake (of either
  loop — whichever is more practically triggerable within this session) that currently has no
  ready clip-earn account for a given `ANICCA_INSTANCE`, and confirm the agent — of its OWN
  accord, reading the updated guidance, not following a hardcoded script — decides to invoke
  `ig-account-create` and a REAL new Instagram account comes into existence as a result, then
  completes REQ-103/104 (account-file provisioning + isolated browser login) for that real,
  agent-created account. This is the load-bearing verification: the account must be created BY THE
  LOOP'S OWN DECISION during a real wake, not by the main Claude Code session driving the browser
  by hand.
- Verify (via real command execution, `ANICCA_INSTANCE=clawrouter`) that `run.sh`/`monitor.sh`
  correctly resolve to the NEW instance's isolated queue/posted/ledger/pending-verify paths, with
  ZERO overlap with claude-p's existing (unsuffixed) state (REQ-105, unchanged).
- Actually wire `ANICCA_INSTANCE=clawrouter` into `com.anicca.daemon.plist`'s
  `EnvironmentVariables` dict + reload via `launchctl` (REQ-106, unchanged) so the REAL genesis-loop
  daemon process's own environment carries it.
- The live E2E post (REQ-107) still applies, but is now downstream of the loop's OWN decision to
  post (using the account it itself provisioned), not a main-agent-driven `run.sh` invocation
  against a hand-created account.

## Out of scope

- Building a SECOND new IG account for this instance beyond the first (multi-account-per-instance
  scaling is a future concern).
- The weekly self-improvement scoring loop (task #4 — separate feature; "improving with metrics" is
  explicitly part of Dais's stated full-cycle vision but is tracked as its own feature, not
  re-scoped into this one, to keep this feature's Gate achievable).
- The promote.fun Sutando harness (task #5 — separate feature).
- Telegram reporting (task #6 — separate feature).
- Modifying `_instance_paths.sh`, `run.sh`, `monitor.sh`, `self_heal.py`, `reel_verify.py`,
  `count_posts.py`, or `post_reel.py` — ALL of these are ALREADY instance-aware and ALREADY tested
  (Feature 1 + `clip-post-verify-hardening`); this feature only adds a REGISTRY entry + PROMPT
  guidance, it does not change any of these files' code.
- Building a NEW, separate "account-provisioning skill" wrapper — `ig-account-create` ALREADY
  exists and is proven; this feature makes it VISIBLE/INVOKABLE to the loop, it does not rewrite it.
- Actually running the genesis `~/anicca/runtime/loop` as a NEWLY-installed continuously-scheduled
  daemon (it already runs as `com.anicca.daemon`, confirmed live — this feature reloads its
  existing plist, it does not install a new one) or setting up claude-p's tmux session from scratch
  (it may already be running per `clip-cli.sh` — this feature's job is the WIRING + a real
  demonstration within an achievable session window, not standing up new infrastructure processes).

## Requirements (EARS)

- **REQ-101 (new wallet)**: THE SYSTEM SHALL generate ONE new Solana keypair via the same
  mechanism/library already used for `myclaude-solana.json` (verified during implementation:
  `solders` is importable in this environment), persist it at
  `~/.cloak/clawrouter-clip-solana.json` with `chmod 600`, and the resulting `pubkey` SHALL be
  provably distinct from `myclaude-solana.json`'s `pubkey` (a direct string-inequality check, not
  an assumption).
- **REQ-102 (agent-invokable account provisioning — ★ REDESIGNED per the 2026-07-04 scope pivot:
  was "I create ONE account by hand", now "the LOOP decides to create it, using tooling this
  requirement wires" ★)**: THE SYSTEM SHALL (a) add an `"ig-account-create"` entry to
  `~/anicca/skills/registry.json` (same shape/fields as the existing `"earn/clip"` entry: `track`,
  `dir`, `entrypoint` pointing at a real, invocable script, `status: "live"`, `owner`), so
  `liveSlotNames(registry)` genuinely includes it in `activeSkillSlots` and the ClawRouter genesis
  loop's tool-menu (`getToolDefinitions`/`buildUserMessage` in `runtime/loop/prompt.mjs`) offers it
  as a real `run_skill({slot:"ig-account-create", args})` option; (b) update `clip-cli.sh`'s
  `STARTUP` cron-registration string (claude-p's own onboarding prompt) to explicitly state: when
  `EARN_MODE=discover bash run.sh` reports no ready account, the agent SHALL invoke
  `ig-account-create` (with a fresh Gmail plus-address tag, e.g. `keiodaisuke+clawrouter<N>@gmail.com`)
  to provision one itself, per that skill's proven zero-human flow, ALSO launch that account's own
  isolated CloakBrowser instance (REQ-104) and write its own entry into `$CLIP_ACCTS` (REQ-103 —
  `ig-account-create` itself has no knowledge of the clip-earn account registry; the STARTUP prompt
  explicitly instructs the agent to also do this trivial file-write step, a deterministic action
  well within the agent's existing Bash/file tools, not a new skill), THEN retry `run.sh`. THE
  SYSTEM SHALL THEN, as the real verification bar (not a hand-driven substitute), trigger a REAL
  wake of
  EITHER loop that currently has no ready account, and CONFIRM (via the loop's own tool-call log /
  cron output, not a mocked trace) that the agent itself chose to invoke `ig-account-create` and a
  REAL new Instagram handle came into existence as a direct result — completing the same
  "COMPLETE account" bar (profile icon + bio, per that skill's own contract) — with the resulting
  handle provably distinct from `aiclipsvault`.
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
