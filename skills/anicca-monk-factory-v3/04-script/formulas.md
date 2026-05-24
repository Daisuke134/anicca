# Script Formulas & Structure — derived from 10 REAL Yang Mun viral videos

This OVERRIDES the article-based §12 of the spec (which said 20–40s / emotional
reframe). The real winners are 77–123s health/wisdom listicles + rituals + reveals
with a comment-keyword CTA and an OCCASIONAL product link. Copy this exactly,
spoken as **Ajahn Sutta** (body + mind, our voice/face).

## Length
**75–120 seconds** (target ~90s). Not 20–40s.

## The 5 formats (ranked by how often they hit, from the 10 videos)

| rank | format | hook shape | use for |
|---|---|---|---|
| 1 | **LISTICLE / SIGNS** | "N signs your [X] is [warning]" | sugar/kidneys/feet → ours: "5 signs your mind is quietly exhausted", "5 signs your body never truly rests" |
| 2 | **MORNING/NIGHT RITUAL** | "Do this every morning/night and your [X] will change" | hot water/garlic/3 foods → ours: "drink this before bed", "do this one thing every morning" |
| 3 | **REVEAL / MYTH-BUST** | "They lied to you / The #1 [X] is NOT [obvious]" | watercress/black-seed-oil → ours: "they told you to empty your mind. they lied." |
| 4 | **REFRAME** (secondary) | "If you're going to [habit]… [redirect]" | emotional, calm topics |
| 5 | **VALIDATION** (secondary) | say what they already feel | loneliness/letting go |

## The mandatory structure (present in ~10/10) — every script obeys this

```
1. HOOK (0–3s)      number + bold claim / curiosity / fear / "they lied"
                    e.g. "Five signs your mind is quietly exhausted, my friend."
2. RETENTION (3–6s) "Listen carefully." / "Stay until the end —
                    you may not find this again when you need it most."
3. AUTHORITY        "I am Ajahn Sutta. For fifty years I have watched
                    the body and the mind, in silence." (vary / sometimes light)
4. BODY (the bulk)  numbered signs/steps OR one reveal. EACH wrapped in a
                    POETIC NATURE MECHANISM, never clinical:
                    "the rivers of your blood", "the inner fire", "vessels open
                    like rivers after winter", "the body speaks in whispers
                    before it screams", "your body never lies".
5. ONE TURN         one clear takeaway / one thing to do tonight.
6. CTA (engagement) "Comment [KEYWORD] below" + "share with someone who [pain]"
                    + "follow me, my friend". KEYWORD ideas: PEACE, STILL,
                    BREATHE, ENOUGH, BALANCE.
7. PRODUCT (OCCASIONAL — ~1 in 5, or proven winners only)
                    soft line to ebook/app in bio. NOT every video (scam-feel).
```

## 🔴 THE #1 RULE — every script ends with a SPECIFIC NAMED ANSWER (Dais 2026-05-22)
Yang Mun's win core = he always NAMES the concrete thing: watercress, black seed
oil, milk thistle, the 4-7-8 breath, "drink warm water with 3 cloves of garlic."
He never ends abstract. **We copy this exactly.** Every Anicca script — body OR
suffering — must give one specific, named, do-it-tonight answer. No poetic-only
endings, no "just let go" with nothing concrete. If the viewer can't DO a named
thing after watching, the script fails.

## 🔴 TWO CONTENT TRACKS (alternate / both daily) — both obey the #1 rule
| track | domain | what it copies | example specific answer |
|---|---|---|---|
| **T1 — BODY/WELLNESS** | sleep, energy, digestion, calm body, aging | Yang Mun direct | the 4-7-8 breath; warm water before bed; magnesium for night cramps; "5 signs your body never rests" |
| **T2 — SUFFERING / MIND** | attachment, letting go, anger, overthinking, peace (Anicca core) | Yang Mun FORMAT, Anicca soul | a named 3-question release practice; "name it, thank it, set it down"; a specific 2-minute sit; the "one hour" experiment |
- Copy faithfully ("really inspired"). T2 must be just as CONCRETE as T1 — Dais: "even the reducing-suffering ones should be specific answers."
- Alternate tracks across the daily slots so the account is both viral-health AND Anicca's real mission.

## House rules (copied + adapted)
- Catchphrase **"my friend"** in hook or close. Closing release **"…and that is enough."**
- Poetic nature imagery is non-negotiable — it IS the brand texture (anicca/river/leaf/fire/breath).
- Hedge health claims Yang-Mun-style: "the old texts say", "may be", "this is not medicine, it is a way." Never diagnose, never promise a cure.
- ONE idea/turn per video even inside a listicle (the list serves one message).
- Body + mind both allowed. Suffering-reduction is the through-line (a tired body is suffering too).
- Suno/face/voice fixed forever. Only the script changes daily.

## CTA / product policy (Dais 2026-05-22)
- DEFAULT cta_mode = `engage`  → comment-keyword + share + follow. NO product mention.
- `product` cta_mode (ebook/app link in bio) only ~1 in 5 videos OR on winners.
- App-link vs ebook = TBD; keep CTA text swappable. An ebook already exists.

## Bank entry schema (04-script/bank_en.jsonl)
```json
{
  "id": "2026-05-22-en-001",
  "format": "listicle|ritual|reveal|reframe|validation",
  "topic_domain": "mind|body|both",
  "pain_point": "can't switch off at night",
  "hook": "Five signs your mind is quietly exhausted, my friend.",
  "script": "…75–120s full text…",
  "keyword": "STILL",
  "cta_mode": "engage|product",
  "duration_est_s": 95,
  "status": "unused"
}
```
