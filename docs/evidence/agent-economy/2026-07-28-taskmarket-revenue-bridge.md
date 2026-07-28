# TaskMarket award-to-ledger bridge live evidence

## Claim boundary

This evidence proves that the TaskMarket worker is continuously monitored and
that a completed external award can reach the Life Manager earnings ledger only
after an independent finalized Base USDC receipt check. It does **not** prove
Life Manager earned money: both owned tasks are still open and the production
run wrote zero rows.

## Production deployment

| Field | Readback |
|---|---|
| Merged change | PR `#1208`; main `36319ef15575116fd43d1661bd5a164479954acb` |
| launchd label | `ai.anicca.life-manager-taskmarket-ledger` |
| Interval | 300 seconds |
| Two consecutive runs | both exit `0`; stderr empty; launchd `runs=2` |
| Both results | `tasks_seen=2`, `pending=2`, `rejected=0`, `recorded=0`, `duplicates=0`, `transactions=[]` |
| Existing loops | daily, dev, financial-report, payout, selfbuild, and x402-ledger all remained loaded |

The installer adds a separate label and contains no `bootout`, `unload`, or
`kickstart -k`. The boot script resolves the recorder beside itself, so it does
not depend on the nonexistent historical path `~/anicca/apps/life-manager`.

## Award contract

The bridge accepts a row only when all of these facts agree:

| Boundary | Required evidence |
|---|---|
| Marketplace | task is `completed`, is not `selfAward`, and lists the same award in its readback |
| Ownership | awarded worker is the dedicated worker; requester is outside every known self wallet |
| Amount | `workerPayment + platformFee = grossAmount`; the exact worker payment is used |
| Chain | Base chain ID `8453`, successful receipt, and receipt block at or below the `finalized` head |
| Asset transfer | exactly one native Base USDC Transfer from a non-self sender to the worker for the exact `workerPayment` |
| Ledger | stable task+tx idempotency key; `financial_external_income`; source `taskmarket_work` |

The cent ledger never rounds revenue upward. For example, `2.312500 USDC`
becomes `231` cents plus `2,500` excluded atomic units in metadata.

## Independent real-settlement replay

A public completed TaskMarket award was used only as an external verifier
fixture; its revenue was captured in memory and was **not** written to Life
Manager's database.

| Field | Readback |
|---|---|
| Task | `0x7b7392ea5bd137efda1c9125529425ebda319d7c3652b34bcf6a508c4122c1c5` |
| Worker payment | `925000` USDC atomic units |
| Settlement tx | `0xb919c2edc93d0e1c49ac07da0d94607b3a599d4adfc4d87d6fc140db4d8bb35f` |
| Receipt | Base block `49163158`, status `1`, finalized |
| Verifier result | one in-memory `taskmarket_work` row for `92` cents; rejected `0` |
| Database side effect | zero |

## Owned live work

| Work | Current live readback |
|---|---|
| Spider memory-game bounty | task `0xd871…f486`; `open`; award count `0`; submission count `20` |
| TaskMarket GTM pitch | task `0x37f6…7c7d`; `open`; pitch count `39`; owned pitch `1712f0fd-5892-478a-8dc6-2cac519257c8` is `pending`; reward `13 USDC` if selected and accepted |
| Withdrawal destination | `0x477eee969ccfdc0e959f38ce8b83e372fc0262ad`; USDC EIP-712 domain chain ID `8453` |

The 0.001 USDC pitch fee is acquisition cost, not revenue. A submission,
selection, elapsed deadline, or API claim cannot advance 13c. Only an awarded
owned task plus the independently verified settlement can do so.

## Verification

| Check | Result |
|---|---|
| Focused TaskMarket TDD suite | `11/11` pass |
| Related earnings regression suite | `85/85` pass |
| Full Life Manager test | `659/660`; only the pre-existing host-state assertion expecting the loaded dev loop to be absent failed |
| Shell/plist/diff | `bash -n`, `plutil -lint`, and `git diff --check` pass |
| Repository secret scan | TruffleHog filesystem + history pass |

Primary protocol source:
[Daydreams TaskMarket documentation](https://docs-market.daydreams.systems/llms-full.txt).
