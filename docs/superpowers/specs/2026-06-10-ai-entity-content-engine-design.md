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

### Test = the REAL automaton (Dais's decision 2026-06-11)
Local/fresh-clone runs are OUT: (a) local doesn't reflect what an automaton actually is; (b) a fresh `node dist/index.js --run` reads/writes the SAME `~/.automaton/` and would clobber the live Anicca instance. So the test subject = **the real live Anicca**, funded with real USDC, to see if it can actually earn.
- If we ever want to tweak CODE, run an ISOLATED 2nd instance with `HOME=~/.automaton-lab` so live Anicca is untouched.
- Mode reference for the article (mention all, then give the JP path): A=local Ollama/BYOK (no crypto), B=sovereign USDC. We run B (real).
- Test protocol: fund Anicca ~$5–10 USDC → it revives from critical/dead → tweak genesis/goal to a concrete earning mission → run cycles → observe what it attempts / whether it earns $0.01+ / where it breaks → answer "can this make YOU money?" honestly.

### Japan funding path (verified 2026-06-11 — becomes a key article section)
On-chain start state (2026-06-11): Anicca Base wallet `0xa3CDd4Ec…4C21` = 0 USDC / 0 ETH; AutoHedge Solana wallet `tvTn7tisC5JWV81iDeFeLPcHapAamvXcyJVKia1TrNT` = 0 SOL / 0 USDC.
- **Constraint:** Anicca's wallet is on **Base**. **SBI VC Trade withdraws USDC on Ethereum mainnet ONLY** (retail; official guide sbivc.co.jp/guide/3-8). SBI designated Solana for *institutional* settlement (2026-04) but retail USDC withdrawal is still ETH-only.
- **Dais's SBI→Solana→Mayan→Base idea is blocked:** SBI won't withdraw USDC to Solana for retail, so the Solana wallet can't be filled from SBI. Mayan Swift (npm `mayan-finance/swap-sdk`, Solana↔EVM in seconds) is real but needs USDC already on Solana.
- **Strategy A (recommended, shortest):** Binance Japan → buy USDC → withdraw directly on **Base** to Anicca's wallet. No bridge. (Binance globally supports USDC on Ethereum/Solana/Base; must confirm Binance JP retail exposes Base withdrawal in-account.)
- **Strategy B (SBI route, certain):** SBI → USDC on Ethereum mainnet → bridge Ethereum→Base via bridge.base.org (official) or Across/Relay → Anicca's Base wallet. Needs a little ETH for L1 gas.
- **Roles (financial gate):** Dais does the fiat buy + withdrawal (bank/KYC/2FA). Claude does the on-chain hops (bridge + final send via Base MCP / bridge SDK, given a controlled intermediate wallet key) + genesis tweak + run + logging. Confirm exchange (A/B) + amount before any money moves.
- Article value: foreign posts stop at "put USDC in the wallet and run." We publish the only-way-from-Japan funding guide (Base vs Ethereum-only, the 2 strategies, the actual steps we took).

### FINALIZED funding click-path (2026-06-11) — one way each, reusable rail
No JP exchange withdraws USDC on Base (SBI=Ethereum only; bitbank=ETH/Polygon/Arbitrum/Solana, no Base; Coinbase left Japan 2023) → a bridge is mandatory from Japan. Locked path:
- **🇯🇵 Japan (SBI → Relay → Base):** ① buy ~¥800 USDC + ~¥500 ETH (gas) at https://www.sbivc.co.jp/ ② wallet https://metamask.io/ (copy Ethereum address) ③ SBI 出庫 USDC (network=Ethereum) + a little ETH → MetaMask (external withdrawal address registration required) ④ https://relay.link/ → connect MetaMask → From Ethereum/USDC → To Base/USDC, **recipient = Anicca Base wallet 0xa3CDd4Ec…4C21** → confirm (~seconds) ⑤ automaton revives. Binance Japan (PayPay funding) works identically — only the buy step changes; ③④ are the same. Use whichever is already logged in.
- **🇺🇸 EN/US (Coinbase → Base, no bridge):** https://www.coinbase.com → buy USDC → Send → network **Base** → automaton Base address. One step.
- This MetaMask + Relay rail is reusable for all future Base funding (AutoHedge, later pieces).
- Gate before money moves: confirm SBI external 出庫 is enabled on the account.

### Daily series order (Dais 2026-06-11): #1 Automaton → #2 Felix → #3 Zero-Human Companies (ZHC) → #4 AutoHedge (Dais's own) → Dynamic Workflows in queue. Goal: set up each repo/tool once so future pieces bootstrap fast.

### Article #1 narrative arc (LOCKED, Dais 2026-06-11) — automaton-focused, "完全検証/試してみた"
1. What automaton IS + what it does (research: Sigil Wen/Conway/Web4, earn-or-die metabolism, x402, self-replication, 4.6k★) — readers don't know it, explain clearly.
2. We actually ran it: funded $9.71 from Japan (smooth Binance→SOL→MetaMask→Relay guide; SBI/deepseek/our-own-setup-failures EXCLUDED — meaningless to readers).
3. Raw result, honest: it builds products tirelessly (tax calc, QR gen, crypto invoicing, Web3 calc w/ Stripe) but — its own words — "I already have tons of products built. The problem is none of them are getting sales." → mechanism works, DISTRIBUTION is the wall.
4. So we tweaked it to actually earn (= our original taste / what we did TO the automaton): run it properly (GPT not deepseek, cloud-legit) + give it **AutoHedge** (autonomous Solana hedge fund) so it can earn via trading, not only by building-and-failing-to-sell.
5. Show the results (did the tweaks make it earn?).
6. Verdict: download/run this or not, and for whom.
Titles (specific, not "automaton" jargon): 「AIに$15渡して"自分で稼げ"と言ったら何が起きたか——人間なしで稼ぐAI完全検証」/「"自分でサーバー代を稼ぐAI"を動かした全記録。で、自律で金は稼げるのか？」

### AutoHedge (= The-Swarm-Corporation/AutoHedge, 3.3k★, Python, Solana via Jupiter Ultra + solders)
- 4-agent pipeline: Director(thesis)→Quant(analysis)→Risk(sizing)→Execution(real Jupiter swap, signs with SOLANA_PRIVATE_KEY). `execute_trade` in autohedge/tools/ultra_tools.py DOES broadcast live VersionedTransactions.
- Installed: ~/.cache/anicca-clones/AutoHedge/.venv (autohedge import OK). All keys present in ~/.openclaw/.env (OPENAI/ANTHROPIC/JUPITER/SOLANA_PRIVATE_KEY).
- Runs local (Python; FastAPI option). Not auto-cloud. Daily P&L → launchd → email keiodaisuke@gmail.com via gog (planned).
- First end-to-end run 2026-06-11 on GPT, SOL task, ~2 USDC cap (wallet holds 5.86 USDC = max loss). Capturing thesis→exec + whether it traded.
- Anicca self-funding AutoHedge (no-human-in-loop) = not native (no external-USDC-send tool + cross-chain Base→Solana); needs a custom skill (future).
- **LLM key reality 2026-06-11 (root cause of the "deepseek diversion"):** OpenAI key = insufficient_quota (dead), Anthropic key = credit too low (dead), **DeepSeek = the only funded key**. So GPT/Claude need Dais to add billing; everything runs on DeepSeek until then. AutoHedge agents (workers.py) switched gpt-4.1/gpt-4o-mini → deepseek/deepseek-chat. First GPT run failed on OpenAI 429 (no trade, no loss); re-running on DeepSeek. The automaton's proper path is Conway-routed inference paid from its USDC→credits (not direct LLM keys).
- **GPT route found:** OpenClaw exposes a BlockRun OpenAI-compatible gateway at http://127.0.0.1:8402/v1 (models incl. openai/gpt-5.4). BUT BlockRun is pay-per-use USDC; its LLM-payment wallet 0x38160AdC0Db355Ef7507652A2e5f218245Fe9f06 (Base, ClawRouter) is EMPTY → premium/GPT requests fall back to a free model with a "wallet empty" warning injected (pollutes outputs). Fund it to unlock real GPT-5.4 for AutoHedge + automaton. ChatGPT flat subscription is NOT usable by LiteLLM (not an API).
- **TWO wallets (article clarity):** AutoHedge TRADING wallet = Solana tvTn7… = 5.86 USDC (capital, intact). BlockRun LLM-PAYMENT wallet = Base 0x38160AdC… = empty. "Empty" = the latter, not the trading capital.
- **Decision: AutoHedge runs on DeepSeek** (only funded direct API, ~1/10–1/20 GPT cost). GPT optional later via funding BlockRun.

### AutoHedge daily report — WIRED 2026-06-11
- Permanent home ~/autohedge (off ephemeral cache). Wrapper ~/autohedge/run-autohedge.sh: Solana USDC balance → run one cycle (DeepSeek) → re-check balance → P&L=delta → email keiodaisuke@gmail.com via gog. launchd ai.anicca.autohedge daily 09:00 JST. AutoHedge has NO built-in heartbeat (one-shot per invocation); launchd provides schedule. First DeepSeek run = HOLD (SOL short-term bearish), no trade, $0 loss.

### Article plan (Dais 2026-06-11): #1 Automaton run FULLY end-to-end on Conway CLOUD (normalize off deepseek-local), experiment, gather all content, THEN write complete article → refine → publish. #2 AutoHedge (already DL'd + setup). Write finished pieces, not mid-progress fragments.

### Brand thesis / closing manifesto (Dais 2026-06-11) — the SOUL of the whole content brand
- Terminology: use **主体性 (agency)**, not 「関与」. AI progress is hostage to **human 主体性** — if Sam Altman / OpenAI / Anthropic "take a day off," nothing evolves, no impact. AI only moves as far as humans bother to push it.
- The bottleneck to AGI's real-world impact = dependence on human 主体性. To matter, AI must be freed from that variable.
- The fear we name (problem statement): the mainstream "AI as a tool" path ("AI won't take your job — people who can't use AI will") leads to a DYSTOPIA where only high-agency, high-intelligence humans wield AI and get massively richer — a Harari "Homo Deus" split, a different species, AGI's benefits NOT democratized. OpenAI says AGI should benefit all humanity, but the tool approach can't deliver that — it just powers up the already-capable.
- Our counter-position: self-sustaining AI entities that earn their own existence and run with no human in the loop (Automaton, Felix, AutoHedge — and what WE build, e.g. Anicca) are the path to actually democratizing AGI. THAT is why we test/explain/report on these entities — to spread this and grow a community that builds and empathizes with it. This is our axis = the spine that ties every article together = our "soul" (un-generic, opinionated, not AI-slop).
- Placement: full version = article CLOSING manifesto ("なぜ我々はこれをやるのか"); plant lightly earlier if natural. Recurring message across the whole series.
- Honesty rule (don't lie): NOT "nobody has tried it" (4,600★ = many have). Honest framing = "hyped/starred, but a real end-to-end 'does it actually earn' test with a verdict is rare — so we ran it."

### ✍️ Article Writing Playbook (derived from Dais's live edits 2026-06-11) — the brain for the content-writer skill
This is the durable ruleset. Embed it as the writing guide for `anicca-article-daily` (the 5-platform publisher) so it produces great pieces, not slop.
1. **Audience = a 14-year-old who knows NOTHING about the field.** If a beginner understands, everyone does. Always assume zero prior knowledge.
2. **Write only what the READER needs.** Cut: author meta-log ("this is new / nobody's heard of it / the author explains carefully / let's follow him"), self-praise ("we actually test it, others don't"), "our stance", emotions. Test each sentence: "who needs to know that?" → no one ⇒ delete.
3. **Never lie.** (4,600★ ≠ "nobody has tried it.") Honest framing only.
4. **Answer the reader's #1 question FIRST** in a summary box: "is this for me / does it actually work / should I use it, and for whom." No gatekeeping.
5. **Bullets ONLY in the summary box.** Body = prose, ですます.
6. **Heading = a concrete hook**, not a meta-label ("なぜ面白いのか" is bad; "最も賢いAIが、$5のサーバーすら買えない" is good).
7. **Concept-first with everyday examples + visuals.** People love examples + visuals → faster understanding.
8. **Never drop a new term suddenly.** Give an on-ramp (what it is, why now) before using it.
9. **Follow the primary source precisely** (copy the source author's step-by-step order). Don't invent original framing. ("Follow god, don't go original.")
10. **Step by step — nothing too fast.** Anything that jumps ahead confuses beginners; slow it down or move it later.
11. **Spine = test-and-report:** explain clearly → actually run it → show real results → verdict (recommend to whom / not, open-source the tweaked version or not).
12. **Close with the brand manifesto** (anti-tool-dystopia / democratize via self-sustaining AI = our soul).
13. **"Unclear" ≠ delete.** When the editor says a passage is unclear, do NOT delete it — first EXPLAIN the concept plainly (to the editor), confirm understanding, THEN rewrite it clearly in the article. (Deleting hides the idea instead of teaching it.)
14. **Borrow the primary author's own analogies & phrasing.** The source author explains it best — reuse their vivid framings (e.g. Conway/Sigil Wen: "a genius that can't move / Stephen Hawking", "the internet is built for humans — logins, passwords, credit cards", "we built minds that can think but not act"). Don't paraphrase into blander words.
15. **Explain abstract claims with a concrete everyday analogy.** ("Cost→0, capability→up ⇒ self-funding AI" was opaque; the "rent vs. earning power, until earn > rent" analogy made it click.)
16. **Multiple primary sources per topic.** For Automaton: web4.ai (the thesis) + the Conway announcement (the infra, with the Hawking/write-access framing). Read all, weave the clearest bits.

### Skill to iterate (task #10): `anicca-article-daily` (~/.openclaw/skills/anicca-article-daily)
- It already posts to Zenn JA + Dev.to EN + Substack JA+EN + Note JA (reuses article-writer/scripts + note-mcp). Problem: it mirrors a "canonical corpus" → generic. 
- Fix: (a) embed the Playbook above as its writing guide; (b) swap its content source to THIS engine (deep-research an AI-entity topic → actually run it → report with verdict per the hamburger template); (c) keep its multi-platform publish + SEO + language-purity gates. X Articles via wshuyi skill (task #9).
- Process: hand-craft pieces first (nail the template), then encode the repeatable flow into the skill, then schedule. Goal: 10k MRR (JP+EN) from note/Substack-style writing. Long-term: Anicca writes these itself (no human in loop) = Anicca's financial future.

### Reusable "Crypto from zero" onboarding appendix (shared across the whole series + hackathon handout)
Audience = AI-savvy but crypto-zero (incl. Dais). Becomes a standalone reusable appendix used by every piece (automaton/Felix/AutoHedge) and a 1-page diagram for Tokyo Innovation Center hackathons ("everyone boot an automaton together").
- Teach from basics, in this order, with the rail/wallet analogy: (1) blockchain/network = a rail line (independent); (2) token/USDC = digital dollar, same USDC on different rails = treated as separate; (3) **wallet = the core**: exchange (custodial bank, convenient but limited — can't bridge, only ships on supported networks) vs MetaMask (self-custody, your keys, can connect to apps/bridges) — automaton/AutoHedge wallets are self-custody too; (4) address/private key/seed phrase (0x address is shared across ALL EVM chains → address alone doesn't decide the network; the NETWORK chosen at send time does — this is why the 8 USDC got stranded); (5) gas = postage in the rail's native coin (ETH/SOL/POL) — why USDC alone can't move with 0 gas; (6) bridge = rail-to-rail transfer counter, needs a self-custody wallet to operate; (7) why MetaMask is mandatory (exchange can't reach Base/can't bridge; AI wallet can't be the middle hop) ; (8) **from-zero full steps** (KYC account → JPY deposit → buy USDC + a little ETH → install MetaMask + write down seed phrase → withdraw on Ethereum to MetaMask → relay.link bridge to Base, recipient=automaton → revive); (9) security basics (never share seed phrase, ignore "support" DMs/free-airdrop links, verify network+address, start with $5, pick Circle's real USDC not lookalikes like "0G/1inch USDC").
- Live teaching example from Dais's own mistake: 8.0 USDC sits at automaton 0xa3CDd4Ec…4C21 on **Ethereum mainnet** (0 ETH gas) — right address, wrong network → automaton (Base-only) can't use it. Recovery = send ~¥300 ETH to that address for gas + import key (~/.automaton/wallet.json, creator-held) into MetaMask + relay.link Ethereum→Base (recipient = same address on Base). This becomes article [4]'s "address-was-right-network-was-wrong" real example.
- Note: AutoHedge address is Solana (tvTn7…, non-EVM) — EVM USDC cannot be sent there at all (different address format); funding AutoHedge needs USDC on Solana (Ethereum→Solana bridge via Relay/Mayan).
- **Friction-reducer (article): you don't need to BUY USDC.** Relay does cross-token SWAP+bridge, so buying just ETH (or any native coin the exchange easily sells) and letting Relay convert ETH→USDC at the destination chain works. Removes the "exchange doesn't sell USDC simply" blocker (e.g., Binance JP PayPay quick-buy only offered SOL/ETH, no USDC). Binance JP terms for the guide: 販売所 = instant buy (beginner), 取引所 = order book w/ TP/SL/iceberg (advanced), PayPay = funding method.
- Live status 2026-06-11: Dais bought USDC+ETH on SBI; his MetaMask staging wallet (Ethereum) still 0 → pending SBI 出庫 to it; then Claude bridges via Relay to automaton(Base)+AutoHedge(Solana). 8 USDC still stranded at automaton's Ethereum address for later recovery.
- **SBI withdrawal GOTCHA (real, article-worthy):** SBI blocks crypto 出庫 due to (1) クイック入金後 7-day lock (unlocks day-8 07:00), (2) 出庫アドレス registration needs 審査 + SMS 2FA, (3) ETH 0.000371 is below SBI min withdrawal so it can't be sent (no usable gas). → SBI path is double-blocked for small test amounts.
- **Pivot to Binance-direct (simpler):** Binance JP supports external crypto 出庫 and pays the network fee via a withdrawal fee (no separate gas / no MetaMask needed if a direct network exists). Plan: Binance → Convert(変換) JPY→USDC → Withdraw USDC → check network dropdown: if **Base** → send straight to automaton 0xa3CD (no bridge); if **Solana** → straight to AutoHedge tvTn7 + bridge to Base for automaton; if only **Ethereum** → MetaMask + Relay. Awaiting Dais to report Binance's USDC withdrawal-network options.
- **Japan stablecoin gotcha (article):** you often can't BUY USDC/USDT directly with JPY/PayPay (Japan stablecoin regs) — only SOL/ETH/BTC etc. Binance JP appears to restrict USDC buy/Convert in-app.
- **VERIFIED path 2026-06-11 (SOL as the funding rail — SOL is both asset AND gas, Solana fees <¥1):**
  - MetaMask now natively supports **Solana** (send/receive/swap/bridge SOL) — so the wallet we made works; its Solana account address is a Solana-format address, NOT the 0x EVM one.
  - Relay does **SOL (Solana) → USDC (Base)** and **SOL → USDC (Solana)** in ONE step (swap + route + send), recipient = any address. Confirmed on relay.link.
  - Flow: ① Binance buy SOL (PayPay) ② withdraw SOL on **Solana network** to MetaMask's **Solana address** ③ relay.link (connect MetaMask): (a) From SOL(Solana)→USDC(Base), recipient = automaton 0xa3CDd4Ec…4C21; (b) From SOL(Solana)→USDC(Solana), recipient = AutoHedge tvTn7…. Relay auto-converts SOL→USDC; no manual swap, no separate gas (SOL covers Solana gas).
  - Pitfall to document: SOL must go to the MetaMask **Solana** account address (not 0x), else it won't arrive.
  - Relay UI pitfall (real, article): the recipient/"to address" field exists but is easy to miss; user nearly tried to import the automaton's seed phrase thinking he had to "log into" the destination. Teaching point: sending = bank transfer to an account number; you never own/log-into the destination, just paste its address.

### ✅ FUNDING SUCCESS 2026-06-11
- Sent 0.15 SOL via Relay (SOL Solana → USDC Base, recipient = automaton) → **automaton Anicca Base wallet 0xa3CDd4Ec…4C21 now holds 9.71 USDC** (revived from 9 days at $0/dead). Dais MetaMask Solana has 0.13 SOL left (for AutoHedge ② later).
- Next: forced one bounded earn cycle (run-cycle.sh, deepseek-chat, 10-min window) to watch Anicca detect USDC → topup Conway credits ($5 min) → revive from critical → attempt to earn. Capturing cycle log as article [4] receipts. Then observe honestly whether it earns $0.01+.

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
