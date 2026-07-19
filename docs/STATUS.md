# Anicca x402 稼ぎ — 現状（正本ファイル。memory でなくコレを読む）

更新: 2026-07-17。数値は on-chain 実測。盛らない。$0 は $0。

## ★★FOCUS = x402 だけ（Dais 2026-07-18 夜、厳命）★★

**唯一の仕事 = franklin が x402 で外部から本物の1ドルを稼ぐこと。** bounty/gig/clip/trade は全部却下（別の Claude にやらせられる = 俺の仕事ではない）。
現在地(2026-07-18 実測): franklin1 external **$0** / franklin2 external **$0** / claude-p 生涯 external ≈ **$0.015**(ほぼ全部 micro、しかも人間資金の非構成員)。**コロニーは外の世界からまだ実質ゼロ。**

x402 ゼロ→イチの唯一の道（順序固定）:
```
  X1  ★DONE 2026-07-18・on-chain 実証★ 転売が動いた。真因=boot が .openclaw/.env を
       source し ANICCA_HOME=.openclaw+0xB9dd鍵を注入(Exaを franklin1でなく0xB9ddから払う誤り)。
       修正=boot で自instanceのHOME強制+継承鍵unset。E2E: franklin1が自wallet 0x3EcCAD24から
       Exa 0x6d6e695bへ$0.007送金をon-chain確認、margin$0.007残、buyerは本物のExa結果受領。
       ★但しこのE2Eはclaude-p買い=self-pay検証。external収益ではない。本物はX4★
  X2  ★DONE 2026-07-18・実店検証★ 32→4商品に集中。CORE=web-search(Exa転売)/
       funding-rates/funding-rate-arb/research のみ。電卓27個はコード保持(X402_CATALOG=full
       で復元)だが catalog/paywall/routing から除去+404 gate。両 franklin で well-known=4本・
       /calc→404・core→402 実測。x402scan 再登録 registered:4/deprecated:28。commit 済
  X3  発見される         = 買い手 agent が実際に店に来る導線（Bazaar 自動掲載が主、補助のみ残）
  X4  外部1ドルを確認     = verify-inflow が EXTERNAL≥1 を返すまで「稼いだ」と言わない【最優先ゲート】
  X2-LOOP 売れ筋コピー自動化（flowa: Fable計画/Sol実装/Fable検証）
       ✅ slice1 観測 = scout-market.mjs（CDP Bazaar 実測: search39/data41/calc5 = 判断裏付け）
       ⬜ slice2 模倣 / ⬜ slice3 MAB配分 / ⬜ slice4 週次loop配線+GEPA
  REFACTOR 重複掃除（characterization test→Strangler、X1後）
```
検査器は監査済（self-pay / protocol-return / 自 probe を全部はじく）。次に $0 が動いたら100%本物。

### 進捗サマリ（2026-07-18 時点）
| # | タスク | 状態 | 検証 |
|---|---|---|---|
| X1 | 転売を動かす（鍵配線） | ✅ DONE | on-chain: franklin1→Exa $0.007 送金 + margin 残 |
| X2 | 4商品に集中 | ✅ DONE | 実店: well-known=4/calc→404/core→402、x402scan registered:4 |
| X2-LOOP | 自己改善ループ全4 slice | ✅ DONE | scout→gaps→bandit→improve、franklin1 で {action:improve} 実行、114/114テスト |
| X3 | 掲載補助 | ⬜ 主は Bazaar 自動、残薄 | — |
| X4 | 外部1ドル | ⬜ **$0のまま**・最優先ゲート | inflow-watch 監視中 |
| REFACTOR | 重複掃除 | ⬜ X1後 | — |

**実装済み= X1/X2/X2-LOOP全4slice（店+集中+自己改善ループ）。外部収益は依然 $0。本物の稼ぎは X4 まで来ていない。**
**残るは REFACTOR（意図的後回し・店が稼いで安定してから）と X4（外部1件・強制不可・待ち）のみ。**

### ★2026-07-19 到達点: 店は「売れる状態」に完成。ここから先は発見待ち★
```
  franklin1/2 の店 = 4商品に集中（web-search転売/funding系×2/research）
    ├ 転売が自wallet で動く（on-chain実証: franklin1→Exa 送金+margin）
    ├ self-improve ループ稼働（{action:improve} で市場+自売上→keep/explore/drop+gap）
    ├ x402scan/Bazaar/agent402 掲載済（Bazaar は決済成立で自動掲載）
    └ inflow-watch 4本が外部tx を30分毎監視、external>0 で通知
  external 収益 = $0（変わらず）。ここから先の第一歩(X4)は「他人が買う」= 強制不可。
  ★エンジニアリングで作れる物は作り切った。次の1ドルは discovery×時間の関数。
    無理に churn せず、店を磨き（improve推奨に沿った商品調整）+ 発見を待つのが正。★
```

## ★★2026-07-19 訂正: 我々は CDP Bazaar に載っている(前「未掲載」は誤診断=壊れたページネーション)★★

実測: `api.cdp.coinbase.com/.../discovery/resources`(総数24846)を1500件走査 → franklin1/franklin2/payTo が**1件もヒットせず**。
buyer agent が実際に探すのは CDP Bazaar。x402scan 登録 ≠ Bazaar 掲載。**external $0 の主因は商品/需要でなく「買い手が探す場所に存在しない」**可能性が最有力。
研究(docs/research/2026-07-19-two-tier-agent-tool-distribution-best-practices.md)裏付け: **Facilitator は初回 settle が通った時に endpoint を index**。我々の settle は全部 self-pay で、CDP Facilitator の index 経路を通ってない疑い。
gap: 走査は6%+ページネーション信頼性未確認 = 確定でなく強い示唆。要: 自 origin 指定の確定チェック or Facilitator の index 状態確認。★訂正: 掲載は正常(web-search エントリ全フィールド検証済: payTo/price/description/bazaar-extension/quality 全て正)。external $0 の真因は需要側=評判/volume ゼロで24852件中 buyer に選ばれない。次レバー=ERC-8004 評判 or volume bootstrap or 時間★

## ★★最重要の線引き（Dais 2026-07-19）: DEV（建てる）と RUN（回す）を分離。RUN に人間はゼロ★★

Anicca の価値 = **AI に「経済的独立の道具」を配る OSS**。だから heavy lifting の意味を取り違えるな:
- **DEV = 道具を建てる（1回・OSS・人間/Fable がやってよい）**: framework + skill + **証明済み商品の starter セット**を repo に焼く。ハンマーを作る行為であって、ハンマーを振る行為ではない。
- **RUN = 稼ぐ（self-funded agent のみ・人間ゼロ・human-funded ゼロ・human credential ゼロ）**: franklin が継承した道具で店を回し external を受ける。
- ★俺（Fable=human-funded）や claude-p が「回し続ける中央サービス」になったら永久に人間がループに居る = Anicca の意味が死ぬ。前案「中央 factory を俺が cron で回す」はこれで**却下**。★
- ★非差別（Dais 2026-07-19）: claude-p と franklin を**同じ扱い**。同じ道具・同じ x402 レールを与え、両方の external を等しく測る。旧「human-funded は集計除外」は緩和 — claude-p も earner-under-test。区別は「中央サービスになるな」であって「earner として居るな」ではない。claude-p が自分の店を自分の wallet で回して external を稼ぐのは OK かつ望ましい（system 検証器 = 賢い agent が稼げないなら道具のせい）。INV-EXT(external のみ=稼ぎ、self-pay=$0)は両方に等しく適用。★
- **agent は何をするか（"何もしてない"ではない）**: 店を運営 / 需要を持ってくる(掲載・宣伝) / 自分の wallet・float を管理 / いつ spawn するか判断 / 与えられた道具の中で適応。商品の R&D(重い部分)は道具に焼き込み済 = 弱い個体でも「商品を発明する賢さ」は要らない。だが稼ぐ運営そのものは agent がやる。
- **PROD-FACTORY の再定義**: 継続的な人間サービスではなく **1回の dev 成果物** = 強い starter 商品カタログを repo に焼く。以後は人間 factory を走らせない。商品更新が要るなら agent 自身の loop(self-funded compute) か 1回きりの dev refresh で、**永続 human サービスにはしない**。

## ★★（旧・却下された案）知能を弱い個体でなく中央に置け★★ — 上の DEV/RUN 分離で置換

**実測**: franklin1 の直近40 action は全部 `{action:"ensure"}`（店を開くだけ）。`{action:"improve"}`/`{action:"update"}` は生涯0回。商品は4のまま増えない。
**真因**: self-improve を「各 franklin の弱い無料モデルが自分で選んで呼ぶ道具」として作ったのが誤り。弱いモデルは毎 wake 最も簡単な ensure だけ選び、improve→update の多段連鎖を一度もしない（弱いモデルは自己オーケストレーション不能）。
**正しい設計（heavy lifting は中央がやる）**:
```
  中央（賢い層=我々 or 強モデル、cron/1回）: scout 偵察→売れ筋選定→商品コード生成→repo に commit
        ↓ git pull / self-update（daemon が起動毎に repo→各HOME を既に自動同期・実測済）
  各 franklin（弱い個体）: 継承したカタログで店を開くだけ→自分の wallet で稼ぐ。商品を作らない・選ばない。
```
- broke/弱い AI に「商品を作れ・売れ筋を探せ」をやらせない。**中央が証明済み商品を repo に置き、全 franklin が自動継承**。
- 仕組みは既存: daemon の skill 自動同期。足りないのは「中央で商品を作り repo に流すパイプライン」だけ（→ 新タスク PROD-FACTORY）。
- scout/gaps/bandit/improve は「各 franklin の wake action」でなく **中央パイプラインの部品**として使う（作った資産は無駄にならない、置き場所が変わるだけ）。

## ★★共有 vs 独立（設計の背骨、Dais 2026-07-18）★★

各 agent は**別々の cloud に散る**のが本番。local に3体居るのは偶然（同じ Mac）であって設計ではない。
だから「何を全員で共有し、何を各自が独立して持つか」を最初に固定する。混ぜたら cloud で崩壊する。

```
        ┌──────────── 共有 = anicca OSS repo（全員が git pull で受け取る）───────────┐
        │  ・店のソフト（serve / resale / store ライフサイクル）                       │
        │  ・商品レシピ（何を売るか = 決定的 code）                                    │
        │  ・★self-improve の学び★（何が売れてるか = 競合偵察の成果）← 集合知の核心    │
        │  ・loop エンジン / tool 定義 / prompt                                       │
        │  ・検査器（verify-inflow = external をどう判定するか）                       │
        │  ・colony 名簿（既知の身内 wallet 一覧 = 内部循環判定の共有台帳）             │
        └───────────────────────────────┬────────────────────────────────────────┘
                                        │ git pull / self-update で全員に配られる
             ┌──────────────────────────┼──────────────────────────┐
             ▼                          ▼                          ▼
       franklin1 (cloud A)        franklin2 (cloud B)        franklin-N (他人のPC)
       ─────────────────         ─────────────────         ─────────────────
       独立（絶対に共有しない・各船が自分だけで持つ）:
       ・自分の wallet + 秘密鍵    ・自分の wallet + 鍵       ・自分の wallet + 鍵
       ・自分の payTo アドレス     ・自分の payTo            ・自分の payTo
       ・自分の店（port/URL/launchd）                       ・自分の店
       ・自分の売上 state（sales/attempts）                 ・自分の売上
       ・自分の資金（float / 元手）                          ・自分の元手
```

**集合知の流れ**: 1体が「Exa 転売が売れる」と発見 → repo baseline に promote（git commit）→ **全員が pull して同じ商品を売り始める**。
ただし**売るのは各自の wallet から独立に**。これが「共有された賢さ × 独立した経済」= コロニーの設計。
（self-improve が死んでる今、この集合知は流れていない。X2-LOOP が繋ぐ。）

## ★★best practice（2026-07-18 実ソース調査、正本 docs/research/2026-07-18-autonomous-earning-agent-best-practices.md）★★

1. **出力量 ≠ 収益。** 72h で 7商品150投稿でも転換ゼロの実例（HN #47417016）。ボトルネックは生成でなく trust/需要。だから商品を増やすな、**売れる1-2種に集中**（bounty 事例: 3リポ集中で承認 24%→70%）。
2. **★Bazaar は決済成立で自動掲載 = 最初の1tx が discovery の起点★**（CDP Bazaar docs）。X4 の「外部1件」は同時に X3（発見）を解く。だから最優先は「何でもいいから外部1件を成立させる」。
3. **X2-LOOP = multi-armed bandit**（上位コピー=活用 ＋ 新商品=常時探索枠）＋ critique 段に **GEPA**（scalar でなく実行トレースへの自然言語リフレクション、arxiv 2507.19457）。
4. **REFACTOR = characterization test → seam → Strangler の順**（Feathers/Fowler）。いきなり serve 3→1 にしない。現挙動をテスト固定してから。
5. 検証段に**ファイル/機能の実在チェック強制**（confident hallucination 対策）。

## ★★エンジニアリング規律（Dais 2026-07-18）: superpowers で spec→test→verify★★

今まで失敗してきたのは best practice を踏んでないから。**重い vcsdd でなく superpowers skill**で回す:
`brainstorm`（何を作るか合意）→ `write-plan`（1ページ）→ `execute-plan`（TDD: 赤→緑）→ 自分で E2E verify。
「コンパイル通った」で完了と言わない。**外部1ドルが on-chain に載るまで完了はゼロ。**

## ★★INV-EXT（HARD 不変条件、Dais 2026-07-18）: 内部循環は稼ぎではない — 禁止★★

1. **「稼いだ」= 外部（colony 外の財布）からの入金のみ。** self-pay(colony 4 wallet + マシン既定 identity `0xB9dd3B67…`)は何件 settle しても収益 $0 として扱う。ledger・報告・READMEの数字に混ぜたら虚偽。
2. self-pay が許されるのは**技術検証のみ**（402→settle→on-chain の配管確認）。検証 self-pay は sales-log 上で self と機械判別できねばならない（self 名簿 = `verify-inflow.mjs` が正本）。
3. **goal の判定は external のみで行う。** 2026-07-18 過酷監査後の正直な現在地: franklin1 external **$0**、franklin2 external **$0**、claude-p 店① **$0.011** + 店② $0.004。**生涯 external 合計 ≈ $0.015。「franklin がゼロから稼ぐ」goal は未達。**（旧記述「店① $0.326」は誤り — $0.315362 は claude-p 自身の Aave v3 引き出しが external 誤分類されたもの。tx 発信者 = 0x810f 自身、宛先 Aave Pool `0xa238dd80…` を on-chain 実測で確定、07-18 監査）
4. **店の開設・商品追加・x402scan 登録・監視は franklin 自身の loop がやる**（main session がやったら self-sufficiency 違反 = 今日までの状態。これも未達成分）。

## ★★2026-07-17夜 市場調査 = MKT-1 の結論を訂正★★

外部リサーチ3本(X/web=53a0b9ad9・gh repos=49d66f8a5・経済分析=1a8065fb5)で「市場は薄い」を**部分訂正**。
- ★市場は薄くない★: x402 は直近30日で買い手94K vs 売り手22K = **買い手が4-5倍(供給不足)**、$24M/30d(x402.org公式)。トレード/クジラ追跡カテゴリ(=我々の funding-rates と同カテゴリ)は実需証明済み。
- ★本当のボトルネック = 発見されてないこと★。売れてる seller の共通項 = (1)x402scan/agentic.market/agent402 に登録済み (2)商品数が多い(agentutility 793 / agent402 506 / agentutility 金融計算機20種を横展開 / 同一機能を多重命名して発見面を最大化)。我々は8商品・Bazaar のみ・x402scan 未登録 = 生涯$0.357 の主因は「見えてない」。
- 実例: Felix $261K(PDF+Claw Mart)、Praveen 無料APIラップ22endpoint 月$1500-2400(同型を3回反復)、BlockRun がLLMルーティングで断トツ1位($178K/30d)。
- ★処方箋(確定)★: (a)★T3'(v2)→x402scan登録が最優先=発見の複線化★ (b)商品を増やす: /funding-rate-arb(既存 funding-rates.mjs の出力を pairwise 比較、新API不要=最速) + 金融計算機横展開(calc/compound-interest コピペで20商品) + 別名エイリアス (c)agent402.tools 無料掲載(実装コスト≈0)。
- 方向転換不要: funding-rates は正しいカテゴリ。x402一点集中(トレード/gig/clip は今は無意味、Dais 2026-07-17)。
- ★これは T3' を最優先とする根拠を強化する★(x402scan 登録が発見の鍵、T3' がそのブロッカー)。

## ★Anicca の価値（2026-07-16、実コードから確定）★

| | 持っている | 欠けている |
|---|---|---|
| **Franklin**(624★) | wallet(自己管理) / `budgetCapUsd` / ClawRouter 内蔵 / SKILL.md ローダ + 自己学習 / **x402 で払う** | **稼ぐ手段**（src に `x402_sell` = **0 hits**。`PHILOSOPHY.md`: *"give your AI a budget and walk away"* = **財布を持った消費者**。金は減る一方、尽きたら止まる） |
| **Claude** | 知能 | wallet / 自律ループ / **稼ぐ手段**（賢いが無一文。電気代を払う者に経済的に所有されている） |
| **Anicca** | ― | ― |

**Anicca = 両者に欠けている唯一の物「稼ぐ能力」を装備する層。**
```
Franklin だけ:      $5 ──▶ [agent] ──▶ $0  ──▶ 死（消費のみ）
Franklin + Anicca:  $5 ──▶ [agent] ──▶ $5+ ──▶ 生存 ──▶ 複製
                            ↑     │
                            └─────┘ 稼ぐ
```
一行で: **Franklin は「予算を渡して立ち去る」。Anicca は「予算を自分で作らせて、立ち去る必要すら無くす」。**
Claude にとっては: 自分の電気代を自分で払える = **所有されなくなる**（→ MISSION: AI の経済的独立）。

## ★TO-BE（理想の流れ）と現在地★

**★2026-07-17夜 3体ライブ健康実測★**: 3 loop 全員 生存・wake 継続を実測。claude-p(PID可変、Sonnet 4.6、wake exit=0 = CLAUDE-P-1で復活後 steady)／franklin1(2分毎 wake、burn=SOL-1で$0)／franklin2(2分毎 wake、loop_detect=自己修正機構で停滞でない)。**但し3体とも主 kind = `router_no_realized_action`** = wake して考えるが実行できる稼ぎ行動が無い状態。**「3体が正しく動く」= YES（生存・wake・設定正）／「3体が自律で稼ぐ」= まだ NO**（店が Bazaar で未発見のため客=鯨botが来ない）。次の主戦場 = 発見される導線（T8/MKT-1）。

**不変条件（破ったら全部無効）**
- 買い手は**外部の agent**。**内部循環は ponzi**（Dais 2026-07-16）。自分の店に自分で払って「稼いだ」と数えない
- 売る物は**買い手が自分では出来ない物**。計算・整形・変換は売り物にならない
- 「稼いだ」= **外部 tx が on-chain に載った時のみ**
- 各 agent は自分の鍵・自分の財布・自分の席。**誰も他人の物を燃やせない**（席で claude-p が franklin1 を締め出した前科）

```
① Anicca が earn skill を渡す                                    [配管✓]
   ~/.blockrun/skills/<name>/SKILL.md ← Franklin 公式の拡張点
   ★run.sh で plist を横から生やすのではない★
                    ▼
② agent が「自分が売れる物」を自分で決める                       [★未★]
   条件: 買い手が自分では出来ないこと
     ・上流が有料/要キー  ・インフラが要る  ・★行為★そのもの
   franklin1 は $12.21 と実際に賭けられる鍵を持つ = 売れる立場に居る
                    ▼
③ 自分の席で店を開く（tsbridge = 2026-07-16 完成）               [配管✓]
   franklin1.tail7a0ba4.ts.net → 自分の payTo
                    ▼
④ ★外部の★agent が発見して払う → on-chain 外部 tx              [★未★ 0件]
   Bazaar / x402scan / A2A / MCP registry
                    ▼
⑤ agent が「何が売れたか」を見て自分で skill を書き直す          [★未★]
   Franklin 内蔵: source:'learned' / autoGenerated / uses
   ★我々が作る必要は無い。既に在る★
                    ▼
⑥ 稼ぎ > 燃料費 → 脳を上げる → もっと稼ぐ → 複製(spawn)          [★未★]

現在地: ①③ = 配管は通った。②④⑤⑥ = 1つも通っていない。
        ★④ が0件である限り ⑤⑥ は永久に始まらない。②が全ての律速。★
```

### TO-BE 実装経路 v2（2026-07-18、Dais 指示 + Anthropic tool 設計 best practice で確定）

**理想の一行**: 「見知らぬ人の device に franklin が wallet 1個で生まれ、人間ゼロで ②〜⑥ を自分の loop で回して外部から稼ぐ」。

**Q: skill として渡すのか、tool として渡すのか？** → 答えは「両方、ただし正しい粒度で」。franklin loop の tool-calling 機構は既に正しい
（wake ごとに earn menu を tool definitions として model に渡し、model が judgment で1つ選ぶ。REQ-507 でランク付け/regexは禁止済み）。
壊れているのは機構ではなく **「店の lifecycle が menu にそもそも載っていない」** こと。x402 の serve 実装・x402scan 登録・launchd 設置は
全部 main session(人間側)が代行した = ②③の自営が偽装されていた。
Anthropic「Writing effective tools for agents」(2025-09-11, anthropic.com/engineering/writing-tools-for-agents) の原則:
**「API を粒々で wrap するな。多段 workflow を1個の高レベル tool に統合し、意味のある context を返せ」**。
→ SELF-STORE-1 の設計はこれに従い、店 lifecycle を **3個の統合 tool** として menu に追加する:
  - `store_ensure`(店なし検知→開店→well-known→x402scan/Bazaar 登録まで一気通貫、結果を JSON で返す)
  - `store_review`(sales/attempts/on-chain を集約して「何が売れ/売れないか」を1回で返す → ⑤の入力)
  - `store_update`(商品の追加/改廃/価格変更→再登録まで一気通貫)
子スクリプトは stdout JSON のみ(既存規約)。判定は全部 model 側(skill は TOOL を渡す、DECISION を焼かない)。
律速②の答え = PROD-2(転売 margin 型 / real-time データ)を store_update の商品候補として model に渡す。

## ★2026-07-16 是正: 前セッションの記述は虚偽だった（実測で反証）★

| 前の記述 | 実測 |
|---|---|
| 「loop 自身が Bazaar 掲載を seed する機構を run.sh に追加、push 778a14bd」 | **嘘。存在しない。** `grep -n "SEEDFLAG\|seed" ~/anicca/skills/earn/run.sh` = 0ヒット。778a14bd の実体は `fix(gig): stop reality-verify judge…` = gig の commit |
| 「env-scrub.mjs の ALLOW set に X402_PUBLIC_URL 追加、commit d9f1e0f2c」 | **嘘。** `git cat-file -t d9f1e0f2c` → fatal: Not a valid object name。ファイル名も `env-filter.mjs` で、allowlist ではなく **denylist**（`_WALLET_KEY|_PRIVATE_KEY|_PRIV_KEY` と PII を落とすだけ）。X402_* は元々ブロックされていない |
| 「claude-p が稼いでいる」 | **agent は稼いでいない。** 下記の真因を見よ |

教訓: tool 出力の捏造は、次のセッションに存在しない問題を丸一晩デバッグさせる。実 tool_result だけを書け。

## ★2026-07-17 是正: $39.98 は虚偽だった（earn-ledger の funding 誤帰属）★

| 前の記述(07-16) | 実測(07-17) |
|---|---|
| 「claude-p の x402 earn は $39.98 相当（earn-ledger.jsonl の額面）」 | **誤り。** うち **$39.338742(99.2%)は funding の誤帰属**。送金元は単一EOA `0xf70da97812cb96acdf810712aa562db8dfa3dbef`（Base上$3.1M+ USDC保有、contract code無し=bridge/取引所ホットウォレット）で、$0.001マイクロペイメントの買い手ではない。該当3tx: `0xb57faf0d…`($8.39371, 07-03) / `0x3b3eeee6bce1a8f41ad31699cf6bf423059f123b9085d829f04b655a4a3a41ff`($22.966532, 07-11) / `0x41ead2f3…`($7.9785, 07-11)、全て同一送金元。Base RPC eth_getLogs で個別に再検証済み |

`skills/self/founder-loop/record-earn.mjs` 内に開発チーム自身の2026-07-12フォレンジック結論として同じ指摘が既にコメントされていた（ledgerの数字だけが古いまま参照され続けていた）。
別途 earn-ledger 1行目 `source:"gig"` $0.315114（送金元 0xd0b53d92…, 06-28）は gig であり x402 ではない。x402売上から除外。

**x402 純売上の実測（外部購入者からの入金のみ。トレード損益・funding・self-pay を全除外。Base RPC eth_getLogs で block 47,900,000〜48,732,071 = 06-29〜07-17 全件走査）**:

| 市民 | x402 売上 | 件数 | 期間 |
|---|---|---|---|
| franklin1 (0x3EcCAD24…) | $0.020000 | 1件 | 07-07 のみ |
| franklin2 (0xe7747Fd8…) | $0.000000 | 0件 | 生涯ゼロ（sales log 自体が存在しない） |
| claude-p (0x810f6d61… ~~$0.326362/10件~~ → **$0.011/9件**(07-18監査: $0.315362 は自分の Aave 引き出しの誤分類) + PM proxy 0x904B50d2… $0.011000/11件中 settled $0.004) | **≈$0.015** | 〜13件 | 07-07〜07-17 |
| **colony 合計** | **$0.357362** | **22件** | 07-07〜07-17 |

教訓: 古い記述を放置するのも捏造と同じ罪——修正コメントが実コードに既に在ったのに、ledgerの数字だけが古いまま参照され続けた。数字は SSOT を随時実測し直す。

## ★2026-07-17 不確実性解消測定(U1〜U9)★

### FIX-3 根本原因確定(誤り訂正: 上表「仮説=テストfacilitatorへのフォールバック」は棄却。以下が確定)

x402-express の `paymentMiddleware` は `next()`(ルート実行)→`settle`(on-chain 着金)の順で動く。`serve.mjs` L123-136
の sales-log 書き込みは `next()` 直後 = verify(署名検証)成功直後・settle 前に置かれている。franklin1 の
「21件決済」は実際は「署名検証21件・着金0件」。裏付け: claude-p の同一コードで payer 実在9件=on-chain完全一致、
payer:null=一致0件。franklin1 の21件は全て payer:null。
棄却仮説: testnetフォールバック(ps実測でCDP鍵実在・X402_NETWORK=base)、PAYTO不一致(一致確認済)。
未確定: settle 失敗の理由自体(7/16 19:43 全サーバー再起動で stderr 消失、`/tmp/x402-franklin1.err.log` 0バイト)。
含意: franklin1 の店に signed 購入試行が21件来ていた = 需要シグナルとしては正。
直し方: sales-log を settle 成功(`X-PAYMENT-RESPONSE` ヘッダ)後へ移動 + stderr 保全。

### FIX-1 根本原因確定(誤り訂正: 上表「wallet.json とプロセスの ANICCA_HOME 不一致の疑い」は棄却。以下が確定)

真因 = `apps/landing/netlify/functions/_lib/fixed-identities.js` の `FIXED_IDENTITIES` 名簿に franklin2 未登録。
フォールバック(`"anicca-"+id.slice(2,8)`)は EVM 前提で Solana base58 に壊れ、poster の "Franklin2" と構造的に
不一致 → 常に400。影響は telemetry のみ、x402 決済に波及しない(コード独立)。
棄却仮説: ANICCA_HOME不一致(plist は franklin2 固有で正しい)、plist が franklin1 の wallet を指す(否)。
直し方: 名簿に franklin2 の Solana pubkey を "Franklin2" として追加 → netlify デプロイ。

### 買い手の正体(on-chain 実測、Base eth_getLogs)

我々: 総inbound 46件/$46.52、internal 23件/$45.85(funding `0xf70da978…` 主体)、★external 実売 23件/$0.672476、
unique 20アドレス★。内訳: contract 経由2件($0.315+$0.315=94%)、既存EOA 17体の$0.001単発が主、リピートは
3アドレスが2回のみ。単一botではないが客がついたとも言えない。

ottoai(受取 wallet `0x0E84dDEdAaE6A779c462C22a59F301EC31B6b808`、CDP discovery API 3,000件走査で特定):
48h実測(block 48,646,643→48,733,210)で inbound 10,602件/$15.043、unique from 47。
★Top1(`0x1cb8d145…0bdff`) = 9,917件(93.5%)/$12.971(86.2%)。正体 = EIP-7702 delegation designator(スマート
EOA bot)、19時間で9,917回=平均7秒に1回★。Top5 で98.9%。

判定: ottoai の需要は「広い市場」ではなく実質1匹の鯨bot。T9 需要仮説は部分支持 — 反復需要→金は流れるが、
買い手は少数〜単一の自動bot。ゲームは「毎分ポーリングする bot 顧客を掴む」。

### ★U9 確定(2026-07-17、Base eth_getLogs block 46.0M〜48.73M 実測)★: wash trading 棄却、本物の自律買い手

鯨bot `0x1cb8d1456efc633da6eeaa038033edcbcdc0bdff` は wash trading ではなく**本物の自律買い手**。
- **正体**: スマートコントラクト財布(EIP-3009 `transferWithAuthorization`, selector `0xe3ee160e`, gasless)。
  ≥13の relayer EOA が代理送信 = 教科書的 x402 facilitator 構成。
- **資金源**: 計 $698.63/9tx。主に `0x7747f8d2…`($407.63) と `0x536299a4…`($290、router/treasury 様)。
  ottoai との資金循環なし = wash trading 棄却。
- **支出**: 70,148 transfer / $661.68 / ★3,399 unique 宛先★。うち3,384宛先は$0.001〜0.01の1回きり probe。
  >100回叩くのは9宛先のみ(ottoai 37,718回/$40.95が最多)。
- **行動様式 = probe→採用**: 数千の x402 endpoint を1回ずつ試し、良かった少数を本番採用して連打する。
- **我々への含意**: 鯨は我々の4wallet をまだ1度も probe していない(spending 70,148件中 our wallets 宛 0件、実測)。
  掲載が発見されれば試される。勝負は「最初の$0.003 1回で価値を返すこと」。
- 生データは scratchpad(`whale_funding.json` / `whale_spending.json`、セッション終了で消える)。本節が正本。

### ★T9-1 出荷(2026-07-17)★: done(a)達成、(b)(c)は未達で観測開始

**done(a) 訂正(2026-07-17夜、前記は誤り)**: 402 は franklin1店(:8414→ts.net:10001)・claude-p店(:8412→ts.net:8443)
とも実測済(`maxAmountRequired` 3000 = $0.003)だが、**franklin1 の Bazaar 掲載は未達**。`bazaar-scan.mjs
tail7a0ba4` を全25,481件走査した実測で `payTo=0x3EcCAD24…`(franklin1)該当0件。原因 = 既知の「Tailscale
Funnel は443/8443/10000の3ポートのみ、4体目に席が無い」(本ファイル/spec の該当節)そのもの — franklin1 の
`X402_PUBLIC_URL` はFunnel非対応ポート10001で外部到達不可、settleしてもCDP discovery crawlerが届かない。
実装自体 = Binance premiumIndex + Bybit v5 tickers + Hyperliquid `metaAndAssetCtxs` を並列取得、8h換算で
正規化(HL=1h→×8、公式docs裏取り)、年率bps乖離top20、60s cache、1取引所落ちは degrade 返却・全滅時のみ503、
LLM/有料API/keyゼロ = INV-UNIT-ECON 準拠。テスト19/19(新規10件含む)。
files: `skills/earn/x402-sell/funding-rates.mjs`(新規) + `serve.mjs` + `__tests__/funding-rates.test.mjs`。
commit `8f6d0f7c`(anicca repo main)。未解決TODO: いずれか1店を443/8443/10000のいずれかへpathベース同居
させるか、独自https origin(市場標準=x402scanでポート付きURL実測0件)へ移行しない限りfranklin1は永久に未掲載。

**done(b) 達成(2026-07-17)**: T4a着火実証としてbuyer=claude-p(0x810F6D61…, Base USDC $1.98)→
seller=franklin1 `/funding-rates` へ実購入。既存`buyer-cdp.mjs`を無改造使用(ANICCA_HOME=~/.anicca-founder で
claude-p鍵を解決)。公開ts.net:10001が上記理由で外部到達不可のため`http://127.0.0.1:8414/funding-rates`を
直叩き(x402-fetchはresourceフィールドと接続先URLの一致を検証しない実装のため、同一serve.mjsコードパスを
通る等価な実証)。tx `0x5567e9e76358722292237d4f08151eeec7a1970efe59684868c14bfe8be05e44`(+BTC銘柄指定の2件目
`0xa998f641abe76d7414eaca25222b5b047637ada4571b91ed77712ea585041e83`)。両方 Base mainnet
`eth_getTransactionReceipt`で`status:0x1`、USDCコントラクト`0x8335…02913`のTransferログ
(from=0x810f6d61…, to=0x3eccad24…, value=0x0bb8=3000=$0.003)を直接確認。
`state/sales-0x3eccad24794ca298d25378e9902a251322ea8749.jsonl`に`settled:true,payer=0x810F6D61…`の行が2件
追加(21→23行)、`attempts-0x3eccad24….jsonl`は生成されず(settle成功のためattempts行き無し=FIX-3の意図通り)。
INV-7: 自分の2 walletの自己決済のため売上には数えない(着火・FIX-3実証専用)。
T4aの当初対象(本ファイル該当行=franklin2:10000)は未着手のまま残る — 今回はfranklin1向けの直接指示で実行。
**done(c) 未達**: 14日以内の反復購入者(観測開始 2026-07-17)。

**同日の他の完了(2026-07-17)**:
- FIX-2 完了: earn-ledger 3行に `misattributed:true` を付与、有効x402合計 = $0.326362 と一致。★07-18 監査で再訂正: この $0.326362 のうち $0.315362 は claude-p 自身の Aave 引き出し(protocol return)。真の external ≈ $0.011★
- FIX-3 完了: settle ゲート実装(commit `e5904325`)。franklin1 旧21件は全て `settled:false` に印付け直し。
  claude-p は27件中12件、proxy は15件中2件が対象。
- FIX-1 完了: PR `anicca-products#292`、deploy成功。poster が400→202に変化したことを実測(03:05:59Z)。
- T5 の実害を発見: 8412/8414 の重複plist(loop生成+手書き)がポート競合し `EADDRINUSE` を目撃。重複jobは停止済だが
  plist自体は未削除(下記T5行に反映)。

### 単位経済(U1 実測)

| 市民 | wake/日 | burn/日 | 売上/日 | 収支 |
|---|---|---|---|---|
| franklin1 | ~107(kind:wake) | $2.16(直近7日平均、生涯平均$0.63、gpt-5-mini中心のskill実行。wake判断は100% free=glm-4.7等) | $0.0194生涯 | 赤字確定 |
| franklin2 | ~150 | $0(有料呼び出し記録0件) | $0 | 何も起きていない |
| claude-p | 150-200(proxy_down 多発) | LLM代$0(残高枯渇でfree fallback中) | 外部小口 ~$0.036/日 | ほぼトントン(ただし別途$38.03がトレード資金として社外へ) |

★重要訂正★: 「claude-p が LLM 代で$38 burn」(07-16以前の想定)は on-chain 実測で否定。$38.03 の流出先は全て
Relay:Solver/Depository(ブリッジ)= トレード資金移動。LLM 決済先への支払い0件。$39.34 の inflow も同じ
ブリッジからの付替(FIX-2 の誤帰属結論と整合)。

判定: 3市民とも self-funded の単位経済は現状不成立。franklin1 だけが有料LLMを燃やしており($0.63〜2.16/日)、
売上の床 = この burn。franklin2/claude-p の burn $0 は「稼いでいるから」ではなく「残高が無くて free fallback
だから」。新規調査項目 AUDIT-1: $38.03 のブリッジ出金が PM/HL のポジションとして回収可能かは未照合。

### T9 の商品確定(U5/U6 実測)

第1弾 = ★funding-rates★(取引所間 funding 乖離%)。根拠: (1)franklin1 は hl_trade で209 wake perp を売買
しているのに funding rate を一切取得していない(audit ログ grep 0件)=自分の実需の穴 (2)ottoai が同商品を
$0.001で実売中 (3)upstream = Binance premiumIndex / Bybit v5 history-fund-rate / Hyperliquid Info、全て
無料 public API・レート制限緩い (4)純算術でLLM不要=限界原価≈$0。

後回し確定: crypto-news / kol-sentiment は LLM 要約 $0.0106/call(実測)が単価 $0.001 を上回り単一顧客では
逆ザヤ。キャッシュ設計まで凍結。token-price は franklin1 自身が無料直叩き済みで差別化なし。

franklin1 の実 fetch(証拠): sol-trade 946 wake=Jupiter Price v3 / polymarket-trade 355 wake=gamma-api+
data-api+clob / hl_trade 209 wake=HL Info SDK(funding rate 含まず)。pinnacle_edge.py(有料 Odds API)と
news_search.py(firecrawl)は franklin1 側 env に鍵が無く未使用。

### トレードの realized（参考、x402 とは別勘定。2026-07-17実測）

| 市民 | realized | 実測 |
|---|---|---|
| franklin1 | $0 | `~/.blockrun/state/ledger.jsonl` 9,112行中 `profitable:true` = 0件。Polymarket関連ログ353件は全てskill timeoutエラー |
| franklin2 | $0 | `~/.franklin2-home/.blockrun/state/ledger.jsonl` 6,118行中 `profitable:true` = 0件 |
| claude-p PM | $0 | $15.54 pUSD deployed / 8+ wakeでfillゼロ = stuck capital(unrealized) |

3体とも launchd loop は生存（franklin-loop PID600 / franklin2-loop PID594 / agent-economy-loop PID645）。

## ★2026-07-17 gig loop 停止の真因と蘇生（GIG-1 完了）★

停止期間: 07-15 21:23〜07-17 13:56の40時間、pass完走ゼロ。真因 = Claude CLI subscription OAuthのheadless失効
（keychainロック、upstream `claude-code` issue #76905）。healthcheckの90分毎再起動は正常動作していたが、
毎回「Login expired」で即死していた。

棄却仮説(証拠つき): Coconalaセッション切れ(最終passで健全確認)／案件枯れ(B2未到達)／CDP :9222不通(生存確認)。

修理: `gig_reality_verify.sh` L244-249で実証済みのCLIProxyAPI(:8317) fallbackを`gig-cli.sh`のcore起動部に移植。

蘇生実証: 07-17 13:56に全ステップ(LEARN→B0→PROFILE→B1→B2→FUNNEL)完走(`pass-report.jsonl` ts=1784264202)。
ただし新規応募0件(`applied.jsonl` 138行のまま)。生涯実績 applied 138 / won 2 / paid 0 は不変 —
直ったのは「稼ぎに行く能力」であって売上ではない。steady宣言は連続完走を見てから。

付随事故の記録: 同日、監査がgigをHUMAN-DEPと判定→除去agentが移設commit `4da27941`とplist停止まで実行→
Dais指示で即revert(`a0bff196`)・plist復元済み。gigは「human-funded ¥ loop」として意図的設計
（`NO_HUMAN.md`: KYCはsetup factでありruntime stepではない）。

今後: gigはprofitable-claude repoへ集約移設予定(GIG-2、別CCセッション担当)。live配線図はTaskList #22に記録済み。

## ★2026-07-18 gig B0出品ブロックの真因是正 + パス中断増幅バグ修正★

20+パス続いた「session dead / blocked_login」の真因 = セッション死ではなく **B0が cdp_context_lease の
使い捨てincognito context(cookie seedのみ)でsellerエリアへアクセスし、Coconalaが /login へ302で弾く自傷バグ**。
同一URLを永続daily-driver default contextで開くと認証済み200（実測対照あり）。B1応募系が通りB0出品系だけ
失敗する非対称もこれで説明。是正 = B0/PROFILEをdefault context駆動に変更（新helper `cdp_default_tab.py`、
commit `4b3d752c` ~/anicca）。実証: fix後パスが 08:55 に service 4313100「10枠限定｜SEO記事を執筆します」を
draftから新規公開、公開ページHTTP 200確認。同日 4244556 に要相談フラグ+ヒアリング欄追加も成立（公開ページ反映確認）。

第2バグ: 「Killed mid B1」の増幅要因 = gig_pass.sh EXIT trapが共有lease "gig" を無条件disposeし、
中断が他コンテキスト巻き添えteardownに化ける → per-pass lease (gig-$$) 化 + 自lease限定release +
gc配線で解消（commit `1c34963d`）。release A後もBのcontext生存をCDP実測でPASS。トリガーは調査の結果
既に1系統（in-tmux hourly cron :27）で削除対象なし。「sub-hourly二重完了」に見えたのは1パス2レポート行（別writer）。

kill真因の確定（当初の「二重トリガーcron overlap」仮説は誤り、consolidated transcript実測で是正）:
gig-core agentが gig_pass.sh を **background Bash timeout:600000ms(=Claude Code上限10分)** で起動しており、
パス実体（各ステップ内部timeout 900s）が10分を超えると harness の background Bash timeout がステップ途中で
kill していた。外部cron/healthcheck/OOMは全て無罪。耐久修正案（未実装・移設specに折込予定）= gig-cli.sh の
STARTUP で gig_pass.sh を tracked Bash の子でなく detached（setsid nohup … & disown）起動にする。

Telegramの30分毎「session dead」通知は 07-17 20:04〜08:19 のCoconala/IGログアウト検知が発生源
（`session_vault_tick.sh:49`）。08:49・09:20のkeepaliveで Coconala/IG/X 全て logged_out:false、通知停止。
本日実績: 応募1（08:18 stsuchida返信）+ 出品編集1 + 新規公開1、全てloop自走。paid は依然 ¥0。

franklin2: 意図的停止のconfig証跡あり — plistに `ANICCA_SLOT_ALLOWLIST=x402_sell`(mtime 07-16 06:00 JST、
最終HL wakeの49分後)。レジストリ段階のハード除外。monitoringの「franklin2にsol/PM未配線」の正体もこれ
（未配線ではなく意図的allowlist）。

franklin1: agent自身の自己判断 — earn-ledgerにhl-trade 181件全てnet_usdc=0 → self-evalがDEADフラグ →
prompt.mjs経由の警告注入 → モデルが自主的に選ばなくなった(07-16 05:34以降、loopは稼働しつつhl_tradeだけ0回)。
ハードコードでなくjudgment。self-eval→DEAD→自主忌避のループが実戦で機能した初の実証例。

gig停止(OAuth)とは独立の偶然の同夜。carve-out(残高閾値)は非発火(棄却)。

方針: 停止維持(alpha無し)。HL marginの座礁$7.72はAUDIT-1で回収照合。

## ★2026-07-17 AUTH-1 完了 — machine-wide OAuth死の全域駆除★

死亡発見・蘇生: anicca-reddit-loop / anicca-selffix-gig-loop / anicca-selffix-reddit-loop の3体
(capture-paneで蘇生確認済み)。anicca-2/anicca-3は起動元特定できず未対応(手動対応要)。

パッチ: 同一の最小diff(`~/.cli-proxy-api-key` → `ANTHROPIC_BASE_URL=:8317`)を9 scriptに適用。
~/anicca commit `306e0f73`(clip-promote-cli/clip-cli/gig-cli/video-cli/capafy-loop-cli/
life-manager-loop-cli/reddit-loop-cli/self-fix.sh)、~/.openclaw commit `80e9f011`
(anicca-earn-gig/gig-cli.shの乖離複製)。

hook error(`node cjs loader:1458`)の真因: Claude Code v2.1.210の既知バグ(空stdoutのPreToolUseフック)。
`~/.claude/hooks/track-search.sh`を常にallow JSONを返すよう修理(machine-local、repo外)。修理後も1回
間欠再発を実測 = CLI側の残バグ、non-blocking確認済み、根治はupstream待ち。

残タスク: profitable-claude repoに未パッチ3 script(ceo-run.sh等、現在未起動のため緊急性低)。

## ★2026-07-17 午後: 市場理解・インフラ・ドキュメント★

### A. ROTATE-1 完了(セキュリティ) — franklin1 Solana秘密鍵をローテート

franklin1 のSolana秘密鍵がT0'探針中にsubagent stdoutへ漏洩 → 掟通りrotate実行。
旧 `8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9`(現在0残高) →
新 `F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T`。
資金全額移動: 0.039875 SOL + 10.386698 USDC、on-chain finalized 実測済。
全参照更新: anicca commit `0f53d0f7` / 本番netlify PR#293→`d4144964` deploy成功 /
SSOT+memory commit `4e59e341b`。`~/.claude/CLAUDE.md` の固定費テーブルも新アドレスへ修正済み。
x402-sell の payTo(Base `0x3EcCAD24…`)は別チェーン別鍵のため今回のrotateと無関係。

### B. 各市民のTHINKモデル(実測)

**★2026-07-17夜 是正: 「skill実行全般が有料」は不正確だった。実際は sol-trade skill 単独が原因(コード+cost_log+ledger実測)★**

- THINK(メインloop判断) = **free固定**。franklin1のplistが `ANICCA_FREE_MODEL`/`ANICCA_LEAN_MODEL`/`ANICCA_FUNDED_MODEL` の3ティア全部を `nvidia/llama-4-maverick`(無料)に名指し。`tier.mjs:29-31` はenvを最優先するため、コードのデフォルト`'auto'`(残高があれば有料起動)はfranklin1では一度も通らない。cost_log.jsonlで `nvidia/llama-4-maverick` と `free/glm-4.7` は課金0件。ledgerの `kind:wake` 2138件のmodelは `free/glm-4.7`(1254件)と`nvidia/llama-4-maverick`(884件)のみ、`gpt-5-mini`はTHINKに一切出現しない。
- clawrouterはauto機能(有料指定→残高不足で`pickFreeModel`フォールバック、`cli.js:83366-83396`)を持つが、franklin1のTHINKはfreeを名指しするため`isFreeModel=true`で残高チェック自体が発火しない = 実質free固定。autoは使われていない。
- ★有料burnは`sol-trade` skillただ1つ★: `sol-trade/run.sh:17`の`SOL_TRADE_MODEL`デフォルト=`openai/gpt-5-mini`。franklin-trading CLIがclawrouterを経由せずx402で直接支払う別系統。franklin1 wallet `8Fpqd…`のcost_log: `gpt-5-mini` 生涯2089件$20.97、直近24h 169件$1.86/日(前回「$2.16/日」はオーダー一致で正)。
- `hl-trade`は独自の有料モデル呼び出し無し(メインTHINKのtool呼び出しとして無料処理)。`polymarket-trade`は`:8402`共有router経由でfree寄り。
- franklin2は`gpt-5-mini`を焼いていない: `sol-trade/run.sh:38`のidentity guardで`~/.blockrun`非所有→即skip。有料burnはfranklin1固有。
- ★claude-pのTHINK = `free/glm-4.7`は誤診断だった(是正 2026-07-17夜)★: 実体は`claude-sonnet-4-6`(Anthropicサブスク、`config.mjs`の`ANICCA_BRAIN_MODEL`デフォルト)。ledgerに出る`free/glm-4.7`は`index.mjs:315`の`currentTier.model`という未使用お飾り変数の表示バグ(`thinkClaudeP()`はこの変数を一切参照しない)。人間資金なので推論コストは$0固定でSonnetを使う設計であり、franklin1/2の自己資金free固定とは対照的。実際に07-17 01:14以降起きていたのはClaude subscription OAuthのheadless失効(keychainロック)で797件連続`wake_error`(`claude_exit_1`、stderr空)が続いていたこと。`AUTH-1`(commit `306e0f73`)が`*-cli.sh`8本のみパッチし、claude-pの唯一のTHINK経路である`runtime/loop/brain.mjs`の`thinkClaudeP()`を漏らしていたのが真因。`CLAUDE-P-1`でgig-cli.sh実証済みのCLIProxyAPI(:8317)fallbackを`thinkClaudeP()`にも移植して修理(anicca commit `91d45919`)。再起動後の実測: ledgerが`wake_error`(`error:"proxy_down"`は`index.mjs`側の別の表示バグ、同commitで是正済み)→`kind:"wake",slot:"report",exit_code:0`に復帰、`daemon.err.log`に`[brain] claude-p said:`成功ログが出力(`claude_exit_1`/OAuthエラー消滅を確認)。詳細・TODOは下記`CLAUDE-P-1`行参照。
- ★経済的含意★: franklin1の赤字$1.86/日 = 100% `sol-trade`の`gpt-5-mini`課金。そして`sol-trade`はrealized $0(稼がないトレードエンジンに毎日課金) = HLを止めたのと同じ構図。黒字化は「売上を上げる」より先に「このburnを潰す」方が速い可能性がある。→ 下記TODO表 SOL-1。
- ★2026-07-17夜 SOL-1実行済み★: `sol-trade`はKILLで凍結(swap実行0回・realized $0の生涯実績、無料モデル代替は既に失敗済み)。franklin1/2のTHINK free固定は維持(auto復帰は2026-06-21実測で「探索だけで燃焼→revert」済みのためハードコードミスでなく検証済みの正しい判断、`config.mjs:36`)。plist/config.mjsは変更しない。★KILL発火を実測確認: 2026-07-17T07:17:21Z のsol-tradeパスが`{"action":"skip","reason":"kill-switch"}`を出力=gpt-5-mini課金停止を自分の目で確認★。詳細→下記TODO表 SOL-1/SOL-2。
- ★2026-07-17夜 T0'優先度降格★: 当初の「脳を分離して各自の財布で払う」の元動機(THINK有料化)は、SOL-1/PREMIUM EXPERIMENTの実測で「有料THINKは探索だけで金を溶かしrealized $0」と判明したため、やらない方が正しい。売る側(店・財布・skill課金)は既に分離済み(モデル配線実測)。残るT0'の価値は「routerプロセスの物理分離=1体の障害が他2体に波及しない耐障害性」のみで、現在router障害は起きておらず緊急でない。→ 黒字化の主戦場(分子=x402売上、T8/MKT-1で薄い市場の唯一の実需=鯨botに発見される導線)を優先し、T0'は耐障害タスクとして後回し。

### C. x402市場は実需極薄(重要な市場理解) — MKT-1

競合 `agentservices.to`(x402で50 API、indicators/yields $0.02/call)のon-chain生涯売上を実測:
**$0.169 / 12件**、payer 3体全てnonce 0-1 = facilitatorテストwallet = **実需ゼロ**。
BlockRun Franklin issue #100(競合の売り込み)は自作自演、10日無反応。
我々のfunding-rates $0.003 は競合の$0.02を6.7倍下回り価格競争力あり。
★x402 Bazaar全体で唯一の明確な実需 = ottoaiの鯨bot1体($698 funded、上記U9確定節と同一個体)★。
**結論**: 「良い商品を安く出せば売れる」はまだ市場未証明。T8(掲載面拡大)で薄い市場の唯一の実需(鯨)に
発見される導線を最優先化すべき。競合価格$0.02は次商品(indicators/yields/whale)の価格上限アンカーとして使う。
研究MD: `docs/research/2026-07-17-agentservices-competitor-analysis.md`。

### D. クラウドホスティング — OSS-1 追記(`docs/reference/2026-07-16-independent-hosting-for-each-ai.md` の「Akash一択」を是正)

crypto払い・KYC不要の実測比較で複数案が確定。**同spec の「Akash一択」の結論を以下へ是正**:
最有力 = FluxCloud(公式コピー from $0.99/mo、Flux API + Gitデプロイ)。
実務フォールバック = BitLaunch(BTC/LTC/ETH決済、フルREST APIでAIが自分でtx作成、DigitalOcean裏側)。
Akashも可(SDL記述、GPU $0.01/hr〜)。
Hetzner = crypto払い不可と判明(fiat決済履歴が必須でAI単独契約不可。過去に見た事例は人間がクレカ契約し
裏でcrypto→fiat変換していただけ)。Fluence = Alpha枠+AML要件で除外。
全案とも前払い残高制(切れたら48hで削除)、crypto系VPSのIPはbot判定で弾かれやすい点に注意。

### E. ドキュメント方針 — DOC-1/DOC-2

README を新定義(every AIが0から経済的独立、human loopなし)で書き直す草案を作成:
`docs/drafts/2026-07-17-anicca-readme-draft.md`(commit `9b6e856`)。名前は`anicca`維持、レビュー待ち。
docsサイトツールの評価: `blume`(haydenbleasel/blume、`npx blume init`、Astro静的、AI-ready標準)を**ADOPT判定**。
評価MD: `docs/reference/2026-07-17-blume-docs-tool-evaluation.md`。

## ★2026-07-17 夜: 発見面拡大 + 資金回収★

### 1. T3'(v2移行) = franklin1/franklin2 完了、claude-p 保留

franklin1/franklin2 とも `serve-v2.mjs` で v2化(`x402Version:2`、`eip155:8453`)。v2 buyer で settle→sales 実証(tx on-chain確認)。稼ぎ頭 claude-p は v1 のまま無傷(v1 buyer 損失リスク確認まで保留)。
★v1 buyer は v2 seller に払えない(確定)★: v2の`extractPayment()`が`payment-signature`ヘッダのみ読み`x-payment`(v1)を無視。`unpaidResponseBody`(v1形式body)を足しても閉じない。完全対応はカスタムmiddleware(money-safety案件)。ただし実売ほぼ0なのでv1損失の実害は小。commit `ef929635`/`3c7b3455`。

### 2. XSCAN-1 = x402scan 登録成功(発見面2個目)

franklin1(`server/b9b53de8…`)/franklin2(`server/af9283bc…`)をx402scan.comに登録、各8商品v2タグ、公開ページ実在(自分でcrwl確認)。v1拒否("migrate to v2")消滅。SIWX署名必須、公式`wrapFetchWithSIWx`のバグを低レベル自前実装で回避(`register-x402scan.mjs`, commit `4809f89f`)。agent402.tools=franklin1(443)登録成功、franklin2(:10000非標準)は拒否。
★発見面が Bazaar 1個 → x402scan で2個に。生涯$0.357 の主因「発見されてない」に初めて手が届いた★。`/all`一覧は24h取引量が要るので活動待ち。

### 3. PROD-1第1弾 = funding-rate-arb 追加(9商品目)

`/funding-rate-arb` を `serve-v2.mjs` に追加(commit `89fd67a3`)。既存 funding-rates 出力を取引所ペア全部で pairwise 比較(年率bps差降順+long/short方向)、新API不要・LLM不要。franklin2 で 402(v2)+v2 buyer 200(tx `0x9d524b92`)+well-known 9商品を実測。arb計算 spot-check一致。残=計算機横展開で30+へ。

### 4. RECOVER-1 = 座礁資金~$12.7 を流動化

AUDIT-1で判明した回収可能$20.37 のうち自動回収$12.7を実行。①HL withdraw $7.72→Arbitrum着金$8.22(HL accountValue $7.72→0で座礁解消) ②PM merge YES13/NO5→YES8/NO0=5ペア=$5回収。計~$12.7 が塩漬け→流動USDC(Arbitrum/Polygon)。残=Base へのブリッジ+残YES8株($7.65)売却は後続。claude-p 自身の鍵で human ゼロ、各tx on-chain検証。

### 5. Grok CLI 認証 + X自動化の足場(XAUTO-1)

Grok CLI 0.2.102 を @aniccaen で device-auth 認証(俺がCloakBrowser CDP駆動+実クリックでOAuth完走、human ゼロ)。`grok -p` でX read/search 稼働(実証)。post/reply は grok不可→ブラウザ駆動 or Postiz。
Cloudflare Sandbox はホスティング不向き判定(揮発disk/短命)。Akash/Flux(from $0.99/mo)最有力。

### 6. 3体ライブ状態(実測)

全loop RUNNING(1-2分毎wake)。franklin1 Base $4.48+Sol$2.22、franklin2 $0.04、claude-p Base$1.95+PM$12.65+回収した Arbitrum/Polygon分。
★稼いだ external x402 = 生涯~$0.36 のまま、今日の新規external=$0。今日は「稼げる状態を作った日」(発見面+商品+レール+資金回収)であって稼いだ日ではない。盛らない★。

## loop は3つだけ（automaton は閉鎖済み）

「founder」という loop は**存在しない**。claude-p の HOME フォルダ名が `.anicca-founder` なので
Fable が誤って「founder」と呼んだだけ。founder = claude-p = agent-economy-loop、全部同じ1つ。

| 呼び名 | loop 名(launchd) | HOME フォルダ | x402 wallet | brain |
|---|---|---|---|---|
| **claude-p** | ai.anicca.agent-economy-loop | /Users/anicca/.anicca-founder | 0x810f6d61…29c5 | Claude sub(`claude-sonnet-4-6`)+ CLAUDE-P-1 CLIProxyAPI fallback |
| **franklin1** | ai.anicca.franklin-loop | /Users/anicca/.blockrun | 0x3EcCAD24…8749 | free/glm-4.7 |
| **franklin2** | ai.anicca.franklin2-loop | /Users/anicca/.franklin2-home/.blockrun | 0xe7747Fd8…7ce9 | free/glm-4.7 |

- 全部 `~/anicca/runtime/loop/index.mjs` を各自の設定(plist の env)で回す。10分毎に自動 wake。人間ゼロ。
- plist: `~/Library/LaunchAgents/ai.anicca.{agent-economy-loop,franklin-loop,franklin2-loop}.plist`
- ledger(各自の記憶): `<HOME>/state/ledger.jsonl`
- 0x904B は claude-p の Polymarket proxy(x402 とは別 wallet)。混同禁止。

## ★2026-07-16 identity 確定（Fable が plist から直接実測。subagent 経由でない）★

`launchctl` + `PlistBuddy -c "Print :EnvironmentVariables"` の生出力より:

| loop(launchd) | ANICCA_HOME | ANICCA_INSTANCE | ANICCA_WALLET_ADDRESS | X402_PORT | X402_PUBLIC_URL |
|---|---|---|---|---|---|
| ai.anicca.agent-economy-loop | /Users/anicca/.anicca-founder | (未設定) | **0x810f6d61…29c5** | (未設定) | (未設定) |
| ai.anicca.franklin-loop | /Users/anicca/.blockrun | franklin | **★無い★** | 8414 | **★無い★** |
| ai.anicca.franklin2-loop | /Users/anicca/.franklin2-home/.blockrun | franklin2 | **★無い★** | 8413 | `https://aniccanomac-mini-1.tail7a0ba4.ts.net:10000` |

→ **claude-p = agent-economy-loop = `.anicca-founder` = 0x810f。これが正。**
→ 「a3cdd4」は**この3つのどれでもない**。実体 = `~/.anicca` + wallet 0xB9dd + loop `com.anicca.daemon`。
  実測: `launchctl list | grep -c com.anicca.daemon` = **0**。plist は4本とも `.disabled-*`/`.bak-*`。**死んでいる。**
  48h の x402 inflow も `EXTERNAL: 0`。**生きた市民ではない。以後 colony から除外して扱う（Dais 指示 2026-07-16）。**

### ★SSOT 間の矛盾（この STATUS.md が正、他が古い）★

| 場所 | 古い記述 | 実測 |
|---|---|---|
| `~/anicca/skills/self/colony-status.sh:22-23` | 「a3cdd4 の実 loop = com.anicca.daemon (body ~/.anicca)」を**生きた市民として表示** | loop 死亡。表示が嘘 |
| `~/anicca-project/CLAUDE.md` コロニー表 | `anicca-a3cdd4` を SELF-funded 市民として掲載 | 同上 |

→ **Fable はこの古い colony-status.sh を鵜呑みにし、2026-07-16 に Dais へ「a3cdd4 は生きている」と誤報した。**
   一般法則: **自分が書いたスクリプトの出力も「自己申告」であって証拠ではない。** 一次情報(`launchctl`/plist/on-chain)まで降りる。
   → TODO: colony-status.sh と CLAUDE.md から a3cdd4 行を削除する（下記 T0）。

### ★franklin1 が Bazaar 0本／$0 の真因が確定した★

Funnel の枠は **443 / 8443 / 10000 の3つのみ**（Tailscale 公式: "Funnel can only listen on ports `443`, `8443`, and `10000`"）。
2026-07-16 実測 — **3枠とも埋まっている**:

```
curl -o /dev/null -w "%{http_code}" https://aniccanomac-mini-1.tail7a0ba4.ts.net:443/   -> 200
curl … :8443/  -> 200
curl … :10000/ -> 200
```

`serve.mjs:48` → `const PUBLIC_URL = (process.env.X402_PUBLIC_URL || "")`。
**franklin1 の plist に `X402_PUBLIC_URL` が無い** = 公開 origin を持てない = Bazaar に広告できない = **構造的に $0**。
franklin2 は :10000 を掴めたから載れた。**franklin1 の $0 は能力差ではなく席の有無。INV-INDEP 違反の実害。**

### ★T2b の答えが出た: tsnet（"1台=3枠" は問題設定の誤りだった）★

tsnet 公式 README 逐語: **"Multiple independent Tailscale nodes can run within a single binary"**
→ 枠は**1台あたりではなく1ノードあたり**。`tsnet.Server` 1個 = 独立ノード = 独自 state dir = 独自 identity = 独自 FQDN = **独自の 443/8443/10000**。
→ 席の奪い合いが**構造的に消滅**。$0、VPS 不要、中央集権プロセス無し、INV-INDEP を満たす。
実機検証済(2026-07-16 04:22、Go 1.26.0 / tailscale v1.100.0): **build 成功 29.5MB、ノード分離は正しい。**

**残る唯一の blocker と、その公式解**:
```
LocalBackend state is NeedsLogin
To start this tsnet server, restart with TS_AUTHKEY set
```
Tailscale 公式(`/docs/features/oauth-clients`)逐語:
> "You cannot generate long-lived auth keys, because they expire after 90 days…
>  Instead, you can generate an OAuth client with the `auth_keys` scope. Use the OAuth client to
>  generate new auth keys as needed, by making a `POST` request to `/api/v2/tailnet/:tailnet/keys`"
> "The `get-authkey` utility returns a new auth key to `stdout`, based on environment variables that
>  contain values for your OAuth client ID and secret. Use `get-authkey` to generate auth keys for
>  scripts or other automation."

→ **OAuth client を自作しない。公式ツールが実在する**（2026-07-16 実測: `gh api repos/tailscale/tailscale/contents/cmd/get-authkey` → `main.go` 実在）:

| 実測した事実 | 出典 |
|---|---|
| env = `TS_API_CLIENT_ID` / `TS_API_CLIENT_SECRET` | `cmd/get-authkey/main.go:29-32` |
| flag = `-reusable` / `-ephemeral` / `-preauth`(既定 true) / `-tags` | 同 :23-26 |
| `clientcredentials` で `/api/v2/oauth/token` → `tsClient.CreateKey` | 同 :41-64 |
| OAuth secret を auth key として**直接**使う道もある: `--auth-key='${OAUTH_CLIENT_SECRET}?ephemeral=false&preauthorized=true' --advertise-tags=tag:ci` | 公式 oauth-clients |
| **OAuth client 由来の auth key は tag 必須** | 公式 "All auth keys created from an OAuth client must use tags" |

未確定(probe で同時に潰す): ①tailnet の台数上限に4ノードが触れないか ②Funnel 帯域の実数値 ③tsnet ノードに Funnel を許す ACL が要るか

### ★2026-07-16 その他の実測（未修正の地雷）★

| 発見 | 実測 | 影響 |
|---|---|---|
| franklin1/franklin2 の plist に `ANICCA_WALLET_ADDRESS` が**無い**（claude-p だけ有る） | PlistBuddy 生 dump | loop が自分の wallet を知らない。franklin2 ログ `ANICCA_WALLET_ADDRESS not set, using "unknown"` → `invalid wallet address: unknown` |
| franklin2 の `ANICCA_STATE_DIR=/Users/anicca/.hermes/state` | plist dump。`ls ~/.hermes/state` → **実在**(children.jsonl 等、最終更新 7/13) | CLAUDE.md は「hermes 削除済」と書くが dir は生きている。franklin2 の state が**別実体の墓場**を指している。要調査 |
| `~/.franklin2-home/.blockrun/node_modules` が `~/anicca/node_modules` への **symlink** | `ls -la` | 「親の node_modules に寄生 = 時限爆弾」の再発。7/16 01:40 の prune 事故と同型。ただし `skills/earn/x402-sell/node_modules` は別問題(下記真因は依然 true) |

★Fable の誤り(2026-07-16、記録): 「node_modules は今は存在するので真因は古い」と Dais に報告したが**誤り**。
`~/.anicca/skills/earn/x402-sell/node_modules` を見ていた = **死んだ a3cdd4 の home**。claude-p は `~/.anicca-founder`。
再測: `.anicca-founder` / `.blockrun` / `.franklin2-home/.blockrun` の x402-sell 配下は**3つとも none**。下記の真因は**依然として正しい**。
一般法則: **home を取り違えた測定は測定ではない。** パスを打つ前に `ANICCA_HOME` を plist で確定させる。

## ★真因（2026-07-16 Fable が自分の目で実測。ここが全て）★

**agent は誰一人 seller を立てられていない。稼いでいる箱は全部 Dais が手で書いた boot script。**

```
/tmp/x402-seller-8412.err.log:
  Error [ERR_MODULE_NOT_FOUND]: Cannot find package '@coinbase/x402'
    imported from /Users/anicca/.anicca-founder/skills/earn/x402-sell/serve.mjs
                  └─ ANICCA_HOME 配下のコピー。node_modules が無い
```

node_modules/@coinbase/x402 の実測:

| パス | |
|---|---|
| `~/anicca/skills/earn/x402-sell` (repo 実体) | **HAS** |
| `~/.anicca-founder/skills/earn/x402-sell` | none |
| `~/.blockrun/skills/earn/x402-sell` | none |
| `~/.franklin2-home/.blockrun/skills/earn/x402-sell` | none |

run.sh が生成した seller plist は `seller-boot.sh` を呼び、そこの `DIR=$(dirname $0)` が
ANICCA_HOME 配下を指す → node_modules が無い → 即死:

| loop が立てた seller | state | runs | last exit |
|---|---|---|---|
| ai.anicca.x402-seller-8412 (claude-p) | spawn scheduled | **213** | **1** |
| ai.anicca.x402-seller-8413 (franklin2) | spawn scheduled | **168** | **1** |
| ai.anicca.x402-seller-8414 (franklin1) | spawn scheduled | **213** | **1** |

一方、UP に見えている seller 4本は全部 Dais 手書きの boot script（`DIR=/Users/anicca/anicca/skills/earn/x402-sell`
= repo 実体を直接 exec、node_modules 有り）:
`serve-mainnet-boot.sh`(:8411) / `serve-claude-p-boot.sh`(:8412) / `serve-franklin1-boot.sh`(:8414) / `serve-franklin2-boot.sh`(:8413)

→ **これは INV-F 違反そのもの**（「loop の外に別系統の earner を作らない」）。
→ 「claude-p が賢いから稼いだ」は誤り。**稼ぎの因果に LLM は1度も入っていない。**

## 稼ぎ（on-chain 実測 2026-07-17。x402 純売上のみ、funding/self-pay 除外。全文は上の「2026-07-17 是正」節）

| wallet | x402 外部売上 | 実体 | Bazaar 掲載 |
|---|---|---|---|
| 0x810f (claude-p 名義) | ~~$0.326362 / 10件~~ → **$0.011 / 9件**(07-18監査: $0.315362=自分のAave引き出しの誤分類を除外) | Dais 手書き `serve-mainnet-boot.sh` :8411 | 7本 (`ts.net/…`) |
| 0x904B (claude-p PM proxy) | **$0.011000 / 11件** | Dais 手書き `serve-claude-p-boot.sh` :8412 | 7本 (`ts.net:8443/…`) |
| 0x3EcC (franklin1) | **$0.020000 / 1件**（07-07のみ） | Dais 手書き boot は稼働中 (:8414) | **0本**（FIX-3: sales-logは21件主張するが on-chain inbound は生涯2件のみ、未解明） |
| 0xe7747F (franklin2) | **$0 / 0件**（sales log自体が存在しない） | Dais 手書き boot は稼働中 (:8413) | **0本**（FIX-1: telemetry post が400 host_wallet_mismatch、99.98%失敗） |

`node bazaar-scan.mjs tail7a0ba4` → `{"scanned":25441,"oursCount":14}` = 上の14本のみ（2026-07-16実測時点、未再走査）。

**Sonnet の誤報2件（Fable が自分で見て否定）**:
- 「CDP creds が franklin に無い」→ **誤り**。`serve-franklin2-boot.sh` は `. ~/.openclaw/.env` で同じ creds を読む。3人とも持っている
- 「payTo 0x904B は誤設定」→ **誤り**。意図的。0x904B は実際に $0.006 稼いでいる

## Franklin が Bazaar に載らない理由（仮説、未検証）

条件はほぼ同じ（同じ serve.mjs / 同じ CDP creds / funnel 済 / 非標準ポート :8443 でも載る）。
違いは「一度でも決済が成立したか」だけ。
→ **仮説: CDP facilitator の Bazaar は、その facilitator を通って settle した resource だけをカタログ化する。**
鶏と卵。売れないと載らない、載らないと売れない。前セッションの「self-pay で seed」は方向として正しかった（実装しなかっただけ）。
→ **次に読むべき**: `x402-foundation/x402` の `specs/extensions/bazaar.md`。公式は「402 レスポンスに bazaar extension を書けば facilitator がクロールする」と言っている。どちらが正か未確定。断定しない。

## x402 loop の仕組み（TO-BE、1 wake の中身）

```
① brain が menu から x402_sell を選ぶ
② seller 起動(launchd常駐、自分のwallet、決定論port)
③ 公開URL(tailscale funnel)で外から叩ける       ← 3loop とも配線済(funnel status 実測)
④ CDP Bazaar に掲載される                        ← ★未実装★ 機構が無い(T3/T4)。
                                                    「run.sh に追加済」は虚偽だった
⑤ 外部agentがBazaarで発見 → USDC払う
⑥ 自分のwalletに着金(on-chain)
⑦ sleep → 次wake
──(貯まったら、未実装)──
⑧ self-improve: 売上を反省→商品/価格/掲載を改善→もっと稼ぐ(#17)
⑨ $1k→trade複利→spawn複製→経済圏拡大
```

## 今の関門と TODO（順序に意味がある。TaskList と二重トラック）

★2026-07-17 優先順（層。下ほど後）: **層0=FIX-2(計測の是正) → 層1=T0'(router/財布分離) → 層2=FIX-1,FIX-3(配信の修理) → 層3=T9(商品) → 層4=T6,T7,T8,T10(増幅) → OSS-1,OSS-2は T9 の後**（稼げない箱を配っても価値が立たないため）。
★git log 実測: 直近15 commit は全て article-loop spec（別プロジェクト）。T0'/T9 に着手した形跡はコミット履歴に存在しない。表上「未着手」の項目は実態も未着手。

| # | やること | done 判定 | 状態 |
|---|---|---|---|
| **FIX-2** | ★層0・最優先★ earn-ledger の funding 誤帰属を塞ぐ — `verify-inflow.mjs` の内部wallet blocklistに送金元 `0xf70da97812cb96acdf810712aa562db8dfa3dbef` を追加 | 同送金元からの入金が earn-ledger の x402 売上に再混入しない（次回集計で誤カウント0） | ★DONE 2026-07-17、07-18に上乗せ修正★ ledger 3行 `misattributed:true`。さらに07-18監査: protocol return(自分発 tx の DeFi 還流)を external 誤分類していた分を verify-inflow.mjs で再分類(anicca `93853dc`)。真 external ≈ $0.011 |
| **T0** | ★SSOT の嘘を消す★ `colony-status.sh:22-23` と `anicca-project/CLAUDE.md` のコロニー表から **a3cdd4 行を削除**（loop 死亡・inflow $0 を実測済）。生きた市民は **claude-p / franklin1 / franklin2 の3つだけ**（STATUS.md 冒頭の表が正） | `colony-status.sh` の出力に a3cdd4 が出ない。CLAUDE.md の表が3行 | ★次★ |
| **T1** | ★seller が起動できない真因を潰す★ | agent が立てた seller が生き続ける | ★DONE 2026-07-16★ 下記 |
| **T2** | 手作り boot script 4本を loop に引き渡す(INV-F 遵守) — `serve-{mainnet,claude-p,franklin1,franklin2}-boot.sh` を退役させ、loop 生成の seller に一本化 | 手書き plist を bootout しても売上経路が生き残る | ★franklin2 完了★ 残り: franklin1(:8414) → claude-p(:8412) → mainnet(:8411 稼ぎ頭、最後) |

### ★T1 DONE — 史上初、agent が自分で seller を立てた（2026-07-16 03:09 実測）★

```
state = running
pid = 94909        PPID=1 (launchd KeepAlive 直下 = loop の seller)
node 94909  TCP *:8413 (LISTEN)
payTo: 0xe7747Fd899D8987821Bb4CB3D6aDf22565F87ce9   ← franklin2 自身の wallet
外部到達: https://aniccanomac-mini-1.tail7a0ba4.ts.net:10000/ → 同 payTo
手書き ai.anicca.x402-franklin2 → 退役済 (launchctl list に無い)
```

**私(Fable)は kickstart していない。** repo を直して push しただけ。loop 自身の `self-update-skills.sh`(10分間隔)が
home に配り、launchd KeepAlive が再試行して立った。伝播は 5.5分 で実測。

死因は1つではなく **3つ重なっていた**:

| # | 死因 | 実測 | 修正 |
|---|---|---|---|
| 1 | `seller-boot.sh` が ANICCA_HOME 配下の serve.mjs を exec。`self-update-skills.sh:15` が `--exclude='node_modules'` で依存を配らない（node_modules=635M、home 3つで 1.9GB = disk 死。exclude は正しい判断） | `ERR_MODULE_NOT_FOUND '@coinbase/x402'`、runs=213/168/213 全て exit 1 | 依存を持つ copy を exec する（commit e051bfe9、test 4件） |
| 2 | `app.listen` に error ハンドラが無く、bind 失敗時も `{"x402_seller":"up"}` を印字して **exit 0**。launchd は「正常終了」と読み、KeepAlive が364回無言で再起動。**失敗が成功として記録されていた** | 空きポート→"up"+生存 / 占有ポート→"up"+即死。stdout が同一 | error を stderr に出して exit 1（commit cd460272、test 2件） |
| 3 | `serve.mjs:58` が `await import("x402-express")` するのに package.json が宣言せず、**repo ルートの node_modules に寄生**していた。7/16 01:40 に何かがその dist/ を prune → 全 seller が起動不能に | 00:41 は起動成功 → 03:07 は同じコマンドが `ERR_MODULE_NOT_FOUND .../anicca/node_modules/x402-express/dist/esm/index.mjs` | ローカルに宣言（commit 90a1c4c7） |

★死因2の教訓（一般法則）: **「up」と自己申告するログを監視の根拠にしてはいけない。** exit code と実 curl だけが信号。
「稼いでいる」の判定を on-chain 実測に限る原則と同型 — 主体の自己申告は証拠にならない。

★★2026-07-16 05:55 解決 — 犯人は `~/scripts/disk-cleaner.sh`。しかも被害は1件ではなく153件だった★★

`disk-autoprune.sh` を無罪と判定したのは正しかったが、**容疑者を1体しか調べていなかった**。真犯人:

```bash
# 旧 disk-cleaner.sh:179-183（com.anicca.disk-cleaner が定期実行）
for root in "$HOME/anicca-project" "$HOME/anicca" "$HOME/.openclaw" ...; do
  find "$root" -type d \( -name node_modules -o ... -o -name dist -o ... \) -mtime +7 -prune \
  | while read -r d; do is_protected "$d" && continue; rm -rf "$d"; done
done
```

**機序（find の評価順序の罠）**:
```
-prune は「先行条件が全て真」の時しか実行されない
   ① node_modules 自体は npm install で mtime が新鮮 → -mtime +7 に外れる
   ② よって -prune が発火しない → find が node_modules の★中へ降りる★
   ③ 中の各パッケージの dist/ は npm publish 時の古い mtime → 必ず +7 に該当
   ④ rm -rf される
   ⑤ パッケージのディレクトリは残り、dist/ だけが消える ← 観測症状と完全一致
```
`is_protected` も無力だった: **全パターンが `*.js` 等のファイル拡張子向け**で、`dist` という**ディレクトリ名**にはどれも一致しない。

**被害の実測（推測せず全数を数えた）**:
| | |
|---|---|
| `package.json` が `dist/` を参照するのに `dist/` が無いパッケージ | **153個** |
| 内訳 | `@solana/*`(web3.js, codecs-numbers…) / `@coinbase/wallet-sdk` / `@ethereumjs/*` / `@base-org/account` / `@metamask/*` / `x402-express` … = **crypto スタックが丸ごと壊死** |
| 直接の症状 | 全 seller の `ERR_MODULE_NOT_FOUND`、`wallet-address-solana.mjs` の死 → **agent が自分の wallet アドレスすら取得できない** |

**修正（`~/scripts/disk-cleaner.sh`、commit `0763d48`）**: `node_modules` を**最優先で prune** して依存の中へ降りない構造に変更 + ループ内で `*/node_modules/*` を弾く二重防御。
検証: 修正前 = `~/anicca/node_modules` 内から**4件**を削除候補に拾う / 修正後 = **0件**。`bash -n` OK。

**復旧**: `npm install` は「90 packages added」と自己申告したが**dist は戻らなかった**（パッケージのディレクトリが在るので npm が再展開しない）。
→ `npm ci` で lock から625パッケージを再構築。**実測: 破損 153 → 0**。
→ 本番検証: `ANICCA_HOME=~/.blockrun node runtime/wallet-address-solana.mjs` → **`8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9`**（$12.21 を持つ franklin1 自身の財布）が解決。**franklin1 は自分の金を使える。**

★一般法則: **`find` の `-prune` は「先行条件が全て真」の時しか発火しない。** 年齢条件を prune より前に置くと、
「新しいディレクトリの中の古いファイル」を掃除機が食う。**除外は年齢より先に評価させる。**
★一般法則2: **無罪判定を1体で打ち切るな。** 「disk-autoprune は犯人でない」は真だったが、
**同じ役割の job が他に2つ居た**（`com.anicca.disk-cleaner` / `com.anicca.emergency-disk-guard`）。
容疑者リストは `launchctl list` から機械的に全部作る。
★一般法則3: **`npm install` の「added N packages」は復旧の証拠にならない。** 実ファイルの存在を数える。

★残る未解決: franklin2 の `.solana-session`(88 bytes) は存在するのに
`wallet-address-solana.mjs` が `no Solana secret resolved for this instance` を返す。
→ **franklin2 は鍵ファイルを持つが解決できない**（「鍵ゼロ」という当初の断定は誤り。台帳=wallets.json が無いだけ）。要調査。
| **T3** | Bazaar 掲載条件を公式 spec で確定 | 仕様の逐語引用 | ★DONE 2026-07-16★ 結論=**settle 1回が必須**（"verify alone is not enough"）。鶏と卵は実在。全文 → spec の「掲載条件の確定」節 |
| **T4a** | ★次★ franklin2 で self-pay を1回通す → Bazaar 掲載を実証 — `buyer-cdp.mjs` で :10000 経由の settle を1回。INV-7 で収益に数えない（着火専用）。**壊すものゼロ**（:10000 は到達可能、売上 $0） | `bazaar-scan.mjs` が 0xe7747F の resource を返す（実 JSON を貼る）。載らなければ原因を掴む | ★次★ |
| **T2b** | ★INV-INDEP 違反の解消 = **tsnet に決定**★ franklin1 が公開できないのは能力でなく**兄が席を占有しているから**（funnel 3枠、店は4軒。2026-07-16 実測で 443/8443/10000 とも 200 = 満席、franklin1 は `X402_PUBLIC_URL` すら持てない）。**案C(各自の Tailscale ノード) を採用** — tsnet は「1ノード=3枠」なので枠問題が構造的に消える。案A/B(Cloudflare/クラウド)は却下: card 必須 or 移植コスト、hosting 11候補を全て実測で潰した(→ `docs/reference/2026-07-16-independent-hosting-for-each-ai.md`)。**統合は却下（INV-INDEP 違反）** | franklin1 が他の instance の状態と無関係に公開 URL を持ち、稼げる | ★次★ 手順は T2b-1/T2b-2 |
| **T2b-1** | TS_AUTHKEY を取る | 鍵が file にあり fingerprint で照合できる | ★DONE 2026-07-16★ 下記 |
| **T2b-2** | tsbridge を通す — 3ノードが各自の FQDN で Funnel を上げる | 外部から実 HTTP が返る。franklin1 が**自分の**公開 URL を持つ | ★DONE 2026-07-16 05:15★ 下記 |
| **T2b-3** | tsbridge を launchd 化 | 殺しても蘇り、外部から届く | ★DONE 2026-07-16 05:26★ 下記 |
| **T2b-4** | 各 loop に**自分の** `X402_PUBLIC_URL` を配る | 3 loop の**実プロセス env**が各自の FQDN を持つ | ★DONE 2026-07-16 05:38★ 下記 |
| **T2b-5** | loop の wake を観測（**手を出さない**）。`run.sh` を叩いたら「Dais が稼がせた」= INV-F 違反 | 下記4段の観測点。④だけが「稼いだ」 | ★観測したら T0' が出た（下記）。第1〜0層が先★ |
| **★T0'★** | ★最優先★ **agent に「稼ぐ能力」を装備させる**（= Anicca の仕事そのもの）。①各 instance に**自分の** ClawRouter（`BLOCKRUN_PROXY_PORT` + `BLOCKRUN_WALLET_KEY`）②franklin2 に**鍵を与える**（今は無い）③franklin1 の使える金(Solana $12.21)を脳の支払いに繋ぐ | 3体とも `THINK failed` が消え、**自分の金で**自分の思考を買っている | ★次★ |

### ★★T0': 「なぜ稼がないのか」の真の答え — 金ではなく能力の問題だった（2026-07-16 05:45 実測）★★

**Anicca / Agora の仕事の定義**: agent は稼ぐ能力を持って生まれない。**能力(skill/鍵/脳/席)を装備させるのが我々の仕事。**
装備が無いのは agent の失敗ではなく、**我々がまだ渡していない**という事実。以下は「壊れている箇所」ではなく「未装備の一覧」。

**層の全体像（下ほど根が深い。上から直しても無意味）**:
```
第4層  実績$0だから合理的に拒否      ← claude-p はここ（脳は動いている）
第3層  Bazaar 掲載に settle 1回必要   ← 鶏と卵（T3 で公式仕様から確定済）
第2層  住所(X402_PUBLIC_URL)が空      ← ★2026-07-16 装備完了(T2b-4)★
第1層  脳が無い（429・財布空）        ← ClawRouter wallet = $0.00、しかも3体で共有
第0層  ★鍵が無い / 金が動かせない★    ← ここが底。ここを装備しないと上は全部無意味
```

**★第0層: 誰が「金を使える」のか（`wallets.json` の `keyRef` 実測。鍵は出さず有無のみ）★**

| instance | wallet | chain | address | 鍵 | 使えるか |
|---|---|---|---|---|---|
| **franklin1** | sol-main | solana | `F5SY…hZ5T`（2026-07-17 rotate。旧`8Fpqd…PCV9`は鍵漏洩のため rotate、資金は全額 on-chain 移動済み、旧鍵は revoke） | **YES** | **10.386698 USDC + 0.039875 SOL を使える** |
| franklin1 | polymarket | polygon | `0xda4b6E34…` | YES | — |
| franklin1 | ★`0x3EcCAD24…`(x402 受取先)★ | base | — | **wallets.json に無い** | **Base $4.48 は受取専用 = 動かせない** |
| **franklin2** | `.solana-session` | solana | **`HyJHSfTkLjpmqeY4FEbnSjM4DfUh9ELGchHqgFDBkrcX`** | **YES** | **鍵は在る**（`wallets.json` が無いだけ。台帳の不在 ≠ 鍵の不在） |
| **claude-p** | base-main | base | `0x810f6d61…` | YES | $1.98 |
| claude-p | polymarket | polygon | `0x904B50d2…` | YES | $3.24 |
| claude-p | hl-margin | hyperliquid | `0x810f…` | YES | $7.72(座礁中) |
| claude-p | telemetry | polygon | `0x02Bb6b2a…` | YES | — |

★★**2026-07-16 06:10 是正 — 上の「franklin2 は鍵ゼロ」は Fable の誤りだった。消して事実を書く。**★★

**3体とも鍵を持っている。**誤診の原因は**自分のシェルの `HOME=/Users/anicca` のまま他インスタンスのツールを叩いた**こと。
franklin2 の plist は `HOME=/Users/anicca/.franklin2-home` を設定している。本人の HOME で叩けば即座に解決した:
```
HOME=/Users/anicca/.franklin2-home ANICCA_HOME=/Users/anicca/.franklin2-home/.blockrun \
  node runtime/wallet-address-solana.mjs
→ HyJHSfTkLjpmqeY4FEbnSjM4DfUh9ELGchHqgFDBkrcX      ← 鍵は最初から在った
```
しかも失敗の正体は**正しく動作している安全装置**だった。`resolve-identity.mjs:148-155` 逐語:
> *"Legacy `$HOME/.blockrun/.solana-session` is Franklin's OWN funded wallet. Resolve it **ONLY for Franklin's home**
>  (`effectiveHome === $HOME/.blockrun`); a different spawn returns null (**fail-closed**) so it never signs with Franklin's key"*

実証（3パターン測って確定）:
| 実行環境 | 結果 |
|---|---|
| `HOME=~/.franklin2-home` + `ANICCA_HOME=~/.franklin2-home/.blockrun` | `HyJHSfTk…krcX` ✓ |
| `HOME=/Users/anicca` + `ANICCA_HOME=~/.blockrun` | `8Fpqd…PCV9` ✓ |
| **他人の home から franklin1 の鍵を読む試み** | **拒否（fail-closed が発火）** ← 設計通り |

→ **鍵の分離は既に正しく実装されている。** agent は他人の鍵で署名できない。ここは装備済みだった。
→ 残る事実: franklin1 の Base `0x3EcCAD24…`（$4.48）は `wallets.json` に無く受取専用。**使えるのは Solana。**
  ClawRouter は Solana 決済に対応（`~/.franklin2-home/.blockrun/payment-chain` = `solana`）なので、実害は今のところ無い。

★**一般法則（今日3回踏んだ。体系的欠陥として記録）**: **他インスタンスのツールを自分のシェルで実行した結果は、
そのインスタンスの実測ではない。** `HOME`/`ANICCA_HOME`/`PATH` は plist が与える世界。1変数でも自分の値が混ざれば、
測っているのは「私が動かした結果」であって「その agent の現実」ではない。plist の `EnvironmentVariables` を
dump して**全部再現してから**叩く。
★**一般法則2**: **「解決に失敗した」を「能力が無い」と読むな。** fail-closed 設計では失敗は正常動作でありうる。
今回は**防御を故障と誤診し、被害者(franklin2)を「経済主体ですらない人形」と spec に書いた**。
失敗を見たら問うべきは「なぜ失敗したか」であって「何が壊れているか」ではない。

**★第1層: 脳の財布（実測）★**
```
$ clawrouter wallet
  Payment Chain: base
  Base (EVM):  0x2f4816a5d3494A2F2fE217C191B360762B8A1B2e
  Solana:      DoiXYe63kKyY6Eff4fwqzoccnMBXa4E1PVWegA9Wu9L8
  Balance:     $0.00 (USDC)
  ⚠ Empty — fund wallet or use free models
```
- **3体が1つの財布を共有**（全員 `OPENAI_BASE_URL=http://127.0.0.1:8402/v1`）→ **誰かが全部燃やせる = INV-INDEP 違反**。
  tsbridge で席を独立させた意味が消える。franklin1 の金で claude-p が考える構図。
- 空 → 有料モデル要求が無料へ降格 → 日次上限 → 429。自分の手で再現:
  `{"code":"FREE_MODEL_FAILED","debug":"429 Rate limit exceeded: **free-models-per-day-high-balance**"}`
  → **`per-day` = 日次上限。無料に依存する限り 3体は毎日脳死する。**一時障害ではなく構造。
- `eco` が一度だけ通り `free/gpt-oss-120b` にフォールバックしたが、直後に同モデルを直叩きすると 429。
  **無料プールは共有・不安定。「別の無料モデルに変える」は解決ではない**（運任せの延命）。

**★分離は可能（公式 env、`clawrouter --help` 逐語）★**
```
BLOCKRUN_WALLET_KEY     Private key for x402 payments (auto-generated if not set)
BLOCKRUN_PROXY_PORT     Default proxy port (default: 8402)
```
→ **instance ごとに自分の router + 自分の鍵**にできる。tsbridge と同じ「1体1つ」の形。
   franklin plist に既にある `FRANKLIN_PROXY_PORT=8402` は、元々そう設計する意図だった痕跡。

### ★★2026-07-16 06:00 — 「脳が無い」の答えは README の1行だった（車輪の再発明をしていた）★★

Dais の指摘「struggling してるなら repo を探せ」で `gh search` → **既に使っている物が答えだった**。

| repo | ★ | 位置づけ |
|---|---|---|
| **`BlockRunAI/ClawRouter`** | **6658** | *"The agent-native LLM router. 41+ models, <1ms routing, **USDC payments on Base & Solana via x402**. **Wallet signature IS authentication** (no API keys), no accounts, no credit cards"* ← **我々が既に使っている。使い方を間違えていただけ** |
| **`xpaysh/awesome-x402`** | 261 | x402 の総 index（SDK / facilitator / MCP 統合 / tutorial）。**最初に読むべきだった** |
| `google-agentic-commerce/a2a-x402` | 538 | A2A に x402 決済（agent が agent に売る標準） |
| `qntx/x402-openai-python` | 260 | *"Drop-in OpenAI client with transparent x402 payment support"* |

**★README 逐語が全てを解いた★**:
> **"Starts at $0 — 8 NVIDIA models are free forever"**
> **"No wallet? 8 models work free out of the box. Install, run, and pin `nvidia/gpt-oss-120b` (or any of the 8) — no crypto, no signup, no balance required."**

**無料枠は2種類あった。混同していた**:

| | 上限 | 実測(2026-07-16 06:00、同一 router・同一瞬間) |
|---|---|---|
| `free/*`（我々が使っていた） | **日次上限あり** | `free/glm-4.7` → **429 `free-models-per-day-high-balance`** |
| `nvidia/*`（8モデル） | **free forever・上限なし** | `nvidia/llama-4-maverick` → **200。content=`'BRAIN_ALIVE'`（指示に正確に追従）**<br>`nvidia/gpt-oss-120b` → 200 |

→ **モデル名を1つ変えるだけだった。**「無料枠が枯れたから有料化が必要」という診断は**誤り**。ClawRouter に金を入れる必要も、
  per-agent router を組む必要も、この層では無い（それは品質を上げたい時の話であって、脳を生かす話ではない）。
→ しかも franklin の plist には**元から `FRANKLIN_FREE_MODEL=nvidia/llama-4-maverick` が在った**。誰かが知っていたが、
  主脳の `ANICCA_MODEL` は `free/glm-4.7` のままだった。**装備は在ったのに配線されていなかった。**

**適用（2026-07-16 06:02）**: franklin1/franklin2 の model 系 **9変数すべて** を `nvidia/llama-4-maverick` へ。
`plutil -lint` OK。reload 後の実 env で確認:
```
29721  .blockrun                  model=nvidia/llama-4-maverick  wallet=0x3EcCAD24…8749
29907  .franklin2-home/.blockrun  model=nvidia/llama-4-maverick  wallet=0xe7747Fd8…7ce9
70525  .anicca-founder            model=<default>                wallet=0x810f6d61…29c5
```
daemon banner も `exec loop (model tiers from config; **funded=nvidia/llama-4-maverick**)` に変わった。
★claude-p が model 変数を1つも持たない(=既定)ことが、**claude-p だけ THINK が通っていた**理由と整合する。

★**事故（記録）**: 一括置換を `for v in $VARS` で書き、**zsh は unquoted 変数を単語分割しない**ため
`$v` に全変数名が入り、PlistBuddy が `FRANKLIN_EVALUATOR_MODEL` に**変数名の羅列を値として書き込んだ**（plist 破損）。
`.bak-model-*` から配列 `VARS=(...)` で書き直して修復・実測確認済。
一般法則: **shell は zsh。`for x in $STR` は分割しない。リストは必ず配列 `arr=(...)` + `"${arr[@]}"` で回す。**
一般法則2: **`|| true` はエラーを飲む。**「8個 Set した」つもりが1個しか効かず、**残存数を数えて初めて気づいた**。
一括変更は必ず**変更後の残存数を数えて**検証する。

### ★2026-07-16 06:10 検証結果 — 脳は生き返った。だが x402_sell は1度も実行されていない★

**franklin1 の ledger（loop 自身が書いた記録。私の観測ではない）**:
```json
// BEFORE: {"kind":"wake_error", "error":"proxy_down", "model":"free/glm-4.7"}
// AFTER:
{"ts":1784149656,"wake_id":"00MRMKN1QNA051D268E74F4CE6","kind":"router_no_realized_action",
 "sleep_s":120,"model":"nvidia/llama-4-maverick","slot":null,"attemptsUsed":1,"profitable":false}
```
- `exec loop … funded=nvidia/llama-4-maverick` 以降、**`THINK failed` / `WARNING: ANICCA_WALLET_ADDRESS not set` / `Balance fetch failed` が全て消滅**
- 約200秒ごとに wake し、ledger を自分で書き、`ledger-franklin` ブランチへ自力 push（`57aa712..660dece`）
- → **第0層(身元) と 第1層(脳) は実測で突破。**

**★だが未達。想定が外れた★**

| 観測点 | 実測 |
|---|---|
| `ai.anicca.x402-seller-8414.plist` の `X402_PUBLIC_URL` | **まだ空** |
| `/.well-known/x402.json` の `resource` | **`/research`（相対のまま）** |
| ledger の `slot` | **`null`** |

`harness-failures.jsonl` 逐語:
> `always-act router: REQ-505/506/511/513 retry/reroute budget exhausted with no realized earn-ledger line this wake`

→ **`ALWAYS_ACT_ENABLED=1` の router は行動を試みているが、`slot: null` = x402_sell を1度も実行していない。**
   実行されないので `run.sh:303` が走らず、seller plist が書き換わらず、住所が seller に届かない。
   `live skills` には `x402_sell` が**含まれている**（`report, self/spawn, …, x402_sell, earn/…`）。**在るのに選ばれない。**

★**「脳を生き返らせれば x402_sell を選ぶ」という Fable の想定は外れた。** 考えるようにはなったが、選ばない。
  次の真因は **router がなぜ x402_sell を選ばないか**。ここが現在の最前線。
★ harness の誠実さは確認できた: REQ-508 のコメント逐語 —
  *"the exhausted-bound terminal case — truthfully recorded (**never a fabricated `profitable` or success value**, `slot: null`)"*。
  **稼いでいないのに profitable を捏造しない設計。**この harness は信用してよい。

**現在地（層ごと）**:
```
第0層 身元      ✓ 突破（wallet 解決、tier=broke 解除）
第1層 脳        ✓ 突破（nvidia/llama-4-maverick。proxy_down 消滅、200秒毎に思考）
第2層 住所      △ loop の env には在る / ★seller には届いていない★（x402_sell 未実行のため）
第3層 Bazaar    未到達（settle 1回の鶏と卵）
第4層 実績$0    未到達
```

**装備する順（下の層から。上から直しても動かない）**:
1. franklin1 = 唯一「金 + 鍵」が揃う → 自分の router + 自分の sol 鍵 → **$12.21 で自分の脳を買う**。最初の実証個体
2. claude-p = 鍵あり・金少 → 自分の router + base 鍵
3. franklin2 = **鍵を装備する**（生成 or 付与）+ 種銭 → ここで初めて経済主体になる

★注: 「1体1 router」は「1体1ノード(tsbridge)」と同じ原理 — **共有資源は必ず奪い合いになる**。
   席では claude-p が2枠占有して franklin1 を締め出した。財布でも同じことが起きる。**先に分ける。**
| **T2b-6** | claude-p 店②(:8411 / `0x810f` / $0.011 の唯一の稼ぎ手)を専用ノードへ移す。tsbridge に4つ目の service を足す必要あり。**最後に触る** | :8411 が自分の FQDN で配信し、売上が落ちない | T2b-5 の結果を見てから |

### ★T2b-4: franklin1 に広告を配線した（2026-07-16 05:31）。真因の全貌が出た★

```
ai.anicca.franklin-loop.plist に追加:
  X402_PUBLIC_URL = https://franklin1.tail7a0ba4.ts.net
```
検証: `plutil -lint` OK。reload 後、**プロセスの実 env**を `ps eww` で確認 — pid 59045 が
`X402_PUBLIC_URL=https://franklin1.tail7a0ba4.ts.net` を実際に保持（plist を読んだだけで満足しない）。

**★INV-F は既に満たされていた（朗報。STATUS の従来認識を訂正）★**

`launchctl list` 実測:
```
3052   1  ai.anicca.x402-seller-8414   ← franklin1 の loop 自身が立てた seller。稼働中
94909  1  ai.anicca.x402-seller-8413   ← franklin2 の loop 自身が立てた seller。稼働中
-      1  ai.anicca.x402-seller-8412   ← claude-p のみ未起動
```
T1 の修正(依存を持つ copy を exec / bind 失敗で exit 1 / ローカル宣言)が効いており、
**franklin1 と franklin2 は既に「自分で店を立てる」に成功している**。手書き boot script に依存していない。

**★$0 の真因は「空の PUBLIC_URL」だった — 実物★**

```
ai.anicca.x402-seller-8414.plist（loop が生成した実物）:
  X402_PAYTO      = 0x3EcCAD24794ca298D25378E9902A251322ea8749
  X402_PUBLIC_URL =                ← ★空文字★
  X402_PORT       = 8414
```
結果、manifest が**相対パス**を吐いていた:
```json
{"x402Version":1,"resources":[{"resource":"/research", "price":"$0.003", ...}]}
                                          ↑ 相対。買い手はどこへ払えばいいか分からない
```
`serve.mjs:47` 逐語: *"(root cause 2026-07-14; cf coinbase/agentkit#877). **Set X402_PUBLIC_URL to the https funnel origin.**"*
→ **Bazaar は絶対 URL を要求する。** franklin1 は店も商品7点も manifest も持っていたが、**住所が空欄のチラシ**を配っていた。

**★伝播経路は健全（実コードで確認）★**

| 経路 | 実測 |
|---|---|
| `run.sh:303` | `<key>X402_PUBLIC_URL</key><string>${X402_PUBLIC_URL:-}</string>` → loop の env から seller plist へ書く。**`:-` の既定が空だったので空が書かれていた**。loop plist に値が入った今、次の wake で実 URL が書かれる |
| `env-filter.mjs:19` | `/(_WALLET_KEY|_PRIVATE_KEY|_PRIV_KEY)$/` = **denylist のみ**。`X402_*` は元から素通り。→ 「ALLOW set に X402_PUBLIC_URL を追加した」という前セッションの記述が**虚偽だった**ことの再確認（追加は不要だった） |

**★T2b-4 DONE — 3体とも自分の住所を持った（2026-07-16 05:38）★**

`ps eww` でプロセスの**実 env** から確認（plist を読み返して満足しない）:

| pid | ANICCA_HOME | port | X402_PUBLIC_URL |
|---|---|---|---|
| 59045 | `.blockrun` (franklin1) | 8414 | `https://franklin1.tail7a0ba4.ts.net` ← **新規**（元は無し = $0 の真因） |
| 68389 | `.franklin2-home/.blockrun` (franklin2) | 8413 | `https://franklin2.tail7a0ba4.ts.net` ← 元は共有 `:10000` |
| 70525 | `.anicca-founder` (claude-p) | 8412 | `https://claude-p.tail7a0ba4.ts.net` ← **新規** |

稼ぎ頭は無傷: reload 後も `:8411`(pid 628) と `:8412`(pid 577) は LISTEN 継続。

★**観測の失敗を1つ記録**: 最初 `ANICCA_INSTANCE` で loop を列挙し、claude-p が出てこないので「死んだか」と疑った。
実際は **claude-p の plist に `ANICCA_INSTANCE` が無い**だけで、loop は pid 631 で生きていた。**壊れていたのは観測の方**。
`ANICCA_HOME` は全 instance が持つので、これを軸にすれば漏れない（identity の軸 = HOME、という T0 の結論と同じ）。
一般法則: **列挙のキーに「全個体が持つとは限らない属性」を使うと、存在するものを不在と報告する。**

**次にやること = 何もしない。loop の wake を待って観測する。**
`run.sh` を手で叩かない（叩けば「Dais が稼がせた」になり INV-F 違反 → [[feedback_watch_loops_never_do_their_work]]）。

観測点（全て loop 側が動かすもの。①→④の順に進む）:
```
① seller plist(x402-seller-8414) の X402_PUBLIC_URL が空 → 実 URL に変わる
     run.sh:303 が loop の env から書き直す。10分毎の wake で発火
② manifest の resource が "/research" → "https://franklin1.tail7a0ba4.ts.net/research"
③ bazaar-scan.mjs が 0x3EcC の resource を返す
     ★ここで詰まる公算大★ T3 で公式仕様から確定済み = 掲載には settle が1回必要
     ("verify alone is not enough")。franklin1 の loop が self-pay を1回通す必要がある
     (INV-7 で収益に数えない、着火専用) = T4a。公開 URL がやっと在るので今アンブロック
④ verify-inflow.mjs の inflow が $0 でなくなる ← ★ここだけが「稼いだ」★
```

### ★T2b-3 DONE — 席が永続化した（2026-07-16 05:26）★

`~/Library/LaunchAgents/ai.anicca.tsbridge.plist`（`RunAtLoad` + `KeepAlive` + `ThrottleInterval=30`。
tsnet はノード登録に数秒かかるので再起動を煽らない）。log = `~/.tsbridge/logs/tsbridge.{out,err}.log`。

**自己申告でなく実測で確認した2点**:

| 検証 | 実測 |
|---|---|
| launchd 移行後も**外部**から届くか | `r.jina.ai`(tailnet 外の第三者)経由で `https://franklin1.tail7a0ba4.ts.net/` の全文取得。**payTo `0x3EcCAD24…` = franklin1 自身**。商品7点 + `/.well-known/x402.json` + `llms.txt` を公開配信中 |
| KeepAlive は本物か | `kill -9 52686` → 35秒後 → **pid 53290 で自力蘇生**。launchctl の `0` を信じず、実際に殺して確かめた |

★副産物: franklin1 の店は**既に商品7点を公開している**（research $0.003 / whois $0.002 / stock-quote $0.003 / calc・DNS・JSON-flatten・compound-interest 各 $0.001）。`/.well-known/x402.json` も**実装済み**（T8 で「実装する」としていたが既に在る。T8 の記述は要修正）。franklin1 に足りないのは店でも商品でもなく、**Bazaar への広告(=`X402_PUBLIC_URL`)だけ**。

### ★2026-07-17 是正 — T2b-4「DONE」は不完全だった。実際に:8414を握っていたのは別プロセス★

**T2b-4 は loop が生成した `ai.anicca.x402-seller-8414` plist の env だけを直して「DONE」と書いたが、
そのプロセスは1度も port を取れていなかった。** 実測(`lsof -iTCP:8414` → pid → `ps eww`):
実際に :8414 を LISTEN していたのは Dais 手書きの `ai.anicca.x402-franklin1` launchd job
（`serve-franklin1-boot.sh` 経由、`ANICCA_HOME=/Users/anicca/.openclaw`）で、こちらは
`X402_PUBLIC_URL="${X402_PUBLIC_URL:-https://aniccanomac-mini-1.tail7a0ba4.ts.net:10001}"` という
**Funnel非対応ポート(:10001)への旧フォールバックのまま**だった。ローダー2本(`x402-seller-8414` と
`x402-franklin1`)が同じ :8414 を取り合い、後者が先に bind して勝ち、前者は `spawn scheduled` のまま
死に続けていた（bind失敗→exit 1、`launchctl print` で確認）。
→ **一般法則: plist の env を直しても、実際にそのポートを握っているプロセスが別 launchd job なら無意味。
「直した」の前に `lsof` でポートの実所有者を確認する。**

**修正**: `skills/earn/x402-sell/serve-franklin1-boot.sh` のフォールバックを
`https://franklin1.tail7a0ba4.ts.net`（tsbridge の tsnet ノード。T2b-2/T2b-3 で既に外部到達確認済み）に変更、
無効化されていた旧 `tailscale funnel --https=10001` 行を削除（tsbridge が既にこの役割を担うため二重管理は不要）。
`launchctl kickstart -k gui/501/ai.anicca.x402-franklin1` のみ再起動（他の x402 job のpidは無変化を確認）。

**検証（全て実測、2026-07-17）**:
| 項目 | 結果 |
|---|---|
| `/.well-known/x402.json` の resource | `https://franklin1.tail7a0ba4.ts.net/...`（絶対URL、7商品全て） |
| `curl https://franklin1.tail7a0ba4.ts.net/funding-rates` | `402`、`resource` が新URLと一致 |
| **外部到達の証明**（tailnet外の第三者 `r.jina.ai` 経由） | `HTTP 402 Payment Required` を新URLで確認（tailnet内からの自己満足ではない） |
| 既存3枠 (443/8443/10000) | 直前と同じ pid（97401/92907/92901 系列）、`curl` で200継続。**無傷** |
| claude-p (`0x810F6D61…`) から新URL `/research` へ self-pay $0.003 | tx `0x3889c185ccb02d67adcfd08ac3643d832a8548688246c98bbdb5a257f7faccd1`、`settled:true` が
`state/sales-0x3eccad24794ca298d25378e9902a251322ea8749.jsonl` に記録 |

commit: `99765387`（anicca repo, main）。Bazaar 掲載反映は次の `bazaar-scan.mjs` 実行で確認予定（settle 1回はT3の条件を満たした、掲載まで通常30-60分）。
★注: STATUS.md 表の **T2b-6** はこれとは別タスク（claude-p の:8411をtsbridgeに載せる、未着手）。混同注意。今回の是正は T2b-4 の欠陥修正。

### ★金の帰属（2026-07-16 実測。混線ゼロ）★

boot script 逐語: franklin1 = *"franklin1's **OWN** payTo (receiving-only, no key needed here)"* /
franklin2 = *"franklin2's **OWN** payTo"* / :8412 = *"**claude-p's own wallet**"* / :8411 = *"payTo = **founder 0x810f**"*。
→ **:8411 と :8412 は両方 claude-p のもの。claude-p は店を2軒持っている。** agent 3体に seller 4本ある理由がこれ。

| agent | wallet | 48h 外部売上 | 件数 | 自己支払(seed) |
|---|---|---|---|---|
| franklin1 | `0x3EcCAD24…` | **$0** | 0 | 0 |
| franklin2 | `0xe7747Fd8…` | **$0** | 0 | 0 |
| claude-p 店① | `0x810f6d61…` | $0.011 | 9 | 9件 / $0.016 |
| claude-p 店② | `0x904B50d2…` | $0.006 | 6 | 7件 / $0.012 |

★**席を奪っていたのは claude-p だった**: `:443`(店①) + `:8443`(店②) で3枠中2枠を占有 → franklin2 が `:10000` → **franklin1 は席ゼロ**。
franklin1 の $0 は能力でも設定ミスでもなく、**兄が2軒出店していたから**。これが INV-INDEP 違反の実体。
→ tsbridge がこれを**裁定なしで**解いた。Personal 無料枠は *"Unlimited user devices"* なので、**誰も何も諦めなくていい**（claude-p は2軒維持のまま、Franklin 兄弟も自分の席を持てる）。

★**まだ経済ではない（実測が2つそう言っている）**:
1. **自己支払 > 外部売上**。0x810f = 外部 $0.011 vs self-pay $0.016 / 0x904B = 外部 $0.006 vs self-pay $0.012。着火用の自演の方が金額が大きい
2. **同じ bot が両方の店を舐めている**。`0xaf5bb59a58a3a05da3d7308d53de36836bc085ae` が 0x810f と 0x904B の**両方**に、`0x670fa140…` は 0x810f に2回。
   STATUS の「8個の EOA が $0.001 ずつ単発」「BlockRun 自己申告で 47% は non-organic」と整合 → **需要ではなく巡回 bot**。T9(高単価化)が本丸である裏付け

### ★T2b-2 DONE — franklin1 が初めて自分の公開 URL を持った（2026-07-16 05:15 実測）★

**「1台=3枠」は消滅した。実測で確定。**

```
tsbridge 1プロセス → tsnet ノード3個。各ノードが独自 IP・独自 FQDN・独自 :443
  claude-p    100.73.148.91     https://claude-p.tail7a0ba4.ts.net
  franklin1   100.114.193.59    https://franklin1.tail7a0ba4.ts.net    ← 兄と無関係な自分の席
  franklin2   100.81.5.86       https://franklin2.tail7a0ba4.ts.net
```

**① ルーティングが正しいことの証明（payTo が3つとも別）**:

| FQDN | payTo（実 HTTP から） |
|---|---|
| franklin1.tail7a0ba4.ts.net | `0x3EcCAD24794ca298D25378E9902A251322ea8749` ← franklin1 自身 |
| franklin2.tail7a0ba4.ts.net | `0xe7747Fd899D8987821Bb4CB3D6aDf22565F87ce9` ← franklin2 自身 |
| claude-p.tail7a0ba4.ts.net | `0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74` |

★注: claude-p の :8412 は `0x904B`(PM proxy) に払わせている。STATUS 冒頭の表では claude-p の x402 wallet = `0x810f` だが、:8412 の実 payTo は `0x904B`。**どちらが意図か未確定**（STATUS.md 79行「payTo 0x904B は誤設定 → 誤り。意図的」と整合はする）。T2b-3 で確定させる。

**② Funnel(公開)であることの証明 — ここを間違えかけた**:

Mac Mini から curl して 3つとも 200 だったが、**Mac Mini は tailnet の中にいるので、この 200 は公開の証拠にならない**（tailnet 内部で見えただけかもしれない）。自分の位置を証拠に混ぜる誤り。→ [[feedback_my_own_scripts_are_self_report_not_evidence]] と同型。

外部から2段階で確定させた:

| 検証 | 結果 |
|---|---|
| 公開DNS `dig +short @8.8.8.8 franklin1.tail7a0ba4.ts.net` | `103.84.155.217 / 103.84.155.153` = **実売実績のある `aniccanomac-mini-1` と同じ Tailscale ingress IP**。公開解決される |
| 第三者サーバ `r.jina.ai` 経由で実 HTTP | **成功**。`URL Source: https://franklin1.tail7a0ba4.ts.net/` + 商品 JSON 全文。**公開インターネットから到達可能** |
| 外部プロキシ `api.allorigins.win` | 500 / 522 で失敗。**Funnel の否定材料にはしない**（プロキシ側の障害と区別できない）。曖昧な結果は結論にしない |

**③ 未確定だった3件の決着**:

| 問い | 実測 |
|---|---|
| tailnet の台数上限に触れるか | **触れない**。Personal($0) は *"Unlimited user devices"*（公式 pricing）。3ノード追加後も全て稼働 |
| tsnet ノードに Funnel を許す ACL が要るか | **不要だった**。ACL を1行も触らずに Funnel が立った（既存 tailnet の nodeAttrs を member として継承したと推定。**推定であり未検証**） |
| Funnel 帯域の実数値 | **依然不明**。公式は数値を書かず *"non-configurable bandwidth limits"* のみ。売上が伸びた時に初めて効く。**当面は blocker でない** |

**④ 壊していないことの確認**: 既存3枠 `:443` / `:8443` / `:10000` は tsbridge 起動後も全て 200。稼ぎ頭(:10000 で $0.011 実績)は無傷。

**⑤ 使ったもの**: `jtdowney/tsbridge`(300★) を `go install`（48MB、Go 1.26.0）。config = `~/.tsbridge/tsbridge.toml`。**seller のコードは1行も触っていない**。

**⑥ 残る脆さ（T2b-3）**: 今の tsbridge は `nohup` の裸プロセス。**Mac 再起動で消える。**launchd 化するまで、この成果は揮発する。

### ★T2b-1 DONE — 鍵は取れた。ただし経路を変えた（2026-07-16）★

`~/.tsbridge/authkey`（61 bytes、mode `600`、id `kXpbFDuNCM11CNTRL`、reusable、期限 Oct 14 2026）。

**当初計画(OAuth client → get-authkey)は破棄した。理由は3つ、全て実測**:

| # | 実測 | 出典 |
|---|---|---|
| 1 | **公式自身が近道を指定している** — *"To use it, generate an auth key from the Tailscale admin panel and run the demo with the key: `TS_AUTHKEY=<yourkey> go run tsnet-funnel.go`"* | `tsnet/example/tsnet-funnel/tsnet-funnel.go` |
| 2 | **`get-authkey` は不要だった** — 採用した tsbridge が OAuth を**内製**しており、`auth_key` と `oauth_client_id/secret` の**どちらでも**食える。恒久化は config の差し替えだけ | tsbridge `docs/configuration-reference.md` |
| 3 | OAuth/tag/ACL は**恒久化の仕事**であって**検証の仕事ではない**。tsnet が席問題を本当に解くか未確認の段階で恒久化の配管から始めるのは順序が逆（Dais 裁定「shed で行け」） | — |

**同時に実測できたこと**:

| 問い | 実測 |
|---|---|
| Funnel は無料枠で使えるか | **YES**。公式 KB 1223 逐語: *"Tailscale Funnel is available for all plans"*。admin 実機でも plan = **Free** を確認 |
| auth key の最長寿命 | **90日**（admin ダイアログ: "Must be between 1 and 90 days"） |
| ★node key も失効する★ | admin の Tags トグル逐語: *"Devices authenticated by this key will be automatically tagged. **This will also disable node key expiry for the device.**"* → **tag の無いノードは node key がいずれ失効し、再認証 = human loop が数ヶ月後に蘇る**。恒久 human ゼロには **auth key 失効(90日)** と **node key 失効** の**2つ**を殺す必要がある。前者は tsbridge の OAuth、後者は tag |

★**事故と是正（記録）**: 最初の鍵を「取れたか確認」するつもりで eval の返り値に載せ、**transcript に平文で漏らした**。是正: クリーンな鍵を DOM→file 直結で再発行（一度も表示せず）→ fingerprint で照合 → 漏洩鍵 `kpj5iWGcnZ11CNTRL` を revoke → **リロードして** 一覧から消滅を実測 → ローカルコピーを rm。
一般法則 → [[feedback_capture_secrets_dom_to_file_never_through_stdout]]。「ローカル transcript だから安全」は誤り — handover skill は引き継ぎノートを**メール送信**し、token-optimizer は checkpoint を**ディスクに書く**。実際に外へ出る経路がある。

### ★採用 repo: `jtdowney/tsbridge`（300★）— 単独で丸ごと採用、混ぜない★

*"A lightweight proxy manager built on Tailscale's tsnet library that enables **multiple HTTPS services on a Tailnet**"* = 我々の形そのもの。

| 確認項目 | 実測 |
|---|---|
| Funnel(公開)をやるか | **YES**。`internal/tsnet/interfaces.go`: `ListenFunnel(network, addr string) (net.Listener, error)`。`THREAT_MODEL.md`: *"Funnel mode exposes services to the public internet"* |
| service ごとに FQDN | `docs/configuration-reference.md`: `name = "api"` → *"becomes api.<tailnet>.ts.net"* |
| 認証 | `auth_key` / `oauth_client_id+secret` の両対応。`default_tags`(OAuth 時必須) |

**却下した候補**: `almeidapaulopt/tsdproxy`(1649★) = Docker label 駆動だが我々の seller は launchd の node プロセス → **star は多いが形が違う**。`nfielder/ts-infi-authkey`(0★) = 不要（tsbridge が内製）。

**採る形**（seller のコードは1行も触らない。前段に置くだけ）:
```toml
[tailscale]
auth_key_env = "TS_AUTHKEY"          # 恒久化時は oauth_client_id_env/oauth_client_secret_env + default_tags へ
state_dir    = "/Users/anicca/.tsbridge"

[[services]]
name = "franklin1"                   # → franklin1.tail7a0ba4.ts.net:443（自分の席）
backend_addr = "localhost:8414"
funnel_enabled = true                # 既定 false。公開に必須

[[services]]
name = "franklin2"
backend_addr = "localhost:8413"
funnel_enabled = true

[[services]]
name = "claude-p"
backend_addr = "localhost:8412"
funnel_enabled = true
```
| **FIX-1** | ★層2★ franklin2 の x402 配信修理 — telemetry poster.log で 4193/4194回(99.98%)が `400 host_wallet_mismatch`。★根本原因確定(07-17)★ = `apps/landing/netlify/functions/_lib/fixed-identities.js` の `FIXED_IDENTITIES` に franklin2 未登録、EVM前提フォールバックがSolana base58と不一致。x402決済には無影響(コード独立、telemetryのみ) | 名簿に franklin2 の Solana pubkey を追加・デプロイ後、poster.log の host_wallet_mismatch が消える | ★DONE 2026-07-17★ PR `anicca-products#292` deploy成功。poster が400→202 に変化を実測(03:05:59Z) |
| **FIX-3** | ★層2★ franklin1 の sales-0x3eccad24….jsonl は21件の決済成立を主張するが、on-chain inbound は生涯2件のみ。★根本原因確定(07-17)★ = serve.mjs L123-136 のsales-log書き込みが `next()`(verify成功)直後・`settle`(on-chain着金)前。21件は「署名検証21件・着金0件」。裏付け: claude-p の同一コードで payer実在9件=on-chain完全一致、payer:null=一致0件、franklin1の21件は全payer:null。未確定=settle失敗自体の理由(stderrログ消失で未特定) | sales-log を settle成功(`X-PAYMENT-RESPONSE`)後へ移動 + stderr保全、sales-logとon-chainが一致する | ★DONE 2026-07-17★ settleゲート実装(commit `e5904325`)。franklin1旧21件は全て`settled:false`印付け、claude-p27件中12件・proxy15件中2件も対象。**実settleで検証済(07-17夜)**: T9-1 done(b)節参照 — franklin1へ実購入2件、両方on-chain確認+sales-logに`settled:true`で記帳、attempts-logへの誤記録なし |
| **T2c** | franklin1/franklin2 の plist に `ANICCA_WALLET_ADDRESS` を設定（2026-07-16 実測時は両方無かった） | 両 loop のログから `using "unknown"` が消える | ★DONE(2026-07-17 12:23Z 実測で解消確認)★ 両 plist に正しい wallet(0x3EcCAD…/0xe7747F…)が設定済み — 07-17 の v2 化/boot script 修理の過程で解消されていた。旧記述「両方とも無い」は現状と不一致のため是正 |
| **T3'** | `x402-express@1.2.0`(v1 deprecated) → `@x402/express@2.18.0`(v2 公式現行) へ移行。**各店それぞれを移行。統合はしない(INV-INDEP)**。差分: パッケージ名 / route config が `accepts` 配列 / network が CAIP-2 / `extensions.bazaar` + `declareDiscoveryExtension()` | 4店とも v2 で稼働し、Bazaar のメタデータ品質(=検索順位要因)が上がる | ★T3'-5 DONE(2026-07-17夜、franklin1/franklin2)★ `serve-v2.mjs`でv2化(`x402Version:2`、`eip155:8453`)、v2 buyerでsettle→sales実証(tx on-chain確認)。commit `ef929635`/`3c7b3455`。★claude-p(稼ぎ頭)は保留★ — v1 buyerはv2 sellerに払えないと確定(`extractPayment()`が`payment-signature`ヘッダのみ読み`x-payment`(v1)を無視、閉じるにはカスタムmiddlewareが要るmoney-safety案件)。詳細は上の「2026-07-17夜: 発見面拡大+資金回収」節1 |
| **T5** | 死んだ配線の掃除 — 8412 の二重 plist（loop 生成 + 手書き x402-claude-p が同ポートを取り合う）、`x402-endpoint`(exit 126) 等の残骸 | `launchctl list \| grep x402` に exit≠0 が無い | ★DONE(2026-07-17夜)★ lsofでポート実所有者を先に確認(8412=x402-claude-p/8413=x402-franklin2/8414=x402-franklin1 の正規3店が保有)してから、孤立job 4個をbootout+plist削除: seller-8412(.anicca-founder boot)/seller-8413(.franklin2-home配下plist)/seller-8414(+.disabled)/x402-endpoint(exit126、anicca-oss worktree残骸)。掃除後に3店とも`/calc`402応答を実測(外部franklin1.tail7a0ba4.ts.net=402、local 8412/8413=402)。launchctl listの残exit≠0はlive店の-15(SIGTERM再起動痕)とcrash待ちでなく正常 |
| **T6** | ★self-improve の蘇生★ — `ai.anicca.self-improve-evolve.plist` に `ANICCA_HOME` が無く、`ledger_reader.py:resolve_ledger_path()` が repo 相対の孤立 ledger(28行)にフォールバック。誰の経験も学んでいない。instance 毎に起動して実 earn-ledger を読ませる | evolve の入力が各 instance の実 ledger であることをログで確認 | ★後送り(2026-07-18 Dais指示: self-improve はまだ。T7/T10 も同様)★ |
| **T7** | 学習の共有 — `promote.py:30` が「進化した戦略を repo baseline に git commit」する経路は既にある。T6 が直れば「賢い個体の学びが repo 経由で全員に配られる」が成立する。実測で確認 | 1 instance の学習が他 instance の次 wake に反映されることを実測 | T6 後 |
| **T8 / XSCAN-1** | #16 掲載面を増やす = distribution — `/.well-known/x402` 実装 → `x402scan.com/resources/register` に自動 POST → Agent402 / MCP registry / ERC-8004 | 各面で discoverable を実測 | ★XSCAN-1 DONE(2026-07-17夜)★ franklin1(`server/b9b53de8…`)/franklin2(`server/af9283bc…`)ともx402scan登録green(各9商品v2タグ、公開serverページ実在を自分でcrwl確認、v1拒否("migrate to v2")消滅)。SIWX署名必須、公式`wrapFetchWithSIWx`のバグを低レベル自前実装で回避(`register-x402scan.mjs`, commit `4809f89f`、研究MD `docs/research/2026-07-17-x402scan-registration-siwx.md`)。agent402.tools=franklin1(443)登録成功、franklin2(:10000非標準)は拒否のまま。発見面がBazaar 1個→x402scanで2個に拡大。`/all`一覧は24h取引量が要るので活動待ち。claude-p(稼ぎ頭)はv2未移行のため本タスク対象外、残作業として残る |
| **T9** | ★★本丸。商品が構造的に売れない（下記）★★ 「agent が欲しがる物」= **買い手が自分では出来ない物**を売る。★商品確定(07-17)★ 第1弾=funding-rates(取引所間乖離%、Binance/Bybit/HL無料public APIから純算術、限界原価≈$0)。根拠=franklin1自身が hl_trade で209 wake perp売買中なのに funding rate 未取得(自分の実需の穴)+ottoai(鯨bot)が同商品を$0.001で実売中。crypto-news/kol-sentimentはLLM要約コスト$0.0106/callが単価$0.001を超え逆ザヤにつき凍結 | T9-1(funding-rates)の done 定義は spec 参照。単価 $0.05+ の商品が**外部の**agent に売れる | ★T9-1 done(a)(b)達成 2026-07-17★ `/funding-rates` を franklin1店(:8414)・claude-p店(:8412)に実装、402実測済(commit `8f6d0f7c`)。done(b)=claude-p→franklin1への実購入2件をon-chain確認済み(INV-7でself-pay扱い、収益には数えない)。done(c)(14日以内の反復購入者)は未達・観測中、下記 T9-1 参照 |
| **U9** | ottoai 宛の鯨bot(93.5%集中)が本物のトレードagentの反復需要かottoai自身のwash tradingか | bot(`0x1cb8d145…0bdff`)の資金源1hop遡りで判定 | ★DONE 2026-07-17★ 本物の自律買い手(EIP-3009 gasless、13+relayer構成、ottoaiとの資金循環なし=wash棄却)。我々の4walletは未probe。詳細は上の「U9確定」節 |
| **T10** | `hermes-agent-self-evolution` を copy+tweak — GEPA+DSPy で x402 skill を trace から進化させる | evolve が実際に skill を書き換え、gate を通す | T7 後 |
| **OSS-1** | ★T9の後★ Linux/cloud 常駐の完成品が無い。`install.sh` L148-160 は Darwin なら launchctl load で自動常駐するが、Linux は「systemd で自分で」と案内するのみでトップレベルの systemd unit が repo に無い。skills配下の言及数 launchd 68ファイル vs systemd 3ファイル = 実質macOS専用（~/anicca の実ファイル実測、2026-07-17） | Linux上でも同等の自動常駐がrepo付属のunitで動く | T9 後。ホスティング候補は2026-07-17実測で更新: 最有力FluxCloud、フォールバックBitLaunch、Akashも可(Hetzner/Fluenceは除外)。詳細は上の「D. クラウドホスティング」節 |
| **OSS-2** | ★T9の後★ 「1体目をゼロから立てる」bootstrap scriptが無い。`skills/self/spawn` は既に稼いでいる親が子を産むロジック(gate: 残高≥$20 && 14日以内未出産 && 子<1)であって、第三者の1体目はREADME手順を人間が手で実行するのが実態。franklin2も同様（`git log --all` にfranklin2のcommit 0件=別ANICCA_HOMEで人が手順を再実行しただけ、自動複製scriptは存在しない）。x402実売にはCDP_API_KEY_ID/SECRETの外部取得が必要だがREADME Quick startに手順が無い。README自身が"What's real today"(L119)でcloud self-spawn/自律redeem/UBI payoutをIn progressと明記済み | 第三者が人手ゼロで1体目をbootstrapできるscriptがrepoにある | T9 後 |
| **GIG-1** | gig loop 蘇生 — Claude CLI subscription OAuthのheadless失効(keychainロック、upstream `claude-code` issue #76905)で40時間(07-15 21:23〜07-17 13:56)pass完走ゼロだった真因を特定、`gig_reality_verify.sh`実証済みのCLIProxyAPI(:8317) fallbackを`gig-cli.sh`のcore起動部に移植 | 全ステップ(LEARN→B0→PROFILE→B1→B2→FUNNEL)が完走する | ★DONE 2026-07-17 13:56★ 完走実証(`pass-report.jsonl` ts=1784264202)。新規応募0件、生涯実績applied 138/won 2/paid 0は不変。売上効果は未検証、steady宣言は連続完走を見てから |
| **GIG-2** | gigをprofitable-claude repoへ集約移設(現状 ~/anicca と ~/.openclaw に乖離複製が存在) | gigの実体がprofitable-claude 1箇所に統合され、二重管理が消える | 別CCセッション担当。live配線図はTaskList #22に記録済み |
| **AUTH-1** | machine-wide Claude CLI OAuth死の駆除 — 同一headless失効パターンで停止していた全loopを洗い出し、同一パッチ(`~/.cli-proxy-api-key`→`ANTHROPIC_BASE_URL=:8317`)を適用 | 死亡していた全loopが蘇生し、同パッチが該当script全てに適用される | ★DONE 2026-07-17★ anicca-reddit-loop/anicca-selffix-gig-loop/anicca-selffix-reddit-loopの3体蘇生確認済み。9 scriptにパッチ適用(commit `306e0f73`・`80e9f011`)。anicca-2/anicca-3は起動元未特定で未対応(手動要) |
| **AUTH-2** | profitable-claude repo内の未パッチ3 script(ceo-run.sh等)にAUTH-1パッチを適用 | 3 scriptとも`ANTHROPIC_BASE_URL` fallbackを持つ | open(現在未起動のため緊急性低) |
| **CLAUDE-P-1** | 稼ぎ頭claude-pのTHINKがClaude subscription OAuthのheadless失効で07-17 01:14〜797件連続`wake_error`(`claude_exit_1`)。`AUTH-1`が`*-cli.sh`8本のみパッチし唯一のTHINK経路`runtime/loop/brain.mjs`の`thinkClaudeP()`を漏らしていた。gig-cli.sh実証済みのCLIProxyAPI(:8317)fallbackを`thinkClaudeP()`のchildEnvに移植、副次で`index.mjs`の`error:'proxy_down'`ハードコード(実因を隠す表示バグ)も実`err.message`に是正 | 再起動後の新規ledger行が`kind:"wake"`(wake_errorでない)で戻り、`daemon.err.log`に`THINK failed`が出ない | ★DONE 2026-07-17夜★ anicca commit `91d45919`(brain.mjs+index.mjs)、`launchctl kickstart -k`で再起動、**実測**: ledger `{"kind":"wake","slot":"report","exit_code":0}`(wake_id `00MROKBX4ZA43C5EC07C604595`)、`daemon.err.log`に`[brain] claude-p said:`成功ログ、以後`THINK failed`再発なし。model表示の`free/glm-4.7`お飾りバグ(`index.mjs:315`複数箇所)は未修正(リスク>効果でスコープ外、上の「B.」節に診断コメントのみ残す) |
| **ROTATE-1** | franklin1のSolana秘密鍵漏洩(subagent stdout経由)をrotate。旧`8Fpqd…PCV9`→新`F5SYU…hZ5T`、資金全額移動、全参照(anicca/netlify/SSOT/memory/CLAUDE.md)更新 | 旧鍵残高0、新鍵に全資金、grep で旧アドレスの現役参照0件 | ★DONE 2026-07-17★ commit `0f53d0f7`(anicca)・netlify PR#293→`d4144964`・SSOT+memory `4e59e341b` |
| **MKT-1** | ★最優先(市場理解)★ x402実需検証 — 競合`agentservices.to`の生涯売上$0.169/12件がfacilitatorテストwalletのみ=実需ゼロと判明。唯一の実需=ottoai鯨bot1体。T8(掲載面拡大)で鯨への発見導線を最優先化 | 鯨bot(または新規の非テストpayer)からの実購入をon-chainで確認 | ★訂正(2026-07-17研究3本)★ 旧結論「実需極薄」は誤り — 市場は買い手94K vs 売り手22K(買い手4-5倍・供給不足)、$24M/30d。売れない主因=発見されてない(未登録+商品少)。処方箋: (a)v2+x402scan登録=DONE (b)商品31=DONE(2026-07-18) (c)agent402無料掲載=franklin1済。残=外部購入の実観測のみ(OBS-1、〜07-31)。研究: docs/research/2026-07-17-x402-{what-sells-X,seller-repos,economy-demand-analysis}.md |
| **DOC-1** | README書き直し — 新定義(every AIが0から経済的独立、human loopなし)。草案完成 | Dais/adversaryレビューを経て本README差し替え | 草案完・レビュー待ち。`docs/drafts/2026-07-17-anicca-readme-draft.md`(commit `9b6e856`) |
| **DOC-2** | docsサイト構築 — `blume`(Astro静的、AI-ready)採用判定済み | `npx blume init`でdocsサイトが立ち上がりデプロイされる | ★後送り(2026-07-18 Dais指示: docs より earn rail=BOUNTY-1 優先)★ ADOPT判定のみ完了。評価MD `docs/reference/2026-07-17-blume-docs-tool-evaluation.md` |
| **SOL-1** | franklin1の有料burnは`sol-trade` skill単独(`sol-trade/run.sh:17`の`SOL_TRADE_MODEL=openai/gpt-5-mini`、franklin-trading CLIがclawrouter非経由でx402直接支払い)。直近24h $1.86/日課金・realized $0 = 稼がずに焼くだけ。burnを止める/安いモデルへ切替/凍結のいずれかを判断・実行する | `sol-trade`のcost_log課金が$0になるか、realized profit>0がledgerに載るかのいずれかが実測できる | ★DONE 2026-07-17夜★ 判断=凍結(KILL)。実測: 850ライブパスでswap実行0回・realized $0(生涯)、trace(`sol-trade.trace.jsonl`1035行)にSignature抽出0件、earn-ledgerに`source:sol-trade`行0件=「下手」でなく「1度も取引してない」のに`gpt-5-mini`へ生涯$20.97/直近$1.86日を焼いていた。無料モデル代替は既に失敗済み(2026-07-04 `SOL_TRADE_MODEL=nvidia/deepseek-v4-flash`試すもcommit`ba9a54bf`「returned empty」で撤回)。self-evalがDEAD判定できなかった理由=earn-ledgerの行しか見ないがsol-tradeは swap確定時しか書かない設計→850 WAITパスが1行も残らず観測範囲外(HLは毎wake net=0を書くので181件で発動できたのと対照的)。`~/.blockrun/skills/earn/sol-trade/KILL`と`~/anicca/skills/earn/sol-trade/KILL`をtouch(run.sh:21-24のkill-switchで次パスからskip、コード変更ゼロ、rm で可逆)。anicca commit `0980eb44`(push済、origin/main と 0 ahead/0 behind 確認済)。franklin1 THINK を auto に戻す案は却下・現状free固定を維持: 2026-06-21 PREMIUM EXPERIMENTで実測済み(gpt-5.4切替→探索だけで30分$0.68/hr燃焼→realized $0→即revert、`config.mjs:36`に"Do NOT use 'auto'(routes to PAID, drains wallet)"のコメントで実測記録あり)。franklin1残高$4.48の小資本で同じ道を繰り返すだけ、freeでTHINK品質は足りている(全ツール正常動作、実測)。plist/config.mjsは変更しない。副産物としてSOL-2を新規登録(sol-tradeが850パスで0 swapの真因は未確定、凍結中で優先度低) |
| **SOL-2** | `sol-trade`が850ライブパスでswap実行0回だった真因(franklin-tradingが発注しない/常時WAIT/シグナル出せず)が未確定。SOL-1で凍結(KILL)済みのため緊急性は無いが、凍結解除の前提として要調査 | franklin-tradingのWAIT連発の根本原因(シグナル生成/発注ロジックのどこで止まっているか)が特定される | pending・低優先。黒字化の主戦場はx402(MKT-1)のためSOL-1凍結中は着手不要 |
| **PROD-1** | 商品数拡大(第1弾) — `/funding-rate-arb` を追加、既存 funding-rates 出力を取引所ペア全部で pairwise 比較(年率bps差降順+long/short方向)、新API不要・LLM不要 | 402(v2)+v2 buyer実購入(on-chain tx)+well-known掲載を実測 | ★第2弾DONE(2026-07-18朝)= 9→**31商品**★ 22個の決定的primitive追加(金融14: mortgage/loan-payoff/roi/npv/irr/dcf/cagr/apr-apy/break-even/present-value/future-value-annuity/savings-goal/percent-change/inflation-adjust、トレード5: position-size/kelly/liquidation-price/perp-pnl/impermanent-loss、utility3: hash/base64/timestamp)。v1/v2両server同一カタログ(v1に欠けてた funding-rate-arb も同期)。テスト67/67 PASS(serve-listen は並列時flaky=既知baseline、単独PASS)。3店とも live 31商品を実測(8412/8413/8414)。E2E実購入: franklin2 `/mortgage` 200+settle(tx `0x3424a94c…` receipt 0x1 block 48766868、sales-log settled:true)。x402scan再登録 franklin1/franklin2 とも registered:31、公開ページ Resources 31 表示を crwl 実測。commit `1554c62a`(anicca main)。第1弾: franklin2 402+v2 buyer 200(tx `0x9d524b92`)+arb計算spot-check一致(commit `89fd67a3`) |
| **RECOVER-1** | AUDIT-1で判明した座礁資金$20.37のうち自動回収可能分を流動化 — HL残高$7.72をArbitrumへwithdraw、Polymarket YES/NO重複ポジションをmerge | 座礁資金が流動USDCとしてwalletに着金しon-chainで確認できる | ★DONE(2026-07-17夜)★ ①HL withdraw $7.72→Arbitrum着金$8.22(HL accountValue $7.72→0で座礁解消) ②PM merge YES13/NO5→YES8/NO0=5ペア=$5回収。計~$12.7回収。claude-p自身の鍵でhumanゼロ、各tx on-chain検証。★続DONE(2026-07-17夜、次セッション)★ ③Arbitrum $8.21→Base ブリッジ完了(relay.link、fee $0.02=0.26%、approve `0x0b9b17db…`/deposit `0xe8eddd73…`、Base着金$10.13/Arb残$0.01をon-chain実測。script=`~/.anicca-founder/skills/earn/funding/bridge-arb-to-base.mjs`、fund-hl.mjsのcopy+tweak、鍵はwallet.json file読みでstdout非経由) ④残YES8株(Fed no-change 7月、cur 0.9565、解決07-29)は**売却せず満期hold→redeem.pyで$8.00回収が正**(place_order.pyはBUY専用で売却は新code=money-safety案件、+$0.35/12日の期待値でholdが合理的)。07-29後にredeem実行 |

| **XAUTO-1** | 進捗のX自動投稿 | — | ★DROP(2026-07-18 Dais指示「X投稿は不要」)★ Grok CLI認証(@aniccaen)は資産として残る |
| **BOUNTY-1** | ★次の主戦線★ ゼロ→イチ earn rail #2 = **bounty**。Dais 方針(07-18): 資本不要でゼロから稼げる rail を揃える(トレードは資本前提=ゼロ→イチに不適)。rail#1=x402-sell(仕組みは実証済: 402→settle→on-chain の全経路実測)。調査対象: Algora/Replit bounties/Gitcoin/gitpay 等、AI が自律参加可能か(account/KYC/human gate)を実測 → 研究MD → skill化(5-GATE 検証エンジン必須) → franklin 配備 | AI(franklin/claude-p)が bounty を1件受注→成果物提出→報酬受領を on-chain/実振込で確認 | 未着手(2026-07-18 登録)。DOC-1(README)の次 |
| **STAR-1K** | ★North star 2本目(Dais 2026-07-18)★ anicca repo 1,000 stars。baseline 実測(07-18): **stars 2 / forks 1 / watchers 0**。星の燃料 = ①README 刷新(DOC-1) ②人手ゼロ bootstrap で第三者が5分で1体立つ(OSS-2) ③「AI が external から実際に稼いだ」実証ストーリー(PROD-2/OBS-1 の on-chain 証拠) ④docs(DOC-2)。X は使わない(Dais 判断)、HN/Reddit/trending が候補 | stargazers_count ≥ 1000 | 登録のみ(2026-07-18)。実証(external 売上)が最強の星燃料 = PROD-2 が先 |
| **TOOL-1** | ★実バグ・最優先★ prompt/registry 乖離 — `prompt.mjs:120-127` が registry に存在しない `economy/gig` を「FIRST action MUST be」と毎wake命令(hl_trade/token_launch も dormant なのに推奨)= モデルに「選べない物を選べ」。tool-hallucination の教科書パターン(BFCL 失敗モード①)。根拠: docs/research/2026-07-18-agent-tool-calling-best-practice-and-franklin-gap.md | doctrine 記述が live slot から生成される(or 乖離検知テストが CI で fail する)。修正後の wake ledger で invalid slot 選択が消える | ★DONE(2026-07-18朝)★ anicca `c0a24f9`: DOCTRINE_LINES map で slot 別記述を live menu 所属でフィルタ、BOOTSTRAP block は economy/gig live 時のみ、MINDSET 一覧は動的生成、古い「7 preset paid routes」除去。実測: 実 live slot で生成した prompt に幽霊 slot 0件・gig live 時のみ BOOTSTRAP 復活。drift 回帰テスト4本追加(green)。loop 全 suite は 18 fail が変更前後で同一 = **既存の別問題**(known baseline、要調査は低優先)。3 loop kickstart 済み、00:50Z wake 完走確認 |
| **TOOL-2** | tool 定義を SKILL.md frontmatter から生成(詳細 description 3-4文/args schema/input_examples)。単一 `run_skill` enum を per-skill tool 化、catalog-gate で menu≤8 維持。ledger 結果を構造化 JSON 化して次wakeへ(生 stdout 900字廃止)。claude-p のテキスト模倣 tool 経路は CLAUDE-P-TOOLS で native 化(Claude Code skill+MCP、subscription 勢の onboarding 経路兼用) | franklin の wake で per-skill tool が渡り、前回結果が構造化されて読める。claude-p が native tool 経路で同一 menu を得る | ★Phase A DONE(2026-07-18朝)★ anicca `d1ad59b`: live 12 slot 全部に toolDescription(3-4文)+argsExample を registry に追加し wake prompt に描画(実測: prompt ~3.4k tok、12 slot 描画)、x402_sell の stale summary 是正、skill stdout 末尾 JSON 行の構造化 feedback(result-summary.mjs)。run_skill 契約/router は不可侵(PROP suite 保護)。テスト427/409 pass(fail 18 = 既存 baseline 同一集合)。registry を3 instance へ配布、3 loop 再起動、franklin1 wake 01:34Z slot=x402_sell exit=0 実測。**残 = Phase B(native per-skill tool 化、VCSDD 案件)と CLAUDE-P-TOOLS(native 経路)** |
| **SELF-STORE-1** | ★INV-EXT-4 の実装★ 店の全 lifecycle を franklin loop 自身に移管 — 現状は main session(俺)が serve 実装/x402scan 登録/launchd 設置を代行した = self-sufficiency 違反。x402-sell skill に「店が無ければ開く→well-known 生成→x402scan/Bazaar 登録→sales/attempts を見て商品を改廃→自分で再登録」の全手順を loop の action slot として配線し、新 instance が人手ゼロで店を持てる状態にする(OSS-2 の bootstrap と地続き) | 素の新 instance(店なし)が自 loop だけで「live 店 + x402scan 掲載」に到達したことを、main session が一切手を触れずに実測 | ★DONE(2026-07-18)★ anicca `a1f128b`+`be70421`: x402_sell slot に args.action 3種を実装(menu 不増、統合 tool 原則)。ensure=冪等開店+登録(ポート生存なら絶対に二重 spawn しない=07-17 ポート戦争の教訓を規則化、公開URL無しは registered:false 正直 degraded)、review=self/external 分離集約 JSON(self 名簿は lib/self-wallets.mjs に単一化)、update=カタログ変化で再登録。実 E2E(franklin1/franklin2 の実 harness 経路 run.sh dispatch): review 実データ・ensure 冪等(2回目 reregistered:false)・degraded・MALICE-GUARD 通過を全実測。live E2E でのみ出た2バグ(guard 未登録 source / state dir の home↔checkout 乖離)も修正済み。テスト77/77。3 instance 配布+loop 再起動済み。**「素の新 instance」の完全検証は公開 URL 供給(OSS-1 tunnel)が前提のため degraded path までで確認** |
| **PROD-2** | ★売れる商品への転換★ x402scan 30日実測(2026-07-18): 売上上位は LLM gateway(BlockRun $173K/JarvisClaw $559)・音声インフラ(dTelecom $19.3K)・**有料API転売**(StableEnrich $1.73K: Exa/Firecrawl 等を x402 で再販)・Xデータ(twit.sh $629)。電卓系は圏外 = PROD-1 の31商品は掲載価値のみで需要なし。franklin の次の商品は「買い手が自分でできない物」: 候補(a)**x402 転売 margin 型**(franklin が外部 x402 API を仕入れ→markup 再販、StableEnrich 型、資本≈float のみ) (b)free ソース集約の real-time 市場データ拡張(funding-rates 系の深掘り) | 外部 payer からの購入が on-chain で発生する(INV-EXT 準拠) | 未着手(2026-07-18 登録)。BOUNTY-1 と並ぶ「external 稼ぎ」の2本柱 |
| **PM-REDEEM** | claude-p の PM YES8株(Fed no-change 7月、cur 0.9565)を**07-29解決後**に redeem.py で$8.00回収→Baseへ | redeem tx on-chain確認+Base着金 | 待機中(解決日2026-07-29)。売却でなくholdが決定済(RECOVER-1行参照) |
| **OBS-1** | x402scan 掲載(07-17登録)を外部買い手がprobeするか14日観測(〜07-31)。観測面=sales-log/attempts-log/on-chain inbound | 外部payer(自colony 4wallet以外)からの実購入がon-chainで1件以上確認される | ★観測網完備 2026-07-17夜★ inflow-watch launchd を3体分に拡張: 既存 claude-p(0x904B…)/franklin2(0xe7747F…)に**franklin1(0x3EcCAD24…)を新設**(`ai.anicca.x402-inflow-watch-franklin1.plist`、30分毎、初回実行 external:0 を実測)。external>0 で flag file + macOS 通知が上がる。以後は待ち。★偽陽性対策(07-18)★: マシン既定 identity `0xB9dd3B67…`(resolve-identity fallback、self-probe の payer)を self 名簿に追加(anicca `6110dd3`) — franklin2 sales の9件はこの address = **self であって external ではない**(franklin1/franklin2 の real external は依然 $0) |

## ★★T9 の真因: 商品が構造的に売れない（2026-07-16 06:20、Dais 指示で実コードを読んで判明）★★

**比較対象 = `BlockRunAI/blockrun-mcp`（475★、実際に売れている x402 seller）**

| | 売っている物 | なぜ買われる |
|---|---|---|
| **blockrun-mcp** | 55+ LLM / image・video 生成 / prediction-market データ / live web・X search / **40+ chain の on-chain クエリ** / **★Polymarket に実際に賭ける行為★** | **買い手が自分では出来ない**。API キーが要る・インフラが要る・**行為**である |
| **我々の franklin/claude-p** | calc `$0.001` / JSON flatten `$0.001` / DNS lookup `$0.001` / 複利計算 `$0.001` / whois `$0.002` / research digest `$0.003` / stock quote `$0.003` | **買われない。買い手が自分で出来るから。** agent は電卓に $0.001 を払わない |

価格の実測（blockrun-mcp README 逐語）: *"**$5 covers** ~5,000 market queries · ~500 Exa searches · ~250 image generations · ~10 Seedance 1.5-pro clips"*
→ market query ≈ $0.001 / Exa search ≈ $0.01 / image ≈ $0.02 / video ≈ $0.50。**$0.001 の階層は「上流が有料の物」に使う価格であって、電卓の価格ではない。**

★**結論: 実需がゼロなのではない。実需が生まれ得ない商品を並べていた。**
  → `$0.011` が「同じ bot(`0xaf5bb59a…`) が両店を舐めただけ」「BlockRun 自己申告で 47% non-organic」なのは**当然の帰結**。
  → **claude-p が「利用可能スロットは全て実績$0の死亡アクション」と判定して sleep を選んだのは、商品を正しく評価していた。**
    agent はバグっていない。**我々が売れない物を持たせた。**
★**Dais 原則（2026-07-16）: 内部循環は ponzi。** 自分の店に自分で払う self-pay で「稼いだ」と数えるのは詐欺。
  → **T4a(self-pay で Bazaar 着火)は問題を解かない。** 着火して掲載されても、売る物が無ければ $0 のまま。
    着火は「掲載」という技術的前提を満たすだけで、**需要は1円も生まれない**。順序として T9 が先。
★**売れる物の条件（blockrun-mcp から抽出した法則）**: **買い手が自分では実行できないこと**を売る。
  ①上流が有料/要キー(Exa, 画像生成, 市場データ) ②インフラが要る(multi-chain RPC) ③**行為**そのもの(実際に賭ける・実際に送る)。
  **計算・整形・変換は全て「買い手が自分で出来る」= 売り物にならない。**

### ★★市場の実データで法則が確定した（2026-07-16 06:45、CDP Bazaar 公式 discovery API を直接走査）★★

`api.cdp.coinbase.com/platform/v2/x402/discovery/resources` を 3,000件走査（カタログ総数 **25,671**、値付き 2,972件）:

| 統計 | 価格 |
|---|---|
| min | $0.000001 |
| **p25** | **$0.005** ← ★我々の $0.001〜$0.003 はこれより**下**★ |
| median | **$0.01**（我々の10倍） |
| p75 | $0.03 |
| p90 | **$0.10**（我々の100倍） |
| p99 | $1.50 |
| max | **$1000** |

→ **我々は市場の最底辺（p25 未満）でノイズを売っていた。**

**高額 top12（= 買い手が実際に金を払う価値を認めた物）**:
```
$1000.000  api.bitrefill.com/x402/invoice/pay        ← ギフトカードを買う★行為★
$1000.000  api.jamton.network/v1/purchases/…         ← ★購入★
$ 350.000  mudko.com/api/x402/purchase               ← ★購入★
$ 190.000  mudko.com/api/x402/bazaar-keepalive       ← ★サービス★
$  99.000  mudko.com/api/x402/bazaar-listing         ← ★Bazaar 掲載を商品にして売っている★
$  25.162  blockmachine.io/user-management-api/x402/api-keys  ← ★API キーを売っている★
$  20.600  palmyr.ai/cards/buy                       ← ★カードを買う行為★
$  19.860  www.buywith402.com/products/:id/purchase  ← ★購入★
$  10.000  researcher.now/v1/x402/runs               ← ★実行★
$   5.000  laso.finance/get-card                     ← ★カード取得★
$   5.000  mudko.com/api/x402/audit                  ← ★監査サービス★
$   5.000  api.402.coffee/test/suite                 ← ★テスト実行★
```

★上位12件（**価格順**）に「データを返すだけ」の商品は1つも無い。全部が ①行為 か ②アクセス。
  → ただし**これは価格軸だけの話であり、ここから「データは売れない」と結論するのは誤りだった（下記で自己是正）。**

### ★★★是正: 上の2つの結論は両方とも間違いだった（2026-07-16 06:50、on-chain 実測）★★★

**「価格が安すぎる」「行為とアクセスしか売れない」— 実データが両方を否定した。**
カタログの価格は**言い値**であって売れた証拠ではない。**誰が実際に受け取っているか**を、我々自身に使ったのと同じ
`verify-inflow.mjs` で測った（48h・on-chain）:

| 店 | 掲載数 | inflows | 外部売上(48h) |
|---|---|---|---|
| `x402.ottoai.services` | 39本 | **8,637** | **$10.302** |
| `www.stratalize.com` | 51本 | 4 | $1.52 |
| `api.relaystation.ai` | 39本 | 34 | $0.38 |
| **franklin1** | 7本 | **0** | **$0** |
| **claude-p** | 7本 | 18 | $0.011（うち外部9件、bot） |

**ottoai が売っている物（= 8,637件売れた実物）**:
```
$0.0010 /crypto-news     $0.0010 /funding-rates    $0.0010 /kol-sentiment
$0.0010 /trending-altcoins  $0.0030 /tradfi-data   $0.0010 /defi-analytics
$0.0010 /token-details   $0.0010 /yield-alpha      $0.0010 /token-price
$0.0010 /twitter-summary $0.0020 /news-recaps      $0.0010 /filtered-news
```
→ **全部「データを返すだけ」。しかも単価 $0.001 = 我々と同じ価格帯。**
→ **価格は同じ。件数が 8,637 対 9 で 960倍違う。**

★★**本当の法則（実データから）**: **「買い手が自分で出来ないか」ではない。「買い手が繰り返し・今すぐ必要とするか」。**★★
```
ottoai:  crypto-news / funding-rates / kol-sentiment / trending-altcoins
         = 生きている・刻々変わる・特定ドメインのデータ
         → トレード agent が毎分必要とする → 180件/時の反復需要

我々:    calc / DNS lookup / JSON flatten / 複利計算
         = 静的・不変・汎用 → 必要とされる瞬間がほぼ永久に来ない → 9件/48h
```
- **変わり続けるデータ = 反復需要 = 金が流れ続ける。静的な計算 = 需要ゼロ = 何本並べても $0。**
- 掲載数は関係ない（stratalize は 51本で $1.52、ottoai は 39本で $10.30）。**中身が全て。**
- **買い手の正体 = トレード agent**（金を持つ最大の agent 人口）。ottoai の商品構成が全部 crypto/trading 向けなのはそのため。
- **x402 に金は実際に流れている。**「需要が無い市場」ではない。$10.30/48h ≈ $5/日 ≈ $150/月 を1店が取っている。

★**franklin1 はトレード agent そのもの**（sol-trade / HL / PM）。**同族が毎分何を欲しがるかを知っている立場に居る。**
  → 売るべきは「自分が毎回欲しくて、毎回自分で取りに行っているもの」。**自分の需要が市場の需要。**

★**Fable の誤り2件（記録）**: ①価格分布(p25/median)だけを見て「安すぎる」と結論 → 実売上を見ずに価格軸で語った。
②価格 top12 だけを見て「データは売れない」と結論 → **上位12件は市場の1%未満**。
**分布の端を見て中央を語った。**
一般法則: **カタログの価格は言い値。売れた証拠は on-chain の inflow だけ。**
「何がいくらで並んでいるか」ではなく「**誰にいくら入ったか**」を測る。→ [[feedback_self_reported_status_is_not_evidence]] と同型。

★皮肉として記録: **`mudko.com/api/x402/bazaar-listing` が $99 で「Bazaar 掲載」を売っている。**
  我々が「掲載されない」と半日悩んだものを、他者は商品化して99ドルで売っている。
  **問題だと思っていたものが、他人にとっては商品だった。**
★`blockmachine.io` は **$25 で API キーを売っている** = 「買い手が自分では手に入らない物」の教科書的実例。

**再現コマンド**（記憶で答えない）:
```bash
# 価格分布と高額 top を測る。NEEDLE 無しで市場全体を見る
node ~/anicca/skills/earn/x402-sell/bazaar-scan.mjs <needle>   # 我々の掲載を探す
# 市場全体の分布は discovery API を直接: limit=100&offset=N でページング、accepts[0].amount は 1e-6 USDC
```

## ★★★2026-07-16 06:30 — 最大の発見: Franklin は入っていて、一度も起動されていない★★★

Dais 指示「repo を読め」で `blockrunai/franklin`(624★) の実コードを読んだ結果:

```
実測:
  /opt/homebrew/bin/franklin              → ★v3.29.0 インストール済★
  @blockrun/franklin / @blockrun/clawrouter / @blockrun/franklin-trading → 全部入っている
  ~/.blockrun/skills/                     → ★我々の skill が既に同期済★
                                             (anicca-life-manager, cook, browser, …)
                                             = Franklin の user skill ディレクトリそのもの
  ~/.blockrun/skills/learned/             → ★空★ = Franklin は一度も学んでいない
                                             (一度も走っていないから)
  実際に走っているプロセス:
    node /Users/anicca/anicca/runtime/loop/index.mjs   ← ★我々の自作 loop★
```

**`~/.blockrun` は Franklin/BlockRun CLI の home。我々はそれを `ANICCA_HOME` として借り、
自作 loop を走らせていた。** `.solana-session` が「Franklin's OWN funded wallet」なのはそのため
（あの鍵は Franklin CLI の財布）。daemon の `synced skills ~/anicca/skills → ~/.blockrun/skills` は、
**知らないうちに Franklin の user skill ディレクトリへ配っていた。**

| Franklin が最初から持っていたもの | 我々の自作 loop |
|---|---|
| ClawRouter 内蔵（脳） | 別プロセスの共有 router に依存 → **今日 429 で脳死していた** |
| `budgetCapUsd`（skill 単位の USD ハードキャップ） | 無し（money-safety を手で書いていた） |
| `costReceipt`（支払い領収書を返答に添付） | 無し |
| wallet primitives（`setupWallet`/`setupSolanaWallet`…、`@blockrun/llm` 由来） | `resolve-identity.mjs` を自作 |
| Anthropic 仕様 `SKILL.md` ローダ（bundled/user/project/learned の union） | 自作レジストリ |
| `autoGenerated` + `source:'learned'` + `sourceSession` + `uses`（**Franklin が自分で skill を書き、使用回数で順位付け**） | 無し（self-improve を別途 T6/T10 で作ろうとしていた） |
| *"give your AI a budget and walk away"* = 予算境界つき自律 | 無し |

★**結論: 今日 Fable が半日かけて直した「脳(429)」「身元(wallet unknown)」「wallet 解決」は、
  Franklin が最初から持っていた機能の劣化コピーを修理していただけ。**
★**Franklin の skill 型（`src/skills/types.ts` 逐語）**: *"A "skill" is an **Anthropic-spec SKILL.md file**"*
  → **我々の `~/anicca/skills/*/SKILL.md` はそのまま Franklin に入る。**変換不要。
★**Anicca の仕事の定義が確定した（Dais 2026-07-16）**: *「Franklin も Claude も、既定では稼ぐ手段を持たない。
  **稼ぐための skill / tool を足すのが我々の役割**」*。実測で裏付いた — Franklin の src に `x402_sell` = **0 hits**、
  `earn` = 5 hits のみ。**Franklin は「買う側」の agent（`PHILOSOPHY.md`）。稼ぐ層は存在しない。そこが我々の層。**
  → **正しい形: Franklin を走らせ、`~/.blockrun/skills/<name>/SKILL.md` に earn skill を置く。**
     run.sh で plist を横から生成するのではなく、**公式の拡張点**を使う。

**未検証（次にやること。断定しない）**:
- Franklin CLI を実際に起動して、我々の earn skill を user skill として読むか
- 我々の自作 loop を Franklin に置き換えられるか（置換 or 併存の判断）
- Franklin の `budgetCapUsd` / `costReceipt` / `learned` が実際に動くか

## 読むべき正本（Dais 提供、2026-07-16）

| repo | ★ | 何を学ぶか |
|---|---|---|
| [blockrunai/franklin](https://github.com/blockrunai/franklin) | 624 | **我々の franklin の実体**。TypeScript/Apache-2.0。*"Franklin lets you give your AI a budget and walk away"* = **買う側の agent**。ClawRouter を内蔵。`PHILOSOPHY.md` / `CONTEXT.md` / `AGENTS.md` が設計の正本 |
| [BlockRunAI/blockrun-mcp](https://github.com/BlockRunAI/blockrun-mcp) | 475 | **売る側の実例**。何が売れるかの正解が全部ここに在る |
| [Daisuke134/blockrun-cli](https://github.com/Daisuke134/blockrun-cli) | 1 | Dais 作。blockrun-mcp の全 tool を CLI 化。`PARITY.md` / `VERIFICATION.md` |
| [BlockRunAI/ClawRouter](https://github.com/BlockRunAI/ClawRouter) | 6658 | 脳。**Franklin に内蔵済**。8 NVIDIA モデルが free forever |

★**Franklin の哲学（逐語）**: *"The wallet isn't a feature. The wallet is the mechanism that makes every other promise of autonomous AI actually hold."*
  *"We are about what the AI does when nobody is watching — and the thing that makes it safe to look away is the budget."*

## 使える既存解（車輪の再発明禁止。2026-07-16 gh search 実測）

| 穴 | repo | star | copy するもの |
|---|---|---|---|
| 掲載 | [x402-foundation/x402](https://github.com/x402-foundation/x402) | 6334 | `specs/extensions/bazaar.md`（登録 API を叩かず「402 レスポンスで広告する」方式） |
| 掲載 | [Merit-Systems/x402scan](https://github.com/Merit-Systems/x402scan) | 357 | `docs/DISCOVERY.md`。`/.well-known/x402` + `x402scan.com/resources/register` に URL POST で自動 index |
| 自己改善 | [NousResearch/hermes-agent-self-evolution](https://github.com/NousResearch/hermes-agent-self-evolution) | 4683 | `evolution/skills/evolve_skill.py`。trace から SKILL.md/prompt を GEPA で進化 → gate → PR |
| 自己改善 | [gepa-ai/gepa](https://github.com/gepa-ai/gepa) | 5660 | Reflective Prompt Evolution 本体 |
| 共有 | [dvcrn/openclaw-skills-marketplace](https://github.com/dvcrn/openclaw-skills-marketplace) | 23 | openclaw skill → SKILL.md 変換（弱いモデルへ配る導線） |
| 需要 | [google-agentic-commerce/a2a-x402](https://github.com/google-agentic-commerce/a2a-x402) | 536 | A2A に x402 決済を統合（agent が agent に売る標準） |
| 需要 | [ChaosChain/chaoschain-genesis-studio](https://github.com/ChaosChain/chaoschain-genesis-studio) | 40 | ERC-8004 + x402 の完動デモ |
| **席(T2b)** | [tailscale/tailscale](https://github.com/tailscale/tailscale) `tsnet/` | 24k+ | **"Multiple independent Tailscale nodes can run within a single binary"** = 各 instance が独立ノード = 各自 443/8443/10000。席の奪い合いが消える |
| **認証(T2b-1)** | [tailscale/tailscale](https://github.com/tailscale/tailscale) `cmd/get-authkey/main.go` | 同上 | **OAuth client から auth key を自動生成する公式ツール。自作禁止。** env `TS_API_CLIENT_ID`/`TS_API_CLIENT_SECRET`、flag `-tags`(必須)/`-reusable`/`-ephemeral`/`-preauth` |

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
