# Comedy AI research cycle — recording provenance / pseudoreplication guard (2026-11-23 07:55 JST)

## Evidence baseline and scope
- Canonical repository: `Daisuke134/anicca`, branch `main` at cycle start `a8da1ca90b14ff6b8f14263d9a441c0bf06801eb`.
- Read `comedy/AGENTS.md` (`aa5b798ccb38cb2c3c6dd045e7a26f7adac44b09`), `skills/comedy-agent/SKILL.md` (`fe21da855d08d5d01feff89be7244176087d4044`), `comedy/COMEDY-AGENT-LOOP.md` (`a3325b5851155311a09805d443ea352a239347e6`), `comedy/benchmarks/README.md` (`3216991539eeaa8be855bc3bf7fc00589dafdc6e`), `comedy/IMPROV-PLAYBOOK.md` (`5f494c648ac6a630fe932342b53c575f4349e3db`), `comedy/feedback/KANEKO-2026-11-15.md` (`6c26deba72a978b29da3cfb1975a96d6993451ca`).
- Also inspected current 2-minute script and 2026-11-22 failure review. Protected: `sagi-injury-help.md` v8 (`099ab68381e23f838299a9706c64f82bfc2dce1d`), 9/6 confirmed script `sagi-denwa-2026-09-06-live.md` (`036a10a7a0cd103663c48b56b9ab5137b3f2c4b9`), selected two-minute script (`892ce8db0cc84eece3a64ecf661a7fdc90cc5784`). **No edits to protected scripts or Skill.**

## Problem and implementation
Previous `audit_stage_repeatability.py` accepted two `audio_annotated` run IDs pointing at the **same recording reference** and reported `SAME_DECLARED_CONDITIONS_ONLY`. This is pseudoreplication: two annotations of the same captured performance are not automatically independent rehearsals. It also did not detect reuse of a self-declared recording content digest under another filename.

The offline auditor now:
1. Tracks stripped `recording_ref` values for `audio_annotated` runs. Reuse creates a `reused_recording_ref` provenance issue and makes `repeatability_comparison=NOT_COMPARABLE`.
2. Optionally accepts `recording_sha256` (64 hex characters, case-insensitive). A repeated digest, including under a different `recording_ref`, creates `reused_recording_sha256`. Invalid digests are rejected. Synthetic source records cannot claim recording evidence.
3. Reports `recording_uniqueness` and per-run `provenance_issues` **separately from dialogue PASS/FAIL**. A reused recording can pass a text-only stage script gate while still failing independent-run provenance.
4. Does **not** open recordings or authenticate SHA-256 claims: even `UNIQUE_SELF_REPORTED_REFERENCES_ONLY` does not prove independent real-world trials or audio reproducibility.

## Actual executed tests (on connected Mac mini, isolated /tmp working directory)
- Baseline: 14/14 unit tests PASS before modification.
- Modified script: **19/19 unit tests PASS** (5 new cases: same recording ref, unique refs, same digest with different refs, invalid digest, synthetic false evidence).
- CLI synthetic negative control `2026-11-23-0755-duplicate-synthetic.json`: two *fictional* annotation records with the same fake recording ID, both text gates PASS, provenance `DUPLICATE_DECLARED_RECORDING_EVIDENCE`, comparison `NOT_COMPARABLE`, `--strict` exit 1 (expected).
- CLI synthetic positive control `2026-11-23-0755-unique-synthetic.json`: two distinct *fictional* IDs, text gates PASS, comparison `SAME_DECLARED_CONDITIONS_ONLY`, `--strict` exit 0; still **not verified as audio**.
- This proves only **deterministic auditor behavior on synthetic metadata**. No voice recording, real listener, laughter, audience or sound-pressure measurement was performed.

## New answer generation (original internal development set, NOT a fixed benchmark)
- Created **eight new original tasks** (4 standalone oogiri, 4 phone-AI stage ad-libs) and **16 text drafts** (two variants per task). No external website prompt, copyrighted submission or contest content was used.
- Model: ChatGPT **GPT-6** (product label). The two candidates per prompt were produced in the **same chat context**, *not* separate provider API invocations. Exact model build, temperature, effort and provider receipt: **unavailable / uncontrolled**.
- Frozen skill Git blob: `fe21da855d08d5d01feff89be7244176087d4044`; starting main / skill commit field `a8da1ca90b14ff6b8f14263d9a441c0bf06801eb`.
- Executed `validate_run.py --strict`: **15/16 PASS, 1/16 FAIL**. The original draft for `20261123-0755-st03` candidate A used 豆腐田プル男 but **omitted the required literal world anchor 絹ごし3号**. Kept the failed answer, without cherry-picking or quietly rewriting it. This is a lexical hard gate, not a humor score.
- Executed `audit_comparison_provenance.py`: **NOT_COMPARABLE**, reasons `fewer_than_two_models`, `invalid_generation_setting`, `missing_generation_setting`, `missing_provider_receipt`, `no_verified_independent_invocation`.
- Reason Network connection checks for the available three links all returned HTTP 409 `agent_network_offline`. Therefore **Grok/Muse NOT_RUN**, no model ranking.

## Stage relevance and next evidence
- Kaneko feedback: phone-end AI role, Dais's explicit start cue, no early AI speech, literal opening and second line, concrete callbacks (おもち34号・右折田・絹ごし3号・会田), Dais's reaction space, and back-of-room intelligibility remain the performance specification.
- This cycle addresses **audio provenance and repeatability claims**, not stage delivery itself. Current AI voice latency, actual speaker separation, loudness, start-cue precision, improv laughter, and audience understanding: **NOT_MEASURED**.
- Scripted safety exception for clearly real emergencies remains in force.
- `publish_enabled=false`, `auto_reply_enabled=false`. No X posts, contest entries, third-party scraping, mass replies, or external publishing.

## Reproduction
```bash
python3 comedy/benchmarks/test_audit_stage_repeatability.py -q
python3 comedy/benchmarks/validate_run.py --tasks comedy/benchmarks/runs/2026-11-23-0755-tasks.jsonl --responses comedy/benchmarks/runs/2026-11-23-0755-responses.jsonl --output /tmp/comedy-0755-format.json --strict
python3 comedy/benchmarks/audit_comparison_provenance.py --tasks comedy/benchmarks/runs/2026-11-23-0755-tasks.jsonl --responses comedy/benchmarks/runs/2026-11-23-0755-responses.jsonl --output /tmp/comedy-0755-provenance.json
python3 comedy/benchmarks/audit_stage_repeatability.py --input comedy/benchmarks/runs/2026-11-23-0755-duplicate-synthetic.json --output /tmp/comedy-0755-duplicate.json --strict
```
**Expected**: unit test exits 0; format strict exits 1 because the preserved draft fails; provenance auditor exits 0 while reporting NOT_COMPARABLE; duplicate fixture strict exits 1 as a desired negative test. None of these scripts uploads or publishes anything.
