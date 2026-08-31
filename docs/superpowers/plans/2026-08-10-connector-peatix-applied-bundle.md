# Connector Peatix Applied Bundle Implementation Plan

> **For Luna:** Use Superpowers test-driven-development. Commit only the two owned minimal-evidence files.

**Goal:** Extend the existing minimal evidence chain so an exact Peatix registered readback can produce the same complete Calendar + PNG + Telegram `applied_bundle` as Luma.

**Architecture:** Keep one `completeEvidence` orchestration. Select a provider-specific event identity/URL validator and evidence store for `luma` or `peatix`, then reuse the existing screenshot hash, Calendar idempotency/readback, Telegram message/photo delivery, immutable bundle digest, and recovery-compatible file layout. No provider success is inferred inside evidence.

**Tech Stack:** Node.js CommonJS, `node:test`, existing Luma and reviewed Peatix evidence stores, gog Calendar adapter, outbound guardian.

## Ponytail gate

- Reuse the entire existing evidence orchestration; add only provider-specific validation/store selection and dynamic provider text/refs.
- Luma behavior and refs remain byte-compatible.
- Peatix accepts only `peatix-event://event/<positive-id>`, exact `https://peatix.com/event/<same-id>`, and provider state `registered`.
- Use `createPeatixEvidenceStore` under the same evidence root. Receipt must be `provider-receipt://peatix/<sha256>`.
- Calendar idempotency remains SHA-256 of exact canonical provider URL; independent post-write readback remains required.
- PNG fullPage bytes, artifact SHA, Telegram message positive ID, Telegram photo positive ID, provider receipt, and Calendar receipt must all exist before bundle write.
- Never include attendee name/email/form answer/ticket ID/browser target in the bundle or notifications.
- Do not modify native provider order, auth, Browser Harness, schedule, or live state.
- Plan size: modify two files; production target under 65 changed LOC, tests under 100 changed LOC.

### Task 1: Generalize the minimal evidence chain for Peatix

**Files:**
- Modify: `apps/mr-bot/lib/connector-minimal-evidence.js`
- Modify: `apps/mr-bot/lib/connector-minimal-evidence.test.js`

- [ ] Write RED tests for a Peatix registered candidate producing an exact provider receipt, Calendar create+readback, full-page PNG/artifact SHA, dynamic Telegram message/photo, immutable `provider:"peatix"` bundle, and no private fields.
- [ ] Add negative tests for cross-event URL, pending Peatix state, wrong receipt provider, Calendar mismatch, and nonpositive Telegram IDs; assert no bundle success.
- [ ] Preserve the existing Luma test unchanged and assert its output remains Luma.
- [ ] Run RED: `node --test apps/mr-bot/lib/connector-minimal-evidence.test.js`.
- [ ] Import/create the Peatix store, add exact provider descriptor selection, and replace hard-coded Luma strings only where provider-dependent.
- [ ] Run GREEN:

```bash
node --test \
  apps/mr-bot/lib/connector-minimal-evidence.test.js \
  apps/mr-bot/lib/peatix-evidence-store.test.js \
  apps/mr-bot/lib/luma-evidence-store.test.js \
  apps/mr-bot/lib/connector-minimal-production.test.js \
  apps/mr-bot/lib/connector-minimal-runner.test.js
```

- [ ] Run `node --check` and `git diff --check`.
- [ ] Commit `feat(connector): complete Peatix applied bundle` and push `feature/connector-native-completion`.

After Luna reports RED/GREEN, fresh Sol review verifies no partial-success path. Sol then wires the existing private identity into native config and only afterward adds Peatix to the official foreground provider order for the real E2E.
