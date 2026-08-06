# Marketing Engine — the shared distribution OS

**One engine. Many loops. You never reinvent distribution.**

**Status: migration in progress.** The target is one engine, but production is still split across Life Manager, profitable-claude, and anicca-dais/OpenClaw. Do not interpret this README as proof that a listed capability has already cut over; Spec 27 and live scheduler/dependency evidence decide that.

## Repository map and current SSOT

This directory is the **target canonical home**. Do not build a second shared engine here without first importing the proven pieces that already exist elsewhere.

| Source | What exists there now | Rule |
|---|---|---|
| `~/profitable-claude/marketing/engine/` | product/channel/slice registry, contracts, producer adapters, bounded learning, canary/weight-consumption receipts, dashboard CLI | Absorb and preserve these contracts here; do not reimplement them |
| `~/.openclaw/` (`anicca-dais`) | live cron store, Larry/ReelClaw/watercolor/monk scripts and assets, Postiz identities, histories and legacy state | Treat as live migration input; never disable in bulk or infer account mapping |
| `~/anicca/skills/earn/marketing-engine/` | target registry, truth plane, attribution, reporting, scheduler inventory, publisher/metric adapters | Becomes the only runtime SSOT after account-by-account handoff |

Full mapping and cutover order: `../../../specs/27-MARKETING-ENGINE-END-TO-END.md` §§6 and 15.6. During migration, references to `~/profitable-claude` and `~/.openclaw` are explicit debt, not permission to add new dependencies.

Every marketing loop (capafy, clip, and every future product) ultimately runs on this ONE shared engine.
The completed engine owns all the hard, dangerous, already-solved work — creating IG accounts that survive,
warming them, posting durably, measuring reach, self-improving, reporting. A loop is just a
**manifest**: the 4 things that are actually different per product.

## To launch a new marketing loop, you decide ONLY 4 things

| You decide | Manifest key | Example (capafy) |
|---|---|---|
| **WHO** (persona) | `MKT_PERSONA` | devs who want ready-made Claude skills |
| **WHAT PROBLEM** | `MKT_PROBLEM` | building an AI skill from zero is slow |
| **WHAT you sell** (product) | `MKT_PRODUCT_SOURCE` / `MKT_LISTING_URL_FMT` / `MKT_BIO_LINK` | capafy `/agent/agents` listings |
| **HOW** (content) | `MKT_CONTENT_ADAPTER` | `faceless-video` (or slideshow / carousel / clip-cut) |

Everything else — account creation, warmup, posting, reach, self-improve, telegram — is the
shared engine. **Do not copy or re-implement it. Copy a manifest.**

## How to add a loop

1. Copy `manifests/capafy.manifest.sh` → `manifests/<yourproduct>.manifest.sh`, edit the values.
2. (soon: `new-marketing-loop <yourproduct>` registers the launchd job automatically.)
3. Done. The engine provisions an account, warms it, and posts your content on the shared,
   hardened distribution.

## The hard-won invariants baked into the engine (never re-learn these)

- **Account lifecycle**: day1 = signup + profile ONLY (no instagrapi login — a day-1 account is
  too young, private-API login is always rejected). Warm day1–2 via browser. **Day3**: establish
  the ONE golden instagrapi session (`Client().login` now accepted, aged) → `dump_settings`.
  **Never relogin after** — a relogin trips bloks `ChallengeRequired` = poison. Post from day3.
- **Status vocabulary (SSOT)**: `warming_day1` and `warming` mean the account is still warming;
  both are usable for the provision counter but are not eligible to post. `ready` means posting
  is allowed. Any poisoned status or poison marker excludes the account. Provisioning therefore
  counts non-poisoned `warming*`/`ready*`, while posting selection remains strictly `ready` only.
- **Browser isolation**: every loop leases its OWN isolated context on the shared `:9222`
  daily-driver via `cdp_context_lease.py` (never the raw default context — that churns other
  loops' tabs and poisons accounts). Each account gets a dedicated port (never 9222/9223).
- **Poster**: `poster.py` (tier1 saved session). One poster for every loop. The web
  composer (`post_reel.py`) is a dead end — IG silently drops automated web-composer posts.
- **Reach is the real shadowban test**; near-zero views across posts = cooked → provision fresh.
- **Poison detection only on day3+ accounts** (a young account failing instagrapi is expected,
  not poison — don't false-cook it).

## Two lanes today, one lane as the goal (measured 2026-07-30)

The earlier claim that Postiz was cancelled is **wrong**: the API answers and lists
**29 live integrations** (16 TikTok, 7 Instagram, 3 YouTube, 1 X), and `anicca-larry`
publishes through it. So there are two lanes right now:

| Lane | Used by | Status |
|---|---|---|
| **agent-owned** — engine creates the account, warms it, posts via `poster.py` (instagrapi) | Instagram (clip, capafy) | the target design |
| **Postiz API** (`POSTIZ_API_KEY`) | TikTok, YouTube, X | load-bearing; cutting it now kills 19 accounts |

Postiz is kept deliberately until the free lanes are green. It cannot ship to other
Life Manager users (one owner's accounts, one paid seat), so it is a temporary bridge,
not the design. Note the free replacement for TikTok is **not** the official Content
Posting API — an unaudited client can only post privately and the audit is a human
review — it is agent-owned accounts plus browser/session upload, exactly like IG.

| `MKT_CONTENT_ADAPTER` | Instagram media | `poster.py` route |
|---|---|---|
| `faceless-video` | Reel | instagrapi `clip_upload` |
| `clip-cut` | Reel | instagrapi `clip_upload` |
| `slideshow` | Carousel | instagrapi `album_upload` |
| `carousel` | Carousel | instagrapi `album_upload` |

Monetization assets are a separate check: a loop may only go live with revenue links the
agent owns (an affiliate tag owned by a human must be replaced before live).

## Files

| File | Role |
|---|---|
| `provision_prompt.sh` | shared account-creation prompt (parameterized by manifest) |
| `account_state.sh` | resolve active handle/port from a loop's account state file |
| `load_manifest.sh` | `me_load_manifest <name>` → export `MKT_*`, validate required keys |
| `manifests/*.manifest.sh` | per-loop config (the ONLY thing that changes) |
| `poster.py` | shared instagrapi poster (tier1 saved session), one poster for every loop |
| `warmer.py` | deterministic WARM step; establishes the golden instagrapi session on day3 |

## Where a loop's own code lives

A loop keeps only what is genuinely unique: its selector (what to promote), its copy/voiceover
judgment, and its content adapter (how the video/slideshow is built). Everything else is here.

**Target**: proven shared-engine contracts migrate **from** `profitable-claude` and live producer/account inputs migrate **from** `anicca-dais/OpenClaw` into this directory. A product becomes a manifest and asset pack; local launchd and cloud workers execute the same engine. No second scheduler or product-specific engine is created.
