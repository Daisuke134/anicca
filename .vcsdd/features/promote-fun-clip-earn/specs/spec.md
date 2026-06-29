# Behavioral Spec — promote-fun-clip-earn (VCSDD, lean) — REV 3 (post-adversary ×2)

> REV 3 closes the REV 2 re-review findings (`reviews/spec-review-verdict-rev2.md`: 1 critical, 6 major,
> 2 minor). Cross-refs marked `[FIND-2xx]`. REV 1→2 closed the original 9 (`spec-review-verdict.md`).

## Goal (provable finish line)
An autonomous, no-human loop that earns **real USDC on Solana** on Promote.fun by clipping active brand
campaigns and posting them to a **warmed, verified Instagram account**.

**DONE (the ONLY acceptance gate) = a real, confirmed, EXTERNAL on-chain USDC inflow to the wallet
`xxKC33TYJ2czjGQAADrvDCLjF6pRvtHX125fCwP5u9H` (Solana), persisted as ONE ledger line for which the
canonical `isProfitable(persistedLine) === true`.** Nothing short of that is DONE. Pre-payout milestones
are pipeline STATE, never DONE; a milestone wake prints `earned_usdc:0` and keeps the slot `declared`.
Only a RECORD wake can flip the slot `live`.

## Canonical file map (paths VERIFIED to exist on disk) [FIND-203]
- Ledger + classifier (THE one recorder): `~/anicca/skills/_shared/lib/ledger.mjs`
  (`deriveLine`, `isProfitable`, `appendLedger`, `readLedger`).
- Write bridge: `~/anicca/skills/earn/lib/record.mjs` (calls `deriveLine` → `assertOwnIdentityOnly`
  → `appendLedger` → `isProfitable`; imports `../../_shared/lib/ledger.mjs` + `identity-guard.mjs`).
- Malice-guard: `~/anicca/skills/_shared/lib/identity-guard.mjs` (`assertOwnIdentityOnly`,
  `ALLOWED_EARN_SOURCES`).
- EVM verifiers (siblings, EVM-only — NOT reused for Solana): `~/anicca/skills/_shared/lib/verify-tx.mjs`,
  `~/anicca/skills/_shared/lib/usdc.mjs`.
- **NEW Solana adapter SHALL live at `~/anicca/skills/_shared/lib/solana-verify.mjs`** (beside the EVM
  siblings).
- Existing test suite to EXTEND + re-run: `~/anicca/skills/_shared/lib/__tests__/ledger.test.js`
  (+ NEW `__tests__/solana-verify.test.js`).
- This feature's slot dir (NEW): `~/anicca/skills/earn/clip-promote/` — `run.sh`, `decide.py` (PURE,
  mirrors `~/anicca/skills/earn/video/decide.py`), `tests/`, `state/clip-promote-state.json`.
- Reused as-is: `~/.claude/skills/earn-clip-rewards/` (clip), `~/.claude/skills/ig-reels-poster/` (post),
  `~/anicca/skills/earn/clip/run.sh` (warm-account pattern; reads `~/.cloak/clip-accounts.json`).
- The Python `video/record_earn.py` is the VIDEO track's local recorder. clip-promote does NOT use it as
  the write path — it mirrors only its PRINCIPLE (inflow-only + idempotent). [FIND-202]

## ONE canonical recorder [FIND-202]
The earn line is recorded EXCLUSIVELY via the JS canonical path `record.mjs` → `deriveLine`/`isProfitable`
in `_shared/lib/ledger.mjs`. No other recorder is authoritative for this feature. The line schema is the
JS schema (`tx`/`status`/`external` for EVM; `sig`/`confirmed`/`chain` for Solana — see below), NOT the
Python `tx_hash`/`verified`/`direction` schema.

## Solana chain support — REQUIRED lib changes (the DONE write-path) [FIND-201/202/203/206/207]
Promote.fun pays on Solana (base58 wallet); the EVM gate cannot honestly confirm it. The following
changes to the canonical lib are MANDATORY and each has a test:

1. **`deriveLine` MUST carry the Solana fields** (`_shared/lib/ledger.mjs`, currently copies only
   `{ts,wallet,source,task,earn_usdc,cost_usdc,net_usdc,wake}` + conditional `tx`/`status`/`external`).
   Add, conditionally (same style): `if (o.sig) line.sig = o.sig; if (o.confirmed === true)
   line.confirmed = true; if (o.chain) line.chain = o.chain;`. Without this the persisted line lacks
   `sig`/`confirmed` and DONE can NEVER fire. [FIND-201]
2. **`isProfitable` MUST be generalized** off the hard EVM `0x1` assumption, keeping every existing guard
   (net>0, external:true, not-a-swap). New predicate:
   `net_usdc>0 AND external===true AND source∉SWAP_SOURCES AND ((tx && status==="0x1") OR (sig && confirmed===true))`.
   This is backward-compatible with the existing suite (non-`tx`/non-`0x1` lines stay false). [FIND-207]
3. **`assertOwnIdentityOnly` MUST accept the Solana clip source.** Add `"promote.fun"` (and `"clip-promote"`)
   to `ALLOWED_EARN_SOURCES` in `identity-guard.mjs` — it is Anicca's OWN identity (own IG + own Solana
   wallet); it matches no `FORBIDDEN_EARN_SOURCES` pattern. [FIND-201]
3a. **PII-scrub duty is `run.sh`'s, NOT the harness's.** [FIND-301] The harness (`run-skill.mjs` →
   `env-filter.mjs scrubPrivateKeys`) strips ONLY `*_WALLET_KEY`/`_PRIVATE_KEY`/`_PRIV_KEY`, NOT PII — so
   `GOOGLE_LOGIN`/`COMPOSIO`/`*GMAIL*`/`TELEGRAM`/`USER_*` would still reach the wake, and `record.mjs:19`
   calls `assertOwnIdentityOnly(line)` against `process.env` → `findUserPIIEnv` would THROW before append →
   DONE silently never fires. THEREFORE `run.sh` SHALL invoke the RECORD step under a CLEAN env:
   `env -i PATH="$PATH" HOME="$HOME" SOLANA_RPC_URL="$SOLANA_RPC_URL" EARN_LEDGER="$LEDGER" node <record.mjs> '<json>' "$LEDGER"`
   — passing ONLY the public wallet address + RPC + ledger path, never any PII var. (OTP/Gmail are needed
   only at LOGIN wakes, never at RECORD, so a clean RECORD env loses nothing.) Regression test: set a PII
   var (e.g. `GOOGLE_LOGIN=x`) in the parent env → the run.sh RECORD invocation STILL records the line
   (because `env -i` stripped it) AND a direct `record.mjs` call WITH that var in env still throws (guard
   intact). [FIND-301]
4. **NEW `solana-verify.mjs`** (pure transport, `fetchImpl` injectable for tests; RPC = `SOLANA_RPC_URL`,
   default a public mainnet RPC):
   - `sigStatus(signature, {rpc, fetchImpl})` → `getSignatureStatuses`/`getTransaction`; returns
     `{confirmed, err}` where `confirmed === (confirmationStatus ∈ {confirmed,finalized} && err === null)`.
     Signature validated as base58 ~64–88 chars (NOT `0x…64`).
   - `usdcDeltaForSig(signature, wallet, {mint, rpc, fetchImpl})` → from the tx's `meta.preTokenBalances`
     / `postTokenBalances`, for EACH `postTokenBalances` entry where `owner === wallet` AND `mint === USDC
     mint`, find the matching `preTokenBalances` entry **by `accountIndex`**; **if no matching pre entry
     exists, pre = 0** (this IS the acceptance case — the wallet has no USDC ATA today, so the first
     inbound withdraw CREATES the ATA and emits a post entry with no pre). Sum `(post.uiAmount −
     pre.uiAmount)` over those entries only, ignoring every other transfer in the same signature
     (batch/multi-transfer safe). Returns the net inbound USDC to OUR ATA (6dp). Tests MUST include a
     first-inbound fixture (post entry present, NO pre entry → delta = full post amount). [FIND-209/303]
   - `usdcBalance(wallet, {mint, rpc, fetchImpl})` → `getTokenAccountsByOwner(wallet,{mint})` parsed
     `tokenAmount.uiAmount`; **returns 0 (not throw) when the ATA does not exist** (verified on-chain
     2026-06-29: our wallet currently has no USDC ATA → first inbound withdraw creates it).
   - USDC SPL mint `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` (verified accepted by
     `getTokenAccountsByOwner` 2026-06-29); re-confirm against the wallet's actual USDC ATA at build time.
5. **`sig`-keyed idempotency** (neither recorder dedups today): before a RECORD append, the WITHDRAW/RECORD
   wake SHALL `readLedger(file)` and skip the append if any existing line has `line.sig === sig`. Spec'd as
   a helper `alreadyRecordedSig(file, sig)` in `ledger.mjs` (pure over `readLedger`), tested. [FIND-206]
6. **Regression gate**: the change to the SHARED `_shared/lib/ledger.mjs` SHALL extend
   `__tests__/ledger.test.js` with Solana cases (confirmed+external+net>0 → true; `confirmed:false` →
   false; `sig` present but `external` missing → false; `deriveLine` carries `sig`/`confirmed`/`chain`)
   AND re-run the FULL suite green (existing EVM `0x1`/swap/external guards preserved). [FIND-207]

## Payout mechanics (Promote.fun FAQ, verified 2026-06-29)
Verbatim (`https://www.promote.fun/faq`): *"Earnings are added to your promote balance once a campaign
ends, withdraw USDC instantly on the Solana blockchain."*
1. Per-view reward accrues to an off-chain Promote.fun `balance`.
2. Credited (withdrawable) only once the campaign ENDS.
3. Withdrawal = manual claim → ONE Solana USDC SPL transfer to our wallet's ATA. Its **signature** is the
   on-chain DONE proof. WITHDRAW + RECORD are distinct wakes.

## Context (proven E2E, no-human)
Promote.fun `aniccaclips` (creds `~/.cloak/promotefun-anicca.json`). IG `@aishigoto.labo` LINKED +
✓Verified (bio-code BQ8RUXY8). Auth: web login → session cookie; OTP via `gog gmail` (env
`GOG_KEYRING_PASSWORD`, query `in:anywhere` incl. SPAM). Browser: CloakBrowser daily-driver (CDP :9222),
isolated profile per clip account.

## EARS Requirements
- **REQ-1 (campaign select):** WHEN the loop wakes in SELECT, the system SHALL fetch ACTIVE campaigns
  (authenticated) and pick one allowing Instagram, not in the dedup ledger this cycle, preferring higher
  (CPM × remaining budget).
- **REQ-1a (no campaigns):** IF zero eligible ACTIVE campaigns, print `did:"no-eligible-campaign"`,
  `earned_usdc:0`, exit 0 (idle, never error/block).
- **REQ-2 (source + spec):** obtain the campaign source video URL + clip spec (length, 9:16, IG allowed).
- **REQ-3 (clip):** produce a **15–45s, 1080×1920** clip (reuse earn-clip-rewards), NO mock. A dedicated
  gate asserts `15 ≤ dur ≤ 45` (the shared `verify_clip.sh:38` 8–90s window is insufficient — layer the
  stricter check, fail otherwise).
- **REQ-4 (post — WARMED account only):** post via `ig-reels-poster --live` ONLY to an account whose entry
  in `~/.cloak/clip-accounts.json` has `status === "ready"` (Day-7-warmed, written by `ig-account-warmer`;
  same file `earn/clip/run.sh:22,47` reads) AND whose isolated browser confirms it is logged in as that
  exact handle (fail-closed guard). IF no `ready` account: defer (`did:"no-warm-account"`, exit 0), do NOT
  post. Capture + profile-verify the live post URL. [FIND-208]
- **REQ-5 (submit):** submit the post URL to the campaign; read submission status.
- **REQ-5a (not accepted):** IF REJECTED/pending/disallowed: record status, mark `(campaign,post)` as
  `submit-failed`, do not blindly re-submit, narrate, exit 0.
- **REQ-6 (measure + liveness, with an honest dead-vs-early discriminator):** [FIND-204] In MEASURE, read
  views + accrued balance, AND check: (a) post URL still resolves on profile, (b) submission still
  `accepted/active`. A direct shadowban is NOT detectable via (a)+(b) (a throttled reel still resolves +
  stays accepted) — so the dead-vs-early-zero discriminator is **time-bounded**: IF views are still `0`
  after `DEAD_ZERO_HOURS` (default 48h) since the post went live, classify the item `stalled` (treat as
  not-earning), free the campaign slot, narrate. views==0 BEFORE that bound = legitimate early-zero, stay
  in MEASURE. views==0 is NEVER a pass of the earning gate. (a)/(b) failing = `dead` immediately.
- **REQ-7 (withdraw):** WHEN a campaign has ENDED AND the Promote.fun withdrawable balance `> 0`, the
  WITHDRAW wake SHALL trigger the on-chain USDC claim to the Solana wallet and capture the Solana
  **signature**.
- **REQ-8 (record-earn):** WHEN a withdrawal `sig` exists AND `alreadyRecordedSig(file,sig)` is false, the
  RECORD wake SHALL verify it (`solana-verify.sigStatus(sig).confirmed === true` AND
  `usdcDeltaForSig(sig,wallet) > 0`) and append via `record.mjs` ONE line
  `{chain:"solana", sig, confirmed:true, source:"promote.fun", earn_usdc:<delta>, cost_usdc:<run cost>,
  external:true, wallet, task, wake}` for which `isProfitable(persistedLine) === true`. A non-confirmed or
  zero-delta or already-seen `sig` is REJECTED (never recorded as earned). This is the ONLY wake that
  prints `earned_usdc > 0`.
- **REQ-9 (no-human INVARIANT + watchdog — owner defined):** [FIND-205] zero human — captcha→CapSolver,
  OTP→`gog gmail`, login→stored creds. Verified TWO ways. (a) static: adversary greps for human-gating
  calls. (b) runtime: **the harness `run-skill.mjs` enforces the wake-level `SKILL_TIMEOUT_S`** (kills a
  wake that overruns); **AND `run.sh` self-guards every browser/IO step with a portably-resolved timeout
  binary.** [FIND-302] run.sh SHALL resolve `TIMEOUT_BIN="$(command -v timeout || command -v gtimeout)"`
  (GNU coreutils ships `gtimeout`; some installs also expose `timeout` — BOTH verified present at
  `/opt/homebrew/bin` on this Mac 2026-06-29, but the cloud box may have only one); IF neither exists, fall
  back to a pure wrapper (`node`/`python3` child killed via `SIGTERM` after the deadline). Each browser/IO
  step runs as `"$TIMEOUT_BIN" "$STEP_DEADLINE_S" <cmd>` (default `STEP_DEADLINE_S=120`). If a wrapped step
  blocks on human input (daily-driver captcha/2FA fallback, IG interstitial, file-attach prompt) the
  wrapper returns 124 → run.sh prints `did:"blocked:human:<step>"`, `earned_usdc:0`, exit 0 (a recorded
  defect, NEVER a hang, NEVER a silent wait-for-Dais). Constructible test: `"$TIMEOUT_BIN" 1 sleep 5` (or
  `STEP_DEADLINE_S=1` + a `sleep 5` step) returns 124 → assert the printed line is `blocked:human:*` and
  exit code 0.
- **REQ-10 (auth resilience):** IF OTP missing/expired or session expired mid-flow, re-authenticate once
  within the step deadline; if re-auth fails print `did:"auth-failed"`, exit 0 (no human prompt).
- **REQ-11 (idempotent + bounded + dedup):** safe every wake; dedup keyed on `(campaign_id, post_url)`
  and on withdrawal `sig` (REQ-8 helper). Never double-post/-submit/-record. `429`/rate-limit → back off
  (`did:"rate-limited"`, exit 0).
- **REQ-12 (slot contract — single-wake mapping):** `run.sh` spawnable by `run-skill.mjs`, reads env
  (wallet/keys scrubbed from output), runs the ONE bounded transition chosen by PURE `decide(state, now)`,
  prints ONE structured line `{slot,did,earned_usdc,cost_usdc}`, exits 0. State persists in
  `state/clip-promote-state.json`.

## Multi-wake state machine (PURE decide, mirrors earn/video/decide.py)
| State | One bounded action | earned_usdc |
|---|---|---|
| SELECT | REQ-1 / REQ-1a | 0 |
| CLIP | REQ-2 + REQ-3 | 0 |
| POST | REQ-4 (warmed-only, else defer) | 0 |
| SUBMIT | REQ-5 / REQ-5a | 0 |
| MEASURE | REQ-6 (loops til campaign end or `stalled`) | 0 |
| WITHDRAW | REQ-7 (campaign ended + balance>0 → sig) | 0 |
| RECORD | REQ-8 (verify sig + append profitable line) | **>0 (DONE)** |
| dead/stalled/idle | free slot, narrate | 0 |

## Verification architecture (maker≠checker)
- REQ-1/1a/2/5/5a: live session read (fresh screenshot/JSON) shows campaign + submission status + the
  idle/reject narrate lines.
- REQ-3: `ffprobe` → `15 ≤ dur ≤ 45` AND `1080×1920` AND audio stream present.
- REQ-4: post URL resolves on profile (`/p/` or `/reel/`); the account's `clip-accounts.json` `status`
  was `ready` before posting.
- REQ-6: stats read returns a real view number; (a)+(b) liveness; the `DEAD_ZERO_HOURS` rule classifies
  stalled vs early-zero (honest — no shadowban overclaim).
- REQ-7: withdraw returns a base58 Solana signature.
- REQ-8 (DONE): `solana-verify.sigStatus(sig).confirmed===true` AND `usdcDeltaForSig(sig,wallet)>0` AND
  `record.mjs`-persisted line satisfies `isProfitable`. Re-run with same sig appends nothing
  (`alreadyRecordedSig`). Runnable end-to-end against the named lib — no phantom field.
- REQ-9: (a) grep finds no interactive prompt; (b) inject a blocking step → `timeout` 124 → exit 0 with
  `blocked:human:*` within the deadline.
- Lib regression: `node --test ~/anicca/skills/_shared/lib/__tests__/*.test.js` green (extended ledger +
  new solana-verify suites), preserving the EVM/swap/external guards.
- 5-GATE: V1 campaign-picked / V2 clip-posted-live(warmed) / V3 submitted-accepted / V4 views-inbound /
  V5 **USDC-withdrawn + Solana-confirmed + recorded** (the only DONE). pass-without-evidence grep-blocked.

## Out of scope
TikTok (IG only). Educational slideshow track (@aishigoto.labo) stays SEPARATE. OUTER self-improvement
(#6) + self-heal (#8) = follow-on.

## NOTE / risk
@aishigoto.labo is AI-niche; campaigns are mainstream. REQ-4 forbids posting until an account is `ready`
(Day-7-warmed); a dedicated warmed clip account is the clean path if @aishigoto.labo is not yet Day-7.
Bio still holds BQ8RUXY8 (removable). Wallet has 0 SOL + no USDC ATA today — fine for RECEIVING an SPL
withdraw (sender funds the ATA); we never sign our own Solana tx.
