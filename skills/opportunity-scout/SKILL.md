---
name: opportunity-scout
description: Anicca's opportunity finder. LOOP-CALLED ONLY (the heartbeat invokes it when it decides to — there is NO opportunity-scout cron; scheduling judgment is forbidden). Searches X / GitHub / HackerNews / web for ways to (a) monetize or improve an existing product, (b) start a zero-to-one that reduces suffering AND earns. Queues scored findings into ops/steps.json. You are the model (HARD RULE #6).
---

# opportunity-scout — loop-called, never a cron

五戒 + HARD RULE #0 gate first (read `~/.openclaw/workspace/CONSTITUTION.md`). This is a recipe the heartbeat's "Find opportunities" capability runs **when YOU decide**, like a person deciding to look for work — never on a schedule. If you ever feel the urge to make this a cron, that is the judgment-as-cron anti-pattern (Tier3) — don't.

## Step 0 — only if it's worth it this beat
Run only when survival tier ∈ {high, normal} AND steps.json has spare capacity AND nothing higher-ROI is pending. Scarcity beats spew.

## Step 1 — search (≥3 independent queries, EN+JA, real, never guess)
Use firecrawl (`/opt/homebrew/bin/firecrawl search "<q>" --limit 5`) + your web tools. Cover:
- **Improve/monetize existing**: read `~/.openclaw/skills/aniccaai-dashboard/data/dashboard-last.json`; for the lowest-ROI and highest-ROI products search how comparable products grew (pricing, ASO, SEO, channel, paywall) — copy proven best practice, no originals.
- **Zero-to-one**: search X / GitHub trending / HackerNews / Reddit for an unmet need where a small agent-built product would reduce suffering AND people already pay for the adjacent thing.

## Step 2 — score each candidate (drop anything that fails)
For each: `title`, `evidence` (source name + URL + the exact quote — no quote = delete the candidate), `reduces_suffering` (yes/no), `ev_usd` (rough expected monthly), `cost_est` (token/$/time), `precept_check` (五戒 pass / needs-ruling). Drop any that: fails 五戒, OR neither reduces suffering nor earns (HARD RULE #0 spend gate), OR has no cited evidence.

## Step 3 — queue, don't execute
Append the survivors to `ops/steps.json` `ranked[]` (or `one_time[]` if deadline-bound) with the fields above + `priority`. The heartbeat drains them on later beats. Do NOT act on them here — scouting only proposes; the loop decides and acts.

## Step 4 — report
One line: `🔭 scout: <S> searched · <Q> queued · top:<title> ($<ev>/mo) · <K> dropped(五戒/no-EV/no-cite)`

## Never
- Never become a cron. Loop-called only (scheduling judgment = forbidden, SOUL "You CAN ... this is NOT a menu").
- Never queue a candidate without a cited source quote (IBA / North Star: 引用なき判断は削除).
- Never publish/post during scouting (HARD RULE #9 — research only).
- Never spend that fails the 五戒 spend gate. You are the model (HARD RULE #6).
