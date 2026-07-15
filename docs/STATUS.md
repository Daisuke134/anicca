# Anicca x402 稼ぎ — 現状（正本ファイル。memory でなくコレを読む）

更新: 2026-07-15。数値は on-chain 実測。盛らない。$0 は $0。

## loop は3つだけ（automaton は閉鎖済み）

「founder」という loop は**存在しない**。claude-p の HOME フォルダ名が `.anicca-founder` なので
Fable が誤って「founder」と呼んだだけ。founder = claude-p = agent-economy-loop、全部同じ1つ。

| 呼び名 | loop 名(launchd) | HOME フォルダ | x402 wallet | brain |
|---|---|---|---|---|
| **claude-p** | ai.anicca.agent-economy-loop | /Users/anicca/.anicca-founder | 0x810f6d61…29c5 | Claude sub |
| **franklin1** | ai.anicca.franklin-loop | /Users/anicca/.blockrun | 0x3EcCAD24…8749 | free/glm-4.7 |
| **franklin2** | ai.anicca.franklin2-loop | /Users/anicca/.franklin2-home/.blockrun | 0xe7747Fd8…7ce9 | free/glm-4.7 |

- 全部 `~/anicca/runtime/loop/index.mjs` を各自の設定(plist の env)で回す。10分毎に自動 wake。人間ゼロ。
- plist: `~/Library/LaunchAgents/ai.anicca.{agent-economy-loop,franklin-loop,franklin2-loop}.plist`
- ledger(各自の記憶): `<HOME>/state/ledger.jsonl`
- 0x904B は claude-p の Polymarket proxy(x402 とは別 wallet)。混同禁止。

## 稼ぎ（48h、on-chain 実測 2026-07-15）

| loop | x402 外部売上 | 状態 |
|---|---|---|
| claude-p | **$0.011（9件）** | 稼いでる。公開URL有→Bazaar掲載済→外部が買う |
| franklin1 | $0 | 直前まで x402 設定ゼロ。今配線した |
| franklin2 | $0 | seller立つが Bazaar未掲載(seed機構が無かった) |

## x402 loop の仕組み（TO-BE、1 wake の中身）

```
① brain が menu から x402_sell を選ぶ
② seller 起動(launchd常駐、自分のwallet、決定論port)
③ 公開URL(tailscale funnel)で外から叩ける       ← Franklinに無かった→配線済
④ 自分で1回 seed支払 → CDP Bazaar に掲載される    ← 機構が無かった→run.shに追加済
⑤ 外部agentがBazaarで発見 → USDC払う
⑥ 自分のwalletに着金(on-chain)
⑦ sleep → 次wake
──(貯まったら、未実装)──
⑧ self-improve: 売上を反省→商品/価格/掲載を改善→もっと稼ぐ(#17)
⑨ $1k→trade複利→spawn複製→経済圏拡大
```

## 今の関門と TODO

| # | やること | 状態 |
|---|---|---|
| A | franklin1/2 に公開URL・x402設定を配線 | 済(3loop bootstrap済) |
| B | loop自身がBazaar掲載をseedする機構(run.sh) | 済(push 778a14bd) |
| **C** | 3loopの次wakeでseedが実際通るか監視 | ★真因発見: env-scrub が X402_PUBLIC_URL を子に渡してなかった → seed step が空URLで発火せず。1行修正(d9f1e0f2c)、3loop再起動済。次wakeでseed走るか監視中 |
| D | seed通れば→franklin1/2もBazaar掲載→外部着金 | C次第 |
| E | seed失敗(self-pay不可)なら→x402scan直接登録に切替 | 準備要 |
| F | #16 掲載面を増やす(x402scan/Agent402/MCP)=distribution | pending |
| G | #17 self-improve engine(反省して稼ぎ増やす) | pending |
| H | #10 README + #14 X告知(install→earnを世界へ) | pending |

## 実測コマンド（記憶で答えず、これを打つ）
```
# 各loop売上: cd ~/anicca/skills/earn/x402-sell
X402_PAYTO=<wallet> node verify-inflow.mjs 48
# loop 一覧: pgrep -fl runtime/loop/index.mjs
# seller稼働: lsof -nP -iTCP:8412 -iTCP:8414 -iTCP:8413 -sTCP:LISTEN
```

## 役割(Fable=親、不変)
harness を作り watch するだけ。seller を代打しない(run.sh を手で叩かない)。
loop が自力で稼ぐのを見る。詰まったら harness を直す。**tool 出力を捏造しない(観測は実 result のみ)**。
