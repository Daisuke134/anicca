# Phase 1c Spec Review — anicca-agent-economy — Iteration 3 (gate iteration cap)

**Verdict: FAIL** (1 new finding, FIND-201 — both iteration-2 blockers independently reconfirmed resolved)

## Scope

Fresh-context, disk-only re-review of:
- `specs/behavioral-spec.md` (revision: iteration 3)
- `specs/verification-architecture.md` (revision: iteration 3)

against the real source files each document makes claims about (`skills/registry.json`,
`runtime/loop/index.mjs`, `runtime/loop/prompt.mjs`, `runtime/loop/liquidity.mjs`,
`skills/self/spawn/{run.sh,lib/spawn-decision.js}`, `skills/economy/gig/run.sh`,
`skills/economy/ubi/ubi.js`, `skills/earn/run.sh`, `skills/earn/hl-trade/hl.py`).

## Iteration-2 blockers: both confirmed genuinely resolved

**FIND-101** (registry classification gap): `registry.json` today has exactly 17 `status:"live"`
slots. REQ-201's classification table lists all 17 by exact name, no omission, no invention.
Spot-checked three of the table's "safe" classifications directly against their own source:
`self/spawn`'s `decideSpawn()` gates all real provisioning on `balanceUsdc >= minBalanceUsdc`
(default 20) before any wallet/droplet/seed spend; `economy/gig/run.sh` really does call
`decide.mjs`'s `decideGigAction()` before the `post` branch executes; `economy/ubi/ubi.js`'s
`contribute()`/`distributeAI()` really are the fail-closed no-ops the table describes. The
classification is now a BINDING Phase 2 acceptance criterion, and PROP-201g (Tier 0) + Gate
item (4a) require the Phase 3 adversary to independently re-derive a sample rather than accept
the table at face value. Resolved.

**FIND-102** (`hasOpenRiskPositionOf` mechanism gap): re-read `index.mjs:243-247` — the cited
ledger-scan expression for the `yield` branch is verbatim the real, already-computed
`positionsSummary` expression (no new I/O). Re-read `skills/earn/run.sh` — `hl-trade` ledger
lines are still written `source:'hl-trade'` (never matching `startsWith('yield')`), and the
script already invokes `hl.py account` as a subprocess (lines 171-172), which is exactly the
primitive the spec says the new `hl_trade` query reuses. `hl.py`'s `open_positions` construction
matches the spec's citation. The lazy-invocation gating and the fail-open-on-failure default are
now fully specified with a reasoned justification. PROP-201h/PROP-201i give this a concrete,
checkable test plan. Resolved.

Iteration-1 findings (FIND-001, 002, 004, 005, 006) and the FIND-003 deadlock fix were all
reconfirmed intact — no regression from this revision's edits.

## New finding this iteration: FIND-201

REQ-204's Acceptance Criteria explicitly scope the prompt-text removal to three named things
(the `★COLONY BOOTSTRAP PRIORITY★` block, `"Prefer this over re-yielding surplus"`, `"it is
almost never 'yield again'"`) and its Edge Cases explicitly say "REQ-204 targets only the
imperative/ranking language named above." A full, fresh re-read of the CURRENT
`runtime/loop/prompt.mjs` (not just the lines already cited by prior findings) turned up a
fourth, equally-real ranking phrase in the same paragraph as one of the three already-named
ones: **`"the highest-leverage move is to POST"`** (line 71, inside the `## Your earn tools`
section's `economy/gig` entry — five lines before the already-flagged `"Prefer this over
re-yielding surplus"`). This is a textbook instance of what REQ-203 itself prohibits ("any
steering text that tells the model WHICH of the remaining options to prefer"), yet REQ-204 never
names it, so a Phase 3 implementation that satisfies REQ-204's own acceptance criteria to the
letter would still leave this phrase in the shipped file. This produces a real internal
contradiction between two proof obligations describing the identical code state: PROP-204a's
narrow "grep for the specific quoted phrases above" could report PASS while PROP-203b's broader
"no pre-existing steering block of equivalent strength remains" would have to report FAIL for the
same file — a non-binary, self-contradictory verification outcome VCSDD's proof-obligation design
is meant to prevent.

## Recommendation

This is iteration 3, the stated cap for this gate. Both iteration-2 blockers are genuinely
closed by independent re-verification against real source — this is not a regression or an
unresolved carry-over. The single new blocker is narrow and mechanical: add
`"the highest-leverage move is to POST"` to REQ-204's Acceptance Criteria / PROP-204a's grep
target list (and consider a general instruction to remove/neutralize any comparable ranking
phrase found anywhere in the file's binding sections, not only phrases enumerable today, so a
similar gap cannot recur). Escalate for a targeted patch rather than a full 4th iteration of this
gate.
