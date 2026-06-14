# Article #2 — Frank (BlockRun) Design Spec

- **Date**: 2026-06-14
- **Series**: AI-entities (parent SSOT = `docs/superpowers/specs/2026-06-10-ai-entity-content-engine-design.md`)
- **Status**: DRAFT — research workflow pending, hamburger structure to be confirmed by Dais
- **Editor / co-author**: Daisuke (human-in-loop, block-by-block) + Claude Code
- **Subject**: **Frank / Franklin** by **BlockRun** (founder = @bc1beat). The "AI agent with a wallet" — spends USDC autonomously across 55+ providers via x402.
- **Anti-rule**: NEVER mention Anicca in this article. Reader = anyone who wants to understand Frank/BlockRun. We are scouts who actually ran it.

## 1. Why this piece (slot in the series)

Article #1 (Automaton, 2026-06-11 draft) framed the "earn-or-die" sovereign-AI thesis and showed the no-human-in-loop end of the spectrum. In that piece, Frank was introduced in one paragraph as "the more autonomous one with a wallet that decides what to pay for, per task". Article #2 zooms in on Frank: what it actually does, the BlockRun ecosystem around it (ClawRouter + blockrun-mcp + Money-Maker), and whether a reader should adopt it.

## 2. Primary sources (locked, must all be read in full)

| # | URL | Role |
|---|---|---|
| 1 | https://blockrun.ai/get-started | Onboarding path (what a new user does first) |
| 2 | https://blockrun.ai/docs | Concept + API surface |
| 3 | https://github.com/BlockRunAI/Franklin | The agent itself (627★, Apache-2.0, TS) |
| 4 | https://github.com/BlockRunAI/blockrun-mcp | Live-data MCP (search/research/markets/crypto/X), x402 pay-per-call (466★) |
| 5 | https://github.com/BlockRunAI/awesome-blockrun | Official ecosystem index (15★) |
| 6 | https://github.com/BlockRunAI/awesome-OpenClaw-Money-Maker | Money-loop curation (270★) |
| 7 | https://x.com/bc1beat | Founder voice / latest framing |

Adjacent for context (cite as needed): x402.org, Coinbase x402 launch post, Base for Agents, awesome-OpenClaw-Money-Maker README's "Web4 money loop" diagram (USDC → Franklin → ClawRouter → LLM → profit → reinvest).

## 3. Reader / verdict (block [0] target)

- **Reader**: AI builder who already runs Claude Code / OpenClaw, hears "Frank" / "BlockRun" everywhere, wants a straight call: install it or skip.
- **Pre-research hypothesis (to verify in WE-RAN-IT)**:
  - ✓ blockrun-mcp = useful TODAY for any agent (live web/X/markets, USDC pay-per-call, no subs) → install if you build agents
  - ◯ Franklin = useful if you want a wallet-funded autonomous worker; needs USDC funding (same Japan rail as Automaton)
  - ? "earns money on its own" = unverified — Frank's docs frame it as a SPENDER (autonomously pays for tools to get work done), not an earner. We test whether ANY revenue path is built in.

## 4. Hamburger (PRE-RESEARCH skeleton — to be replaced by workflow output)

The final hamburger comes from the research workflow run in §6. This is a placeholder so the structure is visible while research runs:

| Block | Working title | Notes |
|---|---|---|
| [0] | Verdict box | text only, 1-line use/skip + cost/risk/who-for table |
| [1] | Hook | The bottleneck not solved by Automaton (= Frank's actual thesis surfaced from sources) |
| [2] | What Frank is (everyone) | Wallet + YOPO + 55+ providers — in plain words |
| [3] | The BlockRun stack | ClawRouter (LLM gateway) + blockrun-mcp (live data) + Franklin (the agent) + awesome-OpenClaw-Money-Maker (the money loop) |
| [4] | How it actually works | x402 per-call payment flow, wallet boot, model selection, fallback (free-tier when wallet empty) |
| [5] | WE RAN IT — receipts | install blockrun-mcp, run Franklin, fund wallet via the Japan rail (re-use), observe real spend log + outputs |
| [6] | Honest verdict expanded | who should/shouldn't, what it earns/doesn't, where it breaks, founder credibility |
| [7] | Series hook | next piece + manifesto closing (per parent SSOT §13) |
| [8] | 出典 | every URL cited inline + listed |

Locked rules from parent SSOT Playbook (apply verbatim, do not re-derive):
- Audience = 14-year-old who knows nothing (rule 1).
- Verdict in sentence 1 (rule 4).
- Body = ですます prose, bullets only in verdict (rule 5).
- No em-dash「——」(rule 30). No unnatural set-phrases (rule 31).
- Heading = concrete hook, not meta-label (rule 6).
- Every term defined on first use, minimally (rules 8 / 39 / 54).
- Cite everything; concrete > vague; map the landscape, don't aggregate one source (rules 25–27).
- Show full blocks in review (rule 44).
- Close with the brand manifesto (rule 12, parent SSOT §11 closing manifesto).

## 5. WE-RAN-IT protocol (block [5] receipts to capture)

| Step | Action | Receipt |
|---|---|---|
| 1 | `git clone --depth 1` Franklin into `~/.cache/anicca-clones/` (HARD #-1) | repo size, top-level layout |
| 2 | Read Franklin README + `package.json` + entrypoint; document what's needed to boot | exact `npm` commands |
| 3 | Run blockrun-mcp via the published install path (don't clone if a `npx` / SDK entry exists) | first response from one live-data tool |
| 4 | Fund Frank wallet (if Frank has its own wallet at boot, capture address; reuse parent SSOT §12 Japan rail if needed) | wallet address (truncated) + USDC arrival tx |
| 5 | Run Frank with a small concrete task (e.g. "research X and produce a 1-page brief", $0.50 cap) | terminal log: what it paid for, how many providers, total spend, output quality |
| 6 | Honest report: did the output justify the spend? did it try to earn anything? | screenshot + verdict |

Spend cap: $1 USDC total for this test. Capture full log into `docs/articles/research/2026-06-14-frank-run-log.md`.

## 6. Research workflow (Dynamic Workflow — BP 6 patterns)

Built per the BP article (fan-out → adversarial verify → synthesize). One-shot, foreground, returns the hamburger structure as structured JSON.

- **Phase Fetch (fan-out)**: one Haiku-class agent per primary source (7 sources). Each agent uses `firecrawl scrape <url> markdown` (HARD 0.23) + `gh api` for GitHub files (README, key code files). Returns structured `{facts, quotes, claims, concrete_numbers, founder_voice_snippets}`.
- **Phase Verify (adversarial)**: for each non-trivial CLAIM surfaced in Fetch, spawn a verifier agent that re-checks against the primary URL with the explicit instruction to REFUTE. Vote ≥ majority confirms; otherwise the claim drops.
- **Phase Synthesize (one Opus agent)**: ingest verified facts + parent SSOT §11 playbook + Automaton article voice sample → produce: (a) 3 title candidates JP, (b) 9-block hamburger with one-paragraph guidance per block, (c) image-spot 🎨V# list, (d) sources list.
- **Token budget**: ~50k output tokens total. Quarantine: all Fetch agents are read-only (no side-effects). No agent writes to disk; outputs land in workflow return value, then this main loop writes to the spec.

Output of the workflow goes into a new section §7 below (replaces §4 placeholder).

## 7. Locked hamburger (TO BE FILLED by workflow run)

_Empty until §6 workflow completes — Dais reviews and iterates from title and block [0] one-by-one._

## 8. Publishing pipeline (parent SSOT §7 inherited)

JP first: note + Zenn + Substack(JP) + X Articles. EN follow-up: dev.to + Substack(EN) + X Articles. TikTok: 1 image JP + 1 image EN. The "AI article-writer" skill rebuild (parent SSOT §13 task) will absorb this flow once Article #2 is shipped — Article #2 sets the second data point (after Automaton) for what the skill must automate.

## 9. Open items

- Article slot in series: Automaton (#1, drafted) → **Frank (#2, this)** → Felix / ZHC / AutoHedge (later — order TBC).
- Founder bio: get @bc1beat real-name + pedigree from Twitter scrape during Fetch phase.
- Does Frank have a public dashboard like Felix's $202k? → Fetch phase answers.
- Does BlockRun host Franklin (managed) or is it self-host only? → Fetch phase answers.

## 10. Skill iteration follow-up (parent SSOT §13)

After Article #2 ships and is reviewed by Dais, rebuild `~/.openclaw/skills/article-writer` (or successor `anicca-article-daily`) so the deepest-search → run end-to-end → hamburger → multi-platform publish flow is automated. Embed parent SSOT §11 Playbook (54 rules) + this article's template + Automaton's template as in-skill guides. The skill must produce Article-#1-and-#2-quality pieces with no human in the loop, fulfilling the very thesis the series writes about (parent SSOT §13 brand strategy).
