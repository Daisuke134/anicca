# UBI E2E results — HONEST status (corrected 2026-06-18)

## TRUTH (no overclaim)
**No end-to-end test where a real human RECEIVES money in a usable form is complete.** What is
actually proven so far is ONLY: "anicca can broadcast a real USDC transfer on Base." That is NOT
"a person received basic income and can spend it / get it to their bank."

| TestID | what was ACTUALLY done | what is NOT proven (the gap) | honest status |
|---|---|---|---|
| UBI-E1 wallet | Real on-chain USDC transfer from anicca wallet (0xa3CDd4) to a **throwaway address I control** (0xF4776B, $0.20, tx 0x3d6be651, status 0x1). | A real END USER receiving to THEIR own wallet + using it. Sending to my own test address is NOT a user receiving. | on-chain SEND proven only |
| UBI-E2 email (Crossmint) | Created a Crossmint email-owned smart wallet (0x9557…, owner keiodaisuke@gmail.com) + transferred $0.50 USDC on-chain (tx 0x421f0307). | **The email owner (Dais) CANNOT yet log in and see/withdraw it** — there is NO consumer UI for it, and I did NOT verify any hosted Crossmint login works for an API-created wallet. I earlier told Dais "sign in at crossmint.com" — that was UNVERIFIED / likely wrong. = NOT a usable receive. OVERCLAIM, corrected. | money is in a wallet Dais can't yet touch |
| UBI-E3 bank/PayPay (JP) | nothing | The entire USDC(Base) → JPY → bank/PayPay path. UNVERIFIED which exchange even accepts USDC on Base + allows JPY bank withdrawal. | NOT started / UNVERIFIED |
| UBI-E3 bank (US) | nothing | USDC → USD bank. | NOT started |

## What "done" must mean (no more lies)
A path is done ONLY when a real person, on a named website, taps named buttons, and ends with money
they can SPEND (in their wallet they control, or yen/USD in their bank / PayPay) — verified by that
person seeing it. On-chain transfer alone ≠ done.

## Open research (being answered by a dedicated agent, with citations)
1. Real working USDC(Base) → JPY → MUFG/PayPay path: which JP exchange accepts USDC on the Base network for deposit AND allows JPY bank withdrawal? Exact steps, fees, minimums.
2. US/EN: USDC → USD bank, the simplest real path.
3. Crossmint email wallet: can the end user independently access + withdraw (hosted UI?), or must we build the access page?
