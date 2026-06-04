# 20 — REF: 666ghj/MiroFish (the prediction / rehearsal engine)

| Field | Value |
|---|---|
| Repo | github.com/666ghj/MiroFish · Python(backend) + Vue(frontend) · 16MB · pushed 2026-05-24 · 265 commits |
| Read at | SOURCE: backend/app/services/{simulation_runner,oasis_profile_generator}.py + scripts/run_parallel_simulation.py + file tree |
| Role for Anicca | spec 18 §3-B PREDICT: rehearse a costly action (post / market move / UBI change) in a digital-twin society BEFORE acting |

> Read the ACTUAL backend source (not just README). Documented from code; adoption stated separately.

## § 1. What MiroFish ACTUALLY is (from source)
"简洁通用的群体智能引擎，预测万物" — a **swarm-intelligence prediction engine**. Builds a high-fidelity
parallel digital world of N persona-agents from seed material, runs a social simulation, predicts the
trajectory. Stack read from code:
```
 backend/app/services/
   graph_builder.py            GraphRAG: seed → entity/relationship graph + memory injection
   ontology_generator.py       entity-relationship ontology from seed
   oasis_profile_generator.py  ★ persona generation → OasisAgentProfile
   simulation_config_generator.py  builds the run config
   simulation_runner.py        ★ "OASIS模拟运行器" — drives the OASIS sim (asyncio+subprocess+IPC)
   simulation_manager.py / simulation_ipc.py   process mgmt + IPC channel (CommandType/IPCResponse)
   zep_graph_memory_updater.py / zep_entity_reader.py / zep_tools.py   ★ Zep graph memory (temporal)
   report_agent.py             ★ ReportAgent: analyze post-sim world + deep interaction
   text_processor.py / utils/llm_client.py
 scripts/ run_parallel_simulation.py · run_twitter_simulation.py · run_reddit_simulation.py
```
**Built on: OASIS** (CAMEL-AI's large-scale social-media agent simulation — thousands of agents on a
simulated Twitter/Reddit) + **Zep** (temporal graph memory) + **GraphRAG**.

## § 2. The real mechanism (file:line grounded)
```
 OasisAgentProfile  [oasis_profile_generator.py:30]  fields: persona, age, gender, mbti, country,
   profession, interested_topics  →  .to_reddit_format() [:61]  /  .to_twitter_format() [:89]
 AgentAction        [simulation_runner.py:49]  fields: platform(twitter|reddit), agent_id, agent_name, ...
 SimulationRunner   [simulation_runner.py]  asyncio + threading + subprocess; talks to the OASIS
   sim over IPC (SimulationIPCClient / CommandType / IPCResponse [simulation_ipc.py]); ZepGraphMemoryManager
   updates temporal memory each step.
 Parallel run       [scripts/run_parallel_simulation.py]  runs twitter + reddit sims concurrently
   (--twitter-only / --reddit-only); LLM via .env LLM_API_KEY.
```
WORKFLOW (5 steps, README confirmed by code): (1) Graph building (seed extract + GraphRAG) →
(2) Environment setup (entity extraction + persona gen + agent config inject) → (3) Simulation
(dual-platform parallel + dynamic temporal memory) → (4) Report (ReportAgent w/ toolset) →
(5) Deep interaction (chat with any sim agent / ReportAgent).

## § 3. HOW ANICCA USES IT (adoption, not interpretation)
```
 MiroFish concept       →  Anicca instantiation
 ──────────────────────────────────────────────────────────────────────────────
 seed material          →  the action Anicca is about to take (a TikTok hook, an X post, a gig
                           proposal, a UBI-allocation change, a price)
 persona-agent society  →  a digital twin of the target audience (the niche's viewers / the gig client /
                           the recipient population) — OASIS personas with MBTI/demographics/interests
 simulation             →  run the society's reaction to each candidate variant (parallel twitter/reddit
                           = the actual platforms Anicca posts to)
 prediction report      →  predicted engagement / acceptance / risk per variant
 USE: a "rehearsal" layer stacked ON TOP of the eval-loop (spec 16 §C). eval-loop scores an output
      against a rubric; MiroFish SIMULATES the world's reaction. Anicca runs the variant that wins the
      simulation, THEN ships. = predict before acting → quality multiplier on earn + redistribute + UBI-policy.
 ALSO: the same engine can model "will this UBI mechanism cause harm?" before changing it (spec 18 §4
      UBI is mutable via forum + simulation evidence).
```
Reuse path: OASIS + Zep are pip-installable; MiroFish is the integration blueprint. Anicca's `predict`
skill (spec 18 task #337) wraps OASIS persona-sim + Zep memory, fed by the action-to-test.

## § 4. ASCII — predict layer in Anicca's loop
```
  Anicca about to act (post / gig reply / UBI change)
        │  generate K candidate variants
        ▼
  EVAL-LOOP  → score each variant vs rubric (0-1)  [spec 16 §C]
        │  top variants
        ▼
  MiroFish PREDICT  → build digital-twin society (OASIS personas of the audience, Zep memory)
        │           → simulate reaction on twitter+reddit in parallel → ReportAgent predicts engagement/risk
        ▼
  pick the variant that WINS the simulation  →  SHIP  →  observe real result  →  feed back to eval suite
```

## § 5. Changelog
| 2026-06-04 | Read backend source (simulation_runner = OASIS runner via IPC; oasis_profile_generator = persona w/ MBTI/demographics; parallel twitter+reddit; Zep temporal graph memory; GraphRAG graph_builder; ReportAgent). Built on OASIS+Zep+GraphRAG. Adoption: `predict` skill = digital-twin rehearsal stacked on eval-loop, before any costly action. |
