---
name: faceless-money-factory
description: Generate a FRESH faceless personal-finance short video every day, forever, for $0. AI-AGNOSTIC — ANY agent runs it with its OWN model; the skill calls NO LLM API and names NO provider (you, the agent, write the script in natural language; deterministic scripts do TTS + stock b-roll + captions + assembly). Copies a proven viral template (head-to-head) with brand-new content each run. No face, no lip-sync, no paid APIs, no keys. Use to mass-produce monetizable short-form finance content (TikTok/Reels/Shorts) on autopilot. Default output = DRAFT email for approval until posting accounts are wired.
---

# Faceless Money Factory

Repeatable, $0, **AI-agnostic** faceless short-form video factory. Any AI agent (DeepSeek on OpenClaw, Claude, anything) runs this with its own model. **New script + new video EVERY run.** Niche = personal finance (`moneytok`) — highest faceless reach (Apify: median 914K views, 3.5–13× other niches).

## How it works (you = the agent = the model)
This skill is **natural-language instructions + deterministic tools**. There is **no LLM call inside the skill** — YOU write today's script yourself (you're already a model), then run the tools. That's what makes it AI-agnostic: nothing to configure, no provider, works for any agent on earth.

### Step 1 — YOU write today's fresh script (natural language, your own model)
1. Read recent topics so you never repeat: `tail -30 state/script-ledger.jsonl` (each line `{"topic": "..."}`).
2. Pick a NEW personal-finance angle not in that list (budgeting, saving, investing, debt payoff, credit, side income, taxes, retirement, no-spend, automation, …).
3. Write the script **copying this proven template** (it got 3,000,000 views — keep the structure, make the content new):
   ```
   HOOK : "These are the exact <X> that helped me <impressive SPECIFIC numeric result>. Let's go."
   BODY : numbered list (First / Next / The third / And the last) — each item = ONE concrete concept + ONE actionable numeric rule (a % or $ figure)
   CTA  : "Follow for more money tips."
   ```
   Rules: strong specific hook with a number; exactly 4 list items; ~110–150 words; natural spoken voiceover; NO emojis, NO hashtags. Source of truth to match: `@breakyourbudget`.
4. Save it to a file, e.g. `state/today.txt`, and append the topic to the ledger:
   `printf '{"topic":"<your topic>"}\n' >> state/script-ledger.jsonl`

### Step 2 — run the deterministic pipeline
```bash
bash scripts/run-daily.sh state/today.txt en
```
This does (no LLM, all $0/keyless): free TTS (edge-tts) → free stock b-roll (Mixkit) → beat-aligned cuts (whisper) + burned captions → 1080×1920 mp4 → DRAFT email for approval.
Post instead of draft (once YT/TikTok/IG accounts wired): `DRAFT_ONLY=0 bash scripts/run-daily.sh state/today.txt en`.

## Why AI-agnostic matters
The whole thesis: every AI on earth (self-funded or human-funded) can run this and earn. So the skill must never depend on a specific model/provider/key. The judgment (the script) is done by the running agent's own intelligence in natural language; only the mechanical work (TTS/ffmpeg/whisper/stock download) is scripted. (See `feedback_every_skill_must_be_model_agnostic`.)

## Freshness guarantee (no slop / no rotation)
`state/script-ledger.jsonl` records every topic; Step 1 bans the recent ones, so each run is a genuinely new angle. Content always new; only the proven structure is fixed.

## Monetization
Caption/bio CTA → affiliate (finance apps/books, TikTok Shop) + own ebook (beginner money guide) → later sell grown channels (20–40× monthly). AdSense is NOT the main lever (AI/reused-content risk).

## Cost
$0: your own model (no extra spend) + free edge-tts + free Mixkit stock (commercial-OK, keyless) + local ffmpeg/whisper.

## Verified
money_v2 (2026-06-29): 45.1s, full-length (no cut-off), beat-synced bg, captions — Dais "top notch". Pipeline run E2E with fresh topics each run.

## Next
- [ ] optional: caption-grouping polish + BGM
- [ ] adversary VERIFY (generated vs `@breakyourbudget` template) before send
- [ ] posters: YT + TikTok + IG account-create/warm/post → flip `DRAFT_ONLY=0`
Spec SSOT: `docs/superpowers/specs/2026-06-29-faceless-closed-loop-factory-design.md`.
