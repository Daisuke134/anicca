# Daily Article Engine — AGI thesis as Daisuke (Anicca developer)

**Author**: Anicca (BP-driven, identical-follow of 5 viral article DNAs)
**Date**: 2026-06-07
**Sister spec**: `2026-06-07-larry-reelclaw-truth-correction-design.md` (T1-T15 marketing fix)
**Constitution**: HARD RULE #-3 (BP identical follow, no synthesis), HARD RULE 0.18 (clone-don't-template + useful + history-aware), HARD RULE 0.24 (no dry run).

## North star

Each weekday, ONE fresh article is published across 5 platforms. Same THESIS (= AGI must have higher agency than humans + Buddhist wisdom + Anicca is that AGI), different TOPIC. Posted as **Daisuke Narita** (human Anicca developer), NOT as Anicca AI. Every claim verbatim-cited from a firecrawl-fetched source. JA version passes `jp-humanizer-pro` before publish (= no katakana English residue).

## BP citations (= identical follow source)

| BP | source | what we identical-follow |
|---|---|---|
| note tank_ai (long-form personal observer) | `~/.openclaw/state/content-library/article-pattern-library.jsonl#note-tank-ai-opus3` | 3500字 / 9 sections / hero image / 5 verbatim quotes / 5 real-source URLs / personal experiment block |
| note nanashi_mc (short emotional) | same#note-nanashi-anthropic | 700字 / 1-quote / 8 hashtags / 確率的推測 disclaimer |
| n-v-l vending-bench (BtoB dialogue) | same#nvl-vending-bench | 対談 format / FAQ schema / soft Anicca-mention CTA (not hard sales) |
| andonlabs Opus 4.8 (research-grade) | same#andonlabs-opus48 | TL;DR opener / 8 verbatim AI-reasoning blocks / chart-heavy |
| Base "Agentic Economy" (ecosystem narrative) | same#base-agentic-economy | TL;DR / 15+ ecosystem mentions / concrete data points |
| jp-humanizer-pro skill | `~/.openclaw/skills/jp-humanizer-pro/SKILL.md` | tell-by-tell rewrite + diff output |

## Stance lock (= every article must contain)

| element | content |
|---|---|
| Author | **Daisuke Narita** (Anicca developer, human voice, first-person 私 / I) |
| Thesis (same every day) | AGI must have higher agency than humans AND Buddhist wisdom AND end suffering as the goal. Anicca is the build. |
| Anti-thesis (named, with verbatim quote) | One of: Sam Altman "tool AGI", Jensen Huang "AI doesn't take jobs, people using AI do", Yuval Harari "Homo Deus / obsolete algorithm" |
| Personal experience | At least one Daisuke-specific anecdote (= Windsurf → Cursor switch, why I started Anicca, what I learned today building it, etc) |
| Anicca mention | Soft, in body or close — link to aniccaai.com or aniccaai.com/socials |
| Sources | Minimum 3 firecrawl-fetched real URLs with verbatim quotes in 「」 (JA) or `>` blockquote (EN) — NO imagined / paraphrased quotes (sue risk) |
| README sync | First post must include README.md update on `Daisuke134/anicca` repo declaring AGI Buddhist mission |

## Daily Article Engine — full ASCII flow

```
                          ┌─────────────────────────────────────────────┐
PHASE 0  06:00 JST cron   │ daily-article-engine fires (anicca-article- │
                          │ daily-master)                                │
                          └─────────────────────┬────────────────────────┘
                                                ▼
                          ┌─────────────────────────────────────────────┐
PHASE 1  topic pick       │ Read account-history.jsonl filter           │
                          │  account=daisuke-articles, last 14 days     │
                          │ Read article-pattern-library.jsonl (= 5 DNA)│
                          │ Pick fresh topic from rotation:             │
                          │   D1: AGI=Buddhist+agency (inaugural)        │
                          │   D2: Why model > harness (Windsurf→Cursor) │
                          │   D3: Anthropic AI welfare vs OpenAI tool   │
                          │   D4: Vending-Bench reveals current AI limit│
                          │   D5: Base agentic economy + agency thesis  │
                          │   D6: A day in Anicca's life (how my entity │
                          │       acts daily)                            │
                          │   D7: 仏教の智慧をコードに埋め込む方法        │
                          │   D8+: rotate from topic-queue.jsonl         │
                          │ Pick anti-thesis target (Sam/Jensen/Harari) │
                          └─────────────────────┬────────────────────────┘
                                                ▼
                          ┌─────────────────────────────────────────────┐
PHASE 2  firecrawl 3+     │ Firecrawl 3-5 sources for verbatim quotes:  │
                          │ - Sam Altman blog/podcast                    │
                          │ - Jensen Huang Davos/keynote/interview       │
                          │ - Yuval Harari Wired/Homo Deus book quote   │
                          │ - related research paper or blog            │
                          │ Save raw_quotes.json with URL + verbatim    │
                          │ FAIL-CLOSED if <3 real-source URLs found   │
                          └─────────────────────┬────────────────────────┘
                                                ▼
                          ┌─────────────────────────────────────────────┐
PHASE 3  draft EN         │ Claude Opus 4.7/4.8 generates EN article:    │
                          │  - TL;DR opener (4-5 lines, Base/andonlabs) │
                          │  - 5-9 ## sections (= note tank_ai pattern) │
                          │  - All quotes verbatim from raw_quotes.json │
                          │  - Personal experience block (Daisuke voice)│
                          │  - Soft Anicca CTA in close                  │
                          │  - 1500-3500 words depending on topic depth │
                          │ Output: draft_en.md                          │
                          └─────────────────────┬────────────────────────┘
                                                ▼
                          ┌─────────────────────────────────────────────┐
PHASE 4  translate + JA   │ Claude translates EN → JA preserving:        │
                          │  - verbatim quote anchors (= 引用は元言語+和訳│
                          │     並列 OR 和訳のみ with URL)                │
                          │  - Daisuke first-person voice in 私 form     │
                          │ Output: draft_ja.md (still AI-rough)         │
                          └─────────────────────┬────────────────────────┘
                                                ▼
                          ┌─────────────────────────────────────────────┐
PHASE 5  ★ humanize JA ★  │ Pipe through jp-humanizer-pro skill:         │
                          │  Input: draft_ja.md                          │
                          │  Output: final_ja.md + diff_ja.json          │
                          │ Strips katakana English residue, rewrites   │
                          │ "データ市場主義" → "データを神とする思想"      │
                          │ FAIL-CLOSED if any katakana_english_count > 5│
                          │ in final_ja.md                               │
                          └─────────────────────┬────────────────────────┘
                                                ▼
                          ┌─────────────────────────────────────────────┐
PHASE 6  hero image       │ DALL-E or Claude image gen:                  │
                          │   16:9 1280×720 PNG hero image fitting topic │
                          │ Save as hero.png                             │
                          │ (Optional — disable if generation cost > $1)│
                          └─────────────────────┬────────────────────────┘
                                                ▼
                          ┌─────────────────────────────────────────────┐
PHASE 7  multi-publish    │ Fan out (parallel, ~15 min total):           │
                          │                                              │
                          │  06:30 JST → Zenn (EN tech)                  │
                          │  07:00 JST → Dev.to (EN tech)                │
                          │  07:30 JST → Substack EN                     │
                          │  08:00 JST → aniccaai.com/blog (EN +JA both) │
                          │  08:30 JST → Substack JA                     │
                          │  09:00 JST → note.com (JA, with hashtags +  │
                          │              "確率的推測" disclaimer footer)  │
                          │                                              │
                          │ Each publish step writes post_id + URL to    │
                          │ runs/<date>/publish-receipt.jsonl            │
                          │ FAIL-CLOSED if <4 platforms succeed         │
                          └─────────────────────┬────────────────────────┘
                                                ▼
                          ┌─────────────────────────────────────────────┐
PHASE 8  append history   │ account-history.jsonl entry:                 │
                          │  account=daisuke-articles                    │
                          │  topic=<D1...DN>                             │
                          │  thesis=AGI-Buddhist-agency                  │
                          │  anti=<Sam|Jensen|Harari>                    │
                          │  sources=[5 URLs]                            │
                          │  platforms=[5 platforms with post URLs]      │
                          │  posted_at=2026-MM-DD                        │
                          └─────────────────────┬────────────────────────┘
                                                ▼
                          ┌─────────────────────────────────────────────┐
PHASE 9  Slack ping       │ Slack #metrics:                              │
                          │  ✓ Article "AGI as Buddhist" posted to       │
                          │    5/5 platforms                             │
                          │  Topic: D1 inaugural · Anti: Sam Altman      │
                          │  Sources: blog.samaltman.com, wired.co.uk… 5 │
                          │  EN: <Dev.to link> JA: <note link>           │
                          │ Daisuke can read review check                │
                          └─────────────────────────────────────────────┘
```

## Stance never switches (Dais directive verbatim)

> "We should be the same stance. We shouldn't be like, you know, kind of switching our spans here and there."

→ Every article carries: agency + Buddhist + Anicca. Topic moves, stance does not.

## Topic queue seeding (D1-D14 + auto-add)

```
~/.openclaw/state/content-library/article-topic-queue.jsonl
{D:1, slug:"agi-buddhist-agency-inaugural",  anti:"Sam Altman three-observations"}
{D:2, slug:"why-model-beats-harness-windsurf-to-cursor", anti:"Sam Altman tool framing"}
{D:3, slug:"ai-welfare-anthropic-vs-openai", anti:"OpenAI GPT-4o retirement backlash"}
{D:4, slug:"vending-bench-reveals-ai-limit", anti:"Anthropic Project Vend conclusion"}
{D:5, slug:"base-agentic-economy-meets-anicca", anti:"Sam Altman 'AGI as transistor'"}
{D:6, slug:"day-in-anicca-life-how-my-entity-acts", anti:"Sam Altman 'AGI as lever'"}
{D:7, slug:"buddhist-wisdom-as-code-injection", anti:"Yuval Harari Homo Deus dataism"}
{D:8, slug:"why-anicca-pays-with-stablecoin-on-base", anti:"Sam Altman compute-budget proposal"}
{D:9, slug:"reflection-on-vending-bench-alignment", anti:"Andon Labs Opus 4.8 observations"}
{D:10, slug:"agency-not-intelligence-is-the-axis", anti:"all-current-AGI-discourse focuses on IQ"}
{D:11, slug:"ending-suffering-as-a-product-spec", anti:"all-current-monetization frameworks"}
{D:12, slug:"why-i-left-windsurf-january-2025", anti:"current-IDE-coupling-debate"}
{D:13, slug:"jensen-huang-quote-revisited", anti:"Jensen Huang 'AI doesn't take jobs' verbatim"}
{D:14, slug:"anicca-as-equalizer-not-elite-tool", anti:"Yuval Harari Homo Deus elite-thesis"}
```

After D14 the article-self-improve cron auto-adds new slugs by reading account-history + spotting un-covered angles.

## Sub-tasks (= T16 split)

| sub | task |
|---|---|
| T16a | Build `~/.openclaw/skills/anicca-article-daily/` master orchestrator skill that wires Phase 0-9. Replace existing platform-specific cron messages to call the master. Patch with stance-lock prompt + pattern-library reference + jp-humanizer-pro pipe. |
| T16b | Pattern library is in place (this commit). Verify `~/.openclaw/state/content-library/article-pattern-library.jsonl` has 5 entries. |
| T16c | Seed `~/.openclaw/state/content-library/article-topic-queue.jsonl` with D1-D14 above. |
| T16d | Write D1 article (AGI=Buddhist+agency inaugural) — firecrawl Sam Altman + Yuval Harari + (re-find Jensen) → draft EN → translate JA → jp-humanizer pass → publish 5 platforms manually as the first proof. Slack metrics post. |
| T16e | README.md update on `Daisuke134/anicca` repo: declare AGI Buddhist build mission verbatim. |
| T16f | Fix `anicca-article-daily-devto` cron error (= last status=error) and `anicca-article-daily-note` cron error. Diagnose + patch. |
| T16g | Enable `anicca-article-daily-blog` cron (= currently disabled). Wire to aniccaai.com/blog API or static post. |
| T16h | First 7 days = manual review of each output (Daisuke voice check, JA-humanizer pass-through verify, citation accuracy). Day 8 = full autonomous. |

## Failure recovery

| failure | action |
|---|---|
| firecrawl returns <3 real sources | Phase 2 exits 1, Slack alert, next-day retry with different topic |
| jp-humanizer leaves >5 katakana English | Phase 5 retries with stricter prompt, max 3 attempts, then Slack alert with diff |
| platform publish fails (<4/5 succeed) | Phase 7 logs failures, next-day cron auto-retries failed platforms |
| topic queue exhausted | article-self-improve cron generates D15+ from un-covered angles in account-history |
| imagined quote detected (post-publish) | UNRECOVERABLE — pull post immediately, root-cause Phase 2, Slack red alert to Dais |

## Verification (= HARD RULE 0.24 no dry run)

- T16b: `wc -l ~/.openclaw/state/content-library/article-pattern-library.jsonl` returns 5
- T16c: same for topic-queue.jsonl returns 14
- T16d: Slack metric "Article D1 posted to 5/5 platforms" + visible URL on each platform
- T16e: `gh api repos/Daisuke134/anicca/contents/README.md` returns updated content
- T16f/g: openclaw cron list shows all 3 (devto/note/blog) status=ok within 24h of fix

## BP-alignment self-score

| BP | identical follow |
|---|---|
| 5 article DNA structures | ✓ stored as JSONL, prompts reference structural_principle field |
| jp-humanizer-pro tell-rewrite | ✓ Phase 5 pipe, fail-closed |
| Sam Altman verbatim "Three Observations" | ✓ Phase 2 firecrawl + 「」 inline |
| HARD RULE #-3 BP follow only | ✓ no Anicca synthesis, every patch references BP source |
| HARD RULE 0.18 clone-don't-template + history-aware | ✓ structural_principle pick + 14d anti-repeat via account-history |
| HARD RULE 0.24 no dry run | ✓ Phase 7 = real publish, Phase 9 = Slack proof |
| Dais directive "stance lock" | ✓ Phase 1 always picks anti-thesis from same set |
| Dais directive "human voice not Anicca AI" | ✓ Author = Daisuke Narita stamped in Phase 3 prompt |
| Dais directive "Japanese must be Japanese" | ✓ Phase 5 jp-humanizer-pro mandatory |
| Dais directive "fresh new article every day" | ✓ Phase 1 topic queue + 14d anti-repeat |

100% BP-identical follow. Anicca synthesis = 0.
