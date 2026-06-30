---
feature: proactive-loop-skeleton
phase: 1a
mode: lean
language: python
sprint: 2
depends_on:
  - earn-shared-skeleton (sprint-1, CONVERGED 2026-07-01)
sources:
  - github.com/sonichi/sutando (50 days, 600+ PRs, proven autonomous build loop)
  - github.com/sonichi/sutando/blob/main/skills/proactive-loop/SKILL.md
  - github.com/sonichi/sutando/blob/main/AGENTS.md
  - earn-shared-skeleton spec § "Sprint-2 Architecture Simplification"
---

# Behavioral Specification — proactive-loop-skeleton (sprint-2)

## Purpose

Replace the over-engineered 9-handler Group J architecture (sprint-1 earn-shared-skeleton)
with the Sutando-derived 4-primitive design that handles every failure class GENERICALLY.

Sutando proves (50 days, 600+ PRs, single proactive-loop) that AI-agent autonomy needs
4 primitives — proactive-loop + health-check + quota-tracker + bot2bot — not 9 per-failure
handlers. We adopt this pattern.

## Goal (= "Done" condition)

After convergence: ANY earn slot's launchd plist invokes `proactive-loop.sh <slot>` every
5 min. Each pass runs the same 8-step body for gig/clip/video/affiliate/bounty. Self-heal
is generic (`health-check.py --fix`), self-improvement is continuous (`quota-tracker` +
`build_log.md` + ROI-driven menu pick), AI-to-AI coordination is via gh issues
(`bot2bot.sh`). Human gate count: ZERO (REQ-J8 invariant inherited from sprint-1).

## Scope (in vs out)

**In scope** — sprint-2 SHALL ship:
- `~/anicca/skills/_shared/proactive-loop.sh` — single 5-min cron entry, 8-step body
- `~/anicca/skills/_shared/health-check.py` — generic auto-recovery with `--fix`
- `~/anicca/skills/_shared/quota-tracker.py` — Claude usage → per-pass budget
- `~/anicca/skills/_shared/bot2bot.sh` — gh issue-based AI-to-AI coord
- `~/anicca/skills/_shared/lib/build_log.py` — narrative memory read/write helper
- `~/anicca/skills/_shared/lib/menu.py` — infinite-menu config schema + picker
- Per-slot seed files: menu.json (5 slots: gig/clip/video/affiliate/bounty)
- Gig slot migration to proactive-loop.sh (= first proof-of-concept)

**Out of scope** — sprint-3 will handle:
- 5-slot mass migration (clip/video/affiliate/bounty + new) — sprint-3
- Real ed25519 nacl.signing key + CI signed-commit gate (= sprint-1 FIND-015 carry)
- LLM-driven proposal/deliverable revise (= sprint-1 FIND-004/005 carry; folded into
  proactive-loop step 5 menu pick)
- Pure-layer missing symbols (= sprint-1 FIND-006 carry)

## EARS-Format Functional Requirements

### Group P — Proactive Loop (`proactive-loop.sh`)

The single 5-min cron entry per slot. 8-step body. PIVOT-ON-BLOCK rule: blocked work
never stops the loop, only switches lane.

- **REQ-P0** WHEN `proactive-loop.sh <slot>` starts, THE SYSTEM SHALL write
  `{"status": "running", "slot": <slot>, "step": "<description>", "ts": <epoch>}` to
  `~/loops/<slot>/state/core-status.json` AND update the `step` field as it progresses
  through steps 1-7 AND write `{"status": "idle", "ts": <epoch>}` at end of pass.

- **REQ-P1** AS STEP 0.5, THE SYSTEM SHALL invoke `quota-tracker.py` to compute the
  per-pass budget: `FULL` (remaining% per pass > 3%) / `MEDIUM` (1-3%) / `LIGHT` (< 1%)
  / `MINIMAL` (0% remaining). The budget gates the depth of subsequent steps.

- **REQ-P2** AS STEP 1, THE SYSTEM SHALL process any files in `~/loops/<slot>/tasks/`
  (= owner-injected tasks; in our case = test fixtures + cross-instance task hand-off).
  Process highest-priority first (urgent > normal > low). On completion, write a result
  file at `~/loops/<slot>/results/<task-id>.json`.

- **REQ-P3** AS STEP 2, THE SYSTEM SHALL read `~/loops/<slot>/pending-questions.md`. If
  any unanswered items exist AND budget is at least LIGHT, THE SYSTEM SHALL log them to
  `build_log.md` as a category of work. NO Telegram / Discord / voice surfacing —
  REQ-J8 invariant from sprint-1 inherited.

- **REQ-P4** AS STEP 3, THE SYSTEM SHALL invoke `health-check.py --fix <slot>`. Any
  detected-and-fixed issue SHALL be logged to `build_log.md`. Unfixable issues SHALL
  surface as `~/loops/<slot>/.unfixable.jsonl` and ALSO appear as menu items in step 5.

- **REQ-P5** AS STEP 4, THE SYSTEM SHALL read `~/loops/<slot>/build_log.md` (= the
  slot's narrative memory) to understand what's already done. The system SHALL NOT
  re-do work the log says is complete.

- **REQ-P6** AS STEP 5, THE SYSTEM SHALL pick from `~/loops/<slot>/menu.json` the work
  item with the highest `roi_estimate × probability_of_landing`. Items in the menu are
  scoped to the slot (gig: scan-requests / nurture-talk-rooms / deliver / evaluate;
  clip: source / cut / post / monitor; etc).

- **REQ-P7** PIVOT-ON-BLOCK: AS STEP 5, IF the highest-ROI item is blocked
  (= external waiting on platform / buyer / upstream PR), THE SYSTEM SHALL log the block
  to `build_log.md` AND pick the next-highest-ROI unblocked item. Idling = forbidden.
  Sutando rule verbatim: "Blocked ≠ stop. Pivot lane."

- **REQ-P8** AS STEP 6, THE SYSTEM SHALL execute the picked work to depth allowed by
  budget. `FULL` = subagents OK, heavy research OK. `MEDIUM` = code fixes, monitoring, no
  subagents. `LIGHT` = task processing + health checks only. `MINIMAL` = owner tasks +
  health + log only.

- **REQ-P9** AS STEP 7, THE SYSTEM SHALL append a narrative summary of the pass to
  `~/loops/<slot>/build_log.md` covering: budget at start, work picked, outcome, next
  candidate, any unfixable surfaced. Append-only — never rewrite history.

- **REQ-P10** EXIT CONDITION: at end of pass, THE SYSTEM SHALL exit cleanly with
  status=idle. The cron next 5-min tick re-enters. NO background daemon is left running.

- **REQ-P11** SKIP CONDITIONS (= the ONLY legitimate reasons to skip step 6, per Sutando):
  (a) budget = MINIMAL AND no tasks in step 1; (b) `~/loops/<slot>/.presenter-mode.sentinel`
  active (= human-set, single-tap pause for ad-hoc demos; this is the ONE owner-control file
  the loop respects); (c) `~/loops/<slot>/.loop-paused-until.sentinel` future-dated;
  (d) external wait on PRIMARY item ONLY (= other menu items still fair game per REQ-P7).

### Group H — Health Check (`health-check.py --fix`)

Generic auto-recovery. Replaces Group J's J1/J2/J3/J5. Detects + auto-fixes EVERY known
failure class without per-mode handler proliferation.

- **REQ-H1** WHEN invoked, THE SYSTEM SHALL collect a HealthSnapshot containing:
  tmux session state, `.last-pass` mtime, `.last-start` mtime, restart-log entries,
  pane-text capture (for the slot's claude-p session), cron registration state,
  spawn-surface sha-pinned validity, hook-modules-allowlist validity.

- **REQ-H2** `health-check.py --check` (= read-only) SHALL produce a list of detected
  issues. `health-check.py --fix` SHALL additionally attempt repair for each detectable
  issue.

- **REQ-H3** Auto-fix dispatch — for each detected issue, ONE of:
  (a) `tmux dead` → restart via slot's `<slot>-cli.sh --restart`;
  (b) `.last-pass stale (>90 min)` → restart;
  (c) `NOT_LOGGED_IN` (pane contains "Not logged in") → invoke credential-restore helper
      (camofox + Gmail OTP per REQ-J1 of sprint-1; the actual recovery flow);
  (d) `trust_dialog` (pane contains "Quick safety check") → `tmux send-keys "1" Enter`;
  (e) `hook_module_missing` → research via firecrawl + add to allowlist via signed PR;
  (f) `spawn_surface_drift` (pinned-sha mismatch) → `git checkout` last anicca-bot-signed
      commit of `_shared/`;
  (g) `tmux_server_corrupted` (e.g. socket missing) → `tmux kill-server` + restart.

- **REQ-H4** Each fix attempt SHALL be logged to `~/.openclaw/logs/<slot>-health.log`
  with `{ts, issue, action, outcome: "fixed" | "unfixable", details}`.

- **REQ-H5** Unfixable issues (= the action failed) SHALL be appended to
  `~/loops/<slot>/.unfixable.jsonl` so step 5 picks them up as menu items (= the
  health-check loop hands off to the proactive-loop's regular work-picker).

- **REQ-H6** THE SYSTEM SHALL NOT post to any human-touch surface for any of these
  detections — REQ-J8 invariant from sprint-1 inherited. Telegram / Discord / Slack /
  osascript dialog: forbidden.

### Group Q — Quota Tracker (`quota-tracker.py`)

Continuous budget. Replaces J4/J6/J9.

- **REQ-Q1** WHEN invoked at end-of-pass (step 0.5 from the NEXT pass's perspective —
  it reads the current state), THE SYSTEM SHALL read Claude Code's remaining usage % and
  the next reset timestamp.

- **REQ-Q2** Budget computation:
  `budget_per_pass = remaining_pct / (minutes_until_reset / 5)`.
  Then quantize: `FULL` if > 3, `MEDIUM` if 1-3, `LIGHT` if 0.1-1, `MINIMAL` if < 0.1.

- **REQ-Q3** IF quota source is unavailable (claude command not exposing usage), THE
  SYSTEM SHALL fall back to byte-count × 4-bytes-per-token heuristic AND apply 2×
  conservative penalty (sprint-1 REQ-B6 inherited) AND emit `token_source: "estimated"`.

- **REQ-Q4** AT END-OF-PASS, THE SYSTEM SHALL emit a roi.jsonl row (sprint-1 REQ-B1
  schema) AND append a 1-line summary to `build_log.md`.

- **REQ-Q5** IF cumulative ROI (= sprint-1 REQ-B5 rolling_window) has been < 0 for 14
  consecutive days AND the slot is not freshly seeded, THE SYSTEM SHALL write
  `~/loops/<slot>/.dormant.sentinel` (= graceful disable; the cron next tick reads this
  and skips step 6, only updating state to `idle`). This is the slow continuous version
  of INV-11 token kill-switch.

- **REQ-Q6** Sentinel removal: ONLY a bot2bot.sh response or a successful adversary-PASS
  on a new strategy.json may remove `.dormant.sentinel`. NEVER a human gesture.

### Group B — Bot-to-Bot (`bot2bot.sh`)

Replaces J7 MOTHER queue. Sutando uses Discord channel; we use gh issues to stay
zero-side-channel (= REQ-J8 compliant).

- **REQ-B1** `bot2bot.sh post <slot> <kind> <body-file>` SHALL create a gh issue with:
  - label = `bot2bot-<kind>` (kinds: `review-requested`, `opinion-requested`,
    `escalation`, `pr-mentioned`);
  - title prefix = `[bot2bot][<slot>][<kind>]`;
  - body = contents of `<body-file>`;
  AND append `{ts, slot, kind, issue_url}` to `~/loops/<slot>/bot2bot-sent.jsonl`.

- **REQ-B2** `bot2bot.sh poll <slot>` SHALL fetch open `bot2bot-*` issues authored by
  an anicca-bot account (= the other AI instance's reply) AND emit them as JSON for the
  proactive-loop step 1 to ingest as tasks.

- **REQ-B3** `bot2bot.sh auto-merge <slot> <pr-number>` SHALL be called after a sibling
  AI instance's fresh-context adversary returns PASS on a PR. The merge SHALL use
  `gh pr merge --merge --delete-branch` signed by anicca-bot (= CI pipeline secret).

- **REQ-B4** THE SYSTEM SHALL NEVER create a gh issue with label `escalation` whose
  body asks a human to act. REQ-J8 invariant: `escalation` label is reserved for the
  bot2bot internal use ONLY (= "the other AI should review this", never "Dais should
  look at this").

### Group M — Memory + Menu (`build_log.py`, `menu.py`)

- **REQ-M1** `~/loops/<slot>/build_log.md` SHALL be append-only. A pass appends a
  fenced section:
  ```
  ## 2026-07-01T05:00Z — pass <pass_id>
  budget: FULL/MEDIUM/LIGHT/MINIMAL
  picked: <menu-item-name> (roi=<n>, prob=<p>)
  outcome: <description>
  next-candidate: <menu-item-name>
  ```

- **REQ-M2** `~/loops/<slot>/menu.json` SHALL define the slot's infinite work catalog:
  ```jsonc
  {
    "schema_version": 1,
    "categories": [
      {
        "name": "scan-requests",
        "roi_estimate_jpy": 0,
        "probability_of_landing": 0.05,
        "novelty_weight": 1.0,
        "blocker_check": "coconala_search_reachable"
      },
      ...
    ],
    "novelty_quota_ratio": 0.1
  }
  ```

- **REQ-M3** `menu.pick_next(menu, log_tail, history)` SHALL return the unblocked
  item with highest `roi_estimate × probability_of_landing`, applying the novelty
  quota (REQ-H1 from sprint-1) — at least 10% of picks must be `(category, novelty)`
  tuples not seen in `history`.

- **REQ-M4** Sprint-1's existing jsonl streams (`lessons.jsonl`, `earnings.jsonl`,
  `applied.jsonl`, `roi.jsonl`) SHALL remain as immutable audit logs. `build_log.md`
  is the NARRATIVE summary. No data is lost in the simplification.

### Group J — Anti-Human-Touch Invariant (KEPT from sprint-1)

- **REQ-J8** (inherited verbatim from earn-shared-skeleton sprint-1) THE SYSTEM SHALL
  NEVER POST to Telegram / Slack / Twilio / osascript / terminal-notifier / Touch ID
  Keychain / Discord (when used for human messaging) / FCM push / APN push / pushover /
  ntfy / messagebird / ~/Library/Mobile Documents / ~/Documents/anicca-please-* path.

- **REQ-J8a** Static analyzer (sprint-1 `anti_human_touch_violations`) SHALL be re-run
  over ALL new sprint-2 source files (= proactive-loop.sh, health-check.py,
  quota-tracker.py, bot2bot.sh, build_log.py, menu.py). Any violation FAILs the daily
  adversary review.

### Group S — Slot Migration (`gig` first, others sprint-3)

- **REQ-S1** Gig slot migration: rewrite `gig-cli.sh` STARTUP prompt so the slot's
  cron prompt body becomes `bash ~/anicca/skills/_shared/proactive-loop.sh gig` (= 1
  line) instead of the current 8000-character B1-B5 prompt.

- **REQ-S2** Per-slot seed files SHALL be installed at:
  - `~/loops/gig/menu.json` (= the gig work catalog)
  - `~/loops/gig/strategy.json` (= existing, kept, REQ-C3 gated)
  - `~/loops/gig/build_log.md` (= new, starts empty)
  - `~/loops/gig/tasks/` (= directory, owner-injected tasks)
  - `~/loops/gig/results/` (= directory, result mirror)

- **REQ-S3** Existing gig state (`applied.jsonl`, `lessons.jsonl`, `earnings.jsonl`,
  `.last-pass`, `.last-start`) SHALL be preserved verbatim. The migration changes the
  ORCHESTRATOR, not the data.

- **REQ-S4** After migration, the first proactive-loop pass MUST observably:
  (a) touch `~/loops/gig/.last-pass`,
  (b) append at least one section to `~/loops/gig/build_log.md`,
  (c) NOT regress on the existing growing-applied behavior (= applied.jsonl count
  must continue to grow across passes).

## Non-Functional Requirements

- **NFR-1** All shared scripts SHALL be POSIX-bash or Python 3.11+; no new external
  runtime dependencies beyond sprint-1's set (tmux, jq, gh, python3, node, claude,
  openssl, curl) + `pipx` for sprint-2 dev tools (bandit, semgrep).

- **NFR-2** State SHALL be file-backed. NFR-2 sprint-1 inherited: tmp-file + atomic
  rename, single-line jsonl appends with `flock`.

- **NFR-3** Scripts SHALL be re-entrant. `flock -n ~/loops/<slot>/.proactive.lock`
  guards entry; concurrent ticks exit 0 silently.

## Edge Cases

- **EDGE-S1** First pass on a freshly migrated slot: `build_log.md` doesn't exist →
  auto-create with header `# <slot> build log — initialized YYYY-MM-DD`.

- **EDGE-S2** menu.json malformed: log to `~/.openclaw/logs/<slot>-menu-load.log` and
  fall back to a built-in default menu with single item `pending: investigate menu.json`.

- **EDGE-S3** Quota source unavailable AND estimated-byte fallback also fails (= claude
  CLI not in PATH): log + set budget = MINIMAL + write `{"status": "quota_unknown"}` to
  core-status.json.

- **EDGE-S4** All categories in menu.json are blocked at step 5: log "no unblocked
  menu items" + run step 3 health-check again with a more aggressive --fix-deep flag
  AND, if still nothing, exit cleanly with idle status. Sutando rule: "infinite menu
  by design — if you truly find nothing to do, that's a menu-misconfiguration, not
  legitimate idle."

- **EDGE-S5** bot2bot.sh poll returns 0 issues: that's normal (= no sibling instance
  online or none has answered yet). Step 1 just continues with local tasks.

- **EDGE-S6** Concurrent passes (= cron fires while previous pass still running):
  flock REQ-NFR-3 silently exits the second tick. The first tick's `core-status.json`
  shows `step` so observers know it's still alive.

- **EDGE-S7** Adversary daily review (= sprint-1 REQ-E1, replaced in sprint-2 as a
  menu item) is just a high-ROI menu category that fires on a once-per-day cadence
  inside the menu picker, not a separate launchd plist. Saves one launchd surface.
