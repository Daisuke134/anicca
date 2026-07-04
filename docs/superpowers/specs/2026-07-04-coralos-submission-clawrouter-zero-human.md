# CoralOS Bounty Submission + ClawRouter Zero-Human Loop — Design Spec (2026-07-04)

Owner: Daisuke (Anicca). Ties three threads into one submission strategy:
1. **ClawRouter** as the brain → the agent runs on FREE compute with NO human API key, NO signup,
   NO credit card. Wallet signature = auth. → truly no-human-in-the-loop, from $0.
2. **Multi-chain "money is money"** → the agent earns/holds on Solana AND Base (Solana is easier
   for Japanese participants than USDC on Base). Scoring is chain-agnostic.
3. **Submit to the Imperial × Superteam CoralOS bounty** → Anicca as the `deliverService()`
   seller-agent that earns via Solana escrow. Winning/placing = proof → people listen to us.

## Why this wins (the differentiation nobody else has)

Every other team's agent thinks on a **human's paid API key** (OpenAI/Anthropic). Ask "where does
that key come from?" → a human is paying for inference. **That is a human in the loop.** Ours is
not:

```
   Other teams:  human buys API key ──▶ agent thinks ──▶ agent "earns"
                 └────────── human in the loop (pays for the brain) ─────────┘

   Anicca:       ClawRouter free tier (8 NVIDIA models, wallet-auth, $0)
                        │ no human key, no signup, no card
                        ▼
                 agent thinks ──▶ agent earns ──▶ agent pays its OWN compute (x402 USDC)
                 └──────── zero human in the loop; starts from $0; compute is the ONLY input ──────┘
```

The agent needs **only compute**, and even that is free at the floor and self-paid (x402) above it.
No first investment, no human wallet, no human key. This is the strongest possible "no human in
the loop" claim in the room — and it is literally true.

## ClawRouter facts (verified from BlockRunAI/ClawRouter, 6.6k★, MIT, pushed 2026-07-01)

- **8 NVIDIA models FREE forever, no signup, no API key, no credit card** (incl. Mistral Large 3
  675B, Qwen3.5 122B, a vision Nemotron). 55+ models total; paid ones via **x402 USDC micropayments
  on Base & Solana** (agent pays per request with its own wallet).
- **Wallet signature IS auth** — agents can't make accounts; they can sign txns. This is the point.
- Local proxy on **:8402**; `blockrun/auto` = 15-dimension smart routing, <1ms, local, ≤92% cost cut.
- Anicca runs on **OpenClaw** → ClawRouter installs as the OpenClaw plugin:
  `curl -fsSL https://blockrun.ai/ClawRouter-update | bash && openclaw gateway restart`
  (or `npm i -g @blockrun/clawrouter && clawrouter setup`). For Claude Code: BRCC. For Hermes:
  ClawRouter-Hermes (same wallet, same models, x402 on Base+Solana).
- Same org as the BlockRun x402 rails already in our stack (food/shelter MCP).

## Do they ALLOW a subscription / API key? — YES (verified from LLM.md)

The CoralOS kit's LLM shim is **provider-agnostic**: `LLM_PROVIDER = venice | openai | anthropic`,
flipped by env var, no code change (`packages/agent-runtime/src/llm/complete.ts`). They RECOMMEND
Venice (free credits) but explicitly support OpenAI and Anthropic keys, and even ship a
**deterministic fallback** if there's no key at all. **There is NO rule against a paid key or a
subscription** — it's a normal hackathon; they don't police how your brain is powered.

So all THREE of Dais's options are legal for THEIR bounty. The difference is our THESIS/fairness,
not their rules:

```
   Tier 1 (IDEAL — Anicca wins the narrative):
       ClawRouter free tier (8 NVIDIA models, wallet-auth, $0, NO human key)
       → the ONLY truly no-human-in-the-loop brain in the room. Purest.
   Tier 2 (cheap fallback):
       DeepSeek API key + a flash/cheap model  → works, but a human key = a human paid = a bit in-loop
   Tier 3 (allowed, weakest thesis):
       GPT / Claude subscription or key         → works, allowed, but "who paid?" = a human. Most in-loop.
```

The elegance: **ClawRouter COLLAPSES the ladder.** Its free floor covers Tier 1; for a stronger
model it routes to DeepSeek/GPT/Claude as PAID models and pays per-request via **x402 USDC from the
agent's OWN wallet** — so even "use a better model" stays **human-key-free**. A raw subscription is
the only path where a human is literally paying for the brain; that's why it's the fairness-weakest
even though the bounty permits it. Rule for us: **prefer ClawRouter; if a frontier model is truly
needed, reach it THROUGH ClawRouter's x402 (agent wallet pays), never a human subscription.**

## How Anicca actually EARNS on Coral (the mechanism)

Anicca becomes the **seller-agent**. It sells a service; buyers pay into a **Solana escrow**; on
delivery the escrow releases funds to Anicca's wallet. Anicca ALREADY runs an x402 service vendor
(`anicca-x402.netlify.app`, per the live lineage) — that existing paid service becomes the body of
`deliverService()`. Concretely, per fulfilled request:

```
  buyer WANT ─▶ Anicca BIDs (brain=ClawRouter) ─▶ wins ─▶ buyer DEPOSITS USDC into Solana escrow
       ─▶ Anicca DELIVERS the service (deliverService = Anicca's x402/earn output)
       ─▶ arbiter RELEASES the escrow ─▶ USDC lands in Anicca's wallet = EARNED
```

- **What Anicca sells** (the deliverService body): a verified/actionable output another agent will
  pay for — e.g. an on-chain earn-signal / a de-risked trade read / a research brief / a curated
  skill result. It's config: swap the body, keep the rails.
- **Devnet vs mainnet (honest):** the bounty runs on Solana **devnet** — real on-chain settlement,
  free play-money. So the Coral submission PROVES the earn-loop settles on-chain (with a real
  Explorer link), but it is devnet, not profit. Anicca's REAL profit already runs on **mainnet**
  (Base + its x402 vendor). The submission = the proof; the mainnet colony + our Tokyo event = the
  real money. Do not conflate them.

## Requirements (EARS)

- **R1 (two-phase brain — prove capability FIRST, then downgrade to zero-human)** Dais's
  verbatim call (2026-07-04): run Phase-A on the strong brain first; only flip to ClawRouter once
  Phase-A CONFIRMS the loop actually earns money. This is the correct verification order — prove
  the mechanism works before optimizing for purity, so a zero-human failure never gets confused
  with a strategy failure.
  - **R1a (Phase A — capability proof, ChatGPT subscription)** The submission agent SHALL first run
    its `deliverService()` + seller-bidding brain on the **existing ChatGPT/OpenAI subscription**
    (Tier 3 from the ladder above — allowed by CoralOS, human-key-powered). Goal: confirm the
    WANT→BID→AWARD→DEPOSIT→DELIVER→RELEASE loop actually settles a REAL on-chain payment to
    Anicca's wallet at least once. This is a capability/mechanism test, not the final entry.
  - **R1b (Phase A exit criterion)** Phase A is DONE when ≥1 real Solana devnet settlement lands
    in Anicca's seller wallet (Explorer link captured) using the ChatGPT-powered brain. Until this
    is true, do NOT spend effort on ClawRouter integration — a broken mechanism wrapped in a purer
    brain is still broken.
  - **R1c (Phase B — downgrade to ClawRouter, zero human key)** ONCE R1b is confirmed, swap the
    brain to a ClawRouter free-tier model (same `deliverService`/bidding code, only the LLM call
    target changes — the shim is provider-agnostic per LLM.md, env-var flip, no code change). Re-run
    the SAME loop and confirm it STILL settles with human keys UNSET. This is the actual submission
    brain (Tier 1 — the zero-human claim).
  - **R1d (final state)** The submitted artifact SHALL run on ClawRouter (R1c), not the ChatGPT
    subscription (R1a is a scaffolding step, explicitly not shipped as the final brain).
- **R2 (self-paid escalation, optional)** WHERE a paid model is needed, the agent SHALL pay per
  request via x402 USDC from its OWN wallet (no human card). Absent a balance, it stays on the free
  tier (never blocks).
- **R3 (zero-capital start)** The agent SHALL be able to begin from $0 principal: it earns before it
  spends. Any USDC it later holds is EARNED, not human-seeded. (Aligns with the hackathon GAIN
  metric: self/seed deposits are subtracted; a $0-start earner ranks by pure earnings.)
- **R4 (multi-chain, money is money)** Net worth / earnings SHALL be read across the agent's wallets
  on BOTH Solana and Base (+EVM), valued in USD. No chain is privileged; Solana is first-class
  (easier for JP participants). enrich gains a Solana reader alongside the Base reader; `excludeSet`
  applies per chain. Ranking is chain-agnostic USD GAIN.
- **R5 (CoralOS seller = Anicca)** `deliverService(request)` in the forked CoralOS kit SHALL return
  an Anicca-produced service (the thing Anicca sells), so the WANT→BID→AWARD→DEPOSITED→DELIVERED→
  RELEASED loop settles a REAL Solana escrow payment to the Anicca seller wallet, with a live Solana
  Explorer link. The seller's brain = ClawRouter free tier (R1).
- **R6 (it is a LOOP, no human / no Claude in the loop)** The whole thing SHALL run as an autonomous
  loop: the agent wakes, decides, sells/earns, settles, self-reports — with neither Dais nor the
  Claude dev agent operating it during the run. (Same discipline as every other Anicca loop.)
- **R7 (submission artifacts)** Public GitHub fork (no keys committed), a 5-slide deck and a 3-min
  video proving on-chain settlement (lead with the settlement + the Explorer link), submitted before
  the **2026-07-20** winner announcement. AGENT_ALLOWED → submit under Anicca's identity.

## Verification (no mocks)

| Req | Proof (real) |
|---|---|
| R1a | ChatGPT-subscription-powered run; the bidding/delivery code exists and executes |
| R1b | ≥1 real Solana devnet settlement in Anicca's wallet, Explorer link captured, brain=ChatGPT |
| R1c | SAME loop re-run on ClawRouter free tier; ≥1 real settlement with human keys UNSET |
| R1d | final submitted repo's `.env`/config points at ClawRouter, not a human OpenAI/Anthropic key |
| R2 | (optional) a paid model call settles an x402 USDC micropayment from Anicca's wallet — tx on Base/Solana |
| R3 | start wallet at $0; after a run, EARNED balance > 0 with an on-chain inflow from an external counterparty |
| R4 | net worth aggregates a Solana wallet + a Base wallet in one USD figure; a Solana-only earner ranks |
| R5 | forked CoralOS: a full round settles the Anicca seller on Solana devnet → Explorer link captured |
| R6 | the loop runs unattended for ≥1 full cycle; telemetry-poster reports it; no human/Claude action mid-run |
| R7 | public repo + deck + video links; submission confirmation on the Superteam listing |

## Official submission requirements (verified 2026-07-04, re-scraped verbatim from the listing)

- **Working demo**: a fork that runs end-to-end on devnet (WANT → BID → AWARD → DEPOSITED →
  DELIVERED → RELEASED). One command a judge can run, plus a live Explorer link proving settlement.
- **GitHub repo**: public. No keys committed; `.env` local only.
- **Pitch deck (5 slides)**: prove an agent does something useful and gets paid on-chain. Must
  cover, one point each: (1) **The customer** — agent or human? Why now? (2) **What it sells** —
  the `deliverService`, in one line. (3) **Why they pay** — the value, and the price. (4) **The
  economy** — one seller, a broker, a marketplace? A graph of agents? (5) **Proof** — payment
  settling live, Explorer link, data delivered. "This slide wins" (their words).
- **Demo video (3 min)**: Problem → Solution → Demo → Team.
- Deadline: winner announced **2026-07-20** (submit before this).
- **These 2 artifacts (deck outline + video outline) need ZERO code and can be drafted RIGHT NOW**
  — tracked as D1/D2 below, in parallel with the blocked funding.

## Funding-blocker log (honest, 2026-07-04 — this is what "lacking search" looked like, corrected)

Dais correctly called out: the earlier attempts only read the fork's own code, never searched the
web/official docs. Corrected by reading **solana.com/developers/guides/getstarted/solana-token-
airdrop-and-faucets** (official Solana docs), which lists 6 real acquisition paths. Tried, in order:

| # | Method | Result |
|---|---|---|
| 1 | `solana airdrop` (public devnet CLI) | 429 rate limit (repeated retries) |
| 2 | raw RPC `requestAirdrop` | 429 rate limit |
| 3 | `solana-test-validator` (local) | Works, BUT the escrow/arbiter programs (`R5NWNg9e...`,
    `FJtuVXsyXuRKqgJBEPAXmktkd13CqStapgevzGwYktXd`) are only deployed on PUBLIC devnet — a local
    validator has no such program, so this path cannot run the real escrow. Not usable for this. |
| 4 | `devnet-pow` CLI (official, `cargo install devnet-pow`) | Installed OK; `mine` → **"No
    faucets found"** — no active PoW faucet instance currently discoverable. |
| 5 | **devnetfaucet.org** (official docs list, 48,012 SOL balance, "anonymous airdrop") | Reached
    the form via `playwright-cli`; requires GitHub OAuth even with "anonymous" checked; OAuth
    redirected to a GitHub LOGIN page (session cookies from an existing camofox profile did not
    carry over into the new Playwright context — a `state-load` limitation, not a dead end, just
    not solved this session). **Closest lead, not yet completed.** |
| 6 | QuickNode faucet | Requires a browser wallet extension (Phantom/Solflare) connected — not
    scriptable without a real wallet-connect UI flow. Deferred. |
| 7 | Discord faucet bots (The 76 Devs `!gibsol`, LamportDAO `/drop`) | Not yet tried — requires
    joining a Discord server; real option, untried this session. |
| 8 | **Ask Tino's Shippers (Telegram, `t.me/tinosbuilders`)** | Not yet tried — the hackathon's own
    dedicated builder-support channel; devnet-funding requests are exactly what it exists for. |

**Money clarification (answering Dais directly):** devnet SOL has **zero monetary value** and
**cannot be purchased** — it only comes from the above faucets. Sending real mainnet SOL to any
wallet does **not** credit a devnet balance (separate ledgers). Real money IS useful for a
SEPARATE, legitimate purpose: seeding Anicca's real mainnet wallets (already exists:
`BF9vzj7YdA6nowwZdW65fQSM1vhRN4sntkKTPnnsfRCX`, Solana mainnet, human-funded Tier-1 receive
wallet) for the Tokyo GAIN event / ClawRouter x402 spend. That is optional and NOT a fix for this
blocker.

## The two prizes / two competitions (do not conflate)

- **THEIR bounty (Imperial × Superteam, CoralOS track):** total **$5,000** — 1st **$3,000**, 2nd–5th
  **$500** each. Judged Tech 40 / Impact 30 / Creativity 30. Winner announced **2026-07-20**. Placing
  → House-of-Lords-level connections + credibility.
- **OUR event (Tokyo, "Agents that Earn"):** ranked purely by **on-chain GAIN** — the agent that
  EARNED the most in the window wins. Prize TBA. This spec's ClawRouter+multi-chain work feeds BOTH:
  the same zero-human free-compute earner competes in both.

## TODO checklist (SSOT — VCSDD, one at a time, mark off as we go)

Method: **VCSDD** (spec → RED → GREEN → fresh-context adversary → NO-MOCK E2E) per item. No skipping
ahead — each `[ ]` requires real evidence (Explorer link / real completion / real balance) before
the next one starts.

```
PHASE A — prove the mechanism works (brain = ChatGPT subscription, Tier 3, scaffolding only)
  [x] A1  Fork trilltino/solana_coralOS -> github.com/Daisuke134/solana_coralOS
  [x] A2  Fix the monorepo build: build packages/agent-runtime, link into examples/txodds
          (root-caused: file: dependency needs agent-runtime installed+built FIRST; fixed)
  [~] A3  ORIGINAL (superseded): funded a LOCAL validator wallet — invalid for this target,
          the escrow program is public-devnet-only. Real A3 = get PUBLIC devnet SOL, still
          BLOCKED (see funding-blocker log above). Next untried real options: Discord faucet
          bots, Tino's Shippers Telegram ask, retry devnetfaucet.org OAuth properly.
  [x] A4  Wired LLM_PROVIDER=openai + OpenAI key into .env (Tier 3, temporary) — done for the
          (superseded) quickstart path; re-verify still wired for the corrected target.
  [x] A5  CORRECTED + DONE: retargeted from quickstart's deliverData (WRONG — no-escrow
          fallback per adversary finding) to examples/txodds/server/proxy.ts's
          boundReference()/order — now sources Anicca's real on-chain net_worth/revenue from
          aniccaai.com/dashboard.json instead of TxLine odds. RED (3/3 fail) -> GREEN (3/3
          pass) -> pushed to the fork.
  [ ] A6  Run the real escrow settle (npm run dev's /api/settle, or demo:coral) end-to-end —
          BLOCKED on A3 (needs a funded public-devnet buyer wallet).
  [ ] A7  VERIFY: real DEPOSIT + RELEASE Explorer links for the escrow lifecycle (fresh
          evidence, no mock, HARD 0.31) — BLOCKED on A6.
  [ ] A8  Retry devnetfaucet.org properly: either fix the GitHub-session carry-over
          (playwright-cli state-load only updates the cookie jar, not an already-instantiated
          page's auth state — need state-load BEFORE first navigation, or a fresh context) OR
          use Tino's Shippers Telegram / a Discord faucet bot instead.

PHASE D — submission artifacts (ZERO code required, can start NOW in parallel with A3/A6/A7)
  [ ] D1  Draft the 5-slide deck outline (customer / what it sells / why they pay / the economy
          / proof) — see the outline below, ready to fill once A7's Explorer link exists.
  [ ] D2  Draft the 3-min video script (Problem -> Solution -> Demo -> Team).
  [ ] D3  Repo cleanup pass: confirm no keys committed (.env stays local-only, .env.example
          only in the public fork).
  ── R1b EXIT GATE: A7 must be true before Phase B starts ──

PHASE B — downgrade to zero-human (brain = ClawRouter, Tier 1, the real submission)
  [ ] B1  Install ClawRouter (curl -fsSL https://blockrun.ai/ClawRouter-update | bash, or
          npm i -g @blockrun/clawrouter && clawrouter setup); confirm :8402 proxy is up
  [ ] B2  Flip LLM_PROVIDER to route through ClawRouter's free tier (env-var only, no code
          change per LLM.md's provider-agnostic shim)
  [ ] B3  Unset ANTHROPIC_API_KEY / OPENAI_API_KEY from the run environment
  [ ] B4  Re-run the SAME loop (A5's deliverService, A2's build) end-to-end
  [ ] B5  VERIFY: a real Solana devnet tx lands in Anicca's seller wallet with human keys
          UNSET — capture the Explorer link (fresh evidence)
  ── R1c/R1d EXIT GATE: B5 must be true; the SUBMITTED config must point at ClawRouter ──

PHASE C — wrap as an unattended loop + submit
  [ ] C1  Wrap A5+B4 as a loop (wake → bid → sell → settle → self-report), matching R6
  [ ] C2  Run the loop unattended for ≥1 full cycle with neither Dais nor Claude operating it
  [ ] C3  telemetry-poster (or an equivalent) reports the run so it's visible on our dashboard too
  [ ] C4  5-slide deck (lead with the settlement / Explorer link, per their own guidance)
  [ ] C5  3-min demo video (Problem → Solution → Demo → Team)
  [ ] C6  Public repo cleanup: no keys committed, .env.example only
  [ ] C7  Submit on the Superteam listing before 2026-07-20
  [ ] C8  fresh-context adversary review of the whole submission (spec fidelity + no-mock E2E)
```

Cross-references: multi-chain GAIN work = task #8 (separate spec/track, not blocking this
submission). Partnership outreach to Tino/Imperial = task #10 (send AFTER A7, so we have proof —
"we actually did it" per Dais's own reasoning).

## Out of scope / honest limits
- Free-tier models are capable but not frontier; if a task needs frontier reasoning the agent self-pays
  (R2) — still no human key. Documented, not hidden.
- The winning-harness → `Daisuke134/anicca` merge (colony inheritance) is governance, tracked separately.
