# self-improve

Per-instance self-improvement loop (spec 18 §1, #335). Every 6h: build a self-model → detect
slop/failures → file a GitHub issue → attempt an autonomous, eval-gated fix → open a PR → share
the learning to the swarm. North Star + Law I are immutable and never auto-edited.

See `SKILL.md` for the full contract. Run the E2E test with:

```bash
bash skills/self-improve/tests/test_self_improve_e2e.sh
```
