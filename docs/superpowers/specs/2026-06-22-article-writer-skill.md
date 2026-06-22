# SPEC — article-writer skill (no-human, tested, cited, beginner, never-slop) — 2026-06-22

Goal: a skill that writes genuinely good, beginner-friendly, cited, non-slop articles (JP-first → EN) that
people would PAY a subscription for — then self-scores and posts to note/Zenn/dev.to/X with no human in the
loop. The automaton article (this session) is the reference "known-good" used to evaluate the skill (Dais =
editor, the skill = writer). Don't reinvent generic good-writing mechanics; lift them. OUR differentiators
(no skill provides these): beginner/no-jargon calibration, real Firecrawl/ctx7 source-fetching for citations,
JP-first with zero English leakage.

## Evaluated 5 source skills (installed ~/.claude/skills/) — what to take
- **stop-slop** (Hardik Pandya, MIT) — EN de-slop. COPY WHOLESALE: kill -ly adverbs, no em dashes, human
  subject every sentence, kill false agency, kill throat-clearing/vague-declarative, 5-axis score <35/50→rewrite.
- **stop-ai-slop-jp** (genshi.ai; has LICENSE—verify before verbatim) — JP de-slop. COPY: "AI臭=書き手の不在",
  A2 falsifiable-claim-or-delete, A3 lukewarm verdicts, A6 kill both-sides + keep venom, false-agency table,
  banned phrases.md (いかがでしたでしょうか/近年〜注目/全角ダッシュ/装飾絵文字), B7 noun-phrase headings, "音読".
- **research-paper-writing** (Master-cai/Peng Sida, MIT, keep attribution) — CHERRY-PICK: one-paragraph-one-
  message (msg in sentence 1), reverse-outlining, Claim|Evidence|Status map (unsupported→weaken/cut),
  adversarial skeptical-reviewer loop, transition-word bank, lazy-load section guides. SKIP CV/ML stems.
- **article-writing-skills** (Irteza, MIT) — CHERRY-PICK only: banned-phrase list, show-don't-tell
  ("adjectives are cheap; multipliers are earned"), honest-vs-rhetorical hedging, before/after teaching format.
  SKIP the Karpathy persona + jargon-mandate (inverse of beginner-friendly).
- **cody-article-writer** (iBuildWith.ai, ⚠️ PROPRIETARY All-Rights-Reserved — IDEAS ONLY, never paste/fork)
  — re-implement: 12-phase gated pipeline, progressive style-guide-as-JSON (voice as 0-10 knobs applied
  stage-by-stage), "firm sounding board not sycophant", required-source completion check, editor pass writes
  a NEW file. NOTE: its anti-slop is opt-in (our mistake to avoid) + it uses WebSearch (banned → Firecrawl).

## The 10 rules OUR skill encodes (default-ON, every run)
1. Falsifiable-claim gate: every key sentence is arguable; can't get concrete → delete. (jp A2)
2. Claim|Evidence|Status map before "done"; Status must point to a FETCHED source (Firecrawl/ctx7), not memory. (research+IBA)
3. Name the human — kill false agency ("データが示している"→"誰が何をした"). (jp+stop-slop)
4. One paragraph=one message (sentence 1); nouns self-contained; cause/contrast/consequence flow; verify by reverse-outline. (research)
5. BEGINNER layer (ours): jargon→plain ("思考のOSを更新"→"考え方を変える"); gloss a load-bearing term before reuse; explain HL/Ethereum/etc on first use.
6. Lukewarm verdicts + keep venom; kill both-sides hedging. (jp A3/A6)
7. Show-don't-tell: replace adjectives with the number/multiplier. (IBA)
8. Banned-phrase blocklist DEFAULT-ON: JP (いかがでしたでしょうか/近年注目/全角ダッシュ/**残骸/装飾絵文字) + EN (Here's the thing/dive deep/Thanks for reading/-ly/em-dash).
9. Noun-phrase headings not propositions; rhythm variance (length/tone); two items beat three. (jp B7/B9)
10. Adversarial fresh-eyes loop (= VSDD gate): skeptical first-reader marks each claim pass/revise; 5-axis score <35/50→rewrite; final = 音読.

## OUR three differentiators to BUILD (no skill has these)
- beginner/no-jargon calibration (audience = total beginner, not expert)
- real Firecrawl/ctx7 citation fetching (HARD RULE 0.23 — never WebSearch)
- JP-first, zero English-leakage (verbatim_blacklist-style guard)

## Process (VCSDD)
topic+angle → Firecrawl/ctx7 research (cited) → outline (reverse-outline check) → DO/TEST the thing yourself
(real run, real numbers — never superficial) → draft JP (beginner, de-slop default-ON) → adversarial gate
(fresh-context reviewer: slop? claims sourced? jargon? English leak? 5-axis<35→rewrite) → 音読 → EN translate
→ self-score → post (note/Zenn/dev.to/X). Rename target: existing AI-entity/article writer → `article-writer`.
