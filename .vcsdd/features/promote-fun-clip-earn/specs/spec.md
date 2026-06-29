# Behavioral Spec — promote-fun-clip-earn (VCSDD, lean) — REV 2 (post-adversary)

> REV 2 rewrites REV 1 to close all 9 adversary MUST-FIX items
> (`reviews/spec-review-verdict.md`, FAIL 5/5). Cross-refs to that verdict are marked `[Fn.n]`.

## Goal (provable finish line)
An autonomous, no-human loop that earns **real USDC on Solana** on Promote.fun by clipping active
brand campaigns and posting them to a **warmed, verified Instagram account**.

**DONE (the ONLY acceptance gate) = a real, confirmed, EXTERNAL on-chain USDC inflow to the wallet
`xxKC33TYJ2czjGQAADrvDCLjF6pRvtHX125fCwP5u9H` (Solana), recorded as ONE profitable ledger line.**
Nothing short of an on-chain USDC inflow is DONE. [F1.2/F3.2/F5.2]

Pre-payout milestones (campaign selected, clip live, submission accepted, views accruing) are tracked
as **pipeline STATE**, never as DONE, and each is independently evidence-backed. A milestone wake prints
`earned_usdc:0` and leaves the slot `declared` (not `live`). Only the payout/record wake can flip the
slot `live`. [F4.2]

## Context (already proven E2E, no-human)
- Promote.fun account `aniccaclips` created + logged in (creds `~/.cloak/promotefun-anicca.json`:
  `username`, `password`, `email`, `wallet_solana`, `linked_ig`).
- IG `@aishigoto.labo` LINKED + ✓Verified on Promote.fun (bio-code BQ8RUXY8).
- Auth: web login (username+password) → session cookie; email OTP via `gog gmail` (needs env
  `GOG_KEYRING_PASSWORD` from `~/.openclaw/.env`; OTP query `in:anywhere`, incl. SPAM).
- Browser: local = CloakBrowser daily-driver (CDP :9222); each clip account in its OWN isolated profile.

## Payout mechanics (Promote.fun — verified from FAQ 2026-06-29) [F1.3]
Source: `https://www.promote.fun/faq` — verbatim: *"Earnings are added to your promote balance once a
campaign ends, withdraw USDC instantly on the Solana blockchain."*
1. Per-view reward accrues to an **off-chain Promote.fun `balance`** as the submitted post gathers views.
2. The balance is **credited (becomes withdrawable) only once the campaign ENDS** (campaign has an end
   date / budget exhaustion).
3. Withdrawal is a **manual claim** action by the account holder → produces **one Solana USDC transfer**
   (an SPL-token transfer of mint `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` to the wallet's ATA).
   That transfer's **signature** is the on-chain proof of the only true DONE state.
   (The USDC SPL mint address MUST be re-confirmed at build time against the wallet's actual USDC ATA;
   do not hardcode without an on-chain check — HONESTY Rule 1.)

## Chain model — Solana, NOT EVM/Base [F3.1/F4.1/F5.1]
The reused canonical earn ledger (`~/anicca/skills/earn/lib/ledger.mjs`) and its verifiers
(`lib/verify-tx.mjs`, `lib/usdc.mjs`) are **EVM/Base-only** (`eth_getTransactionReceipt`→`0x1`,
`eth_call balanceOf`, `0x…64`/`0x…40` regexes). Promote.fun pays on **Solana** (base58 wallet). The
EVM gate can NEVER honestly confirm a Solana payout, so:

- **A new Solana adapter SHALL be built** (`lib/solana-verify.mjs`):
  - `sigStatus(signature, {rpc, fetchImpl})` → reads `getSignatureStatuses` /`getTransaction`; returns
    `{confirmed: bool, err: any}` where `confirmed === (confirmationStatus ∈ {confirmed,finalized} && err === null)`.
    Signature regex = base58 ~64–88 chars (NOT `0x…64`).
  - `usdcDeltaForSig(signature, wallet, {mint, rpc, fetchImpl})` → from the tx's `meta.preTokenBalances`
    / `postTokenBalances`, computes the SPL-USDC `uiAmount` delta credited to `wallet`'s ATA in that tx
    (the inbound amount). Returns a number (USDC, 6dp).
  - `usdcBalance(wallet, {mint, rpc, fetchImpl})` → `getTokenAccountsByOwner(wallet,{mint})` parsed
    `tokenAmount.uiAmount`, for an independent before/after balance proof.
- **`isProfitable` SHALL be generalized off the EVM `0x1` assumption** (canonical ledger.mjs):
  a line counts iff `net_usdc > 0` AND `external === true` AND source-not-swap AND a chain-correct
  confirmation:
  - EVM line: `tx` present AND `status === "0x1"` (unchanged), OR
  - Solana line: `sig` present AND `confirmed === true`.
  The `external:true` flag SHALL be set ONLY by run.sh after the Solana adapter asserts an INBOUND
  USDC transfer to our wallet (delta > 0) on a confirmed signature — never by env, never by a swap.
  RPC = `SOLANA_RPC_URL` env (default a public mainnet RPC), injectable for tests.

## EARS Requirements
- **REQ-1 (campaign select):** WHEN the loop wakes in SELECT phase, the system SHALL fetch ACTIVE
  Promote.fun campaigns (authenticated session) and select one whose platform allows Instagram and that
  is not already in the dedup ledger this cycle, preferring higher (CPM × remaining budget).
- **REQ-1a (no active campaigns):** IF zero eligible ACTIVE campaigns exist (none, all clipped, none
  allow IG), the wake SHALL print one narrate line `did:"no-eligible-campaign"`, `earned_usdc:0`, and
  exit 0 (idle, never error, never block). [F2.1]
- **REQ-2 (source + specs):** WHEN a campaign is selected, the system SHALL obtain its source video URL
  and clip spec (allowed length, vertical 9:16, allowed platforms incl. Instagram).
- **REQ-3 (clip):** WHEN source + spec are known, the system SHALL produce a **15–45s, 1080×1920** clip
  (reuse earn-clip-rewards: yt-dlp + faster-whisper + ffmpeg), NO mock asset. A dedicated duration gate
  SHALL assert `15 ≤ dur ≤ 45` (the shared `verify_clip.sh` window 8–90s is NOT sufficient; layer a
  stricter check or fail the clip). [F3.3/F5.4]
- **REQ-4 (post — WARMED account only):** WHEN a clip exists, the system SHALL post it via
  `ig-reels-poster --live` ONLY to an account whose warm-state is `ready` (warmer Day-7 complete) AND
  whose isolated browser confirms it is logged in as that exact handle (fail-closed account-guard). IF no
  `ready` account exists, the wake SHALL defer (narrate `did:"no-warm-account"`, exit 0) and NOT post —
  posting commercial brand clips from an un-warmed account is a ban/shadowban path and is forbidden.
  [F2.2] The live post URL SHALL be captured and verified to resolve on the account's profile.
- **REQ-5 (submit):** WHEN posted, the system SHALL submit the post URL to the campaign on Promote.fun
  and read the submission status.
- **REQ-5a (submission not accepted):** IF the submission is REJECTED / pending / disallowed, the wake
  SHALL record the status, mark that (campaign,post) as `submit-failed` in state (do NOT re-submit blindly),
  print a narrate line, and exit 0. Acceptance is required before MEASURE. [F2.3]
- **REQ-6 (measure + liveness):** In MEASURE phase the system SHALL read views + accrued balance per
  submission from Promote.fun stats AND assert post liveness (the post URL still resolves on profile AND
  the submission is still `accepted/active`, not removed/shadowbanned/rejected). views MAY be a real `0`
  ONLY while liveness PASSES; **views=0 is NOT a pass of the earning gate** — it leaves the pipeline in
  MEASURE state. A failed liveness check (dead/removed/rejected post) is an explicit FAIL that moves the
  item to `dead` and frees the campaign slot. [F3.2/F5.2]
- **REQ-7 (withdraw):** WHEN a campaign has ENDED and the Promote.fun withdrawable balance for our
  account is `> 0`, the WITHDRAW wake SHALL trigger the on-chain USDC withdrawal (claim) to the Solana
  wallet and capture the resulting Solana transaction **signature**. [F1.3]
- **REQ-8 (record-earn):** WHEN a withdrawal signature exists, the system SHALL verify it with the
  Solana adapter (`sigStatus.confirmed === true` AND `usdcDeltaForSig > 0` inbound to our wallet) and
  append ONE ledger line `{chain:"solana", sig, confirmed:true, earn_usdc:<delta>, cost_usdc:<run cost>,
  external:true, source:"promote.fun"}` to the canonical ledger via `record.mjs`/`isProfitable`. Idempotent:
  the same `sig` is NEVER double-counted. A non-confirmed or zero-delta signature is REJECTED (never
  recorded as earned). This is the ONLY path that prints `earned_usdc > 0`. [F1.1/F3.1]
- **REQ-9 (no-human INVARIANT + watchdog):** every step SHALL run with zero human — captcha→CapSolver,
  OTP→`gog gmail`, login→stored creds. Verified TWO ways: (a) static — fresh-context adversary greps the
  impl for human-gating calls; (b) **runtime** — each wake runs under a hard `SKILL_TIMEOUT_S` watchdog and
  each browser/IO step under a per-step deadline; if any step would block on human input (daily-driver
  captcha/2FA fallback, IG interstitial, file-attach prompt) it SHALL trip the deadline, the wake SHALL
  print `did:"blocked:human:<step>"`, `earned_usdc:0`, and exit 0 (recorded as a defect — NEVER a hang,
  NEVER a silent wait-for-Dais). [F5.3]
- **REQ-10 (auth resilience):** IF OTP does not arrive / is expired, or the session cookie expired
  mid-flow (between post and submit), the wake SHALL re-authenticate (login → OTP) once within its
  deadline; if re-auth fails it prints `did:"auth-failed"` and exits 0 (no human prompt). [F2.4]
- **REQ-11 (idempotent + bounded + dedup):** safe to run every wake; dedup is keyed on
  `(campaign_id, post_url)` and on withdrawal `sig` (REQ-8) — never double-post the same clip to the same
  campaign, never double-submit the same post URL, never double-record a sig. Promote.fun/IG `429`/rate
  limits SHALL back off (narrate `did:"rate-limited"`, exit 0). [F2.5]
- **REQ-12 (slot contract — single-wake mapping):** entrypoint `run.sh` is spawnable by `run-skill.mjs`,
  reads config from env (wallet/keys scrubbed from output), performs the ONE bounded transition chosen by
  a PURE decision function for the current pipeline STATE, prints ONE structured stdout line
  (`{slot, did, earned_usdc, cost_usdc}`), and exits 0. State persists in a JSON state file across wakes
  (see state machine). [F4.2/F2.4]

## Multi-wake state machine (mapped onto the single-wake run.sh) [F4.2]
A PURE `decide(state, now)` (no I/O, testable in isolation — mirrors `earn/video/decide.py`) returns ONE
transition per wake. State persists in `state/clip-promote-state.json`. Per-item lifecycle:

| State        | Wake transition (one bounded action)                                   | prints earned_usdc |
|--------------|------------------------------------------------------------------------|--------------------|
| SELECT       | REQ-1: pick a campaign (or REQ-1a idle)                                 | 0 |
| CLIP         | REQ-2+REQ-3: produce the 15–45s clip                                   | 0 |
| POST         | REQ-4: post to a warmed account, capture URL (or defer)                | 0 |
| SUBMIT       | REQ-5: submit URL; REQ-5a on reject                                    | 0 |
| MEASURE      | REQ-6: read views + liveness (loops here until campaign ends)          | 0 |
| WITHDRAW     | REQ-7: campaign ended + balance>0 → claim → capture sig                | 0 |
| RECORD       | REQ-8: verify sig on Solana + append profitable line                   | **>0 (DONE)** |
| dead/idle    | liveness fail / no work → free slot, narrate                           | 0 |

Most wakes legitimately print `earned_usdc:0` and keep the slot `declared`; the slot flips `live` only
on a RECORD wake. This is expected and explicitly spec'd (not a silent stall).

## Verification architecture (how each REQ is checked — maker≠checker)
- REQ-1/1a/2/5/5a: live Promote.fun session read shows the selected campaign + submission status
  (fresh screenshot/JSON), and the idle/reject narrate line for the empty/rejected cases.
- REQ-3: `ffprobe` confirms `15 ≤ dur ≤ 45` AND `1080×1920` AND an audio stream present (no silent).
- REQ-4: the post URL resolves on the account profile (a `/p/` or `/reel/` tile), browser-verified; the
  account's warm-state was `ready` (assert the state file) before posting.
- REQ-6: stats read returns a real view number AND liveness PASS; a dead/removed post FAILS the check.
- REQ-7: the withdraw action returns a base58 Solana signature.
- REQ-8 (the DONE check): `solana-verify.sigStatus(sig).confirmed === true` AND
  `usdcDeltaForSig(sig, wallet) > 0` AND the ledger line satisfies `isProfitable` (net>0 + external:true +
  Solana-confirmed). Re-running with the same sig appends nothing (idempotent). A maker≠checker agent can
  run all of these against the named lib — no phantom `external`/`0x1` field. [F1.1/F5.1]
- REQ-9: (a) `grep` finds no interactive prompt; (b) inject a step that blocks → the watchdog trips and
  the wake exits 0 with `did:"blocked:human:*"` within `SKILL_TIMEOUT_S`. [F5.3]
- 5-GATE (earn engine): V1 campaign-picked / V2 clip-posted-live(warmed) / V3 submitted-accepted /
  V4 views-inbound(liveness) / V5 **USDC-withdrawn-and-Solana-confirmed-recorded**. pass-without-evidence
  is grep-blocked. Only V5 is DONE.

## Out of scope (this feature)
- TikTok (IG only for now). The educational slideshow track (@aishigoto.labo) stays SEPARATE.
- The OUTER self-improvement loop (#6) + self-heal (#8) are follow-on features.

## NOTE / risk
@aishigoto.labo is AI-niche; campaigns are mainstream. REQ-4 forbids posting until an account is warmed
(`ready`); a dedicated warmed clip account is the clean path if @aishigoto.labo is not yet Day-7. The bio
still holds BQ8RUXY8 (removable after verification).
