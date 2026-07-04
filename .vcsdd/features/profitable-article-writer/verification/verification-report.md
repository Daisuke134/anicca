# Verification Report — profitable-article-writer, Sprint 1

Mode: strict. Phase 5 (formal hardening). Sprint 1 = the article-orchestration SKELETON, draft-first.

## Proof Obligations

Sprint-1 required proof obligations, each proven by a green oracle test (13/13, real logic; `bash tests/run-red.sh`):

| PROP | Obligation | Proven by | Status |
|---|---|---|---|
| PROP-1 | model-agnostic (no provider/model/API-key literal; sonnet tier allowed) | test-prop1 (+ negative case: `claude-3-opus` draft fails) | proved |
| PROP-2 | Mode-B path has no human-gating call | test-prop2 | proved |
| PROP-3 | no external-repo/tool execution in the write-path | test-prop3 | proved |
| PROP-5 | fail-closed publish wiring (only both-PASS publishes) | test-prop5 (injected seam) + test-v0-real/test-v05-real (real gates, no-mock) | proved |
| PROP-6 | Mode A stops at draft + notify (url+screenshot), never publishes | test-prop6 | proved |
| PROP-9 | sonnet tier; record-earn no-LLM (fail-closed on flip) | test-prop9 | proved |
| PROP-10 | per-install creds only; no shared/Dais account | test-prop10 | proved |
| PROP-12 | account-absent → self-create-eligible / flag-unavailable, never a loud failure | test-prop12 | proved |
| PROP-14 | no-viable-topic → skip (no article) | test-prop14 | proved |
| PROP-15 | 3-round abort ceiling + failure recorded (hostile-topic JSONL safe) | test-prop15 + test-json-escape-fallback | proved |

Real-gate mechanics (v0 heading/size, v05 (e) arithmetic + judge_v05 response parser) proven no-mock by `test-v0-real.sh` / `test-v05-real.sh` with the FORCE seams unset.

## Summary

All Sprint-1 required proof obligations are proved by green, non-vacuous oracle tests, independently re-run by the
main agent. Adversary implementation review (Phase 3) PASSed after 3 rounds with zero open findings. No formal
proof tooling (e.g. TLA+, model checking) is applicable to this bash orchestration skeleton; correctness is
established by the oracle suite + adversarial review. Deeper formal/property work applies at Sprint 2+ when real
publish and on-chain earn land.
