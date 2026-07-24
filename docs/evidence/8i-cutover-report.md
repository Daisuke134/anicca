# Life Manager 8i Cutover Evidence

## Result

The `life-call` production service runs from `Daisuke134/life-manager`, branch
`main`, root directory `apps/life-manager`.

| Check | Evidence |
|---|---|
| Active Railway deployment | `6806b0d4-dcdf-430f-acea-35d8a5b11212` |
| Requested commit | `a7ac84d44faac86ce00dc45b1d2ebeeb52ec9218` |
| Railway API commit readback | `a7ac84d44faac86ce00dc45b1d2ebeeb52ec9218` (`SUCCESS`, active) |
| Railway source readback | `Daisuke134/life-manager` / `apps/life-manager` / `/apps/life-manager/railway.toml` |
| Production health | HTTP `200`; `{"ok":true,"service":"life-call","ws":"/ws","build":"lm27-voicemail-v1"}` |
| Zero-downtime monitor | 358 consecutive samples; 0 non-200 responses |
| Telegram production bot | `getMe` succeeds, webhook ends in `/telegram`, real `sendMessage` succeeds |
| Telegram message ID | `217` |
| Canonical panel | Authenticated `GET /panel` returns HTTP `200` |
| Repository archive | `Daisuke134/anicca-products` API readback returns `archived: true` |

## Panel readback

The canonical authenticated panel renders the five required sections and each
production data endpoint returns HTTP `200`.

| Section | Production data evidence |
|---|---|
| `timeline` | 16 real timeline items |
| `scores` | Real four-organ score model returned |
| `ledger` | 1,000 API-cost items and the financial ledger model returned |
| `gates` | 2 real gate records |
| `settings` | Real call schedule and connection state returned |

The current page also includes `control-center`; its production endpoint returns
HTTP `200` with connection, context, control, identity, and settings models.

## Archive gate

Archiving happens only after the deployment SHA, health, Telegram, and panel
checks pass. Before archive, commit `93cc012` adds this banner at the beginning
of the old repository README:

> → Daisuke134/life-manager へ移行済み

GitHub API readback then confirms `Daisuke134/anicca-products` is archived.

## Failed attempts retained as evidence

1. Deployments `fd8b50c2-6d45-4661-8564-94ad9b18bb75`,
   `c197e414-4293-4a42-9d42-7af5e0c7b31f`, and
   `fc84aceb-f286-488e-926d-83e6ed28690c` fail before the migrated root is
   fully applied. Railway still retains the old
   `/apps/life-call/railway.toml` and `apps/life-call/**` service settings.
2. Updating `railwayConfigFile` to `/apps/life-manager/railway.toml` and
   `watchPatterns` to `apps/life-manager/**` fixes the build configuration.
3. Deployment `1c28905f-980d-4c39-bdc6-01c2e749f730` reaches the requested
   commit successfully but is superseded by an automatic current-HEAD
   deployment while the configuration update settles.
4. Production auto-deploy is temporarily paused, the requested commit is
   deployed as `6806b0d4-dcdf-430f-acea-35d8a5b11212`, and auto-deploy is
   re-enabled. API readback still shows this requested deployment as active.
5. The external health monitor records no non-200 response during any failed,
   superseded, or successful attempt.

No credential, token, key, cookie, Telegram chat ID, or personal data is stored
in this report.
