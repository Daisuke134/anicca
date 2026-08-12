# Connector Item 23B — crash reporter narrow configuration

## Goal

Keep the last-resort process-crash Telegram report available when the full Connector startup identity/configuration is precisely what failed.

## Ponytail full gate and size

- Exact three files: `skills/connector/native-pass.js`, `skills/connector/minimal-crash-report.js`, and the existing crash test. Production about 12–25 LOC; test about 3–12 LOC.
- Extract one narrow native report configuration from the existing shared-env loader, owner-token-derived wake ID, and existing strict Telegram target resolver. Full production config composes it and retains every current email, legal-name, Kana profile, keyring, Calendar, and provider validation.
- Crash reporter consumes only narrow `wakeId` and `telegramTarget`. Add no module, fallback recipient, inline secret, browser action, restart, retry, or second sender.

## TDD and verification

1. RED is `minimal-crash-report.test.js` failing in `requiredEmail` before the injected report operation.
2. Tighten the fixture to Telegram target only; it must report `circuit_open/process_crash/0` with positive ID while browser/Calendar/submit remain zero.
3. Native entrypoint tests must prove full production config still fails closed without its current private identity inputs.
4. Run focused crash/native tests, then the full Connector suite. Fresh Sol review must verify the helper cannot weaken ordinary wake configuration.
