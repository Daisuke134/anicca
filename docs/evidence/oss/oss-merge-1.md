# OSS-MERGE-1 evidence

## Verified outcome

The remote `feature/oss-merge-1` tree is self-contained at verified commit
`edea1e06b461959ccecd37284b92bb3624fcd0c7`. PR #1268 is mergeable; canonical
`main` readback remains the last close gate.

| Gate | Evidence |
|---|---|
| Fresh remote clone | shallow clone of exact remote commit `edea1e06b…`; clean before and after |
| Root install | `npm ci` PASS |
| OSS boundary | 11/11 contract tests and `npm run verify:oss` PASS; seven required source classes present; Gitlinks, external source roots, duplicate runner, unclassified manifest drift 0 |
| Isolated installer | `LIFE_MANAGER_HOME=<temp>/runtime LIFE_MANAGER_INSTALL_DAEMON=0 ./install.sh` PASS; `.env` created/preserved; LaunchAgents 0 |
| App install/test | app `npm ci` PASS; fresh-clone `npm test` 647/647; panel score 14/14 |
| Deterministic evals | calendar 21/21, late 12/12, context 12/12, score 27/27, intent 18/18, mental 15/15, physical 19/19, relations 10/10 |
| Panel privacy eval | api 177, browser 63, recipes 19, channels 9 |
| Single runtime engine | `runtime/agent-runner` 9/9; marketing wiring 10/10; job loop 152/152; second runner 0 |
| Browser auth focused | 84/84 PASS on the integrated tree |
| Current-tree privacy | tracked PII-shape scan 0; Python security manifest 13/13; `gitleaks dir` 0 |
| Language/runtime checks | all tracked shell and Python source parses |

The repository's older shared history still triggers the pre-existing history-mode gitleaks scan.
No history rewrite or credential-rotation claim is made here; this proof is for the canonical
branch tree and a depth-one distributable clone.

## Scope boundary

No loaded Mac loop was unloaded, restarted, or moved during this atomic. Runtime state, credentials,
logs, generated media, and user destinations remain external to the repository. This proof does not
claim `BROWSER-AUTH-1`: real Luma encrypted-session restore through the production cloud queue is the
next cursor after the merged-main readback.

The two historical RevenueCat credentials recorded in
`docs/evidence/oss/oss-security-baseline-1.md` remain an external Anicca iOS/API
incident. RevenueCat is not a Life Manager connector or completion gate.
