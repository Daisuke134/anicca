# Spec: anicca-cron-doctor v2 + R-4 batch + R-11 LEARNINGS

| meta | value |
|---|---|
| parent specs | `2026-06-04-cron-rat-proof-architecture-design.md` (v2 OpenClaw-all-the-way) + `2026-06-04-cron-doctor-design.md` (v1) |
| scope | Claude-owned remaining R-tasks: R-4, R-6, R-7, R-8, R-9, R-11, R-13, R-14, R-15 |
| out of scope | R-1, R-2 (Dais billing), R-3 (auto observation), R-5 (doctor handles ongoing), R-10 (社外 PR), R-12 (CFO sync separate) |
| date | 2026-06-04 22:00 JST |
| directive | `/goal` hook: "Superpowers implemented end to end... make the spec and then implement it end to end." |

## 1. Why v2

v1 doctor は L1-L6 phase で 26+35 = 61 件の "Read SKILL.md" prompt を rewrite した。 然し v2 で対応すべき 9 件の落ち穂が残った (= 15 R-tasks のうち Claude 担当 9 件):

| R | gap |
|---|---|
| R-4 | 34 件の context-bearing cron (target/language/EXACTLY context あり) が L1 skip。 1 回手動 migrate して context-preserving wrapper 形にする必要 |
| R-6 | streak counter が「今回 detect されない = リセット」 → 23h gap で streak が 1 ずつしか積めない。 24h sliding window に refactor |
| R-7 | L1 skipped_complex 34 件の manual review queue が Slack 1 行しか出てない → 週次 digest (= 月曜 detail dump) |
| R-8 | bounty 1 fire ≒ 69k tokens × 1日12回 ≒ 828k tokens/day。 月予算 guard 無し → cron-codex.sh に budget check |
| R-9 | doctor が jobs.json を書換えるが git push 無し → diff lost on Mac Mini DR |
| R-11 | 18:20 incident post-mortem が learnings に未記録 → 同じパターンを次回繰り返すリスク |
| R-13 | openclaw.json の primary model が memory rule 違反したら警告無し → 静かに gpt-5.5 fallback に行く |
| R-14 | cron list の `lastRunStatus: error` が delivery-only false positive で Dais 混乱 → 注釈必要 |
| R-15 | `openclaw cron edit --message` が複数行 / 特殊文字でシェル quoting 失敗 → python subprocess helper module 集約 |

## 2. Design

### 2.1 Module structure (= isolation boundaries)

```
~/.openclaw/skills/anicca-cron-doctor/
├── SKILL.md                    [updated v2 description]
├── scripts/
│   ├── run.sh                  [unchanged — orchestrator]
│   ├── phases.py               [refactored — L1..L7 + delegates to helpers]
│   ├── format_report.py        [updated — L7 + false-positive注釈]
│   ├── helpers/                ★NEW dir
│   │   ├── __init__.py
│   │   ├── cron_edit.py        ★R-15: python wrapper around openclaw cron edit
│   │   ├── streak_window.py    ★R-6: 24h sliding-window streak math
│   │   ├── token_budget.py     ★R-8: shared token spend tracking
│   │   ├── git_sync.py         ★R-9: jobs.json auto-commit+push
│   │   └── config_audit.py     ★R-13: openclaw.json model rule check
│   └── digest-weekly.sh        ★R-7: weekly Monday rollup of skipped_complex
├── data/
│   ├── revenue-critical.json   [unchanged]
│   ├── refusal-streak.json     [schema migration: int → [ts1,ts2,...]]
│   ├── l3-last-refire.json     [unchanged]
│   ├── reports/YYYY-MM-DD.json [extended schema: L7 added]
│   └── digests/YYYY-MM-DD.json ★R-7: weekly archive
└── templates/                  [deleted — was launchd.plist.tmpl]
```

`~/.openclaw/skills/_dispatcher/scripts/cron-codex.sh` — minor: token budget guard inserted at head.

`~/.openclaw/.learnings/LEARNINGS.md` ★R-11: append session post-mortem entry.

### 2.2 Per-task design

| R | implementation detail |
|---|---|
| R-15 | `helpers/cron_edit.py::edit_message(cron_id, new_msg) -> bool`。 subprocess.run with list-args (no shell), captures stderr, returns True on rc==0. All phases (L1, L5) switch to this. Idempotent — checks if same message already set before invoking. |
| R-6 | `helpers/streak_window.py::tick_streak(name, refused_now, window_seconds=86400) -> int`。 Reads `refusal-streak.json` shaped as `{name: [timestamp,...]}`. Adds `now` if refused_now=True. Drops timestamps older than window. Returns len(remaining). Migration: on first load, detect old int-schema and convert to single-element list with current time. |
| R-8 | `helpers/token_budget.py::check_budget(skill, est_tokens=80000)`。 Reads `~/.openclaw/.env::OPENAI_MONTHLY_BUDGET_USD` (default $50), reads `data/openai-spend.json` accumulator. Computes spend_so_far_usd (= sum tokens × $/1k from a per-model rates table). If spend + est_tokens > 80% of budget → return False (caller skips + posts warning). cron-codex.sh sources this before launching codex exec. |
| R-9 | `helpers/git_sync.py::commit_and_push(message) -> bool`。 cd ~/.openclaw && git diff --quiet cron/jobs.json (= changed?) → if changed: add cron/jobs.json + add data/refusal-streak.json + add data/l3-last-refire.json + add data/reports/Y-M-D.json + commit + push. Runs at the END of run.sh after L6. |
| R-4 | Separate one-shot script: `scripts/migrate-context-bearing.sh`. Reads jobs.json backup from `cron/jobs.json.bak-phaseA-20260604-202021`. For each of 34 affected crons: extracts skill name + the non-Read context (= everything except the Read SKILL.md line + canonical "Execute X skill" preamble). Writes new prompt = `bash $HOME/.openclaw/skills/_dispatcher/scripts/cron-codex.sh <skill> "<extra_context_quoted>"`. Updates via cron_edit helper. Idempotent — skips if already _dispatcher form. Reports applied/skipped count + diff to Slack. cron-codex.sh `[extra prompt]` arg → appended to codex prompt. |
| R-11 | `~/.openclaw/.learnings/LEARNINGS.md` append entry: date 2026-06-04, title "Cron rat-proof — OpenClaw-all-the-way pivot". Core lesson: "Anicca has 5+ tool paths. Defaulting to launchd-only on cron failure was lazy escape (HARD RULE #-1 violation). Real answer: stay inside the user's chosen runtime (OpenClaw) and reduce the LLM decision surface to a single deterministic exec call." Concrete commands inventory: cron-bash.sh + cron-codex.sh wrapper template, jobs.json edit pattern, gateway hot-reload race workaround. |
| R-13 | `helpers/config_audit.py::audit_model_config() -> dict`。 Reads `~/.openclaw/openclaw.json::agents.defaults.model`. Compares against allowlist (= memory rule canonical = `deepseek/deepseek-v4-pro` primary preferred, `openai-codex/gpt-5.4-mini` acceptable). Returns `{primary, fallbacks, drift_detected: bool, violations: [...]}`. New L7 phase in phases.py invokes this. L6 format includes "L7 config drift" line. |
| R-14 | `format_report.py`: when reporting cron with `lastRunStatus=error` and `delivery=not-requested`, append annotation "(delivery skipped intentionally — actual cron status OK if Slack post received)". Requires fetching per-cron metadata via openclaw cron get during L6. |
| R-7 | `scripts/digest-weekly.sh`: separate cron entry, OpenClaw cron `0 4 * * 1 Asia/Tokyo` (Monday 04:00 JST). Reads last 7 days of `data/reports/*.json`. Aggregates: total L1 fixed, total L3 retries, full skipped_complex list with manual-review suggestion per cron. Posts to Slack as a thread under that week's first :stethoscope: doctor message. |

### 2.3 Data flow

```
[nightly OpenClaw cron 03:00 JST anicca-cron-doctor]
     │
     ▼
[run.sh] sources .env, ensures dirs, calls phases.py + format_report.py
     │
     ▼
[phases.py]
  L1 prompt lint  → cron_edit.edit_message() for matching crons
  L2 path lint    → classify-only
  L3 refusal retry → cron_edit.refire() (rate-limit via l3-last-refire.json)
  L4 streak monitor → streak_window.tick_streak() for each detected
  L5 hard escalate → cron_edit.edit_message() to cron-codex.sh wrapper
  L7 config drift → config_audit.audit_model_config()
     │
     ▼
[format_report.py] reads report.json, slack-formats, adds annotations
     │
     ▼
[run.sh tail]
  - posts L6 Slack message via SLACK_BOT_TOKEN chat.postMessage
  - calls git_sync.commit_and_push() to persist diff


[weekly OpenClaw cron 04:00 JST Monday anicca-cron-doctor-digest]
     │
     ▼
[digest-weekly.sh]
  reads ~7 reports, aggregates, posts to Slack thread


[per cron-codex.sh invocation]
     │
     ▼
[cron-codex.sh head]
  source .env, inject OPENAI_API_KEY
  python -c "from .helpers.token_budget import check_budget; check_budget('<skill>')" || exit 0
  (skip cleanly if budget exceeded, post warning to Slack)
     │
     ▼
[codex exec runs as before]
```

### 2.4 Error handling

| Failure mode | Behavior |
|---|---|
| `cron_edit.edit_message` rc != 0 | log to skipped_errors, continue, report in L6 |
| `git_sync` push fails | continue (no abort) — log to Slack as `:warning: cron-doctor git push failed: <err>` |
| `token_budget` corrupt JSON | reset to {}; report in next run.sh |
| `config_audit` reads broken openclaw.json | skip L7, log warning, continue |
| cron-codex.sh budget guard skip | exit 0 (not failure), post `:money_with_wings: skipped <skill>: budget < threshold` |

### 2.5 Testing strategy (= TDD per HARD RULE #0)

| Layer | Test |
|---|---|
| `cron_edit.py` | unit: mock subprocess, assert correct CLI args. integration: real edit + read-back. |
| `streak_window.py` | unit: edge cases (empty, expired-only, fresh+expired mix, schema migration). |
| `token_budget.py` | unit: budget within / over / corrupt JSON. |
| `git_sync.py` | integration: actual git commands in ~/.openclaw, verify commit on top of HEAD. |
| `config_audit.py` | unit: in-compliance config, drift case, corrupt JSON. |
| `migrate-context-bearing.sh` | integration: run on 1 cron (= larry-trend-hunter-ja), verify message contains "target: larry-ja" pass-through. |
| `phases.py` | dry-run mode untouched + actual cycle 1 vs cycle 2 idempotency check. |
| `digest-weekly.sh` | integration: with fake report files for 7 days, verify aggregation count. |
| `format_report.py` | unit: report dict → expected Slack lines. |

## 3. Verification matrix

| AC | What | How |
|---|---|---|
| AC-V1 | R-15 cron_edit helper exists + all phases use it | grep for `subprocess.run.*openclaw.*cron.*edit` outside helpers/ returns 0 |
| AC-V2 | R-6 streak_window in place | `refusal-streak.json` schema = `{name: [timestamps]}`, tests pass |
| AC-V3 | R-8 budget guard wired in cron-codex.sh | dry-run with fake OPENAI_MONTHLY_BUDGET_USD=0.01 → exits 0 + posts Slack warn |
| AC-V4 | R-9 doctor auto-commit | after `bash run.sh`, `git log -1 ~/.openclaw` shows new commit by cron-doctor |
| AC-V5 | R-4 batch migration applied | 34 affected crons all have `_dispatcher/scripts/cron-codex.sh` in their payload.message with context preserved as 2nd arg. larry-trend-hunter-ja shows `"target: larry-ja"` in 2nd arg |
| AC-V6 | R-11 LEARNINGS entry written | `grep -c "2026-06-04.*Cron rat-proof" .learnings/LEARNINGS.md` ≥ 1 |
| AC-V7 | R-13 L7 reports config drift | Slack report L7 line present in 1 doctor fire |
| AC-V8 | R-14 false-positive annotation | next doctor report contains annotation line when applicable |
| AC-V9 | R-7 weekly digest cron registered | `openclaw cron list \| grep anicca-cron-doctor-digest` returns 1 row |
| AC-V10 | end-to-end | `openclaw cron run <doctor-id> --wait --expect-final` → Slack `:stethoscope:` + auto-commit shows in git log |

## 4. Out-of-scope (= HARD RULE #0 strict)

- launchd plist 復活 (= v2 spec で全廃済)
- main session systemEvent path 復活 (= Anthropic credit refill 待ち、 R-2 separate)
- OpenClaw 本体 PR (= R-10 separate work)
- visual / UI changes — terminal-only flow

## 5. Risks & mitigations

| Risk | Mitigation |
|---|---|
| 34 件 batch migration が 1 件失敗で blocks 全体 | per-cron try/except, accumulate failures, report at end |
| token_budget の単価表が古くなる | rates inline + `last_updated` timestamp + warn if > 90 days old |
| streak_window 移行で過去 state 失う | first load: detect int → convert to `[time.time()]`, log migration |
| git_sync が conflict | abort push, log error, continue (data still in jobs.json) |
| weekly digest token cost | digest はテキスト集計のみ、 LLM 不使用、 cost = $0 |

## 6. References

- parent spec: `docs/superpowers/specs/2026-06-04-cron-rat-proof-architecture-design.md` (v2)
- v1 doctor spec: `docs/superpowers/specs/2026-06-04-cron-doctor-design.md`
- HARD RULE #-1 / #-2 / #0 / 0.4 / 0.12 / 0.14: `CLAUDE.md`
- OpenAI pricing: https://openai.com/pricing (for token_budget rate table)
- session goal: Superpowers implemented end-to-end (Dais 2026-06-04 22:00 JST)

## 7. Change log

| date | change |
|---|---|
| 2026-06-04 22:00 JST | v2 design — bundles R-4/R-6/R-7/R-8/R-9/R-11/R-13/R-14/R-15 in one spec |
