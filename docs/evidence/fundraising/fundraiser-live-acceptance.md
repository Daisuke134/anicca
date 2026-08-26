# Fundraiser live acceptance

## Natural recurrence

- Owner: `ai.anicca.fundraiser`
- Cadence: `StartInterval=1800`
- Prior run: `20260826T072236Z-15209`, finished `2026-08-26T07:32:25Z`
- Natural run: `20260826T080226Z-24897`, started `2026-08-26T08:02:27Z`
- Manual kickstart between these runs: none
- Launchd run count: 12 to 13

## Runtime route

- Task class: `application-intent-planner`
- Route: `luna-high-isolated-application-intent`
- Provider/model: `codex` / `gpt-5.6-luna`
- Effort: `high`
- Attempts: 1
- Timed out: false
- Schema valid: true

## Natural-pass outcome

- Submitted: 6
- Submit unknown: 0
- Checkpoints: 2
- Telegram: every terminal report and aggregate returned `TELEGRAM_SENT=true`
- Worktree changes made by the runtime: none

Official Sent readbacks exist in the private application receipt ledger for:

1. Scion Ventures
2. Lobby Capital
3. Llama Ventures
4. Lightside Venture Capital
5. Eastlink Capital
6. TechLink Ventures

The pass did not replay Samsung Catalyst Fund, Cana, or B Capital. It continued after failures and
checkpoints: SF Startup Labs became a retryable browser failure, while 43 and Camford Capital became
human checkpoints. No provider-specific production code was added during the pass.

Private Gmail message IDs, account hashes, credentials, founder fields, and full receipt records
remain outside this public evidence file.
