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
  per-pass budget. The quantization is canonical and SHALL appear EXACTLY ONCE in this
  spec; per REQ-Q2 (FIND-3-001 fix: REQ-P1 defers to REQ-Q2 verbatim): `FULL` iff
  `b >= 3.0`; `MEDIUM` iff `1.0 <= b < 3.0`; `LIGHT` iff `0.1 <= b < 1.0`; `MINIMAL` iff
  `b < 0.1`. All ranges are inclusive-lower, exclusive-upper. The budget gates the
  depth of subsequent steps.

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

- **REQ-P11** SKIP CONDITIONS (= the ONLY legitimate reasons to skip step 6):
  (a) budget = MINIMAL AND no tasks in step 1;
  (b) `~/loops/<slot>/.dormant.sentinel` present (= REQ-Q5 wrote it; only bot2bot or
      adversary-PASS strategy mutation can remove it; FIND-013 fix removes the
      presenter-mode sentinel which was a human-control surface);
  (c) `~/loops/<slot>/.unfixable.jsonl` has ≥3 entries that are all REQ-H3 unfixable
      AND each menu item is blocker_check-blocked (= cascading failure; logged + exit).

  No human-control sentinel exists. Per Sutando's "infinite menu by design", if every
  category is genuinely blocked, that's a menu-misconfiguration to be surfaced via
  bot2bot, NOT a legitimate idle state.

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
  (c) `NOT_LOGGED_IN` (pane contains "Not logged in") → call
      `credential-restore.sh <slot>` which executes per FIND-012 fix below;
  (d) `trust_dialog` (pane contains "Quick safety check") → `tmux send-keys "1" Enter`;
  (e) `hook_module_missing` → call `auto-allowlist.sh <slot> <module>` which executes
      per REQ-H3e below;
  (f) `spawn_surface_drift` (pinned-sha mismatch) → call `auto-rollback.sh <slot>` which
      `git fetch origin main` then `git checkout <last-anicca-bot-signed-sha> -- skills/_shared/`
      then re-validates `verify_spawn_surface`;
  (g) `tmux_server_corrupted` (socket missing OR `tmux ls` exits non-zero) →
      `tmux kill-server` then call (a).

  Issue classes are mutually exclusive by detection priority (= same priority order as
  sprint-1 REQ-A classify); when multiple match, the highest-priority issue is the only
  one dispatched per pass (the next pass re-detects whatever remains).

- **REQ-H3c** Credential restore (FIND-012 fix; defines what (c) actually does):
  `credential-restore.sh <slot>` SHALL:
  (i) launch camofox (= `~/.openclaw/skills/camofox-browser`, port :9377) with the
      stored `~/.cloak/profiles/anicca-login` profile;
  (ii) navigate to `claude.com/cai/oauth/authorize?...` (the OAuth URL extracted from
       the pane);
  (iii) IF Google sign-in shown, fill `${GOOGLE_LOGIN_EMAIL}` + `${GOOGLE_LOGIN_PASSWORD}`
        from `~/.openclaw/.env`;
  (iv) IF OTP requested, invoke `gog gmail` (= `~/.openclaw/skills/gog/gmail`) to read
       the most recent code matching `subject contains "Claude"|"Anthropic"` AND
       `receivedWithin 5min`;
  (v) capture the redirected callback URL containing `code=...`;
  (vi) `tmux send-keys "$code" Enter` into the slot's pane (= paste auth code into the
       waiting `/login` prompt);
  (vii) `tmux capture-pane -p` to verify "Logged in as <email>";
  (viii) `<slot>-cli.sh --restart` to restart the slot core with fresh credentials.

  IF any step fails 3 attempts, write to `~/loops/<slot>/.unfixable.jsonl` per REQ-H5
  AND post to `bot2bot.sh post <slot> opinion-requested` so a sibling instance can
  diagnose. NO human is contacted.

- **REQ-H3e** Hook auto-allowlist (FIND-004 fix replaces vague --fix-deep with concrete):
  `auto-allowlist.sh <slot> <module>` SHALL:
  (i) `firecrawl scrape https://npmjs.com/package/<module> markdown` and extract
      weekly_downloads + author + last_publish + advisory_count;
  (ii) read `~/anicca/skills/_shared/trusted-authors.json` (sprint-1 carry);
  (iii) IF weekly_downloads >= trusted-authors.json's `min_weekly_downloads` AND author
        in `trusted_npm_authors` (OR module starts with any `trusted_org_namespaces`)
        AND no security advisories AND no `deny_pattern_substrings` match, append
        module to `~/anicca/skills/_shared/hook-modules-allowlist.txt` AND
        `git commit && git push` to a branch `auto-allowlist/<module>` AND
        open a PR for sibling-AI review (bot2bot.sh post);
  (iv) ELSE: skip + lessons.jsonl row `{outcome: hook-skipped, evidence_id: <npm-url>}`.

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

- **REQ-Q2** Budget computation (FIND-2-001 fix: half-open boundaries verbatim,
  matching PROP-P1):
  `budget_per_pass = remaining_pct / (minutes_until_reset / 5)`.
  Quantize: `FULL` iff `b >= 3.0`; `MEDIUM` iff `1.0 <= b < 3.0`; `LIGHT` iff
  `0.1 <= b < 1.0`; `MINIMAL` iff `b < 0.1`. All ranges are inclusive-lower,
  exclusive-upper.

- **REQ-Q3** Measurement-seam resilience (FIND-002 fix; restores full sprint-1 REQ-J9
  semantics):
  (a) Primary seam: read `CLAUDE_USAGE_ENV` or equivalent env-published usage if exposed.
  (b) Fallback 1: parse the tmux pane footer counter `↓ <N>k tokens` if the pane is
      capturable; reverse-engineer cumulative.
  (c) Fallback 2: byte-count × 0.25 (= 4-bytes-per-token) heuristic; emit
      `token_source: "estimated"` AND multiply computed cost by 2× (sprint-1 REQ-B6
      conservative penalty preserved).
  (d) Running ratio: when `Σ token_source=="estimated" / Σ all > 0.5` over the last 100
      rows, escalate to 4× penalty (sprint-1 REQ-J9 line 2 preserved).
  (e) Persistent degradation: IF degraded for 7 days (= 168 hourly rows), THE SYSTEM
      SHALL append a row to `~/anicca/state/mother-recovery-queue.jsonl` (= sibling
      instance picks it up via its own `bot2bot.sh poll`; not a separate service).

- **REQ-Q4** AT END-OF-PASS, THE SYSTEM SHALL emit a roi.jsonl row (sprint-1 REQ-B1
  schema) AND append a 1-line summary to `build_log.md`.

- **REQ-Q5** Dormancy boundary uses sprint-1 REQ-B5's `roi_7day_jpy` directly (FIND-001
  fix; one window definition across the framework). IF `roi_7day_jpy < 0` for 14
  consecutive 7-day windows (= 14 calendar days where each day's rolling-7d sum was
  negative) AND slot age > 14 days, THE SYSTEM SHALL write
  `~/loops/<slot>/.dormant.sentinel` (= graceful disable). The 14-window count is the
  HARD limit; INV-11 binary kill-switch (sprint-1 REQ-B4) remains as a backstop for the
  cost-cliff case.

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

- **REQ-B3** (REVISED FIND-003 fix; auto-merge SCOPE-DEFERRED to sprint-3)
  Sprint-2 ships `bot2bot.sh annotate-pr <slot> <pr-number> <verdict>` which adds a
  COMMENT to the PR carrying the sibling instance's fresh-context adversary verdict.
  Sprint-2 explicitly DOES NOT merge. Auto-merge requires sprint-3's real-ed25519 +
  anicca-bot CI pipeline (= FIND-015 sprint-1 carry); without that identity gate, a
  rogue sibling could merge arbitrary code.

  Sprint-2 merge path: the PR is annotated with `bot2bot-review-passed` label + verdict
  comment; an external watcher in the CI pipeline (= existing GitHub Actions on the
  framework repo, configured by Dais at install time) is the one that performs the
  actual merge once it sees the label AND verifies an ed25519 signature on the comment.
  This separates "AI proposes" (= sprint-2 in-scope) from "trust gate enforces" (=
  sprint-3 + Dais's CI config). The proactive-loop never directly merges.

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

- **REQ-M3** Canonical signature (FIND-3-002 fix: SINGLE shape used everywhere —
  Purity table, PROP-P6, PROP-P7, PROP-cadence, PROP-blocker-gate all reference this
  exact shape):

  `pick_next(menu: dict, log_tail: list, history: list, blockers: set[str],
             now_ts: int, budget: BudgetEnum) -> dict | None`

  Returns the unblocked item with highest `roi_estimate × probability_of_landing`,
  applying IN ORDER:
  (i) the cadence gate — items whose `min_cadence_seconds` is set AND whose
      `last_fired_ts` (read from log_tail or sidecar cadence.json) satisfies
      `now_ts − last_fired_ts < min_cadence_seconds` are excluded;
  (ii) the budget gate — items whose `required_budget` (= one of FULL/MEDIUM/LIGHT)
       exceeds the current `budget` are excluded;
  (iii) the blocker gate — items whose `blocker_check` name is in `blockers` (= the
        set of currently-failing blocker predicates) are excluded;
  (iv) ranking — among remaining items, pick argmax(roi_estimate × probability_of_landing);
  (v) the novelty quota (sprint-1 REQ-H1 inherited verbatim) — at least 10% of picks
      across history must be `(category, platform)` tuples not present in `history`
      (FIND-005 fix); the quota is enforced by occasionally promoting a novelty-eligible
      item over the strict argmax pick.

  Returns `None` iff every menu item is excluded by (i)-(iii) — proactive-loop's
  EDGE-S4 sink handler then fires.

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
  (c) preserve the growing-applied invariant (FIND-006 fix): a SINGLE menu pick at step 6
  in the `scan-requests` category SHALL itself apply a BATCH of N requests (where N is
  driven by strategy.json `max_apply_per_pass` from sprint-1), so applied.jsonl grows
  by N per scan-requests-pick. The acceptance is that applied.jsonl growth over the
  first 24h post-migration is ≥ 50% of the 24h before migration (= no regression in
  apply throughput; menu-driven picks are NOT per-row but per-batch-action).

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

- **EDGE-S4** All categories in menu.json are blocked at step 5 (FIND-004 fix; removes
  vague --fix-deep): log "no unblocked menu items" + call `bot2bot.sh post <slot>
  opinion-requested` with the blocker breakdown as the body (= surfaces to sibling
  instance for menu re-configuration) + exit cleanly with `idle`. Sutando rule:
  "infinite menu by design" — full block means menu config drift, surface via bot2bot.

- **EDGE-S5** bot2bot.sh poll returns 0 issues: that's normal (= no sibling instance
  online or none has answered yet). Step 1 just continues with local tasks.

- **EDGE-S6** Concurrent passes (= cron fires while previous pass still running):
  flock REQ-NFR-3 silently exits the second tick. The first tick's `core-status.json`
  shows `step` so observers know it's still alive.

- **EDGE-S7** (FIND-2-005 / FIND-016 fix) Adversary daily review is a regular menu
  item with `min_cadence_seconds: 86400` (= once per 24h). REQ-M3(ii) cadence-aware
  pick handles the timing. The adversary still runs as a FRESH subagent
  (sprint-1 REQ-E1 isolation requirement preserved) — it's the SCHEDULING that
  merged into the menu, not the EXECUTION isolation. `bash adversary-daily.sh
  <slot>` (from sprint-1) is still the actual invocation; only the WHEN-TO-FIRE
  decision moved into the menu picker.
