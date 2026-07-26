# 13b — the payout question's real round trip, closed 2026-07-26

Done condition: one real registration round trip over real Telegram, plus the real DB row.

## The chain, each link a readback

| step | evidence |
|---|---|
| discovery announcement | the 2026-07-25 weekly message with ［登録する］ existed in the user's real chat (screenshot in session) |
| tap ［登録する］ | performed in the user's own Telegram Web session (Dais authorized driving the browser in chat: "I can go to browser and tap too … no human in loop"), via the daily-driver CDP browser |
| question delivered | the §9.11 FINANCIAL copy arrived verbatim at 02:17 PM JST: 「収益の送金先を1つだけ教えてください。これ以外の個人情報は不要です。」with the three buttons — this transit proves the webhook repair (INC-3) end to end, since the callback had to reach the server to trigger the send |
| tap ［walletアドレスを登録］ | rail choice is spec-derived, not guessed: §9.8 rules fiat closed in Japan (Stripe Link JP unavailable) and the crypto rail operative — wallet is the only rail that can pay today |
| DB row | production readback: `payout_destination = {"type":"wallet","status":"awaiting_details","answered_at":"2026-07-26T05:18:30.952Z"}` on uid `lm_784ad279…` |

## What the row honestly is, and is not

`awaiting_details` is load-bearing: 13b records which rail the user chose, and
`isPayoutDestinationUsable()` returns false for it by design — nothing downstream may mistake "they
told us the rail" for "we know where to send money". Collecting the actual wallet address is 13d's
first step, gated by its own closed question.

## Incidental finding

A second closed question (calendar interpreter's オンライン/対面 for a recurring day-job event) was
pending in the same chat. Left untouched — its answer is the user's private information that no spec
derives, exactly the class an agent must not guess.
