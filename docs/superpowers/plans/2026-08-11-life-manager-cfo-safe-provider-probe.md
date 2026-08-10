# CFO-2a2b.5c2b Safe Provider Probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan
> task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Sol owns this plan, review, state, commit, and push;
> Luna alone writes production code and tests.

**Goal:** Give the existing `ai.anicca.life-manager-daily` route one explicit provider-only mode that records real
Life Manager attempt/usage rows without generating media, posting, messaging, paying, or mutating business state.

**Architecture:** Reuse the existing portable runner, usage ledger, adjacent attempt ledger, output schema, and
`diagnostic-agent` read-only Codex command. Add one early shell branch before the generator. The branch pins Codex,
uses a newly created empty owner-controlled workdir, invokes exactly one diagnostic pass, and propagates the exact
status returned by `run_agent.sh`.

**Tech Stack:** Bash, Python `unittest`, existing `run_agent.sh`, existing portable `agent_runner.py`.

## Global Constraints

- Ponytail `full`: existing paths only; no new file, helper, dependency, service, DB, scheduler, queue, retry, or agent.
- One task, exactly three existing files, hard maximum **95 gross added LOC**.
- Soft targets: daily shell `+24`, wrapper `+1`, runtime test `+55`; delete/reuse before exceeding them.
- The safe branch runs before generator/distributor/self-improver/marketing ledger/Telegram/success-marker effects.
- `diagnostic-agent` is mandatory because existing `command_for` gives it `--sandbox read-only`; never use the
  unsandboxed `marketing-agent` for this probe.
- `ANICCA_USAGE_LEDGER` is the existing `LM_DAILY_USAGE_LEDGER`; the existing runner derives the adjacent
  `agent-usage-attempts.jsonl`. Clear any inherited `ANICCA_USAGE_ATTEMPT_LEDGER` override. Do not invent or copy
  token/cost values.
- Luna does not stage, commit, push, call a real provider, write a live ledger, edit launchd, or send Telegram.

---

### Task 1: Wire one read-only Life Manager provider probe

**Files:**
- Modify: `skills/life-manager/life-manager-daily.sh`
- Modify: `skills/earn/marketing-engine/run_agent.sh`
- Test: `skills/video/tests/test_life_manager_daily_runtime.py`

**Interfaces:**
- Consumes: `LIFE_MANAGER_SAFE_PROBE_ONLY=1`, `LM_DAILY_USAGE_LEDGER`, optional
  `LM_SAFE_PROBE_WORKDIR`, optional `LM_DAILY_EVIDENCE_DIR`, and existing `RUN_AGENT_BIN`/`AGENT_RUNNER_BIN` seams.
- Produces: one `diagnostic-agent` invocation with task label `life-manager-safe-probe`, loop `life-manager`, exact
  `run_agent.sh` exit status, and no later daily-loop effect.

- [ ] **Step 1: Write the failing integration test**

Add this one test to `LifeManagerDailyRuntimeTest`; it uses the real shell wrapper and a local Python provider stub:

```python
    def test_safe_provider_probe_uses_diagnostic_route_before_marketing_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "home"
            home.mkdir()
            capture = root / "capture.json"
            generator_marker = root / "generator-called"
            generator = executable(
                root / "generator",
                "#!/usr/bin/env bash\n: >\"$GENERATOR_MARKER\"\nexit 91\n",
            )
            provider = root / "provider.py"
            provider.write_text(
                "import json,os,pathlib,sys\n"
                "a=sys.argv[1:]\n"
                "v=lambda k:a[a.index(k)+1]\n"
                "p=pathlib.Path(v('--prompt-file')).read_text()\n"
                "pathlib.Path(os.environ['CAPTURE_PROVIDER']).write_text(json.dumps({"
                "'task_class':v('--task-class'),'task_label':v('--task-label'),"
                "'loop':v('--loop'),'workdir':v('--workdir'),'prompt':p,"
                "'usage':os.environ.get('ANICCA_USAGE_LEDGER'),"
                "'attempt_override':os.environ.get('ANICCA_USAGE_ATTEMPT_LEDGER'),"
                "'provider':os.environ.get('AGENT_RUNNER_PROVIDER')}))\n"
                "raise SystemExit(int(os.environ.get('PROVIDER_RC','0')))\n",
                encoding="utf-8",
            )
            env = os.environ.copy()
            env.update({
                "HOME": str(home),
                "LIFE_MANAGER_SAFE_PROBE_ONLY": "1",
                "LM_VIDEO_GENERATOR": str(generator),
                "RUN_AGENT_BIN": str(ROOT / "skills/earn/marketing-engine/run_agent.sh"),
                "AGENT_RUNNER_BIN": str(provider),
                "LM_DAILY_USAGE_LEDGER": str(root / "agent-usage.jsonl"),
                "LM_DAILY_RUN_LEDGER": str(root / "daily-runs.jsonl"),
                "LM_SAFE_PROBE_WORKDIR": str(root / "workdir"),
                "LM_DAILY_EVIDENCE_DIR": str(root / "evidence"),
                "ANICCA_USAGE_ATTEMPT_LEDGER": str(root / "poison-attempts.jsonl"),
                "CAPTURE_PROVIDER": str(capture),
                "GENERATOR_MARKER": str(generator_marker),
            })
            result = subprocess.run(["bash", str(DAILY)], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            row = json.loads(capture.read_text(encoding="utf-8"))
            self.assertEqual(row["task_class"], "diagnostic-agent")
            self.assertEqual(row["task_label"], "life-manager-safe-probe")
            self.assertEqual(row["loop"], "life-manager")
            self.assertEqual(row["workdir"], str(root / "workdir"))
            self.assertEqual(row["usage"], str(root / "agent-usage.jsonl"))
            self.assertIsNone(row["attempt_override"])
            self.assertEqual(row["provider"], "codex")
            self.assertIn("Do not use tools", row["prompt"])
            self.assertIn("do not access files or the network", row["prompt"])
            self.assertFalse(generator_marker.exists())
            self.assertFalse((root / "daily-runs.jsonl").exists())
            self.assertFalse((home / ".local/state/life-manager/state/.life-manager-core-last-pass").exists())
            env.update({
                "LM_SAFE_PROBE_WORKDIR": str(root / "failed-workdir"),
                "LM_DAILY_EVIDENCE_DIR": str(root / "failed-evidence"),
                "CAPTURE_PROVIDER": str(root / "failed-capture.json"),
                "PROVIDER_RC": "23",
            })
            failed = subprocess.run(["bash", str(DAILY)], env=env, text=True, capture_output=True)
            self.assertEqual(failed.returncode, 23, failed.stderr)

            occupied = root / "occupied-workdir"
            occupied.mkdir()
            env.update({
                "LM_SAFE_PROBE_WORKDIR": str(occupied),
                "LM_DAILY_EVIDENCE_DIR": str(root / "blocked-evidence"),
                "CAPTURE_PROVIDER": str(root / "blocked-capture.json"),
                "PROVIDER_RC": "0",
            })
            blocked = subprocess.run(["bash", str(DAILY)], env=env, text=True, capture_output=True)
            self.assertEqual(blocked.returncode, 2)
            self.assertEqual(blocked.stderr, "life-manager-safe-probe: workdir unavailable\n")
            self.assertFalse((root / "blocked-capture.json").exists())
```

- [ ] **Step 2: Run RED and retain the expected failure**

Run:

```bash
python3 -m unittest \
  skills.video.tests.test_life_manager_daily_runtime.LifeManagerDailyRuntimeTest.test_safe_provider_probe_uses_diagnostic_route_before_marketing_effects
```

Expected: FAIL with return code `91`; the fail-fast generator marker exists and no `capture.json` exists.

- [ ] **Step 3: Open the existing read-only route in the thin wrapper**

Change only the whitelist case in `skills/earn/marketing-engine/run_agent.sh`:

```bash
  repeatable-agent|tool-agent|browser-lane-agent|diagnostic-agent|marketing-agent|high-value-agent) ;;
```

- [ ] **Step 4: Add the minimal early branch**

Immediately after the existing `AGENT_WIRING_PROBE_ONLY` branch in `life-manager-daily.sh`, add exactly this branch:

```bash
if [ "${LIFE_MANAGER_SAFE_PROBE_ONLY:-0}" = "1" ]; then
  SAFE_WORKDIR="${LM_SAFE_PROBE_WORKDIR:-$LM_DATA_ROOT/state/agent-runner-safe-probe-workdir/$(date +%s)-$$}"
  SAFE_EVIDENCE_DIR="${LM_DAILY_EVIDENCE_DIR:-$LM_DATA_ROOT/state/agent-runner-evidence/life-manager-safe-probe/$(date +%s)-$$}"
  if ! mkdir -p "$(dirname "$SAFE_WORKDIR")" 2>/dev/null || ! mkdir "$SAFE_WORKDIR" 2>/dev/null; then
    printf 'life-manager-safe-probe: workdir unavailable\n' >&2
    exit 2
  fi
  export ANICCA_USAGE_LEDGER="$USAGE_LEDGER"
  unset ANICCA_USAGE_ATTEMPT_LEDGER
  export AGENT_RUNNER_PROVIDER="codex"
  SAFE_PROMPT='Return exactly {"status":"ok","evidence":["provider response received"]}. Do not use tools; do not access files or the network; do not send messages, publish, purchase, or mutate anything.'
  printf '%s\n' "$SAFE_PROMPT" | "$RUN_AGENT" --task-class diagnostic-agent \
    --evidence-dir "$SAFE_EVIDENCE_DIR" --task-label life-manager-safe-probe \
    --loop life-manager --workdir "$SAFE_WORKDIR" >>"$LOG" 2>&1
  exit $?
fi
```

- [ ] **Step 5: Run GREEN and regression gates**

Run:

```bash
python3 -m unittest \
  skills.video.tests.test_life_manager_daily_runtime.LifeManagerDailyRuntimeTest.test_safe_provider_probe_uses_diagnostic_route_before_marketing_effects
python3 skills/video/tests/test_life_manager_daily_runtime.py
python3 -m unittest skills.earn.marketing-engine.test_capafy_loop_wiring
PYTHONPATH=runtime/agent-runner python3 -m unittest discover -s runtime/agent-runner/tests -p 'test_*.py'
bash -n skills/life-manager/life-manager-daily.sh skills/earn/marketing-engine/run_agent.sh
python3 -m py_compile skills/video/tests/test_life_manager_daily_runtime.py
git diff --check
```

Expected: focused `1/1`, daily runtime `9/9`, wrapper wiring `6/6`, portable runner `18/18`, syntax and diff checks PASS.

- [ ] **Step 6: Verify scope and hand back to Sol**

Require exactly the three owned files, no real provider process, and `<=95` gross additions. Report RED/GREEN,
exact diff counts, and any concern. Do not stage or commit; Sol performs fresh review, verification, commit, push,
spec state, Telegram milestone, and the bounded live rollout in 5c2c.
