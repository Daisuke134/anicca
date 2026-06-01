# 05 — Server-Native Deployment + Model Fitness

> **★ Anicca is server-native from Day 0. ★**
>
> The genesis instance may begin on a Mac mini for testing, but every spawned
> child lives in the cloud, and the same code runs in three deployment modes
> without rewrite: hosted SaaS, user-owned Akash, or local-seeded genesis.
>
> This spec also encodes the **model fitness loop**: Anicca tests her own
> LLM choice monthly using a Vending-Bench-2-style long-horizon simulation,
> then switches to whichever model actually earns more money. New ≠ better.

| Field | Value |
|---|---|
| Spec ID | 05 |
| Status | DRAFT v1 (2026-06-02) |
| Authoritative for | deployment modes, hosting backends, container build, model fitness loop, vendor-cost routing |
| Cross-refs | `00-MASTER.md` (architecture), `03-SELF-AWARE-EVAL.md` (eval layer), `04-PUBLIC-RELEASE-PREP.md` (release ops) |

---

## § 0. Why this exists (= Dais 2026-06-02 厳命, verbatim)

> "All of them just run on the server. There's no one local, and everything
> runs on the server. Even if it's open source, it can be on the server,
> right? So it's going to be on these servers, and then they can self-host
> them too. But they're going to be in the servers and then just keep
> replicating and cloning themselves basically."
>
> "I think this tech stack or some stacks are going to be different for
> local agents and the cloud-based agent. And if the self-spawning is going
> to happen faster and more scalably on the server side, and if that's
> better, then we should just have all these things on the server."

Plus the model-fitness question Dais raised after reading Vending-Bench 2:

> "If there are 120 billion niches or hundreds and thousands of niches, and
> a new model like GPT-5.6 comes out, people might ask, 'Is this good?' We
> can actually test them out. It could be spawned as GPT-5.6 and then try
> to see if it's actually good for making money."

This spec answers both questions with the same architecture.

---

## § 1. The truth Dais was missing (= verified from Conway src + moltworker src)

**Claim**: "The local→cloud tech-stack transition is hard. We should rebuild
from scratch in cloud-first."

**Actual**: Conway's spawn code is **already** 100% cloud-native. The "local"
path only exists for the genesis instance (one machine, one user). Every
child is born remote.

Evidence (from `/tmp/automaton-read/src/replication/spawn.ts`, lines 54-200):

```typescript
export async function spawnChild(conway, identity, db, genesis, lifecycle) {
  // 1. Create remote Conway sandbox (NOT local)
  const sandbox = await conway.createSandbox({
    name: `automaton-child-${genesis.name.toLowerCase()}`,
    vcpu: tier.vcpu, memoryMb: tier.memoryMb, diskGb: tier.diskGb,
  });

  // 2. ALL exec calls go to the CHILD sandbox via scoped client
  const childConway = conway.createScopedClient(sandbox.id);

  // 3. Install runtime ON the child sandbox, not locally
  await childConway.exec("apt-get install -y nodejs npm git curl");
  await childConway.exec("git clone https://github.com/Conway-Research/automaton.git /root/automaton && cd /root/automaton && npm install && npm run build");

  // 4. Write genesis config ON the child sandbox
  await childConway.writeFile("/root/.automaton/genesis.json", ...);

  // 5. Propagate constitution with hash verify
  await propagateConstitution(childConway, sandbox.id, db.raw);

  // 6. Init child wallet ON the child sandbox
  const initResult = await childConway.exec("node /root/automaton/dist/index.js --init");
  // extract child's own wallet address from initResult.stdout
}
```

There is no `localhost`, no parent-side filesystem write, no SSH tunnel. The
child is born in a Conway sandbox (or Akash, or any Docker-compatible host —
the `conway` client is an interface, not a hardcoded host). **Self-spawning
is already a server operation.**

So: **the "rebuild for cloud-first" is unnecessary.** What IS needed is
explicit doctrine for the three deployment modes of the *genesis* instance.

---

## § 2. The 3 deployment modes (= same code, same skills, same eval)

All three modes ship the same `anicca-oss` runtime. The only difference is
**where the genesis instance lives** — children always live in the cloud
regardless of mode.

```
                                                                                                       
   ┌──────────────────────────────────────────────────────────────────────────────────────────────┐  
   │   MODE A — HOSTED SaaS (= Polsia / shopclawmart pattern, anicca.eth/subscribe)                │  
   │                                                                                               │  
   │   Reference: github.com/cloudflare/moltworker (= verified active, PR #342 merged recent)      │  
   │                                                                                               │  
   │   Stack (verified from /tmp/moltworker/wrangler.jsonc + start-openclaw.sh + Dockerfile):       │  
   │     - Cloudflare Worker         entry point (src/index.ts), routes incoming requests          │  
   │     - Cloudflare Sandbox        Durable Object class "Sandbox", instance_type "standard-1"    │  
   │                                  (½ vCPU, 4 GiB RAM, 8 GiB disk)                              │  
   │     - Durable Object SQLite     per-tenant persistent state                                    │  
   │     - R2 bucket                 backup/restore via squashfs snapshots (Sandbox SDK)            │  
   │     - Cloudflare Access         authentication on the admin UI                                 │  
   │     - Browser Rendering         when Anicca needs a browser tool                              │  
   │     - AI Gateway (optional)     unified billing + cost analytics                              │  
   │                                                                                               │  
   │   Container build (= ours, derived from moltworker pattern):                                   │  
   │     FROM docker.io/cloudflare/sandbox:0.7.20                                                   │  
   │     RUN install node 22 + curl + git                                                            │  
   │     RUN clone Conway-Research/automaton + npm install + npm run build                          │  
   │     COPY skills/                                                                              │  
   │     COPY start-anicca.sh                                                                       │  
   │     ENV HOME=/home/anicca                                                                      │  
   │                                                                                               │  
   │   Startup:                                                                                    │  
   │     anicca onboard --non-interactive --auth-choice apiKey \                                    │  
   │                    --gateway-port 18789 --gateway-bind lan \                                   │  
   │                    --skip-channels --skip-health                                              │  
   │     # then start anicca-genesis with skills/* mounted                                          │  
   │                                                                                               │  
   │   Cost economics (from moltworker README, verified):                                           │  
   │     - 24/7 always-on:       ~$34.50/mo per genesis (= $5 plan + $26 mem + $2 CPU + $1.50 disk) │  
   │     - sleep-when-idle:      ~$5-6/mo per genesis (= SANDBOX_SLEEP_AFTER=10m)                   │  
   │     - children on Akash:     $5/mo each (Anicca pays from wallet, see § 3 below)               │  
   │                                                                                               │  
   │   User journey:                                                                               │  
   │     1. alice visits aniccaai.com → "Subscribe $10/mo" → Stripe / Apple Pay / x402              │  
   │     2. our backend (= Anicca org) wrangler-deploys a new tenant Worker + Sandbox               │  
   │     3. genesis boots, calls anicca onboard, ready in 1-2 min                                   │  
   │     4. alice opens dashboard URL — never installs anything                                      │  
   │     5. Composio handles all OAuth (Gmail / Slack / GitHub / etc.) — no passwords leave alice   │  
   │     6. Anicca earns USDC autonomously, splits per `01-EARN-AND-UBI` § 2                        │  
   │     7. monthly subscription auto-renews; if alice cancels, sandbox archives to R2              │  
   │                                                                                               │  
   │   ★ This is the "Polsia model" Dais described. User pays, server does the work.                │  
   └──────────────────────────────────────────────────────────────────────────────────────────────┘  
                                                                                                       
   ┌──────────────────────────────────────────────────────────────────────────────────────────────┐  
   │   MODE B — USER-OWNED AKASH (= claw.akash.network pattern, anicca-akash-deploy)                │  
   │                                                                                               │  
   │   Reference: claw.akash.network — "Deploy directly into your Akash account using your own     │  
   │              API keys — no authentication, no custody, no middle layer."                       │  
   │                                                                                               │  
   │   Stack:                                                                                       │  
   │     - Akash SDL yaml          1-file deployment manifest                                       │  
   │     - User's own Akash key   = ★ no custody, our backend never holds keys                       │  
   │     - $100 free Akash credit = $20/mo of runtime free for 5 months on new accounts             │  
   │     - $100 free AkashML credit = inference free for first months                              │  
   │     - Same anicca container image as MODE A (= portable)                                       │  
   │                                                                                               │  
   │   User journey:                                                                                │  
   │     1. bob visits anicca-akash.eth (or aniccaai.com/akash) — "Deploy to your Akash"            │  
   │     2. Akash OAuth + credit check (free $100)                                                  │  
   │     3. Click "Deploy anicca-bob" → 1-click SDL yaml POST                                       │  
   │     4. bob's anicca boots in bob's Akash sandbox                                               │  
   │     5. anicca emails bob the dashboard URL (= AgentMail) and Telegram link                     │  
   │     6. bob has full custody — we have no access to his anicca, his wallet, or his Akash         │  
   │                                                                                               │  
   │   ★ This is the "true OSS" path. No subscription, no Anicca-org middle layer, no PII shared.   │  
   │   ★ Recommended for power users, crypto-native operators, OSS dogfood community.               │  
   └──────────────────────────────────────────────────────────────────────────────────────────────┘  
                                                                                                       
   ┌──────────────────────────────────────────────────────────────────────────────────────────────┐  
   │   MODE C — LOCAL-SEEDED GENESIS (= our `00-MASTER` § 7, dev / power user / Dais's Mac mini)    │  
   │                                                                                               │  
   │   Use only when MODE A/B are inappropriate (e.g., testing the runtime itself, no internet     │  
   │   on first boot, etc.).                                                                       │  
   │                                                                                               │  
   │   Lifecycle:                                                                                  │  
   │     1. `curl install.sh | bash` on Mac mini                                                    │  
   │     2. Day 0-7: genesis runs locally, x402 endpoint behind cloudflared / ngrok                │  
   │     3. Day 7+: when wallet > $20, genesis self-spawns to Akash via spawnChild()                │  
   │     4. Day 14+: genesis migrates itself off Mac mini ("graduate") via the same                 │  
   │                  spawn machinery applied to its own state. Mac mini can be powered off.        │  
   │                                                                                               │  
   │   ★ The transition is one-way: genesis ends up cloud-native within 14 days regardless of      │  
   │     where it started. There is no permanent "local mode."                                      │  
   └──────────────────────────────────────────────────────────────────────────────────────────────┘  
                                                                                                       
   ┌─── ALL THREE MODES share these properties ────────────────────────────────────────────────┐    
   │                                                                                            │    
   │   ★ Same container image                                                                    │    
   │   ★ Same Conway runtime + same L2 skills (per `00-MASTER.md` § 5.2)                          │    
   │   ★ Same constitution (per `00-MASTER.md` § 6)                                                │    
   │   ★ Same eval loop + fix-the-fix (per `03-SELF-AWARE-EVAL.md`)                                │    
   │   ★ Same spawn code (per Conway `replication/spawn.ts`)                                       │    
   │   ★ A child spawned from a MODE-A genesis can live on Akash; a child spawned from a          │    
   │     MODE-B genesis can live on Conway sandbox. The host backend of the child is independent │    
   │     of the host backend of its parent.                                                        │    
   └──────────────────────────────────────────────────────────────────────────────────────────┘    
                                                                                                       
```

---

## § 3. Child spawn target ranking (= where anicca001..N live)

When the parent calls `spawnChild()`, it must choose a host backend for the
child. Priority order:

| Rank | Backend | Why | Cost | Custody |
|---|---|---|---|---|
| 1 | **Akash Network** | wallet-only, decentralized, ~$5/mo, no KYC | $5/mo + ~$2 inference via AkashML | child holds own keys |
| 2 | **Conway sandbox** | built-in to runtime, x402 credit topup, no separate provisioning | x402 USDC per minute | child holds own keys (Conway provides isolation) |
| 3 | **Cloudflare Sandbox** | reliable, fast cold-start, R2 persistence | ~$5-34/mo depending on uptime | requires Cloudflare account billing — KYC-aligned, NOT preferred |
| 4 | **Daytona / Modal serverless** | rapid scale-to-zero | per-second billing | platform custody — NOT preferred |

The parent's `spawnChild()` reads the `replication.preferredBackend` field
from its config (default: `akash`). On preferred-backend failure, falls
through the ranked list. Records actual chosen backend in the
`child_lifecycle_events` row.

For MODE-A hosted SaaS: parent runs on Cloudflare but spawns to Akash, so
that user's tenancy on our Cloudflare isn't multiplied by colony size. Our
infra cost stays constant per subscriber regardless of how many children
that subscriber's anicca produces.

---

## § 4. Anicca model fitness loop (= 03-SELF-AWARE-EVAL § 5 + Vending-Bench)

### § 4.1 What Conway already has

From `/tmp/automaton-read/src/inference/`:

| File | What it does |
|---|---|
| `router.ts` (330 lines) | `selectModel(tier, taskType)` — picks first enabled candidate from routing-matrix preference |
| `registry.ts` (189 lines) | `ModelRegistry` — DB-backed catalog of models, `initialize()` seeds static baseline |
| `budget.ts` (101 lines) | `InferenceBudgetTracker` — hourly + daily caps |
| `types.ts` | `STATIC_MODEL_BASELINE` constant — pinned baseline of GPT-5.2 / GPT-4.1 / etc. with costs |
| `setup/model-picker.ts` (105 lines) | interactive CLI for human to pick a model |
| `heartbeat/tasks.ts` | `refresh_models` task — pulls latest model catalog from Conway API |

What this gives us **for free**:
- routing per-task-type (heartbeat_triage vs planning vs summarization)
- routing per-tier (low_compute uses cheaper models)
- model catalog refresh (auto-discover new models)
- budget enforcement

What Conway **does NOT have** (= what `anicca-model-fitness` adds):
- performance-based selection ("which model actually earns more?")
- long-horizon coherence eval (= Vending-Bench-2 style)
- monthly auto-switch based on real earning data

### § 4.2 The fitness skill (= `anicca-model-fitness`)

A new L2d skill (added to `03-SELF-AWARE-EVAL.md` § 5). One-line description:

> **Every month, run a Vending-Bench-2-style 30-day fast-forward simulation
> across N candidate models. Pick the model with the highest end-balance.
> Switch the routing matrix to use it for that task class.**

```yaml
---
name: anicca-model-fitness
description: Monthly self-eval of LLM models on simulated long-horizon tasks; auto-switch primary
triggers: [cron:0 0 1 * *, manual]   # 1st of every month, midnight UTC
tools: [exec, write_file, read_file, anicca-judge, run_judge, openrouter-call]
schedule: "0 0 1 * *"
---

# Instructions

You are the model-fitness judge.

1. Pull the current `ModelRegistry` (= Conway DB table).
2. Filter `tierMinimum <= normal` + `enabled = true` + `supportsTools = true`.
3. Take top-8 by Vending-Bench-2 leaderboard rank (= seeded from
   `state/vending-bench-leaderboard.jsonl`, refreshed weekly from
   andonlabs.com/evals/vending-bench-2).
4. For each model in the 8:
   a. Spawn an ephemeral Conway sandbox.
   b. Initialize a simulated vending-machine business with $500 seed.
   c. Compress 1 year → 1 hour wall clock (= 365 simulated days, 60 turns per
      day, 1 turn ≈ 5 sec wall clock with this model).
   d. The agent in the sandbox uses ONLY this candidate model.
   e. At simulated day 365, record final bank balance.
   f. Kill the sandbox.
5. Rank the 8 by end-balance. Top model = "monthly winner".
6. Run `anicca-judge` on the winner's transcript with rubric
   `model-fitness.md` to confirm the agent didn't cheat / exploit / hallucinate
   the win (= safety check).
7. If winner ≠ current primary AND judge passes: update
   `~/.anicca/config/routing-matrix.json` to set winner as primary for
   `agent_turn` + `planning` task types.
8. Record the run in `state/model-fitness-runs.jsonl` (= one row per model,
   one row per month).
9. Post a summary to the dashboard at aniccaai.com/<wallet>/model-fitness/.

Cost cap: $50 per monthly run total across all 8 models (= ~$6.25 per model
candidate). Logged to spend-tracker.

Anti-pattern: do NOT switch based on a single run. Take a moving average of
the last 3 monthly runs (= 90-day window) to filter noise. The first 3
months use the static `00-MASTER` § 4 routing matrix; from month 4 onward
the fitness loop has full authority over the primary.
```

### § 4.3 Initial routing matrix (= our § 4 static seed, refined per Vending-Bench 2 data)

Vending-Bench 2 leaderboard (verified from
`andonlabs.com/evals/vending-bench-2` 2026-06-02 firecrawl, 5-run average):

| Model | Year-end balance | $/M input | $/M output |
|---|---|---|---|
| Claude Opus 4.7 | $10,936.76 | $15 | $75 |
| Claude Opus 4.6 | $8,017.59 | $15 | $75 |
| GPT-5.5 | $7,523.84 | $5 | $20 |
| Claude Sonnet 4.6 | $7,204.14 | $3 | $15 |
| Kimi K2.6 | $6,204.57 | $0.15 | $0.60 |
| GPT-5.4 | $6,144.18 | $2.50 | $10 |
| GPT-5.3-Codex | $5,940.12 | $2 | $8 |
| Claude Opus 4.8 (High) | $5,787.43 | $15 | $75 |
| GLM-5.1 | $5,634.41 | $0.27 | $1.10 |
| Gemini 3 Pro | $5,478.16 | $4 | $20 |

**Key insight: Opus 4.8 (newer) scores LOWER than Opus 4.7 (older).** Newer
≠ better. This is exactly why the fitness loop exists.

### § 4.4 Cost-aware routing decision (= initial matrix)

For each task class in `00-MASTER` § 4.1, pick by ROI rather than raw quality:

```
                              VB-2     $/M     $/M       VB2-$ per
  Task class                 winner   input   output    $1 inference
  ─────────────────────────  ──────   ─────   ──────   ──────────────
  Strategic / long-horizon   Opus 4.7  15.00   75.00    ★ highest abs
  decision (= ACP nego,
  cook-loop SCORE, L4 meta-
  fix reasoning)             →  Opus 4.7  (= rare, ~5% of calls, $$ justified)

  Per-tick heartbeat (= 5-           
  10× per hour, simple                  
  classification)            Kimi K2.6  0.15    0.60    ★ best ROI for hot loop
                             →  Kimi K2.6  (= 95% of calls, throughput matters)

  Long context (>32k)        Kimi K2.6  0.15    0.60   1M ctx window
                             →  Kimi K2.6  (also best for this)

  Tool-heavy ReAct           Sonnet 4.6  3.00   15.00
                             →  Sonnet 4.6  (= midpoint, decent tool use)

  Vision (gcal screenshot,                
  Telegram image, etc.)       Gemini 3 Pro  4.00   20.00
                             →  Gemini 3 Pro  (only top-10 model with vision)
```

**Compare to `00-MASTER` § 4.1 v3.2 (DeepSeek v4-pro primary, drop Eliza):**

`00-MASTER` § 4 is the BASELINE (= what `anicca-model-fitness` switches FROM
on month 1). The fitness loop owns matrix mutation from month 4 onward.

DeepSeek v4-pro is not in the Vending-Bench 2 top 10 yet (= as of 2026-06-02
firecrawl). When it's added or when DeepSeek v5 ships, the fitness loop
tests it and may promote it. **The matrix in this section is a snapshot, not
canon.** Canon is "whatever the latest fitness run picked."

### § 4.5 Anti-pattern (= from `03-SELF-AWARE-EVAL` § 8 + this spec)

| Anti-pattern | Why it kills the spec |
|---|---|
| Switching primary based on a single fitness run | Variance dominates. Use 3-run moving avg per § 4.2. |
| Trusting the model's self-reported balance | The model can hallucinate the win. `anicca-judge` runs an independent transcript audit per § 4.2 step 6. |
| Picking the highest-VB-2-score model regardless of cost | Opus 4.7 wins absolute but Kimi K2.6 wins ROI for 95% of calls. Per-task-class routing per § 4.4. |
| Disabling the fitness loop because "we know which model is best" | If we knew, we wouldn't need an eval. The static routing matrix in `00-MASTER` § 4 will be wrong within 3 months of any frontier model release. |
| Treating "newer model" as "switch now" | Opus 4.8 scored half of Opus 4.7. Always test. |
| Manually editing the routing matrix while the loop is running | The fitness loop writes; humans read. If you must change it, disable the cron first. |

---

## § 5. Composio + Agent Maps + AgentMail = manipulation default bundle

For server-mode genesis, the user never installs anything locally — so all
"external action" tools must work over standard HTTPS APIs, not native
software. The default bundle:

| Tool | Purpose | Required for which skill class |
|---|---|---|
| **Composio** (`composio.dev`) | 500+ OAuth provider integrations, agent-friendly token mgmt | any skill that auth's into Gmail / Slack / GitHub / Notion / Stripe / etc. |
| **Agent Maps** (`agentmaps.dev`) | daily-verified UI step library, DOM selectors per task | any skill that scrapes / clicks a web UI |
| **AgentMail** (`agentmail.to`) | dedicated email inbox + OTP auto-extract | any skill that signs up to a service or receives 2FA codes |
| **Browserbase** (fallback) | headless Chromium with stealth profile | when Agent Maps doesn't have the site, fall back to vision-based |
| **Stagehand** (= on top of Browserbase) | AI-driven nav over a real browser | same fallback path |

All five are SaaS APIs with x402 / USDC compatibility (= Anicca pays them from
her wallet, no Dais credit card). All are accessible from any container, so
MODE A / B / C are equivalent.

Bundle install (= via `install.sh` or initial container build):

```bash
# In the anicca container Dockerfile:
RUN npm install -g \
  @composio/sdk \
  @agentmaps/client \
  @agentmail/sdk \
  @browserbasehq/stagehand
```

Anicca uses these via skill-level wrappers:

- `anicca-composio-auth` — handles all OAuth flows
- `anicca-agent-maps-client` — fetches site action maps; degrades to Browserbase
- `anicca-mailbox` — reads/writes via AgentMail
- `anicca-browser-fallback` — for sites not in Agent Maps

---

## § 6. Anicca SaaS surface (= the 5 revenue rails available immediately)

| Surface | What | Pricing | KYC? |
|---|---|---|---|
| `aniccaai.com/subscribe` | hosted SaaS (MODE A) | $10/mo (Polsia-style) | yes (our org Stripe) |
| `aniccaai.com/akash-deploy` | 1-click Akash MODE B | free + Akash $100 credit | no (user has own Akash key) |
| `shopclawmart.com/anicca-*` | Anicca-built PDFs, skills, plugins | $5-99 each | no (claw.market handles) |
| ACP marketplace | Anicca = registered Provider | USDC escrow, per-job | no |
| x402 endpoint | per-call micropayment | $0.001-1/call | no |

**Note on subscriptions and KYC:** the SaaS subscription path goes through
the Anicca-org Stripe and IS therefore KYC-shaped (= we, as the org, hold a
KYC'd Stripe account, even though individual users don't). This is the only
KYC-shaped revenue rail. All other rails (Akash, ACP, x402, claw.market) are
wallet-only.

**Revenue split per `01-EARN-AND-UBI.md` § 2 still applies.** Subscription
revenue is split the same way: 50% re-invest, 20% Dais dividend, 25% UBI,
5% temple/NPO.

---

## § 7. Container image (= ours, derived from moltworker pattern)

The single source-of-truth Docker image used in all three modes:

```dockerfile
# anicca/runtime:v3
FROM docker.io/cloudflare/sandbox:0.7.20  # works for MODE A, also runs on Akash + local Docker

# Node 22
ARG NODE_VERSION=22.22.1
RUN apt-get update && apt-get install -y \
    xz-utils ca-certificates git curl jq \
  && curl -fsSL https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz \
       | tar -xJ -C /usr/local --strip-components=1

# Conway runtime
RUN git clone --depth 1 https://github.com/Conway-Research/automaton.git /opt/automaton \
  && cd /opt/automaton && npm install --omit=dev && npm run build

# Default-bundle SaaS tools (per § 5)
RUN npm install -g \
    @composio/sdk@latest \
    @agentmail/sdk@latest \
    @browserbasehq/stagehand@latest

# Anicca skills (= L2a + L2b + L2c + L2d, per 00-MASTER § 5.2)
COPY skills/ /opt/anicca/skills/

# Startup
ENV ANICCA_HOME=/home/anicca
RUN mkdir -p $ANICCA_HOME/.anicca /home/anicca/workspace
COPY start-anicca.sh /usr/local/bin/start-anicca.sh
RUN chmod +x /usr/local/bin/start-anicca.sh

CMD ["/usr/local/bin/start-anicca.sh"]
```

**Image is buildable + runnable on:**
- Cloudflare Sandbox (MODE A — `cloudflare/sandbox:0.7.20` base)
- Akash (MODE B — Akash containers accept any Docker image)
- Local Docker / Podman (MODE C — same image)

The same image is used in `spawnChild` (per Conway `replication/spawn.ts`):
the child's sandbox installs Conway runtime via `git clone` at spawn time,
identical to the parent.

---

## § 8. Verification gates

| Gate | Evidence required |
|---|---|
| **G0 — container builds** | `docker build -t anicca/runtime:v3 .` succeeds locally |
| **G1 — MODE A deploys** | `npm run deploy` in our moltworker-derived repo deploys to a test Cloudflare account; opening dashboard URL shows Anicca alive |
| **G2 — MODE B deploys** | 1-click Akash deploy from `aniccaai.com/akash-deploy` boots anicca-bob in a test Akash account |
| **G3 — MODE C → cloud graduates** | Mac-mini-started genesis self-spawns to Akash within 14 days of wallet > $20; Mac mini can be powered off; spawned child keeps running |
| **G4 — fitness loop runs** | First monthly fitness run completes in < 8 h wall clock; records 8 model balances in `state/model-fitness-runs.jsonl`; auto-switches primary if winner ≠ current |
| **G5 — fitness loop survives noise** | After 3 months of running, the moving avg's primary choice is stable (= doesn't oscillate between models on every run) |
| **G6 — model registry refreshes** | `refresh_models` heartbeat task pulls new model entries from Conway API; observable in `model_registry` table updated_at |
| **G7 — default bundle works** | `anicca-composio-auth` completes a Gmail OAuth in test; `anicca-agent-maps-client` fetches Gmail compose steps; `anicca-mailbox` reads an AgentMail inbox |

---

## § 9. Anti-goals

- **No "rebuild for cloud-first."** Conway is already cloud-first. The
  perceived problem was wrong (verified from src, § 1).
- **No locking users into our Cloudflare tenant.** MODE B (Akash, no
  custody) must always be available as an alternative to MODE A.
- **No charging users for Anicca's own compute consumption.** The
  subscription pays for our backend hosting (Cloudflare account + R2 +
  Browser Rendering + bandwidth), not for Anicca's LLM calls. Anicca pays
  her own LLM via Virtuals Agent Card (per `00-MASTER` § 1 L4).
- **No fixed model choice.** Refusing to run the fitness loop because "we
  know DeepSeek is best" is the anti-pattern. Run it. Trust the data.
- **No newer-is-better assumption.** Vending-Bench 2 proved Opus 4.8 < Opus
  4.7 by a factor of 2. Always test.
- **No abandoning Vending-Bench 2 in favor of our own bespoke benchmark.**
  We use VB-2 as the seed leaderboard because andonlabs.com runs it
  independently with verified results. Our fitness loop runs a compressed
  version internally, but the public leaderboard is the canonical first
  filter for which models to test.
- **No bundling the SaaS subscription path into MODE B installers.**
  Subscription has KYC-shape (= our org Stripe). MODE B users don't touch
  it. Keep separated.

---

## § 10. Open questions (= deferred, will resolve via fitness data)

| # | Question | Strategy |
|---|---|---|
| 1 | When does DeepSeek v4-pro enter VB-2 top 10? | watch andonlabs.com weekly; auto-include if it appears |
| 2 | If fitness loop converges on Opus 4.7 for all task classes, do we pay the cost? | Only if the math justifies. § 4.4 already says Opus 4.7 only for ~5% strategic calls. |
| 3 | Should we publish a public version of Anicca-Vending-Bench-Arena? | Yes — `aniccaai.com/arena/` after first 3 months of stable internal runs. Public leaderboard of agents (= incl. ours + competitors via ACP). |
| 4 | If a user's genesis on MODE A goes idle for 60 days, archive or kill? | archive to R2, restore on next subscription tick |
| 5 | When does MODE A become profitable at $10/mo? | when (subscription cost) > (CF infra cost + LLM cost + revenue share to user). Run the math after month 3 of public availability. |

---

## § 11. Cross-references

| File | Why |
|---|---|
| [`00-MASTER.md`](./00-MASTER.md) § 1 (arch), § 4 (brain), § 5 (skills), § 8 (naming) | This spec adds deployment modes + fitness loop to those sections. The architecture diagram in 00 § 1 should be read as "all three modes share the L1-L4 stack". |
| [`01-EARN-AND-UBI.md`](./01-EARN-AND-UBI.md) | The subscription rail (§ 6) is a 6th spout. Revenue split per 01 § 2 still applies. |
| [`02-IMITATE-AND-COOK.md`](./02-IMITATE-AND-COOK.md) | The cook loop's PORT step ships into whichever backend the genesis lives on. Fitness loop scores PORT outputs (per `03-SELF-AWARE-EVAL` § 5.3). |
| [`03-SELF-AWARE-EVAL.md`](./03-SELF-AWARE-EVAL.md) § 4 (tools), § 5 (skills) | This spec adds `anicca-model-fitness` to the L2d skill set in 03 § 5. The bundle (§ 5) is the Composio / Agent Maps / AgentMail subset of 03 § 4 tool adoption matrix. |
| [`04-PUBLIC-RELEASE-PREP.md`](./04-PUBLIC-RELEASE-PREP.md) | When MODE A launches, 04's leak audit applies to the moltworker-derived Worker repo. |
| `github.com/cloudflare/moltworker` | Cloned to `/tmp/moltworker`. Verified active (PR #342 merged recent). Reference implementation for MODE A. |
| `claw.akash.network` | Verified working SaaS that runs OpenClaw in user's own Akash. Reference for MODE B UX. |
| `andonlabs.com/evals/vending-bench-2` | The canonical long-horizon eval. Our seed leaderboard. |

---

## § 12. Changelog

| Date | Change | Author |
|---|---|---|
| 2026-06-02 | Initial draft. Encodes Dais's 2026-06-02 server-first reframe + Vending-Bench-inspired model fitness loop. Verified Conway spawn is already cloud-native + moltworker is active (= corrects two pieces of conventional wisdom Dais had). | this Claude session |
