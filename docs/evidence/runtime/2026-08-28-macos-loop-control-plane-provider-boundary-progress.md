# macOS Loop Control Plane — TODO 7 provider boundary

This slice removes the prohibited Codex subscription-account rotation and
consolidates the active Gig, Job Search, Connector, Mr.bot daily, and X
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
- Gig launchd definitions, helper defaults, Job Search, Connector, Mr.bot
  daily, X repost/tweeter/digest, and portable Lancers releases reference the
  canonical runner.
- X model calls preserve their downstream deterministic JSON/effect gates and
  no longer create `CODEX_HOME`, link `auth.json`, or invoke `codex exec`.

Source scans show zero account rotation, account-index fallback, provider env
override, or direct auth selection in the canonical router and zero direct
profile/auth selection among active existing registry entrypoints.

## Writer completion

The two misclassified Writer registry entrypoints now name their business
workers:

- `writer-opportunity-discovery`
- `writer-opportunity-response`

Their judge calls use `shared-model-runner.py`. The established
`model-runner.sh` CLI delegates production agent/judge/vision/Sol/repair/session
runs to the canonical router. Repair keeps its workspace-write cage, `/tmp`
exclusions, network denial, explicit session ID, live event stream, and
schema-bound last message. Explicit fake binaries retain the historical command
contract for isolated tests only; no installed Writer plist configures one.

## Final readback

- Active existing registry entrypoints with direct `CODEX_HOME`, `auth.json`,
  or `AGENT_RUNNER_PROVIDER`: 0.
- Canonical runtime account rotation/failover symbols: 0.
- Canonical Codex profiles: exactly `acct2`; every Codex candidate names it.
- Duplicate operational provider runners: 0.
- Production Writer delegation tests: normal judge and repair/session pass.

Twenty-four unrelated Writer repair-state tests already fail identically at
the pre-slice commit `50b8c9ea6`; the isolated baseline run records the same
24-test list. They remain a final full-suite blocker, not evidence against the
provider/profile boundary.
