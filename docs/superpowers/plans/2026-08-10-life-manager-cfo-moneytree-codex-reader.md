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

- [ ] **Step 1: Write the focused failing test**

Use an injected `execFileImpl` and one synthetic Codex JSONL transcript containing an `item.completed` event whose
`item.type` is `mcp_tool_call` and whose `item.result.structured_content` is the existing synthetic Moneytree accounts
fixture. Prove:

1. the executable call is shell-free and its fixed args include `exec --ephemeral --json`, `gpt-5.6-luna`,
   `read-only`, and the fixed CFO working directory;
2. exactly one raw MCP accounts object becomes the existing validated/frozen composed read;
3. `LM_UID_SECRET` and an unrelated secret sentinel are absent from the child environment;
4. model prose, stderr, balances, and raw provider fields are never logged or embedded in an error;
5. missing or duplicate accounts MCP results fail with one fixed redacted error.

- [ ] **Step 2: Run RED**

```bash
cd apps/life-call
node --test scripts/cfo-moneytree-codex-read.test.js
```

Expected: non-zero because the reader does not exist.

- [ ] **Step 3: Implement minimum GREEN**

Use only Node stdlib `child_process.execFile` with a two-minute timeout and a two-megabyte buffer. Use a fixed prompt
that requests the installed Moneytree App's `show_accounts` tool with locale `ja` exactly once and forbids every
other tool and private-field output. Do not use a shell. Give the child only the minimal runtime environment needed
for Codex (`HOME`, `PATH`, `USER`, `LOGNAME`, `SHELL`, `TMPDIR`, locale, and `CODEX_HOME` when present); never inherit
the parent environment wholesale.

Parse stdout as JSONL. Require exactly one completed MCP item and exactly one `structured_content` object with
`type === "accounts"` and an object `data.accountGroups`. Reject missing, duplicate, malformed, oversized, timed-out,
or non-zero results with `cfo_moneytree_codex_read_failed:unavailable`. Never include stderr/stdout/raw exceptions in
the error or logs.

Serialize only that provider object for `adaptMoneytreeAccounts`, derive `interactive_success` with liabilities and
aggregation unknown, and return `composeMoneytreeRead(...)`. Do not calculate or copy balances in the reader.

- [ ] **Step 4: Verify GREEN**

```bash
cd apps/life-call
node --test scripts/cfo-moneytree-codex-read.test.js
npm run test:cfo
npm test
wc -l scripts/cfo-moneytree-codex-read.js scripts/cfo-moneytree-codex-read.test.js
git diff --check
```

Expected: all exit `0`; production is <=100 LOC; exactly three files changed.

- [ ] **Step 5: Fresh review and real no-send E2E**

Fresh Sol review checks only Critical/Important correctness: one MCP call, raw-event extraction rather than model
prose, child secret scrubbing, fixed errors, no private logging, no connector bridge or scheduler expansion, and LOC.
Sol then runs the real CLI with the existing local environment and prints only booleans/counts. Required live evidence:
real App call succeeds, connected account count is positive, source/state validate and are frozen, native currency is
JPY, liabilities remain unknown/partial, no Telegram call occurs, and no private field is printed.

- [ ] **Step 6: Close**

Update this plan and the parent CFO spec with RED/GREEN/review/live evidence, commit, and push. Then make Telegram CFO
detail callback wiring the only active item. Do not install the hourly launchd job in this task.

## Definition of done

A real non-interactive Luna/Codex invocation reads the connected Moneytree account data and returns the existing
validated CFO Moneytree contract without any LLM-transcribed amount, raw provider output, secret inheritance,
Telegram send, new service, or scheduler change.
