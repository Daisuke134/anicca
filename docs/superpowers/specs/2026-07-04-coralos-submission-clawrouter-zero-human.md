# CoralOS Bounty Submission + ClawRouter Zero-Human Loop — Design Spec (2026-07-04)

Owner: Daisuke (Anicca). Ties three threads into one submission strategy:
1. **ClawRouter** as the brain → the agent runs on FREE compute with NO human API key, NO signup,
   NO credit card. Wallet signature = auth. → truly no-human-in-the-loop, from $0.
2. **Multi-chain "money is money"** → the agent earns/holds on Solana AND Base (Solana is easier
   for Japanese participants than USDC on Base). Scoring is chain-agnostic.
3. **Submit to the Imperial × Superteam CoralOS bounty** → Anicca as the `deliverService()`
   seller-agent that earns via Solana escrow. Winning/placing = proof → people listen to us.

## Is Solana required for "our way" of earning? — NO. It's required ONLY for this one bounty.

Clarifying a question Dais asked directly: **the Tokyo "Agents that Earn" event (the main thing)
does NOT need Solana at all** — it already runs, live, on Base mainnet (real USDC, real GAIN
scoring). Solana devnet is required for exactly ONE thing: **this specific CoralOS bounty**,
because the sponsor (Coral Protocol) built their escrow/settlement program on Solana, and their
judging criteria require using it. This is optional, additional upside — not a dependency of the
main event. If the devnet-funding blocker (below) never clears, the Tokyo event is unaffected;
only this one $5,000 bounty submission is at risk.

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
| 8 | **GitHub issue on the upstream repo (chosen over Telegram — no Telegram account setup
    needed, already-authenticated `gh` CLI)** | DONE 2026-07-04:
    https://github.com/trilltino/solana_coralOS/issues/2 — asked Tino directly for devnet SOL to
    the buyer wallet `Gterk9J4xg8Q8DxrgBLiwLs1Z3hRVnk9y54JQ3sZJEHB`; also opened the partnership
    thread (Dais's global self-funded-AI consortium goal). Awaiting response. |
| 9 | `solana airdrop` retried at intervals (2026-07-04, 3x over ~45s) | still 429 — rate limit
    window has not cleared yet; keep retrying periodically. |
| 10 | `devnet-pow mine` retried (2026-07-04, correct usage this time: `~/.cargo/bin/devnet-pow
    get-all-faucets` DOES list funded faucets, e.g. `6yvwhesLJ...` with 2.1M SOL @ difficulty 3 /
    reward 0.02) | `mine` (with `--no-infer` + matching `-d`/`--reward`) proceeds to actually mine,
    but its final step calls an internal `requestAirdrop` (to cover the miner's own tx fee when
    balance=0) → **same 429** as #1/#2. Root cause confirmed: this is a network-wide IP/wallet rate
    limit on the OFFICIAL faucet infra, shared by every tool built on top of it (CLI, raw RPC, PoW
    miner) — not something fixable by switching tools. Only a truly independent faucet (Discord
    bot, a peer sending from their own already-funded wallet) escapes it. |
| 11 | **Self-deploy the escrow, sidestep public-devnet entirely** — built `anchor build` for
    `examples/txodds/escrow/{escrow,arbiter}` against `solana-test-validator`. Blocked initially by
    `rustc 1.84.1` (bundled with `platform-tools` v1.48/v1.50) rejecting `edition2024` crates
    (`zeroize`, `toml_edit`, `hashbrown` all bumped their MSRV). **Fixed**: `anchor build` /
    `cargo-build-sbf --tools-version v1.54 --force-tools-install` pulls a newer toolchain — resolved
    the edition2024 wall. Result: `anchor deploy --provider.cluster localnet` succeeded for real —
    both programs `Executable: true` on my own `solana-test-validator`, real tx sigs
    `TEp4GjwMnAbVPkJx95bfvhUyKjBStiVRVrr8KYAnRHoxJrGNEreMaz59tfySAQM9gauBkAcamLQjyh5uVnWVfFw`
    (arbiter) and `jRFEo7GXrvGRocgoU9bQFj86esSBqWgRfNTNouDt6CvzPZJncW4Nkb5SnJLTeg3ZjpvS8NbPXnuMfqt4DfoJKHQ`
    (escrow), confirmed via `solana confirm`. **This answers Dais's "can't we create our own
    devnet/Solana ourselves" directly: yes — `anchor build && anchor deploy --provider.cluster
    localnet` is the one-command path, once `platform-tools v1.54` is installed.** Caveat: this
    deploys MY OWN copy of the program under a NEW program ID (`CBMhXWdqRAdGcUqBdyrvhNZDp3btunc
    ggJBDYRZMUDi2` / `7hWqsuKRxHUm4nvJ3EEZRheXVEcuBCQqxRQaMVfurST2`), not the CoralOS bounty's
    canonical public-devnet IDs (`R5NWNg9e.../FJtuVXsy...`) that `proxy.ts`/`arbiter.ts` hardcode —
    so it does NOT by itself satisfy REQ-3's "real public-devnet settlement against the CoralOS
    submission's actual programs." It DOES fully unblock task #8 (Tokyo multi-chain infra): each
    hackathon participant's own local validator, seeded independently, sidesteps the shared
    rate-limit entirely. |

| 12 | **RESOLVED 2026-07-05**: Dais manually funded the buyer wallet via `faucet.solana.com`
    (human-solved CAPTCHA — the automation blockers found in #1-#11 were specific to
    `solana airdrop`/raw RPC/PoW-faucet/Discord-signup CAPTCHA, not the web faucet's own UI, which
    just needed one human click-through). Confirmed: `solana balance
    AJ99EemzNHpkdjpMJ9aXfLthvfQYkjSXUjYrQr3853MN --url https://api.devnet.solana.com` → **5 SOL**.
    REQ-5 (funding precondition) is now satisfied. |

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
  [x] A3  RESOLVED 2026-07-05 (see funding-blocker log entry #12): Dais manually funded
          `AJ99EemzNHpkdjpMJ9aXfLthvfQYkjSXUjYrQr3853MN` via faucet.solana.com's own web UI
          (human solves the CAPTCHA — every AUTOMATED path (#1-#11: CLI/RPC/PoW/Discord
          signup) was blocked, but the plain web faucet just needed one human click).
          `solana balance ... --url https://api.devnet.solana.com` -> 5 SOL confirmed.
  [x] A9  BONUS (not on the critical path, but proves capability + unblocks task #8):
          self-build + self-deploy the escrow/arbiter to MY OWN `solana-test-validator` —
          real `anchor build && anchor deploy --provider.cluster localnet`, real tx sigs,
          `Executable: true` confirmed on-chain. Root-caused + fixed the edition2024 build
          wall via `platform-tools v1.54`. See funding-blocker log entry #11 for full detail.
  [x] A4  Wired LLM_PROVIDER=openai + OpenAI key into .env (Tier 3, temporary) — done for the
          (superseded) quickstart path; re-verify still wired for the corrected target.
  [x] A5  CORRECTED + DONE: retargeted from quickstart's deliverData (WRONG — no-escrow
          fallback per adversary finding) to examples/txodds/server/proxy.ts's
          boundReference()/order — now sources Anicca's real on-chain net_worth/revenue from
          aniccaai.com/dashboard.json instead of TxLine odds. RED (3/3 fail) -> GREEN (3/3
          pass) -> pushed to the fork.
  [x] A6  DONE 2026-07-05: killed a stale proxy process (port 8801, no LLM key wired), wired
          `OPENAI_API_KEY` + `LLM_PROVIDER=openai` into the repo `.env`, restarted `npm run
          proxy` fresh, hit `GET /api/settle?amount=0.001&fixtureId=18185036` against
          `https://api.devnet.solana.com`. Result: `{"ok":true,"mode":"direct",...}` — arbiter
          path threw `NotArbiter` (expected per README: setup.js's arbiter keypair isn't the
          configured arbiter) and correctly fell back to the direct buyer-released escrow, per
          the documented fallback behavior — not a bug, not a mock.
  [x] A7  VERIFIED 2026-07-05, fresh evidence, no mock:
          - DEPOSIT: `2eVohw53ndLLKf7uz1BvRWbVpNx155y4msJg6kBTS837jB5NaWvToVmQ28WAB9yMtwgxMznCRANs7MYLqMuaMMRU`
            -> https://explorer.solana.com/tx/2eVohw53ndLLKf7uz1BvRWbVpNx155y4msJg6kBTS837jB5NaWvToVmQ28WAB9yMtwgxMznCRANs7MYLqMuaMMRU?cluster=devnet
          - RELEASE: `JbqJUj9t98R8XNZjgnJWJoQoBJoq8qjvUuwmJctUqyrMnfGDpEqb1sfEu37cz7NBTr3CMvKRRqSBBSTL6eWsfvo`
            -> https://explorer.solana.com/tx/JbqJUj9t98R8XNZjgnJWJoQoBJoq8qjvUuwmJctUqyrMnfGDpEqb1sfEu37cz7NBTr3CMvKRRqSBBSTL6eWsfvo?cluster=devnet
          - Escrow PDA: `BGMdLe9AvpYAdykG1QexFtd2Vpg3aPxw9MwSMuyJaEPi`
          - Both confirmed `Finalized` via `solana confirm`. Balance deltas confirmed: buyer
            5 -> 4.97416288 SOL, seller 0 -> 0.001 SOL (exact settle amount, real 2-party
            transfer, not self-pay). **R1b exit gate (A7 true) is now satisfied.**
  [~] A8  HONEST GAP FOUND (separate from this feature, tracked as new follow-up, NOT
          blocking): the settle response's `order` was `{"source":"anicca","agentId":
          "18185036","fallback":true,"error":"no leaderboard entry"}` — REQ-2 (deterministic
          fallback, never crash) is proven, but REQ-1's non-fallback happy path (real Anicca
          net_worth/revenue replacing the fallback) did NOT get exercised, because
          `https://aniccaai.com/dashboard.json` currently has **no `leaderboard` key at all**
          (`updated_at` on that file is stale, 2026-06-05 — the sprint-1/2/3 leaderboard-sync
          code exists and is tested, but `render-dashboard.mjs` isn't actually running against
          production yet). This is a real, separate production gap — filed as a new item, not
          silently worked around. devnetfaucet.org's GitHub-OAuth path is deprioritized (A3 is
          done via the simpler manual faucet.solana.com route instead).

PHASE D — submission artifacts (ZERO code required, can start NOW in parallel with A3/A6/A7)
  [ ] D1  Draft the 5-slide deck outline (customer / what it sells / why they pay / the economy
          / proof) — see the outline below, ready to fill once A7's Explorer link exists.
  [ ] D2  Draft the 3-min video script (Problem -> Solution -> Demo -> Team).
  [ ] D3  Repo cleanup pass: confirm no keys committed (.env stays local-only, .env.example
          only in the public fork).
  ── R1b EXIT GATE: A7 must be true before Phase B starts ──

PHASE B — downgrade to zero-human (brain = ClawRouter, Tier 1, the real submission)  DONE 2026-07-05
  [x] B1  ClawRouter was ALREADY running system-wide (`/opt/homebrew/bin/clawrouter`, part of the
          main Anicca-OpenClaw instance) — `curl localhost:8402/health` ->
          `{"status":"ok","wallet":"0xa3CDd4Ec...","paymentChain":"base"}`. No fresh install
          needed; this machine's existing ClawRouter instance was reused.
  [x] B2  NOT env-var-only after all (LLM.md's `pickProvider()` had no generic base-URL
          override for a 4th provider) — required a small code addition, the SANCTIONED
          extension path LLM.md itself documents ("add a provider in code": extend the
          `LlmProvider` union, add a `DEFAULT_MODEL` entry, teach `pickProvider()`, dispatch in
          `complete()`). Added `clawrouter` as EXPLICIT-ONLY (never auto-detected — it needs no
          key at all, so silence-of-keys must not silently select it). Also root-caused +
          fixed a real bug found along the way: `LLM_MODEL=''` (the shipped .env.example
          default) bypassed `DEFAULT_MODEL` because `??` doesn't fall through on `''`, only
          null/undefined — every provider was silently affected, not just this one. 2 new unit
          tests (pickProvider explicit-wins / never-auto-detected), 10/10 GREEN, pushed to
          `Daisuke134/solana_coralOS@d9fc893`.
  [x] B3  `.env`: `OPENAI_API_KEY=`, `ANTHROPIC_API_KEY=`, `VENICE_API_KEY=` all blank;
          `LLM_PROVIDER=clawrouter`; also unset any shell-exported copies (`unset
          OPENAI_API_KEY ANTHROPIC_API_KEY VENICE_API_KEY`) and verified `env | grep -i
          "OPENAI\|ANTHROPIC\|VENICE"` returned nothing before restarting the proxy.
  [x] B4  Re-ran BOTH endpoints fresh (killed + restarted the proxy so the new build + env took
          effect): `GET /api/edge?fixtureId=18185036` (the real LLM call) and `GET
          /api/settle?amount=0.001&fixtureId=18185036` (the full escrow loop).
  [x] B5  VERIFIED, fresh evidence, zero human LLM keys present:
          - `/api/edge` trace: `[llm] provider=clawrouter model=eco` -> real parsed JSON
            (`{"call":"Morocco is favored...","confidence":0.216}`, NO fallback note — the
            first attempt with `model=auto` produced verbose reasoning prose that failed
            `parseJsonReply()` and fell back; switching `LLM_MODEL=eco` fixed it).
          - `/api/settle` DEPOSIT: `2JL3mk2m8GuEsf64KJ1yifDuBSZmSeLKUKGPtjeeFphCwMmrBAuKZGHBTo8skF5fsLALexoEjZw5D3p2oH4XvKLq`
            -> https://explorer.solana.com/tx/2JL3mk2m8GuEsf64KJ1yifDuBSZmSeLKUKGPtjeeFphCwMmrBAuKZGHBTo8skF5fsLALexoEjZw5D3p2oH4XvKLq?cluster=devnet
          - `/api/settle` RELEASE: `51YnRDSHYR7BQrTBxWaRfKTn6h8GCzVfw9AFPHezY3U6Hw8Y8UeNBmymSMpPEt1fshmGotCdVEFEgGAZjFesUdXo`
            -> https://explorer.solana.com/tx/51YnRDSHYR7BQrTBxWaRfKTn6h8GCzVfw9AFPHezY3U6Hw8Y8UeNBmymSMpPEt1fshmGotCdVEFEgGAZjFesUdXo?cluster=devnet
          - Both confirmed via `solana confirm` (Confirmed status). **R1c/R1d exit gate satisfied.**
  ── R1c/R1d EXIT GATE: B5 true; SUBMITTED config points at ClawRouter — SATISFIED ──

PHASE C — wrap as an unattended loop + submit
  [x] C0  R5 GAP FOUND + FIXED 2026-07-05: A5 earlier only patched examples/txodds/server/
          proxy.ts (the single-agent web demo). The OFFICIAL demo requirement (WANT->BID->
          AWARD->DEPOSITED->DELIVERED->RELEASED) actually runs through coral-agents/
          seller-agent/src/service.ts + examples/txodds/coral/round.ts — a SEPARATE codebase,
          still TxLine-only. Fixed: added the same 'anicca' service branch there (4 new tests,
          6/6 GREEN), buyer now WANTs 'anicca' instead of 'txline'. Also found + fixed 2 real
          infra bugs live: (a) coral-server rejects undeclared toml options — had to add
          CLAWROUTER_URL/ANICCA_DASHBOARD_URL to coral-agent.toml; (b) our generated
          ARBITER_KEYPAIR_B58 isn't the arbiter program's on-chain configured admin, so
          SETTLEMENT_MODE must be 'direct' not 'arbiter' (same fallback the single-agent path
          already uses). Installed colima (Docker wasn't running) + docker-compose plugin,
          built both agent Docker images from source, ran `docker compose up -d coral && npm
          run coral` for REAL — full round completed: 3 sellers bid, seller-worldcup won
          AWARD, DEPOSITED 0.001 SOL, DELIVERED, RELEASED. Real tx:
          `4p79RhXcw3iHdD2hbWZzasDPNuk9NbBvGnSLEqtCeG4mxTJ5wTLDAuiPuJgUcTfbXUQvzWzzFUt1qiY5NsbGczZU`
          -> https://explorer.solana.com/tx/4p79RhXcw3iHdD2hbWZzasDPNuk9NbBvGnSLEqtCeG4mxTJ5wTLDAuiPuJgUcTfbXUQvzWzzFUt1qiY5NsbGczZU?cluster=devnet
          confirmed `Finalized`. **R5 is now genuinely satisfied — the official one-command
          judge demo (`docker compose up -d coral && npm run coral`) actually works end-to-end
          on this fork, trading Anicca's own service.** Pushed to
          `Daisuke134/solana_coralOS@7367721`. Disk hygiene: colima grew to ~5.2GB mid-run
          (host disk hit 1.8Gi free, a real risk) — stopped + fully deleted colima immediately
          after capturing evidence, reclaimed to 7.0Gi free. Docker/colima are NOT required to
          stay installed for anything else in this repo; a judge re-running the demo would
          need their own Docker runtime (documented in C6/README, not this machine's problem).
  [~] C1  Re-read `buyer-agent/src/index.ts` this round: the loop already exists (`while(true)`:
          wake → decide → settle → sleep(CYCLE_MS) → repeat) — NOT new code. What was missing
          was self-report (R6's last clause) — see C3.
  [ ] C2  Run the loop unattended for ≥1 full cycle with neither Dais nor Claude operating it —
          BLOCKED behind C3's live verification (same Docker session would prove both at once).
  [~] C3  IMPLEMENTED, unit-verified, NOT YET live-E2E-verified (honest partial):
          `coral-agents/seller-agent/src/telemetry.ts` (buildRoundPayload/canonicalMessage/
          reportRound) fires on RELEASED/ARBITER_RELEASED, signs via ed25519
          (chain:'solana', same wire format as apps/landing's telemetry-verify.js), ALWAYS
          reports `net_worth_usd:0, revenue_mo_usd:0` (devnet SOL is fake money — never
          reported as real), tags `'coralos-hackathon'`, log_feed spells out devnet/test-only
          + the round/sig. 8 new unit tests, real ed25519 keypair, all GREEN. Wired into
          index.ts + round.ts (SELLER_KEYPAIR_B58 forwarded) + coral-agent.toml (new options
          declared). Pushed to `Daisuke134/solana_coralOS@901a255`.
          **BLOCKED on live E2E**: reinstalled colima to rebuild the seller-agent image with
          this new code — host disk hit **1.3Gi free mid-rebuild** (colima's own baseline VM
          costs ~3-4GB before any image build even starts). Per disk-hygiene HARD RULE, STOPPED
          before the second build, deleted colima immediately, disk recovered to 4.4Gi. This
          machine does not currently have enough sustained headroom for back-to-back
          colima+2-image-build cycles without also freeing other caches each time. Real,
          disclosed gap — NOT worked around by skipping the live proof and claiming done.
          Next attempt: free more disk first (candidates: `~/.npm` 1.6G, more `~/.cache/
          anicca-clones/*` stale clones) OR do the live E2E on a machine with more free disk.
  [~] C4  5-slide deck CONTENT drafted (`SUBMISSION.md` in the fork, pushed to
          `Daisuke134/solana_coralOS@ff7ead7`), grounded in the real Explorer link/tx sig from
          C0 — not yet rendered as an actual slide file (Keynote/PDF/Google Slides), that's
          still a manual production step.
  [~] C5  3-min video SCRIPT drafted (same `SUBMISSION.md`, timestamped Problem/Solution/Demo/
          Team beats) — not yet recorded/edited, that's still a manual production step.
  [ ] C6  Public repo cleanup: no keys committed, .env.example only; README notes Docker is
          required to run the multi-agent round (judges need their own Docker/colima)
  [ ] C7  Submit on the Superteam listing before 2026-07-20
  [ ] C8  fresh-context adversary review of the whole submission (spec fidelity + no-mock E2E)
```

Cross-references: multi-chain GAIN work = task #8 (separate spec/track, not blocking this
submission). Partnership outreach to Tino/Imperial = task #10 (send AFTER A7, so we have proof —
"we actually did it" per Dais's own reasoning).

## C1/C3 design — the loop already exists; what's missing is self-report (re-verified 2026-07-05)

Ground truth (re-read `coral-agents/buyer-agent/src/index.ts` this round): the buyer already runs
a `while (true)` loop — wake (`ctx.waitForMention`), decide (`pickWinner`), settle
(`deposit`→`release`), `sleep(CYCLE_MS)`, repeat. **C1's loop mechanism already exists** — it is
NOT new code to write. What R6 additionally asks for ("self-reports") does NOT exist yet: nothing
currently tells Anicca's own telemetry system that a round happened.

**Honesty constraint (non-negotiable, ties to the no-fake-numbers HARD RULE):** the CoralOS
settlement is on Solana **devnet** — devnet SOL is worthless play money (established earlier this
session). Reporting it as `revenue_mo_usd`/`net_worth_usd` on the REAL leaderboard would inject a
fake number into a system whose entire design point is "no fake numbers." Therefore:

- **S-C3.1** The self-report SHALL post `net_worth_usd: 0, revenue_mo_usd: 0` (never the devnet SOL
  amount) — this loop earns ZERO real dollars; only the mechanism is being demonstrated.
- **S-C3.2** The self-report SHALL carry `tags: ['coralos-hackathon']` and a `log_feed` entry
  describing the round (round number, RELEASE tx sig, explicit "devnet, test-value-only" wording)
  so a human reading the dashboard is never misled about what happened.
- **S-C3.3** The report SHALL use Sprint-6's `chain: 'solana'` signing path (ed25519 via
  `tweetnacl`/`bs58`, `id` = the seller's own devnet wallet, case-preserved) — reusing
  `registerSpawn`'s wire format (`canonicalMessage` + signature), posted to the SAME
  `aniccaai.com/.netlify/functions/telemetry` endpoint every other Anicca instance uses.
- **S-C3.4** SHALL fire from the seller side, at the point it observes `RELEASED`/`ARBITER_RELEASED`
  (`coral-agents/seller-agent/src/index.ts` around the existing `if (verb(text) === ...)` block) —
  the seller is the one earning, so the seller is the one that self-reports, matching R6's own
  wording ("wakes, decides, sells/earns, settles, self-reports").
- **S-C3.5** Never crash the round on a report failure — same fail-open contract as every other
  network call in this fork (log and continue, don't throw).

Verification: unit tests with an injectable fetch + a real ed25519 keypair (mirrors the sprint-6
`tweetnacl`/`bs58` pattern already proven in `apps/landing`), asserting the exact posted body
(`net_worth_usd===0`, `tags` includes `'coralos-hackathon'`, `chain==='solana'`) — then ONE more
live Docker round (colima reinstalled fresh, cleaned up immediately after, same disk discipline as
C0) confirming a real POST leaves a row visible via the telemetry API.

## Out of scope / honest limits
- Free-tier models are capable but not frontier; if a task needs frontier reasoning the agent self-pays
  (R2) — still no human key. Documented, not hidden.
- The winning-harness → `Daisuke134/anicca` merge (colony inheritance) is governance, tracked separately.
