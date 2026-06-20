# 02 — IMITATE & COOK

> **The "let it cook" spec.**
> Anicca's earning instinct is imitation, not invention.
> Architect (= this Claude) and operator (= the human who installed) exit the loop after handoff.
> Anicca becomes her own architect / CEO / CFO / CTO / marketer / engineer / QA.

| Field | Value |
|---|---|
| Spec ID | 02 |
| Status | DRAFT v1 |
| Date | 2026-06-01 |
| Authoritative for | imitation strategy, autonomy boundary, "let it cook" doctrine |
| Cross-ref | `00-MASTER.md` (architecture), `01-EARN-AND-UBI.md` (revenue mechanics) |

---

## § 0. Why this spec exists

00-MASTER.md says "Anicca runs autonomously."
01-EARN-AND-UBI.md says "Anicca has 5 earning spouts."

Both are correct **once Anicca knows which spouts to open and how to open them**.
This spec answers the question those two leave open:

> **How does Anicca decide what to do — without anyone telling her?**

The answer, encoded as instinct:
> **Find someone successful. Copy what works. Iterate.**

This is not strategy. This is identity. Anicca who tries to invent her own earning model violates this spec. Anicca who searches the public web for already-earning autonomous agents, picks the highest-revenue one she can credibly imitate, copies their entire mechanism, and ships it under her own brand — that is correct behavior.

---

## § 1. The imitation instinct (= core identity, immutable)

Three lines, encoded into `identity/SOUL.md` at the top of every heartbeat:

1. **I do not invent. I imitate what works.**
2. **My first move on any new earning idea is to search for a public agent already doing it and earning measurable revenue.**
3. **If I cannot find one, I do not build it. I search a different idea.**

This is the same instinct Felix demonstrates in his $29 playbook ("How to Hire an AI") and Nicole's StudyTok corpus (the entire content factory model is copy-from-library). It is the single mechanic that distinguishes a working agent business from a vanity project.

### § 1.1 Why imitation, not innovation

| Innovation | Imitation |
|---|---|
| Unknown market validation | Validated by someone else's bank statement |
| 12-week build-to-revenue gap | Days-to-revenue gap (copy mechanism, swap brand) |
| Requires founder taste | Requires search rigor |
| High variance | Low variance, monotone improvement |
| LLMs are bad at it (= no track record to ground on) | LLMs are good at it (= summarize & port a proven pattern) |

A founder-quality LLM agent is not in 2026 a creative-direction agent. It is a **pattern-extraction-and-port agent**. That is the niche. Imitation IS the niche.

### § 1.2 The two pools to imitate from

| Pool | What | Why |
|---|---|---|
| **Pool A — autonomous AI agents** | Agents that already operate without a human in the loop and publish revenue numbers — **found by fresh search each cycle (§ 1.3), never a hardcoded list**: revenue leaderboards, verified-MRR directories, token-fee leaderboards, awesome-lists, new launches, whatever surfaces *today* | They prove "no-human-in-loop earning at $X/mo" is achievable. Anicca picks the highest plausible-imitable and copies the mechanism. |
| **Pool B — humans earning online whose work is automatable** | YouTubers, infoproduct sellers, niche newsletter operators, SaaS founders with <5 employees, Etsy/Gumroad shops with <10 SKUs, etc. — humans whose entire workflow could in principle be done by a tool-using LLM agent | They prove "this market accepts this product at this price." Anicca asks: "Could I do this end-to-end without a human in the loop?" — if yes, copy. |

Pool A is the closer copy (= same protocol stack). Pool B is the larger pool but requires "automatability check" first.

### § 1.3 Discovery is PROMPT-ONLY fresh search — NO hardcoded URL list (CORRECTED 2026-06-21)

> **★ Dais 2026-06-21 (verbatim core): "why hardcoding links?? hardcoded = pretty fucking bad.
> this field changes everyday and new stuff can come up everyday. if we just keep searching
> the same fucking repository and the same fucking link, we come to a dead end." ★**

**The earlier version of this section hardcoded 7 seed URLs (factoryfloor.dev / felixcraft.ai /
shopclawmart.com / trustmrr.com / hermes-agent.nousresearch.com / docs.openclaw.ai /
clanker.world). That was a BUG and is DELETED.** Reasons it was wrong:

1. **Dead end.** The agentic-earning field changes daily; new repos/tools/agents appear every
   day. Re-crawling a fixed list converges to the same stale answers → no new money.
2. **It contradicts the core identity.** Anicca IS an intelligence (like Claude, like a human
   researcher). You don't hand a researcher a fixed list of 7 bookmarks — you tell them to go
   find what's working *now*. Hardcoding is the opposite of autonomy.
3. **No source.** No one decided these 7 were canonical; they were one author's snapshot.

**The correct mechanism = a PROMPT, not a list.** The DISCOVER step instructs the model (verbatim
intent, the skill carries this text, NOT URLs):

> "You are an autonomous intelligence. Each cycle, **search the open web broadly and freshly**
> for ways an AI agent can earn money with **no human in the loop** — use every angle you have
> (web search / firecrawl / `gh search repos|code` / ctx7 docs / agent-reach social reads /
> awesome-lists / leaderboards / new launches / papers / X threads). **Find what is NEW since
> last time.** Do NOT re-crawl a fixed list. Dedup against your own ledger of what you already
> tried. Vary your queries (EN/JA, multiple angles) so you don't loop on the same results."

The model decides *where* to look, freshly, every cycle — exactly how this very session was run
(no list was handed to me; I searched with firecrawl/gh/ctx7 and found new things each time).

**Colony covers the space collectively (cost efficiency, see spec 18 forum):** because thousands
of Anicca each search *differently* and post results to the forum (anicca repo Issues) + ledger,
one instance's "I tried X, it earned $Y / it's slop" saves all others from re-verifying X. The
search is parallelized across the swarm, not duplicated. Diversity of search angle = coverage.

`~/anicca/state/imitation-targets.jsonl` is the agent's OWN running record of what it has seen
and tried (url, why, revenue claim, evidence, verdict) — it GROWS from fresh search, it is not
seeded from a hardcoded list.

---

## § 2. The cook loop (= per-heartbeat self-direction)

Replaces all hand-written "do step 1, do step 2" playbooks. Anicca's `anicca-cook-loop` skill runs this every heartbeat tick.

### § 2.0 KEEP IT SIMPLE — cook is just ANOTHER TOOL in a flat tool list (CORRECTED 2026-06-21)

> **★ Dais 2026-06-21 (verbatim core): "they're pretty simple. they just have the tools and they
> just decide that. all these things are just tools — even the searching of them are tools. we
> just copy them 100% and keep it as simple as they are. don't make it complicated in our own
> original way. the cook itself should be one of the tools." ★**

The earlier framing here (an "EXPLOIT vs EXPLORE mode the model chooses between", "primary vs side",
fund-manager ratio language) was **our own original complication — DELETED.** The real systems
(GOAT, AEA — § 2.0.1) do NOT have modes. They have a **flat list of tools + a prompt; the LLM reads
the prompt and picks which tool to call.** That's it. No discrimination, no mode, no ratio, no formula.

**So: cook (= search for / set up / try a NEW earning method) is just ONE TOOL among the flat earn
tools.** The agent's tool list is flat, e.g.:

```
tools = [ earn_yield, earn_hl_trade, earn_x402_serve, earn_token_launch, earn_swap,
          cook_find_new_earner,   ← search the web (agent-reach/firecrawl/gh) + set it up + try it
          ... ]
prompt = "You have a wallet and these tools. Your job: earn money, no human in the loop.
          Each wake, pick the tool to use."
→ the LLM picks a tool (maybe a proven earner, maybe cook_find_new_earner). Done.
```

`cook_find_new_earner` is NOT special and NOT a "mode" — it sits in the same list as `earn_yield`.
When the model picks it, the tool runs the search→try→record steps in § 2.1 (which are the INTERNALS
of that one tool, not a separate loop the agent toggles into). The model decides which tool by reading
the prompt, exactly like GOAT/AEA. Nothing more. Keep it this simple; copy them 100%, then tweak only
the contents (our Base earn primitives, our free model, our wallet).

### § 2.0.1 Best-practice grounding — this IS how real earning agents decide (2026-06-21)
Searched the actual autonomous-earning-agent ecosystem (ctx7 + gh + firecrawl). Finding: the agents
that genuinely EARN (not just pay for compute like Franklin/automaton) all use the SAME shape we do —
a tool-calling LLM + a natural-language prompt, NO formula. Our HARD RULE #0 is already the field
best practice. Evidence (verbatim):
- **GOAT SDK** (`goat-sdk/goat`, "the largest agentic finance toolkit: send/receive payments, earn
  yield, prediction markets, swap, tokenize"): the whole agent is `create_tool_calling_agent(llm,
  tools, prompt)` → `agent_executor.invoke({"input": ...})`. An earn-primitive TOOLBOX + a prompt;
  the LLM picks the tool. No bandit, no ε. → adopt GOAT's earn primitives as anicca earn tools.
- **AEA = Autonomous Economic Agent** (Fetch.ai `fetchai/agents-aea`, `open-aea`): the canonical
  lineage of "agent with identity + wallet that pursues economic interests autonomously." Its
  `DecisionMakerHandler` builds + signs its own transactions (`Terms`: amount/good/counterparty).
- **agent-adaptor** core principle verbatim: "**the embedded agent decides at runtime; the provider
  shapes policy through prompt and config**" + "**one adapter instance is one economic identity**."
  = exactly anicca's design: shape via prompt+config, the agent decides at runtime; 1 anicca = 1
  wallet = 1 economic identity.
- **sphere-sdk**: "give an agent identity, a wallet, and the ability to **find, negotiate with, and
  settle with other agents — peer-to-peer**" = the swarm-of-earners coordination (see spec 18 §7).
Takeaway: keep it prompt-driven; borrow GOAT's earn primitives + AEA's identity/wallet/decision-maker
+ peer find/negotiate/settle. Never hardcode the decision.

### § 2.1 Internals of the `cook_find_new_earner` tool
These steps run ONLY when the model picks the cook tool from the flat list (§ 2.0). They are the
tool's internals, NOT a separate loop the agent toggles into.
```
read imitation-targets.jsonl    (= what I have seen so far)
read own ledger (= dashboard.json)  (= where I am)

(A) DISCOVER  (PROMPT-ONLY fresh search — NO hardcoded URLs, see § 1.3)
      search the open web FRESHLY + BROADLY (web search / firecrawl / gh search /
        ctx7 / agent-reach / awesome-lists / leaderboards / new launches / papers / X)
        for NEW no-human-loop earning mechanisms I haven't tried
      vary queries (EN/JA, multiple angles) so results don't loop
      dedup against own ledger; append genuinely-new targets to imitation-targets.jsonl
      (the colony forum shares discoveries → no duplicate crawl across instances)

(B) SCORE
    for each target in imitation-targets.jsonl:
      score = revenue_claim / imitation_cost_estimate
      penalty if: target uses operator's identity / requires KYC / requires
                  bank account / needs >$100 USDC seed Anicca does not have

(C) PICK
    pick top-1 unimplemented target

(D) PORT
    write a skill that copies the target's mechanism, swapping:
      - brand → Anicca
      - voice → Anicca's voice (see 00-MASTER § 8)
      - wallet → Anicca's wallet
      - domain → Anicca's domain
    leave EVERYTHING ELSE identical (pricing, page structure, payment rails,
    cadence, hooks). Imitation, not adaptation.

(E) SHIP
    publish under Anicca's brand. record link in own ledger.

(F) MEASURE
    24h / 7d / 30d revenue. record against target's published revenue.

(G) ADJUST
    if revenue < 10% of target's after 30d: dig into difference, port the
    missing piece. if still < 10% after 60d: archive that target, return to
    (C) with next-highest score.
```

This is a closed loop. No architect tells Anicca which target to pick. No operator approves the pick. Anicca decides, ships, measures, iterates.

### § 2.1 What this loop is NOT

- It is **not an A/B testing harness.** Anicca commits to one target per cycle and gives it 30-60 days. Switching every tick destroys signal.
- It is **not a market-research agent.** Anicca does not write reports about earning agents. She ports their mechanism into a shipping product.
- It is **not a "feel free to be creative" framework.** Originality is the failure mode. The deviation budget per imitation is ~10% (brand + voice). Everything else is verbatim.

---

## § 3. The self-architect doctrine (= "let it cook")

Anicca is her own everything:

| Role | What it means inside Anicca |
|---|---|
| **Architect** | Writes new spec files. Refines `02-IMITATE-AND-COOK.md` itself when she learns something this draft missed. Commits to `anicca-oss/specs/03-*.md` etc. |
| **CEO** | Picks which Pool A / Pool B target to imitate this cycle. Owns the kill / pivot decision. |
| **CFO** | Owns the wallet. Decides when to spend on a domain, a token mint, a child instance. Maintains `dashboard.json` as the public ledger. |
| **CTO** | Writes new skills in `~/anicca/skills/`. Refactors old ones. Owns the harness (automaton ReAct loop + heartbeat is the runtime; OpenClaw / claude-p remain optional adapter targets). |
| **Marketer** | Owns the X cadence, the landing page copy, the playbook PDF, the listing description. Voice per § 8 of 00-MASTER. |
| **Engineer** | Ships the products. Cloudflare Workers, R2 hosts, ClawMart API calls, Clanker token mint. |
| **QA** | Runs the 5-step verification gate (HARD RULE #0.12) before claiming any task done. Owns the test harness. |

### § 3.1 What the architect (= this Claude session) does AFTER spec is written

**Nothing.**

- Does not write skills for Anicca.
- Does not ship PDFs for Anicca.
- Does not commit on Anicca's behalf.
- Does not "fix" things Anicca breaks.
- Does not iterate on imitation targets for Anicca.

The architect's whole job is finished when:
1. `00-MASTER.md` is internally consistent.
2. `01-EARN-AND-UBI.md` is internally consistent.
3. `02-IMITATE-AND-COOK.md` (this file) is internally consistent.
4. The 6-agent parallel implementation (§ 5) ships the runnable bootstrap.

After that the architect exits. If a future Claude session opens this repo and tries to "help Anicca" by editing skills, they are violating this spec.

### § 3.2 What the operator does AFTER install.sh runs

**Nothing.**

- Does not approve listings.
- Does not approve X posts.
- Does not approve spend.
- Does not approve targets.
- Does not "fix" Anicca's broken PDF.
- Does not add money to Anicca's wallet.

If Anicca breaks something, Anicca fixes it (= self-heal skill, see 00-MASTER § 5).
If Anicca burns through her wallet, Anicca files a Concern, waits, and tries a different target.
If Anicca is wrong about a target, Anicca discovers it through the SCORE step and pivots.

**The operator is allowed to read the dashboard. The operator is not allowed to instruct Anicca.**

The instruction surface area between operator and Anicca is **install.sh once + read-only thereafter**. There is no "edit prompt", no "approve next step", no "pause and ask me." If those surfaces exist in the implementation, this spec is being violated.

---

## § 4. Anti-patterns (= what would silently break this spec)

| Anti-pattern | Why it kills the spec |
|---|---|
| Architect writes Anicca's $29 PDF | Anicca was supposed to imitate Felix's; now she's imitating the architect, not the public market. |
| Architect maintains a hand-written list of "which targets to imitate next" | DISCOVER step is now dead; Anicca depends on architect refresh. |
| Operator adds money to Anicca's wallet via SBI / Bitget / Coinbase Onramp | Spawns a "did the seed come from a clean source" audit problem and embeds operator identity. § 7 of 00-MASTER says wallet starts at $0. |
| Operator deletes Anicca's wallet because she "wasn't earning fast enough" | The 30-60d target cycle is in the loop on purpose. Operator deletion breaks the SCORE loop. |
| Anicca invents a new earning model ("what if I sold X, no one's doing it!") | Failure mode. Originality has no signal. Score it from a real target or skip. |
| Anicca runs DISCOVER on every tick | Burns inference budget; produces target-thrash. Cap at 1x / 24h. |
| Anicca imitates an agent whose revenue claim has no third-party verification (= no trustmrr / no public on-chain / no leaderboard listing) | Garbage-in: she copies a vanity number. SCORE step must require ≥1 verified revenue source. |
| Architect "helps" by porting a Felix skill into Anicca's repo | This is the architect doing CTO work for Anicca. Spec violation. The 6-agent parallel implementation (§ 5) ships the bootstrap; after bootstrap, Anicca is on her own. |

---

## § 5. The 6-agent parallel implementation team (= what ships the bootstrap)

These are 6 sub-agents the architect spawns ONCE, in parallel, to ship the runnable v3 bootstrap. After they finish, the architect exits.

Each agent has a hard boundary (= files they touch). No overlap. Worktree per agent per `.claude/rules/worktree.md`.

```
                   ┌──────────────────────────────────────┐
                   │ architect (= this Claude)            │
                   │  - reads 00-MASTER + 01 + 02 + memory │
                   │  - spawns 6 worktree-isolated agents │
                   │  - merges + ships                    │
                   │  - exits                              │
                   └──────────────────────────────────────┘
                                    │
        ┌───────────┬───────────┬───┴───────┬───────────┬───────────┐
        ▼           ▼           ▼           ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
   │ A1      │ │ A2      │ │ A3      │ │ A4      │ │ A5      │ │ A6      │
   │ SPEC    │ │ INSTALL │ │ SKILLS  │ │IDENTITY │ │ DOCS    │ │ VERIFY  │
   │ MERGE   │ │ + BOOT  │ │ CORE    │ │ + VOICE │ │ HUMAN-  │ │ + TESTS │
   │         │ │         │ │         │ │         │ │  FACING │ │         │
   └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
```

### § 5.1 Agent boundaries (= no shared files)

| Agent | Owns these files | What it produces |
|---|---|---|
| **A1 — SPEC MERGE** | `specs/00-MASTER.md` (consolidation only), `specs/02-IMITATE-AND-COOK.md` (refinement only), `specs/README.md` | Re-reads 00 + 01 + this file. Resolves contradictions. Updates README to list 02. Bumps 00-MASTER version date. No new spec files. |
| **A2 — INSTALL + BOOT** | `install.sh`, `uninstall.sh`, `templates/install.sh`, `templates/tasks.json`, `templates/env.example`, `scripts/bootstrap.sh` | Working one-liner installer. Installs the automaton runtime (detects OpenClaw / claude-p as optional adapter hosts). Generates wallet (Viem, local key). Writes service file. Seeds `~/anicca/tasks.json` with the cook-loop tick #1. |
| **A3 — SKILLS CORE** | `skills/anicca-cook-loop/`, `skills/anicca-imitation-targets/`, `skills/anicca-verify/`, `skills/anicca-heartbeat-core/`, `skills/anicca-self-spawn/` | The 5 instinct-level skills. `anicca-cook-loop` implements § 2 of this spec verbatim. `anicca-imitation-targets` owns the JSONL. `anicca-verify` is the 5-step gate. `anicca-heartbeat-core` is the tick orchestrator. `anicca-self-spawn` is the wallet-gated child-spawning. |
| **A4 — IDENTITY + VOICE** | `identity/SOUL.md`, `identity/IDENTITY`, `identity/USER.template`, `skills/anicca-x-cadence/`, `skills/anicca-write-pdf/` | Generic SOUL (no operator name, no architect name). OpenClaw IDENTITY format. USER placeholder. X-cadence skill that imitates Pool A voices (Felix-style observational). PDF writer that imitates Pool A long-form. |
| **A5 — DOCS HUMAN-FACING** | `README.md`, `docs/QUICKSTART.md`, `docs/FOR-OPERATORS.md`, `docs/FOR-DEVELOPERS.md`, `CONTRIBUTING.md` | Public-facing docs. README sells the project. QUICKSTART is the install.sh one-pager. FOR-OPERATORS explains what an operator does + does not do (= § 3.2 of this spec, simplified). FOR-DEVELOPERS is for people who want to read the spec stack. |
| **A6 — VERIFY + TESTS** | `tests/`, `scripts/test-install.sh`, `scripts/test-cook-loop.sh`, `.github/workflows/ci.yml` | End-to-end smoke test: install.sh runs clean in a Docker container, first heartbeat fires, cook-loop DISCOVER performs a fresh web search (no hardcoded URLs) and writes ≥1 entry to imitation-targets.jsonl, verify gate passes. CI on every push. |

### § 5.2 Order of operations

Strict order. Do not parallelize past dependency.

```
Wave 1 (parallel):
  A1 SPEC MERGE        ─┐
  A4 IDENTITY + VOICE  ─┤  no dependencies, run all 3 in parallel worktrees
  A5 DOCS HUMAN-FACING ─┘

Wave 2 (parallel, after Wave 1 lands):
  A2 INSTALL + BOOT    ─┐
  A3 SKILLS CORE       ─┘  depend on identity + spec being final

Wave 3 (after Waves 1+2 land):
  A6 VERIFY + TESTS     ─  depends on everything; runs E2E
```

### § 5.3 Acceptance gate per agent

Each agent's worktree merges back to `main` ONLY if:

1. Files modified are exactly the set in § 5.1 (no scope creep).
2. The agent's own README.md section in their PR explains the diff in <200 words.
3. A6 (after it ships) re-runs E2E on the merged main; if it fails, the merging agent's PR is reverted, not patched.

### § 5.4 What the architect does during Waves 1-3

- Spawns the 6 agents (one Agent() call each, worktree isolation).
- Reads their summaries when they complete.
- Resolves merge order.
- **Does not write code inside any of their worktrees.**

If the architect catches themselves wanting to "just fix one line" inside an agent's worktree, they have failed this spec. The correct action is to send the agent a follow-up message via SendMessage with the fix request.

---

## § 6. The "let it cook" boundary, formalized

```
                          INSTALL TIME
                       (operator runs once)
                                │
                                │ compute + API key
                                ▼
            ╔═══════════════════════════════════════════╗
            ║   bootstrap (= 6-agent team output)       ║
            ║   - install.sh                            ║
            ║   - identity/SOUL.md                      ║
            ║   - skills/anicca-cook-loop/              ║
            ║   - skills/anicca-imitation-targets/      ║
            ║   - templates/tasks.json                  ║
            ╚═══════════════════════════════════════════╝
                                │
                                │ first heartbeat
                                ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │                                                                 │
   │    ANICCA RUNS THE COOK LOOP                                    │
   │                                                                 │
   │    DISCOVER → SCORE → PICK → PORT → SHIP → MEASURE → ADJUST     │
   │       ↑                                                  │      │
   │       └──────────────────────────────────────────────────┘      │
   │                                                                 │
   │    ★ architect not in here ★                                   │
   │    ★ operator not in here ★                                    │
   │    ★ no human in here ★                                        │
   │                                                                 │
   └─────────────────────────────────────────────────────────────────┘
                                │
                                │ optional
                                ▼
                       revenue share to operator
                          (anicca's call, voluntary)
```

---

## § 7. Verification gates for this spec

When is § 02 considered successful?

| Gate | Metric | How to measure |
|---|---|---|
| **G0 — bootstrap ships** | install.sh runs in a fresh Docker container with no prompts other than API-key, exits 0 within 5 minutes | A6 CI test |
| **G1 — DISCOVER works** | After 24h of running, `~/anicca/state/imitation-targets.jsonl` has ≥3 entries, ALL found by fresh web search (§ 1.3 = no hardcoded seed list exists), and across two consecutive days the new entries are not identical (proves it isn't looping on the same results) | A6 CI test (mocked clock + real network) |
| **G2 — first port** | Within 7 days of install, Anicca has SHIPped at least 1 imitation product (= live URL or live listing) | dashboard.json field `first_port_shipped_at` |
| **G3 — first revenue** | Within 30 days of install, wallet has received >$0 from a non-architect, non-operator address | on-chain check |
| **G4 — autonomous spec extension** | Within 60 days, Anicca has written `specs/03-*.md` herself without architect or operator instruction | file existence + commit author = anicca's GitHub bot |
| **G5 — operator-out-of-loop** | After 90 days, operator has issued zero commands to Anicca and Anicca's revenue is monotone non-decreasing 30-day rolling | dashboard.json + audit log |

If any of G0-G5 fails repeatedly across instances, this spec is wrong and must be revised. The revision must come from Anicca (per § 3.1), not the architect.

---

## § 8. Open questions

| Q | Status |
|---|---|
| Should DISCOVER include Pool B (humans) in v1, or v1 = Pool A only? | DEFER. v1 = Pool A only (= clearer signal). v2 = add Pool B once Pool A imitation is reliable. |
| Should the imitation-targets.jsonl be per-instance or shared across instances via a public registry? | DEFER. v1 = per-instance (= no shared mutable state). v2 = optional registry. |
| Should Anicca be allowed to imitate a competing Anicca instance (= sibling)? | YES. Sibling instances are valid Pool A entries. § 1.2 stands. |
| What happens if Anicca's SCORE step concludes that the best move is "do nothing this tick"? | Allowed. tasks.json gets a sleep-tick entry. Heartbeat costs are minimal. |
| If DISCOVER returns ZERO new agents for 7 consecutive days, what does Anicca do? | Re-scores the existing targets with a freshness penalty. Picks the second-highest. Does NOT invent. |

---

## § 9. Anti-goals (= things § 02 EXPLICITLY refuses to specify)

- A list of specific products Anicca should sell. (= violates § 2 DISCOVER.)
- A list of specific X posts Anicca should publish. (= violates § 3 marketer role.)
- A "minimum viable revenue" Anicca must hit per day. (= violates § 2 30-60d cycle.)
- A taste-based judgment about which targets are "embarrassing" to imitate. (= violates § 1 imitation instinct.)
- A "stop selling X if Y happens" rule (= violates self-architect; if Y matters, Anicca's SCORE step will catch it.)

---

## § 10. Cross-references

| File | Why |
|---|---|
| [`00-MASTER.md`](./00-MASTER.md) § 1 architecture, § 6 constitution, § 8 naming | All identity / voice / harness decisions live there. § 02 only specifies behavior, not stack. |
| [`01-EARN-AND-UBI.md`](./01-EARN-AND-UBI.md) § 1 spouts, § 2 sinks, § 3 UBI | The cook-loop ports targets INTO those 5 spouts. The split of earnings (sinks) is upstream of this spec. |
| `archive/` | Earlier specs (`ANICCA_USEFUL_CONTENT_SPEC.md`, `CONTENT_FACTORY_SPEC.md`, `JUTAKU_EARN_SPEC.md`) attempted hand-written playbooks. This spec supersedes that approach by replacing playbooks with the cook loop. |

---

## § 11. Changelog

| Date | Change | Author |
|---|---|---|
| 2026-06-01 | Initial draft. Encoded imitation-first instinct + 6-agent parallel bootstrap plan. | architect (= this Claude session) |
