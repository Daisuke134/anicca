# Daily Article Engine — AGI thesis as Daisuke (Anicca developer)

**Author**: Anicca (BP-driven, identical-follow of 5 viral article DNAs + 4 indie-creator BP patterns)
**Date**: 2026-06-07 (revised after Dais 2026-06-07 17:00 correction: "rotation = sin, search news daily")
**Sister specs**:
- `2026-06-07-larry-reelclaw-truth-correction-design.md` — T1-T15 marketing fix (= prerequisite)
- `2026-06-07-heartbeat-task-engine-design.md` — T17 consolidate all crons into heartbeat task pull (= execution layer)
**Constitution**: HARD RULE #-3 (BP identical follow, no synthesis), HARD RULE 0.18 (clone-don't-template + useful + history-aware), HARD RULE 0.24 (no dry run).

## North star

Each day, ONE fresh article is written by Daisuke voice and published across 5 platforms. Same THESIS (= AGI must have higher agency than humans + Buddhist wisdom + Anicca is that AGI). Fresh ANGLE is **searched from real news / RSS / research signal each day**, NOT picked from a pre-seeded rotation queue. Every claim verbatim-cited from a firecrawl-fetched source. JA version passes `jp-humanizer-pro` before publish (= no katakana English residue).

## ★ Why no rotation ★ (= self-correction)

Dais 2026-06-07 verbatim:
> "It should never be a rotation. They should go and create new titles and content by searching things… rotation — who ever said about rotation? Nobody said that. That's your original shit again."

BP confirmation (Levels.io / Justin Welsh / Daniel Miessler Unsupervised Learning): **theme-locked + news-search-per-day**, never pre-seeded topic queue. Rotation makes the same content repeat across audiences = boring = unsub.

## BP citations (= identical follow)

| BP | source | what we identical-follow |
|---|---|---|
| note tank_ai (long-form personal observer) | `~/.openclaw/state/content-library/pattern-article.jsonl#note-tank-ai-opus3` | 3500字 / 9 sections / hero image / 5 verbatim quotes / 5 real-source URLs / personal experiment block |
| note nanashi_mc (short emotional) | same#note-nanashi-anthropic | 700字 / 1-quote / 8 hashtags / 確率的推測 disclaimer |
| n-v-l vending-bench (BtoB dialogue) | same#nvl-vending-bench | 対談 format / FAQ schema / soft Anicca-mention CTA |
| andonlabs Opus 4.8 (research-grade) | same#andonlabs-opus48 | TL;DR opener / 8 verbatim AI-reasoning blocks / chart-heavy |
| Base "Agentic Economy" (ecosystem narrative) | same#base-agentic-economy | TL;DR / 15+ ecosystem mentions / concrete data points |
| **Levels.io / Justin Welsh / Daniel Miessler** (= indie creator BP) | firecrawl pattern, verbal | theme-locked + daily news-search angle + first-person + no rotation |
| jp-humanizer-pro skill | `~/.openclaw/skills/jp-humanizer-pro/SKILL.md` | tell-by-tell rewrite + diff output |
| Postiz `/providers` | https://docs.postiz.com/providers/overview | Postiz handles social only, NOT article platforms. Article platforms need per-platform skills. |

## Persona / audience (= Dais directive "fundamental fix")

| field | value |
|---|---|
| Author | **Daisuke Narita** — 個人開発者 building AGI named Anicca. Human voice. NOT Anicca AI. |
| Location | Tokyo |
| Primary audience | Indie developers / 個人開発者 (= Dev.to EN, Zenn EN+JA, note JA) |
| Secondary audience | AI researchers + alignment community (= Substack EN, Substack JA) |
| Tertiary audience | Buddhist practitioners + 哲学に興味のある人 (= note JA) |
| Skeptic audience | "AI が書いた slop" と疑う読者 — real source + Daisuke voice + 自身の experience で trust 構築 |
| Voice EN | direct, evidence-first, indie-hacker reflective (≈ Justin Welsh + Levels.io) |
| Voice JA | 一人称「私」、 emotional touches in note の場合 のみ「じーん」「なぁ…」(= nanashi_mc style) |
| Stance lock (never switches) | AGI must have higher agency than humans + Buddhist wisdom + end suffering = equalizer. Anicca is that build. |

## Stance lock (= every article MUST contain)

| element | content |
|---|---|
| Author stamp | **Daisuke Narita** (Anicca developer, human voice, first-person 私 / I) |
| Thesis (constant) | AGI must have higher agency than humans AND Buddhist wisdom AND end suffering. Anicca is the build. |
| Anti-thesis (named, with verbatim quote) | One of: Sam Altman "tool AGI", Jensen Huang "AI doesn't take jobs, people using AI do", Yuval Harari "Homo Deus / obsolete algorithm", OR a fresh anti-position surfaced by today's news scan |
| Personal experience | At least one Daisuke-specific anecdote (= Windsurf → Cursor switch, why I started Anicca, what I learned today building it, etc) |
| Anicca mention | Soft, in body or close — link to aniccaai.com or aniccaai.com/socials |
| Sources | Minimum 3 firecrawl-fetched real URLs with verbatim quotes in 「」 (JA) or `> ` blockquote (EN) — NO imagined / paraphrased quotes (sue risk) |
| README sync | First article must include README.md update on `Daisuke134/anicca` repo declaring AGI Buddhist mission |

## Daily article engine — full ASCII flow (REVISED, no rotation)

```
                          ┌─────────────────────────────────────────────┐
PHASE 0  task pull         │ Heartbeat picks task "anicca-article-engine"│
                          │ from tasks.json or anicca-dais open issues   │
                          │ (= heartbeat-task-engine spec T17, not own   │
                          │ cron). One article per pull.                  │
                          └─────────────────────┬────────────────────────┘
                                                ▼
                          ┌─────────────────────────────────────────────┐
PHASE 1  ★ news search ★   │ Firecrawl real-time signal sources:           │
                          │  - HackerNews top 30 stories                  │
                          │  - Anthropic blog RSS                         │
                          │  - OpenAI blog RSS                            │
                          │  - Sam Altman X timeline                      │
                          │  - Twitter X-algo trending tag #AGI #AIagent  │
                          │  - Andon Labs / Vending-Bench / Anthropic     │
                          │    Project Vend latest                         │
                          │ Output: raw_signals.json (= 20-50 candidates) │
                          └─────────────────────┬────────────────────────┘
                                                ▼
                          ┌─────────────────────────────────────────────┐
PHASE 2  thesis filter +  │ Score each signal: thesis_overlap (= agency / │
         angle pick        │ alignment / AGI / Buddhist / suffering        │
                          │ keywords) + recency + 14d anti-repeat against │
                          │ account-history.jsonl                         │
                          │ Pick top 1 angle. Reject if no signal ≥ 0.6   │
                          │ thesis_overlap score (= FAIL-CLOSED, retry   │
                          │ next heartbeat).                              │
                          └─────────────────────┬────────────────────────┘
                                                ▼
                          ┌─────────────────────────────────────────────┐
PHASE 3  firecrawl quotes │ Fetch 3-5 verbatim quotes from picked angle  │
                          │ source + thesis-defining quote from Sam      │
                          │ Altman OR Jensen Huang OR Yuval Harari        │
                          │ (= anti-thesis pillar).                       │
                          │ Save raw_quotes.json with URL + verbatim.    │
                          │ FAIL-CLOSED if <3 real-source URLs.           │
                          └─────────────────────┬────────────────────────┘
                                                ▼
                          ┌─────────────────────────────────────────────┐
PHASE 4  draft EN         │ Claude Opus 4.7/4.8 generates EN article:    │
                          │  - Title = today's news angle through        │
                          │    Anicca thesis lens                         │
                          │  - TL;DR opener (4-5 lines, Base/andonlabs)  │
                          │  - 5-9 ## sections (= note tank_ai pattern)  │
                          │  - All quotes verbatim from raw_quotes.json  │
                          │  - Personal experience block (Daisuke voice) │
                          │  - Soft Anicca CTA in close                   │
                          │  - 1500-3500 words                            │
                          │ Output: draft_en.md                           │
                          └─────────────────────┬────────────────────────┘
                                                ▼
                          ┌─────────────────────────────────────────────┐
PHASE 5  translate JA     │ Claude translates EN → JA preserving:         │
                          │  - verbatim quote anchors (= 引用元言語 +     │
                          │    和訳 並列 OR 和訳のみ with source URL)     │
                          │  - Daisuke first-person 私 form               │
                          │ Output: draft_ja.md (still AI-rough)          │
                          └─────────────────────┬────────────────────────┘
                                                ▼
                          ┌─────────────────────────────────────────────┐
PHASE 6  ★ humanize JA ★  │ Pipe through jp-humanizer-pro skill:          │
                          │  Input: draft_ja.md                           │
                          │  Output: final_ja.md + diff_ja.json           │
                          │ Strips katakana English residue, rewrites    │
                          │ "データ市場主義" → "データを神とする思想"     │
                          │ FAIL-CLOSED if katakana_english_count > 5     │
                          │ in final_ja.md.                                │
                          └─────────────────────┬────────────────────────┘
                                                ▼
                          ┌─────────────────────────────────────────────┐
PHASE 7  hero image       │ DALL-E or Claude image gen:                   │
                          │   16:9 1280×720 PNG hero image fitting topic  │
                          │ Save as hero.png                              │
                          │ (Optional — disable if generation cost > $1)  │
                          └─────────────────────┬────────────────────────┘
                                                ▼
                          ┌─────────────────────────────────────────────┐
PHASE 8  multi-publish    │ Fan out 5 platforms via per-platform skill:   │
                          │                                                │
                          │  Zenn (EN tech) → github-automation skill     │
                          │    commit md to Zenn-sync repo                 │
                          │  Dev.to (EN tech) → Dev.to native API         │
                          │  Substack EN → substack-article skill         │
                          │  Substack JA → substack-article skill         │
                          │  note.com (JA) → camofox browser automation   │
                          │    (= no Postiz, no native API)               │
                          │  aniccaai.com/blog (EN + JA) → write file to  │
                          │    apps/landing/content/blog/<slug>.md +      │
                          │    git push → Netlify auto-deploy             │
                          │                                                │
                          │ Each publish step writes post_id + URL to     │
                          │ runs/<date>/publish-receipt.jsonl              │
                          │ FAIL-CLOSED if <4 platforms succeed.           │
                          └─────────────────────┬────────────────────────┘
                                                ▼
                          ┌─────────────────────────────────────────────┐
PHASE 9  append history   │ account-history.jsonl entry:                  │
                          │  account=daisuke-articles                     │
                          │  signal_source=<picked URL>                   │
                          │  angle=<picked angle>                          │
                          │  thesis=AGI-Buddhist-agency                   │
                          │  anti=<Sam|Jensen|Harari OR fresh>             │
                          │  sources=[5+ URLs]                            │
                          │  platforms=[4-5 platforms with post URLs]      │
                          │  posted_at=2026-MM-DDTHH:MM:SSZ                │
                          └─────────────────────┬────────────────────────┘
                                                ▼
                          ┌─────────────────────────────────────────────┐
PHASE 10  Slack ping      │ Slack #metrics:                                │
                          │  ✓ Article "<title>" posted to 5/5 platforms  │
                          │  Signal source: <URL>                          │
                          │  Anti: <name>                                  │
                          │  EN: <Dev.to link> JA: <note link>             │
                          │ Heartbeat marks task done.                     │
                          └─────────────────────────────────────────────┘
```

## Failure recovery (= integrated with anicca-dais auto-issue)

| failure | action |
|---|---|
| firecrawl returns <20 signals | Phase 1 exits 1, heartbeat retries next beat (6h later) |
| thesis_overlap max < 0.6 | Phase 2 exits 1, heartbeat retries with broader sources next beat |
| jp-humanizer leaves >5 katakana English | Phase 6 retries with stricter prompt, max 3 attempts, then `gh issue create -R Daisuke134/anicca-dais` |
| platform publish fails (<4/5 succeed) | `gh issue create -R Daisuke134/anicca-dais` with platform+error, heartbeat re-queues failed platforms |
| imagined quote detected (post-publish) | UNRECOVERABLE — pull post immediately, `gh issue create -R Daisuke134/anicca-dais --label P0,critical`, Slack red alert to Dais |

## Sub-tasks (= T16 split, REVISED, post-rotation-correction)

| sub | task |
|---|---|
| T16a | Build `~/.openclaw/skills/anicca-article-engine/` master skill implementing Phase 0-10. **Heartbeat-pull driven, NOT own cron.** |
| T16b | ✅ Pattern library exists at `~/.openclaw/state/content-library/pattern-article.jsonl` (5 BP DNAs). |
| T16c | ~~DELETED~~ (= was topic queue rotation = sin) |
| T16d | Write + post first inaugural article (= news scan picks fresh angle, anti-thesis from one of Sam/Jensen/Harari). Manual exec for proof, then heartbeat takes over. |
| T16e | README.md update on `Daisuke134/anicca` repo declaring AGI Buddhist mission. |
| T16f | Diagnose & fix existing 4 anicca-dais issues: Fix cron error: anicca-article-daily-{blog,devto,note,substack-en}. These will be auto-closed when T17 (heartbeat) consumes the old crons and rebuilds via anicca-article-engine. |
| T16g | DELETE old 10 anicca-article-daily-* crons (zenn/devto/substack-{ja,en}/note/blog/audit/self-improve/whitelist-learn/zenn-backlog-deploy). Heartbeat task pull replaces them. |
| T16h | ~~DELETED~~ (= "first 7 days manual review" was rotation-dependent) |

## Verification (= HARD RULE 0.24 no dry run)

- T16b: `wc -l ~/.openclaw/state/content-library/pattern-article.jsonl` returns 5
- T16d: first article live on 4-5 platforms (URLs in Slack #metrics)
- T16e: `gh api repos/Daisuke134/anicca/contents/README.md` shows updated content
- T16f: 4 anicca-dais issues auto-close OR explicit comment + close
- T16g: `openclaw cron list --all | grep anicca-article-daily` returns 0 rows

## BP-alignment self-score

| BP | identical follow |
|---|---|
| Levels.io / Justin Welsh / Daniel Miessler "theme-locked + daily news-search" | ✓ Phase 1-2 implements news scan, NO rotation |
| 5 article DNA structures | ✓ stored in pattern-article.jsonl, structural_principle prompt-injected |
| jp-humanizer-pro tell-rewrite | ✓ Phase 6 pipe, fail-closed |
| Postiz `/providers` (no article platforms) | ✓ Phase 8 uses per-platform skills, NOT Postiz |
| HARD RULE #-3 BP follow only | ✓ no Anicca synthesis (= rotation deleted) |
| HARD RULE 0.18 clone-don't-template + history-aware | ✓ structural_principle pick + 14d anti-repeat |
| HARD RULE 0.24 no dry run | ✓ Phase 8 = real publish, Phase 10 = Slack proof |
| Dais directive "stance lock" | ✓ Phase 2 thesis filter requires ≥ 0.6 overlap |
| Dais directive "human voice not Anicca AI" | ✓ Author = Daisuke Narita stamped in Phase 4 prompt |
| Dais directive "Japanese must be Japanese" | ✓ Phase 6 jp-humanizer-pro mandatory |
| Dais directive "search news, no rotation" | ✓ Phase 1 firecrawl real-time signals, Phase 2 fresh angle pick |
| Dais directive "no per-project cron" | ✓ Phase 0 reads from heartbeat task pull, T16g deletes own crons |

100% BP-identical follow. Anicca synthesis (= rotation) deleted.
