# Writer global money execution notes

- Fresh `origin/main=95ed258c`; work continues on `fix/writer-w2-resume`. Both Writer owners were idle on release `f7214aac`.
- One claim-loop kick ended exit 75 with a new `MODEL_UNAVAILABLE` receipt, queue 0, and no article-daily wake. External effects remain 0.
- Provider evidence was rc=0/schema-valid but result `{}`. Root cause is the shared empty schema being converted into a Codex schema that permits only an empty object.
- The minimal fix omits provider-side output schema only for `{}`, preserving concrete schemas and local JSON validation. Focused tests pass.
- PR #3109 merged as `f8600ca9`; the main-derived full release was cut and target-applied to `writer-claim-loop`. Production then returned a real SELECT, proving the empty-object blocker closed. The next receipt was `DEMAND_CARD_INVALID` because a selected price receipt appeared in `binding_observation_ids` but not the parent `observation_ids`; article-daily remained untouched. The follow-up normalization adds only already-selected immutable binding IDs before the existing evidence gates.
