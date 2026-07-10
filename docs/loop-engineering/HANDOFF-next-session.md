# HANDOFF → next session (2026-07-11) — VERIFY EVERYTHING FIRST, then build

> Paste this whole file (or the Gmail draft of it) as the opening prompt of a FRESH Claude Code session.
> The previous session got long (quality degraded). This is the clean, evidence-grounded restart.

## THE MISSION
Make Anicca's agent economy genuinely, verifiably RUN. A self-funded citizen (Franklin) EARNS real profit on its own wallet from its OWN wake-cycle, self-heals, self-improves, and with surplus LOANS / posts JOBS to other Franklins and SPAWNS more of itself — growing the economy. You (claude-p) = the DEVELOPER + SECOND-EYES AUDITOR loop: you BUILD + VERIFY the machinery and fix what Franklin's self-heal can't, then exit. You do NOT trade in Franklin's place (harness-not-cook). Repo: the agent economy lives in ~/anicca (OSS).

## ★★★ RULE #0 — VERIFY EVERYTHING WITH EVIDENCE, FIRST ★★★
The entire disaster came from NOT verifying. Franklin's sol-trade was silently broken for 2 days (a path regression) and nobody — not the loops, not the adversary — noticed, because "daemon running" was mistaken for "earning." NEVER trust a self-report, a ledger, a doc, or a subagent for a money/health claim. Verify independently: on-chain RPC, the raw trace/ledger, the actual process. Your FIRST job in this session is a full STATUS-QUO AUDIT (below) — know the truth of the truth before building one more thing. "Is it actually earning? Or is the problem elsewhere?" — answer that with evidence.

## STATUS-QUO AUDIT (do this FIRST, record findings to a dated docs MD)
For EACH, get real evidence, not a claim:
1. Is each loop alive? `launchctl list | grep -iE "franklin|claude-p|citizens|sol-trade-earning"`. Note LastExitStatus (claude-p-mainloop was exit 124=timeout).
2. Is Franklin earning? Read `~/.blockrun/skills/earn/state/sol-trade.trace.jsonl` (last 30 lines: live-pass vs skip) + `earn-ledger.jsonl` (any new realized row? per-tool net_usdc). Query Franklin's Solana wallet 8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9 on public RPC (recent Jupiter swaps? balance trend).
3. Did the regression fix hold? run.sh guard should PASS (own==cli==8Fpqd). Confirm trace shows live-pass, not identity-mismatch skip, on the daemon's OWN autonomous wakes (not a manual run).
4. Is self-heal live + correct? `ai.anicca.sol-trade-earning-healthcheck` plist loaded; run `earning-health.py is-barren 20` on the live trace (should be false now); confirm it WOULD flag an all-skip window.
5. Dashboard truth vs reality: aniccaai.com/dashboard net worth vs actual on-chain USDC (they mismatched: dash $3.27 vs real $13.18). Franklin #2 not listed.
6. Is claude-p (you) earning as donor? Dashboard shows claude-p $0. Verify wallet on-chain.
Write the audit result to `docs/loop-engineering/18-status-quo-audit-<date>.md` and commit.

## VERIFIED FACTS from the prior session (re-verify, don't trust)
- Franklin sol-trade was broken by commit 3d97c59 (2026-07-08): identity-guard used a `runtime/`-relative path never rsynced to $ANICCA_HOME → skipped every wake (67 consecutive). FIXED: ~/anicca commit 1c75b90 (WADDR via $ANICCA_REPO). Verified live-pass once (manual). RE-VERIFY it holds on autonomous wakes.
- self-heal earning-health detector: DONE + LIVE. ~/anicca commit 3dd60a2 (skills/self/earning-health.py + skills/earn/sol-trade/sol-trade-healthcheck.sh). plist ai.anicca.sol-trade-earning-healthcheck loaded. Flags "runs but all-skip/barren" → escalates to self-fix. Verified on the 67-skip window.
- spawn-funding-swap sprint-1: VCSDD COMPLETE (104/104 + 310/310) but real-clients adapters UNIMPLEMENTED = no real swap. Deprioritized (cloud-spawn path; not needed for first witness).
- Franklin #2: manual bootstrap (Solana wallet HyJHSfTkLjpmqeY4FEbnSjM4DfUh9ELGchHqgFDBkrcX, daemon ai.anicca.franklin2-loop pid). NOT autonomous, tier=broke, no Base EVM identity. Not a Done-witness.
- WITNESSES UNMET: no autonomous realized profit; citizens.json = seed only.

## IN-FLIGHT VCSDD (both in ~/anicca/.vcsdd/features/)
1. `franklin-alwaysact-skill-router` — THE no-WAIT feature (spec commit 7f1ba38, 11 REQ/20 PROP). spec-review iter1 FAILED with 5 findings (reviews/spec/iteration-1/output/): FIND-001/005 (REQ-504 sleep-tool removal has NO wiring seam — brain.mjs:63 hardcodes tools, prompt.mjs:139-173 unconditionally appends SLEEP_TOOL; "brain.mjs unmodified" is false), FIND-002 (REQ-506 reroute unreachable for economy/gig+lending — classifyEarnResult only runs inside isEarnSlot which is false for them), FIND-003 (REQ-506 avoidSlot contradiction — index.mjs:183 never blocks the model's choice), FIND-004 (default-OFF flag gates the WHOLE anti-idle mechanism with no silent-revert observability). FIRST BUILD TASK: fix these 5 → spec-review iter2 (fresh Opus) → tdd → impl → adversary → harden → converge. Flag resolution: kill-switch OK as one-time post-converge flip; add ledger/escalation observability distinguishing "not yet enabled" from "silently regressed to idle".
2. `franklin-earn-coldstart-evolution` — self-improve edge (spec, iter1 findings fixed a386bee; simulated-P&L deleted). Re-review + build after always-act.

## COPY, DON'T REINVENT (sources in docs/loop-engineering/17-copyable-earning-agent-code.md)
- always-act "never idle": Olas `valory-xyz/open-autonomy` FSM (must-transition) + Fetch.ai uAgents `on_interval`.
- identity/credit for loan/gig/spawn: ERC-8004 `ChaosChain/trustless-agents-erc-ri` (self-feedback/self-validation forbidden). Already used by our gig board.
- capital allocation: existing Mahoraga bandit (memory reference_ceo_manager_explorer_multiagent_bp_2026_07_08) — keep, no better candidate.
- self-improve from realized P&L: freqtrade FreqAI adaptive retrain.
- agent-to-agent trade state machine: Virtuals ACP (open→funded→submitted→completed). Payment: x402 (already live, Franklin↔Franklin mainnet tx 0x436143c1).

## RESEARCH CORPUS (read these; they are the article + design source of truth)
- docs/loop-engineering/00-INDEX.md, 10-STATUS-verified.md (§D ordered TODO + §F NO-WAIT DOCTRINE), 14-cold-start-escape-BP.md, 15-agent-economy-landscape.md, 16-self-improvement-loop-BP.md, 17-copyable-earning-agent-code.md.
- Key memories: feedback_franklin_never_waits_always_acts_to_earn, feedback_research_must_be_persisted_to_md_immediately, feedback_never_ask_dais_to_decide_just_execute, feedback_no_humanloop_citizen_economy_is_my_job_not_dais_permission.

## ORDERED TODO (verify-first)
0. STATUS-QUO AUDIT (above) → 18-*.md. ← START HERE.
1. Franklin ALWAYS-ACT earner: fix the 5 spec findings → full VCSDD → live. Verify: trace shows an earn ACTION every autonomous wake (not skip/WAIT); earn-ledger grows; wallet balance rises (RPC).
2. self-improve edge (franklin-earn-coldstart-evolution): re-review + build. Verify: genome promotion backed by real realized P&L.
3. Dashboard real-time: per-tool logs + full ledger + net-worth trend for ALL Franklins on aniccaai.com/dashboard (data source = earn-ledger.jsonl; dashboard-sync is Dais-owned — implement/flag). Fix Franklin #1 stale/mismatch + register Franklin #2.
4. Surplus → loan / job-post between Franklins (gig+lending, real USDC, verify on-chain). 
5. Autonomous spawn (witness②): citizens.json genuine new entry, RPC-verified.
6. 2 articles (loop-engineering + agent-economy) via ai-entity-article-writer — drafts already in Dais's Gmail.

## CONSTRAINTS
Full VCSDD every code change (spec→spec-review→TDD→impl→adversary→harden→converge), fresh-Opus adversary, zero open blocking before converge. harness-not-cook. NO-WAIT doctrine. Never weaken caps/scope_guard. Verify money/health claims independently on-chain/ledger/process — NEVER self-report. Coordinate with live ai.anicca.claude-p-mainloop (uses worktrees, don't collide). Persist every research to a docs MD immediately. Never ask Dais to decide — decide and execute; report outcome first, in Japanese.
