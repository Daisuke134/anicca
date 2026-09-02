# Connector Connpass submit wiring repair

## Goal

Enable the existing production Connector path to submit eligible Connpass events
when the local operator has explicitly opted in, then preserve the existing
provider readback, Google Calendar, Telegram, evidence, and dedupe contracts.

## Root cause

`skills/connector/native-pass.js` does not pass a Connpass submit permission into
`createMinimalProductionDependencies()`. The factory therefore receives its
default `false`, exposes `connpass_action_boundary`, and the runner deliberately
skips every Connpass action after sending the candidate report.

## Scope and non-goals

- Add one allowlisted shared-env opt-in, off unless its value is exactly `true`.
- Forward that value at the native production dependency boundary.
- Keep the existing manual boundary available when the opt-in is absent or off.
- Update the Connector contract/spec to describe the explicit local opt-in.
- Do not add a CLI, crawler, provider API, scheduler, browser profile, model
  decision gate, new evidence path, or second implementation.

## TDD and acceptance

1. RED: the env loader rejects the new key and native config omits the opt-in.
2. GREEN: the allowlisted value reaches the factory as a boolean; omitted and
   non-`true` values remain false.
3. Run focused native/production/runner tests, the full outbound suite, shell
   and diff checks, then build a pushed immutable release.
4. Apply only `ai.anicca.life-manager-connector-native`; read back the exact
   loaded release, hourly cadence, owner, state path, and process cleanup.
5. Run one bounded live wake. Accept an external application only when the
   existing Connpass official readback, Calendar exact-one readback, Telegram
   positive IDs, and durable `applied_bundle` all exist. Otherwise preserve the
   truthful failure/no-effect state and do not retry an unknown effect.
