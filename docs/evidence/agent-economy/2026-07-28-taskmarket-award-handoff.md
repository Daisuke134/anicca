# TaskMarket award → Life Manager wallet handoff

## Outcome

TaskMarket の verified external award が Life Manager earnings ledger に現れた後、worker wallet の Base USDC を登録済み Life Manager agent wallet へ自動移送する経路を production 化した。未受賞時は wallet balance 読取前に no-op し、外部 mutation はゼロである。

| Gate | Production evidence |
|---|---|
| Award ownership | recorder の `recorded + duplicates > 0`、owned worker、award settlement tx evidence を必須化 |
| Destination preflight | `GET https://api.taskmarket.dev/api/wallet/withdrawal-address?address=<worker>` の登録先が Life Manager wallet と完全一致しない限り停止 |
| Exact amount | `taskmarket wallet balance` の `balanceBaseUnits` を整数のまま6桁USDCへ変換し、`taskmarket withdraw <exact>` を `execFile` argv で実行 |
| Chain proof | chain ID `8453`、成功receipt、worker→Life Manager wallet の一致する native USDC `Transfer` がちょうど1件、かつ finalized block 到達を必須化 |
| Retry | ledger duplicate + positive worker balance は再試行、worker balance 0 は `worker_balance_zero` no-op |
| Revenue boundary | worker→Life Manager wallet は内部移送であり、新しい external revenue rowとして記帳しない |

## TDD / regression

| Verification | Result |
|---|---|
| RED | module未実装とlaunchd未配線で focused test が失敗 |
| GREEN | handoff / launchd focused tests `10/10` PASS |
| payout + TaskMarket focused regression | `26/26` PASS |
| Life Manager full suite | `659/659` PASS |
| shellcheck | `taskmarket-work-ledger-boot.sh` PASS |
| PR | [#1216](https://github.com/Daisuke134/life-manager/pull/1216), production commit `29b1968c588911ae914a07df6eab4eaa42c6a380` |

## Production no-award proof

既存 `ai.anicca.life-manager-taskmarket-ledger` を `launchctl kickstart` で発火した。他の loop は unload/bootout していない。

```json
{"observed_at":"2026-07-28T07:45:13.906Z","ok":true,"worker_address":"0xd7db94062afec8a86f70250b931c77619acf8937","tasks_seen":10,"pending":10,"rejected":0,"recorded":0,"duplicates":0,"transactions":[]}
{"ok":true,"status":"noop","reason":"no_verified_award","verified_awards":0}
```

発火前後の worker balance は両方 `balanceBaseUnits=1000 / balanceUsdc=0.001000`。launchd readback は `runs=26 / last exit code=0`。したがって現在の external revenue は引き続き `$0.00` であり、13c doneとはしない。

## Upstream behavior measured

| Source | Measured contract |
|---|---|
| TaskMarket CLI `@lucid-agents/taskmarket@1.7.1` installed source | `withdraw <amount>` は登録済み withdrawal address をAPIから取得し、USDC `TransferWithAuthorization` を署名して `/api/wallet/withdraw` へ送る |
| TaskMarket API live readback | workerの登録先は Life Manager wallet、USDC domainは chain `8453` / native Base USDC |

