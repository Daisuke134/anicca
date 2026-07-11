# Security Hardening Report — franklin-alwaysact-skill-router (VCSDD Phase 5)

Worktree `/Users/anicca/anicca/.worktrees/alwaysact-impl`, branch
`feature/franklin-alwaysact-skill-router`, HEAD `39a9c217`.

## Tooling

| tool | version | invocation | scope |
|---|---|---|---|
| semgrep | 1.168.0 (`/opt/homebrew/bin/semgrep`, pre-existing, no install needed) | `semgrep --config auto runtime/loop/{always-act-router,go-live,index,context,brain,prompt,ledger,ledger-record,env-filter}.mjs` | every file this feature's diff adds or additively modifies |
| `node --test` (money-safety/guardrail assertions, doubling as security tests) | v25.6.1 | `node --test __tests__/franklin-plist-config.test.mjs`, `always-act-reroute.test.mjs::PROP-509a/PROP-509b` | deployed-config guardrail + guard-block reroute |
| `git diff` (diff-path allowlist, PROP-509a) | — | `git diff --name-only 826c7f6 HEAD -- skills/earn skills/_shared/lib/earn-guard.mjs runtime/loop/catalog-gate.mjs` | money-safety guard files |
| bandit / Wycheproof | N/A | — | **not applicable** — this is a JS/ESM codebase (bandit is Python-only); no cryptographic primitive (signing, key derivation, ciphers) is introduced or modified by this feature — the one wallet-derivation call (`wallet-address-solana.mjs`) is REUSED, unmodified, out of this feature's diff, and was already covered by its own feature's Wycheproof-equivalent verification if any exists — re-auditing it here would be redundant, matching this feature's own `verification-architecture.md` Tier-3 scoping note |

Raw output: `security-results/semgrep-report.txt` (+ `.json`), `security-results/plist-guardrail-run.txt`.

### semgrep — 0 findings

```
Scanning 9 files tracked by git with 1074 Code rules:
  js  153  9  Community
  <multilang>  47  9
Findings: 0 (0 blocking)
Rules run: 200
```
Clean across all 9 scanned files (`always-act-router.mjs`, `go-live.mjs`, `index.mjs`, `context.mjs`,
`brain.mjs`, `prompt.mjs`, `ledger.mjs`, `ledger-record.mjs`, `env-filter.mjs`).

## Threat-model of the new surface

### 1. `ALWAYS_ACT_REGISTRY_PATH_OVERRIDE` (test-only registry-path env override)

- **Risk**: an attacker who can set this env var for Franklin's process points `registryForAlwaysAct`
  at an attacker-controlled `registry.json` whose per-slot `risk` field is falsified (e.g. a real
  capital-risking slot mislabeled `risk:"safe"`). Since `isMarketRiskFree` (`always-act-router.mjs:107-109`)
  and `assembleAlwaysActMenu`'s catalog filter both trust `riskTagOf` as given (never independently
  re-derived), a falsified registry would defeat REQ-506's reroute filter (CRIT-006/PROP-506e's money-safety
  guarantee) — an attacker-controlled `risk:"safe"` label on a real capital slot would make it a
  legitimate reroute target.
- **Existing mitigation**: `index.mjs:138-142` — the exact same unconditional-honor-in-code, mitigated
  only by deployed-plist-absence idiom this codebase already uses for `ANICCA_BALANCE_OVERRIDE`
  (`balance.mjs:14,48` / `config.mjs:128-129`, pre-existing, not introduced by this feature) and
  `CLAUDE_BIN`. The mitigation is `franklin-plist-config.test.mjs`'s two dedicated guardrail tests
  (lines 62-76) that read the REAL deployed `~/Library/LaunchAgents/ai.anicca.franklin-loop.plist` /
  `ai.anicca.franklin2-loop.plist` and assert neither's `<EnvironmentVariables>` dict carries this key.
- **Verified live this session** (both the automated test AND an independent hand-check):
  ```
  $ node --test __tests__/franklin-plist-config.test.mjs
  ℹ tests 4  ℹ pass 4  ℹ fail 0
  ```
  Independent re-derivation (not the test file, a separate `plutil`+`python3` one-liner run directly
  against the real deployed plist this session):
  ```
  ALWAYS_ACT_ENABLED present: False   ALWAYS_ACT_REGISTRY_PATH_OVERRIDE present: False
  ```
  Both confirm the deployed Franklin plist neither carries this override key NOR has
  `ALWAYS_ACT_ENABLED` set at all right now (the feature's own gate is default-OFF in production, as
  designed — `ALWAYS_ACT_ENABLED` absent → `resolveAlwaysActGate` returns `engaged: false`,
  `flagReason: 'flag_unset'`, per `index.mjs:280-288`).
- **Residual risk**: **accepted, same class as the pre-existing `ANICCA_BALANCE_OVERRIDE`/`CLAUDE_BIN`
  precedent** — the only mitigation for this WHOLE class of test-injection env var in this codebase is
  "verify the deployed plist doesn't set it," never a code-side production/test-mode gate. This is a
  structural choice already made (and accepted) by this codebase before this feature; this feature does
  not introduce a NEW mitigation gap, it extends an existing, already-accepted one to a new,
  money-safety-relevant variable. An attacker who can already write to
  `~/Library/LaunchAgents/*.plist` or set arbitrary env vars for Franklin's process already has
  local-machine control sufficient to bypass money-safety guards through many other paths (e.g.
  directly editing `skills/registry.json` itself, which this feature's menu assembly reads
  unconditionally) — this override is not a meaningfully NEW attack surface beyond that baseline.

### 2. `ALWAYS_ACT_ENABLED` env flag (spoofing risk)

- **Risk**: an attacker who can set `ALWAYS_ACT_ENABLED=1` in Franklin's process env engages
  always-act mode, which withholds the `sleep` tool on the outbound wire (REQ-504) — removing the
  model's "opt out and do nothing" safety valve for that wake.
- **Existing mitigation**: engagement requires BOTH this flag `=== '1'` (`index.mjs:282-286`) AND
  `checkAlwaysActIdentity()` returning true — a REAL Solana-address derivation match between the
  process's own wallet and `$HOME/.blockrun`'s wallet (`index.mjs:247-269`), which itself requires
  `ANICCA_SOLANA_PRIVATE_KEY`-holding filesystem access to `~/.blockrun/.solana-session` (or the
  structural `looksLikeFranklinHome` fast-path, itself gated on `ANICCA_HOME` literally equalling
  `$HOME/.blockrun` — not spoofable by an env var alone without also controlling `$HOME`/the real
  identity file). The flag alone, without also controlling the real Solana identity material, is
  insufficient to engage always-act — this is a two-factor design (flag + identity), not a
  single-env-var toggle.
- **Verified**: `CRIT-001`'s passThreshold (contracts/sprint-1.md) + `PROP-501a/b/c` (this session's
  fresh run, `always-act-reroute.test.mjs`, 4 tests, all green) exercise identity-mismatch/flag-only
  and flag-mismatch/identity-only combinations, confirming neither alone engages the gate.
- **Residual risk**: **accepted** — engagement even when both factors align only removes a UI-level
  safety valve (the `sleep` no-op tool); it does NOT bypass any money-safety guard (`MAX_SPEND`,
  `earn-guard.mjs`, per-skill kill switches — REQ-509/PROP-509a's diff-path check confirms zero touch
  to those files) and does NOT grant any new capability beyond what a non-always-act Franklin wake
  could already do (pick any live earn slot and execute it) — it only removes the OPTION to idle. An
  attacker who already has the local-machine access required to set this env var on Franklin's real
  process already has far more direct paths to cause harm (e.g. spawning the skill binaries directly).

### 3. Ledger writes — injection via skill output (`skip_reason` / `result` fields)

- **Risk**: `skip_reason: skillResult.output || ''` (`index.mjs:812`) carries a guard-blocked skill's
  RAW stdout/stderr text into a ledger line, unmodified/uncapped (deliberately, per REQ-509's "preserved
  verbatim" AC — no `.slice()`, no whitespace-collapse, unlike the wake's own terminal `result` field at
  `index.mjs:852`). Could a malicious/misbehaving skill emit output containing a literal newline,
  unescaped quote, or crafted string designed to break JSONL line-per-record framing, forge a fake
  additional ledger line, or inject arbitrary JSON keys?
- **Existing mitigation — structural, not pattern-matching**: `formatRecord` (`ledger-record.mjs:12-14`)
  is `return JSON.stringify(fields) + '\n'` — `skillResult.output` is placed into the `fields` OBJECT as
  a plain JS string value BEFORE serialization, so `JSON.stringify` structurally escapes every
  `\n`/`\r`/`"`/control character inside it (per the JSON spec, not a regex/allowlist this feature
  wrote) — a malicious skill's output can only ever appear as the ESCAPED CONTENT of the `skip_reason`
  string value inside one well-formed JSON object per line; it can never inject a second top-level key,
  break the one-line-per-record JSONL framing, or forge an additional ledger line. This is inherent to
  using `JSON.stringify` over a data structure rather than string-concatenating a line — no additional
  sanitization pass is needed or was added for this reason (a separate, existing pass —
  `redactPrivateKeyPatterns` — is applied for a DIFFERENT reason, secret redaction, not structural
  safety; see below).
- **Verified this session**: read `ledger-record.mjs` in full (14 lines) — confirmed the single
  `JSON.stringify` call is the entire implementation, no manual string-building. `redactPrivateKeyPatterns`
  (`env-filter.mjs:46-49`) is applied to the skip record's FULL serialized string
  (`redactPrivateKeyPatterns(skipRecordStr)`, `index.mjs:814`) — its regex (`/0x[0-9a-fA-F]{64}/g`) only
  ever substitutes a matched 64-hex-digit run with the literal `[REDACTED]`; this substitution happens
  AFTER `JSON.stringify` has already produced valid JSON, and the replacement text `[REDACTED]` contains
  no JSON-structural characters (`"`, `\`, control chars), so it cannot itself introduce a framing break
  even in the pathological case where the matched hex run happened to span a JSON string boundary (it
  can't — the match is always inside an already-escaped string's content, since `0-9a-fA-F` characters
  need no JSON escaping themselves).
- **Residual risk**: **none identified** — the safety property here is structural (JSON serialization
  over a data structure), not a completeness property of a pattern-matcher; there is no realistic
  "malicious skill output" that defeats `JSON.stringify`'s own escaping.

### 4. `go-live.mjs` CLI — invocation authority & idempotency race

- **Who can invoke**: the file's own doc-comment (`go-live.mjs:43-45`) and `contracts/sprint-1.md`'s
  "Known residual scope boundary" section both state this is "the operator's own one-time command...
  run AFTER `vcsdd-converge`" — i.e. a human/agent-operator with shell access to the deployment host,
  same trust tier as anyone who could edit the deployed `.plist` files or `ALWAYS_ACT_ENABLED` itself.
  No network-facing invocation path exists; `go-live.mjs` is never imported by `index.mjs` (confirmed
  live this session — see below) so no wake, engaged or otherwise, can trigger it.
  ```
  $ grep -n "go-live.mjs\|recordGoLive" runtime/loop/index.mjs
  (zero matches, confirmed this session)
  ```
- **Idempotency**: `recordGoLive` (`go-live.mjs:35-40`) is `read tail → if shouldRecordGoLive(tail) →
  append`. This is a **read-then-write TOCTOU race** for genuinely CONCURRENT invocations: two `node
  runtime/loop/go-live.mjs` processes launched close enough together could both read a tail with no
  existing `always_act_go_live` line, both evaluate `shouldRecordGoLive` true, and both append —
  producing two `always_act_go_live` anchor lines rather than the intended exactly-one. `appendLedgerLine`
  itself is safely atomic at the OS level for each individual write (`O_APPEND`, sub-`PIPE_BUF` writes,
  per `ledger.mjs`'s own doc-comment) — the race is at the `read-tail → decide → append` LOGICAL level,
  not a corrupted/torn write.
- **Verified this session**: `go-live.test.mjs`'s 4 tests (re-run, all green) cover SEQUENTIAL
  double-invocation ("a SECOND invocation... never duplicates") but `grep -n "concurrent\|race\|Promise.all"
  __tests__/go-live.test.mjs` finds zero matches — **no test exercises genuinely concurrent invocation**.
- **Residual risk (honestly disclosed, not discharged)**: **low-likelihood, low-impact, untested.**
  This is a manual, human-invoked, one-time operational action (explicitly out of this feature's own
  automated-wake control flow by design) — a true double-fire requires an operator (or a misconfigured
  automation) to launch two `go-live.mjs` processes within the same narrow read-then-write window, which
  is not a realistic accidental scenario for a command meant to be run exactly once by a human. The
  IMPACT of a duplicate anchor line is also bounded: `isPostGoLiveRegression`'s own scan
  (`always-act-router.mjs:235-256`) treats any non-`always_act_not_engaged` line (including a second
  `always_act_go_live` line) as a "successfully engaged" run-counter reset, so a duplicate anchor does
  not silently suppress or falsely trigger the regression detector — at worst it is a harmless, cosmetic
  double-entry in the ledger, not a money-safety or observability-integrity failure. **Recommendation for
  a future hardening pass** (not blocking Phase 6, per the VCSDD "never block Phase 6 for non-required
  proof obligations" rule — this was never a declared `PROP-5xx` obligation in the first place): add a
  file-lock or a single sequential invocation test asserting the SAME behavior under
  `Promise.all([recordGoLive(...), recordGoLive(...)])` to convert this from an honestly-disclosed gap
  into a proved property.

## Summary

**Findings: semgrep 0/0 (clean).** Four threat surfaces analyzed:
`ALWAYS_ACT_REGISTRY_PATH_OVERRIDE` (accepted risk, same precedent class as
`ANICCA_BALANCE_OVERRIDE`/`CLAUDE_BIN`, mitigated by a live-verified deployed-plist-absence guardrail —
re-confirmed both by test and independent hand-check this session), `ALWAYS_ACT_ENABLED` spoofing
(accepted risk — two-factor gate with real Solana identity derivation, removes only the idle-safety-valve,
never a money-safety guard), ledger-write injection via raw skill output (**no residual risk** —
structural JSON-serialization safety, independently re-derived by reading `ledger-record.mjs` in full),
and `go-live.mjs`'s CLI idempotency (**one honestly-disclosed, untested residual gap** — a low-likelihood,
low-impact TOCTOU race on manual double-invocation, not a declared proof obligation, recommended but not
blocking for a future pass). No cryptographic/Wycheproof-style check applies (JS codebase, no crypto
primitive introduced by this diff). No High or Medium severity finding from any tool. Money-safety guard
files independently confirmed untouched (`git diff --name-only 826c7f6 HEAD -- skills/earn
skills/_shared/lib/earn-guard.mjs runtime/loop/catalog-gate.mjs` → zero output, this session).
