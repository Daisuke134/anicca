# 13d-a — the user types, the manager hears, verifies, and answers. Live 2026-07-26.

Full E2E performed agent-side under ruling §10.0-16 (browser-driven, zero human steps), after
PR #1144 merged (23/23 + full suite exit 0; review hardening: the money-bearing write re-verifies
`row.telegram_chat_id` against the sending chat).

## The measured round trip (real chat, real production)

| actor | line | time |
|---|---|---|
| typed | 送金先を変更 | 08:26 PM |
| LM | walletアドレスを1つ送ってください（Base, USDC）。例: 0x1234…abcd これは収益の送金にだけ使います。 | 08:26 PM |
| typed | `0x6592EB8EF820aBC092e8C3474fb2042dffCCEDc7` (= `DAIS_CREATOR_ADDRESS`, the address the colony already pays Dais on — recorded data, not a guess) | 08:27 PM |
| LM | ✅ 登録しました: 0x6592…EDc7（Base）利益が出た月はここへ送金します。変更は「送金先を変更」と送信。 | 08:27 PM |

Production DB readback:
```json
{"type":"wallet","status":"usable","address":"0x6592EB8EF820aBC092e8C3474fb2042dffCCEDc7","confirmed_at":"2026-07-26T11:27:08.300Z"}
```

The confirmation quotes the value read back from the database after the compare-and-set, not the
parsed input — a write that cannot be read back replies as a failure. EIP-55 checksum verified
against the audited keccak; malformed input gets a visible, reasoned rejection.

With this, the product's full input grammar is live: taps for choices (CB-1), typed lines for
values, and every input answered visibly. 13d-b (the on-chain transfer to this address) sits on
the crypto track per ruling §10.0-17.
