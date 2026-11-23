# Comedy AI research: position-balanced A/B review without fictitious humor scores

Date: 2026-11-23 JST. Mode: RESEARCH / EVAL, **internal only**. Source of truth: GitHub `Daisuke134/anicca` `main` at the beginning of the run (`2c01f4cf550c280011737b66bf265f26768727f7`).

## Motivation

Previous cycles improved objective hard gates, timing metadata, provenance and transcript consistency, but **none established that proposed jokes are funnier**. The next useful step is to make a controlled *human* comparison possible without systematically favoring the first displayed candidate. Pairwise evaluation has known position biases (Shi et al., *Judging the Judges*, https://arxiv.org/abs/2406.07791). A live improv humor study also used audience ratings rather than equating a generation test with humor quality (https://www.clinjournal.org/clinj/article/view/214). These works inform the study design; neither validates our specific Japanese sketch.

## Canonical inputs reviewed

- `comedy/AGENTS.md` blob `aa5b798ccb38cb2c3c6dd045e7a26f7adac44b09`.
- `skills/comedy-agent/SKILL.md` v0.2.1 blob `fe21da855d08d5d01feff89be7244176087d4044`.
- `comedy/COMEDY-AGENT-LOOP.md` blob `a3325b5851155311a09805d443ea352a239347e6`.
- `comedy/benchmarks/README.md` initial blob `acf15700602b3431b73be7334939690ae2a1733d`.
- `comedy/IMPROV-PLAYBOOK.md` blob `5f494c648ac6a630fe932342b53c575f4349e3db`.
- `comedy/feedback/KANEKO-2026-11-15.md` blob `6c26deba72a978b29da3cfb1975a96d6993451ca`.
- Also read `comedy/feedback/REVIEW-2026-11-22-INJURY-RETRY.md` and `comedy/sagi-injury-help-2min-live.md`. Kaneko attribution in the feedback transcript is uncertain; do not present it as verbatim quotations.

## New material and invocation provenance

- **Original internal development questions, not the fixed benchmark**: 8 new legally original text prompts (4 general oogiri, 4 telephone-dispatcher stage improvisations); 2 text candidates each, 16 total. No third-party Oogiri site corpus used; rights `original_internal_draft`.
- Generator: this ChatGPT text session, product label **GPT-6**. Precise model build and provider API receipt **not available**. Invocation `chat_session`, no independent API repeats, temperature/effort **NOT_CONTROLLED**; Skill blob SHA above. Each response (including its metadata) is saved verbatim, with no post-hoc selection.
- Grok / Muse not run. Reason Network Primary, DAISUKE, MK each returned **HTTP 409 `agent_network_offline`** when queried. Do not claim a multi-model comparison.
- `audit_comparison_provenance.py`: **NOT_COMPARABLE** (fewer than two models, missing API receipts, no verified independent invocation, unknown/invalid controlled settings).

## Implemented: position-balanced human review packet preparation

- `comedy/benchmarks/prepare_blind_pairs.py` uses deterministic seeded task ordering to position candidate #1 first for 4/8 tasks in version `v1`, and candidate #2 first for 4/8; `v2` reverses every A/B pair. Each reviewer **must see only one version**, not both. Source model labels, run IDs and Skill SHA are excluded from presentation cards, but they remain in the source records.
- It requires original rights, complete paired candidates, nonblank text, separate candidate text, valid Skill blob SHA, matching Skill within each pair, and passage of existing objective hard gates. Inputs failing these checks are rejected rather than silently removed.
- Public raw answer text can be cross-matched with the public packet, so **true blinding of a reviewer with repository access is NOT guaranteed**. This is a prepared protocol and packet, *not* a completed blind study or a provider-controlled model comparison.
- Present a single version to each independent evaluator later; permitted results are A / B / TIE, with a qualitative rationale. Do not expose the parallel version during evaluation. Before any conclusion about humor, collect independent judgments and assess agreement, order, and task effects. No raters contacted in this cycle.

## Actually executed, on connected Mac mini using read-only in-memory Python

The Mac mini's normal git fetch attempt failed with **No space left on device** (filesystem earlier showed ~143 MiB available and was exhausted during the fetch attempt). We did **not** modify or clean its dirty existing checkout; instead the GitHub branch contents were re-read and executed using `python3 -c` without writing files.

- Unit tests: **13/13 PASS** (including swapped order, 4/4 balance, deterministic reproduction, metadata exclusion, missing/duplicate responses, hard-gate failure, Skill mismatch, nonhex SHA, identical answers, unlicensed source, zero human labels).
- Existing `validate_run.score` run on 16 actual generated responses: **16/16 objective gate PASS**. This is **not** a rating of originality or funniness.
- Prepared packet: 8 pairs × 2 counterbalanced variants. `v1` A-side 4 sample-1 / 4 sample-2; `v2` A-side 4 sample-2 / 4 sample-1. `human_judgments=0`, `review_status=NOT_MEASURED`. Packet JSON generated by **executing the Python implementation**, not simulated.
- Pre-existing 2-minute script static checker executed in memory against `main`: **PASS**, 22 dialogue turns, 714 spoken characters. This does not measure a two-minute real-world runtime or Voice adherence.
- Original full v8 blob `099ab68381e23f838299a9706c64f82bfc2dce1d`, 9/6 confirmed script blob `036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`, current 2-min script blob `892ce8db0cc84eece3a64ecf661a7fdc90cc5784`: **do not edit**.

## Stage interpretation, Kaneko feedback and limits

Future human ratings should separately check whether audience can identify the offstage voice as the **AI rescue dispatcher on Dais's phone**, whether Dais's starting cue alone activates it, if the first two exact utterances stay intact, whether the dispatcher uses existing cast (おもち34号 / 右折田 / 会田 / 病院), and whether Dais has physical reaction room. Ratings of text originality must not be confused with live delivery, audience laughter, audibility in rear seats, third-party speaker filtering, real Voice delay, or 2-minute duration. All these live/audio fields are **NOT_MEASURED**. Any apparently real emergency overrides fictional acting.

## Outputs and publication boundary

- `comedy/benchmarks/runs/2026-11-23-0853-blind-pair-tasks.jsonl` — original 8 tasks.
- `comedy/benchmarks/runs/2026-11-23-0853-blind-pair-responses.jsonl` — all 16 unedited text outputs and model/Skill provenance.
- `comedy/benchmarks/runs/2026-11-23-0853-counterbalanced-review-packets.json` — unscored, order-reversed v1/v2 preparation.
- `comedy/benchmarks/prepare_blind_pairs.py` and `test_prepare_blind_pairs.py` — implemented code and executed tests.

`publish_enabled=false`, `auto_reply_enabled=false`. **No X post, contest submission, external automated browsing, bulk applications or user impersonation**. No claim of permanent model training, superior humor, real audio repeatability or observed audience laughter.
