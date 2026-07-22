# Sprint 2 corrective RED/GREEN evidence

Status: product behavior locally GREEN; fresh independent reviews and changed-module coverage gate remain required. No PASS verdict is authored here. FIND beads remain open.

## RED

- Commit: `5f8db7f1353b163c267eb415c3c7e12456f6195d`
- Command: `node --test lib/panel-corrective-red.test.js`
- Result: exit 1 with deterministic assertions mapped to FIND-001 through FIND-010.

## GREEN

- Focused panel suite: 39 tests, 39 pass, 0 fail.
- Full `npm test`: exit 0.
- `npm run eval`: Calendar 21/21 plus Late 12/12 = 33/33.
- `npm run smoke:panel-api`: 5/5 HTTP 200.
- `npm run smoke:panel-ui`: 6/6 semantic sections/controls.
- `git diff --check`: exit 0.
- Local fixture work only: provider/OAuth/send/production/L3 calls = 0.

## Coverage truth

`node --test --experimental-test-coverage lib/panel-corrective-red.test.js lib/panel-control-center.test.js lib/panel-api.test.js lib/panel-ui.test.js` exits 0. `panel-api.js` line coverage is 95.59% and `user-command.js` is 99.40%; `scheduler.js` is 41.94% line / 36.11% function. Therefore the requested >=90% changed-module coverage gate is not satisfied and no completion/PASS claim is made.

## Finding mapping

- FIND-001: `unsupported delegation is honest...`; `runtime OFF blocks call/DAILY/notification...`
- FIND-002: `pending and concurrent duplicate executes one mutation`
- FIND-003: `every API scope is rebound to current uid and chat`
- FIND-004: `receipts bind uid chat_id and idempotency key`
- FIND-005: `calendar selection rejects foreign, missing identity, and ambiguity`
- FIND-006: `disconnect verifies same account and rolls back exact account`
- FIND-007: `OAuth callback requires exact owned ACTIVE provider readback`
- FIND-008: `connection model distinguishes connect reconnect disconnect`
- FIND-009: `request body stops retaining bytes and settles once after 32 KiB`
- FIND-010: `corrective evidence remains pending fresh review`
