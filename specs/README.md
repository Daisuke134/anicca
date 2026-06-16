# `anicca-oss/specs/` — single source of truth

All architectural decisions for Anicca v3 (NHOSS) live in this folder. The
mission is one line:

> **★ Anicca reduces human suffering without humans in the loop. ★**

| File | Status | What it is |
|---|---|---|
| [`00-MASTER.md`](./00-MASTER.md) | ★ AUTHORITATIVE (locked 2026-06-11) | The current architecture. Engine = **Conway automaton** (ReAct loop + heartbeat daemon), run in local-mode; compute = **ClawRouter / BlockRun** USDC x402; native primitives = wallet / x402 / spawn_child / constitution. Read this first. |
| [`01-EARN-AND-UBI.md`](./01-EARN-AND-UBI.md) | DEEP-DIVE | WHERE money comes from (5 spouts) + WHERE it goes (3 sinks) + HOW UBI reaches recipients (4 channels). |
| [`02-IMITATE-AND-COOK.md`](./02-IMITATE-AND-COOK.md) | DEEP-DIVE | HOW Anicca decides what to do. Imitation instinct + cook loop. |
| [`03-SELF-AWARE-EVAL.md`](./03-SELF-AWARE-EVAL.md) | ★ DEEP-DIVE | ★ The meta-awareness layer (= L2d). 5+1 survival conditions, 3-place eval loop, L1-L5 fix-the-fix doctrine. **Without this, the other three specs fail.** |
| [`04-PUBLIC-RELEASE-PREP.md`](./04-PUBLIC-RELEASE-PREP.md) | active (operational) | Git squash + leak audit + grandma-E2E playbook for flipping `anicca-oss` public. Note: § 9 "rename `~/.openclaw` → `~/.dais-companion`" is SUPERSEDED by `00-MASTER.md` § 8.1 (= openclaw stays put). |
| [`05-SERVER-NATIVE-DEPLOY.md`](./05-SERVER-NATIVE-DEPLOY.md) | ★ DEEP-DIVE | ★ The 3 deployment modes (hosted SaaS / Akash user-owned / Mac mini genesis) + Vending-Bench-2-inspired model fitness loop. Verified from `cloudflare/moltworker` src + Conway `replication/spawn.ts`. Confirms self-spawning is **already** cloud-native. **§ 1 / § 2 reference the Conway automaton runtime — which is the CURRENT engine (the 07 Hermes pivot was reversed), so no Hermes patch is needed.** |
| [`06-PROJECT-TRACKING-HEARTBEAT.md`](./06-PROJECT-TRACKING-HEARTBEAT.md) | ★ DEEP-DIVE | ★ Anicca as project-tracking, context-aware, follow-through-capable agent (= no more "one-shot reactor"). Multi-step / multi-day / multi-thread task model. |
| [`07-HERMES-PIVOT.md`](./07-HERMES-PIVOT.md) | ⚠️ SUPERSEDED (historical) | The 2026-06-03 proposal to pivot the runtime to **Hermes Agent** + 10 specialist profiles per instance. **Reversed** — the project runs the **Conway automaton** directly (its wallet/x402/spawn/constitution primitives are native, so nothing was "ported into Hermes"). Kept only as a record of the path considered and rejected. Salvaged ideas (CDP wallet, USDC-x402 compute = ClawRouter/BlockRun, Daytona/Akash hosts, self-replication) live in `00-MASTER.md` / `THESIS.md`. |
| [`08-INBOX-RESPONDER-LOOP.md`](./08-INBOX-RESPONDER-LOOP.md) | ARCHIVED-WITHIN-A-DAY | Spec 08 proposed Inbox Zero + Mastra + Composio on a Hermes daemon. Same-day taste-test (= 2026-06-03) replaced this stack with **memU + AgentMail + camofox**, and the runtime later locked to the **automaton** (not Hermes — see 16/00). The architectural diagram in spec 08 § 1 is still pedagogically useful but the substrate choices are superseded by specs 10 + 11 and by the automaton runtime. |
| [`09-EARN-X402-LIVE.md`](./09-EARN-X402-LIVE.md) | ★ CHUNK-SPEC (Wave 2) | Anicca's first sovereign revenue endpoint. HTTP 402 + USDC micropayment server. Receipt issuance + agentic.market listing. Agent: anicca-earner-x402. Worktree `.worktrees/earn-x402/`. |
| [`10-AGENTMAIL-INBOXES.md`](./10-AGENTMAIL-INBOXES.md) | ★ CHUNK-SPEC (Wave 1) | Per-Anicca-instance custom inboxes + push webhook → heartbeat in <60s + Reply Zero analog in state.db. Replaces spec 08's Inbox Zero choice. Agent: anicca-inbox-keeper. Worktree `.worktrees/agentmail/`. |
| [`11-MEMU-HEARTBEAT.md`](./11-MEMU-HEARTBEAT.md) | ★ CHUNK-SPEC (Wave 1) | memU integration (DeepSeek + Ollama, verified 2026-06-03 Tanaka E2E). heartbeat retrieves project context + memorizes today. Replaces spec 06 v1 + spec 08's memory stack. Agent: anicca-memory-weaver. Worktree `.worktrees/memu/`. |
| [`12-CUSTOM-ADAPTERS.md`](./12-CUSTOM-ADAPTERS.md) | ★ CHUNK-SPEC (Wave 1) | Lancers / Coconala / Bland.ai / AgentMail thin adapters in the standard `SKILL.md` skill format (loaded by the automaton skill registry). camofox-backed for JP gig platforms. Agent: anicca-adapter-smith. Worktree `.worktrees/adapters/`. |
| [`13-CLOUD-SPAWN-002.md`](./13-CLOUD-SPAWN-002.md) | ★ CHUNK-SPEC (Wave 2) | anicca-002 alive on Akash with own AgentKit wallet + own AgentMail inbox + constitution hash verify. First child of the colony. Agent: anicca-spawn-mother. Worktree `.worktrees/akash/`. |
| [`14-UBI-FIRST-PAYOUT.md`](./14-UBI-FIRST-PAYOUT.md) | ★ CHUNK-SPEC (Wave 3) | First 1 USDC payout to a real charity recipient + ledger row on aniccaai.com/donation. Proves the mission loop (suffering reduction with no human in the loop). Agent: anicca-redistributor. Worktree `.worktrees/ubi/`. |
| [`15-FRICTION-FIXER.md`](./15-FRICTION-FIXER.md) | ★ CHUNK-SPEC (Wave 1, highest priority) | A0.5.5 enforcer: detects "user-click / OAuth interactive / device-code / configure X" surfaces in Anicca's outbound messages and replaces them with the correct auto-fix path BEFORE they reach the user. Agent: anicca-friction-fixer. Place: `~/.openclaw/skills/anicca-friction-fixer/` (runtime store, main-direct per HARD RULE #0 exception). |
| [`../control-room/`](../control-room/) | ★ OPERATIONAL LAYER (= sibling to specs/, **not** a spec file) | Shann-style control room scaffold for Anicca v3.4. 10 specialist profile docs (inventory / docker / env-map / runbook / backup / soul each = 60 files) + shared/{architecture,commands,security} + api-keys-sop + orchestrator-and-fleet-skills + templates for new-profile + new-instance. Zero raw secrets, zero PII. Specs answer **what / why**; control-room answers **how-to-run**. See per-profile config that spec 07 § 2.6 references. |
| `archive/` | historical | Pre-v3 specs (`ANICCA_AUTONOMY_SPEC.md`, `ANICCA_OSS_MASTER_SPEC.md`, `SELF_HEALING_SPEC.md`, etc.). Superseded but kept for context. Also: post-v3 archive moves (`CONWAY_RUNTIME_DEEPDIVE.md` 2026-06-02, `VIRTUALS_PROTOCOL_PLAN.md` 2026-06-02) per 07-HERMES-PIVOT.md. |

## Reading order for a new implementer

1. `00-MASTER.md` § 0 (Mission), § 1 (Architecture), § 8 (Naming), § 6 (Constitution) — the big picture.
2. The deep-dive for the layer you're touching:
   - Touching revenue / UBI? → `01-EARN-AND-UBI.md`.
   - Touching the cook loop / imitation strategy? → `02-IMITATE-AND-COOK.md`.
   - Touching anything that ships output, fixes a cron, or evaluates an agent? → `03-SELF-AWARE-EVAL.md`.
   - Flipping the repo public, doing leak audit, or grandma E2E install? → `04-PUBLIC-RELEASE-PREP.md`.
   - Touching how/where Anicca is deployed? → `05-SERVER-NATIVE-DEPLOY.md`.
   - Touching multi-step / multi-day project tracking? → `06-PROJECT-TRACKING-HEARTBEAT.md`.
   - Touching the runtime substrate or wallet? → `00-MASTER.md` (automaton, current) + `16-RUNTIME-CODE-TRUTH.md` (the source-level comparison). `07-HERMES-PIVOT.md` is the superseded Hermes proposal, history only.
   - Operating the fleet day-to-day (restart a profile / rotate a key / spawn a new instance)? → `../control-room/`.
3. `00-MASTER.md` § 9 (Migration plan) for which sub-agent owns which file.
4. `00-MASTER.md` § 12 (Verification gates) before claiming "done".

## Editing rules

1. **One source of truth.** If a value (model name, port, threshold, channel
   name) appears in both `00-MASTER.md` and a deep-dive, the master wins.
   Deep-dives say "see § N of 00-MASTER.md" rather than restate.
2. **Never silently delete a section.** Move reversed decisions to `archive/`
   with a date and a one-line reason.
3. **Date every change at the top of `00-MASTER.md`.** Bump the version.
4. **A new top-level spec belongs as a section of 00-MASTER unless it's
   100+ lines of self-contained doctrine.** 01, 02, 03, 04, 05 all cleared
   that bar. The next one needs to clear it too.
5. **The mission line is hardcoded.** If a future spec change reads as
   "Anicca's mission is now to [X]", and [X] is not "reduce human suffering
   without humans in the loop", the change is wrong.
