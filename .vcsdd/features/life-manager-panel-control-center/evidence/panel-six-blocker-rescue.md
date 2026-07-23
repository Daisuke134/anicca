# PANEL-0 six-blocker local RED/GREEN evidence

Status: product behavior locally GREEN. No deploy, merge, provider/OAuth call, send, L3, production request, or self-authored independent-review verdict occurred.

## RED

- Base: `c3fbf22ebe3148a52d4768dd36d00d4230e3fa28` (`HEAD == upstream == PR #331 head` before RED).
- Rejected static-shape input SHA-256: `8ca3f3e9b43159d9d0739d31df6d89a2b9763f38b1e7b22c68c722adb94d9553`; it was not committed.
- Behavior RED commits: `0f0675a7b` and fixture correction `5bfd87d59`.
- Command: `node --test lib/panel-permanent-session.test.js`.
- Exact base result: 13 total, 1 pass, 12 fail. Production/auth/API/UI/scheduler/discovery/server/migration implementation diff was zero.
- Blocker 1: `B1 real /panel...`, resolver concurrency/retry/revoke, and logout tests failed.
- Blocker 2: `B2 production getUserByUid...` and default discovery preference tests failed.
- Blocker 3: rebound page/OAuth and write-boundary rebind tests failed.
- Blocker 4: reconnect substitution/fake ACTIVE and disconnect rollback truth tests failed.
- Blocker 5: scoped rendered controls/personalization test failed; shared command HTTP dispatch was the one positive behavior.
- Blocker 6: oversize + late socket error test failed.

## GREEN verification

- Permanent behavior suite: 17/17 pass.
- Prior corrective focused suite: 39/39 pass.
- Full `npm test`: exit 0.
- `npm run eval`: Calendar 21/21 plus Late 12/12 = 33/33.
- `npm run smoke:panel-api`: 5/5 HTTP 200.
- `npm run smoke:panel-ui`: 6/6 semantic sections/controls.
- Coverage suite: 83/83 pass.
- `git diff --check`: exit 0.
- Secret scan: no raw session/token/service/provider secret in the diff; the only pattern match was a test restoring the `SUPABASE_SERVICE_ROLE_KEY` environment-variable name.

## Changed-module coverage

| Module | Line | Function |
|---|---:|---:|
| `panel-auth.js` | 97.45% | 90.48% |
| `panel-api.js` | 96.67% | 90.63% |
| `panel-ui.js` | 100.00% | 100.00% |
| `runtime-preferences.js` | 100.00% | 100.00% |
| `user-command.js` | 100.00% | 93.75% |
| `feature-discovery.js` | 99.46% | 94.12% |

The legacy scheduler aggregate is excluded by the rescue order; its changed selector behavior is exercised through fetch-backed `getUserByUid`, OFF/peer scheduler actions, Inngest-positive-control tests, and default discovery tests.
