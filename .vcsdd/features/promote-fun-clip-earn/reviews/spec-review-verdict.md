# VCSDD Phase 1c — Adversary Spec Review Verdict

- Feature: `promote-fun-clip-earn`
- Spec reviewed: `.vcsdd/features/promote-fun-clip-earn/specs/spec.md`
- Mode: lean
- Reviewer: fresh-context adversary (disk-only, zero builder context)
- OVERALL VERDICT: **FAIL** (5 / 5 dimensions FAIL)

---

## Dimension 1 — Spec Fidelity: **FAIL**

**F1.1 (critical, requirement_mismatch). REQ-7 misquotes the contract it depends on.**
Spec REQ-7 (line 29): *"record ONLY the real EXTERNAL on-chain USDC inflow to the ledger (lib/ledger.mjs isProfitable: tx+0x1+net>0+external)."*
The actual function `isProfitable` at `.claude/worktrees/lipsync-monk/skills/earn/lib/ledger.mjs:32-34` is:
`line && line.tx && line.status === "0x1" && Number(line.net_usdc) > 0` — there is **no `external` field** anywhere in the contract. The spec cites an interface guarantee that does not exist. A builder coding to this line will assume a non-existent gate.

**F1.2 (critical, spec_gap). The "provable finish line" has an OR-branch that requires no money and no views.**
Goal (lines 6-7): *"DONE = a real on-chain USDC inflow ... OR, pre-payout, a clip LIVE + submitted + accruing views."* Combined with REQ-6 (line 41) which explicitly allows views to be `0` ("may be 0 early — honest"), the DONE condition is satisfiable with **zero earnings and zero views**. The headline calls this an "earning loop" but the acceptance gate can pass without earning. This is the exact "submitted counted as earned" anti-pattern.

**F1.3 (major, spec_gap). No requirement covers the payout/withdrawal trigger.**
REQ-7 (line 28) begins "WHEN Promote.fun pays out USDC on-chain" but nothing specifies HOW that payout is initiated — auto-payout vs. manual withdraw, minimum payout threshold, claim button, schedule. There is a hole between REQ-6 (measure) and REQ-7 (record): the actual money-movement step is unspecified, so the loop has no defined action that produces the only true DONE state.

---

## Dimension 2 — Edge Cases: **FAIL**

**F2.1 (major, test_coverage). No-active-campaigns / all-already-clipped is undefined.**
REQ-1 (lines 17-19) selects a campaign "not already clipped this cycle" but specifies no behavior when zero ACTIVE campaigns exist or all are exhausted. Loop wake outcome undefined (idle? error? narrate line?).

**F2.2 (major, requirement_mismatch). Day-1 account posting commercial clips contradicts the poster's own safety contract.**
NOTE (lines 52-53) admits @aishigoto.labo is "day-1 warming". But `ig-reels-poster/SKILL.md:36` states `--live` is "only when the account is warmed (ig-account-warmer) and verify_clip.sh passed." Posting mainstream brand clips (Crocs/music/sports) from an unwarmed AI-niche account is an unhandled ban/shadowban path the spec waves through with "Dais OK'd."

**F2.3 (major, test_coverage). Submission rejection has no path.**
REQ-5 (lines 25-26) only handles the accepted case ("confirm the submission is accepted"). No behavior for campaign REJECTED / pending / clip-disallowed, despite this being the normal failure for a new account.

**F2.4 (major, test_coverage). Auth/session edge cases unspecified.**
REQ-8 (lines 30-31) asserts OTP via `gog gmail`, but there is no behavior for: OTP not arriving, OTP expired, session cookie expired mid-run between post and submit, or `GOG_KEYRING_PASSWORD` (line 13) missing. REQ-9 (line 33) splits on `SKILL_TIMEOUT_S` but says nothing about re-authentication across the split.

**F2.5 (minor, test_coverage). Duplicate-submission and rate-limit not covered.**
REQ-9 (line 32) dedups "posted campaigns" but not duplicate submission of the same post URL to the same campaign, nor IG/Promote.fun rate-limit / 429 handling. IG post removal/shadowban after posting is also unaddressed.

---

## Dimension 3 — Implementation Correctness risks: **FAIL**

**F3.1 (critical, verification_tool_mismatch). The reused earn ledger gate is EVM/Base-only; the payout is Solana — the gate can NEVER honestly confirm it.**
Spec line 14: *"Payout currency = USDC on Solana; wallet `xxKC33TYJ2czjGQAADrvDCLjF6pRvtHX125fCwP5u9H`."* That is a base58 Solana address. The contract REQ-7 reuses is hard-wired to EVM/Base:
- `lib/verify-tx.mjs:5` `TX_RE = /^0x[0-9a-fA-F]{64}$/` and line 16 `method:"eth_getTransactionReceipt"`, returning `"0x1"/"0x0"` (line 22) — Solana signatures are base58 ~88 chars and have no `0x1` receipt.
- `lib/usdc.mjs:7` `ADDR_RE = /^0x[0-9a-fA-F]{40}$/`, line 6 Base USDC `0x833589...`, line 16 `eth_call balanceOf` — a Solana wallet/SPL-USDC cannot be queried here at all.
- `lib/ledger.mjs:33` requires `status === "0x1"`.
Therefore REQ-7 as written is **unimplementable against the named contract**: either the loop fabricates `status:"0x1"` to force a pass (false-positive earn, HARD 0.24 violation) or it never reaches GATE-0. The spec does not acknowledge that a Solana adapter (signature verify + SPL balance delta) must be built, nor that `isProfitable` must be generalized off `0x1`.

**F3.2 (critical, requirement_mismatch). "submitted + accruing views" can pass while broken.** See F1.2. With views=0 honest (REQ-6), a silently shadowbanned post, a rejected clip, or a removed reel all yield the same observable as a healthy clip. No liveness signal distinguishes "0 because early" from "0 because dead."

**F3.3 (major). Clip-spec enforcement is weaker than stated.** REQ-3 (lines 20-22) requires 15–45s. The shipped verifier `earn-clip-rewards/scripts/verify_clip.sh:38` accepts `8 <= DUR <= 90`. If the builder reuses that gate (the spec says "reuse earn-clip-rewards"), a 60s or 10s clip violating REQ-3 passes verification.

---

## Dimension 4 — Structural Integrity: **FAIL**

**F4.1 (critical). REQ-7 contradicts the record-earn / on-chain-USDC invariant of the slot it claims to honor.** The `earn` slot contract (`skills/earn/SKILL.md:50`, `run.sh:5`) defines a profitable wake as a Base receipt `0x1` + EVM USDC before/after delta in one wake. The spec bolts an asynchronous, multi-wake, Solana, externally-triggered payout onto that gate without reconciling chain, address format, or timing. This is a direct structural contradiction, not an extension.

**F4.2 (major). The single-wake run.sh GATE-0 contract is not reconciled with the multi-wake clip pipeline.** REQ-10 (lines 34-35) requires `run.sh` to print ONE structured line and exit 0 per wake; the existing `run.sh` is built for one on-chain tx per wake (EARN_MODE/EARN_TX/EARN_STRATEGY). But clip→post→submit→measure→payout spans many wakes (REQ-9 explicitly splits generate/post/measure) and the earning event (payout) arrives asynchronously days later. The spec never defines what `did`/`earned_usdc` each intermediate wake prints, so most wakes will report `earned_usdc:0` and the slot will sit `declared`, never flipping `live` — undetected by the spec.

---

## Dimension 5 — Verification Readiness: **FAIL**

**F5.1 (critical). REQ-7's verification is uncheckable as written.** Verification architecture line 42: *"ledger line has tx + status 0x1 + external:true."* Per F1.1/F3.1, `external` is not produced by the contract and `0x1` cannot exist for a Solana payout. A maker≠checker cannot run this check against the named lib; it is a phantom acceptance criterion.

**F5.2 (major, unfalsifiable). REQ-6 success is unfalsifiable.** Line 41: views "may be 0 early — honest." A value of 0 is declared an acceptable PASS, so REQ-6 has no failing state — it can never be falsified, which means it verifies nothing.

**F5.3 (major). REQ-8 no-human INVARIANT is contradicted by its own tooling and not grep-checkable.** REQ-8 (line 43) proposes "grep the impl for any human-gating call; none allowed." But the browser stack REQ-4 depends on — CloakBrowser daily-driver — has a documented human fallback ("captcha/新規login/2FA で詰まったら = Dais を呼ぶ", per the daily-driver rule), and `ig-reels-poster/SKILL.md:50-63` documents fresh-account interstitials and an incognito file-attach failure requiring manual workaround. A static grep cannot detect a runtime "wait for Dais to tap" stall, so the INVARIANT is asserted but not actually verifiable by the named method.

**F5.4 (minor). REQ-3 duration check disagrees between the spec verifier and the reused tool.** See F3.3 — verification architecture says 15–45s, the reusable verifier says 8–90s. Two different acceptance windows; the REQ is not unambiguously checkable.

---

## MUST-FIX before building (prioritized)

1. **[F3.1/F4.1/F5.1] Resolve the chain mismatch.** Either (a) build a Solana adapter (signature/`confirmationStatus` verify + SPL-USDC ATA balance delta) and generalize `isProfitable` off the EVM `0x1`/`0x...64`/`0x...40` assumptions, OR (b) change the payout chain to Base. Until then REQ-7 is unimplementable and the earn gate cannot honestly fire.
2. **[F1.2/F3.2/F5.2] Remove the money-free DONE branch.** The provable finish line must be a real on-chain inflow. If a pre-payout milestone is tracked, it must NOT be labeled DONE and views=0 must be an explicit non-pass, with a liveness check distinguishing dead/shadowbanned posts from early-zero.
3. **[F1.1] Fix the REQ-7 contract citation** to match `ledger.mjs:32-34` (or add the `external` field to the lib first); no spec line may reference a non-existent field.
4. **[F1.3] Specify the payout/withdrawal step** — threshold, trigger (auto vs claim), and which wake performs it.
5. **[F2.2] Reconcile day-1-account posting with `ig-reels-poster`'s warmed-only `--live` contract** (warm first, or use a dedicated warmed clip account); define ban/shadowban handling.
6. **[F4.2/F2.4] Define the multi-wake state machine** mapped onto the single-wake run.sh contract: what each wake prints, how state persists across generate/post/submit/measure/payout, and re-auth on session/OTP expiry mid-flow.
7. **[F2.1/F2.3/F2.5] Add EARS requirements** for no-active-campaigns, submission-rejected, duplicate-submission, and rate-limit/429.
8. **[F3.3/F5.4] Unify the clip-duration gate** to the spec's 15–45s (either patch verify_clip.sh or specify a dedicated check); pick one window.
9. **[F5.3] Make the no-human INVARIANT verifiable** beyond grep — add a runtime assertion/timeout that fails the wake if any step blocks on human input (the daily-driver/CapSolver/IG-interstitial fallbacks can stall on a human tap).
