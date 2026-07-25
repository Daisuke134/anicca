# CORE-8f — context / onboarding / discovery, production L3

Run date: 2026-07-25 (JST). Production service `life-call`, Railway environment `production`.

## What the earlier record got wrong

The recorded blocker said typed `source=telegram_live_location` rows could not be persisted
(`live_location_unlock / poll_timeout`). Production contradicts that: the row exists with
`telegram_message_id=199` and its `observed_at` advances roughly every 20 seconds. What actually failed
was the narrower case of a location the agent injected over MTProto. 8e's L3 reached a late decision from
this same real row, so the location leg was never the open question here.

## Evidence

| Property | Measured |
|---|---|
| An unlocked gate is never asked again | Against real production rows the locked set is `["payout"]` alone — the location gate drops out of selection because the live location is fresh. With `last_discovery_gate=location`, the rotation selects `payout` |
| Real Telegram announcement | Delivered as message `246`, gate `payout` |
| DB provenance | `last_discovery_at=2026-07-25T03:27:14.263Z`, `last_discovery_gate=payout` |
| The same question is not repeated | A second run reports `isDiscoveryDue=false` — the seven-day throttle holds |
| Real callback through production | The user pressed the button; the production webhook recorded `[discovery] callback action=register gate=payout` |
| Zero forbidden-topic utterances | No standalone `出た？ / まだ？` prompt exists in shipped source. The single i18n hit is discovery copy explaining that sharing a location removes that check; the rule matches only a whole-message prompt |
| Eval | Context/onboarding/discovery eval 12/12 (100%) |

## Gap found and closed

A discovery answer left no trace. Nothing recorded which gate the user replied to, so the press above
would have been invisible and the unlocked-gate rotation could not be proven end to end. The webhook now
names the action and the gate, and deliberately logs no chat or user identifier.

## Known defect this run surfaced — owned by 13b

Pressing "register" on the payout announcement acknowledges the tap and then does nothing: the user sees
a bare receipt and no reply. The intended shape is a round trip — the press should lead to a single closed
question, the user answers, and the destination is stored. That flow is row 13b, which is not built, so
today the announcement has no landing point. Verified: `payout_destination` is still null after the press.
This is recorded rather than patched here, because inventing interim copy would pre-empt the §9.11
FINANCIAL wording that 13b owns.

## Verification at the merged commit

`npm test` 738 pass / 0 fail · `npm run eval` 7 suites at 100% · `npm run eval:panel-privacy` PASS.

Canonical main and Railway production both at `2c4c5a60` (deployment status SUCCESS).
