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
