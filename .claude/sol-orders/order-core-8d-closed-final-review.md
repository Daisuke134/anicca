# CORE-a / 8d closed collector final fresh review

Read-only independent review in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d`: head `904e158c8f8592b7a6d8c3fcd2f215c037f842b1` against parent `1f1be94de617a3b88857486daa983897d2dc087d`.

Do not edit/commit/push/merge/deploy or call network/provider/Railway/Telegram/email/dial. Do not spawn another agent. Row 8d remains pending 6/9 regardless of local verdict.

Verify the sole prior blocker is closed honestly:
- production collector module exports only no-argument real controlled collection plus pure validators;
- no exported or reachable transport-DI factory/constructor/parameter (`botCall`, MTProto, exec, send, receipt, mail factory, env/fetch/clock/random/sleep/poll substitution);
- controlled CLI cannot pass caller env/fetch/collector/proof into controlled collection;
- all DI factories and mirrors are test-support only and production never imports them;
- readable fixed production code is retained: no split identifiers, computed properties, aliases, source-scan gaming, shell commands, or fake proof paths;
- production wiring test installs every fake before requiring production, can never fall through to real sidecar/fetch/Resend/gog, and asserts one-send budgets;
- `/panel core8d_<nonce>`, fixed peer derivation, webhook backlog, exact email nonce receipt, sanitation and report binding remain correct;
- historical artifact is unchanged 6/9 and spec records the prior accidental fixture attempt.

Run diff check, focused tests, full npm test/eval where read-only sandbox permits, targeted coverage where possible, export/signature/import scans, historical hash. Use VERIFIED/REASONED/ASSUMED.

Finish exactly:
```text
FINAL_VERDICT: PASS | FAIL
MERGE: NO
BLOCKERS: <count>
FINDINGS:
- [severity] file:line — problem — correction
VERIFICATION:
- command => exit/result
```

MERGE stays NO because controlled production 9/9 is not yet rerun.
