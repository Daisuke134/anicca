# `life-manager-v0` retirement evidence

## Result

`Daisuke134/life-manager-v0` is a read-only historical archive. The canonical
source, issue tracker, runtime source, and deployment source remain
`Daisuke134/life-manager`.

| Check | Measured result |
|---|---|
| legacy repository identity | repository ID `1273052304`, default branch `main`, public, `archived=true` |
| final legacy commit | `210adead08afbb5a19902b5b107fcf0601fad387` (`docs: redirect archived v0 to canonical repository (#12)`) |
| tracked inventory | 35 files, 184,580 bytes, unclassified 0 |
| README | canonical URL exactly 1; install, run, deploy, scheduler instructions 0 |
| GitHub activity | open issue 0, open PR 0, workflow 0, webhook 0, deployment 0, release 0, tag 0 |
| transferred issue | legacy issue `#11` redirects to canonical [issue #1287](https://github.com/Daisuke134/life-manager/issues/1287); it remains open for its real-event outcome measurement |
| local runtime | installed LaunchAgent literal scan: legacy source references 0; running legacy process 0 |
| canonical runtime source | executable source dependency on v0 0; one remaining literal is `inventory-legacy-jobs.js`, which identifies and rejects a legacy job |
| rollback | unarchive repository ID `1273052304`, inspect immutable commit `210adea…`, and restore only a behavior proven missing by a canonical regression test |

GitHub recommends closing issues and pull requests and updating the README and
description before archival, then makes the repository read-only. The measured
state follows that order. Source:
[GitHub Docs — Archiving repositories](https://docs.github.com/en/repositories/archiving-a-github-repository/archiving-repositories)
(“read-only for all users”); live state:
[GitHub repository API](https://api.github.com/repos/Daisuke134/life-manager-v0).

## 35-file behavior and history disposition

`canonical behavior` means the required behavior exists in the current
JavaScript/cloud-or-local implementation and has a focused regression test.
`historical only` means the file is provenance or obsolete execution
instructions, not required runtime source. No legacy byte-copy is used as proof.

| # | v0 path | Disposition | Canonical target or retained proof |
|---:|---|---|---|
| 1 | `.env.example` | canonical behavior | `apps/life-manager/.env.example`; secrets remain external inputs |
| 2 | `.gitignore` | canonical behavior | root and `apps/life-manager/.gitignore`; generated archives and runtime state remain excluded |
| 3 | `E2E-SPEC.md` | historical only | current product/spec contracts and `apps/life-manager/test/` replace the stale local-only instructions |
| 4 | `LICENSE` | license/provenance | root `LICENSE` preserves MIT terms; v0 Git history remains readable |
| 5 | `README.md` | historical only | final redirect at commit `210adea…`; active instructions exist only in canonical |
| 6 | `SKILL.md` | canonical behavior | `apps/life-manager/skill-life-manager/SKILL.md` |
| 7 | `__tests__/test-planner.js` | canonical behavior | `test/scheduler.test.js`, `lib/wake-filter.test.js` |
| 8 | `adapters/transport.js` | canonical behavior | `lib/transport/index.js`, calendar/mail provider adapters |
| 9 | `adapters/transport.py` | superseded | one maintained JS transport boundary; no second Python runtime |
| 10 | `agent/resolve.py` | canonical behavior | `lib/ask.js`, `lib/calendar-interpreter.js`, `lib/places-memory.js` |
| 11 | `ask/SLOT.md` | historical only | current skill contract and scheduler wiring |
| 12 | `ask/__tests__/test-ask-local.js` | canonical behavior | ask callback, calendar interpreter, and transport tests |
| 13 | `ask/ask-local.js` | canonical behavior | `lib/ask.js`; candidate/context resolution precedes a user question |
| 14 | `call.js` | canonical behavior | `scheduler.js`, `lib/dial.js`, `lib/call-bridge.cjs` |
| 15 | `call/PATCH-call-escalation.diff.md` | historical only | applied behavior is tested by scheduler/wake tests; patch prose is not runtime |
| 16 | `call/SLOT.md` | historical only | current skill contract and scheduler wiring |
| 17 | `call/call.js` | canonical behavior | `lib/dial.js`, `lib/call-bridge.cjs`, `lib/telnyx-webhook.js` |
| 18 | `call/lib/.gitignore` | superseded | app/root ignore policy |
| 19 | `call/lib/call-bridge.cjs` | canonical behavior | `apps/life-manager/lib/call-bridge.cjs` and focused test |
| 20 | `call/lib/call-logic.js` | canonical behavior | `apps/life-manager/lib/call-logic.js` and focused test |
| 21 | `call/lib/package.json` | superseded | `apps/life-manager/package.json` and lockfile |
| 22 | `call/lib/runner-telnyx.mjs` | canonical behavior | persistent `server.js`, `lib/dial.js`, `lib/telnyx-webhook.js` |
| 23 | `call/lib/runner-twilio.mjs` | superseded | provider-independent call bridge; active production carrier path is Telnyx |
| 24 | `config.js` | canonical behavior | app env boundary, `lib/runtime-paths.js`, and `lib/secret-provider.js` |
| 25 | `config.py` | superseded | one maintained JS runtime/config boundary |
| 26 | `locate/__tests__/locate.test.js` | canonical behavior | `lib/late-notice.test.js` location-expiry and late gates |
| 27 | `locate/locate.js` | canonical behavior | `lib/late-notice.js` and `lm_user_locations` migration |
| 28 | `notify/SLOT.md` | historical only | current skill/runtime contract |
| 29 | `notify/__tests__/notify-logic.test.js` | canonical behavior | `lib/late-notice.test.js` and receipt tests |
| 30 | `notify/__tests__/test-motion-gate.js` | canonical behavior | location gate and atomic late-notice tests |
| 31 | `notify/notify.js` | canonical behavior | `lib/late-notice.js`, mail receipt adapters, Telegram reporting |
| 32 | `planner.js` | canonical behavior | `scheduler.js`, `lib/wake-filter.js`, `lib/dial.js` |
| 33 | `travel/SLOT.md` | historical only | current skill/runtime contract |
| 34 | `travel/__tests__/test_travel_fill.py` | canonical behavior | `lib/travel*.test.js` covers route, origin, block, cache, and arrival-time rules |
| 35 | `travel/travel_fill.py` | canonical behavior | `lib/travel.js`; traffic-aware drive and event-anchored transit are retained |

Disposition totals: canonical behavior 22, superseded 5, historical only 7,
license/provenance 1; total 35, missing required behavior 0.

## Verification

| Surface | Command class | Result |
|---|---|---|
| legacy JavaScript behavior | v0 planner/ask/locate/notify Node tests | 48/48 PASS |
| legacy Python travel behavior | v0 `pytest` travel suite | 9/9 PASS |
| canonical mapped behavior | transport/travel/ask/call/wake/late/scheduler focused tests | 116/116 PASS |
| no-account boundary | explicit empty `account` while host `GOG_ACCOUNT` is populated | fail-closed, provider calls 0 |
| README readback | GitHub Contents API at `main` | canonical URL 1, install/runtime commands 0 |
| archive readback | repository/workflow/hook/deployment/issue/PR APIs | archived true; every active count 0 |

The comparison exposed one real canonical defect before archival: an explicit
empty local Google account fell through to the host `GOG_ACCOUNT`. The transport
constructors and cache identity now distinguish `undefined` from an explicitly
empty account, and the regression test proves provider calls remain zero.
