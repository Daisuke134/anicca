# Life Manager CFO Moneytree Codex Reader Implementation Plan

> **Execution routing:** Ponytail full and Superpowers subagent-driven-development are mandatory. Sol owns this
> plan, review, live evidence, state, commit, and push. Only Luna writes production code and tests.

**Goal:** Give the local CFO a launchd-callable, real Moneytree/MUFG account read without adding a browser scraper,
Moneytree API credential, MCP proxy, database object, or service.

**Architecture:** A small Node CLI runs one non-interactive `codex exec` with the Luna model and the already-connected
Moneytree App. The model only requests `show_accounts`. The CLI ignores the model's prose and deterministically
extracts the one raw `accounts` object from the Codex JSONL MCP completion event at
`item.result.structured_content`. It passes that untouched object to the existing Moneytree adapter and coverage-state
composer. No model-generated financial number is accepted.

```mermaid
flowchart LR
    L[launchd caller] --> R[Node Moneytree reader]
    R --> C[codex exec\nLuna + read-only]
    C --> M[Connected Moneytree App\nshow_accounts once]
    M --> E[Raw MCP JSONL event]
    E --> X[Deterministic extraction\nno prose]
    X --> A[Existing Moneytree adapter]
    A --> V[Validated frozen CFO read]
```

**Observed evidence:** Local probes with both Sol and Luna completed the installed Moneytree `show_accounts` call.
Luna emitted exactly one raw accounts object in eight Codex JSONL events at index-independent path
`item.result.structured_content`; no Telegram call or private field was printed. The running
`ai.anicca.life-manager-connector-host-bridge` supports only Calendar and route operations, so this plan does not
modify it. Official OpenAI documentation lists the Responses API connector IDs and does not list Moneytree; the
connected Codex App is therefore reused through Codex rather than falsely inventing a public connector ID.

## Ponytail size and scope gate

| Element | Files | Production LOC soft target | Why it exists |
|---|---:|---:|---|
| Launchd-callable reader CLI/module | 1 new | <=100 | Invoke the existing App and normalize its raw event |
| Focused contract test | 1 new | 0 | Prevent prose-derived money, secret inheritance, or raw logging |
| CFO test registration | 1 modify | <=2 | Keep the reader in the existing CFO suite |

Exactly three files. Explicitly excluded: connector-host bridge changes, new MCP server, OAuth extraction, browser
automation, scheduler/launchd installation, Telegram callbacks/sends, database/schema, transactions, spending advice,
Binance, dependency additions, generalized subprocess frameworks, and hostile-object combinatorics.

---

### Task 1: Read Moneytree accounts through Codex JSONL

**Files:**
- Create: `apps/life-call/scripts/cfo-moneytree-codex-read.js`
- Create: `apps/life-call/scripts/cfo-moneytree-codex-read.test.js`
- Modify: `apps/life-call/package.json`

**Interfaces:**
- Module: `readMoneytreeViaCodex(options)` returns the existing frozen composed Moneytree read.
- CLI: exits `0` and prints only a safe status envelope (`ok`, `sourceId`, `accountCount`, `partial`); it never prints
  balances, account/provider IDs, institution labels, raw App output, credentials, or Codex prose.
- Required stable reference secret: existing `LM_UID_SECRET` (already present and >=32 bytes). It is used only by the
  existing HMAC adapter and is removed from the child Codex environment.

- [x] **Step 1: Write the focused failing test**

Use an injected `execFileImpl` and one synthetic Codex JSONL transcript containing an `item.completed` event whose
`item.type` is `mcp_tool_call` and whose `item.result.structured_content` is the existing synthetic Moneytree accounts
fixture. Prove:

1. the executable call is shell-free and its fixed args include `exec --ephemeral --json`, `gpt-5.6-luna`,
   `read-only`, and the fixed CFO working directory; the returned child stdin is ended exactly once so Codex receives
   EOF and never waits for an unused `<stdin>` append;
2. exactly one raw MCP accounts object becomes the existing validated/frozen composed read;
3. `LM_UID_SECRET` and an unrelated secret sentinel are absent from the child environment;
   the child instead receives the fixed non-secret `CODEX_INTERNAL_ORIGINATOR_OVERRIDE=codex_exec` required by the
   measured non-interactive Apps path;
4. model prose, stderr, balances, and raw provider fields are never logged or embedded in an error;
5. missing or duplicate accounts MCP results fail with one fixed redacted error.

- [x] **Step 2: Run RED**

```bash
cd apps/life-call
node --test scripts/cfo-moneytree-codex-read.test.js
```

Expected: non-zero because the reader does not exist.

- [x] **Step 3: Implement minimum GREEN**

Use only Node stdlib `child_process.execFile` with a two-minute timeout and a two-megabyte buffer. Use a fixed prompt
that requests the installed Moneytree App's `show_accounts` tool with locale `ja` exactly once and forbids every
other tool and private-field output. Do not use a shell. Capture the returned child process and immediately call
`child.stdin.end()` exactly once; treat a missing/unusable stdin as unavailable. Give the child only the minimal runtime environment needed
for Codex (`HOME`, `PATH`, `USER`, `LOGNAME`, `SHELL`, `TMPDIR`, locale, and `CODEX_HOME` when present), plus the
fixed non-secret `CODEX_INTERNAL_ORIGINATOR_OVERRIDE=codex_exec`. Never inherit the parent environment wholesale,
and never pass the parent session's `CODEX_THREAD_ID`, `CODEX_CI`, `CODEX_SHELL`, or originator value.

Parse stdout as JSONL. Require exactly one completed MCP item and exactly one `structured_content` object with
`type === "accounts"` and an object `data.accountGroups`. Reject missing, duplicate, malformed, oversized, timed-out,
or non-zero results with `cfo_moneytree_codex_read_failed:unavailable`. Never include stderr/stdout/raw exceptions in
the error or logs.

Serialize only that provider object for `adaptMoneytreeAccounts`, derive `interactive_success` with liabilities and
aggregation unknown, and return `composeMoneytreeRead(...)`. Do not calculate or copy balances in the reader.

- [x] **Step 4: Verify GREEN**

```bash
cd apps/life-call
node --test scripts/cfo-moneytree-codex-read.test.js
npm run test:cfo
npm test
wc -l scripts/cfo-moneytree-codex-read.js scripts/cfo-moneytree-codex-read.test.js
git diff --check
```

Expected: all exit `0`; production is <=100 LOC; exactly three files changed.

- [x] **Step 5: Fresh review and real no-send E2E**

Fresh Sol review checks only Critical/Important correctness: one MCP call, raw-event extraction rather than model
prose, child secret scrubbing, fixed errors, no private logging, no connector bridge or scheduler expansion, and LOC.
Sol then runs the real CLI with the existing local environment and prints only booleans/counts. Required live evidence:
real App call succeeds, connected account count is positive, source/state validate and are frozen, native currency is
JPY, liabilities remain unknown/partial, no Telegram call occurs, and no private field is printed.

The first live CLI attempt is retained as RED evidence: the child environment scrubbed the host originator as well as
secrets, so Codex did not complete before the 120-second bound and the CLI correctly emitted only its safe failure
envelope with exit `1`. A no-send diagnostic proved the same prompt/cwd succeeds under the normal environment, and
then proved a minimal clean environment succeeds with only the fixed official `codex_exec` originator added. After
that fix, the real CLI still timed out. A bounded diagnostic observed zero JSONL events before timeout, proving Codex
was waiting before the turn began. `execFile` had left its stdin pipe open, and Codex treats piped stdin plus a prompt
argument as additional input. An injected wrapper that ended child stdin made the unchanged real reader succeed with
a positive account count, valid frozen source/state, partial coverage, no private output, and zero Telegram calls.
Luna must add both live regressions before changing production.

- [x] **Step 6: Close**

Update this plan and the parent CFO spec with RED/GREEN/review/live evidence, commit, and push. Then make Telegram CFO
detail callback wiring the only active item. Do not install the hourly launchd job in this task.

## Definition of done

A real non-interactive Luna/Codex invocation reads the connected Moneytree account data and returns the existing
validated CFO Moneytree contract without any LLM-transcribed amount, raw provider output, secret inheritance,
Telegram send, new service, or scheduler change.

## Completion evidence

Luna closed the two real-runtime blockers with focused regressions: the child receives the fixed non-secret
`codex_exec` originator, and its stdin is ended exactly once. Final verification passed focused `7/7`, CFO `249/249`,
the complete repository test command, syntax checking, and `git diff --check`; production is 86 LOC and the change
remains exactly three files. The real local CLI then completed against the connected Moneytree App with exit `0`,
`sourceId=moneytree_mufg`, one connected account, and partial coverage while printing no amount or private provider
field and making no Telegram call. Fresh Sol review returned `ship — Spec ✅` with no Critical or Important finding.
This reader slice is **COMPLETE**. Telegram detail callback wiring is the first unfinished CFO-1i slice.
