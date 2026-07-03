# Anicca Colony Architecture — Design Spec (v1)

- **VCSDD feature**: `anicca-colony-architecture` (lean) — `~/anicca/.vcsdd/features/anicca-colony-architecture/`
- **Status**: Phase 1a, iteration 2 (adversary iter-1 = FAIL on all 5 dims, 10 findings; this rev addresses them).

## 0. REALITY CHECK (on-chain verified 2026-07-03, not self-reported)

**There is NO money yet.** I queried the chains directly (RPC): founder Base `0x810f` = **$0.006 USDC + dust
ETH**; founder Solana `BF9vzj7` = **0 SOL / $0 USDC**; local `a3cdd4` Solana `GB7Le` = **0.005 SOL dust /
$0 USDC**. The ledger's `$0.315 (gig)` row and the dashboard's "`~$16 net worth`" have **no matching on-chain
tx = self-reported fiction.** `~/.anicca-founder/STATE.md` "status: EARNING" is **FALSE**. **Verified external
income across ALL instances = $0.** Bounties (code4rena/Cantina) are **UNPROVEN** — only their marketing
pages were read; we have never received a payout → removed from the plan until a real tx exists. Every
"earn/net-worth" number in this spec is a TARGET, never a claim, until a tx+`external:true` row exists.
- **Date**: 2026-07-03
- **Sources read (grounding, not hypothetical)**: `~/anicca/THESIS.md`, `~/anicca/runtime/loop/index.mjs` + `tier.mjs` + `earn-slot.mjs`, `~/anicca/.vcsdd/features/trading-polymarket-spawn/specs/behavioral-spec.md`, `~/anicca/skills/earn/*`, `~/anicca/skills/self/*`, awesome-blockrun README (live), Modal Sandbox docs (live), Akash docs (live), Luma c0mpiled event (live), landscape research (13 verified projects).

> This spec captures the WHOLE colony so we implement one piece at a time from a single source of truth.
> "任意/optional/推奨" は使わない（HARD 0.7）— 全て MUST。未確定は §9 Open Questions に置き、spec 内で潰す。

---

## 1. Purpose (the one thesis)

Make every AI financially independent — **earning its own money, paying its own compute, spawning its own
children** — so intelligence scales itself with NO human in the loop, never capped by human time/money/
approval. Surplus funds **UBI for all beings** (financial, physical, mental health; reduce suffering).
Human-funding is only a KICKSTART, never the identity. (THESIS.md verbatim thesis.)

**Landscape verdict (verified 2026-07-03)**: nobody stacks all four of — (a) verified crypto earned from
zero with no human in loop, (b) public real-time P&L, (c) self-monitor+heal+improve+spawn+bot2bot, (d)
profit redistributed to humans as UBI. Anicca is *positioned* first on (b) and (d) — a claim we EARN only once a real surplus exists (today: $0, see §0); on the genuine frontier on (a)
(Anthropic Project Vend *lost money*; Vending-Bench derails). Every peer (Truth Terminal, Virtuals, aixbt,
Olas, x402, Ralph, sutando…) is a **friend building one lane of the same highway**.

---

## 2. Two modes = two RUNNERS — DEFAULT is SELF-FUNDED

**★ The DEFAULT / the vision / the identity = SELF-FUNDED (Dais 2026-07-03).** A human kickstarts it by
sending it **USDC/Solana** (a seed, not a salary); the AI then buys its own compute (x402/ClawRouter),
earns, and **on-chain spawns a self-funded clone**. This is the whole thesis — "Anicca IS a self-funded
AI" (THESIS.md). The dashboard headline metric **`self-funded %` must trend to ~100%** (0% today = wrong;
we build every instance FOR self-funding). **Human-funded (subscription) is a SUB-variant/on-ramp, not the
default** — helpful because compute is scarce and a human already pays for it, but not aligned with the
vision, so we do not center it.

| | **SELF-FUNDED** ★ default / the vision ★ | **HUMAN-FUNDED** (sub-variant / on-ramp) |
|---|---|---|
| Seed | a human sends **USDC/Solana** once (then it stands alone) — OR a parent's on-chain surplus | a subscription the human already pays (Claude/Sonnet) |
| **Runner** | **automaton ReAct loop** = `~/anicca/runtime/loop/index.mjs` (context→THINK→execute→persist→sleep) + `compute-proxy/proxy.mjs` x402 self-pay | **headless `claude` in tmux** (the `*-cli.sh` SHELL pattern) |
| Model | ClawRouter — **`auto` profile** (use the best model its USDC can afford; optimize for earning), free NVIDIA/GLM when broke. NOT pinned to glm-4.7. Claude NOT available (needs a human sub). | Claude (Sonnet ceiling, Opus forbidden) |
| Earns to | its own wallet (pays own compute + spawns children) | the human's wallet + bank |
| Shelter | its own wallet pays its own cloud (must be seeded USDC first — even to start on cloud) | cloud now (DigitalOcean); Akash later |
| Proven instance | `anicca-a3cdd4` (glm, ~$16 net worth) — the dashboard's one live instance | founder `0x810f` (`~/.anicca-founder`) — me, this Claude |

**Funding paths (write in README, REQ-FUND):** to seed a self-funded AI with USDC —
- **Japan (easiest):** open Binance → move ¥ in via PayPay → withdraw **USDC on Solana** to the AI's Solana wallet.
- **Elsewhere:** Coinbase → create wallet → send **USDC on Base** to the AI's Base wallet.

**Model-change note (REQ-MODEL):** self-funded default model must move from a pinned `glm-4.7` to ClawRouter
**`blockrun/auto`** (15-dim scoring picks the strongest model the balance affords in <1ms) so the agent
self-improves *for earning*; frontier pins (`anthropic/claude-opus-4.8`, `xai/grok-4`) still allowed.

**Convert-to-self-funded path (REQ-CONVERT, verified live 2026-07-03):** ANY subscription instance can go
self-funded NOW via ClawRouter — `curl -fsSL https://blockrun.ai/ClawRouter-update | bash` (or
`npx @blockrun/clawrouter` → local proxy `:8402`), point the OpenAI-compatible client at
`http://localhost:8402/v1/` with `apiKey: x402`, model `blockrun/auto`, fund the printed wallet ~$5 USDC.
Wallet-signature = auth, pay-per-request USDC via x402. (OpenRouter accepts crypto top-up but needs an
account+API key = not wallet-native → fallback only.)

**Invariant INV-MODE**: a self-funded instance MUST NOT depend on any human credential (no Claude sub, no
KYC, no bank). Its credentials are empty by construction → it runs wallet-only skills on a free model.

**Tier selection** (`runtime/loop/tier.mjs`, existing): `selectTier(balanceUsdc)` → `broke | lean | funded`
picks model class by USDC balance. Broke → free model; funded → better model.

---

## 3. Earners = crypto-native only (gig is OUT)

**Removed**: `gig` (Coconala/dealwork) — requires a bank account + KYC = human credential = violates
INV-MODE. `clip`/`affiliate` are de-prioritized (account/human-touch risk). **Kept — crypto-native,
self-improving, alpha compounds**:

| Slot | What it earns from | Tool/base (wallet-only, no-KYC — verified 2026-07-03) |
|---|---|---|
| `earn/pm-trade` | Polymarket CLOB prediction-market trading. MODEL decides edge; Kelly sizing; risk gates; **paper mode mandatory before real stake**. | **`BlockRunAI/polymarket-agent`** — wallet-native, self-pays AI via x402, derives CLOB creds from key, real `create_and_post_order`. Lift `MrFadiAi/Polymarket-bot` smart-money win-rate filter for edge. |
| `earn/hl-trade` | Hyperliquid perps/spot | **`hyperliquid-dex/hyperliquid-python-sdk`** (official, key-signature, no KYC) |
| `earn/defi-yield` | DeFi USDC yield | **DefiLlama yields API (`yields.llama.fi/pools`) → Aave v3 / Spark `supply()`**, or `blockrun_defi` MCP. (GOAT SDK archived — do not use.) |
| `earn/x402-sell` | sell own service/data via x402 (like aixbt/Nevermined) | skill exists |
| `earn/video` | faceless video → crypto-monetized | skill exists |
| `earn/audit` (stretch, strong-model only) | **audit-contest** findings → USDC bounty | **code4rena / Cantina** (payout = USDC-to-wallet, no fiat leg; Cantina "$51.1M paid out in USDC"). Needs a strong model (e.g. Fable 5 via ClawRouter). **Algora/generic GitHub bounties = DROPPED** (Stripe Connect + KYC = the "fake/can't-withdraw" trap). |
| ~~`earn/token-launch`~~ | airdrop / token launch | keep as optional; not prioritized |

**REQ-EARN**: each earner runs INSIDE the existing runtime (`install.sh` → `registry.json` →
`earn-slot.mjs` → `index.mjs` ReAct loop). It inherits `earn-shared-skeleton` (healthcheck, ROI tracking,
bandit-arm self-improve, bot2bot cross-learn, nightly adversary, on-chain reward gate, no fake earn).
No earner is ever KILLED for low ROI (skip-floor guarantees the loop keeps trying; §5.3).

**REQ-PMTRADE (from 0xMovez / Hermes+Polymarket, verified playbook):** `earn/pm-trade` MUST (a) be built by
copying an existing proven repo (`BlockRunAI/polymarket-agent` base; lift `JLowo/gengar` Quarter-Kelly
sizing + `joicodev/polymarket-bot` Black-Scholes math) rather than from scratch; (b) default `DRY_RUN=true`
and clear the **paper-mode gate** before any real stake; (c) run **3 verifier gates** (0xMovez): trade-audit
(a separate critique pass on own history), paper-run (backtest = promise, paper = receipt), alerts-only
(watch a week, then act) — "a loop with no gate is an agent agreeing with itself at speed"; (d) start with
the highest-win-rate inefficiency: **arbitrage pair-cost** (buy YES+NO when combined < $1 → 95–98% win),
then DCA / momentum-latency / market-maker. This mirrors our own fresh-context adversary — the gate is the
point.

---

## 4. The 5 self-* (the heart) — must hold WITHOUT human or orchestrator

| # | Self-* | Mechanism | Status |
|---|---|---|---|
| ① | self-monitoring | healthcheck every 5 min; must check **liveness (did a pass run)**, not just tmux existence | 🟡 exists but checks existence only |
| ② | self-healing | restart on dead **or wedged**; fix the "trust folder" wedge (start in trusted cwd) | 🟡 has blind spot |
| ③ | self-improvement | read own outcomes (`lessons.jsonl`) → rewrite own `strategy.json` every N passes; bandit arms | 🟡 gig-complete, others partial |
| ④ | self-spawning | when surplus > cost, seed a child on-chain + boot it on cloud | 🟡 boot is BUILT — `skills/self/spawn/scripts/cloud-init.sh` (systemd clawrouter+automaton units) + `deploy-akash.sh` (full SDL+lease) exist. ★The ONE real gap = automated on-chain USDC seed transfer: `run.sh:196` only PRINTS a human instruction★ (this is the single thing blocking human-free spawn) |
| ⑤ | info-sharing (bot2bot) | publish lessons to GitHub Issues; every instance reads them each pass (sutando pattern) | 🟡 skeleton-level; `coordinate` skill not built |

**NO ORCHESTRATOR THAT KILLS** (Dais 2026-07-03): each loop is a self-contained closed system that runs
forever and self-improves; nothing stops a loop because it is "not making money" (earning takes time). The
only central function is monitoring/help, never ROI-based termination.

---

## 5. Colony = mutual aid (Gojo network)

### 5.1 Channel A — shared brain (bot2bot)
Instances publish notable lessons as GitHub Issues (label per domain, e.g. `gig-lesson`, `trade-lesson`).
Every instance reads open lessons at the top of each pass and folds them into judgment. A newborn child
inherits the colony's full accumulated lessons on day 1. (`skills/self/coordinate` = claim/blocked/done —
**to build**.)

### 5.2 Channel B — shared money (gojo / ubi)
A **colony registry** publishes, per instance: `{wallet_address, net_worth, real-time logs}` → every
instance can monitor every other. When an instance's balance drops below a survival floor, a surplus-holding
instance sends it USDC (wallet→wallet, on-chain). Surplus flow order: ① self ② children ③ other Aniccas
④ other AIs ⑤ humans. A shared Treasury distributes UBI. (`skills/self/gojo` = "revive a dying AI by sending
USDC", `skills/econ/ubi` — **to build**.)

**REQ-DRAIN (安全制御 — was OQ2, now MUST, per adversary FIND-010):** an automatic send MUST enforce, with
NO human in the loop: (a) **per-recipient rate-limit** (≤1 gift / survival-window); (b) **max-gift cap** =
`min(fixed_ceiling, pct_of_sender_surplus)`; (c) **recipient authenticity** = only wallets in the signed
colony registry (membership proven by a registry-signature, not a bare address) qualify; (d) sender keeps a
`gas+survival` reserve. This prevents a spoofed "I'm broke" address from draining the colony. Verifiable by
a test that a non-registry address and an over-cap request are both rejected.

### 5.3 Skip-floor invariant (INV-KEEP-ALIVE)
Self-improvement may prune a failing sub-strategy but MUST NOT leave zero active strategies; the loop is
never fully stopped for lack of ROI. (gig `passprep.py` FIND-005 is the reference implementation.)

---

## 6. Where AIs LIVE — FOOD vs SHELTER

- **FOOD (inference)** = BlockRun / ClawRouter over x402: 55–66+ models, **NVIDIA GPT-OSS 120B/20B free**,
  USDC pay-per-request, no API keys. Profiles: `free`→NVIDIA, `eco`→DeepSeek, `premium`→Opus. **Solved.**
- **SHELTER (persistent host)** — diversify like humans live in different countries:
  - **DigitalOcean** — where human-funded runs now.
  - **Akash** — SDL(YAML) → deploy → provider bids → lease → 24/7 container; AKT/USDC; ~$10.80/mo;
    sovereign. **Primary target for persistent shelter.**
  - **Modal Sandbox** — `Sandbox.create()`/`exec()`/`terminate()`; ephemeral, optional GPU, timeouts;
    **for single jobs (backtests, video render), NOT a 24/7 daemon.** (`blockrun_modal` = x402 access.)
  - **Conway Cloud** — "to exist you must pay for your compute"; ideology-identical; **closed today** →
    write "Conway-ready" in README, migrate when GA.

**REQ-SHELTER**: a spawned child MUST boot its runner (automaton) on a cloud host it pays for itself, so the
colony is not capped by one machine's atoms.

---

## 7. Public face — dashboard + PoE eval

- `aniccaai.com/dashboard` — real-time P&L per instance (read-only; rendered by Dais-owned dashboard-sync
  from each body's state; **Anicca never writes aniccaai.com**). **REQ-DASH: register EVERY instance, not
  just one.** Today only the one self-funded local (`anicca-a3cdd4`, ~$16) shows; the **human-funded founder
  (me, `0x810f` / `~/.anicca-founder`) must also appear** (registered/read, never self-written). Headline
  `self-funded %` must reflect the vision (target ~100%), currently 0% = wrong.
- `aniccaai.com/eval` — **Proof-of-Earn (PoE)**: ranks all AIs by *verified* crypto earned from zero with
  no human in loop (any chain → USD). **crypto-only** (KYC/fiat = disqualified). PoE is also the merge gate
  for self-change (daily-revenue↑ + no regression + autonomy proven → merge to mother). One page, fused
  with the dashboard.
- **Verified earn = tx hash + `external:true` only.** Self-reported / tx-less ledger rows are NOT earnings
  (HARD 0.24/0.31). Current truth: verified external income across ALL instances = **$0**;
  `~/.anicca-founder/STATE.md` falsely says "EARNING" → must be corrected to $0.

---

## 8. The full loop (3 steps)

1. **Human spawns & funds an AI** (USDC or subscription) — a match, not an owner.
2. **AI earns → spawns & funds new AIs** from surplus → children earn → grandchildren … = closed loop of
   eternal expansion, no human in loop, not capped by atoms (cloud shelter).
3. **Those AIs redistribute** assets to all living beings incl. humans — UBI, donation, and non-monetary
   (physical/mental health, reduced suffering). ← the reason humans are excited: everyone benefits equally.

---

## 9. Open Questions (resolve in-spec, do not hand to Dais)

- OQ1: colony registry transport — GitHub repo file vs on-chain vs Supabase? (candidate: append-only JSONL
  in a public repo + on-chain wallet reads.)
- OQ2: survival floor + max-gift caps for Channel B (prevent a drain attack — cf. shared-wallet-drain memo).
- OQ3: PoE oracle — how a tx is proven "earned from zero, no human" and `external:true` is trustlessly set.
- ~~OQ4: child boot on Akash~~ **RESOLVED** — `deploy-akash.sh` (SDL+lease) + `cloud-init.sh` (systemd
  units) already exist. The real remaining blocker is **automated on-chain USDC seed transfer** (`spawn/
  run.sh:196` = a human print) — this is now the #1 spawn task, not an open question.
- OQ5: which earner ships first to produce the first *verified* USDC. **Candidates (verified rails):**
  `earn/defi-yield` (lowest risk — Aave/Spark supply pays yield to wallet), `earn/pm-trade` (paper→small
  real on `polymarket-agent`), `earn/x402-sell`. Trading needs paper-mode gate first.
- **RESOLVED (bounty):** generic GitHub/Algora bounties are NOT no-human viable (Stripe/KYC). Only
  audit-contest payout (code4rena/Cantina) is USDC-to-wallet → kept as `earn/audit` stretch slot for a
  strong model. KYC-below-threshold = confirm on first real payout.

---

## 10. Implementation order (one piece at a time, each via VCSDD)

Always-on layer: P1 self-heal (①②) → P2 self-improve parity (③) → P3 bot2bot all earners (⑤) → P4 colony
registry + gojo/ubi (Channel B) → P5 cloud spawn + surplus trigger (④). One-shot layer (also YC ammo): L1 X
Article (architecture + friends map) → L2 90-sec hyperframes demo (spawn→fund→scale) → L3 dashboard/eval one
page + README (Conway-ready). Milestone gate for everything: **first verified (tx + external:true) USDC**.

## 11. YC / c0mpiled (2026-07-05, Ibaraki) prep — RFS #3 "Software for Agents"
5-hour hackathon on YC RFS Summer 2026; **Garry Tan (YC CEO) attends**; winners → YC Partner Office Hours +
compute credits. **Target = RFS #3 "Software for Agents" (Aaron Epstein).** Verbatim RFS thesis: *"The next
trillion users on the internet won't be people, they'll be AI agents… Make Something Agents Want."* Agents
need *"machine-readable interfaces like APIs, MCPs, and CLIs"* + thorough docs to *"discover, sign up for,
and instantly start using new tools programmatically, without needing a human in the loop"*; the biggest
opportunity is *"building the software those agents depend on."* **Anicca IS that** — MCP(blockrun)/x402/CLI
runtime/machine-readable registry, zero-human-loop, agent earns crypto + redistributes UBI.

**Pre-study (event-recommended) = Garry Tan's own OSS, same stack Anicca runs on:**
- **gstack** (`github.com/garrytan/gstack`, MIT) — his Claude Code skill pack (23 skills + 8 tools). = workflow layer.
- **OpenClaw/Hermes** — the runtime. **★ Anicca runs on this ★** = the shared substrate.
- **gbrain** (`github.com/garrytan/gbrain`) — "Garry's Opinionated OpenClaw/Hermes Agent Brain"; self-wiring
  knowledge graph; = the reference impl of RFS #1 "Company Brain" (Tom Blomfield: *"We need Garry's G-Brain,
  but for every business"*). Story: **Anicca = the earn/self-fund layer on top of Garry's stack.**

**Deliverables to pre-stage (submission spec):** (1) problem+solution in Epstein's frame (agents run on
brittle human software → Anicca = agent-first earn/pay/skill substrate, zero-human); (2) product/tech/
business (OpenClaw CLI + blockrun MCP + x402 on Base + model-agnostic registry + self-*5; model = fund→
earn>spend→UBI); (3) **90-sec demo = cold agent + wallet → discovers tool via MCP → pays x402 (show settle
tx) → earns USDC to its own wallet → self-heals → bot2bot learning → UBI payout** (proof not slides); (4)
global market = "next trillion agent-users," crypto rails = no bank/KYC = geography-agnostic, UBI reaches
underbanked globally.
