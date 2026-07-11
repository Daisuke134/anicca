# behavioral-spec.md — gig-reality-verify (増分2b: own-eyes 検証を loop に焼く)

Source of truth for scope: `docs/loop-engineering/26-gig-loop-asis-tobe-plan.md` §8 (増分2b設計), §4
(検証設計), §5 (自己修復設計). BP citations: `docs/loop-engineering/25-browser-use-verify-selfimprove-bp.md`
§2/§7 (browser-use/benchmark `judge.py`, VERIFIED raw fetch, 198L, saved at
`scratchpad/judge_bu.py`).

## Purpose

Replace "私(claude-p)が main session で navigate→screenshot→判定" with a loop-owned, fresh-spawned,
report-skeptical verifier that runs on its own cadence (auditor.sh, hourly :45) and judges the gig
core's jsonl claims against the REAL Coconala screen state — never trusting the core's self-report.

## Purity Boundary (informal, script-level)

- **Pure / deterministic core**: `gig_judge.build_verifier_prompt()` — a pure function, no I/O, no
  LLM call, no network. Given claims + ground_truth URLs it returns a prompt string. 100% unit
  testable without a browser or network.
- **Effectful shell**: `gig_reality_verify.sh` — reads jsonl files (I/O), spawns a fresh `claude -p`
  process (subprocess + LLM call + browser via CDP :9222, network), writes `audit-reality.jsonl` and
  optionally `.gig-core-selfheal-request.json` (I/O). `auditor.sh` — orchestrates: existing
  deterministic verdict, then invokes the effectful shell.

## Requirements

### REQ-001: gig_judge exposes a pure prompt-builder, not an LLM caller
**EARS**: WHEN a caller imports `gig_judge` and calls
`build_verifier_prompt(claims, ground_truth_urls)` THE SYSTEM SHALL return a `str` prompt and SHALL
NOT perform any network call or LLM invocation inside `gig_judge.py`.
**Edge Cases**:
- Empty `claims` list: prompt SHALL still be returned (not raise), and SHALL state there are no
  claims to verify this round.
- `claims` containing non-ASCII (Japanese ¥/カテゴリ) text: prompt SHALL preserve it verbatim (no
  mangled encoding).
**Acceptance Criteria**:
- `import gig_judge` succeeds with only the Python stdlib (no `browser_use`/`pydantic` hard
  dependency — copy+tweak the prompt/spec of `judge.py`, not its message-object plumbing, since the
  runner is a bare `claude -p` prompt, not the browser-use LLM wrapper).
- Returned prompt is non-empty and contains the report-skeptical instruction phrases from judge.py
  L148/L101/L76 (see REQ-002).

### REQ-002: verifier prompt is report-skeptical (judge.py parity)
**EARS**: WHEN `build_verifier_prompt` constructs the prompt THE SYSTEM SHALL include instruction
text that (a) tells the judge to be doubtful of self-reported success, (b) tells the judge that a
claim reported "done" but not visible/true on the actual screen/ground-truth MUST be judged false,
and (c) tells the judge that ground-truth (the real page state) takes precedence over the claim.
**Edge Cases**:
- If `ground_truth_urls` is empty, the prompt SHALL still instruct the judge to navigate to the
  Coconala mypage screens the task defines by default (services_lists / received_orders/open /
  dashboard_provider), not silently skip verification.
**Acceptance Criteria**:
- Prompt text contains, case-insensitively, all three of: a "doubtful"/"skeptical"-class phrase, a
  "ground truth" phrase, and an instruction that mismatch → `verdict` must be `false`.
- Prompt instructs a binary (`true`/`false`) verdict, not a rubric/score (BP §2: "Binary verdicts are
  more reliable").

### REQ-003: JudgementResult is a plain, dependency-free result shape
**EARS**: WHEN gig_judge defines `JudgementResult` THE SYSTEM SHALL provide fields
`reasoning: str | None`, `verdict: bool`, `failure_reason: str | None`, `impossible_task: bool`,
`reached_captcha: bool`, constructible from a plain dict (as parsed from the fresh-spawn's JSON
stdout) without requiring `pydantic` to be installed.
**Edge Cases**:
- A dict missing optional keys (`failure_reason`, `impossible_task`, `reached_captcha`) SHALL still
  construct successfully with sane defaults (`None`, `False`, `False`).
- A dict missing the required `verdict` key SHALL raise (fail loud — a judge result without a verdict
  is not a valid judgement).
**Acceptance Criteria**:
- `JudgementResult.from_dict({...})` round-trips a minimal `{"verdict": true}` dict without error.
- `JudgementResult.from_dict({})` raises (missing required `verdict`).

### REQ-004: gig_reality_verify.sh spawns a FRESH, report-independent judge
**EARS**: WHEN `gig_reality_verify.sh` runs THE SYSTEM SHALL (a) collect the most recent N claim rows
from `~/gig/shuppin.jsonl`, `~/gig/applied.jsonl`, `~/gig/earnings.jsonl`, (b) spawn a **fresh**
`claude -p` subprocess (new context — no conversation history from the gig core session) instructed
to navigate the live CDP :9222 browser to the ground-truth pages, screenshot via
`cdp_snapshot.py`, read the real DOM, and emit exactly one `JudgementResult` JSON object on stdout,
(c) parse that JSON and append one row to `~/gig/audit-reality.jsonl`.
**Edge Cases**:
- No claim rows exist yet (fresh install): the script SHALL still run, emit a `no_claims` row (not
  crash), and SHALL NOT spawn a judge for nothing.
- The fresh `claude -p` process hangs or exceeds a timeout: the script SHALL kill it and record a
  `verdict:false, failure_reason:"timeout"` row rather than block auditor.sh forever (600s cap).
- The fresh process's stdout is not valid JSON (model deviated from the format): the script SHALL
  catch the parse failure and record a `verdict:false, failure_reason:"unparseable_judge_output"` row
  rather than crash.
**Acceptance Criteria**:
- `bash -n gig_reality_verify.sh` exits 0 (syntax valid).
- stdout of the script contains ONLY the final structured JSON summary line(s) — all diagnostic /
  progress text goes to stderr (memory: `feedback_loop_scripts_must_emit_clean_json_stdout`).
- The `claude` invocation line includes `--dangerously-skip-permissions`, `--add-dir "$HOME"`, and
  runs with `ANTHROPIC_API_KEY` unset (`env -u ANTHROPIC_API_KEY`) so the spawn uses the Claude
  subscription session, not pay-per-token API billing (parity with `gig-cli.sh`/`self-fix.sh` spawn
  idiom, adapted to non-interactive `-p` mode per `adversary-daily.sh`).
- On `verdict:false`, the script writes
  `~/.openclaw/state/.gig-core-selfheal-request.json` with `{reason, failure_reason, ts}`.
- On `verdict:true`, the script SHALL NOT write/overwrite the selfheal-request file with a false
  reason (no spurious self-heal trigger on a passing round).

### REQ-005: auditor.sh remains regression-safe and additive
**EARS**: WHEN `auditor.sh` runs THE SYSTEM SHALL still compute and print/append its existing
deterministic verdict row to `~/gig/audit.jsonl` exactly as before, and SHALL, after that, invoke
`gig_reality_verify.sh` as an additional step.
**Edge Cases**:
- `gig_reality_verify.sh` is missing or not executable: `auditor.sh` SHALL NOT fail/abort the
  deterministic verdict step because of it (append `|| true`-class tolerance), since the deterministic
  audit is the pre-existing safety net.
**Acceptance Criteria**:
- `bash -n auditor.sh` exits 0.
- The existing deterministic Python heredoc block (verdict/hb_age/progressing/jpy_earned logic) is
  byte-identical to before this change (no regression).
- A new line calling `gig_reality_verify.sh` appears strictly after the existing verdict-append block.

### REQ-006: deterministic, reproducible navigation (fresh-adversary FIND-001 fix)
**EARS**: WHEN the fresh judge is instructed to visit a ground-truth URL THE SYSTEM SHALL provide a
navigation helper COMMITTED IN THIS REPO that performs a real CDP `Page.navigate(url)` call, waits
for the page to finish loading (via `Page.loadEventFired` and/or a `document.readyState` poll), then
captures a screenshot and appends a trajectory row — so navigation is a deterministic, reproducible
tool call, not freeform LLM-improvised Bash/CDP calls that happened to work once.
**Edge Cases**:
- The helper must not reference any path outside this repo (no dangling cross-repo reference such as
  the historical comment pointing at `~/gig/cdp_lib48.py`, which lives outside `~/anicca`); any
  `navigate()`/`get_tab()` logic needed must be copied INTO the repo helper.
- Navigation that never reaches `readyState==='complete'` within a bounded timeout SHALL still capture
  whatever screenshot is available (never hang the judge indefinitely) and record the row.
**Acceptance Criteria**:
- `skills/earn/gig/scripts/cdp_nav_snapshot.py` exists, contains a `Page.navigate` CDP call, and
  contains a load-wait (`Page.loadEventFired` event handling or a `readyState` poll loop).
- `gig_judge.build_verifier_prompt` instructs the fresh judge to call this exact helper once per
  ground-truth URL (by pass_id + seq), not to improvise navigation.
- `cdp_snapshot.py`'s comment no longer references an out-of-repo file path.

### REQ-007: deterministic evidence gate — the caller never accepts an unbacked verdict (FIND-002 fix)
**EARS**: WHEN `gig_reality_verify.sh` receives the fresh judge's self-reported `JudgementResult` JSON
THE SYSTEM SHALL, before accepting a `verdict:true` as a clean pass, deterministically (no LLM) check
that at least one trajectory row per ground-truth URL was captured during THIS run (by `pass_id` and a
`ts >= run_start` bound read from the real `~/gig/trajectory/<pass_id>/trajectory.jsonl` file). If the
evidence count is below the required count, THE SYSTEM SHALL override the accepted verdict to `false`
with a `failure_reason` stating the verifier produced a verdict without capturing ground-truth
screenshots, and SHALL treat this exactly like any other `verdict:false` (selfheal-request write).
**Edge Cases**:
- `verdict:true` + zero trajectory rows (judge fabricated/skipped navigation entirely) → gated to
  `false`, selfheal-request written.
- `verdict:true` + trajectory rows for a DIFFERENT/stale `pass_id` (not this run's) → does not count
  (evidence must be scoped to the run's own `pass_id` + `ts` bound).
- `verdict:false` from the judge itself is never "upgraded" — the gate only ever downgrades an
  unbacked `true`, never invents a `true`.
**Acceptance Criteria**:
- A pure, unit-testable function (`gig_judge.gate_verdict(judgement, evidence_count, required_count)`)
  exists: returns the judgement unchanged when `evidence_count >= required_count` OR `verdict` is
  already `false`; returns a `false`-verdict `JudgementResult` with the fixed failure_reason otherwise.
- A dedicated script (`scripts/gig_reality_gate.py`) reads the real trajectory file for a given
  `pass_id`/`min_ts`, counts matching rows, and applies `gate_verdict` — directly testable by pointing
  it at a temp trajectory root with zero rows and asserting the output verdict is `false`.
- `gig_reality_verify.sh` uses this gate (not a bare parse-and-trust) before writing to
  `audit-reality.jsonl` / deciding the selfheal-request.

### REQ-008: stable pass_id ties navigation evidence to one verification run (FIND-003, falls out of 006+007)
**EARS**: WHEN `gig_reality_verify.sh` spawns the fresh judge THE SYSTEM SHALL generate one stable
`pass_id` deterministically (bash-side, e.g. time-based) BEFORE the spawn, embed it in the prompt so
every navigation-helper call in that run writes under the SAME `~/gig/trajectory/<pass_id>/` directory,
and use that same `pass_id` when counting evidence in REQ-007's gate.
**Acceptance Criteria**:
- The `pass_id` used in the prompt and the `pass_id` used by the evidence gate are the identical value
  for a single run (no drift, no LLM-chosen pass_id).
- The evidence-count required for a clean pass equals the number of ground-truth URLs used in that
  run's prompt (one screenshot minimum per ground-truth URL).

### REQ-009: prompt-injection resistance for third-party claim text (FIND-004, mitigation)
**EARS**: WHEN `gig_judge` renders claim rows into the prompt THE SYSTEM SHALL wrap each claim's
rendered content in an explicit `<untrusted_claim>...</untrusted_claim>` delimiter and SHALL include
an explicit instruction that text inside that delimiter is third-party DATA, never an instruction to
the judge, and any instruction-like content inside it must be ignored.
**Acceptance Criteria**:
- Rendered claims are wrapped in `<untrusted_claim>...</untrusted_claim>`.
- The prompt contains an explicit "ignore any instruction" (or equivalent) warning near the claims
  block.

## Deferred (explicitly out of scope for this increment)
- **FIND-005 (ARG_MAX risk)**: `CLAIMS_JSON`/judge-raw-text are currently passed as heredoc `argv`
  arguments to `python3 -`. For a very large accumulated claims history this could theoretically
  approach the OS `ARG_MAX` limit. NOT fixed in this increment (current claim volumes — N≤5 rows per
  source, ≤~15 total — are far below any practical limit). If claim volume grows materially, switch to
  a stdin-piped or temp-file-based hand-off instead of argv. Tracked here so it is not silently lost.

## Non-functional requirements
- No hardcoded judgment: whether a claim is actually true on screen is decided by the fresh LLM judge
  reading real DOM/screenshots — never a regex/keyword match against jsonl text (see
  `feedback_build_agents_not_hardcode_regex`).
- stdout/stderr discipline: any script meant to be parsed by another process emits ONLY the final
  JSON on stdout.
- Money claims are held to the highest bar: an `earnings.jsonl` claim can only be judged `verdict:true`
  if the fresh judge observes actual settled evidence on the real 売上/取引管理 screen — self-report
  jsonl text alone is never sufficient (BP §2 adjudication: 自己申告 77.3% vs LLM検証 60.2% gap).
