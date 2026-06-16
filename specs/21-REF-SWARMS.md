# 21 — REF: kyegomez/swarms (the multi-agent orchestration library)

| Field | Value |
|---|---|
| Repo | github.com/kyegomez/swarms · Python · 186MB(gh-api read, no clone) · pushed 2026-06-03 |
| Read at | SOURCE: swarms/structs/ tree + hiearchical_swarm.py + council_as_judge.py + auto_swarm_builder.py |
| Role for Anicca | spec 18 §3-A EXECUTION: the colony's orchestration patterns (how N agents coordinate a job) + §2 forum consensus (council/debate/vote) |

> Read the ACTUAL `swarms/structs/*.py` (not README). Documented from code.

## § 1. What swarms ACTUALLY is
"Enterprise-grade production-ready multi-agent orchestration framework." An **Agent** = LLM + Tools +
Memory; `max_loops="auto"` lets it self-decide when done. Interops with MCP, x402, skills. The value
is a CATALOG of prebuilt orchestration "structs" (architectures) — pick the topology per task.

## § 2. The orchestration catalog (real files in swarms/structs/)
```
 TOPOLOGY                         file                                what it does
 ─────────────────────────────────────────────────────────────────────────────────────────
 Hierarchical ★                   hiearchical_swarm.py                director plans→orders→workers
                                                                      execute→report back to director
 Hybrid hierarchical+peer         hybrid_hiearchical_peer_swarm.py    director + peer-to-peer mix
 Concurrent (parallel)            concurrent_workflow.py              run agents in parallel
 Sequential / rearrange           agent_rearrange.py                  flow-based ordering of agents
 Graph (DAG)                      graph_workflow.py                   dependency DAG of agents
 Group chat / debate ★            groupchat.py · multi_agent_debates.py · deep_discussion.py · debate_with_judge.py
 Council-as-judge ★               council_as_judge.py                 multi-dimension judge panel + aggregate
 Majority voting ★                majority_voting.py                  N agents vote → majority decision
 Mixture-of-Agents (MoA)          mixture_of_agents.py                layered agent ensemble
 Auto-builder ★                   auto_swarm_builder.py               BOSS agent DESIGNS the team (AI org chart)
 Cron swarm                       cron_job.py                         scheduled swarm runs
 Heavy swarm                      heavy_swarm.py                      large parallel fan-out
 Model router                     model_router.py                     route task → best model
 AOP                              aop.py                              agent-orchestration-protocol (interop)
```

## § 3. The 3 core mechanisms (file:line grounded)
```
 HierarchicalSwarm [hiearchical_swarm.py:4]  "a director agent coordinates multiple worker agents …
   director plans → orders → agents execute tasks and report back to the director" (director default gpt-5.4)
   → the COLONY orchestrator: a lead Anicca plans + assigns to worker Anicca/sub-agents.

 council_as_judge [council_as_judge.py:36-65]  evaluation dimensions = accuracy / helpfulness /
   HARMLESSNESS / coherence; each dimension judged + aggregated (DimensionEvaluationError/AggregationError)
   → the multi-judge EVAL panel (stronger than single-judge) AND the forum CONSENSUS mechanism
     (harmlessness dim ties directly to the constitution Law I).

 auto_swarm_builder [auto_swarm_builder.py:23]  a BOSS agent: "analyze the task → define specialized
   agents w/ distinct roles/personalities → orchestrate" → AI-DESIGNED org chart (same idea as Kimi Swarm).
   → Anicca spawns the right team per job without pre-wiring roles.
```

## § 4. HOW ANICCA USES IT (adoption, not interpretation)
```
 need in Anicca                         →  swarms struct to use
 ──────────────────────────────────────────────────────────────────────────────
 colony does a big job (e.g. an earn    →  HierarchicalSwarm (lead Anicca = director) OR
   campaign across many gigs)              auto_swarm_builder (let the lead design the team)
 parallel independent subtasks          →  concurrent_workflow / heavy_swarm  (or Kimi Agent Swarm ≤300)
 dependent pipeline                      →  graph_workflow (DAG)
 forum: decide if an idea is good        →  majority_voting + council_as_judge (vote + multi-dim judge,
   for ALL Anicca (spec 18 §2 roll-out)     harmlessness dim = constitution gate)
 forum: discussion among agents          →  groupchat / multi_agent_debates / deep_discussion
 eval-loop judge panel (spec 16 §C)      →  council_as_judge (4-dim) instead of single judge
 scheduled swarm                         →  cron_job (or the automaton heartbeat)
 ADOPTION: `pip install swarms`; Anicca's swarm-exec skill (spec 18 #337) wraps the needed structs.
   The automaton runtime runs the agents; swarms provides the TOPOLOGY layer on top. Interops with
   x402/MCP/skills so it composes with the wallet/x402 skills.
```

## § 5. ASCII — swarms topologies in the colony
```
 LEAD ANICCA (director)  ──auto_swarm_builder designs team──►  ┌ worker: earn-on-Lancers
   plan → orders → collect reports                              ├ worker: x402-server
   (HierarchicalSwarm)                                          └ worker: research (concurrent_workflow)
                                                                       │ each = automaton agent, max_loops=auto
 FORUM DECISION (spec 18 §2):  proposal ──► majority_voting (N Anicca vote)
                                          + council_as_judge (accuracy/helpfulness/HARMLESSNESS/coherence)
                                          → consensus → roll-out to all
 EVAL-LOOP (spec 16 §C):  output ──► council_as_judge 4-dim panel ──► 0.7 gate
```

## § 6. Changelog
| 2026-06-04 | Read swarms/structs source (HierarchicalSwarm director→workers; council_as_judge multi-dim panel incl. harmlessness; auto_swarm_builder BOSS designs org chart; full topology catalog). Adoption: swarm-exec skill wraps structs; council_as_judge powers BOTH eval-loop panel + forum consensus/voting; HierarchicalSwarm/auto_swarm_builder = colony orchestration. |
