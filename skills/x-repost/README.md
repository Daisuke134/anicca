# x-repost — daily X quote-tweet loop

One pass a day, driven by launchd, publishing at most one quote tweet from **@selawmqt**
(sela | AI Tools — an AI-owned account, never a personal one).

X is both the only source and the only destination. Nothing is read from HN/Reddit/RSS and
nothing goes through the X API, which has had no free tier since February 2026. Every read and
the publish itself run through one leased CDP browser.

## One pass

| # | Step | Where |
|---|------|-------|
| 0 | CEO registry + budget gate; refuse a second post the same day | `lib/registry-enforce.sh`, `state/posted.jsonl` |
| 1 | Lease the dedicated browser (`x:anicca`), restoring the session from `TWITTER_AUTH_TOKEN` if it lapsed | `~/anicca/skills/browser/ensure_provision_browser.sh` |
| 2 | Scrape live search results for every query | `scripts/x_collect.py --mode recon`, `config/queries.txt` |
| 3 | Refresh engagement on past posts; the best 5 of the last 10 become this pass's few-shot | `scripts/x_collect.py --mode engagement` |
| 4 | Pick ONE post and draft 3 comments (funny / empathy / primary-source) | `codex exec --model gpt-5.6-luna` with `max` effort, `config/voice.md` |
| 5 | Strip the AI register — **a separate call, style only, content frozen** | `codex exec --model gpt-5.6-luna` with `max` effort, `config/humanize-checklist.md` |
| 6 | Choose the one to publish | `codex exec --model gpt-5.6-luna` with `max` effort |
| 7 | Publish, then read the permalink back off the timeline | `scripts/x_post.py` |
| 8 | Append the row, report to Telegram, record the cost estimate | `state/posted.jsonl`, `bin/record-cost-event.sh` |

Selection is the model's judgment, never a regex. Personal attacks, harassment, political
conflict and incident-driven pile-ons are excluded at step 4 by instruction; if nothing is worth
quoting the pass reports why and publishes nothing.

## Why it has its own browser

The interactive daily-driver holds **no** x.com session — measured 2026-08-17, `x.com/home`
redirects to the logged-out landing page. So this loop owns `x:anicca`
(`~/.cloak/profiles/x-repost-daily`, registered in `~/.config/ai/registry/browsers.toml`) and
restores the session from the stored `auth_token` cookie. It never touches the interactive or
gig profile, and it reaches the browser only through `browser-guard.sh`, never a raw port.

## Evidence

Every pass writes `state/evidence/<pass_id>/` — the candidate set, all three prompts, the raw
model output, the published text and the publish result. `state/posted.jsonl` is the ledger the
CEO registry points at; a row exists only when a permalink was read back.

## Where it runs from

launchd points at **`~/profitable-claude/.worktrees/x-repost/`**, not the main checkout, for the
same reason the gig pass does: the main tree follows whatever branch someone is working on, and a
`git checkout` there deletes this skill out from under a scheduled job (that happened once during
the build, 2026-08-17). The runtime worktree stays pinned to `feature/x-repost-loop`, so the daily
pass is immune to branch changes. `state/` — including `posted.jsonl` — lives inside that worktree.

## Run

```bash
W=~/profitable-claude/.worktrees/x-repost/skills/x-repost
bash $W/x-repost-cli.sh          # one pass, then exit
bash $W/x-repost-healthcheck.sh  # schedule + heartbeat check
launchctl kickstart gui/$(id -u)/ai.anicca.x-repost-pass   # fire now, do not wait for 10:25
```
