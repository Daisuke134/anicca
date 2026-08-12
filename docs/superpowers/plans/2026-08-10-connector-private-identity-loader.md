# Connector Private Identity Loader Implementation Plan

> **For Luna:** Use Superpowers test-driven-development. Commit only the loader and its focused test.

**Goal:** Allow the official Connector env loader to read the already-existing private legal-name value needed for the Peatix attendee profile, without exposing any additional env key.

**Architecture:** Extend the closed allowlist in `load-connector-env.js` by one existing key, `DAIS_LEGAL_NAME_ROMAJI`. Test the loader directly with a mode-0600 temporary env. Do not copy the value into repo/state or print it.

**Tech Stack:** Node.js CommonJS, `node:test`.

## Ponytail gate

- Add exactly one allowlisted key; reuse the existing parser/validation.
- Unknown keys, Telegram token, cookies, passwords beyond the already allowed keyring, and arbitrary env remain excluded.
- Do not modify the real private env, native provider order, production config, browser, evidence, or schedule.
- Plan size: production 1 LOC, focused test under 45 LOC.

### Task 1: Allow the existing private attendee name

**Files:**
- Modify: `skills/connector/lib/load-connector-env.js`
- Create: `skills/connector/test/load-connector-env.test.js`

- [ ] Write RED asserting `DAIS_LEGAL_NAME_ROMAJI` is returned with existing `GOG_ACCOUNT`, while an unknown secret key is absent.
- [ ] Assert blank/control-character allowed values fail closed and file size/type rules remain.
- [ ] Run RED: `node --test skills/connector/test/load-connector-env.test.js`.
- [ ] Add the one allowlist entry.
- [ ] Run GREEN: `node --test skills/connector/test/load-connector-env.test.js skills/connector/test/native-entrypoint.test.js`.
- [ ] Run `node --check` and `git diff --check`.
- [ ] Commit `feat(connector): allow private attendee identity` and push `feature/connector-native-completion`.

After Luna reports GREEN, Sol reviews the allowlist. The next separate slice constructs the in-memory Peatix profile and adds Peatix to the official foreground provider order.
