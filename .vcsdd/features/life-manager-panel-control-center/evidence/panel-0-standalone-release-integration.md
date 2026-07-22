# PANEL-0 standalone release integration evidence

Status: **DELEGATION CORRECTIVE PASS; READY FOR A RELEASE PR TO `dev`**. Delegation remains unavailable because no safe delegated-action runtime is active; chat and direct API commands now fail closed without a mutation or success receipt. Migration, merge, deploy, provider mutation, messaging, and L3 remain forbidden.

## Exact revisions and source provenance

- Fresh release base: `5a4ec98e9a4b2919958ad3d2a95ef78fc9970b69` from `origin/dev`.
- Reviewed stacked parent: `c01057a0bfc0d5f1c0e1a308bd3c5de102d659fa` (open PR #330, unfinished CORE 8d).
- PANEL source range: `c01057a0bfc0d5f1c0e1a308bd3c5de102d659fa..a4c86991469419b8f775cfcb89776e89b832b5df`.
- PANEL source binary diff SHA-256: `e44710790ad395c51347872b09af96fece0b451bec7b288f00819de70a3fe659`.
- Obsolete stacked integration evidence `panel-0-parent-rebase-integration.md` is not transplanted.
- Standalone product integration commit: `492174ed2cf43417256842bd87279993cffb9af7`.
- Delegation honesty RED commit: `0dfa240988eb2fa44052674826b80ff7bdaac945` (test only; parent `f1fba91a0ff569b9b415db8565153b99502ec21a`).
- Delegation honesty GREEN commit: `d8c497e87e65d47997809f43b025a89dfe043559`.
- Stacked final evidence head, preserved without modification: `900db6a2444cdced8cc2b0eea6028b20b8b6f0a8` on open PR #331.

Source RED/GREEN/review provenance remains immutable on the stacked history:

- Corrective-1: RED `5f8db7f1353b163c267eb415c3c7e12456f6195d`, GREEN `1c74ff0f70cf8666d9356a4db49b57b2c0c19daf`, review/evidence `c3fbf22ebe3148a52d4768dd36d00d4230e3fa28`.
- Permanent-session corrective: behavior RED `0f0675a7bbd1f36532c2d8500f32adb204c349f7`, fixture RED `5bfd87d59e9c797495a647176713f56ae7cb235b`, GREEN/evidence `3e23328d9436835945c13da64b526202f94f90ac`.
- Corrective-3: RED `cecb45e645667ebf9cb00e302b5f2b06688b7f2b`, GREEN `8f8900e5e8f7cd917211a957e99db04df9363284`, review/evidence `5353bc0c1713301d4f4c4194368cbd51296a2ab7`.
- Corrective-4: RED `6122c184e67ccb9ffdaaccf10f9c0864cfcc3bc5`, GREEN `106edbb1ab851dddfc36e4627cc6320f03f067b9`, reviewed code `a4c86991469419b8f775cfcb89776e89b832b5df`, stacked PASS evidence `900db6a2444cdced8cc2b0eea6028b20b8b6f0a8`.

## Three-way application and conflict resolutions

The exact cumulative binary source diff is checked and applied with `git apply --check --3way` followed by `git apply --3way`. Four overlapping files are resolved against current dev:

1. `.vcsdd/history.jsonl`: retain the complete current-dev ledger and append exactly the 22 PANEL events from the source range. Do not import inherited CORE daily-preflight ledger events.
2. `apps/life-call/package.json`: retain current dev's `pretest`, full `test`, and smoke baseline; add only `lib/panel-control-center.test.js` beside `lib/panel-api.test.js`. Do not add daily-preflight tests or scripts.
3. `apps/life-call/scheduler.js`: retain current dev's `calendarProviderFilter` import and both selector uses; add the PANEL runtime-preference import and preference gating. Do not import `schedulerCohortFilter`.
4. `apps/life-call/lib/user-selector.test.js`: retain all three current-dev calendar-provider assertions and add the source fetch-backed test proving both `lm_users` and `lm_panel_preferences` are queried. The inapplicable `schedulerCohortFilter` symbol assertion is not imported; the phone, paid, and supported-calendar behavior remains asserted.

## Scope proof before evidence

- Source and standalone integration path sets are both exactly 52 paths; sorted path-set SHA-256 is `1cf934facad005f2ad49893d119256a3695fdb4a7df080eda788f8801cd98eb6` for both.
- Non-conflicting `apps/life-call` source and release deltas have the same stable patch-id: `5b21af987f6e73d40e1d5c5a4d23d5c1045afdd4`.
- Source and release additions to `.vcsdd/history.jsonl` have the same SHA-256: `947850b67c64b9ad2ea833bddb78e2609c12a934f6ee19eec22ff784826e3b77`.
- Changed daily-preflight paths: `0`; added `daily-preflight`, `life-manager-daily-preflight`, or `schedulerCohortFilter` lines: `0`.
- `.vcsdd/features/life-manager-daily-preflight/**` paths: `0`.
- Canonical consolidation spec changes: `0`.
- Existing current-dev test deletions or weakened assertions: `0`.
- `git diff --check`: exit `0`.

Corrective scope proof is also zero: changed daily-preflight paths `0`, canonical consolidation spec paths `0`, deleted test lines `0`, and removed assertion lines `0`. The canonical consolidation spec remains byte-identical to base `dev` and is not edited on this branch.

## Fresh product verification on the standalone tree

All commands run from `apps/life-call` unless noted.

| Gate | Exact command | Result |
|---|---|---|
| dependency restore | `npm ci --silent` | exit 0 |
| delegation honesty | `node --test --test-reporter=tap lib/panel-delegation-honesty.test.js` | `5/5`, fail 0 |
| panel control center | `node --test --test-reporter=tap lib/panel-control-center.test.js` | `13/13`, fail 0 |
| corrective4 logout | `node --test --test-reporter=tap lib/panel-corrective4-logout.test.js` | `1/1`, fail 0 |
| corrective3 four blockers | `node --test --test-reporter=tap lib/panel-corrective3-four-blockers.test.js` | `4/4`, fail 0 |
| permanent session | `node --test --test-reporter=tap lib/panel-permanent-session.test.js` | `17/17`, fail 0 |
| focused PANEL | `node --test --test-reporter=tap lib/panel-permanent-session.test.js lib/panel-ui.test.js lib/panel-auth.test.js lib/panel-api.test.js lib/panel-control-center.test.js lib/panel-delegation-honesty.test.js lib/user-selector.test.js` | `67/67`, fail 0 (`62` prior PANEL tests + `5` corrective tests) |
| full life-call | `npm test` | exit 0; `321/321` total (`320` Node tests + scheduler script), fail 0 |
| deterministic eval | `npm run eval` | calendar `21/21` + late `12/12` = `33/33` |
| API fixture | `npm run smoke:panel-api` | `5/5` HTTP 200 |
| UI fixture | `npm run smoke:panel-ui` | `6/6` sections; semantic controls wired |
| diff and scope | `git diff --check` plus exact path/assertion counters | exit 0; daily-preflight `0`, canonical spec `0`, assertion weakening `0` |

`evals/life-manager-panel.test.js` is absent, so the existing evidence/package 33-case command `npm run eval` is the applicable eval.

## Exactly-one fresh substantive review

- Reviewed diff: `5a4ec98e9a4b2919958ad3d2a95ef78fc9970b69..492174ed2cf43417256842bd87279993cffb9af7`.
- Verdict: **FAIL**.
- Critical findings: `0`.
- Important findings: `1`.
- Passing review dimensions: stable session/logout, tenant isolation, panel/chat state path apart from delegation, provider path contamination, current-dev preservation, CORE 8d exclusion, and test weakening.
- Blocking finding: `user-command.js` advertises and accepts `delegation_enabled`, routes it through `mutate_lm_panel_preferences`, records a succeeded receipt, and returns `Setting updated`; the SQL RPC does not update `delegation_enabled`, while the control center honestly renders delegation as unavailable.
- Independent deterministic reproduction parses `turn delegation on`, executes the production command contract with an RPC-shaped response that omits delegation, and observes `ok=true`, `message="Setting updated"`, `receiptStatus="succeeded"`, and no `delegation_enabled` in returned state.

This remains the only adversarial review. No second adversarial-review loop occurs; its one blocker is closed by the focused corrective and builder-side review below.

## Delegation honesty RED/GREEN closure

- Genuine RED ran before production edits. `0/5` failed for the reproduced reasons: all four EN/JA phrases returned `command`; help advertised delegation; `validateCommand` accepted it; `executeUserCommand` returned success; and no unavailable dispatch helper existed.
- GREEN maps `turn delegation on`, `turn delegation off`, `委任をオン`, and `委任をオフ` to a direct localized `unavailable` status. The status says no safe delegated-action runtime is active and contains no question or approval request.
- `delegation_enabled` is absent from the executable setting allowlist and help actions. Direct `true` and `false` API-shaped commands raise `invalid_action` before store access.
- The manager reproduction is closed: no `ok=true`, no `Setting updated`, no preference mutation, no receipt claim/finish, and no `succeeded` receipt. The Telegram dispatch helper returns the honest status with `executeUserCommand` calls `0`.
- The panel remains unchanged at `controls.delegation.state=unavailable` with the human reason `No safe delegated-action runtime is available`.
- Fail-closed basis: OWASP Authorization Cheat Sheet, https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html#deny-by-default — “configured to deny access by default.”

## One focused builder-side diff review

- Reviewed range: `f1fba91a0ff569b9b415db8565153b99502ec21a..d8c497e87e65d47997809f43b025a89dfe043559`.
- Result: **PASS; findings 0**.
- False success is eliminated; chat/API fail closed; mutation and success receipt paths are unreachable; unavailable copy has no question/approval language; and the fresh PANEL/full/eval/smoke results show no regression.
- Review scope is only this delegation corrective. No process, coverage, style, or new adversarial-review findings are opened.

## Side-effect boundary

- Migration application: `0`.
- Merge: `0`.
- Deploy: `0`.
- Provider credential or account mutation: `0`.
- OAuth start/callback: `0`.
- Telegram sends: `0`.
- Email sends: `0`.
- Calls: `0`.
- Production/staging requests and L3 actions: `0`.
