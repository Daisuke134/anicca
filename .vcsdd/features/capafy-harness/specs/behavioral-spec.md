# Behavioral Spec — capafy-harness (Phase 1a) — REV 3 (post iteration-2 FAIL)

REV 2 fixed iteration-1 spec-review BLOCKING findings C-1 (REQ-CAP-102 now wires BOTH
`cadence-evidence.py` dispatch chains, not just `gather_evidence()`) and C-2 (NEW REQ-CAP-112 wires the
Cadence Contract into `verify-loops.sh`/`verify-loops-audit.sh`, the scripts that actually own capafy's
production escalation). Also resolved the non-blocking `apply_category_boost` location note (pinned to
`funnel_metrics.py`, REQ-CAP-108/109). C-1/C-2/T-1 were independently confirmed RESOLVED by iteration-2's
fresh-context re-review.

REV 3 fixes iteration-2's NEW BLOCKING finding C-3: REQ-CAP-112 (REV 2) wired 2 of the 3 scripts that
own capafy's escalation chain, but `cadence-deadline-check.sh` — the ONLY script that actually invokes
`self-fix.sh` for a Cadence Contract loop — was never touched, and REQ-CAP-112's own closing paragraph
made a disproven claim that it "needs no new wiring." REV 3 retracts that claim, adds REQ-CAP-112(e), and
updates the design doc's file-scope line accordingly. See `verification-architecture.md` REV 3 for the
matching PROP-CAP-016(d) fix.

## Context (why this feature exists)
Design: `docs/superpowers/specs/2026-07-09-capafy-harness-design.md`. The capafy loop already
publishes real skills to the Capafy marketplace (`~/.openclaw/skills/capafy-autopublish/state/published.jsonl`
has 21 real rows, e.g. `{"agent_id":"3947077924","skill":"meeting-action-items","status":"submitted (status=1
under review) — agentic CP1","date":"2026-07-08"}`) but is missing 3 of the 5 "gig-proven" harness parts:
a Cadence Contract entry, mail evidence wired to the actual publish pass, and search+metrics-driven
self-improve. This spec closes those 3 gaps using the gig loop's already-proven patterns
(`~/anicca/skills/self/cadence-evidence.py::_gig_activity_event_dates`,
`~/profitable-claude/skills/human-funded/gig/gig-cli.sh`'s STARTUP search-half/metrics-half wiring) —
copy+adapt, not reinvent, per `~/.claude/CLAUDE.md`'s 車輪の再発明禁止 rule.

## Ground truth (re-verified 2026-07-09, exact line numbers / real API responses)

- **Cadence source field**: every `published.jsonl` row written by the current automated pipeline carries
  a bare `"date": "YYYY-MM-DD"` string with NO time component, written by
  `~/.openclaw/skills/capafy-autopublish/scripts/publish_finish.sh:129`
  (`"date":__import__("datetime").date.today().isoformat()`, i.e. `datetime.date.today()` — the process's
  LOCAL calendar day, not UTC). The Mac Mini's system timezone is confirmed `Asia/Tokyo`
  (`readlink /etc/localtime` → `/var/db/timezone/zoneinfo/Asia/Tokyo`; `date` prints `JST`). So
  `publish_finish.sh`'s `date` field is ALREADY the correct JST calendar day — no epoch/ISO→JST conversion
  is needed or possible (there is no time component to convert), unlike gig's `ts` field. This is a real,
  documented difference from `_gig_ts_to_jst_date`'s epoch/ISO parsing — capafy's evidence function MUST
  treat the `date` string as the JST day directly (after format validation), never run TZ arithmetic on it.
  `reconcile_ledger.py:91` (`datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")`), by
  contrast, computes the UTC calendar day — for any reconcile run between JST 00:00–08:59 (UTC 15:00–23:59
  the PREVIOUS calendar day), this writes a `date` ONE DAY EARLIER than the true JST day the reconciliation
  actually happened on, a real off-by-one that could cause a false Cadence Contract miss (self-fix
  escalation for a day that genuinely had a reconciled "online" event). REQ-CAP-103 below fixes this.
- **`published.jsonl` schema today**: keys observed across all 21 real rows (verified via a
  `python3 json.load` sweep of the live file): `agent_id`, `title`, `skill`, `status`, `date`, plus
  `mode`/`model`/`pricing`/`category`/`note` on SOME rows only. Critically, the CURRENT automated
  ledger-append site (`publish_finish.sh:121-133`, the `python3 - "$ID" "$SKILL_NAME" "$LISTING"` heredoc)
  writes ONLY `{agent_id, skill, title, status, date}` — it NEVER writes `category`. The rows that DO carry
  `category` (e.g. `"category": 5`, `"category": "マーケティング"`) are historical, hand-published entries
  from before this agentic pipeline existed. This means "published funnel メトリクス...を見て売れたカテゴ
  リに倍賭け" (design §self-improve) is structurally impossible today — there is no per-listing category on
  any row the CURRENT pipeline writes. REQ-CAP-104 fixes this using data ALREADY available at
  `publish_finish.sh` ledger-append time: `build_config.py:28` already parses the SAME LISTING.md's
  `category:` header line via `re.search(r"category:\s*([^\(·\n]+)", L)` (confirmed present in a real
  LISTING.md: `.../LISTING.md:3` → `"category: 生産性 (winner cat 6)"`) — a genuine fixed-format parse of a
  machine-authored header line, not judgment (BUILD AGENTS RIGHT §1 exemption for "genuine parsing of a
  fixed machine format").
- **No per-agent view-count API exists**: `python3 packager.py publish-list` (verified live call,
  2026-07-09, 23 real agents returned) returns per agent: `agentId, name, desc, agentType, agentStatus,
  hasOnlineVersion, latestAgentVersionId, latestVersionName, latestLogoUrl, updatedAt, sales, rating,
  ratingCount, reviewCount, recentSales`. `recentSales` is a 7-element array (last-7-days sales counts,
  currently all-zero for every online agent — real, matches `capafy-loop/loop.sh`'s own `$0/mo` STATE.md
  reading). There is NO `views`/`impressions`/`clicks` field anywhere in this response, and grepping
  `packager.py`'s subcommands (`login-init/verify/token, publish-init/configure/ship/remote-status/
  refresh-url/list/status`) confirms no analytics/stats subcommand exists either. "閲覧" (views) is
  therefore NOT machine-measurable via any tool found — the metrics half of self-improve (REQ-CAP-108)
  is honestly scoped to `sales`/`recentSales`/`rating`/`reviewCount` (purchase + quality signals) plus
  `~/anicca/skills/self/capafy-loop/loop.sh`'s EXISTING `CAP_MO` (latest monthly payout, `loop.sh:24-34`)
  and `CAP_3D` (3-day net revenue, `loop.sh:36-43`) aggregate reads — never a fabricated view count.
- **Report path is currently split, and only ONE of the two already calls `loop-report.sh`**:
  `~/anicca/skills/self/capafy-loop/capafy-loop-cli.sh`'s STARTUP prompt (the daily 9am tmux-core "money
  loop" wake) already has "STEP4 REPORT: bash ~/anicca/skills/report/loop-report.sh capafy \"<what you did
  + real metric>\" <success|failure|no-op> <usd or 0> \"<evidence url or none>\"" — but this format string
  is vague (no required URL/status/earnings shape) and this wake does not itself publish (it delegates to
  `daily_loop.sh`). `~/.openclaw/skills/capafy-autopublish/DAILY_LOOP.md` (the actual publish runbook, run
  either directly by launchd `com.anicca.capafy-daily` or via `capafy-loop-cli.sh`'s STEP2) is the process
  that ACTUALLY publishes a listing — its step 7 ("Record + report") currently does ONLY `git add -A &&
  commit && push` + "a Telegram summary" (`DAILY_LOOP.md:52-53`), with NO `loop-report.sh` call at all. So
  the pass that does the real work (publish) sends no mail evidence today; the pass that DOES call
  `loop-report.sh` (capafy-loop-cli.sh) has a vague evidence format. Both gaps are fixed below
  (REQ-CAP-105/106).
- **Verify mechanism already exists, just not tied to the report**: `daily_loop.sh:29` already runs
  `reconcile_ledger.py --json` at the START of every run — this is server-truth reconciliation (via
  `packager.py publish-list`, `reconcile_ledger.py:68-78`), NOT an HTTP GET of the public store page. It
  appends a ledger row ONLY for agents the SERVER reports `agentStatus in {"online","approved"}`
  (`reconcile_ledger.py:41,99`) — this is exactly the "既存 reconcile_ledger.py の server 照合を活用" the
  design calls for. What's missing: the evidence string sent to `loop-report.sh` (REQ-CAP-105/106) must
  READ this reconciled truth for the specific `agent_id` being reported on, not a status string frozen at
  publish time (which is always `"submitted..."`, never `"online"`, since an agent can't be confirmed
  online in the same pass it was just submitted).
- **agent-reach skill** (`~/.claude/skills/agent-reach/SKILL.md`) is the established web-research tool
  already used by gig's STARTUP search-half (`gig-cli.sh` B4 IMPROVE STEP, SEARCH HALF (a)) — same
  invocation convention reused here, not a new mechanism.
- **`cadence-evidence.py` has TWO independent per-loop dispatch chains, not one** (re-verified
  2026-07-09 against iteration-1 spec-review finding C-1): its public entrypoint `status_for_loop()`
  (`:356-369`) calls BOTH `gather_evidence()` (`:270-295`, computes today's `met` boolean) AND
  `evidence_by_date_for_streak()` (`:299-353`, computes the `streak` the parent design doc names as
  "health の KPI", `2026-07-08-...-design.md:71`) — EACH ends in `raise ValueError(f"no evidence source
  wired for loop: {loop!r}")` (`:293`, `:353`) for an unhandled loop. Every existing loop (gig/bounty/
  founder-loop/pm-earner) has a matching branch in BOTH chains. `evidence_by_date_for_streak()`'s
  existing `gig` branch (confirmed exact): `if loop == "gig": dates = _gig_row_exists_event_dates();
  for i in range(window_days): d = (today - datetime.timedelta(days=i)).isoformat(); out[d] =
  {"event_dates": [d] if d in dates else []}; return out`. A capafy branch is needed in BOTH chains
  (REQ-CAP-102 below), reusing the SAME `_capafy_row_exists_event_dates()` in each — never two
  divergent implementations.
- **`status_for_loop("capafy")` is called by TWO production scripts that swallow its failure into a
  silent false-negative**: `verify-loops.sh:40-45`'s `cadence_line()` wrapper pipes
  `cadence-evidence.py status <loop>` through a JSON parse and, on ANY non-zero exit or parse failure
  (including the `ValueError` above), falls back to the HARDCODED string `"❌missed (streak=0)
  [evidence-gather error]"` — so a half-wired capafy entry would read as "missed" FOREVER regardless of
  real publish activity, never surfacing as an error. `verify-loops-audit.sh:38-40` does the same via a
  bare `except`. Confirming `status_for_loop("capafy")` returns a real (non-raising) result end-to-end
  is therefore load-bearing, not merely a nice-to-have (REQ-CAP-102/PROP-CAP-015 below).
- **`cadence-contracts.json`'s new `capafy` entry is not read by anything that runs in production
  unless it is ALSO added to the two scripts' loop lists** (re-verified 2026-07-09 against iteration-1
  finding C-2): `verify-loops-audit.sh:35` hardcodes `CADENCE_LOOPS="clip affiliate video gig bounty
  pm-earner founder-loop"` — capafy is absent. Instead, capafy is currently driven by a SEPARATE, OLDER
  mechanism: `verify-loops-audit.sh:19`'s `[ "$(stale_hrs "$CAP")" -ge 30 ] && bash self-fix.sh capafy
  "audit: no new capafy skill published in >30h..."` (a 30h-artifact-staleness self-fix escalation,
  independent of any Cadence Contract), documented at `verify-loops-audit.sh:30-32`'s own comment:
  "capafy/reddit/lm (above) keep stale_hrs()/self-fix unchanged (REQ-LV-104, out of this feature's
  scope)" — an explicit, deliberate deferral by the PRIOR sibling spec
  (`2026-07-08-claude-p-loop-verification-evidence-design.md`, whose own §Cadence Contract states "既存
  OUT_STALE_HRS（30h）方式はこの cadence contract 判定に置き換える" for the 7 loops it migrated, capafy
  excluded). Without also updating these two scripts, REQ-CAP-101/102 would be built exactly to spec,
  pass every unit test, and STILL never change capafy's actual healthcheck/escalation behavior in
  production — the design's stated goal #1 would not be achieved. REQ-CAP-112 below closes this.

## In scope
1. Add a `capafy` Cadence Contract entry (`kind: row-exists`) to `~/anicca/skills/self/cadence-contracts.json`
   and a matching `capafy` branch in BOTH of `~/anicca/skills/self/cadence-evidence.py`'s per-loop
   dispatch chains — `gather_evidence()` AND `evidence_by_date_for_streak()` — so `status_for_loop
   ("capafy")` returns a real result without raising.
1b. Wire that new contract into the three production scripts that actually consume Cadence Contracts —
    `verify-loops.sh`/`verify-loops-audit.sh` (scorecard visibility) AND `cadence-deadline-check.sh` (the
    ONE script that actually invokes `self-fix.sh` for a Cadence Contract loop, REQ-CAP-112(e)) —
    replacing capafy's legacy 30h-staleness self-fix escalation the same way the prior sibling spec
    already replaced it for the other 7 loops.
2. Fix `reconcile_ledger.py`'s UTC-day computation to JST-day (closes the off-by-one Ground Truth found).
3. Add a `category` field to every NEW row `publish_finish.sh` appends to `published.jsonl`.
4. Wire `loop-report.sh capafy` into `DAILY_LOOP.md` step 7 (currently absent) with a concrete evidence
   format (agent URL + server-reconciled status + earnings-or-none).
5. Tighten `capafy-loop-cli.sh`'s existing `loop-report.sh` call (STEP4) to the same concrete evidence
   format, sourcing the earnings figure from that SAME wake's own `loop.sh` STATE.md read (STEP1).
6. Add a search-half (agent-reach: capafy.ai/growth#cases + X best-selling-skill patterns) and a
   metrics-half (publish-list per-agent `sales`/`recentSales`/`rating`/`reviewCount` + `loop.sh`'s
   `CAP_MO`/`CAP_3D`, aggregated by category via item 3's new field) to `capafy-loop-cli.sh`'s STARTUP,
   both ALWAYS running every wake (never conditional on one being skipped), writing to two NEW state files
   under `~/.openclaw/skills/capafy-autopublish/state/`: `strategy.json` (category priority signal for the
   NEXT listing the interactive Opus session builds) and `lessons.jsonl` (append-only history).
7. Never introduce AI-usage-disclosure / "AI-generated" copy into any listing text touched by this
   feature's self-improve diffs (Dais constraint, universal to all loops).

## Out of scope
- Changing `inventory_status.py`'s `ready_inventory()` pick order (alphabetical `os.listdir` scan,
  `inventory_status.py:70-90`) — it drains ALREADY-BUILT inventory mechanically; this feature's
  self-improve output (`strategy.json`) feeds the NEXT listing the interactive Opus session chooses to
  BUILD, not a re-ordering of the existing drain queue. Building a priority-aware picker is a separate,
  larger change not requested here.
- A per-listing view-count metric (no API exists — see Ground Truth).
- Any change to `~/anicca/skills/self/cadence-contracts.json` or `cadence-evidence.py`'s existing
  clip/affiliate/video/gig/bounty/founder-loop/pm-earner entries or functions — those MUST remain
  byte-identical (verified by diff in Phase 3).
- Any change to other loops, other repos, or `~/.openclaw/skills/capafy-autopublish/vendor/` (third-party
  vendored publisher/user CLIs). `verify-loops.sh`/`verify-loops-audit.sh` are shared infra scripts this
  feature DOES touch (REQ-CAP-112), but ONLY the capafy-related lines — every other loop's `cadence_line`/
  `CADENCE_LOOPS` entry, and the reddit/lm legacy `stale_hrs()` blocks, remain byte-identical (same rule as
  `cadence-contracts.json`'s other 7 entries).
- Migrating reddit or lm off their own legacy `stale_hrs()`/`liveurl()` self-fix blocks
  (`verify-loops-audit.sh:20-28`) — that is the SAME deferred-scope item the prior sibling spec already
  named for a future feature; this feature migrates ONLY capafy.

## Requirements (EARS)

- **REQ-CAP-101 (Cadence Contract declaration)**: THE SYSTEM SHALL add a `"capafy"` key to
  `~/anicca/skills/self/cadence-contracts.json` with `kind: "row-exists"`, `cadence: "1/day"`,
  `unit: "listing"`, `boundary_tz: "Asia/Tokyo"`, and a `source` string documenting
  `~/.openclaw/skills/capafy-autopublish/state/published.jsonl`'s `date` field (per Ground Truth: already
  a JST-local calendar day, no epoch conversion). Every OTHER existing key in this file
  (`clip`/`affiliate`/`video`/`gig`/`bounty`/`founder-loop`/`pm-earner`) SHALL remain byte-identical —
  ONLY a new key is added, nothing existing is reordered, reformatted, or reworded.

- **REQ-CAP-102 (evidence-gathering function, gig-parity rigor)**: THE SYSTEM SHALL add a
  `_capafy_published_path()` helper to `cadence-evidence.py` returning
  `os.environ.get("CAPAFY_PUBLISHED_PATH") or os.path.expanduser("~/.openclaw/skills/capafy-autopublish/state/published.jsonl")`
  (same env-override convention as `_gig_applied_path`/`_bounty_funnel_path`), and a PURE function
  `_capafy_activity_event_dates(rows: list) -> set[str]` that: (a) skips any row where
  `isinstance(row, dict)` is False (mirrors `_gig_activity_event_dates`'s GAP-1 guard for a bare non-dict
  JSON line); (b) skips any row whose `"status"` key is missing, `None`, or an empty/whitespace-only
  string (a row with no real status is not a real publish event); (c) for every remaining row, validates
  `row["date"]` matches the fixed machine format `^\d{4}-\d{2}-\d{2}$` (via `re.fullmatch` — genuine format
  parsing, not judgment) and, if it matches, adds it VERBATIM to the returned set (per Ground Truth: this
  IS already the JST day, no conversion); a `date` that is missing, non-string, or does not match the
  format is skipped, never guessed. `gather_evidence()`'s dispatch (the `if loop in (...)` chain,
  `cadence-evidence.py`'s existing structure) SHALL add `if loop == "capafy": return {"event_dates":
  sorted(_capafy_row_exists_event_dates())}` where `_capafy_row_exists_event_dates()` reads
  `_capafy_published_path()` via the EXISTING `_read_jsonl_rows()` helper and calls
  `_capafy_activity_event_dates()` on the result — same shape as `_gig_row_exists_event_dates()`.
  ★ REVISED after iteration-1 spec-review FINDING C-1 (`cadence-evidence.py` has TWO independent
  per-loop dispatch chains, not one — see Ground Truth) ★: THE SYSTEM SHALL ALSO add a matching `if
  loop == "capafy":` branch to `evidence_by_date_for_streak()` (`:299-353`), mirroring the EXISTING
  `gig` branch there EXACTLY (byte-for-byte structure, only the loop name and helper function differ):
  `dates = _capafy_row_exists_event_dates(); for i in range(window_days): d = (today -
  datetime.timedelta(days=i)).isoformat(); out[d] = {"event_dates": [d] if d in dates else []}; return
  out` — reusing the SAME `_capafy_row_exists_event_dates()` this requirement already defines above (no
  second, divergent implementation). With BOTH branches added, `status_for_loop("capafy")` (`:356-369`)
  SHALL return `{"loop":"capafy","met":<bool>,"streak":<int>,"scorecard":"<✅posted-today|❌missed>
  (streak=<int>)"}` without raising, for ANY `published.jsonl` content (including an empty/missing
  file — `met=False`, `streak=0`, no crash). No existing function, branch, or helper for another loop is
  modified in either dispatch chain.

- **REQ-CAP-103 (reconcile_ledger.py JST-day fix)**: THE SYSTEM SHALL change
  `reconcile_ledger.py:91`'s `today` computation from
  `datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")` to a JST-local calendar day (e.g.
  `datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Tokyo")).strftime("%Y-%m-%d")`, matching the
  `boundary_tz: "Asia/Tokyo"` convention every other Cadence Contract in this codebase already uses and
  matching `publish_finish.sh:129`'s own local-day convention), so that a reconciliation appending an
  `"online"` row between JST 00:00–08:59 records the CORRECT (not previous) JST calendar day. This is a
  deterministic timezone-arithmetic fix, not a judgment change — `reconcile_ledger.py`'s online/rejected/
  draft classification logic (`ONLINE`/`REJECTED`/`DRAFT` sets, `:41-44`) is UNCHANGED.

- **REQ-CAP-104 (ledger category field)**: WHEN `publish_finish.sh`'s ledger-append step (`:121-133`)
  writes a NEW row for an agent that has NEVER been ledgered before (the existing dedup-by-`agent_id`
  check, `:118-119`, is UNCHANGED), THE SYSTEM SHALL ALSO extract a `category` value from the SAME
  `$LISTING` file already passed into that heredoc (`$3` / `sys.argv[3]`) using the SAME regex
  `build_config.py:28` already uses (`re.search(r"category:\s*([^\(·\n]+)", L)`, defaulting to
  `"ライティング"` if the header line is absent or unparseable — IDENTICAL default to `build_config.py:29`,
  so a listing whose category the automated pipeline could not parse never silently drops the field) and
  include it as `"category": <value>` in the appended JSON line, alongside the existing `agent_id`, `skill`,
  `title`, `status`, `date` keys (none of which change shape or order). This is a genuine re-parse of a
  fixed machine-authored header line already proven correct by `build_config.py`'s own existing use of the
  identical pattern — not a new judgment call.

- **REQ-CAP-105 (DAILY_LOOP.md mail evidence — currently absent)**: THE SYSTEM SHALL replace
  `DAILY_LOOP.md`'s step 7 ("Record + report") so that, in addition to the existing `git add -A && commit
  && push`, it ALSO runs `bash ~/anicca/skills/report/loop-report.sh capafy "<one-line summary of what
  happened this pass>" <success|failure|queue-empty> 0 "<evidence>"` where:
  - `<success|failure|queue-empty>` maps to: a listing reached `status=1 ∧ isConfirmedConfigKeys=1`
    (success); the publish flow was attempted but a gate failed (failure, per DAILY_LOOP.md's own STOP
    conditions in steps 1/2/3/5); OR the loop determined "cap full" / "inventory empty" (queue-empty, per
    DAILY_LOOP.md steps 1/2's existing STOP language).
  - the 4th positional arg (`earned_usdc`) SHALL be literally `0` — REQ-CAP-102's Ground Truth already
    established a publish-time pass cannot honestly confirm revenue (revenue is a monthly aggregate
    tracked separately by `loop.sh`, not a per-publish-event figure); passing anything else would be a
    fabricated number.
  - `<evidence>` SHALL be, on a `success` result: the string
    `"https://capafy.ai/store/agent/<AGENT_ID> status=<server-reconciled status string, REQ-CAP-107> earned=unconfirmed-at-publish (see monthly capafy-loop check)"`;
    on `failure`/`queue-empty`, SHALL be the literal string `"none: <the concrete reason DAILY_LOOP.md's own
    STOP message already produces>"` (e.g. `"none: cap full, N listed"`, `"none: inventory empty (all items
    online); bottleneck = need NEW inventory"`) — reusing DAILY_LOOP.md's EXISTING stop-message text
    verbatim, never a new fabricated reason string. The existing Telegram summary MAY remain (out of
    scope to remove); it is additive, not a replacement for the mail report.

- **REQ-CAP-106 (capafy-loop-cli.sh evidence format tightening)**: THE SYSTEM SHALL rewrite
  `capafy-loop-cli.sh`'s STARTUP STEP4 report instruction so its `<usd or 0>` argument is no longer a
  vague placeholder but explicitly instructs: "read `capafy_monthly_payout_usd` from THIS wake's own
  `loop.sh` STATE.md output (already read in STEP1) and pass that EXACT value (not a re-derived or
  rounded one) if it is a real number; pass literal `0` only if STEP1's read itself returned `NA` or
  `HEAL-NEEDED`" — and its `<evidence url or none>` argument SHALL follow the SAME format REQ-CAP-105
  defines: on a pass that published (delegated to `daily_loop.sh` in STEP2), the agent URL + reconciled
  status string; on a pass that did NOT publish (no-op/cap-full/inventory-empty), `"none: <reason>"`. This
  is a text-instruction change to the STARTUP prompt string only — the CronCreate registration mechanism,
  the self-heal STEP0, and STEP1/STEP2/STEP3 logic are UNCHANGED.

- **REQ-CAP-107 (search-half self-improve, ALWAYS runs)**: THE SYSTEM SHALL add a NEW instruction block to
  `capafy-loop-cli.sh`'s STARTUP prompt, run EVERY wake (unconditionally — never skipped, never gated on
  `do_improve`/cadence/cold-start, since capafy wakes only 1x/day so every wake IS the improve wake),
  DISTINCT from the EXISTING (and currently server-broken) Capafy-internal marketplace-search attempt
  already in STEP2 ("Market-search... Capafy search is currently server-broken"): use the `agent-reach`
  skill to search for current best practices at `capafy.ai/growth#cases` (the platform's own published
  success-case page) AND for what AI-agent/skill marketplace listings are currently selling well on X —
  apply AT LEAST ONE concrete diff informed by a specific finding from that search to
  `~/.openclaw/skills/capafy-autopublish/state/strategy.json`'s `category_priority` map or
  `recent_bp_notes` list (schema: REQ-CAP-109); WHEN the search finds nothing new/actionable, record that
  honestly in `recent_bp_notes` rather than fabricating a diff (the search itself still counts as done,
  never skipped); IF `agent-reach` itself errors or is unavailable, log a warning and continue — this
  SHALL NEVER abort the wake (matches this codebase's existing gh-failure-never-aborts convention, e.g.
  `gig-cli.sh`'s PRE-STEP/B5 error handling).

- **REQ-CAP-108 (metrics-half self-improve, ALWAYS runs, honestly scoped to real fields)**: THE SYSTEM
  SHALL add a NEW instruction block, run EVERY wake unconditionally (same "always both halves" rule as
  REQ-CAP-107 — this codebase's established principle, `docs/superpowers/specs/2026-07-08-claude-p-loop-
  verification-evidence-design.md` §"Self-improve = 検索 + メトリクスを常に両方"): run a NEW deterministic
  script `~/.openclaw/skills/capafy-autopublish/scripts/funnel_metrics.py` that (a) calls
  `packager.py publish-list` for the LIVE per-agent `sales`/`recentSales`/`rating`/`reviewCount` fields
  (Ground Truth — the only real per-agent signals available, no views field exists); (b) reads
  `published.jsonl` for each row's `agent_id`→`category` mapping (REQ-CAP-104's new field; rows still
  missing `category`, i.e. historical pre-feature rows, are excluded from the by-category aggregation, not
  defaulted); (c) joins them into a PURE aggregation `{category: {"listed": int, "sales_sum": int,
  "recent_sales_sum": int}}`; and (d) also reads `~/anicca/skills/self/capafy-loop/state/STATE.md`'s
  `capafy_monthly_payout_usd`/`capafy_3d_net_usd_leading` lines (the aggregate revenue signal, already
  computed by `loop.sh` STEP1 earlier in the SAME wake — no duplicate API call). THE AGENT SHALL read this
  script's output and, WHEN any category shows `recent_sales_sum >= 1` OR `rating`/`reviewCount` evidence
  of a genuine sale, raise that category's weight in `strategy.json`'s `category_priority` (double-down,
  same "≥1 signal → raise priority" rule gig's B4 METRICS HALF already uses) by invoking
  `python3 funnel_metrics.py boost-category "<category>" "<note>"` — a NEW CLI subcommand on the SAME
  `funnel_metrics.py` file (★ RESOLVED after iteration-1 spec-review's non-blocking note: this is the
  ONE, pinned location for the write — not an "or STARTUP-driven inline write" — see REQ-CAP-109 and
  the verification-architecture purity table) that internally calls the pure `apply_category_boost()`
  then atomically persists the result; WHEN the review finds ZERO categories with any signal yet (true
  cold-start — the current real state, per Ground Truth's all-zero `recentSales`), THE AGENT invokes
  `python3 funnel_metrics.py record-zero-signal` instead (no `category_priority` mutation, but a
  `lessons.jsonl` line IS still written — never a skipped step, matching gig's "confirmation read even
  when the ledger is empty or all-zero" convention).

- **REQ-CAP-109 (state file schemas)**: THE SYSTEM SHALL define
  `~/.openclaw/skills/capafy-autopublish/state/strategy.json` as
  `{"category_priority": {"<category string>": <float weight>}, "recent_bp_notes": ["<string>", ...],
  "last_search_pass_ts": "<ISO-8601>", "last_metrics_pass_ts": "<ISO-8601>"}` (created with
  `category_priority: {}`, `recent_bp_notes: []` on first write if absent — never crashes on a missing
  file, mirrors gig's `passprep.py` bootstrap-from-default convention) and
  `~/.openclaw/skills/capafy-autopublish/state/lessons.jsonl` as an append-only JSONL file, one line per
  REQ-CAP-107/108 finding, shape `{"ts": "<ISO-8601>", "pass_type": "search"|"metrics", "category":
  "<string or null>", "finding": "<string>", "action": "<string, what strategy.json field was changed, or
  'none: <reason>'>"}` — both files live under `capafy-autopublish/state/` (within this feature's
  authorized scope), never under any other loop's directory. REQ-CAP-108's `boost-category`/
  `record-zero-signal` CLI subcommands are the sole writer of `category_priority` (metrics-half, `pass_type:
  "metrics"` lines); REQ-CAP-107's search-half writes `recent_bp_notes` directly (agent-driven file write
  inside the interactive session, not a scripted CLI — the judgment of WHAT to record stays with the agent,
  only the metrics-half's numeric-threshold trigger is mechanical enough to warrant a deterministic wrapper).

- **REQ-CAP-110 (verify — server-reconciled status, not a frozen self-report)**: WHEREVER REQ-CAP-105/106
  build an evidence string referencing an agent's status, THE SYSTEM SHALL source that status from
  `published.jsonl`'s LATEST row for that `agent_id` AFTER `reconcile_ledger.py` has run this wake (already
  invoked at `daily_loop.sh:29` every pass) — i.e., the reported status reflects genuine server truth as of
  THIS pass (via `packager.py publish-list`'s `agentStatus`, per `reconcile_ledger.py:41-44`'s existing
  ONLINE/REJECTED/DRAFT classification), never a status string hardcoded into the evidence builder at
  publish time. A freshly-submitted agent legitimately reports `"submitted (status=1 under review)..."`
  (accurate, not yet online) rather than a fabricated `"online"`.

- **REQ-CAP-111 (no AI-disclosure copy — Dais constraint, all loops)**: Any listing copy text
  (LISTING.md's `## Title`/`## shortDescription`/`## welcomeMessage`/`## detailedDescription`) that
  REQ-CAP-107's search-half diff influences SHALL NEVER introduce AI-usage-disclosure or
  "AI-generated"/"powered by AI" language — this mirrors `BEST_PRACTICES.md`'s existing no-overclaim
  doctrine (already enforced by `DAILY_LOOP.md` step 4's sanity re-read) and is a HARD constraint from
  Dais, not a style preference. This is a constraint on WHAT the agent may write when applying a diff, not
  new code — verified in Phase 3 by adversary re-read of any LISTING.md touched during Phase 2.

- **REQ-CAP-112 (NEW after iteration-1 spec-review FINDING C-2, EXTENDED after iteration-2 FINDING C-3 —
  wire the Cadence Contract into ALL THREE scripts that actually own escalation, not just the two
  informational ones)**: THE SYSTEM SHALL:
  (a) add `capafy` to `verify-loops-audit.sh:35`'s `CADENCE_LOOPS` list (becomes `"clip affiliate video
  gig bounty pm-earner founder-loop capafy"` — order-preserving append, the other 7 names unchanged) so
  the existing `for L in $CADENCE_LOOPS; do ... done` loop (`:37-41`) already scorecards capafy without
  any further code duplication;
  (b) add a matching `echo "[capafy]       $(cadence_line capafy)"` line to `verify-loops.sh`, placed
  alongside (not replacing) the existing `[clip]`/`[affiliate]`/.../`[founder-loop]` `cadence_line` echo
  block (`:46-52`) — the PRE-EXISTING `[capafy] published: ...` informational line (`verify-loops.sh:
  20-23`, which curls the newest listing URL live) is NOT a Cadence Contract check and MAY remain
  alongside the new line as an independent, complementary liveness signal (out of scope to remove);
  (c) REMOVE `verify-loops-audit.sh:19`'s legacy escalation line — `[ "$(stale_hrs "$CAP")" -ge 30 ] &&
  bash "$SELF/self-fix.sh" capafy "audit: no new capafy skill published in >30h..."` — entirely (not
  merely comment it out), since the Cadence Contract path (REQ-CAP-101/102) now OWNS capafy's escalation
  criterion ("did today's contracted cadence happen", not "is the artifact stale"), matching the EXACT
  "REPLACES" precedent this codebase already used for the other 7 loops (`verify-loops-audit.sh:30-31`'s
  own comment: "This REPLACES the old fresh()/stale_hrs() judgment for these 7 loops ONLY"); AND
  (d) update `verify-loops-audit.sh:30-32`'s comment to remove `capafy` from the "kept unchanged" list
  (it now reads `"reddit/lm (above) keep stale_hrs()/self-fix unchanged"` — reddit and lm remain
  genuinely deferred per the prior sibling spec, capafy does not); AND
  (e) ★ NEW after iteration-2 spec-review FINDING C-3 — the claim below (a)-(d) previously made about
  `cadence-deadline-check.sh` needing no wiring is DISPROVEN and RETRACTED; this sub-item (e) is the
  actual fix ★: add `capafy` to `cadence-deadline-check.sh:23`'s `CADENCE_LOOPS` list (becomes
  `"clip affiliate video gig bounty pm-earner founder-loop capafy"` — SAME order-preserving-append
  convention as (a), the other 7 names unchanged). This is REQUIRED, not optional: independent re-read
  of `cadence-deadline-check.sh` (confirmed 2026-07-09) shows it is the ONE place in this codebase that
  actually invokes `self-fix.sh` for a Cadence Contract loop (`:42`, gated by its own per-loop
  `met==False` check at `:38` and a once-per-JST-day marker file at `:39-41`) — `verify-loops.sh`'s (b)
  and `verify-loops-audit.sh`'s (a) additions are BOTH purely informational (a printed scorecard line and
  a report-mail string respectively; confirmed zero `self-fix.sh` calls in either file tied to a
  cadence-contract loop name). Critically, `cadence-deadline-check.sh:23` does NOT read
  `cadence-contracts.json`'s keys dynamically — it is its OWN, independently-hardcoded string, entirely
  unaffected by REQ-CAP-101 adding a `capafy` key to that JSON file. Without this sub-item (e), shipping
  (a)-(d) exactly as written would be a REGRESSION: (c) deletes capafy's only current escalation trigger
  (the legacy `stale_hrs` line) and nothing replaces it, because `cadence-deadline-check.sh` would still
  never call `self-fix.sh` for capafy — capafy would go from "escalates within ~30h" (today) to "never
  escalates, ever, only a passive scorecard line" (post-feature, if (e) were omitted). `verify-loops.sh`'s
  and `verify-loops-audit.sh`'s and `cadence-deadline-check.sh`'s handling of
  clip/affiliate/video/gig/bounty/pm-earner/founder-loop/reddit/lm SHALL remain byte-identical except for
  the ADDED capafy lines above (in all three files).

## Non-functional constraints
- No dry run (HARD RULE): every script this feature adds/edits (`funnel_metrics.py`, the
  `cadence-evidence.py` capafy branch, `reconcile_ledger.py`'s TZ fix, `publish_finish.sh`'s category
  extraction) reads REAL files (`published.jsonl`, `STATE.md`, live `publish-list` API) — no fixture stands
  in for production data outside of the Phase 2 test suite's own explicit unit-test fixtures.
- `cadence-contracts.json`'s existing 7 entries and `cadence-evidence.py`'s existing 7 loops' functions
  (in BOTH `gather_evidence()` and `evidence_by_date_for_streak()`) MUST diff as byte-identical except for
  the new capafy addition (verified in Phase 3 via `git diff`).
- `verify-loops.sh`'s, `verify-loops-audit.sh`'s, AND `cadence-deadline-check.sh`'s existing
  clip/affiliate/video/gig/bounty/pm-earner/founder-loop/reddit/lm handling MUST diff as byte-identical
  except for REQ-CAP-112's added capafy lines (in all three files) and the removed legacy
  `stale_hrs("$CAP")` escalation line (same verification method).
- `agent-reach` / API read failures (REQ-CAP-107/108) never abort the wake — fail-open with a logged
  warning, matching every other loop's established convention in this codebase.
- All new file I/O (`strategy.json`, `lessons.jsonl`) uses the SAME atomic-write-then-rename convention
  `reconcile_ledger.py:118-122` already uses for `published.jsonl` (tmp file + `os.replace`), not a
  bare `open(...,"a")` for `strategy.json` (which is READ-MODIFY-WRITE, unlike the pure-append
  `published.jsonl`/`lessons.jsonl` files).
