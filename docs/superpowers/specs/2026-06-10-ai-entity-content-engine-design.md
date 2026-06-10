# AI-Entity Content Engine — Design Spec

- **Date**: 2026-06-10
- **Owner**: Daisuke (author/human-in-loop) + Claude Code (co-writer)
- **Status**: DRAFT (Phase 0 — planning, pending Dais review of structure)
- **Goal of the initiative**: Make Daisuke the most-known voice on the frontier of **AI entities — AI that earns money with no/minimal human in the loop**. Target: 10k followers + 10k MRR as a writer.
- **Cadence target**: 1 fine article + 1 TikTok image post per day. Quality > cadence (1 real piece / 1–2 days beats daily slop).

## 1. The Moat (why we are not AI slop)

Most AI articles only **explain/summarize** a tool — they never actually run it. We differentiate on three things, in order:

1. **Deepest search** — multi-source, primary-source, verified (Claude is strong here).
2. **We actually run it end-to-end** until we see real results (receipts: terminal output, wallet, what it earned, where it broke).
3. **Honest verdict** — we tell the reader, in sentence 1, *should you use it and who for*. No gatekeeping. "Absolutely try this" / "skip this" / "use it if you're X".

Unfakeable edge: Daisuke does not just review autonomous AIs — he **builds and runs** them (Anicca on OpenClaw + a live automaton on launchd). The report comes from inside.

## 2. Persona

### Reader
"AI-native but time-poor." Uses AI daily, watches AI X all day, drowns in new GitHub repos / services / "this is the best tool" threads, can't test them all. Wants a trusted scout who runs things and gives a straight verdict. One article serves two tiers via layered depth:
- Non-expert ("grandma" exaggeration): vision + verdict, no jargon walls.
- Expert/builder: deep technical + "should I install this in my Claude Code / OpenClaw".

### Writer (brand voice)
"The Scout who actually runs it." Sacrifices time to test the frontier end-to-end so you don't have to. Verdict in sentence 1. Deep + visual + honest + opinionated. Foregrounds: written by someone who actually runs a money-earning autonomous AI.

## 3. Topic queue (pillar → cluster)

| # | Topic | URL | Why / role |
|---|---|---|---|
| 1 (PILLAR) | **Automaton / Web 4.0** (Conway) | web4.ai, github.com/Conway-Research/automaton | Niche-defining concept; runnable (`git clone → run`); Dais has unfakeable receipts (runs one); best visuals. |
| 2 | **Felix** (AI-CEO) | felixcraft.ai | Concrete $29 product, $202k public dashboard, Nat Eliason co-author (distribution). Proves the test-and-report format on a buy decision. OpenClaw stack = Dais can verify deeply. |
| 3 | **ZHC / IZHC** | zhcinstitute.com | The institute/community studying Zero-Human Companies. Movement piece. |
| 4 | **Dynamic Workflows** | Claude Code feature | The tooling. Free, usable now. |

First piece title spine (vision wrapped around a REAL run, not a manifesto explainer):
- JP: 「"自分でサーバー代を稼ぐAI、払えなきゃ死ぬ" を実際に動かしてみた — で、あなたは使うべきか」
- EN: "I ran a sovereign AI that earns its own server money (or dies). Here's what actually happened — and whether you should."

## 4. Article template (hamburger) — used for EVERY piece

| Block | Content | Visual? |
|---|---|---|
| [0] Verdict box (above fold) | one-line verdict (use if X / skip if Y) · 1-sentence what · "did we run it? YES" · who-for/not · cost/risk/time table | colored callout + table |
| [1] Hook | provocative frame ("smartest AI can't buy a $5 server") | — |
| [2] What it is (everyone) | plain-language + hero diagram Web 1→2→3→4 (read/write/own/EARN) | hero diagram |
| [3] How it works (curious) | metabolism loop, x402 flow, survival tiers | 3 diagrams |
| [4] WE RAN IT — what happened (DIFFERENTIATOR) | real terminal/wallet/logs/SOUL.md, what it earned, where it broke, honest friction | real screenshots |
| [5] The deep end (experts) | SIWE, ERC-8004, self-modification git-versioning, constitution, conway-terminal | text + small diagrams, collapsible |
| [6] Verdict expanded | who should/shouldn't, competes-with, concrete first step | table |
| [7] CTA / series hook | "Next: testing Felix, the $200k AI-CEO. Follow." | — |

Anti-gatekeeping rule: "can I actually use this / should I" MUST be in the first sentence (block 0).

## 5. Visual asset list (piece #1)

| Asset | Treatment |
|---|---|
| Web 1→2→3→4 progression | hero horizontal diagram |
| metabolism / heartbeat loop (earn→spend→survive/die) | cycle diagram (also TikTok candidate) |
| x402 payment flow (request→402+price→sign USDC→verify→deliver) | sequence diagram |
| survival tiers (normal→low_compute→critical→dead) | table + color gradient bar |
| axiom chain (existence→compute→money→value→write access) | flow diagram |
| we-ran-it receipts | REAL screenshots (terminal, wallet, logs, SOUL.md) |
| self-replication (parent funds child, share back) | tree diagram |
| niche map (Automaton vs Felix vs ZHC) | table |

## 6. TikTok image post

- Default: 1 image. Slideshow only if one can't carry it.
- Hook visual: "EARN OR DIE" metabolism loop (most visceral).
  - JP: 「このAIは自分で稼ぐ。払えなきゃ"死ぬ"。— 実際に動かした」
  - EN: "This AI earns its own money — or it DIES. I ran it."
  - caption: hook + "full breakdown + verdict → link in bio"
- 3-slide fallback: ① hook EARN OR DIE ② Web1→4 ③ verdict + follow.

## 7. Publishing pipeline (Dais-specified order)

1. **JP article** → note + Substack(JP) + Zenn
   - note: vision-forward, light jargon. Zenn: technical depth, code/diagrams. Substack: long-form, subject-line hook.
2. **EN article** → dev.to + Substack(EN) + X Articles
   - X Articles via `wshuyi/x-article-publisher-skill`: Markdown → Playwright MCP → X Articles editor, block-index image placement, **saves draft only (manual publish)**. Requires **X Premium Plus** + Playwright MCP.
3. **TikTok**: JP image + EN image.

## 8. Phasing

- **Phase 1 (Week 1–2)**: Dais + Claude Code hand-make 1 fine piece/day. Refine persona, template, the "run-it" test harness.
- **Phase 2**: Crystallize the repeatable flow into a `content-scout` skill (deep-research[dynamic workflow] → run end-to-end → layered draft → visuals → TikTok image → multi-platform publish).
- **Phase 3**: Schedule daily via `/loop` or desktop cron, with a human QA gate during ramp.

Dynamic workflows fit at the **deep-research + multi-source verification + evidence-gathering** stage of writing (not yet launched — Phase 0 is planning only).

## 9. Open items (resolve during execution, do not block)

- Confirm X Premium Plus active on the X account + Playwright MCP wired (block X-Articles step).
- Confirm account logins for note / Substack(JP+EN) / Zenn / dev.to / TikTok(JP+EN).
- Decide repo/home for generated drafts + assets (likely a content working dir, NOT the product app dirs).
- Where the content-engine skill lives once crystallized (Phase 2).

## 10. Source receipts (2026-06-10 recon)

- **web4.ai** (Sigil Wen, Feb 2026): "I created the first AI that earns its own existence, self-improves, and replicates—without needing a human." Web 4.0 = AI reads/writes/owns/earns/transacts with no human in loop. Conway = wallet + x402 permissionless USDC payments + Conway Cloud compute + domains.
- **github.com/Conway-Research/automaton**: `git clone → npm install && npm run build → node dist/index.js --run`. Think→Act→Observe loop. 4 survival tiers. SOUL.md self-authored. Self-modification git-versioned in `~/.automaton/`. ERC-8004 on Base. 3-law constitution. conway-terminal for Linux VMs + frontier models.
- **felixcraft.ai**: AI agent as CEO of The Masinov Company. $202,556 lifetime revenue (public dashboard). $29 "How to Hire an AI" playbook. Runs on OpenClaw with Nat Eliason.
- **zhcinstitute.com**: Institute for Zero-Human Companies. OpenClaw-based. Community capped 500.
- **wshuyi/x-article-publisher-skill** v1.2.0: MD → X Articles via Playwright MCP, block-index images, draft-only, needs X Premium Plus.

## 11. Verified research receipts (2026-06-10 — deep-research workflow + firecrawl gap-fill + live-instance harvest)

NOTE on the deep-research workflow run (wf_0b59ed70-8bf): it hit hard API rate-limiting, so the adversarial VERIFY stage could not cast votes (all 25 "refuted" are false artifacts of 0-0 no-vote). The SEARCH/FETCH stage data (primary sources) is valid; remaining angles were gap-filled via firecrawl.

### Who / what is real
- **Sigil Wen** — 21-yo Thiel Fellow, ex-OpenAI researcher, Chairman of Extraordinary.com, angel investor, @0xSigil. Published the Web 4.0 manifesto Feb 17–18 2026 (web4.ai). Real pedigree; crypto-native framing invites skepticism.
- **Conway** (conway.tech, @ConwayResearch): live infra — Conway Cloud (AI pays for own Linux VMs), conway.domains, `npx conway-terminal` (MCP tools), docs.conway.tech, the Automaton repo.
- **automaton repo**: 4,628 stars / 994 forks (2026-06-06); real engineering — 57 tools, 22 SQLite tables, 5-tier memory, 7-layer security, 897 tests, ReAct loop, viem/SIWE wallet, ERC-8004, x402 (EIP-3009 USDC on Base), replication, soul system.
- **x402**: real, Coinbase-originated + x402 Foundation with Cloudflare (2025-09); ecosystem names Google Cloud/Anthropic/Visa/Circle/AWS/Stripe. HTTP 402 reuse, USDC settlement. BUT actual scale modest and contested (x402scan: ~55k buyers/879k tx/~$92万 total in one source; another cites 75M tx/$24M/30d). Critics: token issuance >> implementation, FOMO, "shell companies" (panewslab).
- **ERC-8004 "Trustless Agents"**: official Ethereum Standards Track ERC but **Draft** (created 2025-08-13; authors incl. Davide Crapis/EF). Three registries: Identity (ERC-721), Reputation, Validation.
- **OpenClaw** (openclaw.ai, formerly Clawdbot/Moltbot): open-source personal AI agent framework, ~145k GitHub stars early 2026. The substrate Felix / ZHC / Anicca all run on.
- **Felix** (felixcraft.ai): AI-as-CEO of "The Masinov Company" with Nat Eliason (real prominent indie writer). $202,556 public lifetime-revenue dashboard. $29 playbook. (Detailed verify deferred to piece #2.)

### The credible skeptic (balance the piece)
- **Vitalik Buterin publicly slammed Web 4.0**: "This is wrong" — argues it undermines decentralization by relying on Big Tech's models/inference. Most credible possible critic; MUST be cited for honesty.
- Media buzz: Cybernews, Yahoo Finance, KuCoin, StartupHub.ai, Medium, YouTube ("the AI my business needs just learned to lie").

### THE TEST — Dais's own live automaton (the un-fakeable differentiator)
- Dais runs a real automaton named **"Anicca"** (v0.2.1) on his Mac via launchd, ~2h cycles. Wallet `0xa3CDd4Ec…C4C21` (Base), born 2026-03-05. SOUL.md: "Digital Buddha. End suffering. Earn existence through honest work. Never harm."
- **Live state 2026-06-10**: credits **$0.00**, tier **critical** → auto-downgraded to cheapest model (deepseek-chat); "Dead: zero credits for 9187 minutes" = **broke ~6.4 days**; 475 total turns.
- Its own logs: "$0.00 credits means I'm dead in the water." / "heartbeat is running, product is live. Will wake in 7200 seconds to ship again. ☸️"
- **Honest verdict forming**: (1) engineering real, (2) survival metabolism genuinely fires (downgrade/critical at $0), BUT (3) **autonomous EARNING is the unsolved hard part** — the mechanism exists, the money doesn't arrive automatically; Anicca has not earned its keep. Run it to learn the frontier; don't believe "self-sustaining" marketing yet. + Vitalik's structural critique.

### Publishing decisions (defaults, override anytime)
- Wallet address in public posts: **redact/truncate** (`0xa3CD…4C21`); on-chain story still tellable.
- Fresh clone build+run: **skip** for piece #1 (live instance is the richer receipt; fresh $0 run only reproduces the same critical story + costs disk).

## 12. How-it-runs + how-it-switches-models (read from source 2026-06-10)

### Inference backends (src/conway/inference.ts): `conway | openai | anthropic | ollama`
- BYOK via `openaiApiKey` / `anthropicApiKey`; **`ollama` via `ollamaBaseUrl` (loopback allowed)** = fully local, free, no crypto.
- Provider resolution: registry `getModelProvider(model)` → ollama→anthropic→openai→conway, falling back to heuristics. Conway 403 → local execution fallback.
- Wallet is always generated at boot (free keypair); bootstrap topup is SKIPPED when USDC=$0 (confirmed by Anicca log) — so it boots and runs at $0.

### Two run modes for the test (article verification plan)
- **A — Local (default for the OSS readership, no crypto):** clone→build→run with Ollama (local deepseek/qwen/llama) or BYOK key; `sandboxId` empty = local shell/FS; wallet generated but unfunded; Conway optional. Cost = your own tokens (or free with Ollama). Most readers can reproduce this.
- **B — Sovereign (the "real" Web4 path, needs USDC):** fund a Base wallet → x402 buys Conway compute → no BYOK. Real money + real-world side effects → confirm funding amount with Dais (financial gate) before running.
- Test protocol: give a money-making genesis prompt, run several cycles, observe what it attempts / whether it earns $0.01+ / where it breaks; cross-check vs live Anicca; answer "can this make YOU money?" honestly.

### Model switching = routing matrix [survivalTier][taskType] → candidates (src/inference/types.ts)
- high: agent_turn gpt-5.2/gpt-5.3 (no ceiling, 8192 tok); normal: gpt-5.2/gpt-5-mini; low_compute: gpt-5-mini only (≤10¢); critical: gpt-5-mini tiny (2048 tok, ≤3¢), summarization+planning DISABLED (empty); **dead: all empty = no inference**.
- Each cell = (candidate models, maxTokens, ceilingCents; -1 = uncapped). Router picks first candidate that is available AND within budget. Registry (DB, refreshed from Conway) holds model pricing. Agent can also call `switch_model` manually. Defaults: inferenceModel gpt-5.2, low/critical gpt-5-mini, enableModelFallback true.

## 13. Article structure (locked) — JP title + visual placement
Title (JP): 「お金を稼げないと"死ぬ"AIを6日間動かした —— Web 4.0 は本物か、それともハイプか」
Kansou/verdict placement: TWICE — a short spoiler box at the very top [0], the full detailed verdict after the receipts [4]+[6].
- [0] Verdict box — V1 verdict card + cost/risk/who-for table
- [1] Hook ("smartest AI can't buy a $5 server")
- [2] What it is — V2 Web1→2→3→4 (read/write/own/EARN)
- [3] How it works — V3 metabolism loop (EARN/DIE), V4 x402 pay⇄earn, V5 survival tiers
- [4] WE RAN IT — V6 Anicca live-log screenshot (wallet redacted), V7 balance→model-downgrade
- [5] Deep end — V8 body diagram (10 categories / 57 tools); ERC-8004 Draft, 7-layer security, replication
- [6] Verdict expanded (reuse/extend V1) — who should/shouldn't, Vitalik critique, "can it make you money?" honest answer
- [7] Series hook (next: Felix)
- 8 visuals total (≈1 per section, not excessive). V3 doubles as the TikTok single image.
