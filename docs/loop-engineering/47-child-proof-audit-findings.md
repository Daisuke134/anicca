# child-proof 監査の発見と適用（2026-07-14）

対象: 我々の loop harness が「smart model 前提」だった箇所。監査 = child-proof-audit subagent (sonnet)、
実 ledger/log 証拠付き。原則の正本 = [[45-weak-model-strong-harness]]。適用 commit = anicca `4270e059`。

## 発見（実証拠つき）

| gap | 実証拠 | 適用した fix |
|---|---|---|
| prompt/registry が x402_sell の「商品発明」を招く（4箇所 + registry summary） | GLM-4.7 が `{"sell":"Crypto market intelligence report…","price":"$0.50"}` を発明 → run.sh は args を一切読まず握り潰し → model に「$0.50 で売った」という**偽の自己認識**が残る | 全文面を「menu は FIXED、正しい呼び方は空 args、仕事は demand だけ」に書き換え + brain の shapeSpec に正準 few-shot（空 args 呼び出しそのもの）を注入 |
| skill 同期が「プロセス起動時1回」 | guard fix と report shim が健全 loop に数時間届かず（クラッシュ待ちの無限大遅延） | `runtime/self-update-skills.sh`(rsync のみ・0.2s) を loop 内 10分 `setInterval`+`unref()` で常時実行。伝播上限 = ~10分 |
| registry の entrypoint と実ディスパッチの契約不一致 | report slot が 25+ wake 連続 skill_missing（model 唯一の SOS チャネル沈黙） | run.sh shim で応急済（80f99354）。恒久 = 「live slot は必ず run.sh を持つ」lint → backlog |

## 実装の学び（3回失敗して正解に到達）

per-wake 同期の配置で2回失敗: ①wake 冒頭 await（git fetch 込み）→ ネットワーク+秒単位遅延で
integration テスト 17→22 fail ②fire-and-forget でも wake path 内は flake（→25）。
③正解 = **wake path の外**の `setInterval(...).unref()` — テスト(短命プロセス)では一度も発火せず、
本番では 10分毎。full suite 16 fail = baseline 完全一致で回帰ゼロを確認。
一般法則: **常駐 loop への付帯処理は hot path に足さず、独立タイマーに置く**。

## 効果の検証方法（次の実測ポイント）

- claude-p / franklin2 の次の x402_sell wake で args が `{}` になるか（ledger 実測）
- 偽自己認識の消滅: wake note に「$X で売った」系の幻覚が出なくなるか
