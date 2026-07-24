# 10d production error intake evidence

## Result

Three controlled, actually observed production failure classes create exactly three privacy-safe
database rows and three real GitHub issues:

| Failure class | Production row | GitHub issue |
|---|---:|---|
| provider timeout | `2` | [#1088](https://github.com/Daisuke134/life-manager/issues/1088) |
| failed side effect | `3` | [#1089](https://github.com/Daisuke134/life-manager/issues/1089) |
| 5xx + eval regression | `4` | [#1090](https://github.com/Daisuke134/life-manager/issues/1090) |

The probes execute a bounded timer deadline, a real child-process side-effect failure, and a local
HTTP 503 plus a real nonzero eval process. A probe that returns successfully is rejected before any
row is written.

## Privacy and deduplication

- The intake builder accepts only allowlisted signal, component, and fingerprint slugs.
- Raw provider/error content is deliberately absent from the returned schema and persistence call.
- The only persisted fields are `source_ref`, `summary`, and `labels`.
- `source_ref` is an HMAC-derived `err:sha256:` reference; raw error, identity, contact data, and
  credentials are not hash inputs.
- The existing `lm_feedback_intake.source_ref` unique constraint and `ON CONFLICT DO NOTHING`
  remain the single deduplication mechanism.
- A second execution returns `duplicate=true` for all three classes and creates zero rows.
- GitHub readback finds the exact hidden marker once per issue and reports `forbidden=false` for
  raw Telegram/identity/error/secret-shaped content.
- A fourth issue-worker execution returns `status=no-op`.

## Live readback

| Row | Safe source reference | Status and URL |
|---:|---|---|
| `2` | `err:sha256:2074b5cd06bc15b51f6e1ae9b2cd1166` | `issued` → [#1088](https://github.com/Daisuke134/life-manager/issues/1088) |
| `3` | `err:sha256:1b328dae60dfc5abb61b6bdf2b7d2020` | `issued` → [#1089](https://github.com/Daisuke134/life-manager/issues/1089) |
| `4` | `err:sha256:3448d41490349aff474bc87912cd8fc5` | `issued` → [#1090](https://github.com/Daisuke134/life-manager/issues/1090) |

The first two execution attempts fail before mutation: the isolated worktree has no installed
`pg` package, then the production app exposes the canonical `LM_UID_SECRET` fallback rather than a
dedicated feedback provenance variable. The third approach installs the lockfile dependencies and
uses the same fallback already used by `server.js`. No secret value is printed.

## Verification

- Focused intake, injection, persistence, issue, and D0 runtime tests: `22/22`.
- The six required signals map to exactly three closed classes; `http_5xx` and
  `eval_regression` share one root fingerprint.
- Full tests and every eval run from the isolated branch before merge.
- Changed-path and added-line secret/PII scans contain zero findings.

## Reused practices

- OWASP, [Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html):
  “Access tokens” and “Sensitive personal data and some forms of personally identifiable
  information” belong under data to exclude.
- Sentry, [Grouping and Fingerprints](https://docs.sentry.io/product/issues/grouping-and-fingerprints/):
  fingerprints customize how events are grouped into issues.
- PostgreSQL, [INSERT](https://www.postgresql.org/docs/current/sql-insert.html):
  `ON CONFLICT` provides an alternative to raising a unique-constraint violation.

The implementation follows those established mechanisms and reuses the existing production table,
worker, GitHub label, and D0 loop.
