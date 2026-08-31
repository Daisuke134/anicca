# GA-11B Hosted General Agent Worker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the existing capability worker execute a canonical `general-agent.work` job through one injected bounded specialist and persist a safe structured receipt.

**Architecture:** Add one loop adapter that validates the existing Goal WorkItem shape, delegates semantic work to `runBoundedSpecialist`, and validates the returned receipt. Register it under manifest loop ID `mr-bot.general-agent`; the canonical runtime job continues to use `mr-bot.manager` unchanged.

**Tech Stack:** Node.js built-ins, existing loop adapter registry, `goal-work-item.js`, runtime worker, Node test runner.

**Spec:** `docs/superpowers/specs/2026-08-01-dais-mr-bot-five-phase-execution-spec.md` (GA-11).

## Global Constraints

- No model/provider selection, keyword judgment, goal plaintext, secret value, phone, or chat ID in the adapter.
- Missing specialist or malformed receipt fails before runtime completion.
- `effect_class=none`; this adapter never performs or claims an external effect.
- Production worker capability remains disabled until GA-11C composes tenant-specific services.

---

### Task 1: Bounded WorkItem adapter

**Files:**
- Create: `apps/mr-bot/lib/general-agent-work-adapter.js`
- Test: `apps/mr-bot/lib/general-agent-work-adapter.test.js`
- Modify: `apps/mr-bot/config/loop-adapters.json`
- Modify: `apps/mr-bot/lib/loop-adapter-registry.test.js`

**Interfaces:**
- Consumes: canonical `general-agent.work` job; injected `runBoundedSpecialist({tenant_id, job_id, goal_ref})`.
- Produces: `createGeneralAgentWorkLoopAdapter(deps)` with `plan/execute/reconcile/verify/report`.

- [x] **Step 1: Write RED tests**

Use one canonical job from `buildGoalWorkItem`. Assert `execute` calls the specialist once with only tenant/job/goal refs and accepts this exact receipt shape:

```js
{
  kind: "general_agent_work",
  status: "planned",
  tenant_id: "tenant-a",
  job_id: "goal:hosted-goal-1",
  goal_ref: "intent-entry://tenant-a/hosted-goal-1",
  execution_id: "bounded-execution-1",
  next_job_refs: ["runtime-job://tenant-a/next-job-1"],
}
```

Assert missing specialist, wrong tenant/job/goal ref, raw goal/secret fields, or malformed next-job refs fail. Update registry expectations from 10 to 11 adapters and assert the capability is exposed without production worker enablement.

- [x] **Step 2: Run RED**

```bash
node --test \
  apps/mr-bot/lib/general-agent-work-adapter.test.js \
  apps/mr-bot/lib/loop-adapter-registry.test.js
```

Expected: missing module and manifest length/capability failures.

- [x] **Step 3: Implement the adapter**

Validate job fields exactly: `loop_id=mr-bot.manager`, `capability=general-agent.work`, `effect_class=none`, `effect_key=null`, `max_attempts=1`, and one `goal_ref` beginning with the encoded tenant prefix. `execute` awaits the injected specialist, rejects any receipt key outside the seven listed fields, and returns `{receipt}`. `verify` revalidates receipt/job identity; `report` returns only status, execution ID, and next-job count; `reconcile` returns `{state:"unknown"}` because no external effect exists.

- [x] **Step 4: Register and verify**

Add the manifest definition before `marketplace-application`:

```json
{
  "adapter_id": "general-agent-work",
  "loop_id": "mr-bot.general-agent",
  "capability": "general-agent.work",
  "effect_classes": ["none"],
  "module_ref": "lib/general-agent-work-adapter.js",
  "factory_export": "createGeneralAgentWorkLoopAdapter"
}
```

Run the RED command plus `apps/mr-bot/scripts/runtime-up.test.js` when dependencies are available.

- [x] **Step 5: Commit and push** (`f7b6853ea`)

```bash
git add apps/mr-bot/lib/general-agent-work-adapter.js \
  apps/mr-bot/lib/general-agent-work-adapter.test.js \
  apps/mr-bot/config/loop-adapters.json \
  apps/mr-bot/lib/loop-adapter-registry.test.js
git commit -m "feat: run hosted general-agent work"
git push origin docs/general-agent-simple-scope-20260828
```
