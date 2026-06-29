# earn/gig — NO-HUMAN guarantee (D4)

Every step is autonomous. A human step disqualifies a rail (CC contract #2). Proven by
`__tests__/no-human.test.mjs` (audits run.sh + every lib for stdin reads / interactive
prompts / "ask a human" patterns; fails the build if any appears). The loop also spawns
run.sh with **stdin ignored**, so the slot physically cannot block on human input.

## Human touchpoint → autonomous mechanism
| would-be human step | mechanism | where |
|---|---|---|
| captcha | CapSolver (`CAPSOLVER_API_KEY`) | (dealwork has none; for future browser rails) |
| OTP / login code | `gog gmail` / AgentMail auto-read (incl. SPAM) | any email-code gate |
| login | stored creds in `~/.openclaw/.env` (read from file) | future browser rails |
| publish / submit | CDP browser (daily-driver :9222) | future browser rails |
| private key | loop scrubs `*_WALLET_KEY`; slot reads wallet **address only** from `~/.anicca-founder/wallet.json` | all |
| "did I earn?" | record-earn on-chain scan (external USDC only) — never self-asserted | settle |

## Rails (all no-human end-to-end, own-wallet crypto payout)
- **dealwork** — pure REST API, no captcha, no browser → fully headless no-human. PRIMARY.
- **laborx** — NOT yet a live rail: detection + apply/deliver (CDP daily-driver) not written, so it is
  NOT offered by can_run (avoids a pretended-live rail). Re-add when its no-human apply/deliver code lands.
- **Removed** (human loop / dead): Coconala (¥→human KYC bank), abillio (domain parked).

## Funding-agnostic
Same no-human rails on `ANICCA_BRAIN=claude-p` (human-funded) and `=proxy` (self-funded). The
human funds compute only; the earning loop touches no human.
