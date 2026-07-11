# Connector Loop RCA — fake-event claim + under-application (2026-07-12)

Scope: READ-ONLY root-cause analysis. No code changed, no event applied, nothing sent. All claims below are
either a `file:line` citation, a `state/*.jsonl` row, or a **live** page check performed in this session
(`firecrawl scrape` / `curl` against Connpass, `openclaw cron list`/`cron get`, `tmux capture-pane`,
`git log`, launchd log tails). Every H1-H4 verdict is evidence-backed, not inferred.

## 0. TL;DR

- **The "applies to FAKE events" claim is REJECTED for the current code** (as of commit `403bedc`/`6ac4c64`,
  2026-07-10 sprint-2/3 hardening). The two events actually applied to on Day 1 (2026-07-11) are **100% real**,
  independently confirmed live: both connpass event pages exist, and one (`400140`) shows the actual
  `DaisNar` connpass account **in the live attendee list** — proof of a genuine registration, not a
  fabricated ledger row. See §1.2.
- **BUT the code's own git history proves the fake-event/rubber-stamp bug WAS real** in an earlier iteration
  of this exact rebuild (sprint-1/sprint-2, commits `58775cf`, `1f18380`) — an evidence-free "apply" bug
  functionally identical to what the owner is describing. It was found by the VCSDD adversary and patched
  before the loop went live. The owner's memory of "fake events" almost certainly describes this pre-fix
  state, or the *general class* of risk, not the events currently in the ledger.
- **The "barely applies" claim is TRUE and has a concrete, evidence-backed cause: a ~15-restart crash storm
  on the loop's very first live day (2026-07-11 05:07-08:04 JST), plus a structural 1-candidate-per-day
  prompt design that cannot mathematically fill a 15-day horizon at the cadence the spec itself demands.**
  Since 08:04 JST on 2026-07-11 the tmux core has been "ALIVE" but has completed **zero** further passes for
  **16.8+ hours and counting** (by design — it idles until the next 07:35 JST cron-driven restart) — so only
  ONE calendar day of real data exists at all. Primary root cause = **H3 (instability) is PRIMARY,
  compounded by a spec/prompt mismatch (a variant of H4)**. H1 (hallucinated discovery) and H2 (apply is a
  pure no-op) are **REJECTED** for the current code — both were true bugs in earlier sprints and are fixed.

## 1. AS-IS (evidence)

### 1.1 What the current pass actually does, file:line

Entry point: `connector-cli.sh` starts a detached tmux `claude --model sonnet` session with one giant
STARTUP prompt (`/Users/anicca/profitable-claude/skills/human-funded/connector/connector-cli.sh:18`). There
is **no deterministic discover step** in code — discovery is 100% agent judgment inside the prompt text:
"identify one real candidate event (connpass/Luma/Eventbrite/meetup, via the vendored
anicca-meetup-talk-applier/anicca-booking rails)" (`connector-cli.sh:18`, STEP 1). This is a deliberate
design choice per `event_apply_wrapper.py:8-16` (REQ-CON-102 docstring): "since production never configures
a rail script, this made every registration attempt refuse forever... The registration ACTION... is agent
judgment and is performed by the core agent directly via CloakBrowser/camofox BEFORE this wrapper is ever
invoked."

Deterministic gates that DO exist and DO run (all confirmed present in code, read in full):
- `evidence_gate.py:44-67` — `classify_free()`: default-paid-unless-proven-free, exact-token match (not
  substring) on a machine-format `"ticket class selected: ..."` prefix.
- `event_apply_wrapper.py:73-111` — real-PNG-magic-number + ≥5000-byte snapshot check
  (`is_real_snapshot`), and evidence-text-must-reference-event-host+slug check
  (`evidence_text_references_event`). Comment at `event_apply_wrapper.py:26-31` explicitly documents the
  PRIOR bug this replaces: "the prior version accepted ANY non-empty string as evidence text and ANY
  `os.path.isfile()==True` file as the snapshot, which the repo's own tests satisfied with a 1-14 byte dummy
  file — a rubber-stamp, not a verification" (FIND-002, sprint-2 adversary).
- `register_and_calendar.py:64-146` — single writer of `applications.jsonl`; refuses to write a CONFIRMED
  calendar event unless `event_apply_wrapper.py` itself returned `status:"registered"` (comment at
  `register_and_calendar.py:4-11`, REQ-CON-011/FIND-003, documents the PRIOR bug: "iteration-1 trusted a
  bare registration-result flag supplied directly by the caller, making event_apply_wrapper.py's I-confirm
  gate unreachable dead code").
- `gcal_write.py:112-119` — post-insert `gog calendar event <id>` readback before reporting success.

**Residual structural weakness (not yet exploited in the observed data, but real):**
`evidence_text_references_event()` (`event_apply_wrapper.py:91-111`) only checks that the evidence string
contains the event URL's own host + a path segment. The **event's own listing page** (pre-registration, not
the confirmation page) also contains its own host+slug in any scraped text — so an agent could in principle
satisfy this check by pasting text from the un-registered event page, without ever completing the join flow.
The gate does not require a canonical Japanese "申し込みが完了しました" / `/join/complete/` marker. This is
exactly the shape of bug the owner is worried about; it happens not to have fired in the Day-1 data (see
§1.2) but is not structurally closed. See Fix Plan §4.5.

### 1.2 connector-streak.jsonl / applications.jsonl contents + LIVE verification

`state/connector-streak.jsonl` has **exactly one row** (`state/connector-streak.jsonl:1`, gitignored per
`.gitignore:2`, not in git history):

```
date=2026-07-11, cron_ok=true, day_pass=true, registration=[2 events], telegram_delivered=true
```

`skills/human-funded/connector/state/applications.jsonl` (2 rows total, ever):

| event_id (gcal) | title | evidence_reference | LIVE check |
|---|---|---|---|
| `d27fulks5hb2st09u0ckpg759o` | GENIAC-PRIZE 2026 AI基盤モデル開発コンテスト 参加者募集説明会 | `matsuolab-community.connpass.com/event/399133/join/complete/` — "イベント申し込みが完了しました" | **REAL.** `firecrawl scrape https://matsuolab-community.connpass.com/event/399133/` returns a live connpass page, title/date/host match exactly ("Jul 13", "東大松尾研...", 一般参加 free tier, 20 attendees currently, matches the described GENIAC-PRIZE contest). |
| `i98dqbbhakbepgplhd42nm4u7c` | なんもわからん人の論文読み会（AIエージェントの未来：Foundation Agents）#42 | `wakaran-reading.connpass.com/event/400140/join/complete/` — "イベント申し込みが完了しました" | **REAL, with independent proof of the registration itself.** `firecrawl scrape https://wakaran-reading.connpass.com/event/400140/` returns a live page whose **Attendees** block lists the connpass user **`DaisNar`** (`https://connpass.com/user/DaisNar/`) — the exact account name the OLD OpenClaw connpass script used ("Login = camofox session 'connpass' (DaisNar / GitHub OAuth)", `connpass-lt-apply.sh:6`). This is a logged-out, independent readback that the registration genuinely happened, not a ledger fabrication. |

The two **discovered-but-not-applied** candidates in `opportunities.jsonl` were also live-checked and are
real live connpass events (`findy.connpass.com/event/396881/` — TypeScript AI agent talk, 224 attendees;
`findy-aiplus.connpass.com/event/399499/` — AI-driven dev meetup, live registration counters). Direct `curl`
against connpass (including the documented API `connpass.com/api/v1/event/`) returns a CloudFront **403**
bot-block for all of these URLs — this is *why* the old OpenClaw `discover.sh` disabled the Connpass API path
outright (`discover.sh:9`: "connpass API (blocked by CloudFront 403)") and why the connector prompt requires
driving a real logged-in browser (CDP :9222) rather than a bare HTTP client. `firecrawl scrape` (which does
NOT bot-block) confirms all 4 URLs are real, live, correctly-dated events.

**Verdict: zero fabricated events found in the current ledger.** H1 is rejected for the data that exists.

### 1.3 The crash storm (2026-07-11 05:07–08:04 JST) — `connector-core-healthcheck.log`

`~/.openclaw/logs/connector-core-healthcheck.log` (full tail read) shows:

```
05:07:24 DEAD → restart
05:12:27 DEAD → restart
05:17:29 DEAD → restart
05:22:32 DEAD → restart
05:27:35 DEAD → restart
05:32:37–06:02:36  backoff: 5 restarts in last 60min — not restarting   (7 consecutive backoff cycles)
06:07:36 DEAD → restart
06:12:41 DEAD → restart
06:17:43 DEAD → restart  → then finally "ALIVE (pass pending since restart)"
```

That is **8 DEAD→restart events** hitting the healthcheck's own 5-restarts/60min backoff cap **before the
daily cron even fired**. `restart-log`/`.connector-core-restart-log` records 4 more restarts clustered
07:48:52–08:04:01 JST (`date -r 1783723732` … `1783724641`). The scheduled daily cron
`anicca-connector-daily` (verified via `openclaw cron get ad89027d-c869-4956-8967-542bfa8b31d9`) fired
exactly on schedule at `07:35:00 JST` (`lastRunAtMs=1783722900100`), ran
`connector-cli.sh --restart` in 12 seconds (that command only *launches* the tmux session; it does not wait
for the pass), and the tmux session it launched was itself killed and relaunched 4 more times by the
healthcheck before one incarnation survived long enough to finish STEP0-5 — `applications.jsonl` timestamps
`2026-07-10T22:13:30Z`/`22:43:53Z` UTC = **07:13/07:43 JST**, and
`~/.openclaw/state/.connector-core-last-pass` mtime = **07:45:13 JST** — i.e. the ONE surviving pass squeaked
through in the ~19-minute gap between the 07:35 cron fire and the next 07:48 crash.

The session that started at the final 08:04 restart (captured live via `tmux capture-pane`, this session)
read its own state, correctly recognized the same-day work was already done, and **intentionally skipped
STEP1-5** to avoid a duplicate Telegram/scout row — this part of its behavior is correct. It then went idle
at a bare prompt. **As of this investigation (2026-07-12 00:58 JST), the tmux core has been idle for 1010+
minutes (16.8+ hours) with zero further completed passes** — by design (`connector-cli.sh:17`: "THEN stop
and stay idle -- the cron will drive subsequent passes"), the next trigger is tomorrow's 07:35 JST cron
restart. **`connector-streak.jsonl` therefore has exactly one row because exactly one calendar day of real
operation has occurred, full stop** — there has not yet been a "second day" to be under-applying on.

### 1.4 Cron/registry state (live, not jobs.json)

`openclaw cron list` (the live gateway store — per project memory
`reference_openclaw_cron_live_store_desync_use_cli_only`, `jobs.json` edits do NOT reflect the live state)
shows **zero** `meetup`/`connpass` entries currently scheduled. `/Users/anicca/.openclaw/cron/jobs.json`
still contains `connpass-lt-apply-daily` (`jobs.json:3302`), `anicca-meetup-apply-tokyo-weekly`
(`jobs.json:1093`), `anicca-meetup-discover-daily` (`jobs.json:1067`), `anicca-meetup-apply-sf-monthly`
(`jobs.json:1119`) all marked `"enabled": true` — but this is the **stale, ghost-job file**, not the live
gateway; `openclaw cron list` is definitive and confirms the spec's claim (§5, "OpenClaw イベント cron 9本は
disable済み") is TRUE for the live system. Only two live cron entries drive connector today:
`anicca-connector-daily` (`35 7 * * * Asia/Tokyo`, `connector-cli.sh --restart`, `lastRunStatus: ok`) and
`connector-streak-verify-daily` (`0 8 * * * Asia/Tokyo`, never yet run — `state.nextRunAtMs` only, no
`lastRunAtMs`). `config/directives.json` shows `blockedActions: ["outreach_send"]` only — no connector-apply
block. No registry-pause found for `connector`.

## 2. RCA — hypothesis verdicts

| H | Claim | Verdict | Evidence |
|---|---|---|---|
| **H1** hallucinated discovery | REJECTED (current code) | §1.2: all 4 discover/apply URLs live-verified real via firecrawl; one (`400140`) independently confirmed registered via the `DaisNar` account appearing in the live attendee list. **Was TRUE in an earlier sprint** — see §3. |
| **H2** apply is a dry-run no-op | REJECTED (current code) | `event_apply_wrapper.py:73-111` requires a real ≥5000-byte PNG + host/slug-matching evidence text; `register_and_calendar.py:4-11` structurally cannot bypass the wrapper. Git history (`58775cf`, `1f18380`) proves this exact bug existed in sprint-1/2 and was the sprint-2 adversary's headline FAIL finding ("evidence rubber-stamp") — fixed in `403bedc`. **Residual weakness noted in §1.1**: the evidence-text check would still pass on text scraped from the un-registered event page, not just the confirmation page — not yet exploited, but not closed either. |
| **H3** healthcheck restart-storm starves passes | **CONFIRMED — PRIMARY CAUSE** | §1.3: 8 DEAD→restart cycles hit the 5/60min backoff cap twice before the scheduled 07:35 JST cron even fired, then 4 more restarts 07:48-08:04; only one incarnation survived long enough (~19min window) to complete a pass. The core has been idle 16.8+ hours since with zero further passes (correct by design, but the *design itself* leaves a single ~1-hour crash-prone window per day as the ONLY opportunity to register anything — one bad day and there is a full 24h gap in the ledger). |
| **H4** gates over-filter to zero | REJECTED as stated, but a **related structural cause confirmed**: the STARTUP prompt asks the agent to "identify **one** real candidate event... for an open horizon day" per pass (`connector-cli.sh:18`, STEP 1, singular). At 1 pass/day and (per this prompt's literal wording) 1 candidate/pass, filling the spec's own 15-day horizon (§11 STANDARD bar: "horizon（今日〜14日+）の空き枠に FREE イベント実登録") is **mathematically impossible in under 15 days even with zero crashes**. Day 1 happened to register 2 events only because the crash-restart cycle caused STEP1 to run more than once that day — an accident of instability, not a working horizon-fill mechanism. |

**Primary root cause: H3 (crash-storm instability on the very first live day, compounded by a fragile
"idle-until-next-cron" design that gives the loop exactly one ~1-hour crash-prone window per calendar day to
do any work at all).** **Secondary/contributing cause: a spec-vs-prompt mismatch (H4 variant)** — the STARTUP
prompt's "identify **one** candidate per pass" cannot satisfy the spec's own "fill the whole 15-day horizon"
STANDARD bar at a 1-pass/day cadence, so even a perfectly stable loop would under-apply relative to the
document that defines "done." H1/H2 (the literal "fake events" / "no-op apply" bugs) are **historically real
but currently fixed** — the owner's complaint likely reflects the pre-`403bedc` behavior of this same rebuild
or general (justified) distrust of AI-native, self-reported "applied" claims, not the events currently on
the ledger.

## 3. OLD (OpenClaw) vs NEW (connector) — capability diff, file:line

| Capability | OLD (`~/.openclaw/skills/anicca-meetup-talk-applier/`) | NEW (`~/profitable-claude/skills/human-funded/connector/`) |
|---|---|---|
| Discovery mechanism | **Deterministic code.** `discover.sh:35-91` — real `browser-harness` (CDP :9223) DOM scrape of `tokyo.aitinkerers.org`, extracts real `<a>` hrefs + event-detail page text via regex date parse. Connpass/Luma/meetup.com sources are explicitly `# disabled` in code (`discover.sh:93-95`) because Connpass CloudFront-blocks bare HTTP (confirmed live in this RCA, §1.2). | **Agent judgment, no deterministic discover script.** `connector-cli.sh:18` STEP1 tells the agent in prose to "identify one real candidate event... via the vendored ... rails" but no rail script is ever actually invoked (`event_apply_wrapper.py:18-21`: "production never configures... `CONNECTOR_APPLY_RAIL_OVERRIDE`"). The agent itself drives CDP :9222 by judgment each day. |
| Apply mechanism | **Deterministic code + real browser click-through.** `connpass-lt-apply.sh:14-31` logs into connpass with real stored credentials (`CONNPASS_USERNAME`/`CONNPASS_PASSWORD` via `.env`) through a `camofox`/`CF` (chrome-forwarder) tab-automation HTTP API, then `connpass-lt-discover.py:114-167` (`register_speaker()`) does a real 2-step click-through (open-speaker-slot button → confirm-participation button) and reads the resulting page to confirm. This is code performing the click, not an LLM narrating it. | **Agent judgment + wrapper-verified evidence, no deterministic click-through code.** The registration click-through itself happens entirely inside the Sonnet agent's own tool use (CloakBrowser CDP :9222), with `event_apply_wrapper.py` verifying the *artifacts* the agent reports (PNG + evidence text) after the fact rather than driving the browser itself. |
| Cadence | 3 separate crons at different frequencies matched to real slot scarcity: `anicca-meetup-discover-daily` (daily, discover only), `anicca-meetup-apply-tokyo-weekly` (weekly, speaker-slot apply), `anicca-meetup-apply-sf-monthly` (monthly). Real output: only **2 applications ever recorded** in `data/applications/` (2026-05-06, 2026-06-01) — sparse, because open **speaker/LT** slots are genuinely rare, not because the loop was idle. | Single daily cron (`anicca-connector-daily`, `35 7 * * *`) restarts one tmux core that is asked to fill an entire 15-day **attendee-registration** horizon (a much higher bar than "apply if an open speaker slot exists") but the STARTUP prompt only asks for **one** candidate per pass (§2, H4). |
| Login/session | Static long-lived camofox profile + explicit env-var credentials, one deterministic login-check-then-login flow (`connpass-lt-apply.sh:18-31`). | Relies on the CloakBrowser **daily-driver** tab already being logged in (the owner confirmed they are logged into Connpass there on CDP :9222) — no deterministic login/session-refresh code exists in the connector dir at all; if that daily-driver session ever logs out, there is no fallback and no explicit detection of "logged out" as a failure mode in any of the 6 connector scripts read. |
| Verification / anti-fabrication | None beyond "did the click-through code report `ok:true`" — i.e. the OLD system trusted its own deterministic code, which is a reasonable trust boundary since a human/script drove the actual click. | Extensive, explicit **anti-fabrication machinery** (PNG-magic-number check, host/slug string match, I-confirm gate, single-writer invariant) — because trust boundary shifted from "code clicks" to "LLM clicks, code checks the LLM's claim," which is inherently a weaker guarantee (§1.1 residual weakness) even after two rounds of adversary hardening. |
| Stability | No tmux/headless-Claude process to crash — `discover.sh`/`apply.sh` are plain bash invoked once per cron fire and exit. Nothing to restart-storm. | Long-lived tmux headless-Claude session (`connector-cli.sh:42-43`) that can hang, be OOM-killed, or crash mid-pass; a 5-min-interval healthcheck (`connector-healthcheck.sh`) exists specifically because this failure mode is expected — and it fired 8 times in 3 hours on day 1 (§1.3). |

**What was lost**: a boring, deterministic, code-driven click-through with a narrow real-slot-scarcity-matched
cadence, replaced by an ambitious LLM-judgment-driven "fill the whole calendar" loop that is architecturally
capable of much more (any FREE event, not just open speaker slots) but is measurably less stable (crash-prone
tmux core) and currently under-specified relative to its own stated goal (1 candidate/pass vs. 15-day
horizon-fill).

## 4. FIX PLAN

### 4.1 Stability first (addresses H3, the primary cause)

- Investigate WHY 8 DEAD→restart cycles happened 05:07-06:17 JST, **before** the scheduled cron even fired
  — this is the highest-value unknown (§5). Read `~/.openclaw/logs/connector-core-transcript.log` archived
  segments from that window (the file is `copytruncate`d after each audited pass, so the crash-window
  transcript is likely gone — check `~/.openclaw/state/.connector-core-broken-request.json` and any
  `self-heal-request.json` history first) and any `claude` crash logs for that period.
- Once cause is known, fix at the source (likely: model/tool timeout, tmux pane buffer overflow, or a
  `--dangerously-skip-permissions` prompt hang similar to the `ANTHROPIC_API_KEY` bug already fixed in
  `3180e6c`). Add a regression test per the "suite-promotion gate" already mandated in the spec
  (§11.1 item 6): whatever crashed becomes a permanent regression case.
- Reduce the healthcheck restart interval's blast radius: today a crash-loop consumes the loop's *entire*
  daily window before backing off for an hour, then tries again — for a loop with only one shot per day, that
  is unacceptably fragile. Consider: (a) an immediate one-time retry-with-backoff INSIDE the STARTUP prompt
  itself before ceding to the 5-min healthcheck restart cycle, or (b) shortening `STALE_MIN` isn't the fix
  (it's about *stale*, not *crash-looping*) — the real fix is making the underlying process not crash 8
  times in 70 minutes.

### 4.2 Real discover (Connpass API + Luma, via the :9222 daily-driver where the owner is logged in)

- Connpass's official API (`connpass.com/api/v1/event/`) is CloudFront-403-blocked for bare `curl`/`requests`
  from this network (confirmed live in this RCA, §1.2, and independently confirmed by the OLD system's own
  code comment `discover.sh:9`) — do **not** try to "fix" this by hitting the API directly; it is a
  bot-detection wall, not a code bug. The correct real-discovery path (matching this RCA's own successful
  method) is: drive the CDP :9222 daily-driver browser to `connpass.com/explore/` / a keyword search URL,
  read the **rendered page** for real event links, same trust model as `firecrawl scrape` used successfully
  in §1.2/§1.3 of this doc. This is already effectively what the current STARTUP prompt asks the agent to do
  in judgment — the fix here is not "add a rail," it's "verify the agent is actually doing this and not
  drifting to invented events" (§4.4).
- For Luma: same CDP :9222 daily-driver approach; there is no working Luma discover code in either OLD or
  NEW — this needs building fresh (agent-judgment discovery + the same evidence-gate verification pattern
  already proven for connpass).

### 4.3 Real apply, for TODAY (2026-07-12) through 2026-07-26, all qualifying events

- Keep the current agent-judgment-drives-CDP:9222 + evidence-gate-verifies architecture — it is **already
  producing real, independently-verifiable registrations** (§1.2). Do not regress to "trust the LLM's
  self-report" and do not remove the evidence gates.
- Fix the cadence mismatch (§2, H4): either (a) explicitly change the STARTUP prompt's STEP1 wording from
  "identify **one** real candidate event" to "identify and register a candidate for **every currently-open
  horizon day**, looping until horizon_full or no more real candidates exist that pass," or (b) explicitly
  change the spec's STANDARD bar (§11) to match a realistic 1-candidate/day cadence and accept a ~15-day
  fill time — but the current state, where the PROMPT says "one" and the SPEC says "the whole horizon," must
  not be left silently mismatched; pick one and make the other match it.

### 4.4 Reality-verifier (mirrors the gig own-eyes verifier pattern)

- Add a scheduled, **independent** (not self-reported) verification pass — same pattern as
  `.claude/agents/reality-verifier.md` already built for connector per spec §8.1 (V1, "connector PASS実証済み,
  メール送付済み") and the `connector-streak-verify-daily` cron (`openclaw cron get
  30245234-b027-494b-a0d1-89d62483a874`, already live but has never run — `state.nextRunAtMs` only) — that
  for every row in `applications.jsonl`, does exactly what this RCA did manually: `firecrawl scrape` the
  event URL and assert the evidence text's claimed facts (attendee count direction, event still exists,
  ideally the registering account visible in a public attendee list where the event exposes one) actually
  match the live page. This closes the residual §1.1 weakness (evidence text merely referencing host+slug is
  not proof of actual registration) with an **external, logged-out** check, exactly the "own-eyes
  verification" standard the spec's §10/memory `feedback_i_am_the_final_verifier` already mandates for every
  other loop.
- Concretely harden `event_apply_wrapper.py`'s `evidence_text_references_event()` (currently
  `event_apply_wrapper.py:91-111`) to ALSO require the evidence text or the URL path itself to contain a
  canonical completion marker (e.g. `/join/complete/`, `参加登録`, `申し込みが完了`, or connpass's own
  "Cancel attendance" / キャンセル button text which only appears post-registration) — this is a
  deterministic string check (permitted "fixed-format" parsing per the project's own regex-permission
  clause), not agent judgment, and directly closes the loophole noted in §1.1.

### 4.5 Re-enable OLD OpenClaw cron vs fix NEW — recommendation

**Fix the NEW connector, do not re-enable the OLD cron, but do it fast and narrow.** Reasoning:
- The OLD system's real historical output was **sparse** (2 applications total, matched to genuine
  speaker-slot scarcity) — it is not actually the "reliably applies every day" system the owner remembers;
  it reliably ran a *cron* every day, but "apply" only fired when an open LT/speaker slot existed. Re-enabling
  it would not close the gap the owner is complaining about (horizon-wide FREE-event registration), because
  the OLD system was never built for that goal — it was built for speaker slots only.
  Note this comparison is **REASONED, not exhaustively VERIFIED**: `data/applications/` may not be the only
  historical ledger (e.g. Slack `#content-metrics` posts referenced in `connpass-lt-apply.sh:40-45` were not
  checked in this RCA — see §5).
- The NEW connector's verified, hardened evidence-gate architecture (§1.1-1.2) is a real, independently
  confirmable capability the OLD system never had, and per spec §5 the explicit architectural decision
  ("正式な家 = claude-p... 理由: OpenClaw 側は... 自己修復・自己改善の器として不適") already rejected OpenClaw
  as the long-term home. Reversing that now would be starting over, not fixing a bug.
- The actual fix surface is narrow and already mostly built: (1) find+fix the crash-storm root cause (§4.1,
  the single biggest lever — Day-1 barely survived it), (2) resolve the 1-candidate-vs-whole-horizon mismatch
  (§4.3), (3) close the evidence-text loophole (§4.4). None of these require re-platforming to OpenClaw.
- If, after attempting §4.1, the crash-storm root cause turns out to be something structurally hard to fix
  within the tmux-headless-Claude-core pattern (e.g. an unfixable Claude Code CLI bug under
  `--dangerously-skip-permissions` + `--add-dir $HOME`), then re-enabling `connpass-lt-apply-daily` via the
  `openclaw cron` CLI (never hand-editing `jobs.json`, per project memory
  `feedback_openclaw_cron_live_store_desync_use_cli_only`) as a narrow, deterministic **speaker-slot-only**
  supplementary rail (not a replacement) would be a reasonable fallback while the NEW connector's core
  stability is being fixed — but this should be a last resort, not the first move.

## 5. Open questions / unknowns (honestly listed)

1. **Root cause of the 8 DEAD→restart cycles at 05:07-06:17 JST, before the scheduled cron fired** — not
   determined in this RCA. The transcript log for that exact window was not recoverable (it gets
   `copytruncate`d after each audited pass, and the audit only started tracking after the crash storm ended).
   This is the single most important unknown for §4.1 and should be investigated first.
2. Whether the OLD OpenClaw system had a larger historical application ledger than the 2 files found in
   `data/applications/` (e.g. via Slack `#content-metrics` posts per `connpass-lt-apply.sh:40-45`, or an
   `agentmemory observe` store referenced in the `anicca-meetup-apply-tokyo-weekly` cron prompt at
   `jobs.json:1107`) was **not checked** — this RCA is REASONED on file evidence only, not exhaustively
   verified against every possible ledger.
3. Whether the CloakBrowser daily-driver tab (CDP :9222) is *currently* actually logged into Connpass, as the
   task brief asserts — this RCA did not drive or inspect that browser session (out of scope, read-only task).
   If it is logged out, every future connector pass will silently fail STEP1 with no explicit "logged-out"
   error path in any of the 6 scripts read (§3 diff table) — worth an explicit login-freshness check as part
   of §4.1/§4.4.
4. Whether `anicca-connector-daily`'s 12-second "ok" cron-run status could mask a pass that never actually
   progresses past STEP0 on some future day (since the cron only measures whether `connector-cli.sh --restart`
   itself exited 0, not whether the resulting tmux pass ever completed) — the `connector-streak-verify-daily`
   cron (0 8 * * * JST) is presumably meant to close this gap but has **never yet run** (`lastRunAtMs` absent)
   as of this RCA; its first real output should be checked on 2026-07-12 08:00 JST.
5. Whether the "one candidate per pass" STARTUP-prompt wording (§2 H4) was a deliberate, considered scoping
   decision (e.g. to bound daily token/compute cost) or an oversight relative to the spec's own horizon-fill
   language — not established from the code/spec alone; worth a direct question to whoever last edited
   `connector-cli.sh:18`.

---

## 6. ADDENDUM — main-session が自分の目で再確認(2026-07-12)

RCA agent を止めて自分で実ログ/実ブラウザを確認した結果、以下を更新:

1. **失敗モードは「crash storm」だけでなく『first pass pending ハング』が主**。`connector-core-healthcheck.log` は `ALIVE (first pass pending, 35/40/.../125+min since start)` を延々記録 = **session は生きているが STEP0-5 が完了しない**（2時間以上 pass が着地しない）。巨大な単一 STARTUP prompt（STEP0-5 を1passで browser drive+register+OTP+gcal+telegram）を Sonnet が途中で詰まらせている疑い。crash(DEAD→restart)も別窓で発生。**どちらも「1日1回の窓」を食い潰す**。
2. **self-heal が一度も発火していない**: `.connector-core-broken-request.json` / `.connector-core-selfheal-request.json` = **空**。「pass が2時間 pending」を loop 自身が fixable fault として認識せず self-heal request を書かない = 検知欠落（gig と同じ「report-blind」問題の別形）。
3. **:9222 daily-driver は今まさに Connpass ログイン済**（`https://connpass.com/dashboard/` タブが open）= open-Q#3 解消。fix は このタブを drive すれば実応募できる。login は障害ではない。
4. 従って fix 優先順位（確定）: **(A) cadence=1候補/pass→「開いてる全 horizon 日を埋めるまで loop」に変更**（Dais 要件: 7/12-7/26 全 event 応募）／ **(B) pass ハング/crash の安定化 + self-heal に「pass pending > N分」検知を追加**／ **(C) connector-streak-verify-daily(既存・未起動) の logged-out firecrawl 照合を実際に走らせ各応募を独立検証**。
5. **fake event は現行コードでは無い**（2件は実登録・DaisNar が attendee list に居る）。「fake」記憶は 2026-07-10 修正前 sprint(58775cf/1f18380 の rubber-stamp bug)の状態。
