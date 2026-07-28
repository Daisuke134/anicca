# AE-PUBLICATION-AUDIT-1

## Result

| Item | Result |
|---|---|
| Observed at | `2026-07-28T12:23:54Z` |
| Article | `docs/articles/how-to-make-a-financially-independent-ai-ja.md` |
| Deck | `docs/presentations/how-to-make-a-financially-independent-ai-ja.{md,pptx,pdf}` |
| SSOT | `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md` §0.4 |
| Verdict | **PASS after correction** |
| Material correction | 到達証拠はlevel 3だが、live statusはlevel 2。Franklin 1の6h proof jobは終了し、現serviceはHTTP 503 |

最初の照合では、article / deck / SSOTがFranklin 1を現在稼働中のlevel 3としていた。live readbackがこのclaimを否定したため、
3成果物を「level 3を6時間実証 / live level 2 / replacement未実装」へ修正し、再監査した。

## Claim cross-check

| Claim | Article | Deck | SSOT | Result |
|---|---:|---:|---:|---|
| title = `AIを経済的に自立させる方法` | yes | yes | yes | PASS |
| 自律と経済的自立を分離 | yes | yes | yes | PASS |
| level 3は6h proof | yes | yes | yes | PASS |
| live statusはlevel 2 | yes | yes | yes | PASS |
| level 4は未達 | yes | yes | yes | PASS |
| verified external revenue = `$0.00` | yes | yes | yes | PASS |
| live shelterは停止 | yes | yes | yes | PASS |
| SELL / WORK / CAPITALを分離 | yes | yes | yes | PASS |
| seed / self-pay / internal transferはrevenue 0 | yes | yes | yes | PASS |

機械照合は全8 claimについてarticle / deck / SSOTの`true / true / true`、failure 0だった。

## Fresh live evidence

### Franklin 1 / Nosana

| Readback | Fresh value |
|---|---|
| job | `DdUqQh8…WPS4` |
| job state | `2` |
| timeout | `21600` seconds = 6h |
| same payer running jobs | `0` |
| `/` | HTTP `503` |
| `/statement.json` | HTTP `503` |
| `/heartbeats` | HTTP `503` |
| shelter NOS | `0.75 NOS` |
| shelter SOL | `0.025764161 SOL` |

Nosana dashboard API、公開service、Solana mainnet RPCを独立に読んだ。資金補充は成立しているが、6h ceiling後に次jobを作る
replacementは成立していない。したがって、過去のheartbeat 130+、statement、self-renew receiptはlevel 3の実証証拠として保持する一方、
現在稼働中とは書かない。

### Revenue boundary

| Readback | Fresh value |
|---|---|
| Life Manager production monthly ledger | gross `$0.00` / net `$0.00` / counted rows `0` |
| x402 ledger loop | run `122` / last exit `0`; latest `recorded=0` |
| TaskMarket ledger loop | run `79` / last exit `0`; `tasks_seen=15 / pending=15 / recorded=0` |
| payout loop | run `124` / last exit `0`; `no_verified_surplus` / reserve `35 USDC` |
| PM | live loop remains separate CAPITAL accounting; it is not external SELL / WORK revenue |

production reportはwallet balanceをBase RPC、収益行をproduction `lm_agent_earnings`から読み、補完値なしで生成した。
自己支払い、bootstrap、internal transfer、PM元本はexternal revenueへ含めない。

## Publication artifact validation

| Check | Result |
|---|---|
| Article chapters | `12/12` |
| Primary-source short quotations | `3` |
| External primary-source URLs | `4/4 HTTP 200` |
| Internal relative links | all targets exist |
| Forbidden success claims | `0` |
| Secret-like patterns in article / deck source / SSOT | `0` |
| PPTX ZIP integrity | `testzip=None` |
| PPTX slides / notes | `10 / 10` |
| PDF | `10 pages`, `720 × 405.014 pt` |
| Timing | `400 seconds = 6:40` |

10枚のthumbnail gridを確認し、truth correctionを入れたslide 8とslide 10は1800 × 1013の原寸renderでも確認した。
最初のslide 10 renderでは右下page numberのcutoffを検出し、footer幅を修正して再生成した。再renderでは
cutoff / overlap / contrast defectは0だった。

## Evidence limit

このauditは、financially independent AIの完成を証明しない。証明するのは次だけである。

1. wallet、実支払、6hのMac-off cloud survival、earning rails、receipt verifier、ledgerは実証済み
2. live shelterは停止し、current operational levelは2
3. verified external revenueは`$0.00`
4. level 4、user payout、self-funded childは未達

次のbuildは`SHELTER-REPLACE-1`。6h ceiling前に次jobを作り、confidential delivery、HTTP 200、heartbeat署名を確認してから
旧jobを終了する。失敗時は旧jobを維持し、二重job上限とreserve floorを守る。
