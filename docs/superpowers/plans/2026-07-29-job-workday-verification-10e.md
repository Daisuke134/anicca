# Job Workday Verification 10E Implementation Plan

> **Execution guard:** Use Superpowers test-driven-development and
> verification-before-completion. Opening an activation URL is an external side
> effect and must use the existing inbox loop plus a durable fence.

**Goal:** The inbox loop detects a Workday candidate-account verification
email, accepts only one HTTPS activation URL bound to a tenant already present
in the private credential store, and opens it at most once without exposing its
token.

**Architecture:** Extend deterministic Gmail prefiltering before the model.
A pure extractor treats the email as untrusted text, validates sender, subject,
scheme, exact known tenant host, and activation-path shape, then returns a
private target plus a secret-free receipt. A private SQLite store fences browser
navigation as `claimed -> navigation_started -> opened|navigation_unknown`.
Anything at or after `navigation_started` is never blindly retried.

**Tech stack:** Python standard library (`email.utils`, `html`, `urllib.parse`,
`sqlite3`), existing Gmail/CDP transports, `unittest`.

## Constraints

- Sender must parse to `@myworkday.com`.
- URL must be HTTPS, have no embedded credentials, match an exact tenant from
  the private Workday credential store, and contain an activation token after
  `/activate/`.
- Zero or multiple valid activation URLs fail closed.
- Store only message id, tenant, URL hash, status, and fence; never the URL.
- Mark `navigation_started` immediately before `page.goto`.
- `navigation_started`, `navigation_unknown`, and `opened` never retry.
- Never include activation URL/token in stdout, schema output, evidence,
  Telegram, or repository files.

## Sources

| Source | URL / evidence | Applied rule |
|---|---|---|
| Python URL parsing security | https://docs.python.org/3/library/urllib.parse.html#url-parsing-security | `urlsplit()` does not validate input; verify scheme, hostname, credentials, and path explicitly. |
| OWASP Unvalidated Redirects | https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html | Use an allow-list of trusted hosts rather than navigating an arbitrary email URL. |
| Amazon Builders' Library idempotency | https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/ | Record idempotency state atomically and do not duplicate uncertain side effects. |
| Real authenticated ASML email | private Gmail message `192c35b432b788d7` | Sender is `asml@myworkday.com`; subject is “Verify your candidate account”; link shape is exact tenant `/.../activate/<token>`. |

## Task 1 — RED: detection, validation, fencing

- [x] Test deterministic inbox selection and classification for real Workday
  verification shape.
- [x] Test exact known-tenant activation extraction and secret-free receipt.
- [x] Test wrong sender, wrong tenant, non-HTTPS, malformed path, and multiple
  URL rejection.
- [x] Test durable first claim, start/open transitions, and no retry after
  start/unknown/opened.
- [x] Test prompt and result-schema contract.
- [x] Run focused tests and capture expected failures.

## Task 2 — GREEN: verifier and inbox contract

- [x] Add known-tenant enumeration to the private credential module.
- [x] Implement pure Workday verification extraction.
- [x] Implement mode-0600 SQLite navigation fence.
- [x] Extend Gmail query/prefilter/classifier.
- [x] Extend inbox prompt and schema.
- [x] Run focused and full suites.

## Task 3 — GitHub and live no-mail reflection

- [x] Push, pass all CI, merge, and fast-forward canonical.
- [x] Kickstart only the existing inbox/daily launchd jobs and verify exit zero,
  integrity, and no false-positive processing of historical seen mail.
- [x] Update SSOT spec/evidence. Keep real account creation and verification E2E
  pending until the new CrowdStrike email actually arrives.

Live result: PR #1316 merged as `828c4d7b1` after all seven required checks
passed in run `30453061715`. Daily advanced 6→7 and inbox 13→15 with exit 0;
the inbox timer overlapped the manual kick and both deterministic passes found
zero new recruiting messages. The private verification DB remains absent
because no new matching Workday email arrived, while historical seen mail was
not reopened. Healthcheck reports ledger and interview-prep integrity `ok`.
