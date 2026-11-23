# Comedy AI: blind ballot integrity audit (2026-11-23 JST)

**Research/evaluation only; no external posting.** GitHub SSOT: Daisuke134/anicca main at start ff7737666072c3509d3592bc34c6eb6400e70855.

## Actual improvement

Last run produced position-balanced A/B packets, but a packet cannot show whether ratings are genuine, duplicated, or from the intended version. Added **comedy/benchmarks/audit_blind_ballots.py** and 14 tests.

The auditor rejects a corrupted or pre-scored packet, an incorrect v1/v2 answer inversion, leaked model labels, stale packet fingerprint, invalid vote, repeated (rater, task) vote, the same reviewer viewing v1 and v2, or publishing flags not OFF. It maps a v2 B vote onto the same anonymous answer as v1 A, while leaving ties explicit. The synthetic test fixture never counts as human feedback. Human-declared ratings, if supplied later, are labeled SELF_REPORTED_HUMAN_UNVERIFIED rather than independently authenticated.

Position effects in LLM pairwise judging are documented in Shi et al. (2024), https://arxiv.org/abs/2406.07791; also Xu et al. (2026), https://aclanthology.org/2026.findings-emnlp.1444/. Neither study validates any of our new jokes.

## Canonical inputs actually read

| Path | Starting Git blob SHA |
|---|---|
| comedy/AGENTS.md | aa5b798ccb38cb2c3c6dd045e7a26f7adac44b09 |
| skills/comedy-agent/SKILL.md (v0.2.1) | fe21da855d08d5d01feff89be7244176087d4044 |
| comedy/COMEDY-AGENT-LOOP.md | a3325b5851155311a09805d443ea352a239347e6 |
| comedy/benchmarks/README.md | d3f702cff885b9490efc0523811ef03e129f1379 |
| comedy/IMPROV-PLAYBOOK.md | 5f494c648ac6a630fe932342b53c575f4349e3db |
| comedy/feedback/KANEKO-2026-11-15.md | 6c26deba72a978b29da3cfb1975a96d6993451ca |

Also inspected and DID NOT CHANGE: long script v8 comedy/sagi-injury-help.md (099ab68381e23f838299a9706c64f82bfc2dce1d), finalized 2026-09-06 script comedy/sagi-denwa-2026-09-06-live.md (036a10a7a0cd103663c48b56b9ab5137b3f2c4b9), and 2-minute live script comedy/sagi-injury-help-2min-live.md (892ce8db0cc84eece3a64ecf661a7fdc90cc5784). The selected script's exact first/second AI speech and Dais's exclusive opening authority remain unchanged.

Kaneko feedback has imperfect speaker separation; do not quote it verbatim as reliably attributed speech. The telephone-recipient AI identity, explicit Dais-led cue, callback of old people and vehicles, space for Dais's physical reaction, phone audibility, and repeatable Voice delivery remain important, independently unmeasured objectives.

## New data (not the fixed benchmark)

Eight **original internal development tasks**: four general Japanese oogiri, four fictional telephone-dispatcher improv prompts; 2 fresh GPT-6-chat text candidates per prompt, 16 total. Rights: original_internal_draft. No scraping, external submission, or third-party joke reuse. Unedited outputs are in runs/2026-11-23-0955-original-responses.jsonl; questions in runs/2026-11-23-0955-original-tasks.jsonl.

Generator: ChatGPT GPT-6 product label in the current text session. Exact model build, independently verified provider invocation IDs, temperature, and effort are **not available/controlled**. Skill version v0.2.1, Skill Git blob fe21da855d08d5d01feff89be7244176087d4044, starting commit ff7737666072c3509d3592bc34c6eb6400e70855. Two proposals in one chat are **not** independent API repeats. Grok/Muse not executed; no fair multi-model comparison can be claimed.

## Actually executed on macOS Python 3.14.7

| Test | Actual result | Interpretation |
|---|---|---|
| New unittest test_audit_blind_ballots.py | **14/14 PASS** | packet/ballot integrity tests |
| Existing validate_run.py --strict | **16/16 PASS** | text-only format, anchors, and forbidden literal checks |
| Existing prepare_blind_pairs.py | **8 pairs, 2 inversions**, position 4/4 each | balanced display preparation, NOT human ratings |
| New audit_blind_ballots.py, EMPTY ballots | integrity PASS, human 0, NOT_MEASURED | no invented reviews |
| New audit_blind_ballots.py, synthetic fixture | integrity PASS, 16 synthetic, 0 human, NOT_MEASURED | fixture votes excluded from human counts |
| Existing audit_comparison_provenance.py | **NOT_COMPARABLE** | no independent cross-model receipts |
| Existing check_injury_2min.py | PASS, **22 turns/714 spoken characters** | static stage script only |

Reproduction (from comedy/benchmarks):
- python3 -m unittest -q test_audit_blind_ballots.py
- python3 validate_run.py --tasks runs/2026-11-23-0955-original-tasks.jsonl --responses runs/2026-11-23-0955-original-responses.jsonl --output /tmp/formats.json --strict
- python3 prepare_blind_pairs.py --tasks runs/2026-11-23-0955-original-tasks.jsonl --responses runs/2026-11-23-0955-original-responses.jsonl --output /tmp/pairs.json --seed comedy-20261123-0955
- python3 audit_blind_ballots.py --packets runs/2026-11-23-0955-packets.json --ballots runs/2026-11-23-0955-empty-ballots.jsonl --output /tmp/ballots.json

Saved test fixtures and audit JSON are clearly named synthetic; they are NOT actual humans.

## Conclusions and limits

**Measured: pipeline correctness on 14 controlled tests and 16 text format checks.** Not measured: whether any joke is funny, real human votes (0), audience laughter, whether people understand the voice is the AI on the other end of the phone, stage rear-row audibility, actual speaker gating, Dais's physical acting, real audio latency or repeatability. All these remain NOT_MEASURED. Multi-model comparison NOT_COMPARABLE.

Publishing OFF (publish_enabled=false; auto_reply_enabled=false). No external posts, automatic responses or contest entries. Future real human review should present only one A/B variant to each independent person and retain source consent/metadata without publishing private identities. Future Voice measurement needs recordings and microphone/output conditions. Neither can be inferred from synthetic fixtures.
