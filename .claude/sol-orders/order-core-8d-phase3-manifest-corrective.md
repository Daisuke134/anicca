# CORE 8d — Phase 3 manifest canonical-spec corrective only

Fresh `gpt-5.6-sol`. Work only in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d` at exact clean commit `1a3ce38630a78a42b154bbe3e1a4bcb7e6741b24`, PR #330. No sub-agent and no review.

The orchestrator independently found that the Phase 3 manifest points to the worktree-relative root spec, whose SHA-256 is `35e521617787a48ed2a7373bea8621d34262bcb3a091836f2c994b7d88b70a1a`, while the user-declared canonical live spec is `/Users/anicca/anicca-project/docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`, current commit `d5e261724`, SHA-256 `2235b89a9a734f30539e364006af68d87285c7a310eb3d644693d7e84367782a`, and contains the current Phase 2c evidence. A reviewer reading the relative path would grade stale §10.

Modify only `.vcsdd/features/life-manager-daily-preflight/reviews/sprint-1/input/manifest.json` so the canonical spec input uses that exact absolute path and carries an explicit immutable `sourceCommit=d5e261724` and `sha256=2235b89a9a734f30539e364006af68d87285c7a310eb3d644693d7e84367782a`. Update the manifest closed-key validation as needed within the artifact itself, without changing any other review inputs, commits, contract digest, state/history, source/tests/evidence, global VCSDD files, or output directory.

Freshly validate: absolute canonical file exists; hash and commit match the live root checkout; current §10 row 8d and §10.0 contain Phase 2c evidence `8275d5d9f`; all other 53 artifact paths still exist relative to the review worktree; manifest is closed, duplicate-free, review output absent; state remains Phase 3/sprintCount 0; worktree diff is exactly the manifest.

Commit/push exactly the manifest. Return `RESULT=MANIFEST-CANONICAL-SPEC-FIXED` or `BLOCKED`, validation, commit, push, and `NEXT=fresh artifact-only adversary`.
