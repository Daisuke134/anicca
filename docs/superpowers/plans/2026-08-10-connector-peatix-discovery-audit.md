# Connector Peatix Discovery Audit Implementation Plan

> **For Luna:** Use Superpowers test-driven-development. Commit only the two owned minimal-operations files.

**Goal:** Persist Peatix's existing privacy-safe five-count discovery audit in the official wake lineage before production routing is enabled.

**Architecture:** Reuse the same validated aggregate row and append-only writer already used for Luma and Connpass. Add one Peatix file and one method; do not generalize the operations module or change wake reporting.

**Tech Stack:** Node.js CommonJS, `node:test`, mode-0600 JSONL state.

## Ponytail gate

- Reuse `safeDiscoveryAudit`, `append`, `wakeId`, and `now` exactly.
- Add only `peatix-discovery-audits.jsonl` and `recordPeatixDiscoveryAudit`.
- Do not store provider URL, event ID/title, ticket ID, profile, raw error, or Calendar details.
- Do not change Luma/Connpass files, report text, external actions, schedule, or production router.
- Plan size: modify two files; production target under 10 LOC, test target under 35 LOC.

### Task 1: Add the Peatix aggregate audit sink

**Files:**
- Modify: `apps/mr-bot/lib/connector-minimal-operations.js`
- Modify: `apps/mr-bot/lib/connector-minimal-operations.test.js`

- [ ] Write a failing test that records one valid five-count Peatix row, verifies exact wake lineage/timestamp, JSONL append, mode 0600, and absence of private/provider detail fields.
- [ ] Assert invalid ordering/counts use the existing closed validation and do not append.
- [ ] Run RED: `node --test apps/mr-bot/lib/connector-minimal-operations.test.js`.
- [ ] Add the one file constant, one method using `safeDiscoveryAudit`, and one exported dependency key.
- [ ] Run GREEN plus `node --test apps/mr-bot/lib/connector-minimal-operations.test.js apps/mr-bot/lib/connector-minimal-production.test.js`.
- [ ] Run `node --check` and `git diff --check`.
- [ ] Commit `feat(connector): persist Peatix discovery audit` and push `feature/connector-native-completion`.

After Luna reports RED/GREEN, Sol verifies the diff and then enables Peatix in the production router/native provider order in a separate slice.
