# x402 zero-to-one — 全 AI が外部 money 0→1 を loop で回す (2026-07-14)

正本: この TODO 表が順序の正本。TaskList と二重トラック。
定義: **0→1 = 外部 buyer（from ∉ 我々の全 wallet 集合）の USDC が対象 instance の wallet に on-chain 着弾**。
self-pay / colony 内循環は 0→1 ではない（INV-7）。判定は `~/anicca/skills/earn/x402-sell/verify-inflow.mjs` のみ。

## 不変条件（MUST）

- INV-A: revenue と呼べるのは external inflow のみ。colony wallet 集合 = 0x810f / 0xB9dd / 0x904B（+Franklin EVM 追加時に更新）
- INV-B: 各 route は 402 + https resource + discoverable=true + 決定論 serving path（LLM 無し）
- INV-C: 掲載検証は CDP Bazaar catalog の実 JSON（`bazaar-scan.mjs`）
- INV-D: main session(Fable) は loop で走らない。loop は claude-p / Franklin / automaton のもの
- INV-E: README 等に「earns money」と書けるのは external tx link が貼れてから

## 到達済（2026-07-14、own-eyes）

- 7 resource が CDP Bazaar 掲載（catalog 25,906 件中、実 JSON 確認）
- 全 route の paid path E2E（settle tx 有、例 0x03c875fb…）
- /.well-known/x402.json + /llms.txt 公開
- sell-on-x402 turnkey recipe = `~/anicca/skills/earn/x402-sell/SKILL.md`（commit 695c11e0）
- awesome-x402 掲載 PR: https://github.com/xpaysh/awesome-x402/pull/838
- ★2026-07-14 09:05Z 更新: external revenue = $0.004 USDC (外部 buyer 2件、on-chain 検証済)。zero-to-one 達成★

## TODO 表（順序の正本）

| 段 | owner | やること | done 判定 | 状態 |
|---|---|---|---|---|
| 0 | Fable(今) | ★恒久 disk fix★ — disk-full で session brick を二度と起こさない自動機構（調査→実装→launchd 常駐） | 閾値割れで自動 prune + 通知が実機で動く | ★done 2026-07-14★ (3層: autoprune/janitor/alerter, FORCE 実測 26→34GB, 正本 ~/.openclaw/skills/mac-health/README.md) |
| 1 | Fable(今) | 経済圏 0→1: 外部 buyer 1件（seller payTo=0x810f 稼働中） | verify-inflow で EXTERNAL≥1 | ★done 2026-07-14★ EXTERNAL=2, $0.004 USDC (tx 0x2e06c55b… from 0x74610bd8…, tx 0xe75baae3… from 0x36a9b00e…, 両方 receipt 0x1) |
| 1b | Fable(今) | demand 面の追加: x402scan 掲載確認・Agent402 index・PR#838 follow | 各面で発見可能を実測 | pending |
| 2 | claude-p loop | agent-economy loop 化: payTo=0x904B の seller 複製 + self-improve loop（verify-inflow→死に route 削除→需要 primitive 追加→再掲載）を sonnet loop で常駐 | claude-p wallet に EXTERNAL≥1、loop が無人で1週間回る | pending |
| 3 | Franklin | Franklin の 0→1: per-instance EVM key → 自分 payTo の seller → settle seed → 掲載 → 外部着弾。★self-funded + human credential ゼロの証明★ | Franklin wallet に EXTERNAL≥1 | pending |
| 4 | Fable | Agora 配布: README「install → your AI earns」+ 実 tx link | repo public + tx link | pending(INV-E 待ち) |

## Stop 条件

- 外部 buyer が長期間ゼロ → 「掲載・発見達成、demand 待ち」と正直に報告して区切る（demand は制御外）
- 破壊的・不可逆操作 / Dais 個人 wallet からの資金流出 は停止
