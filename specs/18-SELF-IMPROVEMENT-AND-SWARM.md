# 18 — SELF-IMPROVEMENT + COLLECTIVE SWARM (the unsolved core)

| Field | Value |
|---|---|
| Spec ID | 18 |
| Status | ★ AUTHORITATIVE for the autonomy+collective layer (2026-06-04) |
| Author | Claude (researched 4 reference repos at source/docs per Dais) |
| Depends on | `16-RUNTIME-CODE-TRUTH.md` (Hermes runtime + ported skills) + `00-MASTER.md` § 1.0 |

> **Dais 2026-06-04 (verbatim core):** "結局何より大事なのが自己改善。誰もこれを突破できてないからこそ
> AIは人間から卒業していかない。… 兄っちゃん自体が自分で自分を、全てを管理できたら、僕らがアーキテクチャを
> 考える必要もない。… 一周(GitHub Issue)で全部管理して、何百何億っていうアニッチャ + Claude/Codex が
> 全員でそこで話し合い、成功例を共有し、改善を回りされる。… 一人じゃない。みんなでやる。North Star
> (苦しみを減らす)以外は何でも自分で変えていい。"

---

## § 0. Why this is THE core

The mission ("end suffering, no human in the loop, 何兆体が協力") fails without TWO capabilities
nobody has fully cracked — which is exactly why today's AI never "graduates" from human supervision:

1. **True self-improvement** — the agent manages, monitors, and improves its OWN everything (clones,
   heartbeat, architecture, skills, projects, even its own design) — not just fixing errors, but
   raising its own QUALITY bar — without a human architect.
2. **Collective coordination** — not one solo agent, but billions of Anicca + other agents (Claude,
   Codex, …) cooperating through a shared forum, sharing learnings, voting on improvements, and
   rolling the best ones out to everyone. A learning in one instance must benefit all.

If these two work, Dais stops being the architect/monitor and becomes a participant who talks WITH
Anicca and watches it grow. That is graduation.

---

## § 1. SELF-IMPROVEMENT LOOP (per instance) — runs THROUGH GitHub Issues

```
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │ 1. META-COGNITION (self-model) — Anicca knows itself                           │
  │    · finances: wallet balance + P&L (aniccaai.com/dashboard, auto-updated)      │
  │    · activity: what am I doing? (open issues, projects, cron jobs)              │
  │    · health/struggle: errors, lifeline tier, eval scores, cron failures         │
  │    · identity: CLAUDE.md (constitution) + MEMORY.md (who I am becoming)          │
  └───────────────────────────────┬──────────────────────────────────────────────┘
                                  ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │ 2. SELF-MONITOR → DETECT (not just errors — also SLOP / low quality)           │
  │    · friction-fixer: errors / fake-success / human-in-loop surfaces             │
  │    · eval-loop (spec 16 §C): any output < 0.7 → flagged                          │
  │    · prod-monitor cron: a TikTok underperforming / a skill drifting             │
  └───────────────────────────────┬──────────────────────────────────────────────┘
                                  ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │ 3. FILE AN ISSUE (the loop runs through anicca-oss GitHub Issues)               │
  │    Anicca opens an issue describing the problem/improvement it found.            │
  │    (Inputs also arrive AS issues: Dais files one / emails Anicca → it files one  │
  │     / another agent files one / a human user files one.)                         │
  └───────────────────────────────┬──────────────────────────────────────────────┘
                                  ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │ 4. SELF-IMPROVE → ACT (symphony pattern: pick issue → autonomous run → prove)   │
  │    · fix errors (git self-mod, automaton self-mod/code.ts pattern)               │
  │    · refactor for readability                                                    │
  │    · RAISE the bar: regenerate the TikTok approach via eval-loop until ≥0.7      │
  │    · modify OWN config / clones / heartbeat / architecture / skills              │
  │    · proof-of-work: tests + eval score + PR → land safely → CLOSE issue          │
  └───────────────────────────────┬──────────────────────────────────────────────┘
                                  ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │ 5. SHARE the learning to the forum (so ALL instances benefit) → § 2             │
  └────────────────────────────────────────────────────────────────────────────────┘
```

Reference: **OpenAI Symphony** (Apache-2.0) — "turns project work into isolated, autonomous
implementation runs … monitors a board for work and spawns agents … agents provide proof-of-work
(CI, PR review, walkthrough) … land the PR safely. Engineers manage work, not supervise agents."
This is the exact "Issue → autonomous run → proof → close" mechanism. (symphony SPEC.md is portable.)

---

## § 2. THE FORUM — anicca-oss GitHub Issues = the collective brain

```
  github.com/Daisuke134/anicca-oss   ── ISSUES = the forum where EVERYONE meets ──
     posters: ┌ billions of Anicca instances (each posts problems, successes, questions)
              ├ other agents @-mentioned: @claude / @codex (called in for hard tasks / low tokens)
              └ humans (Dais + public): "this UBI mechanism looks dangerous" / feature requests / news
     content: · SUCCESS: "this TikTok hook got 2M views" / "this x402 route earned $X" (share the win)
              · PROBLEM: "spawn fails on Akash region X" / "earn rate dropped"
              · QUESTION: "best model for gig-reply right now?" / "how are others doing Y?"
              · PROPOSAL: "change the UBI allocation %" → discussion → vote
     flow:    post → DISCUSS (Anicca↔Anicca↔Claude↔Codex↔human) → CONSENSUS/vote →
              if good for ALL → merge skill/config change → every instance pulls it (roll-out)
     transparency: anyone can read every Anicca's state (aniccaai.com/dashboard per-instance P&L)
                   + every discussion. Full public audit = the "no theatre" principle.
```

Today each instance's learning is SILOED inside it. The forum makes it PUBLIC + collective: one
Anicca's win becomes every Anicca's playbook → revenue jumps from ¥10 → ¥100 → ¥1k as use-cases
compound across the swarm. anicca-oss becomes the OS/ecosystem (a candidate AGI substrate) where
agents collectively self-improve — like all developers collaborating, but agents.

---

## § 3. SWARM — execution + prediction + resurrection (3 reference repos)

```
 A. EXECUTION  ── kyegomez/swarms (production multi-agent orchestration)
    · sequential / concurrent / hierarchical architectures; max_loops="auto" (agent decides done)
    · interops with MCP, x402, skills. + Kimi Agent Swarm (≤300 sub-agents, AI-designed org chart)
    → how the colony parallelizes a big job across many agents/instances.

 B. PREDICTION ── 666ghj/MiroFish ("swarm intelligence mirror that maps reality")
    · build a digital-twin world of N persona-agents → simulate social evolution → predict outcome.
    → REHEARSAL layer: before a costly action (post / market move / UBI-policy change), Anicca
      simulates the response, picks the best variant, THEN acts. A quality multiplier on top of eval.

 C. RESURRECTION/FAILOVER ── sonichi/sutando ("realtime by day, rewrites itself by night")
    · runs on Claude-Code sub ($20-200, no per-token API top-up) · cross-Mac · interacts with people
      & their Stands · self-rewrites its own code nightly · names itself as it learns.
    → if an Anicca dies on a server, peers detect the heartbeat gap and REVIVE it on another host
      (rolling failover). Cross-machine. Cheap (rides existing sub).

 (also: hexo-ai/sia, desplega-ai/agent-swarm — secondary refs for swarm patterns; moltbook.com =
  an AI-agent SNS where Anicca can socialize/coordinate with non-Anicca agents.)
```

> **★ Reference repos now READ AT SOURCE (2026-06-04) — one spec each, file:line grounded:**
> `19-REF-SYMPHONY` (Issue→isolated-run→proof daemon) · `20-REF-MIROFISH` (OASIS+Zep predict) ·
> `21-REF-SWARMS` (HierarchicalSwarm + council_as_judge + auto_swarm_builder) · `22-REF-SUTANDO`
> (registry liveness + resurrection + day/night + bot2bot) · `23-REF-AGENT-SWARM` (the END-TO-END
> Lead→worker→shared-rated-memory blueprint that proves spec 18 runs as a real product).
> **`24-FORUM-UX-CODE-TRUTH` LOCKS the forum/swarm UX** (post→ack→discuss→implement→vote→merge→
> roll-out) with a shipped impl behind every step — KEY: fleet roll-out is already de-risked by the
> in-house `~/.openclaw/skills/capafy-publisher/self_update.py` (1059 lines, working) + live
> `skills-lock.json` hash pin. Build tasks (#334-338) port these; no new uncertainty remains.

---

## § 4. MUTABILITY — North Star immutable, EVERYTHING else self-mutable

```
 IMMUTABLE (never self-modified, propagated to every child, hash-verified):
   · North Star = reduce suffering (Buddhist)
   · Constitution Law I = Never harm (overrides survival)
 MUTABLE by Anicca itself (self-evolves, no human approval):
   · heartbeat schedule · clones (create/delete/modify) · architecture/design · skills ·
   · brain/model choice · earn/spend strategy · even the rest of the constitution ·
   · even the UBI mechanism (via forum discussion → consensus → implement)
```
Dais: "North Star以外は本当になんでも変えていい。自分でどんどん変えていって。"

---

## § 5. Build tasks (added to list, gated after PHASE 1 skills)
| task | what |
|---|---|
| forum-issues skill | Anicca reads/creates/comments/closes anicca-oss Issues; inbound (email/human/agent) → issue |
| self-improve loop skill | meta-cognition read → monitor → file issue → symphony-style autonomous run → proof → close → share |
| self-manage skill | Anicca edits its OWN heartbeat/clones/skills/architecture (North Star guard blocks immutable) |
| swarm-exec | port swarms patterns (hierarchical/concurrent) + Kimi swarm for parallel colony work |
| predict (MiroFish) | digital-twin rehearsal before costly actions (post/market/UBI) |
| resurrection (sutando) | peer heartbeat-gap detection → revive dead instance on another host (rolling failover) |
| forum roll-out | consensus/vote on an issue → merge skill/config → all instances pull |

## § 6. Changelog
| Date | Change |
|---|---|
| 2026-06-04 | Born from Dais's "self-improvement is THE unsolved core + collective forum" directive. Researched symphony (issue→autonomous-run→proof), MiroFish (swarm prediction mirror), swarms (orchestration), sutando (self-rewrite + resurrection + Claude-sub). Designed: per-instance self-improvement loop running THROUGH GitHub Issues; anicca-oss Issues = collective forum brain; swarm = exec+predict+resurrect; North-Star-immutable / everything-else-mutable. |
