# O1C-24 YC Daily-driver Migration Design

## Objective

Move every active or compatibility YC browser entry from the deprecated isolated Chrome `:9223` path to the existing CloakBrowser daily-driver at `http://127.0.0.1:9222`, without stopping the unrelated `gig-daily-driver` process that owns `:9223`, filling any form, saving any YC answer, or submitting an application.

## Verified starting state

- The repository-owned funder route manifest already binds `yc-application` to `browser-profile://cloakbrowser/daily-driver`, `http://127.0.0.1:9222`, one shared context, and `connect_over_cdp`.
- The installed successor `~/.openclaw/skills/apply-to-funder/scripts/lib/form_filler.sh` rejects every `BU_CDP_URL` except exact loopback `:9222`, refuses to launch a replacement browser, and requires persisted submission-day and asset-freshness gates before form access.
- The installed deprecated `apply-to-yc/scripts/apply.sh` still defaults to `:9223`, auto-launches a separate Google Chrome profile, composes stale answers, writes fields, uploads files, saves, and can submit without the successor gates.
- `apply-to-yc/SKILL.md` still advertises that unsafe path as a working YC fallback.
- OpenClaw's live cron inventory reports `accelerator-application-monthly-1777948324077` disabled, while the disk store says enabled and its successor command omits `--funder yc-w26`. A restart could therefore revive an ambiguous invocation unless the durable store is reconciled.
- Live `:9222` is CloakBrowser profile `~/.cloak/profiles/daily-driver`. Live `:9223` is CloakBrowser profile `~/.cloak/profiles/gig-daily-driver`; it is not owned by YC and must remain running.

## Alternatives

### A. Change the old script's port only

Rejected. This would preserve duplicate form logic, stale answer generation, direct login, direct save/submit, browser lifecycle ownership, and gate bypass. A transport literal change would not migrate the YC operation to the repository-owned provider.

### B. Delete the old skill completely

Rejected. It removes the unsafe code, but old manual or agent invocations would fail as missing files with no deterministic successor route. A bounded compatibility seam is safer during retirement.

### C. Versioned delegating tombstone plus closed migration receipt

Selected. Check in the exact legacy skill tombstone and directly executed POSIX launcher as deployable runtime assets. The launcher owns no browser or YC form logic: it accepts the old zero-argument invocation, rejects legacy content overrides and any endpoint other than exact `:9222`, then hands off to `apply-to-funder/scripts/run.sh --funder yc-w26` with shell-startup overrides removed. Direct execution prevents caller `BASH_ENV` from running before its gates. Existing `MODE` and `DRY_RUN` semantics pass through to the successor; all live access remains subject to the successor's persisted gates.

## Architecture

```text
legacy apply-to-yc invocation
          |
          v
checked-in POSIX compatibility launcher
  - exact :9222 only
  - no DRAFT_ID/video overrides
  - no browser launch/form logic
          |
          v
apply-to-funder --funder yc-w26
          |
          +--> repository YC provider knowledge
          +--> submission-day + freshness gates
          +--> existing CloakBrowser daily-driver :9222
```

The checked-in migration contract validates the complete artifact set rather than trusting prose. It binds the repository route manifest, YC provider manifest, legacy shim, tombstone skill document, successor runtime files, live port ownership observations, cron observation, backup inventory, operation counts, and content digests into a privacy-minimal receipt. Its public SHA-256 digest proves deterministic structure and accidental-tamper detection, not hostile-source authenticity: the evidence therefore records the same-run direct readbacks separately, and does not present `validateYcBrowserRouteMigrationReceiptStructure` as a signature or HMAC verifier.

## Components

### Checked-in compatibility assets

- `apps/life-manager/runtime-assets/apply-to-yc/SKILL.md` is a tombstone that names only the successor and the migration boundary. It does not advertise direct browser driving, field filling, saving, or submitting.
- `apps/life-manager/runtime-assets/apply-to-yc/scripts/apply.sh` is the only retained executable compatibility entry. It is invoked directly, refuses caller skill-root substitution, and removes `BASH_ENV`/`ENV` before the fixed successor Bash handoff. It never sources credentials, generates answers, launches Chrome, navigates YC, or writes state itself.
- The retired `fill.js` and `progress.js` are removed from the active installed skill after an exact recovery archive is made. They are not copied into the public repository because they contain stale operational knowledge already ported and verified in O1C-21.

### Deterministic migration contract

`apps/life-manager/lib/yc-browser-route-migration.js` provides:

- a closed manifest validator for the one successor route and one compatibility shim;
- content-addressed artifact observations with byte counts and SHA-256;
- exact live owner observations for `:9222` and `:9223`, without cookie, page-body, credential, or websocket-token persistence;
- exact cron identity, disabled durable state, and successor target arguments;
- zero YC navigation/write/save/submit effect enforcement;
- a stable receipt digest and recursive freezing.

It performs fixed-format integrity, routing, lifecycle, and bookkeeping validation only. It makes no semantic decision about application answers, company facts, browser page meaning, or whether submission should occur.

### Runtime deployment

The installed legacy directory is backed up to a content-addressed, owner-only recovery directory under `~/.openclaw/recovery/apply-to-yc/`, outside every active skill subtree, before mutation. Only `SKILL.md` and `scripts/apply.sh` are replaced; `scripts/fill.js` and `scripts/progress.js` are retired from the active directory. OpenClaw cron ID `accelerator-application-monthly-1777948324077` is disabled through the OpenClaw CLI and verified both through the live CLI readback and durable JSON store. The unrelated `:9223` process is observed before and after and is never signalled.

## Contracts and failure behavior

- Exact endpoint: `http://127.0.0.1:9222`; query, credentials, alternate host, alternate scheme, and alternate port fail before successor execution.
- Exact successor: `$HOME/.openclaw/skills/apply-to-funder/scripts/run.sh --funder yc-w26`.
- Legacy `DRAFT_ID`, `FOUNDER_VIDEO`, and `DEMO_VIDEO` overrides fail closed because those values belong to the current provider/application-kit contract.
- Unknown positional arguments fail closed.
- Missing or non-executable successor fails closed.
- `DRY_RUN=true` is preserved and proves routing without browser access.
- Default live mode may reach the successor only; without current persisted gates it must fail before browser access. This design does not create or weaken those gates.
- The shared browser process is never closed. The `gig-daily-driver :9223` process is not modified.
- Any artifact digest, runtime owner, cron identity/state, effect count, or route drift from the closed receipt contract invalidates its structural validation. Authenticity of the observed values comes from the documented direct readbacks and Git history, not the self-digest alone.

## Verification and evidence

1. TDD executes the real shim against a temporary fake successor and verifies exact argv/environment, endpoint refusal, legacy-override refusal, missing-successor refusal, and no local state writes.
2. Contract tests reject artifact substitution, route/provider drift, cron re-enable, missing `--funder yc-w26`, owner/profile drift, non-zero browser/navigation/write/save/submit effects, stale observations, unknown fields, and forged receipt digests.
3. Deploy the exact checked-in assets after creating and hashing a recovery archive; retire the two obsolete JS helpers.
4. Run the deployed shim with `DRY_RUN=true` and a controlled successor probe first, then run the actual successor dry run. Require that no browser operation occurs and no YC page changes.
5. Read live `:9222` through an owned temporary page only to confirm the authenticated YC home route, then close only that page. Record sanitized origin/status evidence, not page bodies, cookies, headers, application answers, or websocket IDs.
6. Record both browser PIDs/profile roots before and after; require the same `:9223` PID remains live.
7. Run focused, outbound, runtime-up, full Life Manager tests, shell/Node syntax checks, external readback, independent review, and `git diff --check`.

## Scope boundary

O1C-24 completes transport ownership and legacy route retirement only. It does not claim O1C-25 company/founder/video/demo/progress preview, O1C-26 submission/confirmation, or O1C-27 reply/interview tracking. No YC field, file input, save control, or submit control is exercised in this item.

## Self-review and approval

- Placeholder scan: no TBD, TODO, or unresolved choice remains.
- Consistency: the shim, successor, cron, live-owner, backup, and effect contracts use the same exact identifiers and endpoints.
- Scope: one bounded browser-route migration; no form-content or submission work is included.
- Ambiguity: `:9223` is explicitly retained for its non-YC owner, while every YC entry is routed to exact `:9222`.
- Approval: Dais explicitly requested sequential execution with no human in the loop; the agent therefore approved this bounded design on 2026-08-02 and proceeded without a human review pause.
