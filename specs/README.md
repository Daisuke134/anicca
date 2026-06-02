# `anicca-oss/specs/` — single source of truth

All architectural decisions for Anicca v3 (NHOSS) live in this folder. The
mission is one line:

> **★ Anicca reduces human suffering without humans in the loop. ★**

| File | Status | What it is |
|---|---|---|
| [`00-MASTER.md`](./00-MASTER.md) | ★ AUTHORITATIVE | The v3 architecture. 4 layers (Virtuals service / Conway runtime / our skills / LLM brain). Read this first. |
| [`01-EARN-AND-UBI.md`](./01-EARN-AND-UBI.md) | DEEP-DIVE | WHERE money comes from (5 spouts) + WHERE it goes (3 sinks) + HOW UBI reaches recipients (4 channels). |
| [`02-IMITATE-AND-COOK.md`](./02-IMITATE-AND-COOK.md) | DEEP-DIVE | HOW Anicca decides what to do. Imitation instinct + cook loop. |
| [`03-SELF-AWARE-EVAL.md`](./03-SELF-AWARE-EVAL.md) | ★ DEEP-DIVE | ★ The meta-awareness layer (= L2d). 5+1 survival conditions, 3-place eval loop, L1-L5 fix-the-fix doctrine. **Without this, the other three specs fail.** |
| [`04-PUBLIC-RELEASE-PREP.md`](./04-PUBLIC-RELEASE-PREP.md) | active (operational) | Git squash + leak audit + grandma-E2E playbook for flipping `anicca-oss` public. Note: § 9 "rename `~/.openclaw` → `~/.dais-companion`" is SUPERSEDED by `00-MASTER.md` § 8.1 (= openclaw stays put). |
| [`05-SERVER-NATIVE-DEPLOY.md`](./05-SERVER-NATIVE-DEPLOY.md) | ★ DEEP-DIVE | ★ The 3 deployment modes (hosted SaaS / Akash user-owned / Mac mini genesis) + Vending-Bench-2-inspired model fitness loop. Verified from `cloudflare/moltworker` src + Conway `replication/spawn.ts`. Confirms self-spawning is **already** cloud-native. **§ 1 / § 2 currently reference Conway runtime — to be patched to Hermes after `07-HERMES-PIVOT.md` is approved.** |
| [`06-PROJECT-TRACKING-HEARTBEAT.md`](./06-PROJECT-TRACKING-HEARTBEAT.md) | ★ DEEP-DIVE | ★ Anicca as project-tracking, context-aware, follow-through-capable agent (= no more "one-shot reactor"). Multi-step / multi-day / multi-thread task model. |
| [`07-HERMES-PIVOT.md`](./07-HERMES-PIVOT.md) | ★ DEEP-DIVE (substrate) | The v3.1 pivot, source-code verified 2026-06-02: L3 = **Hermes Agent** (NousResearch, replaces Conway), L4 = **Coinbase AgentKit CDP Smart Wallet** (replaces Virtuals — Virtuals deferred until OSS code published), brain primary = **Kimi K2.6 via OpenRouter** (USDC-payable, replaces DeepSeek-direct). Supersedes Conway-specific paragraphs in `00-MASTER.md` § 1 / § 2 / § 3 / § 4 / § 9 (patches pending). |
| [`08-INBOX-RESPONDER-LOOP.md`](./08-INBOX-RESPONDER-LOOP.md) | ★ DEEP-DIVE | The v3.2 inbox loop, born from Dais's 2026-06-03 race call. Stack: **Inbox Zero** (Elie, AGPL, 11k stars — has the Reply Zero followup tracker spec 06 v1 said didn't exist) + **Mastra** (suspend/resume durable workflows) + **Composio** (250+ tool adapters) + **Hermes** (24/7 daemon) + Conway state.db reuse. ≈ 600 LOC of glue, not a from-scratch framework. Supersedes spec 06 § 1-§ 7 "build it ourselves" stance — now corrected in spec 06 § 10 (v2 PIVOT). |
| `archive/` | historical | Pre-v3 specs (`ANICCA_AUTONOMY_SPEC.md`, `ANICCA_OSS_MASTER_SPEC.md`, `SELF_HEALING_SPEC.md`, etc.). Superseded but kept for context. |

## Reading order for a new implementer

1. `00-MASTER.md` § 0 (Mission), § 1 (Architecture), § 8 (Naming), § 6 (Constitution) — the big picture.
2. The deep-dive for the layer you're touching:
   - Touching revenue / UBI? → `01-EARN-AND-UBI.md`.
   - Touching the cook loop / imitation strategy? → `02-IMITATE-AND-COOK.md`.
   - Touching anything that ships output, fixes a cron, or evaluates an agent? → `03-SELF-AWARE-EVAL.md`.
   - Flipping the repo public, doing leak audit, or grandma E2E install? → `04-PUBLIC-RELEASE-PREP.md`.
   - Touching how/where Anicca is deployed? → `05-SERVER-NATIVE-DEPLOY.md`.
   - Touching multi-step / multi-day project tracking? → `06-PROJECT-TRACKING-HEARTBEAT.md`.
   - Touching the L3 runtime (Hermes) or L4 wallet (AgentKit) substrate? → `07-HERMES-PIVOT.md`.
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
