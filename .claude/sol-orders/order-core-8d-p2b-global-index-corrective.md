# CORE 8d — Phase 2b final-check global VCSDD index correction

Fresh `gpt-5.6-sol`. Work only in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d` at exact clean commit `efb9ee33db32ef94757288166c1707d52c582cb8`, PR #330. No sub-agent. This is a two-file process-isolation correction only.

The Phase 2b implementation/feature-local state is accepted provisionally: state=`2b`, sprintCount=0, 75 test beads green. Do not change app code/tests/evidence/feature state/history/spec/reviews/contracts/provider/deploy/merge.

Restore `.vcsdd/index.json` and `.vcsdd/active-feature.txt` byte-for-byte to their contents at commit `3e8c6df947bb7280e7fa9b37a1749d3c60bf0c4d` (pre-Phase2b), where the repo-wide active feature remains `fable5-config-slimdown`. This must not alter `.vcsdd/features/life-manager-daily-preflight/state.json`; Life Manager stays feature-locally at `2b`.

Verify exact two-file diff, restored bytes equal `3e8c6df94`, feature state/runtime PASS, 75 green/0 red, baseline 51/51, new 63/63, helpers 12/12, clean worktree after commit, and local/upstream/origin/PR equality. Commit/push only those two global files. Return correction commit and NEXT=orchestrator final check then Phase2c.
