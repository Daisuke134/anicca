---
name: capafy-marketing
description: >
  Capafy marketing loop (Loop B) — drive traffic to Capafy skill listings across social.
  Reuses the clip engine's parts. This dir currently holds B5 (the X poster); B1-B4
  (selector / content adapter / video / IG poster) land here too as they are built.
metadata:
  loop: B (marketing) — sibling of the clip earn loop; instance-separated via ANICCA_INSTANCE=capafy
  status: B5 (X poster) BUILT + draft-verified 2026-07-18. B0 IG account @useclaudeskills warming.
---

# capafy-marketing

Marketing arm that promotes online (status=4) Capafy listings. The link-placement rule
is web-researched: **IG/TikTok comment URLs are not clickable and link-in-body is
down-ranked on X → bio-led on IG, and on X the link goes in the FIRST self-reply, never
the root tweet.** (research MD: `anicca-project/docs/earn/2026-07-17-capafy-marketing-link-placement-research.md`)

## B5 — X poster (`scripts/x_post.py`)

Posts a listing to X via **Postiz** (integration `POSTIZ_X_INTEGRATION_ID`, account アニッチャ)
as a 2-tweet self-thread:

| tweet | content |
|---|---|
| 1 (root) | native value post, **NO link** (X down-ranks link-in-body) |
| 2 (self-reply) | short CTA + the Capafy listing URL, UTM-tagged `utm_source=x&utm_medium=x_reply&utm_campaign=capafy_marketing` (B7 attribution) |

A multi-element Postiz `value` array IS a native X self-thread (`value[0]`=root, `value[1]`=reply).

**This is a deterministic TOOL — it never calls an LLM.** The agent (or the B1 selector)
writes `--tweet`; the script only does the Postiz posting + ledger. Copy is input, not invented here.

```bash
set -a; . ~/.openclaw/.env; set +a      # POSTIZ_API_KEY + POSTIZ_X_INTEGRATION_ID
# DRAFT (default) — creates a real Postiz draft, publishes NOTHING to the live feed (E2E test):
python3 scripts/x_post.py --url "<capafy listing url>" --tweet "<native value tweet, no link>" --reply "Try the skill here:"
# LIVE (production cron only) — type:now, publishes to X:
python3 scripts/x_post.py --url "<url>" --tweet "<...>" --live
```

- Guardrails: rejects a native tweet that contains a link or exceeds 280 chars.
- Output: one clean JSON line on stdout `{ok, mode, listing_url, tagged_url, post_id, release_url}`.
- Ledger: appends to `~/.openclaw/state/capafy-marketing-x-ledger.jsonl` (atomic).
### ★ BLOCKER — Postiz strips all URLs (verified live 2026-07-18, 5 tests) ★
The root native tweet publishes correctly, but **Postiz removes every URL from tweet content**,
so the self-reply link never reaches X. Verified across text+url reply / url-only reply /
single-tweet-body url / shortLink true AND false / SPA url (capafy.ai) AND known-good url
(github.com) — the Postiz `content` field comes back with the URL deleted every time, and the
live tweet on X has no link. This is a Postiz-rail limitation, NOT a code bug and NOT X
account link-stripping (the URL is gone before it reaches X).

Also corrected: the Postiz integration named アニッチャ (`cmm6d7m5..`) posts to **@diceai0**,
NOT @aniccaxxx as `~/.openclaw/skills/x-poster/SKILL.md` claims.

**Fix path (needs a rail decision by lead):**
1. Browser-direct — drive X compose on CloakBrowser :9222 to post root + reply-with-link
   (same pattern as `ig-reels-poster`). Most reliable, bypasses Postiz. Needs @diceai0 (or a
   chosen X account) logged into :9222.
2. X API v2 (OAuth) — post + reply via api.x.com with the account's tokens.
3. Interim degraded — native posts via Postiz + the Capafy link only in the X Profile Website
   (research MD says the profile link is a permanent secondary channel).

**Do NOT wire `--live` to a cron** until the rail is switched — it would post link-less tweets.

## Dependencies / open items
- Capafy listing URL resolution + rotation = B1 (selector). Capafy user token `CAPAFY_ACCESS_TOKEN`
  was expired (401, 2026-07-18) — B1/A-side must refresh it before the selector can query listings.
- B4 (IG poster) should use `ig-reels-poster` (browser-direct), NOT instagrapi — see B0 spec note.
