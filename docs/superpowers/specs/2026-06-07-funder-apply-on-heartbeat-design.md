# Funder-Apply on Heartbeat — sister spec to heartbeat-task-engine

**Author**: Anicca / Claude
**Date**: 2026-06-07
**Parent spec**: `2026-06-07-heartbeat-task-engine-design.md` (= "ONE heartbeat = ONE task", mission-worker dispatch, anicca-dais issue source)
**Best-practice sources** (verbatim citations):
- Sutando — `https://github.com/sonichi/sutando` — `*/5 * * * *` watcher + file-per-task + Monitor
- Conway Automaton — `https://github.com/Conway-Research/automaton` — policy engine + 3-identical-tool interrupt + treasury caps
- mini-swe-agent — `https://github.com/SWE-agent/mini-swe-agent` — linear messages + triple limit (step / cost / wall_time)
- GenericAgent — `https://github.com/lsdefine/GenericAgent` — crystallize-after-success skill emergence
**Constitution**: HARD #0 (SDD mandatory), HARD #-2 (no human/Dais loop), HARD 0.24 (no fake/dry run), HARD 0.26 (disk hygiene), HARD #15 (no rotation, fresh discovery), HARD #16 (single source of truth).

## North star (Dais 2026-06-07 verbatim)

> "you should go apply to all of them like actually right now... I'm tired of them not actually finishing the job... we would implement this task list, though, so that they can go do them here themselves too."

→ Dual track:
1. **Claude executes the urgent 5 applications today** (= FI 6/7 + Anthropic + a16z + JFC + MUFG) via direct camofox calls — evidence in `~/.openclaw/state/funder-evidence/<id>/`.
2. **Anicca's heartbeat continues the remaining 36** autonomously — funder-apply is plumbed into the existing engine as a new task type.

## What we ADD to the existing heartbeat engine

The parent spec's queue already has 4 sources. We add a 5th:

| # | Source | Format | Owner | Pre-existed |
|---|---|---|---|---|
| 1 | `anicca-dais` open issues | gh API | mission-worker | ✓ |
| 2 | `workspace/ops/tasks.json` | JSON | mission-worker | ✓ |
| 3 | `workspace/ops/steps.json` | JSON | mission-worker | ✓ |
| 4 | spec verification rows | parsed | mission-worker | ✓ |
| 5 | **`workspace/funders/tasks/<id>.md`** | **file-per-task** | **funder-apply-handler** | **NEW** |

## File-per-task layout (Sutando-style)

```
~/.openclaw/workspace/funders/
├── tasks/                            ← in queue
│   ├── FT-FI-OFFSEASON-II.md        (priority: P0, deadline today)
│   ├── FT-ANTHROPIC-BUILDER.md      (priority: P0, rolling)
│   ├── FT-A16Z-START.md             (priority: P0, rolling)
│   ├── FT-JFC-NEW-OPEN.md           (priority: P0, rolling)
│   ├── FT-MUFG-DIGITAL-ACCEL.md     (priority: P0, inside advantage)
│   └── ... (36 more, P1/P2)
├── tasks-in-progress/                ← claimed (move = lock)
├── results/                          ← per-task evidence
│   └── FT-FI-OFFSEASON-II/
│       ├── screenshot.png            ← HARD 0.24 physical proof
│       ├── dom.html                  ← snapshot at submit
│       ├── url.txt                   ← post-submit URL
│       ├── policy_decisions.jsonl    ← Conway pattern
│       └── reviewer_notes.md
├── tasks-done/                       ← completed (archive)
├── build_log.md                      ← append-only (Sutando)
└── funder-ledger.jsonl               ← canonical audit log
```

### Single task file (frontmatter + body)

```markdown
---
id: FT-FI-OFFSEASON-II
priority: P0
status: queued
deadline: 2026-06-07T23:59+09:00
crystallize_tag: apply-to-funder
limits:
  step_limit: 30
  cost_limit_usd: 1.50
  wall_time_limit_seconds: 1800
created: 2026-06-07T16:30+09:00
attempts: 0
---

Apply to https://f.inc/offseason/apply by deadline. Use ~/.openclaw/identity/application-kit/
EN materials (deck-en.pdf, Anicca_intro_EN.mp4, KIT.md EN q01-q10, profile.json,
contact@aniccaai.com, github.com/Daisuke134/anicca-oss). camofox > cloak > agent-browser order.
HARD 0.24: no fake success — must see confirmation page. Output: screenshot.png + dom.html +
url.txt to results/<this-id>/. Append funder-ledger.jsonl. Flip status to DONE only after
evidence path written. If captcha → status BLOCKED + brief append reason. If 3+ funders share
form pattern, write SKILL.md to ~/.openclaw/skills/funder-apply/ (= crystallize).
```

## Funder-apply handler (= new skill plumbing)

`mission-worker` dispatch table gets one new row:

| Task source detection | Dispatch to |
|---|---|
| label `cron:X` (issue) | fix-cron skill (existing) |
| `T-` prefix spec row | per-spec skill (existing) |
| article task | anicca-article-engine (existing) |
| **`workspace/funders/tasks/<id>.md` exists** | **funder-apply-handler (NEW)** |

Handler logic:

```python
def funder_apply_handler(task_file):
    task = parse_frontmatter(task_file)
    move_to_in_progress(task_file)

    with policy_engine(task.limits) as policy:
        with camofox_session(user_id="anicca", session_key="funder-apply") as cm:
            cm.navigate(task.url_from_brief)
            snapshot = cm.snapshot()
            fields = llm_map_fields_to_kit(snapshot, kit_path)
            for f in fields:
                cm.fill(f.ref, f.value)
            for upload in task.uploads_from_brief:
                cm.upload(upload.ref, upload.path)
            cm.click(submit_ref)
            confirmation = cm.wait_for_url_change(timeout=60)

            # HARD 0.24 enforcement
            if not confirmation.has_phrase(["thank you", "received", "ありがとう", "受付完了"]):
                raise NoConfirmationFound(snapshot=snapshot)

            cm.screenshot(results_dir/"screenshot.png")
            cm.dom_dump(results_dir/"dom.html")
            (results_dir/"url.txt").write(confirmation.url)

    append_ledger(task.id, status="submitted", evidence_path=results_dir)
    move_to_done(task_file)

    if count_recent_success(crystallize_tag="apply-to-funder") >= 3:
        emit_crystallize_event()
```

Policy engine = Conway-style: caps `cost_limit_usd`, `step_limit`, `wall_time_limit_seconds`. 3 identical tool calls in a row → forced interrupt.

## Throughput strategy

| Phase | Cron | Rate |
|---|---|---|
| Existing | `anicca-heartbeat 0 3,9,15,21 * * *` (6h) | 1 task / 6h = too slow for 41 funders |
| Add | `funder-burst-watcher */5 * * * *` (5min, ONLY when `funders/tasks/` has un-done P0/P1 + queue not draining) | 1 task / 5min during burst |
| Auto-stop | watcher exits when `funders/tasks/` empty OR all remaining are `BLOCKED` | self-deleting |

Sutando's 5-min cadence proven for personal autonomous agent.

## Skill crystallization (GenericAgent)

After **3 successful** `crystallize_tag: apply-to-funder` task results, mission-worker:

1. Reads the 3 result `dom.html` + `screenshot.png` + `policy_decisions.jsonl`
2. LLM diffs common form patterns (email, name, deck upload, video upload, submit button)
3. Writes `~/.openclaw/skills/funder-apply/SKILL.md` with frontmatter:
   ```yaml
   ---
   name: funder-apply
   description: Apply to a startup funder via web form. Crystallized 2026-06-XX from 3 wins.
   auto-activate: false
   triggers: [apply to funder, accelerator application, grant application, VC apply]
   ---
   ```
   Body = step-by-step playbook with common selector patterns + KIT.md mapping table.
4. Future task pickup checks for skill match → faster execution.

## Test plan

| # | Test | Pass criteria |
|---|---|---|
| 1 | Task file written, heartbeat picks it up | `tasks-in-progress/` contains the file within next 5-min tick |
| 2 | camofox session opens FI URL | `tabs/{id}/snapshot` returns form fields |
| 3 | No fake success (kill confirmation, expect failure) | handler exits 1, status reverts to `queued`, attempts++ |
| 4 | Real success → results dir populated | `screenshot.png` + `dom.html` + `url.txt` + ledger entry all present |
| 5 | 3 successes → crystallize fires | `~/.openclaw/skills/funder-apply/SKILL.md` exists with N≥3 evidence refs |
| 6 | Disk hygiene | results dir cap per task = 5MB (PNG max 2MB, DOM max 3MB) |

## E2E judgment

| Aspect | Method |
|---|---|
| End-to-end real | FI Off-Season II submitted today, evidence path exists, JETRO-style confirmation visible |
| No human in loop | Heartbeat picks autonomously; Dais does not see, doesn't approve per-task |
| Disk-safe | Results dir capped 5MB/task = 41 × 5MB = 205MB total worst case |

## Acceptance criteria

- [ ] `~/.openclaw/workspace/funders/{tasks,tasks-in-progress,results,tasks-done}/` directories exist
- [ ] 41 `FT-*.md` task files in `tasks/` with frontmatter + natural-language brief
- [ ] `mission-worker` dispatches `workspace/funders/tasks/*.md` → `funder-apply-handler`
- [ ] `funder-burst-watcher` cron registered (5-min, conditional)
- [ ] FI Off-Season II submitted by 2026-06-07T23:59+09:00 JST, evidence in `results/FT-FI-OFFSEASON-II/`
- [ ] `funder-ledger.jsonl` has 1+ entry with `status=submitted` and `evidence_path` set
- [ ] After 3 successful submissions, `~/.openclaw/skills/funder-apply/SKILL.md` is auto-written

## Migration

| Existing | After |
|---|---|
| `~/.openclaw/skills/apply-to-funder/` (v1, dry_run_planned) | DEPRECATE — README replaced with pointer to this spec |
| `funder-portfolio.json` (5 funders, verified flag) | RETIRE — replaced by `funders/tasks/*.md` |
| `applications/yc-w26-latest.json` `a16z-start-26-latest.json` | MIGRATE — convert to `FT-YC-W26.md` + `FT-A16Z-START.md` with status reflecting last attempt |

## Out of scope (= future, Hermes track)

Hermes (anicca-genesis) gets a parallel spec with DNA-only bootstrap. Not this PR.
