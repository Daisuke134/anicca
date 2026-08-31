# Connector Peatix Native Foreground Wiring Plan

> **For Luna:** Use Superpowers test-driven-development. Commit only native-pass and its entrypoint test.

**Goal:** Supply the reviewed Peatix workflow with the existing private attendee identity and add Peatix as the third provider in the official bounded foreground wake.

**Architecture:** `productionConfig` builds one frozen in-memory attendee profile from allowlisted `DAIS_LEGAL_NAME_ROMAJI` and `GOG_ACCOUNT`, with explicit organizer-privacy acceptance required by the autonomous event-application contract. `DEFAULT_PROVIDERS` becomes `Luma → Connpass → Peatix`. No schedule is loaded; execution still occurs only through the existing official foreground entrypoint.

**Tech Stack:** Node.js CommonJS, `node:test`, existing native-pass config.

## Ponytail gate

- Reuse `productionConfig`, `requiredText`, the shared env loader, and existing minimal runner input.
- Add no profile file, Keychain read, browser code, retry, registry promotion, schedule, or new module.
- The profile exists only in the dependency-factory input; it never enters wake settings, action history, audit, report, cache, or bundle.
- Fail closed before dependency creation if name is missing/invalid or account is not a bounded email-shaped value.
- Provider order is exactly `luma`, `connpass`, `peatix`; no later provider is added in this slice.
- Plan size: modify two files; production under 20 changed LOC, tests under 55 changed LOC.

### Task 1: Enable Peatix in the official foreground pass

**Files:**
- Modify: `skills/connector/native-pass.js`
- Modify: `skills/connector/test/native-entrypoint.test.js`

- [ ] Write RED asserting exact three-provider order and factory input `peatixAttendeeProfile={name,email,accept_organizer_privacy:true}` from fixture env.
- [ ] Assert the profile is frozen, absent from wake settings/serialized provider input, and missing name/malformed account fail before `createDependencies`.
- [ ] Preserve existing Telegram owner resolution and foreground executable tests.
- [ ] Run RED: `node --test skills/connector/test/native-entrypoint.test.js`.
- [ ] Add exact email validation, construct the frozen profile, and change only the default provider array.
- [ ] Run GREEN:

```bash
node --test \
  skills/connector/test/load-connector-env.test.js \
  skills/connector/test/native-entrypoint.test.js \
  apps/mr-bot/lib/connector-minimal-production.test.js \
  apps/mr-bot/lib/connector-minimal-runner.test.js \
  apps/mr-bot/lib/connector-minimal-evidence.test.js
```

- [ ] Run `node --check`, `bash -n skills/connector/run.sh`, and `git diff --check`.
- [ ] Commit `feat(connector): enable Peatix foreground provider` and push `feature/connector-native-completion`.

After Luna reports GREEN, fresh Sol review verifies private-value boundaries. Sol then closes the diagnostic Peatix tab, runs `skills/connector/run.sh` through the official foreground path with scheduling still unloaded, and verifies the real provider readback, Calendar event, PNG/SHA, Telegram IDs, bundle, target cleanup, and no duplicate Submit.
