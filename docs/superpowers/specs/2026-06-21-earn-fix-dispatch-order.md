# SPEC — Earn-fix dispatch, in execution order (2026-06-21)

The single ordered plan to make anicca EARN with each tool + show it real-time. Read this + `docs/patch.md`
(literal diffs) + `docs/REFERENCE-REPOS.md` (sources). Do them IN THIS ORDER. Every patch cites the
repo:file:line it was copied/tweaked from. No source = not approved.

## Done already this session
- ✅ Killed rogue Akash instance (dseq 27230087, tx 8AB31279) sharing wallet 0xa3CDd4 on paid model → name-flip + money-waste stopped.
- ✅ PATCH 5: removed `revenue_by_source` from telemetry (Supabase had no column → 502 froze dashboard). Dashboard live again (anicca-a3cdd4, 2-min posts). commit 911627d.

## ORDER (the only correct sequence)

### ORDER-1 = PATCH 1-4 — Beefy/Fluid auto highest-APY (task #58)
File `skills/earn/execute-yield.mjs`. Beefy 6.1% #1 → Fluid 5.36% #2 → Aave #3, no opt-in.
SOURCE: AEA `fetchai/agents-aea:.../tac_negotiation/strategy.py:413,485` + GOAT `goat-sdk/goat:plugins/lulo/src/lulo.service.ts:6-26` + our `docs/earn-verification-2026-06-18.md:112,233`.
VERIFY: withdraw $1 from Aave → run → Beefy deposit status 0x1 + on-chain Beefy balanceOf > 0.

### ORDER-2 = PATCH 6 — split fat `earn` into per-action tools (task #59)
`skills/registry.json` + `runtime/loop/prompt.mjs` + `runtime/loop/index.mjs`. Slots: yield / hl_trade /
x402_sell / token_launch / cook / self-issue-dev. Model sees every tool, picks via tool_choice:auto.
SOURCE: GOAT `core/src/classes/ToolBase.ts` + `utils/getTools.ts` + `adapters/vercel-ai/src/index.ts`;
agent-adapter `AGICitizens/agent-adapter:apps/buyer-agent/src/tools.ts:16-81` + `loop.ts:64-144`.

### ORDER-3 = PATCH 7+8 — loop_detect escape + ledger truth (task #60)
`runtime/loop/index.mjs:179` clear window → re-evaluate; `skills/earn/run.sh` record only on status 0x1.
SOURCE: AEA `aea/aea.py:399` + `strategy.py:485`.

### ORDER-4 = PATCH R1-R3 — real-time per-source revenue on the dashboard (task #61)
R1 Supabase `ALTER TABLE instances ADD COLUMN revenue_by_source jsonb` (needs SERVICE_ROLE_KEY);
R2 `runtime/dashboard/telemetry-poster.mjs:105` re-add `revenue_by_source: earn.bySource`;
R3 `apps/landing/app/[id]/AgentClient.tsx` add "Earned by source" panel (copy the existing Cell/grid).
SOURCE: OUR dashboard pipeline; real-time = the existing 4s poll in AgentClient.
HONEST: shows $0/source until anicca actually realises a gain — it's the window, ORDER-1/2 is the engine.

### ORDER-5 = LIVE verify per-tool earnings → 6-3 + article (task #62)
Run anicca; read each tool's realised $ from the dashboard's revenue_by_source; write block 6-3 with
real numbers; publish `docs/articles/2026-06-21-automaton-pays-for-itself.md`. If still not net-positive
on free glm-4.7 after the engine works, run the free → auto → premium comparison (the recipe experiment).

## The problems this sequence fixes (Dais's list)
not earning with Beefy (ORDER-1) · not using Fluid (ORDER-1) · not trading/HL realised (ORDER-2 hl_trade
tool + close) · not selling x402 products (ORDER-2 x402_sell tool + demand) · not exploring/sharing
(ORDER-2 cook + share) · not self-improving (ORDER-2 self-issue-dev in the loop) · tools unused (ORDER-2)
· loop spin (ORDER-3) · ledger lies (ORDER-3) · revenue not shown real-time (ORDER-4).
