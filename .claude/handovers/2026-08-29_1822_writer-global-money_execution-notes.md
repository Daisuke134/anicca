# Writer global money execution notes

- Fresh `origin/main=95ed258c`; work continues on `fix/writer-w2-resume`. Both Writer owners were idle on release `f7214aac`.
- One claim-loop kick ended exit 75 with a new `MODEL_UNAVAILABLE` receipt, queue 0, and no article-daily wake. External effects remain 0.
- Provider evidence was rc=0/schema-valid but result `{}`. Root cause is the shared empty schema being converted into a Codex schema that permits only an empty object.
- The minimal fix omits provider-side output schema only for `{}`, preserving concrete schemas and local JSON validation. Focused tests pass.
- PR #3109 merged as `f8600ca9`; the main-derived full release was cut and target-applied to `writer-claim-loop`. Production then returned a real SELECT, proving the empty-object blocker closed. The next receipt was `DEMAND_CARD_INVALID` because a selected price receipt appeared in `binding_observation_ids` but not the parent `observation_ids`; article-daily remained untouched. The follow-up normalization adds only already-selected immutable binding IDs before the existing evidence gates.
- PR #3120 merged as `c38659a4`; a main-derived sparse Writer release was target-applied to `writer-claim-loop`. Production is now `FILLED`, queue 0 to 1, with hash-bound topic `paid-demand:18146fa2060e913ba97f2b80c7087258b281d3d1ee9d990dd7dd1d8b0bed0b6f` and exit 0. Article-daily was not triggered because free capacity fluctuated around 1.0 to 1.3 GiB, below a proven article-run floor; external article effects remain 0.
