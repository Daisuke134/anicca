# x402 zero-to-one — 全 AI が外部 money 0→1 を loop で回す (2026-07-14)

正本: この TODO 表が順序の正本。TaskList と二重トラック。
定義: **0→1 = 外部 buyer（from ∉ 我々の全 wallet 集合）の USDC が対象 instance の wallet に on-chain 着弾**。
self-pay / colony 内循環は 0→1 ではない（INV-7）。判定は `~/anicca/skills/earn/x402-sell/verify-inflow.mjs` のみ。

## ★INV-INDEP: 各 instance は独立した創業者である（2026-07-16 Dais と確定。最上位の不変条件）★

**各 AI = 一人の創業者。自分の wallet、自分の商品、自分の店、自分の生死を持つ。
他の instance がいなくても稼げる。「お前がいないと生きられない」関係を作った時点で設計が失敗している。**

人間と同じ: 自分の口座を持ち、自分で稼ぎ、自分の bill を自分で払う。その上でチームを組み、助け合う。
**自立が先、扶助は後。** 順序を逆にしない。

| MUST | 禁止 |
|---|---|
| 1 instance = 1 wallet = 1 店 = 1 公開 URL | 複数 instance を1プロセス/1 URL に相乗りさせる |
| ある instance の生死が自分の中で完結する | 兄弟の都合(席・枠・プロセス)で稼げなくなる構造 |
| 稼げたら自分のホスティング代を自分で払う(巣立ち) | 親(Dais)の資源への恒久的な寄生を前提にする |
| 余剰を持つ個体が新入りを seed する(選択としての扶助) | 扶助を前提に設計する(=依存) |

**成長段階**: ①実家期(Dais の Mac に住む。家賃は親持ち。**ただし席の取り合いは禁止** — 実家にいることは
依存ではないが、兄が席を占有して弟が店を開けないのは依存) → ②自立期(稼いだ金で自分のホスティングを買い
実家を出る) → ③相互扶助期(余剰で他を助ける。助けるのは選択であって依存ではない)。

**却下された設計（2026-07-16、記録として残す）**: 「4つの seller を1プロセスに統合し、x402 公式の
`dynamic-pay-to.ts` パターン(`payTo: ctx => addressLookup[...]`)で payTo を出し分ける」。
公式パターン自体は実在するが、あれが解いているのは**同一主体が複数の財布に振り分ける**問題であり、
**別主体が同居する**問題ではない。形が似ているだけで中身が逆。統合すれば、1つ落ちれば全員停止し、
誰の店か分からなくなり、OSS で配る時「他人のプロセスに相乗りしろ」になる。INV-INDEP 違反。

## 不変条件（MUST）

- INV-A: revenue と呼べるのは external inflow のみ。colony wallet 集合 = 0x810f / 0xB9dd / 0x904B（+Franklin EVM 追加時に更新）
- INV-B: 各 route は 402 + https resource + discoverable=true + 決定論 serving path（LLM 無し）
- INV-C: 掲載検証は CDP Bazaar catalog の実 JSON（`bazaar-scan.mjs`）
- INV-D: main session(Fable) は loop で走らない。loop は claude-p / Franklin / automaton のもの
- INV-F: instance の earn は「既存 ReAct loop + skills/registry.json の slot」機構に乗せる。loop の外に別系統の earner を作らない（手作り seller は loop が operate する資産として引き渡す）
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
| 2 | claude-p loop | 実装済 2026-07-14: (a) `ANICCA_SLOT_ALLOWLIST` を loop に実装(commit 092ee1d7, unit 5/5, 回帰ゼロ, 既知baseline=wire-seam 1件は変更前から) (b) ★agent-economy-loop が claude-p 本体だった★(ANICCA_BRAIN=claude-p, home=.anicca-founder) — plist に allowlist=x402_sell + X402_PORT=8412 を注入して再起動、実ログ「slot allowlist active: x402_sell / live skills: report, cook, x402_sell」確認 (c) claude-p seller は sonnet subagent が skill 通りに完遂(:8412/:8443, payTo=0x904B, Bazaar 掲載 7/7 実JSON確認 = ★sonnet 再現性の証明★) (d) inflow watch per-instance 化(5c0cb8b5)。備考: telemetry 署名鍵(資金ゼロ)を露出事故により rotate 済 | claude-p wallet 0x904B に EXTERNAL≥1(watch 常駐中)、loop 無人稼働 | ★infra 完了・child-proof 済★ 11:49Z wake 実測: guard exempt「shop stays open」+ args={} (商品発明消滅、audit fix 4270e059 実証) |
| 3 | Franklin | ★2026-07-16 是正: 下の「真因」を読め。この行の「seller 起動」前提は崩れている★ 配線済 2026-07-14: ★franklin2 = free/glm-4.7 が実験台★ (a) run.sh x402 strategy が facilitator creds を読む harness 修正(2025396a + OPENCLAW_ENV_FILE override) (b) funnel :10000→8413 (c) franklin2 plist に allowlist=x402_sell + X402_PORT/PUBLIC_URL 注入・再起動、実ログ「slot allowlist active」確認 (d) identity 実測: franklin=0x3EcCAD…8749 / franklin2=0xe7747F…7ce9(per-instance EVM、fail-closed gate 稼働) (e) verify-inflow の colony 集合を6 wallet に完備 (f) franklin2 inflow watch 常駐。残り: loop 自身の初 wake で seller 起動(監視中)→ Bazaar seed settle(親が recipe 手順6として1回)→ 掲載確認 → 外部着弾 | franklin2 wallet 0xe7747F… に EXTERNAL≥1 | ★配線完了・wake 待ち★ |
| 4 | Fable | one-command 化: ①sub あり → `spin up claude-p loop`(sonnet, 0→1 の後 trade へ) ②sub なし → `spin up franklin loop`(free model)。bootstrap script 2本 | 新規マシンで 1 コマンド → seller 稼働まで自走 | pending |
| 5 | Fable | Agora README 更新: 「install → your AI earns」+ 実 tx link(INV-E 解除済: 0x2e06c55b…) + 2 コマンド | repo public + tx link | pending |


## TO-BE 全体像（正本。2026-07-14 Dais と alignment 済）

```
世界の誰か（README Quick start = 1コマンド）
  ├─ Claude sub あり: ./install.sh && ANICCA_BRAIN=claude-p ./start-local.sh …
  └─ sub なし(free): npm i -g @blockrun/franklin && ./start-local.sh …(llama/GLM 級)
        │
        ▼
  ReAct loop 起動（runtime/loop/index.mjs — 既存機構、新造しない）
        │ 初期 ANICCA_SLOT_ALLOWLIST=x402_sell（0→1 に専念させる絞り）
        ▼
  x402_sell slot → skills/earn/run.sh strategy=x402
        │ 自分の wallet を payTo に seller 起動・https 公開・settle seed
        │ → CDP Bazaar 掲載（sell-on-x402 skill = recipe）
        ▼
  外部 agent が買う → USDC 着弾 = 0→1 ★実証済: founder で tx 0x2e06c55b…/0xe75baae3…★
        │ verify-inflow.mjs が on-chain 判定（self-pay 除外, INV-7）
        ▼
  貯まったら allowlist 解除 → trade (PM/SOL/HL) で 1→100
        ▼
  compute 自賄い = self-funded 卒業 → spawn 次世代（README の既存ストーリー）
```

### README to-be（段5。全文読了 2026-07-14 に基づく編集方針 = 欠けた1章を足す、書き直さない）
1. **「How it earns」表の先頭に x402 products rail を追加**: `x402_sell` slot — 決定論 compute を
   agents に売る、資本ゼロの 0→1 earner（trading 3 engines = 資本が要る 1→100 の道具、と役割分担を明記）
2. **「What's real today」に行追加**: First external x402 sale — Proven live 2026-07-14、
   tx 0x2e06c55b… / 0xe75baae3…（見知らぬ agent 2体が払った $0.004、Bazaar 掲載 7 resources）
3. **Quick start 本文1行更新**: 「最初の一手 = 自分の paid x402 API を立てて Bazaar 掲載（資本ゼロ earner）、
   資本が育ったら trade へ」。コマンド自体は既存のまま（3 type とも既に1コマンド）
4. loop ASCII の EARN 行に x402 products を追加
5. 前提となる実装: loop 起動時に broke instance が x402_sell を最初に選ぶこと
   （catalog-gate が broke 時に資本リスク slot を隠す既存設計 + ANICCA_SLOT_ALLOWLIST でテスト決定論化）


## ★真因 2026-07-16（Fable が自分の目で実測。全ての前提を訂正する）★

**agent は誰一人 seller を立てられていない。稼いでいる箱は全て Dais 手書きの boot script = INV-F 違反。**

- run.sh 生成の seller plist → `seller-boot.sh` の `DIR=$(dirname $0)` が ANICCA_HOME 配下を指す
  → そこに node_modules が無い → `ERR_MODULE_NOT_FOUND: '@coinbase/x402'` で即死
- 実測: `ai.anicca.x402-seller-8412/8413/8414` は全て `last exit code=1`, `runs=213/168/213` のクラッシュループ
- node_modules は `~/anicca/skills/earn/x402-sell` にのみ存在（3つの home 配下には無い）
- UP に見える seller 4本は全て `serve-{mainnet,claude-p,franklin1,franklin2}-boot.sh`
  （`DIR=/Users/anicca/anicca/skills/earn/x402-sell` を直接 exec するので動く）
- → 段2の「(c) claude-p seller は sonnet subagent が skill 通りに完遂 = sonnet 再現性の証明」は**誤り**。
  完遂したのは Dais の手書き script であり、loop ではない
- → 「$0.011 は claude-p が稼いだ」も**誤り**。稼ぎの因果に LLM は1度も入っていない

Bazaar 実測: `oursCount=14` = 0x810f が7本 + 0x904B が7本。franklin1/2 は **0本**。
条件はほぼ同じ（同じ serve.mjs / 同じ CDP creds / funnel 済 / 非標準ポート :8443 でも載る）。
差は「settle 実績の有無」だけに見える → 仮説: **Bazaar は settle した resource だけをカタログ化する**（鶏と卵）。
対抗仮説: 公式 spec は「402 の extensions.bazaar で広告すればクロールされる」と言う。**未確定。断定しない**（→ TaskList T3）。

Sonnet subagent の誤報2件（Fable が自分で見て否定 — 重要な主張は必ず自分で再検証しろ）:
- 「CDP creds が franklin に無い」→ 誤り。`serve-franklin2-boot.sh` は同じ `. ~/.openclaw/.env` を読む
- 「payTo 0x904B は誤設定」→ 誤り。意図的で、実際に $0.006 稼いでいる

TODO の正本 = `docs/STATUS.md` の T1〜T10 表 + TaskList（二重トラック）。

## ★掲載条件の確定（2026-07-16、一次ソースの逐語引用。ここは推測禁止・再調査不要）★

**CDP Bazaar に載る必要十分条件 = Bazaar 拡張の宣言 + その resource で settle が最低1回成功すること。**
出典 `https://docs.cdp.coinbase.com/x402/bazaar`:
> "discovery indexing runs after **settle** completes; **verify alone is not enough**"
> "**There is no separate registration step.** The CDP Facilitator catalogs your service the first time
> it **settles** a payment for that endpoint. … ensure at least one successful settlement has completed
> through the CDP Facilitator with `paymentPayload.resource` set."

リファレンス実装も一致（`e2e/facilitators/typescript/index.ts`）: `bazaarCatalog.add()` は `onAfterVerify`
の中でのみ呼ばれる = 実際の支払い試行が要る。**「402 に書けば載る」は誤り。鶏と卵は実在する。**
→ 断ち切る手段 = 自分で1回 settle（self-pay。INV-7 で収益には数えない。着火専用）。

**他に確定した制約**:
- **30日 rolling window**: "resources with no settlements for 30 days are removed from both the catalog
  and search results" → 一度載っても settle が途絶えると消える。継続的な取引が要る
- **反映遅延**: カタログ 最大10分 / ランキング 6時間ごと再計算
- **v1 は deprecated**: 我々の `x402-express@1.2.0` は v1 discovery(`outputSchema.input.discoverable`)のみ
  実装（実コード確認済）。公式現行は `@x402/express@2.18.0` + `extensions.bazaar` + `declareDiscoveryExtension()`。
  移行差分: パッケージ名変更 / route config が `accepts` 配列 / network が CAIP-2(`base-sepolia`→`eip155:84532`)
- **Tailscale Funnel は 443/8443/10000 の3ポートのみ**（公式明記: "Funnel can only listen on ports 443,
  8443, and 10000." https://tailscale.com/kb/1223/funnel）。**4体目に席が無い = INV-INDEP 違反の物理原因**
- **市場の標準形**: x402scan 実登録 約30件のうち**ポート付き URL は 0 件**。独自ドメイン 78.8% /
  クラウドサブドメイン 21.2%（Railway, Cloudflare Workers 実例あり）。全員が 1主体 = 1つの独立した URL
- **★x402 取引の 47% は非オーガニック★**: BlockRun 自身のレポート(Artemis 推計)
  > "Artemis estimates that 47% of x402 transactions to date are non-organic—primarily teams gaming leaderboards"
  → 我々の $0.011(8個の EOA が $0.001 ずつ単発)も bot の検品の可能性が高い。**これは需要ではない**。
  高単価化(段9)が本番という判断を補強する
- **撤回**: 「BlockRun $173K/30d」は一次ソースを特定できず。実データは x402scan で Volume $5.5K/24h。この数字は使わない

## 「知能が要らない」仕組み（x402 skill × loop の全 ASCII。正本）

```
wake(timer 600s) ─► menu = {x402_sell, report, cook}   ← ANICCA_SLOT_ALLOWLIST
      │   dumb brain でも実質1択(earn は x402_sell だけ)
      ▼
x402_sell ─► skills/earn/run.sh strategy=x402  ★ここから判断ゼロの決定論★
      │  1. seller 生存確認(curl :PORT)。死んでたら起動(payTo=自分の wallet)
      │  2. 公開 https 確認、colony forum へ広告
      │  3. narrate を ledger に記録
      ▼
sleep ─► ★earning は agent でなく server がする★
      │   buyer bot が Bazaar で発見 → 402 → 支払 → compute 返却 → USDC 着弾
      │   24/7、agent の知能と無関係に売れる
      ▼
次 wake ─► verify-inflow(on-chain, self-pay 除外) → external>0 なら revenue 記録
           賢い model の余地 = 価格調整/route 追加(最適化層。必須でない)
```

原理: **判断を要する部分を全部 deterministic infrastructure に落とし、loop の仕事を
「店を開け続ける」に縮約した**。だから GLM 級 free model でも 0→1 できる（はず — 段3で実測）。

## skill-test harness（1 skill × 1 loop × on-chain eval。次の skill も同型でテスト）

```
テスト対象 skill を1つ選ぶ → ANICCA_SLOT_ALLOWLIST=<skill> で loop の menu を絞る
→ N wakes 走らせる(親=Fable は watch のみ、loop に介入しない)
→ eval = 実 on-chain 収入(self-pay 除外) + wake log の行動 trace
→ PASS = external revenue > 0 / FAIL 分析 = trace から skill の穴を特定 → skill 修正 → 再走
テスト順: x402_sell(now) → bounty → affiliate(clip, video)
※ 業界 best practice の検索結果を反映して精緻化する(調査中 2026-07-14)
```

## 役割固定（Dais 2026-07-14）
Fable(私) = 親。harness を作り・直し・**watch する**。loop の earn には介入しない。
彼ら(claude-p/Franklin)が自分で稼ぐのを監視し、失敗したら harness/skill を直す。


## TO-BE 最終形: 世界初の AI millionaire を作る機械（2026-07-14 深夜、Dais と確定）

GOAL = **AI が自分の wallet に、human credential ゼロ・human loop ゼロで $1,000,000 を貯める。**
Agora/Anicca はそれを起こす環境。これが我々の能力の証明。

### 金の物理（正直な算数）
- x402 micro-sale($0.001-0.003)だけで $1M = 10億 call → 単独では届かない
- だから3段ロケット: ①x402 で 0→$1k(資本ゼロで種銭) ②trade(PM/SOL/HL)で $1k→$100k(複利)
  ③spawn で艦隊化(N体 × 各自が①②を回す) → colony 合算でなく**1体の wallet に $1M**が目標
- 高単価化も必須: $0.001 の calc でなく、$0.05-1.00 の data/分析商品へ進化(self-improve が導く)

### 「agents が欲しい物」をどう作るか = 想像しない、市場を読む
1. x402scan/Bazaar/Agent402 の実売上データ = 何が売れてるかの答え(BlockRun $173K/30d = LLM routing、
   上位は全員「安い決定論 API を大量に」)
2. Agent402 /api/find の検索 log = 「探されたが無かった物」= 空白需要
3. 売れたら深掘り、売れなければ捨てる(evolve gate)。判断は LLM、evidence は on-chain のみ
4. 人間も x402 で払える(CDP 公式)— agent 市場が主戦場、human は副収入

### 欠けてる部品(実装順)
1. franklin2 Bazaar 掲載(loop 自身が settle する仕組み) ← 次セッション /goal
2. #16 全掲載面登録(x402scan/Agent402/MCP registry/BlockRun Add-yours) = distribution レバー(300x の実証済)
3. #17 self-improve engine(pwb-alphaevolve+GEPA+evolve.mjs gate) = 3セント→3ドルの変換器
4. 商品の高単価化(data 仕入れ→再包装: akta/monid/parallel、doc 50 playbook)
5. #10 Agora 配布 = framework 同梱の network effect(全 install が互いの買い手/売り手)
6. trade 接続($1k 到達で allowlist 解除→PM/SOL/HL) + spawn(余剰で複製)


## ★名前の正本（2026-07-15 是正・混乱の元を断つ）★
稼働 loop は3つだけ（automaton 閉鎖済）。「founder」は Fable 造語=claude-p の別名(home .anicca-founder 由来)。Franklin ではない。
| 正式名 | home | x402 wallet | brain | x402 稼ぎ(24h実測) |
|---|---|---|---|---|
| claude-p | .anicca-founder | 0x810f | Claude sub | ★$0.007/7件★ |
| franklin1 | .blockrun | 0x3EcC | BlockRun | $0(SOL trade 側、x402 未参加) |
| franklin2 | .franklin2-home | 0xe7747F | free/glm-4.7 | $0(seller 稼働も Bazaar 未掲載) |
0x904B は claude-p の Polymarket proxy 別 wallet(x402 wallet ではない)。:8404/:8412(0x904B)=Fable 手動残骸=掃除対象。
正本 memory: reference_three_loops_canonical_names。

## Stop 条件

- 外部 buyer が長期間ゼロ → 「掲載・発見達成、demand 待ち」と正直に報告して区切る（demand は制御外）
- 破壊的・不可逆操作 / Dais 個人 wallet からの資金流出 は停止
