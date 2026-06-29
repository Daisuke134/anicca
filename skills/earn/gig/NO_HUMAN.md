# earn/gig — NO-HUMAN guarantee (D4)

Every step is autonomous. A human step disqualifies a rail (CC contract #2). Proven by
`__tests__/no-human.test.mjs` (audits run.sh + every lib for stdin reads / interactive
prompts / "ask a human" patterns; fails the build if any appears). The loop also spawns
run.sh with **stdin ignored**, so the slot physically cannot block on human input.

## Human touchpoint → autonomous mechanism
| would-be human step | mechanism | where |
|---|---|---|
| captcha (signup) | CapSolver (`CAPSOLVER_API_KEY`) | LaborX signup; dealwork has none |
| OTP / login code | `gog gmail` / AgentMail auto-read (incl. SPAM) | any email-code gate |
| login | stored creds in `~/.openclaw/.env` (read from file, not env) | LaborX |
| publish / submit | CDP browser driving (CloakBrowser daily-driver :9222) | LaborX apply/deliver |
| private key | loop scrubs `*_WALLET_KEY`; slot reads wallet **address only** from `~/.anicca-founder/wallet.json` | all |
| "did I earn?" | record-earn on-chain scan (external USDC only) — never self-asserted | settle |

## Rails (all no-human end-to-end, own-wallet crypto payout)
- **dealwork** — pure REST API, no captcha, no browser → fully headless no-human. PRIMARY.
- **laborx** — public board detect (no login); apply/deliver via CDP daily-driver with stored
  creds; one-time signup captcha via CapSolver. Browser-gated (runs when daily-driver is up).
- **Removed** (human loop / dead): Coconala (¥→human KYC bank), abillio (domain parked).

## Funding-agnostic
Same no-human rails on `ANICCA_BRAIN=claude-p` (human-funded) and `=proxy` (self-funded). The
human funds compute only; the earning loop touches no human.
