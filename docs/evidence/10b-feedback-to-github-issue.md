# 10b feedback to GitHub issue evidence

## Result

- Real production intake row `id=1` is `issued`.
- GitHub readback: [issue #1085](https://github.com/Daisuke134/life-manager/issues/1085) is open with label `lm:type:self-heal`.
- The issue body contains the privacy-safe summary, regression-test acceptance criteria, and the deterministic hidden marker derived from the HMAC `source_ref`.
- A second worker pass returns `{"status":"no-op"}`. GitHub readback finds exactly one issue with that marker.
- The existing D0 picker selects issue `#1085`; no new picker or developer loop is created.
- `ai.anicca.life-manager-dev` remains the single daily launchd job at 04:10. Its installed program path is the canonical `apps/life-manager/scripts/life-manager-dev-d0.sh`, which runs the issue worker before delegating to the existing D0.

## TDD and verification

- RED: `node --test lib/feedback-to-issue.test.js` fails because `feedback-to-issue.js` does not exist.
- GREEN: focused contract and runtime tests pass `7/7`.
- Full `npm test` exits `0`; no existing test is weakened.
- All evals remain 100%: calendar `21/21`, late `12/12`, context `12/12`, score `27/27`, intent `18/18`, mental `15/15`, physical `12/12`; panel privacy also passes.
- `git diff --check`, Node syntax checks, and ShellCheck pass.
- Changed-path gitleaks scan reports no leaks; changed-path PII patterns report zero findings.

## Production readback

| Surface | Readback |
|---|---|
| PostgreSQL | row `1`, status `issued`, labels `feedback,calendar,panel`, summary length `70`, issue URL exact |
| GitHub | issue `1085`, state `OPEN`, label `lm:type:self-heal`, marker present |
| Idempotency | second worker pass `no-op`; exact-marker issue count `1` |
| Existing D0 | `pick-issue.sh` selects `#1085` |
| launchd | label `ai.anicca.life-manager-dev`, daily `04:10`, canonical wrapper installed |

No raw Telegram text, chat/user identity, contact data, credential, database URL, or token is committed.

## Reused practices

- GitHub Docs, [Creating an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-an-issue): “To create an issue, use the `gh issue create` subcommand.”
- PostgreSQL, [SELECT](https://www.postgresql.org/docs/current/sql-select.html): “With `SKIP LOCKED`, any selected rows that cannot be immediately locked are skipped.”
- The same PostgreSQL section identifies queue-like tables as the intended contention-avoidance use case. The worker therefore claims one row with `FOR UPDATE SKIP LOCKED`, while its deterministic issue marker handles a crash between provider creation and DB URL writeback.
