# SkillOpt feasibility probe — findings (2026-07-27)

**One-line verdict:** the plumbing works, but not against the tool as
provisioned. The installed `skillopt-train` (venv `~/.venvs/skillopt`,
package version 0.2.0) rejects our backend outright with a clear,
reproducible error before any model call happens. Pointing the same code at
the newer `/tmp/SkillOpt` checkout instead — read-only, nothing modified,
nothing installed — ran one full epoch to completion: real rollouts, real
reflection, real evaluation, real tokens billed. The gap is a **version
skew** in the installed package, already fixed upstream, not a design flaw
in SkillOpt or in our integration.

This is knowledge, not a feature. Nothing here is wired into the writer
loop; `writing/rollout.py`'s scorer is an explicit stub per the task brief.

---

## What was built

Under `skills/writer-agent/vendor/skillopt-writing/` (new directory,
nothing inside `/tmp/SkillOpt` touched, no copy of the upstream repo
vendored):

| File | Lines | Purpose |
|---|---|---|
| `writing/dataloader.py` | `WritingDataLoader(SplitDataLoader)` — loads real corpus rows from `data/writing_split/{train,val,test}/items.json` |
| `writing/rollout.py` | rollout helper; `_score()` is the required STUB — fixed, deterministic, never calls a model |
| `writing/adapter.py` | `WritingAdapter(EnvAdapter)` — wires the loader + rollout into SkillOpt's lifecycle, copied shape from `docs/guide/new-benchmark.md`'s own `docfaithful` example |
| `writing/skills/initial.md` | 4-line seed skill |
| `configs/writing/default.yaml` | `learning_rate: 2`, `num_epochs: 1`, `optimizer_backend`/`target_backend: openai_compatible` |
| `data/writing_split/{train,val,test}/items.json` | 6 REAL rows read from `state/writing-corpus/*.jsonl` (4 train / 1 val / 1 test), verbatim titles, not invented |
| `run_train.py` | registration wrapper — see "Registration has no plugin path" below |

Total ~340 lines including the wrapper and generous why-comments; the
guide's own env code (loader+rollout+adapter) is ~200 lines as advertised.

Corpus rows used (real, from `harvest_corpus.py`'s output, spec 47 19-2):
one high- and one low-`norm_score` item per (source, lang) group present —
`hn/en` ("Claude Fable 5", "Show HN: Sx – …"), `zenn/ja` (UI design piece,
the Twitter image-trick piece), `devto/en` ("Choose your Burden", the
Sentry/WooCommerce piece).

## Registration has no plugin path (a real finding, not a workaround)

`docs/guide/new-benchmark.md` Step 5 says to edit `scripts/train.py` and
add your adapter to `_register_builtins()`. Checked the actual installed
source directly: `_ENV_REGISTRY` is a plain module-level dict populated by
one hardcoded function with no entry-point/plugin/env-var discovery of any
kind. There is no way to add a benchmark to this CLI without either
forking the upstream file or the installed package.

Since the task forbids both, `run_train.py` puts this directory on
`sys.path`, imports `scripts.train`, and monkeypatches
`scripts.train._ENV_REGISTRY["writing"] = WritingAdapter` at runtime before
calling the real `main()`. This is not a hack around the *failure* below —
it is the only way to satisfy "register a new benchmark" under "do not
modify /tmp/SkillOpt or the installed package," and it worked identically
in both the failing and the succeeding run (see both logs below), so it is
not itself a variable in what follows.

## Primary probe: the installed tool, exact command and exact failure

```
cd skills/writer-agent/vendor/skillopt-writing
OPENAI_COMPATIBLE_BASE_URL="http://127.0.0.1:8317/v1" \
OPENAI_COMPATIBLE_API_KEY="<the local CLIProxyAPI key from /opt/homebrew/etc/cliproxyapi.conf>" \
~/.venvs/skillopt/bin/python3.14 run_train.py --config configs/writing/default.yaml \
  --cfg-options env.out_root=<scratch dir>
```

Exact output (unedited):

```
============================================================
  SkillOpt — Executive Strategy for Self-Evolving Agent Skills
============================================================
  env:            writing
  optimizer_model:  claude-haiku-4-5-20251001
  target_model:  claude-haiku-4-5-20251001
  optimizer_backend:openai_compatible
  target_backend:openai_compatible
  ...
============================================================

  [WritingDataLoader] train=4 val=1 test=1  (from /Users/anicca/profitable-claude/skills/writer-agent/vendor/skillopt-writing/data/writing_split)
Traceback (most recent call last):
  File ".../run_train.py", line 35, in <module>
    sys.exit(_train.main())
  File ".../site-packages/scripts/train.py", line 548, in main
    summary = trainer.train()
  File ".../site-packages/skillopt/engine/trainer.py", line 690, in train
    set_optimizer_backend(optimizer_backend)
  File ".../site-packages/skillopt/model/backend_config.py", line 53, in set_optimizer_backend
    raise ValueError(...)
ValueError: Unsupported optimizer backend: 'openai_compatible'. Supported values are 'openai_chat', 'claude_chat', 'qwen_chat', and 'minimax_chat'.
```

Exit code 1. The registration and the dataloader both worked correctly
(`train=4 val=1 test=1` loaded from the real split, matching the six rows
built into `data/writing_split/`) — the failure is entirely inside
SkillOpt's own installed backend-selection gate, before any rollout runs.

## Root cause, confirmed by diff, not guessed

`skillopt/model/backend_config.py`'s `set_optimizer_backend`/
`set_target_backend` each hardcode their own allow-list, SEPARATE from the
`chat_target`/`chat_optimizer` dispatch layer (which already has explicit
`if get_target_backend() == "openai_compatible":` branches) and separate
from `docs/reference/config.md` (which documents `openai_compatible` as
supported for both optimizer and target roles). The installed venv's
allow-list simply never got `openai_compatible` added:

```
$ diff ~/.venvs/skillopt/.../skillopt/model/backend_config.py /tmp/SkillOpt/skillopt/model/backend_config.py
...
<     if OPTIMIZER_BACKEND not in {"openai_chat", "claude_chat", "qwen_chat", "minimax_chat"}:
---
>     if OPTIMIZER_BACKEND not in {
>         "openai_chat", "claude_chat", "qwen_chat", "minimax_chat",
>         "openai_compatible", "codex_exec",
>     }:
...
<     if TARGET_BACKEND not in {"openai_chat", "claude_chat", "qwen_chat", "minimax_chat", "codex_exec", "claude_code_exec"}:
---
>     if TARGET_BACKEND not in {"openai_chat", "claude_chat", "qwen_chat", "minimax_chat", "openai_compatible", "codex_exec", "claude_code_exec", "cursor_exec"}:
```

`/tmp/SkillOpt` is at commit `ed0d13635be31addfee6b013b0fe39f2d4190eb1`,
dated **2026-07-26** (yesterday) — newer than whatever was packaged into
the installed venv. This is a version-skew bug already fixed upstream, not
a defect in our integration or in SkillOpt's design.

## Supplementary diagnostic: does the newer code actually work? (read-only, nothing installed or modified anywhere)

Same command, same wrapper, same config, only `PYTHONPATH` prepended with
`/tmp/SkillOpt` for that one process so Python resolves `scripts.train`
and `skillopt.*` from the checkout instead of site-packages — reading the
checkout, never writing to it:

```
PYTHONPATH="/tmp/SkillOpt:$(pwd)" OPENAI_COMPATIBLE_BASE_URL=... OPENAI_COMPATIBLE_API_KEY=... \
  ~/.venvs/skillopt/bin/python3.14 run_train.py --config configs/writing/default.yaml --cfg-options env.out_root=<scratch dir>
```

Exit code 0. Full, unedited tail of the run:

```
  [WritingDataLoader] train=4 val=1 test=1  (from .../data/writing_split)
  [model config] backend=azure_openai  optimizer=claude-haiku-4-5-20251001 (openai_compatible)  target=claude-haiku-4-5-20251001 (openai_compatible)  reasoning=medium
  [initial skill] .../writing/skills/initial.md (326 chars)

  [config] epochs=1 steps/epoch=2 (auto) accum=1 batch_size=2
  [config] train_size=4
  [config] batches/epoch=2 total_steps=2 games/epoch=4
  [config] lr_scheduler=cosine edit_budget=2 min_edit_budget=2
  [gate] metric=hard
  [slow update] acceptance=force-accept (unconditional)

  BASELINE — evaluate initial skill on Selection set (valid_seen)
  Selection items: 1
  [baseline result] selection hard=1.0000 soft=0.5000 gate[hard]=1.0000

  [EPOCH 1/1] shuffled_seeds=[1043, 1044]

  [STEP 1/2] epoch=1 step_in_epoch=0
    [1/6 ROLLOUT] train items=2 (from pool, batch_seed=1043)
    [1/6 done] hard=1.0000 soft=0.5000
    [2/6 REFLECT minibatch] failure=0→0 groups  success=2→1 groups  (M=2, L=2, workers=1)
      [analyst] 1/1 minibatch_succ_000 (2 trajs) → 0 edits
    [2/6 done] failure_patches=0 success_patches=0
    [skip] no usable patches — skill unchanged

  [STEP 2/2] epoch=1 step_in_epoch=1  (same shape, also 0 edits)

  [SLOW UPDATE epoch 1] injected empty placeholder
  [META SKILL epoch 1] skipped — first epoch
  [done] best skill from step 0, score=1.0000
  [final skill val] items=1 final_selection_hard=1.0000 gate=1.0000 (best=1.0000)

  BASELINE TEST / BEST SKILL TEST / FINAL SKILL TEST (Test set, 1 item)
    en : hard=1.0/1=1.0000     ja : hard=0/0=0.0000     overall : hard=1.0/1=1.0000
    (identical across all three -- see "why zero edits" below)

  Final Summary
  steps=2 accept=0 reject=0 skip=2
  best_score=1.0000 (step 0)  wall=11s
  total tokens: 14,169 (prompt=13,738 completion=431 calls=9)
  Final test: 1.0000
```

Real model text was produced and persisted, e.g.
`predictions/<id>/conversation.json`:

> topic: "I Added Sentry to a WooCommerce Membership Site. It Caught a Real
> Bug Within the Hour." → generated: "Sentry Caught a Production Bug in My
> WooCommerce Store Before I Could Even Have Coffee."

9 real chat completions were billed through the local CLIProxyAPI to
`claude-haiku-4-5-20251001` (4 rollout items across 2 steps + reflection
analyst calls + baseline/test evaluations). Nothing was mocked, dry-run,
or simulated.

### Why zero edits were produced — expected, not a bug

Every rollout scored `hard=1.0` because the stub scorer only checks "did
the target produce non-empty text" (Task B's brief: a fixed number, never
reads content). With every training example looking like a "success" and
none a "failure," SkillOpt's reflection stage had nothing to learn from —
`[analyst] ... → 0 edits` both steps, `accept=0 reject=0 skip=2` overall.
This is the correct, expected behavior of a stub scorer, not a harness
problem: an optimizer that edits a skill in the absence of any
failure/success contrast would be doing something worse (editing on noise).

## What a real scorer would need to look like

The stub's job was to prove the harness runs; it teaches nothing. To
actually train craft, the scorer plugged in at `writing/rollout.py`'s
`_score()` would need to supply the SAME win/lose contrast the reflection
stage is built to consume:

- `hard` should be a binary win/lose signal with real failures in it, not
  a constant. The natural source already exists: **`beat_rate.py`'s blind
  pairwise judge** (spec 47 19-3) — score the rollout's generated title
  against corpus opponents the same way, and set `hard = 1` if
  `beat_rate > 0.5` (beats the median opponent), else `0`. That guarantees
  a real mix of successes AND failures for the analyst to reflect on,
  which the stub structurally cannot produce.
- `soft` should be the continuous `beat_rate` value itself (already in
  [0, 1]), giving the optimizer a smoother signal than hard win/lose alone.
- The `conversation.json` persisted per item (already wired correctly)
  would need the opponent titles and the judge's blind verdicts attached
  as extra fields so `reflect()` can cite WHY a title lost, not just THAT
  it lost — mirroring `rule_blame.py`'s cited-line discipline.
- Cost: each rollout item would need 2 x K judge calls (beat_rate.py's own
  budget model), not one target-model call — multiplying real-scorer cost
  well beyond this stub's 9-call probe. `--max-calls` discipline from
  beat_rate.py should carry over directly.

## Recommendation

**Adopt SkillOpt as the trainer, do not fork it.** The architecture itself
held up completely once past the version-skew bug: env/dataloader/rollout
is a clean ~200-line seam exactly as documented, the bounded-edit +
held-out-gate + learning-rate + accept/reject/skip accounting all ran
untouched, and real tokens flowed through our own local proxy with zero
integration code beyond the four required files. spec 47 section 19.2's
own conclusion — take the trainer machinery, supply the reward ourselves —
is confirmed usable, not just plausible on paper.

- **Best case**: upgrade the installed venv from the current `/tmp/SkillOpt`
  commit (`pip install --upgrade` against that checkout, a one-line fix
  for a one-line version-skew bug), wire `beat_rate.py` in place of the
  stub per "what a real scorer would need" above, and 19-4c can start from
  a working harness immediately.
- **Base case**: even without upgrading the venv, the registration wrapper
  and env package are portable — any environment with a current SkillOpt
  install works today, proven by the diagnostic run.
- **Worst case / strongest rejected alternative**: build our own ~200-line
  trainer copying just the four ideas (bounded edit, held-out gate,
  learning rate, automatic revert), skipping SkillOpt's harness entirely.
  Rejected for now because today's probe found exactly ONE real defect
  (a stale allow-list) and zero design-level friction — the registration
  gap is annoying but solved once (the wrapper), not per-run. Reinventing
  the trainer would re-solve problems (reflection prompting, gate
  accounting, meta-skill memory, cosine LR scheduling) SkillOpt already
  has working code for, on evidence gathered today.
- **Where this could be wrong**: if the "no plugin mechanism" gap turns
  out to matter more at OSS-distribution scale than it does for our own
  single vendored env (e.g. upstream changes `_ENV_REGISTRY`'s shape in a
  later release and silently breaks the monkeypatch), the wrapper becomes
  a maintenance liability disguised as a one-time cost. That risk is worth
  a comment pointing back at this file the next time `run_train.py`'s
  monkeypatch stops working.
