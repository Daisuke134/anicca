# Writer global money execution notes

- Fresh `origin/main=95ed258c`; work continues on `fix/writer-w2-resume`. Both Writer owners were idle on release `f7214aac`.
- One claim-loop kick ended exit 75 with a new `MODEL_UNAVAILABLE` receipt, queue 0, and no article-daily wake. External effects remain 0.
- Provider evidence was rc=0/schema-valid but result `{}`. Root cause is the shared empty schema being converted into a Codex schema that permits only an empty object.
- The minimal fix omits provider-side output schema only for `{}`, preserving concrete schemas and local JSON validation. Focused tests pass.
