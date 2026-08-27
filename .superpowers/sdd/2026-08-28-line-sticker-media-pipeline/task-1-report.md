# Task 1 report

## Status

Implemented and pushed on `feat/line-sticker-loop`.

## Commits

- `5510c712d` — `feat(line-sticker): build animated media packages`
- Follow-up report commit is created separately after this file is written.

## Test summary

- RED: before production code, the media suite failed with `ModuleNotFoundError: No module named 'line_sticker_media'`.
- Media focused suite: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/earn/line-sticker/tests/test_line_sticker_media.py -v` → `Ran 11 tests in 25.413s / OK`.
- Existing validator/owner suite: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest skills/earn/line-sticker/tests/test_line_sticker.py -v` → `Ran 78 tests in 300.097s / OK`, wrapper `EXIT=0`.
- `git diff --cached --check`: PASS before commit.
- Real temporary FFmpeg six-batch fixture produced 60 candidates, selected 24, and passed `validate_package` after deterministic APNG normalization and package assembly.
- CLI parse failure emitted one JSON object with empty stderr and no prompt body.

## Concerns

- `line_sticker_media.py` is 1,621 LOC and its focused tests are 370 LOC; this is above the Ponytail soft target and should be split or reduced before broad extension.
- The existing validator requires an exact six-key `provenance.json`, while the media brief asks for richer provenance. The official package keeps the validator-compatible schema; richer provenance is written as work-dir `provenance-ledger.json`.
- Provider/model names are not CLI inputs and are unknown before the first adapter response. The pre-call intent key uses deterministic command/plan hints and records response identities afterward; the contract should define an explicit preflight identity or reconciliation protocol.
- Unknown provider acknowledgements are durably fenced as `reconcile_unknown`; this slice does not expose a CLI reconciliation command carrying the same request id and output hash.
- Command output is captured in temporary files and rejected when either file exceeds 1 MiB; a stricter streaming hard cap may be preferable if untrusted adapters can emit sustained output.
