# 25 — EARN-AGENT PARITY: the common pattern of working earning agents, and our original divergences

| Field | Value |
|---|---|
| Spec ID | 25 |
| Status | ★ AUTHORITATIVE for the earn-agent runtime architecture (2026-06-21) |
| Author | Claude (read the ACTUAL CODE of 4 working repos + audited our own, via 3 parallel agents) |
| Method | clone/`gh api` + read source of goat-sdk/goat, AGICitizens/agent-adapter, fetchai/agents-aea, unicity-sphere/sphere-sdk; audited ~/anicca/runtime/loop + skills/earn |

> **★ Dais 2026-06-21 (verbatim core): "when we don't know the best practice we go search multiple of
> them and read the CODE, then we find: all the working ones have these things in common, but WE are
> doing it in this original way — and probably that's why it's not working / not making money. Then we
> fix that. Remove all the original things; copy what the successful people do, keep it simple." ★**

## § 0. Why
We searched multiple working autonomous earning agents and read their real code. They CONVERGE on one
simple skeleton. Where Anicca diverges from it, the divergence is our own ORIGINAL complication and is
to be removed. This spec records the common pattern (evidence) + every divergence (file:line) + the
target. It governs the runtime loop + earn-tool architecture; it overrides any contradicting plumbing.

## § 1. THE COMMON PATTERN (verbatim from 4 codebases — what all working ones share)

**Skeleton = identity + ONE wallet (sole signer, isolated behind one gate) + a FLAT list of THIN tools
+ a decide-each-tick loop where the LLM picks a tool. NO orchestrator, NO modes, NO scoring, NO router.
The decision lives inside the model's tool-pick + each skill's own logic — never a central brain.**

| Dimension | goat-sdk/goat | AGICitizens/agent-adapter | fetchai/agents-aea | sphere-sdk |
|---|---|---|---|---|
| Tool shape | `{name, description, parameters(Zod), execute}` (`ToolBase.ts` `createTool`) | `{name, description, parameters(JSON-schema), handler}` (`tools.ts` `TOOL_DEFINITIONS`) | skill = Behaviour.`act()` + Handler.`handle()` + Model/strategy (`skills/base.py`) | flat modules `market/swap/payments/...` (`Sphere.ts`) |
| How thin | one `execute` fn; a swap is a one-method `@Tool` API wrapper (`jupiter.service.ts`) | 3 thin handlers; earn = HTTP+402-pay (`x402-client.ts`) | decision inside skill's `act()`/`Model`; loop only ticks | decision inside `proposeSwap/acceptSwap` |
| Selection | LLM picks from flat `getTools()` via `generateText({tools, maxSteps})` | LLM picks from flat array via `chat.completions({tools, tool_choice:"auto"})` loop | per-behaviour `act()` scheduled at `tick_interval`; msgs routed to `handle()` by protocol | event/DM-driven + timers |
| Orchestration/modes/scoring | **NONE** | **NONE** (`while(round<max)` switch-dispatch) | **NONE** (no central planner) | **NONE** (forward state machine only) |
| Signing safety | wallet in tool execute | x402 escrow pay (`payChallenge`) | ★ ONE `DecisionMaker` thread is the SOLE wallet holder; skills CANNOT sign; checks `Terms` affordability before signing ★ | ★ escrow verifies BOTH signatures before money moves; module never holds funds ★ |
| Policy shaping | tool `description` + prompt | `SYSTEM_PROMPT(...)` + YAML config | skill `Model`/strategy + config | caller logic |
| Result | tool-call result JSON back into messages; on-chain txHash = proof | event stream + `report_result(...)` + txHash | ledger tx | escrow state machine → `completed` |

Bottom line: **thin runtime, thin flat tools, fat-ness only inside each skill's own logic, ONE isolated
signing gate, LLM picks.** "Give the model primitives + a prompt; let it decide" (= our HARD RULE #0).

## § 2. OUR ORIGINAL DIVERGENCES (audit of ~/anicca/runtime/loop + skills/earn, file:line)

| # | Divergence (original, to remove) | Where | Fix toward the common pattern |
|---|---|---|---|
| O1 ★biggest★ | LLM only ever sees `run_skill('earn')` + `sleep`; `activeSkillSlots=['earn']` hardcoded — the thin skills (hl-trade/x402-sell/token-launch) are NEVER exposed as pickable flat tools | `prompt.mjs:8-41,50` | generate the flat tool list dynamically from `registry.json` (one tool per live slot) + pass same list into prompt; LLM picks among REAL skills |
| O2 | survival-tier branching broke/lean/funded→model (no working repo has "tiers") | `tier.mjs:18-49`, `index.mjs:144,170` | drop tiers; one `config.ANICCA_MODEL`; optional inline `balance==0→free` guard; delete tier threading |
| O3 | model id semi-hardcoded (`'auto'`, `'free/gpt-oss-120b'`) | `brain.mjs:56`, `tier.mjs:18-20` | single `config.ANICCA_MODEL` resolved once; no balance→model logic |
| O4 | `earn` special-cased in executor env (`slot==='earn'`→inject EARN_MODE/STRATEGY) | `index.mjs:363-375`, `run-skill.mjs:79-95` | pass LLM-chosen args generically (`ANICCA_ARGS` JSON) for EVERY skill; no privileged slot |
| O5 ★ | `earn/run.sh` is a FAT strategy/mode/GATE/UBI orchestrator (modes discover/execute, switch over 0xwork/x402/swap/yield/invest, gas-floor leg, DCA leg, Aave leg, GATE-0 declaration, UBI send) — it does the PICKING the LLM should do | `earn/run.sh:1-243` | split into thin per-strategy tools (earn/yield, earn/swap, earn/0xwork + existing thin hl-trade/x402-sell/token-launch); LLM picks via O1's flat list; harness just executes one + returns result |
| O6 | GATE-0 second-pass classifier (re-reads ledger, correlates WAKE_ID, stamps profitable) | `index.mjs:254-269`, `earn-detect.mjs` (whole file) | skill returns its own verified $ result; loop just records it; delete earn-detect.mjs + classify block |
| O7 | naming ceremony "GATE-0 / pillars / spouts / tiers / narrate" baked into code | `run.sh:5,77,114`; `registry.json:21`; `hl-trade/SKILL.md:8` "TRADE pillar"; `x402-sell/SKILL.md:5` "X402 PRODUCT pillar" | treat every earn as "a tool call that produced verified USDC"; flatten the 5 pillars/spouts into flat tools; drop GATE-0/pillar vocab from code (docs may keep it) |
| O8 ★the differentiator★ | verify→record→**SHARE**: the SHARE is ABSENT in runtime. We verify on-chain (`run.sh:103-116`) + record (`earn-ledger.jsonl`) but NEVER push to the colony forum. SKILL.md *tells the model* to share (`hl-trade/SKILL.md:39`, `x402-sell/SKILL.md:36`) but no tool/loop step does it | `runtime/loop/*` (grep: no forum/share path) | add a thin `share` tool (post earn-line to anicca-repo Issues); auto-call after a verified record. Closes verify→record→SHARE (= task #45) |
| O9 ★not-a-build★ | UBI is co-located INSIDE `skills/earn/` (mixed with earn = INFLOW) and called as a side-effect by run.sh — single-responsibility violation. **NOTE: the UBI mechanism is already BUILT + VERIFIED by another CC** (`distribute-ubi.mjs`, `execute-ubi.py`, `ubi-watcher.mjs`, `ubi-payout-watcher.mjs`, `bank-payout-watcher.mjs` (VCSDD adversary-converged FIND-A..D), `gmo-furikomi.mjs`, `lib/ubi.mjs`, `lib/bank-fanout.mjs`, `lib/bank-recipients.mjs`). The `economy/ubi` registry slot is only a `SLOT.md` stub (declared, empty). | all in `skills/earn/`; `run.sh:58-64,118-120,239` calls `distribute-ubi.mjs` | ★ FIX = SEPARATE, not build: MOVE the verified UBI files out of `skills/earn/` into `skills/ubi/` (OUTFLOW); earn CALLS ubi cross-skill ("earn → distribute a share"); the ONLY coupling point is that call. Promote shared libs (`transfer/ledger/identity-guard/record/usdc/verify-tx`) to `skills/_shared/lib/`. Flip the registry slot to `ubi` `status:"live"`. Consolidate the OLD `~/.openclaw/skills/anicca-payout-wallet/` (exists, separate, read-only — never edited) onto mother's `skills/ubi/` as canonical. ★ |
| O10 | loop-detect idle guard (3 identical actions→sleep) — original addition | `index.mjs:156-165`, `loop-detect.mjs` | acceptable thin safety rail; keep or move to generic middleware (minor) |

### Already CORRECT (thin, flat, model-decides — keep as the template)
`hl-trade/hl.py`, `token-launch/launchpad.py`, `x402-sell/serve.mjs`, `parse-tool-call.mjs`. These are
exemplary "tool + onboarding, no decision baked in." The fix = make the whole loop look like these.

## § 3. TARGET ARCHITECTURE (after removing O1-O10)
```
identity + ONE wallet (sole signer, isolated gate) 
  + FLAT tool list (auto-generated from registry.json — every live skill = 1 thin tool):
      [ earn_yield, earn_swap, earn_hl_trade, earn_x402_serve, earn_token_launch, earn_0xwork,
        cook_find_new_earner, share, ubi, spawn, ... ]
  + ONE prompt: "you have a wallet + these tools; earn money, no human in the loop; pick a tool"
  ↓ LLM picks one tool, fills args (no tier, no mode, no GATE, no router)
  ↓ tool executes → returns {result, verified $ (tx 0x1 + USDC delta)}
  ↓ loop records the returned result to the ledger
  ↓ share tool pushes it to the colony forum (anicca repo Issues) so all peers see it
  signing safety: a single gate validates the tx before money moves (AEA DecisionMaker / escrow style)
```

## § 4. Fix tasks
O1/O4/O5/O6/O7 → "flatten runtime to thin tools" task. O2/O3 → "drop tiers, single model" task.
O8 → task #45 (verify→record→SHARE) ✅DONE. O9 → SEPARATE the already-built UBI out of earn into
skills/ubi/ (move, not build — task #48). O10 → minor/optional.
See the task list (#46+).

## § 5. Changelog
| Date | Change |
|---|---|
| 2026-06-21 | Created from reading the real code of goat-sdk/goat, AGICitizens/agent-adapter, fetchai/agents-aea, unicity-sphere/sphere-sdk (3 parallel agents) + auditing our runtime/loop+skills/earn. Locked the common pattern (thin flat tools + one isolated signing gate + LLM picks + verify/record/share) and the 10 original divergences with file:line + fixes. |
