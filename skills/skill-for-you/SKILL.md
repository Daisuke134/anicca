---
name: skill-for-you
description: Profile the user's day from Claude transcripts + zsh history + git diffs across anicca-project / anicca-products, embed into a topic vector, and rank skills from the ClawHub catalog by cosine similarity. Posts a Slack card with the top recommendation and ✅/❌/😴 buttons. Weekly summary on Sunday 09:00 JST. Use when the user says "today's skill" or "おすすめのスキル" or auto-fired by cron skill-for-you-daily 30 9 * * * JST.
metadata:
  tags: skill-discovery, recommendation, embedding, clawhub, daily, weekly-summary
  requires:
    bins: [python3, jq, git]
    python_pkgs: [PyYAML]
    optional_python_pkgs: [sentence-transformers, numpy]
  requires_env: []
  optional_env:
    - SKILL_FOR_YOU_DRY_RUN
    - SKILL_FOR_YOU_DAILY_N
    - SKILL_FOR_YOU_CATALOG_URL
    - SKILL_FOR_YOU_EMBED_MODEL
    - SLACK_BOT_TOKEN
---

# skill-for-you

Anicca's daily "skill recommender". Profiles what you actually did today from
your Claude transcripts, shell history, and git diffs across the two main
repos; embeds that into a topic vector; and ranks the ClawHub catalog by
cosine similarity. Posts the top-N to Slack with install / skip / mute buttons.

## Pipeline (left → right)

```
~/.claude/sessions/*.jsonl ─┐
~/.openclaw/agents/anicca/  │
   sessions/*.jsonl  ───────┤
~/.zsh_history     ─────────┼──► profile-day.py ──► profile-YYYY-MM-DD.json
git diff anicca-project ────┤        │
git diff anicca-products────┘        │
                                     ▼
                  redact.py (uses redact.yaml)
                                     │
                  ┌──────────────────┴───────────────────┐
                  ▼                                       ▼
         match-clawhub.py                       weekly-summary.py
              │                                 (Sunday 09:00 JST)
              ▼
   recommendations-YYYY-MM-DD.json
              │
              ▼  Slack card with [✅ Install][❌ Skip][😴 Mute 7d]
              │
              └──► reaction handler updates installed.json
                   future runs deweight installed/muted slugs
```

## Files

| Path | Purpose |
|------|---------|
| `scripts/profile-day.py`       | Read sources → tokenize → run through redact → embed → write profile JSON |
| `scripts/match-clawhub.py`     | Fetch (or scrape) ClawHub catalog → embed → cosine-rank → exclude installed → write recommendations + post Slack |
| `scripts/weekly-summary.py`    | "Last week recommended N, installed M, valuable K (≥3 triggers)" — Sun 09:00 JST |
| `scripts/redact.py`            | PII / secrets filter applied BEFORE any embedding payload leaves the box |
| `redact.yaml`                  | Ruleset (filenames, regexes, denylist of unreleased product names) |

## Output paths (under `~/.openclaw/workspace/skill-for-you/`)

| File | Written by | Contents |
|------|-----------|----------|
| `profile-YYYY-MM-DD.json`       | profile-day.py    | `{date, sources, redactions_applied, tokens, vector_dim, vector}` |
| `recommendations-YYYY-MM-DD.json` | match-clawhub.py | top-N ranked candidates with 3-sentence pitch, exclude-list applied |
| `installed.json`                | reaction-handler  | `{slug: {action: install|skip|mute, ts, mute_until}}` (deweights future ranks) |
| `weekly-YYYY-WW.json`           | weekly-summary.py | counts + top installed of the week |

## Wizard config (read from `~/.openclaw/openclaw.json` -> `skills.skill_for_you`)

| Key | Default | Purpose |
|-----|---------|---------|
| `skill_for_you.catalog_url` | `https://clawhub.dev/catalog.json` (with fallback to `https://clawhub.dev/skills`) | Where to pull skill catalog. Spec audit notes this API "does not exist yet" — see `match-clawhub.py` fallback list. |
| `skill_for_you.embed_model` | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding model. If the package isn't installed, the script falls back to a deterministic hash-bag-of-words vector (good enough to test the pipeline). |
| `skill_for_you.daily_n`     | `1` | How many recommendations the daily Slack card shows. |
| `skill_for_you.sources`     | `["claude", "openclaw", "zsh", "git"]` | Which inputs to profile from. |
| `skill_for_you.redact_path` | `~/.openclaw/skills/skill-for-you/redact.yaml` | Where the ruleset lives. |
| `skill_for_you.git_repos`   | `["~/anicca-project", "~/anicca-products"]` | Repos to diff. |

## Run commands

```bash
# Daily — invoked by cron skill-for-you-daily (30 9 * * * JST)
python3 ~/.openclaw/skills/skill-for-you/scripts/profile-day.py
python3 ~/.openclaw/skills/skill-for-you/scripts/match-clawhub.py

# DRY_RUN (no Slack post, no remote fetch)
SKILL_FOR_YOU_DRY_RUN=1 python3 ~/.openclaw/skills/skill-for-you/scripts/profile-day.py
SKILL_FOR_YOU_DRY_RUN=1 python3 ~/.openclaw/skills/skill-for-you/scripts/match-clawhub.py

# Weekly — invoked by cron skill-for-you-weekly (0 9 * * 0 JST)
python3 ~/.openclaw/skills/skill-for-you/scripts/weekly-summary.py
```

## Redaction (always-on, BEFORE any embedding payload leaves the box)

`scripts/redact.py` reads `redact.yaml` and removes:

1. Any line matching `_KEY|_SECRET|_TOKEN|_PASSWORD|API_KEY=` (case-insensitive)
2. Any file path under `.env*` or matching `id_rsa|.pem|.p12|.pfx|credentials.json`
3. Any customer-PII pattern ({{profile.lateness.stakeholders.channel}}, phone E.164, US SSN-shape, JP MyNumber-shape)
4. Any unreleased product name from the denylist in `redact.yaml`

Replacements use the literal token `<REDACTED:KIND>` so downstream embedding
sees a stable shape rather than a deletion. Counts are written into the
profile JSON under `redactions_applied`.

## Slack card

Posted to `${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}` (default #metrics):

```
📦 *Today's recommended skill*  (skill-for-you)

[1] <slug>
    💡 <3-sentence pitch>
    score: 0.83  •  similar to: <top-3 your-tokens that matched>

    [ ✅ Install ]   [ ❌ Skip ]   [ 😴 Mute 7d ]
```

## Reaction handler

When the user reacts:

- `✅` → write `installed.json[slug] = {action:"install", ts}` and emit a
  follow-up agentTurn that runs the install command for that ClawHub slug.
- `❌` → `{action:"skip", ts}` — deweighted in next 24h, ranked normally after.
- `😴` → `{action:"mute", ts, mute_until: now + 7d}` — slug excluded from
  ranking until `mute_until`.

Future runs of `match-clawhub.py` filter out anything with a current
`installed | mute` action and downweight `skip` actions for 24 hours.

## Crons

| ID | Schedule | Purpose |
|----|----------|---------|
| `skill-for-you-daily`   | `30 9 * * *` JST | profile-day → match-clawhub → Slack card |
| `skill-for-you-weekly`  | `0 9 * * 0` JST  | weekly-summary → Slack post |

## Open issues / surprises (carried from audit)

- **ClawHub catalog API status:** the formal `catalog.json` endpoint
  doesn't exist yet. `match-clawhub.py` ships with a hardcoded fallback
  list of well-known ClawHub slugs (read from
  `scripts/clawhub-fallback.json`) so the pipeline doesn't break while
  the catalog is being built. When the API ships, set
  `skill_for_you.catalog_url` to the new endpoint — no script changes needed.
- **`~/.claude/sessions/` does not exist on this machine** — Claude Code
  session storage moved. The script reads from `~/.openclaw/agents/<id>/sessions/`
  as the primary source and falls back to `~/.claude/sessions/` if present.
- **`~/.zsh_history`** may not exist if the user runs a different shell —
  the script no-ops that source on missing-file rather than failing.

## Backup / archive

- Pre-rewrite stub: `~/.openclaw/skills/_backups/skill-for-you-stub-<TS>/`
- Old JS scripts (`analyze.js`, `skill-for-you.js`, `utils/slack.js`) remain
  in `scripts/` as deprecation stubs because the sandboxed mount denies
  unlink. They print a notice and exit 1 if invoked.
