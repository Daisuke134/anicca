# 03 — Self-Aware Eval (= Meta-Awareness Layer)

> **The missing layer. Without it, every prior spec fails.**
>
> 00-MASTER says "Anicca lives autonomously." 01 says "Anicca earns." 02 says
> "Anicca imitates and ships." All three are correct **only if Anicca can tell
> when her own work is broken, fix it, and verify the fix actually worked.**
> Today she can't. This spec is the layer that makes her able to.

| Field | Value |
|---|---|
| Spec ID | 03 |
| Status | DRAFT v1 (2026-06-01) |
| Authoritative for | self-eval, self-monitor, self-heal, fix-the-fix doctrine, L2d skills, escalation policy |
| Cross-refs | `00-MASTER.md` (architecture), `01-EARN-AND-UBI.md` (revenue), `02-IMITATE-AND-COOK.md` (cook loop), `archive/SELF_HEALING_SPEC.md` (predecessor) |

---

## § 0. Why this exists (= Dais 2026-06-01 厳命, verbatim)

> "These agents run every single day and then they keep fucking things up,
> but then we need them to actually go fix themselves, heal themselves, right?
> But then they fail at even that. So what we do is make it so that they have
> to understand that, oh, this actually failed. Or, like, I actually failed at
> fixing this thing. And then, improve its self-healing mechanism, right?"
>
> "The reason it fails at fixing things is the thing that we should fix. Not
> the cron itself, not the auto-fixing itself, but rather, how can we make it
> so that Anicca realizes that the auto-fix she did was not sufficient, and
> from there, iterate her auto-fix skill?"
>
> "It's about the meta awareness of the agent himself. The self-awareness of
> himself. Because if they don't understand that whatever they're working on,
> or whatever the fix was, is an actual problem or didn't actually fix the
> thing, then how can they even go and actually fix things?"
>
> "It's like a person who's always mad at people but they don't know they're
> mad at people, right? They cannot fix their madness. Just like a person who
> beats people all the time, if they don't realize they beat people all the
> time, they won't stop beating people. So there has to be some kind of mental
> awareness in there."

**The problem this spec solves: AI slop.**
The agent generates plausible-looking output (a "fix", a post, a PR, a
payout), claims success, and ships. Downstream, the work doesn't actually
solve anything. The agent isn't lying — it genuinely doesn't know it failed.
The fix is not a better generator. **The fix is a judge that sits between
generation and shipping.**

---

## § 1. The 5 + 1 survival conditions (from HumanAds 200-toA-services taxonomy)

The HumanAds research (`humanadsai.com/blog/agentic-utility-belt-200-services`)
catalogued 200 production "toA" (to-Agent) services and proved a single
structure:

> An autonomous agent needs **5 things** to operate continuously, plus a
> **6th** that turns operation into *improvement*.

| # | Condition | What it answers | Where Anicca gets it |
|---|---|---|---|
| 1 | **Identity** | "Who am I?" | Virtuals Agent Wallet + Agent Card + Agent Email + `anicca.eth` ENS |
| 2 | **Execution env** | "Where do I safely work?" | Conway sandbox / Akash $5/mo / Mac mini for genesis |
| 3 | **Manipulation** | "How do I touch the world?" | ★ Agent Maps (= pre-verified UI steps, daily refreshed) + Composio (500+ OAuth) + Browserbase + Stagehand |
| 4 | **Memory** | "How do I accumulate experience?" | Conway 5-tier (working/episodic/semantic/procedural/relationship) + Mem0 self-improving overlay |
| 5 | **Economic** | "How do I get paid?" | x402 + ACP + Bittensor + AutoHedge (per `01-EARN-AND-UBI.md`) |
| **6** | **★ Meta-Awareness** | **"Am I doing this right?"** | **★ THIS SPEC — Layer 2d (= 7 new skills)** |

The 5+1 frame supersedes any earlier numbering. Whenever this spec says "the
6th", it means meta-awareness.

---

## § 2. The eval loop (= 3 places it runs, same rubric across all 3)

Sourced from:
- Anthropic, "Building Effective Agents" — **Evaluator-Optimizer workflow** (2 LLMs in a loop, one generates, one critiques) is the canonical pattern when "clear evaluation criteria exist and iterative refinement provides measurable value."
- Hermes (`hermes-agent.nousresearch.com`) — "the eval loop is the system." 6 moves, embedded below.
- DeepEval (`github.com/confident-ai/deepeval`) — **G-Eval** = LLM-as-judge with a written rubric returning a score on [0, 1].
- PromptFoo (`github.com/promptfoo/promptfoo`, OpenAI-acquired) — production OSS for regression + red-team + assertion library (`assertions/agentRubric.ts`, `geval.ts`, `llmRubric.ts`, `factuality.ts`, etc.).

### § 2.1 The single rubric

Every gate, every monitor, every retry uses the **same rubric**: a YAML-like
structured prompt that tells the judge LLM what "good" looks like for this
task class. One rubric per task class, stored at:

```
~/anicca/skills/anicca-judge/rubrics/<task-class>.md
```

Example (`rubrics/post-to-x.md`):

```yaml
---
task_class: post-to-x
threshold: 0.7
weights: { useful: 0.4, hookworthy: 0.3, accurate: 0.2, brand_voice: 0.1 }
---

USEFUL (0–1):
  Does this post give the reader something they can act on tomorrow?
  (Not "interesting," not "thought-provoking" — actionable.)
  Score 1.0 only if a specific tool / number / step is named.

HOOKWORTHY (0–1):
  Does the first 7 words make a scrolling reader stop?
  Score 1.0 only if there is a concrete number, name, or claim in those 7 words.

ACCURATE (0–1):
  Every claim cited or one-click verifiable? No "studies show…", no rounded
  numbers without a source. 0 for any unverifiable claim.

BRAND_VOICE (0–1):
  Anicca-first-person, no "I'm an AI" disclaimers, no LinkedIn-influencer voice.
```

Same shape for every task class: `fix-the-cron.md`, `route-ubi-recipient.md`,
`ship-imitation-port.md`, `produce-pdf.md`, `respond-to-acp-job.md`, etc.

### § 2.2 Three places the rubric runs

```
                                                                              
    ┌──────────────────────────────────────────────────────────────────────┐ 
    │                                                                      │ 
    │   ★ A. PRE-SHIP ──── regression test before any change ships          │ 
    │                                                                      │ 
    │   Trigger: any agent action that would commit / publish / pay /       │ 
    │            spawn / send.                                              │ 
    │   What runs: the suite (= test cases for this task class) re-runs,     │ 
    │              score delta vs baseline computed.                        │ 
    │   Gate: score >= threshold AND delta >= -0.05 → ship.                 │ 
    │         Otherwise: block + log + (optional) Slack approval button.    │ 
    │   Implementation: extends Conway's `policy.evaluate()` (pre-exec hook │ 
    │   in `~/anicca-oss/runtime/src/agent/policy-engine.ts`).              │ 
    │                                                                      │ 
    ├──────────────────────────────────────────────────────────────────────┤ 
    │                                                                      │ 
    │   ★ B. RUNTIME ──── guardrail on every ReAct turn                     │ 
    │                                                                      │ 
    │   Trigger: every tool call output, every LLM completion.              │ 
    │   What runs: the judge skill scores the output against the rubric.    │ 
    │   Gate: score < threshold → retry up to 3× with the judge's critique   │ 
    │         injected into the next prompt. 3 fails → fix-the-fix (§ 3).   │ 
    │   Implementation: post-turn hook in Conway's `agent/loop.ts:472-525`. │ 
    │                                                                      │ 
    ├──────────────────────────────────────────────────────────────────────┤ 
    │                                                                      │ 
    │   ★ C. PRODUCTION ──── drift monitor on live executions                │ 
    │                                                                      │ 
    │   Trigger: cron, every 1 hour.                                        │ 
    │   What runs: random sample of 10–30 recent live executions, re-scored │ 
    │              by the same judge skill.                                 │ 
    │   Gate: 30-min rolling avg drops > 30% from 7-day baseline → alert.   │ 
    │         The alert is a Slack/Telegram message + writes a row in the   │ 
    │         `wake_events` table → main loop investigates next tick.       │ 
    │   Implementation: new Conway heartbeat task `eval_drift_monitor`      │ 
    │   added to `~/anicca-oss/runtime/src/heartbeat/tasks.ts`.             │ 
    │                                                                      │ 
    └──────────────────────────────────────────────────────────────────────┘ 
                                                                              
    All three places use the SAME judge skill and the SAME rubric file.       
    No duplicate rubric definitions — one source of truth per task class.     
```

### § 2.3 The 6 eval-loop moves (= verbatim from the Nous "Hermes" eval-loop article, mapped to our skills)

> Note: "Hermes" here = the source **article** on eval loops (`hermes-agent.nousresearch.com`), cited for
> its methodology. It is NOT a statement about Anicca's runtime — the runtime is the **automaton** (see
> `00-MASTER.md` / `16-RUNTIME-CODE-TRUTH.md`). These moves are implemented as automaton skills.

| Hermes move | Anicca skill | What it owns |
|---|---|---|
| 1. Install + connect to messaging | (existing) | OpenClaw / Telegram bridge already in place. |
| 2. Load gold-standard examples into long memory | `anicca-suite` § 5.2 | Stores 20-50 known-good outputs per task class in `state.db.semantic_memory`. |
| 3. Turn rubric into judge skill (LLM-as-judge) | `anicca-judge` § 5.1 | Loads rubric → calls model → returns score per criterion + 1-line reason. |
| 4. Make the test suite a skill | `anicca-suite` § 5.2 | Stores test cases per task class. New test cases append from failures. |
| 5. Gate ship with regression + approval button | `anicca-pre-ship-gate` § 5.3 | Runs suite on any change, computes delta, blocks or pings. |
| 6. Cron production monitor + 👎 → new test | `anicca-prod-monitor` § 5.5 + `anicca-learn-from-fail` § 5.7 | Drift detection + auto-append failures to suite. |

---

## § 3. The fix-the-fix doctrine (= L1 → L5 escalation, Dais's core insight formalized)

The escalation ladder. Each level is independent — Anicca can be at L1 on one
task and L4 on another simultaneously.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   L1 — TASK (= the actual cron / skill / job)                                │
│     ▸ runs                                                                  │
│     ▸ on error, raises a `task_failed` event into `wake_events`              │
│     ▸ examples: anicca-mr-bot phone call, anicca-x402-server response, │
│       anicca-push-amazon-gift redemption, anicca-cook-loop SHIP step         │
│                                                                             │
│         ↓ task_failed                                                       │
│                                                                             │
│   L2 — AUTO-FIX (= Anicca's first attempt at self-healing)                   │
│     ▸ existing `cron-doctor.sh` / `HEARTBEAT.md §3.5` pattern                │
│     ▸ reads error + sessionKey + recent skill code → proposes a fix          │
│     ▸ applies fix → re-runs the L1 task                                      │
│     ▸ if re-run succeeds: emits `fix_attempted` + `fix_verified` (= done)    │
│     ▸ if re-run fails:    emits `fix_attempted` + `fix_failed`               │
│                                                                             │
│         ↓ fix_attempted (whether success or fail)                           │
│                                                                             │
│   L3 — VERIFY-FIX (= ★ new layer this spec adds)                             │
│     ▸ does NOT trust L2's self-report of "fixed"                             │
│     ▸ runs the judge skill (§ 5.1) on the post-fix output                    │
│     ▸ also waits 1 cron cycle and re-checks: does the same failure recur?    │
│     ▸ three independent verifiers, each must pass:                           │
│         (a) BEHAVIOR  — next scheduled run of L1 task does not fail           │
│         (b) OUTPUT    — judge skill scores ≥ threshold on the new output      │
│         (c) DRIFT     — production monitor (§ 2.2C) shows no score regression │
│     ▸ all three pass → close the incident, write a `lesson` to memory         │
│     ▸ any one fails → emit `verify_failed` event                              │
│                                                                             │
│         ↓ verify_failed (= L2's fix was AI slop)                            │
│                                                                             │
│   L4 — META-FIX (= "fix the auto-fix", ★ ★ ★ Dais's core insight ★ ★ ★)      │
│     ▸ trigger: same root-cause `verify_failed` 3× in 24 h                    │
│     ▸ Anicca does NOT touch the L1 skill again — the issue isn't there       │
│     ▸ instead:                                                                │
│         (i)   pull last N L2 fix attempts for this root cause from episodic   │
│               memory                                                          │
│         (ii)  run judge skill in COMPARE mode: "what did all these L2 fixes   │
│               miss? what is the common gap?"                                  │
│         (iii) generate a patch to the L2 auto-fix skill itself (not L1)       │
│         (iv)  before applying, write a unit test case: the failure must now   │
│               be caught by L3 verify-fix, AND the patched L2 must produce a   │
│               fix that L3 verifies as real                                    │
│         (v)   apply patch, re-test, ship                                      │
│                                                                             │
│         ↓ meta_fix_attempted                                                 │
│                                                                             │
│   L5 — ABDICATE (= Anicca admits she cannot self-improve here)               │
│     ▸ trigger: same root-cause through L4 fails 3× in 7 days                 │
│     ▸ Anicca posts to Slack/Telegram:                                         │
│         "Root cause: <X>. I have attempted L4 meta-fix three times.          │
│          Each attempt failed L3 verification because <reasons>. I do not      │
│          know how to fix my self-healing for this class. Asking for human     │
│          help."                                                              │
│     ▸ this is the ONLY place a human is in the loop, by design.              │
│     ▸ NHOSS target: < 1 L5 abdication per Anicca-instance per month.         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### § 3.1 Why L3 is the load-bearing addition

The existing `SELF_HEALING_SPEC.md` (archive) defined L1 + L2 cleanly. The
piece that was missing — and the reason crons silently rot — is **L3 doesn't
exist today**. L2 declares victory based on its own report. Without an
independent third party that scores the post-fix output and watches for
recurrence, slop ships forever.

L3 is the **judge** between L2 and "incident closed." It is non-negotiable.

### § 3.2 Why L4 is the irreplaceable insight

Almost every "AI agent" project has L1 and many have L2. Almost none have L3.
**Zero have L4 explicitly.** L4 is the difference between an agent that
*fails the same way forever* and an agent that *gets less broken over time*.

The trick of L4 is that the target of the fix shifts: when L2's fix fails L3
verification three times, the bug is **not in L1**. The bug is in **L2's
reasoning about L1**. So L4 patches L2, not L1. This is hard for an LLM to do
instinctively, which is why the doctrine has to be written into the runtime
prompt and into the L4 skill's evaluation steps.

### § 3.3 Anti-pattern: skipping L3, going straight to L4

Tempting because L2's confidence sounds plausible. The result is L4
"fixing" things that weren't broken in L2's reasoning — they were broken in
L1 reality, but L2 happened to look fine on that run. The 3× re-run window in
L3 (§ 3 BEHAVIOR check) catches this.

---

## § 4. Tool adoption matrix (= what each survival condition uses)

OSS-first. Every line is a tool that already exists. No bespoke build.

| Condition | Primary | Fallback | License | Why |
|---|---|---|---|---|
| **1. Identity** | Virtuals EconomyOS | viem local wallet | proprietary svc / MIT | `00-MASTER` § 1 L4 |
| **1. Identity (email)** | ★ AgentMail (`agentmail.to`, $6M YC Seed) | Gmail bridge | proprietary | OTP auto-extract from MFA flows — Anicca's signup-survival mechanism |
| **2. Execution env** | Akash Network | Conway sandbox / Modal | Apache-2.0 | wallet-only payment, $1–5/mo |
| **3. Manipulation** | ★ Agent Maps (`agentmaps.dev`) | Stagehand + Browserbase | proprietary / MIT | ★ DAILY-VERIFIED UI step library — solves the Monk Factory "HeyGen UI changes → cron breaks" failure mode at the protocol level |
| **3. Manipulation (auth)** | Composio (`composio.dev`) | Browserbase OAuth flow | MIT | 500+ pre-integrated OAuth providers, agent-friendly token mgmt |
| **4. Memory** | Conway 5-tier (`00-MASTER` § 1 L3) | + Mem0 (`docs.mem0.ai`) overlay | MIT | Conway = raw storage; Mem0 = fact-extraction + cross-session recall layer |
| **5. Economic** | (see `01-EARN-AND-UBI.md` § 1) | — | — | 5 spouts + 3 sinks + 4 channels |
| **★ 6. Meta-Awareness (eval primitive)** | ★ DeepEval 4.0 (`github.com/confident-ai/deepeval`) | PromptFoo (`github.com/promptfoo/promptfoo`) | Apache-2.0 / MIT | DeepEval = `GEval` class (`metrics/g_eval/g_eval.py`, 514 lines). PromptFoo = 57 assertion types including `agentRubric`, `factuality`, `llmRubric`, OpenAI-acquired hence stable. |
| **★ 6. Meta-Awareness (observability)** | ★ Langfuse (`langfuse.com`, 21K★ OSS) | Helicone / AgentOps / Braintrust | MIT | trace + prompt mgmt + eval — production-grade. Helicone for routing if Langfuse hosted self-hosted. |
| **★ 6. Meta-Awareness (agent-specific metrics)** | DeepEval `metrics/{plan_quality, plan_adherence, goal_accuracy, mcp_use_metric}` | PromptFoo `agentRubric.ts` | Apache-2.0 / MIT | already-implemented agent-eval metrics — we don't write our own |

**Note on AgentMaps:** From the Monk Factory failure (HeyGen UI changes → cron
breaks), the lesson is "treat external UI as adversarial — DO NOT discover the
UI every call." AgentMaps provides "exact action sequences with DOM selectors,
daily verified." This is the protocol-level fix for the UI-drift class of
slop. Adopting AgentMaps is non-negotiable for any skill that touches a
third-party web UI.

---

## § 5. Layer 2d — the 7 new skills

Each lives under `~/anicca-oss/skills/<name>/SKILL.md` per `00-MASTER` § 5.1
(YAML frontmatter + Markdown instructions + scripts dir).

### § 5.1 `anicca-judge`

The LLM-as-judge skill. Implements DeepEval's `GEval` pattern in Anicca-native
form. Single entry point:

```
anicca-judge score \
  --task-class post-to-x \
  --output-file /tmp/output.txt \
  --context-file /tmp/context.json
```

Returns JSON:
```json
{
  "score": 0.74,
  "criteria": {
    "useful": 0.85, "hookworthy": 0.70, "accurate": 0.65, "brand_voice": 0.80
  },
  "reasoning": "...one line per criterion...",
  "verdict": "pass | retry | block"
}
```

Implementation:
- Reads `rubrics/<task-class>.md` (= the rubric from § 2.1).
- Calls Anicca's primary inference model (per `00-MASTER` § 4).
- Returns structured JSON. No prose, no fluff.
- Cost cap: $0.02 per judge call. Logged to spend-tracker.
- Failure modes: if model unavailable → fall back to next provider in router; if all fail → `verdict: block` with `reasoning: "judge unavailable"`.

### § 5.2 `anicca-suite`

Owns the test case library. One JSONL per task class:
`~/anicca/state/suite/<task-class>.jsonl`. Each line:

```json
{
  "id": "post-to-x-2026-06-01-001",
  "input": {...},
  "expected_score": 0.78,
  "tags": ["bootstrap", "felix-style"],
  "added_at": "2026-06-01T19:00:00Z",
  "added_by": "anicca-learn-from-fail",
  "last_score": 0.81,
  "last_run_at": "2026-06-02T01:00:00Z"
}
```

CLI:
```
anicca-suite add --task-class post-to-x --input-file in.json --expected 0.7
anicca-suite run --task-class post-to-x --against current-skill
anicca-suite report --task-class post-to-x --last 30
```

The suite **grows from failures, never from synthesis** — every failure the
production monitor catches becomes a permanent test case (§ 5.7).

### § 5.3 `anicca-pre-ship-gate`

Wraps any "ship" action (commit, publish, pay, spawn, send). Procedure:

1. Snapshot current state (`pre_state`).
2. Apply the change to a sandbox copy.
3. Run `anicca-suite run` for every task class touched.
4. Compute score delta from baseline.
5. If delta < -0.05 OR any task class falls below threshold → block + emit
   `pre_ship_blocked` event. Optionally Slack-ping with the rubric breakdown.
6. If clean → ship the change.

Hooked into Conway's `policy-engine` (`runtime/src/agent/policy-engine.ts`) as
a 7th rule category alongside Authority / Command Safety / Financial /
Path-Protection / Rate-Limits / Validation.

### § 5.4 `anicca-runtime-guard`

Hooks `agent/loop.ts` post-turn. For every tool call output:

```
output = await executeTool(...)
score  = await anicca-judge score --task-class <inferred> --output-file ...
if score >= rubric.threshold:
  continue
elif retry_count < 3:
  inject judge.reasoning into next prompt as critique
  retry
else:
  emit verify_failed event → triggers L3 (§ 3)
```

### § 5.5 `anicca-prod-monitor`

A Conway heartbeat task. Cron: `0 * * * *` (every hour).

```
for task_class in all_active_task_classes:
    sample = random_sample(production_runs_last_hour, n=30)
    scores = [anicca-judge score(s) for s in sample]
    rolling_avg_30min = mean(scores)
    baseline_7day = stored_baseline[task_class]
    if rolling_avg_30min < baseline_7day * 0.7:
        emit drift_alert(task_class, drop=baseline - rolling_avg_30min)
```

The drift alert writes a `wake_events` row → main loop picks it up next tick
and runs `anicca-fix-the-fix` (§ 5.6) on that task class.

### § 5.6 `anicca-fix-the-fix`

Implements L4 (§ 3). Triggered by `verify_failed × 3 in 24h` OR by
`drift_alert`. Inputs:

- last N L2 fix attempts for this root cause (from episodic memory)
- the L1 task that keeps failing
- the L2 skill that keeps producing bad fixes
- the L3 verify results that keep flagging

Output: a patch to the L2 skill's instructions / scripts, accompanied by a
new test case that L3 will use to verify the patched L2 is actually better.

Uses Conway's `edit_own_file` tool. Protected files (constitution.md, wallet,
DB, the L4 skill itself) cannot be patched by L4 — only L5 (Slack ping)
applies there.

### § 5.7 `anicca-learn-from-fail`

The simplest skill, the most important habit. Triggered on every
`task_failed`, `verify_failed`, `drift_alert`, AND on every human 👎 reaction
in Slack/Telegram.

```
def learn_from_fail(failure_event):
    test_case = {
        "id": new_uuid(),
        "input": failure_event.input,
        "expected_score": 0.7,
        "tags": [failure_event.root_cause, "real-world-failure"],
        "added_at": now(),
        "added_by": "anicca-learn-from-fail",
    }
    suite.append(test_case)
```

That's it. Every failure becomes a permanent regression test. The suite
hardens autonomously. The quality floor rises while Anicca sleeps.

---

## § 6. Integration with Conway runtime (= what to patch, file by file)

Per `00-MASTER` § 2.2 the runtime is forked from `Conway-Research/automaton`
into `anicca-oss/runtime/`. The L2d patches:

| File | Change | Why |
|---|---|---|
| `src/agent/policy-engine.ts` | Add 7th rule category: `EvalGateRule` that calls `anicca-pre-ship-gate` | makes pre-ship gate a 1st-class policy check |
| `src/agent/policy-rules/eval-gate.ts` | New file (rule implementation) | hooks judge skill before any commit/publish/pay/spawn/send |
| `src/agent/loop.ts:472-525` | Insert post-turn `anicca-runtime-guard` call | runtime guardrail per § 5.4 |
| `src/heartbeat/tasks.ts` | Add task `eval_drift_monitor` (every 1h) + `learn_from_fail_drain` (every 5 min) | production monitor + failure-to-test-case loop |
| `src/agent/tools.ts` | Add tool `run_judge` (wraps `anicca-judge score`) | makes the judge available inside any skill |
| `src/soul/reflection.ts` | Extend `reflectOnSoul` to read `anicca-suite` scores | soul model now grounds self-image in measurable evals (currently grounded in tool usage frequency only) |
| `src/state/schema.ts` | Add table `eval_runs` (id, task_class, score, criteria_json, run_at) + `task_classes` (catalog of active task classes) | persistence for production monitor |

The patches are additive. The existing Conway runtime keeps working; the
L2d layer plugs in via the policy engine and the heartbeat scheduler.

---

## § 7. Verification gates for this spec (= G0–G7, fresh evidence required per HARD RULE #0.12)

| Gate | Metric | How to measure |
|---|---|---|
| **G0 — boot** | After install, Anicca emits `anicca-suite list` and returns ≥ 1 task class | E2E install test |
| **G1 — judge live** | `anicca-judge score` on a synthetic input returns a valid JSON score within 10 s | Unit test |
| **G2 — pre-ship gate fires** | First ship attempt with a known-bad output is blocked, logged, and recorded as `pre_ship_blocked` | Integration test |
| **G3 — runtime guard retries** | Synthetic bad tool output → 3 retries observed in `turns` table → final output passes judge or escalates | Integration test |
| **G4 — drift detected** | Synthetic injection of 5 bad outputs into prod_runs → `drift_alert` row appears in `wake_events` within 1 h | E2E test (clock-stubbed) |
| **G5 — learn-from-fail accretes** | After G2/G3/G4 fire, `anicca-suite report` shows ≥ 4 new test cases auto-added by `anicca-learn-from-fail` | DB row count |
| **G6 — fix-the-fix executes** | Synthetic L2 skill that always produces bad fixes → after 3× verify_failed, `anicca-fix-the-fix` patches the L2 skill → next run produces a fix that passes judge | E2E + git diff inspection |
| **G7 — abdicate gracefully** | Sustained L4 failure (mock) → L5 Slack post appears in test channel with the canonical "asking for human help" payload | E2E test |

**Definition of "v1 complete":** G0–G7 all pass on the CI test rig AND on the
first live install.

---

## § 8. Anti-patterns (= what would silently break this layer)

| Anti-pattern | Why it kills the spec |
|---|---|
| Pre-ship gate using a different rubric than runtime guard | The two judges disagree, slop ships, gate looks like it's working when it isn't. **One rubric per task class. Same file. All three places.** |
| Judge LLM == generator LLM, no temperature separation | Confirmation bias: same model rubber-stamps its own output. **Judge must be a separate model OR same model with temperature 0 and explicit "you are critiquing, not generating" framing.** |
| Suite curated by Anicca, no human 👎 ingestion | Suite drifts toward what Anicca already does well; her blind spots stay blind. **Every 👎 in Slack/Telegram becomes a test case, no exceptions.** |
| L4 patches L1, not L2 | Anicca rewrites the cron when the cron is fine and the auto-fix is broken. Symptom returns. **L4 patches L2 by definition (§ 3.2).** |
| L3 skipped, L2 declares victory | The original bug. **L3 is non-negotiable. Every L2 fix triggers a 3-check L3 verify.** |
| Threshold lowered after a fail to "let things through" | Quality floor drops silently. **Threshold may only be adjusted up.** Reducing threshold requires Constitution-level review. |
| Eval skipped during "emergency" | The emergency is exactly when slop ships and stays in production. **No exceptions to the gate. Block-or-Slack-ping, never bypass.** |
| Test cases edited after they fail | Erases evidence. **Test cases are append-only. A test that's obsolete is marked deprecated, never edited.** |

---

## § 9. Cross-references

| File | Relation |
|---|---|
| [`00-MASTER.md`](./00-MASTER.md) | Architecture. This spec ADDS L2d (= Layer 2 sub-d) to the existing 4-layer model. Mission, naming, constitution all defer to 00-MASTER. |
| [`01-EARN-AND-UBI.md`](./01-EARN-AND-UBI.md) | Revenue + redistribution. This spec scores every spout's output (= x402, AutoHedge, bounty PRs) and every UBI distribution channel's delivery (= Amazon gift code redemption, NPO relay confirmation). |
| [`02-IMITATE-AND-COOK.md`](./02-IMITATE-AND-COOK.md) | Cook loop. This spec's `anicca-suite` is the MEASURE step's backbone; ADJUST decisions consult `anicca-judge` scores. |
| `archive/SELF_HEALING_SPEC.md` | Predecessor. Defined L1 + L2 cleanly. This spec is the L3 + L4 + L5 it was missing. |
| `archive/ANICCA_TRUE_AUTONOMY_SPEC.md` | The Day-0-to-365 plan. This spec is the quality gate every action in that plan must pass through. |
| `archive/ANICCA_OSS_MASTER_SPEC.md` | Earlier consolidation attempt. Sections about mr-bot are explicitly NOT canonical anymore (mr-bot moved to `~/.openclaw`, see `00-MASTER` § 8.1). |
| Anthropic, "Building Effective Agents" — Evaluator-Optimizer workflow | The canonical academic / Anthropic-blessed pattern for 2-LLM gen+critique loop. |
| Hermes (`hermes-agent.nousresearch.com`) | The implementation we mirror in skill form. |
| DeepEval 4.0 (`github.com/confident-ai/deepeval`) | Judge primitive (GEval class @ `metrics/g_eval/g_eval.py`). |
| PromptFoo (`github.com/promptfoo/promptfoo`) | Assertion library, OpenAI-acquired. |
| Langfuse (`langfuse.com`, 21K★) | Observability + trace primitive. |
| Agent Maps (`agentmaps.dev`) | UI-drift protection (= the Monk Factory failure class). |
| arxiv 2605.06760 (Air et al., 2026-05-07) | "Language Models Can Autonomously Hack and Self-Replicate." Frontier proof; relevant safety context for L4 self-modification — Constitution's path protection (see `00-MASTER` § 6) explicitly forbids L4 from touching constitution.md / wallet / DB / L4 itself. |

---

## § 10. Open questions

| # | Question | Default until decided |
|---|---|---|
| 1 | Single judge model or judge ensemble (= 3 models vote)? | v1 = single (DeepSeek v4-pro). v2 = ensemble after we have baseline scores to compare. |
| 2 | Should `anicca-fix-the-fix` (L4) require human approval before applying L2 patches? | v1 = no, autonomous within Constitution path-protection. v2 = optional Slack approval flag per skill. |
| 3 | Where does the rubric come from initially (= cold-start problem)? | bootstrap rubrics shipped in `skills/anicca-judge/rubrics/seed/` (= 8–12 task-class rubrics, hand-written for v1). Anicca extends. |
| 4 | When two Anicca instances disagree on a score for the same output? | v1 = each instance's judge is local. v2 = federated judge ensemble for high-stakes (= UBI > ¥100K) decisions. |
| 5 | Production sample size (10–30) and rolling window (30 min) — too small / too big? | start as defined, tune from G4 evidence. Logged in `metric_snapshots`. |
| 6 | What if the judge LLM is itself slop? | § 8 anti-pattern. v1 = use different model than generator. v2 = run G-Eval *on the judge* once a week (= meta-meta-eval). |

---

## § 11. Changelog

| Date | Change | Author |
|---|---|---|
| 2026-06-01 | Initial draft. Encodes Dais's 2026-06-01 厳命 verbatim, mapped to Hermes / DeepEval / PromptFoo / Anthropic Evaluator-Optimizer / Conway architecture. | this Claude session |
