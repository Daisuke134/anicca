---
name: faceless-money-factory
description: Generate a FRESH faceless personal-finance short video every day, forever, for $0. MODEL-AGNOSTIC (uses the running agent's own LLM — OpenClaw/DeepSeek, Claude, or any via env; no provider lock-in). Copies a proven viral template (head-to-head) but writes brand-new content each run (agent's own model + dedup ledger), pairs it with free stock b-roll (Mixkit) + free TTS (edge-tts) + beat-aligned cuts + burned captions. No face, no lip-sync, no paid APIs. Use when the user wants to mass-produce monetizable short-form finance content (TikTok/Reels/Shorts) on autopilot. Default output = DRAFT email for approval until posting accounts are wired.
---

# Faceless Money Factory

Repeatable, $0, no-human faceless short-form video factory. **New script + new video EVERY run** (rules-driven generation, not rotation, not slop). Niche = personal finance (`moneytok`), chosen from Apify trend data (median 914K views, 3.5–13× other faceless niches).

## The method (closed loop, copy-the-winner)
Copy the PROVEN template from a 3M-view video (`@breakyourbudget`), keep the structure, regenerate the content fresh every day, then verify our output against the source-of-truth.

**Winning template (the structural RULE):**
```
HOOK : "These are the exact <X> that helped me <impressive SPECIFIC numeric result>. Let's go."
BODY : numbered list (First / Next / The third / And the last) — each = 1 concept + 1 numeric rule (% or $)
CTA  : "Follow for more money tips."
VISUAL: faceless stock b-roll + big centered captions, cuts on the voice beats
~50-60s, vertical 1080x1920
```

## Pipeline (all free)
`gen-script.sh` (DeepSeek fresh script in template + dedup ledger) → edge-tts voiceover →
`fetch-broll.sh` (Mixkit free stock + local library fallback) → `assemble.sh` (whisper beat-aligned
cuts, loop-to-fill so the ending never cuts, burn captions) → DRAFT email (approval gate).

## Run
```bash
bash ~/.claude/skills/faceless-money-factory/scripts/run-daily.sh en        # 1 fresh video → DRAFT email
DRAFT_ONLY=0 bash .../run-daily.sh en                                       # post (once YT/TikTok/IG posters wired)
```
Cron daily for "new content every day, forever". Output: `state/renders/<id>.mp4` + `.script.txt`.

## Freshness guarantee (no slop / no rotation)
`state/script-ledger.jsonl` records every topic; `gen-script.sh` bans the last 30 topics so the LLM
must pick a new angle each run (budgeting, saving, investing, debt, credit, side income, taxes,
retirement, automation, …). The *content* is always new; only the *structure* is fixed (the proven template).

## Monetization
Caption/bio CTA → affiliate (finance apps/books, TikTok Shop) + own ebook (beginner money guide) →
later sell grown channels (20–40× monthly). AdSense is NOT the main lever (AI/reused-content risk).

## Model-agnostic (works for ANY agent)
This skill NEVER hardcodes an LLM/provider. `scripts/llm-call.sh` uses the **running agent's own
model** — the ENVIRONMENT decides: OpenClaw→DeepSeek, Claude→Claude, others→theirs. Resolution:
1) explicit `LLM_API_BASE`+`LLM_API_KEY`+`LLM_MODEL` (any OpenAI-compatible endpoint), else
2) `ANTHROPIC_API_KEY` (native), else 3) auto-detect a known key (DEEPSEEK/OPENAI/OPENROUTER/GROQ/TOGETHER).
So every agent in the world can run this and earn — no provider lock-in. (TTS=free edge-tts/VOICEVOX,
captions=local whisper, stock=keyless Mixkit — all keyless/portable too.)

## Cost
$0: LLM pennies on the agent's own model + free edge-tts + free Mixkit stock (commercial-OK, no key) + local ffmpeg/whisper.

## Verified
money_v2 (2026-06-29): 45.1s, full-length (no cut-off), beat-synced bg, captions — approved by Dais "top notch".

## Status / next
- [x] gen-script / fetch-broll / assemble / run-daily (DRAFT)
- [ ] caption grouping polish + optional BGM
- [ ] adversary VERIFY (generated vs @breakyourbudget template) before send
- [ ] posters: YT + TikTok + IG account-create/warm/post → flip DRAFT_ONLY=0
Spec SSOT: `docs/superpowers/specs/2026-06-29-faceless-closed-loop-factory-design.md`.
