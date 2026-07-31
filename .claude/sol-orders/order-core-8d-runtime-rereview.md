# CORE-a / 8d fixed runtime collectors — fresh review

You are a fresh independent reviewer. Read-only review commit `1f1be94de617a3b88857486daa983897d2dc087d` against parent `2df9585c743aafb9083046b8b3dba6613030e474` in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d`.

Do not edit, commit, push, merge, deploy, send Telegram/email, dial, or call provider/Railway APIs. Do not spawn another agent. Ignore builder claims; inspect exact committed artifacts and run local tests only. Row 8d stays pending and production truth stays 6/9.

Goal: decide whether the two prior blockers are closed without false-green or test-to-network paths.

Review:
1. Production CLI has no arbitrary `collectors`, `--proofs`, proof file/JSON/command injection, or artifact post-mutation. DI exists only in a clearly test-only module never imported by production.
2. Production registry contains actual fixed collectors, not unavailable stubs.
3. Telegram production path derives peer from Bot API `getMe`, invokes only pinned interpreter+sidecar argv without shell, sends exactly `/panel core8d_<internal nonce>` once, accepts only a newer inbound reply in the same MTProto dialog, discards raw reply text/opaque URL, hashes IDs, and separately validates exact webhook URL/updates/error and bounded backlog final zero. It never compares MTProto IDs with Bot API update IDs.
4. Email derives recipient/receiver from authenticated `GOG_ACCOUNT`, requires fixed allowlist membership, sends Resend exactly once, requires accepted provider ID plus exact internally generated nonce found by authenticated `gog gmail messages search`, bounded freshness, and hashes refs. Provider acceptance alone cannot pass.
5. Default read-only has zero sends. Controlled failure is nonzero and sanitized. Test runners cannot fall through to actual `execFile`, fetch, Resend, gog, or sidecar.
6. Direct negative branches cover Telegram send/reply/url/updates/error/backlog and email allowlist/send/receipt/nonce/stale. Changed-module line and function coverage meet >=90%.
7. Historical artifact is byte-identical and 6/9. Spec honestly records the unintended fixture attempt to `@LifeBot`; verify a regression test now forces fake exec before any production transport test.
8. Check `gog` command syntax against installed `gog 0.17.0 --help` without authentication/API calls.

Run fresh:
- `git diff --check 2df9585c7..1f1be94de`
- focused collectors/provenance/gog receipt tests
- full `npm test`, `npm run eval`
- targeted changed-module coverage
- source scans for forbidden paths and production imports of `.test-support.js`
- historical artifact hash/parse

Use VERIFIED / REASONED / ASSUMED. Finish exactly:

```text
FINAL_VERDICT: PASS | FAIL
MERGE: NO
BLOCKERS: <count>
FINDINGS:
- [severity] file:line — problem — correction
VERIFICATION:
- command => exit/result
```

MERGE remains NO because production is not 9/9 even if code review passes.
