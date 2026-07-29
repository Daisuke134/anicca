# Job Workday Credentials 10D Implementation Plan

> **Execution guard:** Use Superpowers test-driven-development and
> verification-before-completion. This is a local Order-10 slice; a credential
> receipt is not an application receipt.

**Goal:** When a Workday account-create surface is reached, the loop can
provision and reuse one strong private credential per Workday tenant without
printing the email or password, rotating an existing credential, or committing
secrets.

**Architecture:** A standard-library Python module derives the tenant from an
official `*.myworkdayjobs.com` URL, reads the verified application email from
the private profile, and atomically maintains a versioned mode-0600 credential
store under the private config root. The CLI emits only tenant, path, creation
state, and an email hash. Browser execution reads the private account in-process
and never copies its values into evidence or Telegram.

**Tech stack:** Python standard library (`secrets`, `json`, `os`, `pathlib`),
`unittest`, existing private profile and Workday snapshot contracts.

## Constraints

- Only official `myworkdayjobs.com` tenant hosts are accepted.
- Never accept an email on the command line; load it from the private profile.
- Never print or return an email or password in the CLI receipt.
- Existing tenant credentials are reused, never silently rotated.
- A tenant/email mismatch fails closed.
- Parent directory is mode 0700; store and temporary file are mode 0600.
- Account creation, form fill, and submit remain separate browser side effects.

## Sources

| Source | URL / evidence | Applied rule |
|---|---|---|
| Python `secrets` | https://docs.python.org/3/library/secrets.html | Use cryptographically strong randomness suitable for passwords. |
| Python `os.chmod` | https://docs.python.org/3/library/os.html#os.chmod | Enforce explicit private file modes after creation and replacement. |
| Real CrowdStrike Workday replay | `docs/evidence/job-search-loop/2026-07-29-workday-surface-10b.json` | Tenant account surface requires email, password, verification password, consent, and Create Account. |
| Authenticated Gmail history | private read-only evidence | A prior ASML Workday account belongs to another tenant; no CrowdStrike account message exists. |

## Task 1 — RED: private per-tenant contract

- [x] Test official tenant parsing and non-Workday rejection.
- [x] Test strong credential creation with 0700/0600 modes and atomic output.
- [x] Test a redacted receipt and explicit secret-free CLI stdout.
- [x] Test stable reuse without password rotation.
- [x] Test tenant/email mismatch refusal.
- [x] Run focused tests and capture the expected missing-module failure.

## Task 2 — GREEN: provisioner and loop contract

- [x] Implement deterministic validation plus cryptographically strong password
  generation.
- [x] Implement versioned atomic private-store writes and strict reads.
- [x] Implement a secret-free CLI receipt.
- [x] Update the daily prompt to call the provisioner at
  `workday_account_create` and keep form side effects outside the credential
  helper.
- [x] Run focused and full suites.

## Task 3 — Live private provisioning and GitHub

- [x] Provision the current CrowdStrike tenant in the real private config root.
- [x] Verify mode, redacted receipt, stable second-call reuse, and no repo secret.
- [ ] Push, pass all CI gates, merge, fast-forward canonical, and kickstart only
  the existing launchd jobs.
- [ ] Update SSOT spec and redacted evidence; keep Order 10 `in_progress` until
  confirmed real Ashby and Workday submissions exist.
