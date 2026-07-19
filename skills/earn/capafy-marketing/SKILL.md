---
name: capafy-marketing
description: >
  Capafy marketing loop (Loop B) — drive traffic to Capafy skill listings across social.
  Reuses the clip engine's parts. This dir currently holds B5 (the X poster); B1-B4
  (selector / content adapter / video / IG poster) land here too as they are built.
metadata:
  loop: B (marketing) — sibling of the clip earn loop; instance-separated via ANICCA_INSTANCE=capafy
  status: IG landing attribution implemented. X scripts described in historical notes are not present.
---

# capafy-marketing

> **Current-files note (2026-07-19):** `scripts/x_post.py`,
> `scripts/x_post_browser.py`, `scripts/x_metrics.py`, and
> `scripts/x_attribution.py` are **not implemented in this directory**. References to
> them below describe the historical X-line design only and must not be treated as
> runnable commands. The implemented attribution rail is the IG landing redirect
> plus `scripts/pull_attribution.py` described below.

Marketing arm that promotes online (status=4) Capafy listings. The link-placement rule
is web-researched: **IG/TikTok comment URLs are not clickable and link-in-body is
down-ranked on X → bio-led on IG, and on X the link goes in the FIRST self-reply, never
the root tweet.** (research MD: `anicca-project/docs/earn/2026-07-17-capafy-marketing-link-placement-research.md`)

## Historical pipeline (X line, not runnable here): B1 select → B2 copy → B5 post

```
select_listing.py         # B1: pick an online listing (rotation/dedup), emit {agent_id,name,desc,url}
   → agent writes copy    # B2: the running LLM writes the native tweet + reply CTA from name+desc
   → x_post.py            # B5: validate (no-link native, <=280) + post the 2-tweet self-thread
```

## B1 — promotion selector (`scripts/select_listing.py`)

Deterministic TOOL, no LLM. Reads seller `GET /agent/agents` (no buyer token; 200-verified,
21 online / 26 total), keeps `agentStatus=="online"`, and picks the listing promoted
least-recently (rotation + dedup) via `~/.openclaw/state/capafy-marketing-rotation.jsonl`.
Emits `{ok, agent_id, name, desc, sales, rating, url, online_pool}`. URL = `https://capafy.ai/agent/<id>`.
Verified 2026-07-18: 3 consecutive runs picked 3 different online listings (rotation works).

## B2 — per-listing copy (agent judgment, NOT a hardcoded template)

The running agent reads the selected listing's `name`+`desc` and **writes** the X copy itself:
- native tweet: value-first, <=280 chars, **no link** (X down-ranks link-in-body)
- reply CTA: a short line; `x_post.py` appends the UTM-tagged listing URL

There is deliberately NO copy-generation script — copy is the model's judgment (skill = TOOL,
decision = model). `x_post.py` is the validator/assembler: it rejects a native tweet with a link
or over 280 chars, so a bad draft fails closed. Verified 2026-07-18: selector → agent-written
258-char native tweet → `x_post.py --draft` passed validation and created a Postiz draft (deleted after).

## B5 — X poster history (`scripts/x_post_browser.py` is not implemented here)

★ **`x_post_browser.py` is the rail to use.** `x_post.py` (Postiz) is kept only for reference —
Postiz strips every URL, so the reply link never reaches X (see the Postiz block below). ★

Browser-direct drives the CloakBrowser daily-driver (:9222) to post as the logged-in X account
(**phase 1 = @aniccaen**; @diceai0 was rejected 2026-07-18 — its browser login hits an X phone
-verification wall, and no-human-loop forbids relaying Dais's phone). Flow: compose/post →
insert root (no link) → addButton → insert reply (`Try the skill here: <UTM url>`) → Post all
→ read back the two /status/ URLs.

```bash
set -a; . ~/.openclaw/.env; set +a
# DRY (fills the thread, does NOT post — proves the flow):
python3 scripts/x_post_browser.py --url "<listing url>" --tweet "<native, no link>" --reply "Try the skill here:"
# LIVE (posts the thread as @aniccaen):
python3 scripts/x_post_browser.py --url "<url>" --tweet "<...>" --live
```

**VERIFIED live 2026-07-18**: posted a real thread as @aniccaen (root = Lead Magnet Generator native
tweet, no link / reply = `t.co` link). Logged-out (no auth) the reply's t.co resolved to
`capafy.ai/agent/…/8875030146?utm_source=x&utm_medium=x_reply&utm_campaign=capafy_marketing`, HTTP 200.
root=status/2078252761314115657, reply=status/2078252762740195344.

**@aniccaen cadence rules** (it is shared with article-daily/x-publish): 1 Capafy thread/day max; do
NOT post near an existing article post (space by hours); each post is time-stamped in
`~/.openclaw/state/capafy-marketing-rotation.jsonl`. Do NOT overwrite the profile Website (already set);
the reply URL is the primary CTA.

## B5 historical Postiz poster (`scripts/x_post.py` is not implemented here)

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

## B6/B7 X-line history (the named X scripts are not implemented here)

- **B6 `scripts/x_metrics.py` (not implemented)** — was designed to read views/replies/reposts/likes/bookmarks off each posted
  thread's PUBLIC tweet (browser-direct, :9222) into `capafy-marketing-metrics.jsonl` (time-series).
  Verified 2026-07-18: captured views=3, replies=1 on the first live thread.
- **B6 reflect** — SKELETON in the daily prompt (STEP6): no-op until 7+ distinct threads, then the
  agent leans next copy toward above-median-views winners (clip REFLECT / above-avg gate). Fires
  naturally once data accrues.
- **B7 `scripts/x_attribution.py` (not implemented)** — was designed as a 7-day date-window candidate join of posts × Capafy sales into
  `capafy-attribution.jsonl`. ★HONEST LIMIT: Capafy sales/trend is per-day aggregate (no per-listing
  granularity) → this is a CANDIDATE signal, never proof a post drove a sale. UTM (utm_medium=x_reply)
  is embedded so the join tightens once Capafy exposes per-listing/UTM data. Verified: empty join (0
  candidates) while sales ~0 = correct.
- These historical X scripts are not wired into the daily caller because the files do not exist.

## Implemented IG landing attribution

`build_landing.py` links every online listing card to `/go/<agent_id>`. The Netlify
Function records one immutable Netlify Blob per valid click and redirects to the
Capafy listing with the Instagram bio UTM parameters. `/go-stats` returns cumulative
counts. Immediately after `ig_metrics.py`, the daily caller runs
`scripts/pull_attribution.py` non-fatally; it joins those counts to the current
`GET /agent/agents` sales snapshot and appends at most one dated row per day to
`~/.openclaw/state/capafy-attribution.jsonl`.

## Dependencies / open items
- Capafy listing URL resolution + rotation = B1 (selector). Capafy user token `CAPAFY_ACCESS_TOKEN`
  was expired (401, 2026-07-18) — B1/A-side must refresh it before the selector can query listings.
- B4 (IG poster) should use `ig-reels-poster` (browser-direct), NOT instagrapi — see B0 spec note.
