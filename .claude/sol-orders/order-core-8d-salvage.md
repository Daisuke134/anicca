# CORE-a / 8d dirty-worktree salvage order

You are a fresh Sol taking over a saved dirty worktree after the prior builder was stopped for a hook-induced repeated-diff loop. Your only job is to verify the existing scoped changes, keep 8d truthfully pending, commit them, and push PR #330's branch. Do not rerun production smoke or any external side effect. Do not spawn or invoke another reviewer/agent; main orchestrator performs the fresh review after push.

Working method (non-negotiable):
1. Restate the goal in one sentence + a "done means" criterion before acting.
2. Read the actual files before forming opinions; verify every path/function you reference exists in this project.
3. Name your riskiest assumption and check it first, while it is cheap.
4. The diff is a claim; execution is evidence. Run the project's build/lint/tests and report their real output.
5. Label claims VERIFIED (ran it) / REASONED (read it) / ASSUMED (unchecked) — never upgrade one silently.
6. Before finishing: re-read the original request; every requirement met, nothing promised-but-undone.

## Workspace

- Worktree: `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d`
- Branch: `feature/lm33d-daily-preflight`
- Starting committed head: `a22b6bd26d9403c70bc717538bdf420c1d04b56c`
- PR: `https://github.com/Daisuke134/anicca-products/pull/330`
- Expected dirty paths only:
  - `.vcsdd/features/life-manager-daily-preflight/evidence/daily-preflight-20260721T064624Z.json`
  - `apps/life-call/lib/daily-preflight.js`
  - `apps/life-call/lib/daily-preflight.test.js`
  - `apps/life-call/lib/travel.js`
  - `apps/life-call/lib/travel-routes.test.js`
  - `apps/life-call/lib/user-selector.js`
  - `apps/life-call/lib/user-selector.test.js`
  - `apps/life-call/scheduler.js`
  - `apps/life-call/scripts/daily-preflight.js`
  - `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`

## Preserved evidence

- TDD RED: existing 5 pass plus 8 new blocker tests fail.
- Corrected GREEN: focused preflight/shared-contract suite 34/34.
- Full `npm test`: 312/312.
- Full Node test-file coverage run: 406/406. Production module coverage recorded in spec: daily-preflight lines/functions 91.38/96.43, travel 91.79/91.89, user-selector 100/100; scheduler module-wide lower but changed cohort paths directly tested.
- Eval: calendar 21/21 and late 12/12.
- Corrected production verification was run exactly once and must not be repeated: exit 1, 6/9 pass, 3 fail (`telegram` pending_updates=1 despite successful TG round-trip; `call` Telnyx webhook exact mismatch; `email` controlled send provider rejected and no receipt).
- Controlled side effects already consumed: TG `/panel` round-trip 1; Resend POST attempt 1; no call dial, calendar/location/discovery write, broadcast, schema, credential, or billing change.
- Artifact contains hashed TG refs and no opaque panel URL. 17 production secret values were compared previously: diff leak 0, artifact leak 0.
- 8d must remain `pending`; 8e must remain untouched.

## Required steps

1. Verify branch/head and that dirty paths are exactly the expected list. If any unrelated path exists, do not stage it.
2. Inspect the diff and artifact compactly. Confirm the spec says 8d pending with 6/9 and exact three failure classes. Confirm the artifact is valid JSON and its summary/dependencies agree.
3. Run locally only, with no Railway/provider/network commands:
   - `node --test lib/daily-preflight.test.js lib/user-selector.test.js lib/travel-routes.test.js test/scheduler.test.js`
   - `npm test`
   - `npm run eval`
   - `node --check` for every changed JS production/script file
   - `git diff --check`
   - pattern-based PII/secret/query/opaque URL scan of the new artifact and diff without printing matching values
4. If a local verification fails, make only the smallest in-scope TDD correction, rerun the affected and full checks, and describe it. Do not alter production evidence or claim a new smoke.
5. `git fetch origin`, stage only the ten explicit scoped paths above, commit with a conventional message, and push `feature/lm33d-daily-preflight`.
6. Verify local HEAD equals `origin/feature/lm33d-daily-preflight`, worktree is clean, and PR #330 remains OPEN. Do not merge.

Return a compact VERIFIED report: ending head, exact changed/staged paths, tests/eval exits and counts, artifact summary, secret/PII scan counts, spec state, commit/push/PR facts, and remaining three production blockers.
