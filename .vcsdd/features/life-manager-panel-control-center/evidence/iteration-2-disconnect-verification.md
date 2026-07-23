# Iteration 2 Calendar disconnect verification

Status: builder evidence; fresh artifact-only adversarial review remains required.

## Contract correction

Iteration 1 explicitly omitted connector disconnect from typed commands and had no grammar, native control, or criteria for it. Iteration 2 corrects this against canonical root §9.9.

- Source: [Composio ConnectedAccounts SDK](https://github.com/ComposioHQ/composio/blob/next/ts/packages/core/src/models/ConnectedAccounts.ts) / core quote: “Disable a connected account” and `updateStatus(nanoid, { enabled: false }, requestOptions)`.
- Source: [Composio migration guide](https://github.com/ComposioHQ/composio/blob/next/docs/content/docs/migration-guide/new-sdk.mdx) / core quote: disable and enable map to `PATCH /api/v3/connected_accounts/{nanoId}/status`.
- Source: [Composio ConnectedAccounts SDK](https://github.com/ComposioHQ/composio/blob/next/ts/packages/core/src/models/ConnectedAccounts.ts) / core quote for rejected alternative: delete “cannot be undone and will revoke any access tokens”.

## RED

Command: `node --test lib/panel-control-center.test.js lib/panel-ui.test.js`

Observed before implementation: the new disconnect grammar/allowlist/service and native UI assertions failed; existing PANEL-0 regression assertions continued to pass. Full raw runner output remains private in the local RTK tee log because rendered HTML is intentionally noisy.

## GREEN

- Focused: `node --test lib/panel-control-center.test.js lib/panel-ui.test.js lib/panel-api.test.js lib/panel-auth.test.js` → fail 0.
- Full: `npm test` → fail 0.
- Eval: `npm run eval` → Calendar 21/21; Late 12/12.
- API fixture: `npm run smoke:panel-api` → 5/5 endpoints HTTP 200.
- UI fixture: `npm run smoke:panel-ui` → 6/6 sections; semantic controls wired.
- Coverage, new command layer: 98.78% lines / 93.75% functions. `panel-ui.js`: 100% / 100%. Newly added Calendar provider lifecycle functions and changed command-handler paths are all exercised by fixture tests; aggregate `panel-api.js` is 90.89% lines but 61.11% functions because unchanged legacy endpoint callbacks share the module.
- `git diff --check` → clean.
- Added-line scan found no live secret. Phone/chat values are synthetic fixtures only.

No external provider disable/enable/delete was executed. The only production probe facts used are the private safe facts already captured; no second production `/panel` probe ran.
