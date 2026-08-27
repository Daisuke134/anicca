# macOS Loop Control Plane — TODO 7 provider boundary progress

This slice removes the prohibited Codex subscription-account rotation and
consolidates the active Gig, Job Search, Connector, Life Manager daily, and X
callers on `runtime/agent-runner/agent_runner.py`.

## Closed in this slice

- `providers.codex.accounts` and account expansion/retry code are removed.
- Every Codex route names the single explicit `profile_alias=acct2`; missing or
  unknown aliases fail before provider launch.
- `AGENT_RUNNER_PROVIDER` caller overrides are removed. Provider order comes
  only from canonical task-class config.
- The duplicate `skills/earn/gig/agent-runner` is removed. Token-budget,
  bounded-history, and context-packet utilities needed for parity move to the
  canonical runtime boundary.
- Gig launchd definitions, helper defaults, Job Search, Connector, Life Manager
  daily, X repost/tweeter/digest, and portable Lancers releases reference the
  canonical runner.
- X model calls preserve their downstream deterministic JSON/effect gates and
  no longer create `CODEX_HOME`, link `auth.json`, or invoke `codex exec`.

Source scans show zero account rotation, account-index fallback, provider env
override, or direct auth selection in the canonical router and zero direct
profile/auth selection among active existing registry entrypoints.

## Remaining before TODO 7 is complete

Two active labels still reach the legacy Writer model boundary:

- `writer-opportunity-discovery`
- `writer-opportunity-response`

Both point to `skills/writer-agent/runtime/model-runner.sh`, whose repair,
session resume, judge broker, and vision contracts must be adapted without
losing behavior. TODO 7 remains pending until these two paths and their callers
use the canonical router and the final direct-provider scan is zero.

