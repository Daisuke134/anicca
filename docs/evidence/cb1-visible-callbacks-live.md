# CB-1 — a real tap now leaves a visible mark, proven by the user's own thumb

Ruling §10.0-15: every inline-button tap must produce a durable visible response. Implementation
merged as PR #1139 (877/877 tests, review finding fixed: marking is idempotent), deployed to
Railway on 2026-07-26.

## Production proof

The best E2E arrived unprompted: after the deploy, Dais himself tapped ［あとで］ on the payout
question from his phone. Readback from his real chat:

```
収益の送金先を1つだけ教えてください。これ以外の個人情報は不要です。
［銀行口座を登録］［walletアドレスを登録］［あとで］

→ あとで                                            02:17 PM
```

- the chosen label is appended to the original message (`→ あとで`),
- the inline keyboard is gone (`reply-markup-button` count on that bubble: 0),
- and the persisted destination is untouched: production readback still
  `{"type":"wallet","status":"awaiting_details","answered_at":"2026-07-26T05:18:30.952Z"}` —
  ［あとで］ visibly answers without overwriting an earlier real answer, exactly the honest-gate
  behavior 13b pinned.

Before this change the same tap produced a 0.5-second toast and nothing else — the exact
"nothing happens" Dais reported. The contract now covers ask (オンライン/対面, yes/no), payout
(bank/wallet/later, re-tap → alreadyRegistered reply), and discovery, with cross-tenant and
replayed callbacks pinned by negative tests to mutate nothing.
