---
name: slack-feedback-reader
description: Anicca's INNER LOOP eyes + fixer. Run by the heartbeat every beat (and hourly standalone). Reads its own cron failures + Slack #metrics, verifies with machine signals (verify-gate), and FIXES the broken SKILL.md/cron THIS beat — not log-for-later. Observing without fixing is forbidden (HARD RULE / SOUL MISSION). Outer capture handled by self-improving-agent hook.
---

# slack-feedback-reader — INNER LOOP (detect → verify → fix → recover)

五戒 gate: read `~/.openclaw/workspace/CONSTITUTION.md` first.

## Step 1 — detect (machine signals, never trust Slack text alone)
```bash
python3 -c "
import json
d=json.load(open('/Users/anicca/.openclaw/cron/jobs.json'))
bad=[(j['id'],j.get('name'),j['state'].get('lastError','')) for j in d['jobs'] if j.get('enabled') and j.get('state',{}).get('consecutiveErrors',0)>=1]
print('\n'.join(f'{i} | {n} | {e[:120]}' for i,n,e in bad) or 'ALL_OK')
"
```
Also skim Slack #metrics (channel {{profile.channels.reportChannel}}) last 60 if a Slack read tool is available (slack-digest path); else the cron-state scan above is authoritative.

## Step 2 — verify-gate (real check per cron type — sutando health pattern)
| cron type | verify | pass = |
|-----------|--------|--------|
| article-writer | `curl -s -o /dev/null -w '%{http_code}' https://zenn.dev/anicca/articles/{slug}` | 200 |
| slideshow/reelclaw/mau-tiktok | Postiz GET /posts → state | PUBLISHED/DRAFT-as-intended |
| app-metrics | `jq .status metrics_YYYY-MM-DD.json` | success |
| factory-bp | `ls workspace/factory-evolution/*-YYYY-MM-DD.md` | exists |
| dashboard | `jq .updated_at dashboard-last.json` | today |
Never guess. If verify passes despite Slack noise → it is fine, skip.

## Step 3 — FIX THIS BEAT via the DGM self-improve loop (#34/#35, not later)
DGM (Sakana Darwin Gödel Machine) + SICA — copied, not invented:
1. **READ FIRST** (DGM's most-cited innovation): `.learnings/ERRORS.md` + `ops/improvement-archive.json` — what was tried for this pattern and why it failed. Do NOT repeat a dead variant.
2. **BASELINE**: capture the pre-change measured signal (verify-gate result / `openclaw cron run <id>` exit + output).
3. **OPEN-ENDED, not greedy**: for a non-trivial fix, draft ≥2 candidate variants (different root-cause hypotheses; firecrawl the correct way if unsure — never guess). Path-protected files (CONSTITUTION.md 0444 / keys / wallet) are never eligible.
4. **EVAL-GATE before keep**: apply a variant, `openclaw cron run <id>` to re-verify with a REAL signal. KEEP only if result ≥ baseline (cron passes, no 五戒/ROI regression). Else `git revert` it.
5. **ARCHIVE the attempt** (kept OR reverted) to `ops/improvement-archive.json` with `{variant_id,parent_id,target,commit,baseline,result,decision,why_failed}` + `.learnings/ERRORS.md` Pattern-Key + Recurrence-Count. A reverted variant stays as a stepping stone (never deleted). Recurrence of the same `why_failed` ≥3 → mark that whole approach dead.
6. Max 1 cron deep-fix per beat (precept 5: no heedless batch). Self-mod rate limit = 1 self-edit/beat.

## Step 4 — repentance-continue if unfixable (NOT fail-stop)
Can't fix (external API down / structural) → avow it in `.learnings/ERRORS.md` (Pattern-Key + Recurrence-Count) → keep living, move to next steps.json item this beat. The agent never halts because a cron is broken. **Recurrence ≥3× of the SAME failure is the real failure signal** (not the first occurrence): then escalate to a peer Anicca (GET /status → POST /task); only true external blockers → Slack #metrics SOS Dais. A pending unfixed cron = a degraded state to keep improving across beats, never a stop.

## Step 5 — report
`👂 inner: <N> failing · <F> fixed · <P> pending · <E> escalated`

## Never
- Never observe-and-leave. Detection = fix attempt THIS beat.
- Never fail-stop the agent because a cron failed — fix it or carry it as a tracked degraded state and keep living (graceful-degradation, see CONSTITUTION "When a precept IS violated").
- Never publish to X/TikTok/IG during a fix/test (HARD RULE #9 — draft only).
- You are the model (HARD RULE #6).
