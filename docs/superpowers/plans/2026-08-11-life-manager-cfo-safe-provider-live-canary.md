# CFO-2a2b.5c2c1 Safe Provider Live Canary Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:verification-before-completion. This is a Sol-owned
> operational gate; Luna writes no code in this sub-slice.

**Status:** READY FOR SOL REVIEW

**Goal:** Use the existing `ai.anicca.life-manager-daily` launchd identity to append one real Life Manager attempt
and one same-ID completion to the CFO's canonical telemetry pair, without running any marketing or messaging work.

**Architecture:** While the job is idle, temporarily point only its plist script path to reviewed feature commit
`8554a6616`, set the existing safe-probe flag, and set `LM_DAILY_USAGE_LEDGER` to the CFO canonical telemetry file.
Bootstrap a separate temporary plist and kickstart that one label, verify appended bytes only, then reload the
untouched original plist on every outcome.

**Tech Stack:** launchd, Bash, existing portable runner, local append-only JSONL, Node/Python read-only validation.

## Global constraints

- Ponytail `full`: no code, test, DB, service, scheduler, dependency, new label, manual runner, or fake row.
- Exact label: `ai.anicca.life-manager-daily`; it must be idle before mutation.
- Exact reviewed script:
  `/Users/anicca/Projects/life-manager-main/.worktrees/cfo-agent-usage-cutover/skills/life-manager/life-manager-daily.sh`.
- Exact canonical usage file: `/Users/anicca/.local/state/life-manager/telemetry/agent-usage.jsonl`; the runner must
  derive `/Users/anicca/.local/state/life-manager/telemetry/agent-usage-attempts.jsonl` after the safe branch clears
  inherited attempt overrides.
- The temporary plist adds only `LIFE_MANAGER_SAFE_PROBE_ONLY=1` and the exact usage path. Never use global
  `launchctl setenv`.
- Never edit the on-disk original plist. A `mktemp -d` directory owns one exact temporary plist; rollback always
  bootstraps the untouched original path before any result judgment.
- Do not print JSONL rows, prompts, outputs, token counts, credentials, HOME paths, or provider stderr. Report only
  exit status, append counts, schema/mode/prefix booleans, and same-ID boolean.
- The original plist SHA-256 is
  `0a30e4821ebe5fdd6c62057848a8d6d78e7532b218aaecf43d62bfc68e2a05aa`; restoration is mandatory before verdict.

## Task 1 — Sol executes the bounded live canary

- [ ] **Step 1: Revalidate immutable preconditions**

Require all of the following immediately before mutation:

```text
loaded label state = not running
loaded ProgramArguments[1] = /Users/anicca/Projects/life-manager-main/skills/life-manager/life-manager-daily.sh
on-disk plist SHA-256 = 0a30e4821ebe5fdd6c62057848a8d6d78e7532b218aaecf43d62bfc68e2a05aa
feature worktree HEAD = 8554a6616
feature worktree status = clean
no exact safe-probe/provider process = true
loaded custom/inherited environment has no LIFE_MANAGER_REPO, RUN_AGENT_BIN, AGENT_RUNNER_BIN,
  AGENT_RUNNER_CONFIG, AGENT_RUNNER_PROVIDER, ANICCA_USAGE_ATTEMPT_LEDGER, LM_DATA_DIR, LM_DAILY_USAGE_LEDGER,
  or SCHEMA
canonical usage file = regular 0600 complete-line JSONL
canonical attempt file = absent
```

For the loaded chain, require the worktree-resolved real paths for `life-manager-daily.sh`, `run_agent.sh`,
`agent_runner.py`, `config.json`, and `loop_pass.schema.json` to remain inside the feature worktree and byte-equal
their blobs at commit `8554a6616`. Do not rely only on a clean porcelain.

If any fact differs, stop before mutation and update this plan from measured truth.

- [ ] **Step 2: Snapshot append-only evidence without row content**

Record in memory/state only, and build the exact existing production-cursor state:

```text
usage_size_before
usage_sha256_before
attempt_exists_before = false
prior = {schema_version:1, source_id:"life_manager_agent_usage", byte_offset:usage_size_before,
         prefix_sha256:usage_sha256_before, observed_file_size:usage_size_before}
```

The post-run verifier rereads the first `usage_size_before` bytes and requires their SHA-256 to equal
`usage_sha256_before`.

- [ ] **Step 3: Announce and create a separate temporary plist**

Announce one line before changing the loaded job. Create a `mktemp -d` directory, then use `apply_patch` to create one
temporary plist with the same label, cadence, process type, and log paths as the original. Its only differences are:

```xml
<string>/Users/anicca/Projects/life-manager-main/.worktrees/cfo-agent-usage-cutover/skills/life-manager/life-manager-daily.sh</string>
<key>EnvironmentVariables</key>
<dict>
  <key>LIFE_MANAGER_SAFE_PROBE_ONLY</key>
  <string>1</string>
  <key>LM_DAILY_USAGE_LEDGER</key>
  <string>/Users/anicca/.local/state/life-manager/telemetry/agent-usage.jsonl</string>
</dict>
```

Do not edit or copy over the original plist. Lint the temporary file. Before the first `bootout`, enter one shell that
owns the entire `bootout → temporary bootstrap → loaded verification → kickstart → terminal watch` sequence. In that
same shell, install an `EXIT` trap that bootouts the temporary definition and bootstraps the untouched original; map
`HUP/INT/TERM` to a nonzero exit so the `EXIT` trap runs. Do not clear the trap until restoration itself succeeds.
Any failed command or unexpected state exits that shell through the trap.

Inside the trapped shell, require the temporary loaded definition to show the feature script and exactly those two
owner-set environment values before kickstart; reject any runner/config/repo override named in Step 1. Only then
record this temporary job's integer `runs_before`.

- [ ] **Step 4: Kickstart the existing label and watch to terminal state**

Run exactly:

```bash
launchctl kickstart gui/501/ai.anicca.life-manager-daily
```

Poll `launchctl print` at intervals no longer than 30 seconds. Do not start a second process or manual runner. Record
only the terminal `last exit code`. Before accepting it, require temporary-job `runs == runs_before + 1`, terminal
`state = not running`, and `active count = 0`; otherwise the observed exit belongs to no proven new execution. Exit
`0` is expected; a nonzero result can still prove persistence only if the attempt and completion contracts below
both pass.

- [ ] **Step 5: Restore the untouched original before judging the result**

Boot out the temporary loaded definition, bootstrap the untouched original plist path, and require:

```text
on-disk plist SHA-256 = 0a30e4821ebe5fdd6c62057848a8d6d78e7532b218aaecf43d62bfc68e2a05aa
loaded ProgramArguments[1] = /Users/anicca/Projects/life-manager-main/skills/life-manager/life-manager-daily.sh
loaded EnvironmentVariables has no LIFE_MANAGER_SAFE_PROBE_ONLY
loaded EnvironmentVariables has no LM_DAILY_USAGE_LEDGER
loaded state = not running
```

If reload verification fails, keep repairing restoration; do not inspect or claim canary success first. Only after
all restoration gates pass, delete the exact `mktemp -d` directory and require the original on-disk SHA to have
remained unchanged throughout.

- [ ] **Step 6: Validate only appended bytes**

Require all conditions:

```text
usage and attempt files are regular 0600 complete-line JSONL
pre-run usage prefix SHA-256 is unchanged
attempt append contains exactly one matching new exact-eight-key row whose loop/task label identify this canary
matching attempt event_id is new lowercase nonzero 24-hex
matching attempt version = 1
matching attempt timestamp is a valid UTC ISO-8601 instant
matching attempt attempt is an integer >= 1
matching attempt loop = life-manager
matching attempt task_label = life-manager-safe-probe
matching attempt provider and model are trimmed nonempty strings
`scanLocalAgentUsageAppend("life_manager_agent_usage", current_usage_bytes, prior)` returns no coverage exception
every appended completion row is present in the scanner's accepted `pairs`
scanner pairs contain exactly one completion with that matching event_id
completion status is success or failed
no second completion uses that event_id
```

Use the existing production `scanLocalAgentUsageAppend` from `apps/life-call/lib/cfo-local-agent-usage-cursor.js`, not
a new partial schema checker. This validates provider, provider name, model, status, measurement, token object, and
the complete normalized contract while proving the pre-run prefix from `prior`. Do not require the total usage append
count to equal one. Ignore other accepted pair values for this canary and correlate only the canary attempt ID. If
another matching canary attempt appears, fail as ambiguous rather than choosing one.

Do not require or report a particular token/cost value. The provider row is the truth.

- [ ] **Step 7: State the exact outcome and next slice**

If every gate passes, mark canary complete and advance only to `5c2c2`: Luna updates the existing real two-source E2E
from its obsolete both-attempt-files-absent premise. If any data gate fails, keep `5c2c1` open with the named observed
gap; never append a manual repair row and never call capture ready.
