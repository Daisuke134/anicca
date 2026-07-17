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
- Verified 2026-07-18: draft post accepted by Postiz (2-tweet thread), ledger row written, draft deleted after check.

**Wiring (B8, not yet done):** a daily production cron calls this with `--live` on a B1-selected
listing. Do NOT wire `--live` to a cron until the copy pipeline (B1/B2) feeds real per-listing tweets.

## Dependencies / open items
- Capafy listing URL resolution + rotation = B1 (selector). Capafy user token `CAPAFY_ACCESS_TOKEN`
  was expired (401, 2026-07-18) — B1/A-side must refresh it before the selector can query listings.
- B4 (IG poster) should use `ig-reels-poster` (browser-direct), NOT instagrapi — see B0 spec note.
