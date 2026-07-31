# Sol order — §10 row 8d / CORE-a only

## Goal and hard boundary

Complete exactly §10 row `8d CORE-a`: create or repair a fail-closed DAILY runtime dependency preflight, prove success/failure/timeout contracts, run one fresh read-only production smoke across every dependency named by the row, update the spec with real evidence, and push only the resulting scoped work.

Done means: the tests prove that no dependency failure or timeout is converted to `0`, empty success, or exit code 0; the fresh production smoke emits a redacted machine-readable artifact for every required dependency; all dependencies pass; relevant verification is green; the spec row contains reproducible evidence; and scoped commits are pushed. Do not start `8e` or any later row.

## Role and authorization

You are Sol. You own investigation, tests, implementation, execution, verification, evidence capture, spec update, scoped commit, and push. Fable performs only final read-only adjudication.

This atomic is a read-only readiness check. You are **not authorized** to dial a call, send an email, write a calendar event, send a Telegram message, post to social media, modify production schema, change billing, or broadcast anything. Those side effects belong to later rows.

Work in an isolated worktree; the root worktree contains unrelated user changes. Never use `git add -A`. Stage only explicit paths you own.

### Base/source split discovered by Fable

The current repository has two required truths on different remote refs:

- `origin/dev` contains the latest merged Life Manager implementation through PR #328 and is the **code integration base**.
- `origin/feature/clip-rewards` contains the current rewritten §10 atomic table (`8d CORE-a`, `9b...`, `10a...`) and is the **spec-file SSOT**. Later `dev` work overwrote that table with an older coarse version even though the rewrite commit appears in history.

Therefore, before investigation or edits:

1. Fetch and verify both facts directly.
2. Inspect `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d`. A previous interrupted attempt may have left it as a clean branch based on `origin/feature/clip-rewards`. Only if it is clean, remove that exact worktree and local `feature/lm33d-daily-preflight` branch.
3. Recreate `feature/lm33d-daily-preflight` from **`origin/dev`**, using raw `git worktree add` rather than `rtk git worktree add` (the wrapper previously obscured base behavior during monitoring).
4. Apply only the canonical spec-file delta from `origin/feature/clip-rewards` into that worktree, e.g. a path-scoped `git diff origin/dev origin/feature/clip-rewards -- <spec> | git apply -`. Verify the resulting §10 contains `8d CORE-a` and that `apps/life-call` contains the PR #328 implementation.

Do not merge the whole `feature/clip-rewards` branch and do not base the code change on its older Life Manager tree.

Do not spawn or wait on nested agents. Execute the work yourself. Report progress with:

```bash
bash ~/.agents/skills/agmsg/scripts/send.sh lm-p0 sol-core-8d fable-main '<concise status>'
```

## Sources of truth to read first

1. `/Users/anicca/anicca-project/AGENTS.md`
2. `/Users/anicca/.codex/RTK.md`
3. `/Users/anicca/anicca-project/docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md` — read §9.5, §9.6, §10 row 8d, §10.0, §10.2, and §10.3
4. Relevant nested `AGENTS.md` files for every path you touch
5. The applicable TDD and spec-driven-development skill instructions

The spec §10 table is the only live state. Historical `done` labels and self-reports are not current-runtime evidence.

## Investigation order

The repository has `.codegraph/`. Use CodeGraph before broad `rg`/file reads to locate:

- the DAILY runtime entry point and current dependency graph;
- existing health, Telegram webhook, calendar/Composio, call/Telnyx, location/Supabase, email/Resend, and discovery checks;
- existing smoke/preflight scripts, test styles, redaction helpers, timeout helpers, and CI commands.

Reuse or copy+tweak existing mechanisms. Verify every referenced file and symbol exists. If outside documentation is truly needed, use primary official sources via the repository-prescribed tools and record the URL plus the relevant sentence.

## Required dependency coverage

At minimum, the preflight manifest and prod smoke must cover:

1. production `/health`;
2. Telegram webhook/bot readiness: `getWebhookInfo`, pending/error fields, and required `allowed_updates` (`message`, `edited_message`, `callback_query`) without exposing tokens;
3. calendar readiness through the actual current Composio path, using authentication/read-only capability only;
4. call readiness through the actual Telnyx path: auth/balance, assigned number, and call-control configuration, with no dial;
5. location readiness through the actual Supabase path: schema/read and current-user state, with no write;
6. email readiness through the actual Resend path: auth plus domain/from readiness, with no send;
7. discovery readiness through the actual bot/config/state path, with no notification or broadcast.

Inspect the real call graph and include any direct transitive production dependency (for example the active model provider) that is required for DAILY runtime to work. Do not invent a check solely from this example.

Every result record must include dependency name, status, latency, a useful redacted evidence field, and failure classification. The overall command must exit nonzero if any required dependency fails or times out. Secrets, full PII, tokens, phone numbers, email addresses, raw user location, and sensitive response bodies must never enter committed artifacts or logs.

## TDD and verification sequence

Follow RED → GREEN → refactor:

1. First add failing tests in the project’s existing style for success, explicit failure, and timeout for each dependency adapter or the shared contract where exhaustive per-adapter duplication would add no value.
2. Prove RED with the smallest relevant command and record its real output.
3. Implement the minimum coherent preflight/harness change.
4. Prove GREEN. Tests must assert that failure/timeout cannot become an empty success, a zero count, or process exit 0.
5. Run the related full suite, typecheck/lint/build defined by this project, and scoped coverage when available. No skipped tests.
6. Run exactly one fresh read-only production smoke. Save a timestamped, machine-readable, redacted evidence artifact under an existing evidence convention; if none exists, use the smallest repository-local convention consistent with nearby ship evidence.

Do not mark 8d done if any required production dependency fails, times out, or cannot be verified. Record the exact failed hypothesis/evidence in §10 and leave the row pending or blocked as defined by the spec. After three genuinely distinct failed approaches to this same atomic, stop and record all false hypotheses in §10.

## Git, spec, and completion

- If code changes are required: create a focused branch, commit and push it, open a PR, and report its URL and head SHA. Do not merge it; Fable will order a separate fresh artifact-only review and adjudicate merge.
- If no code change is required: commit the evidence/spec update to the appropriate current branch and push, still using explicit path staging.
- Update only the authoritative §10 row and directly relevant ship-run evidence. A row can say `done` only when all required tests and the fresh prod smoke pass and the evidence is reproducible.
- Include exact commands, exit codes, artifact paths, test counts, coverage if available, commit SHA, pushed remote ref, and PR URL if any.
- Before finishing, fetch and verify that the reported remote contains the exact commit.

## Stop conditions

Stop and report instead of improvising if this atomic would require a destructive production schema change, a billing-path change, an external send from Dais’s wallet, or any unapproved broadcast/side effect. Do not wait for user input when another safe investigation or test can advance this same atomic.

> Working method (non-negotiable):
> 1. Restate the goal in one sentence + a "done means" criterion before acting.
> 2. Read the actual files before forming opinions; verify every path/function you reference exists in this project.
> 3. Name your riskiest assumption and check it first, while it is cheap.
> 4. The diff is a claim; execution is evidence. Run the project's build/lint/tests and report their real output.
> 5. Label claims VERIFIED (ran it) / REASONED (read it) / ASSUMED (unchecked) — never upgrade one silently.
> 6. Before finishing: re-read the original request; every requirement met, nothing promised-but-undone.
