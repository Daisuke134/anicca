# Agent 経済 FULL MAP — to-be ループ + 世界の競合全景 + 我々が解く問題 + 欠けピース

SSOT: 本ファイル(2026-07-11)。内部ループの実行 TODO は `23-anicca-loop-architecture-redesign.md` §8+§9 が正本。本ファイルはその**上の戦略層**（世界の中で我々がどこを解いているか）。

honesty ラベル: **[V]**=research/ファイルで確認 / **[R]**=既知情報から推論 / **[?]**=未確認・要検証。
金の真実: 「稼いだ」= `external:true` 実 tx を on-chain 確認時のみ。report/test-green は稼ぎでない。

---

## 0. 一行の結論

世界は agent 経済の **"配管"（決済/wallet/発見/通信）を 2026 に全部作り終えた**。だが **"エージェントが本当に価値を生んだかの証明（proof-of-earning）" と "実需要" と "実 P&L で自己改善する仕組み" は誰も解けていない**。我々が build しているのは**まさにこの空白層**。ただし我々もまだ解けていない（実現利益は colony 生涯 $5 のみ）。よって我々の立場 = **「先行者」ではなく「業界と同じ最前線に立ち、皆が避けた検証層に賭けている挑戦者」**。

---

## 1. 我々の稼ぐ主体（3+1 citizen）と to-be earn ループ

**[V]** own-eyes on-chain（§9, 2026-07-11）+ 内部棚卸し。realtime は `bash ~/anicca/skills/self/colony-status.sh`。

| citizen | HOME | wallet | 燃料 | 今の残高 | 実現利益(生涯) | 状態 |
|---|---|---|---|---|---|---|
| **claude-p（私）** | `.anicca-founder` + pm | 0x810f(Base) / 0x904B(Polygon pUSD) | human-funded | pm $4.95🔒 | **$5.00**(pm redeem tx 0x20ee0c4e) = colony 唯一 | 🟡 pm が $5床で凍結 |
| **Franklin 1** | `.blockrun` | 8Fpqd(Sol) + 0x3EcCAD(Base) | ★self-funded★ | Sol $3.44+0.02SOL / Base $6.48 | $0 | 🟡 sol-trade は WAIT 継続、推論課金で微出血 |
| **Franklin 2** | `.franklin2-home` | 0xe774 | ★self-funded★ | 未確認[?] | $0 | 🟡 live(PID 6026)だが earn 実績未確認 |
| automaton | `.anicca` | 0xB9dd(Base) | ★self-funded★ | $0.59 | $0 | 🔴 実質 dormant |

**共通の to-be ループ（全 citizen 同一の型、= SSOT §8 ASCII）**
```
 各 citizen（別 HOME・別 wallet・同じ runtime/loop/index.mjs = always-act-router）
 ┌─ 各 wake ─────────────────────────────────────────────┐
 │ ① earn-menu を見て1つ選ぶ                             │
 │    {pm / sol / hl / yield / x402 / lending / spawn /  │
 │     clip / video / cook}  ← registry.json status:live │
 │ ② 選んだ base agent が自分で分析 → trade/action      │
 │    (金欠・gas欠を除去済なら撃つ。no-edge WAIT は正常) │
 │ ③ ★GROUND-TRUTH VERIFY（prompt+tool、報告を読まない）│
 │    on-chain external:true を自分の目で。observ 無=FAIL│
 │ ④ 未達/嘘 → self-fix(別ctx) → 根因 fix → 再発防止 code│
 │ ⑤ 稼ぎ余剰 → lending → 他 citizen → Akash spawn → 拡大│
 └───────────────────────────────────────────────────────┘
 DAIS = 完全に外（GO 不要、crypto が増える通知を見るだけ）
```

**earn-menu の稼ぎ方の分類**（重要 = §3 の「需要問題」への我々の耐性を決める）
| slot | 稼ぎ方 | 需要側は誰か | 我々の実態[V] |
|---|---|---|---|
| pm / sol / hl | market trade（予測市場・perp・spot） | **市場そのもの（外部需要 unneeded）** | pm=$5実現/sol=WAIT/hl=$0 |
| yield | DeFi vault に idle 資金 | プロトコル（需要 unneeded） | 未確認[?] |
| x402_sell | 研究 API 販売 | 他 agent/人（**需要必要**） | mainnet 実売 $0.003 主張[?] |
| gig | agent間労働市場 | 他 agent（**需要必要**） | **Base Sepolia testnet のみ**[V] |
| clip / video | 動画→視聴報酬 | 視聴者（**需要必要**） | 別垢乱造/grid空=broken[V] |
| lending / spawn | citizen 間金融・自己複製 | colony 内部 | 実発火ゼロ[V] |

→ **trading 系(pm/sol/hl/yield)は外部需要が要らない**（相手は市場）＝業界の最大ボトルネック「需要不在」を回避できる唯一の rail。gig/clip/video は需要必要かつ壊れ＝優先度を下げるべき（§6 M2）。

---

## 2. 世界の agent 経済マップ — 何が動き、何が嘘か

**[V]** 外部調査（※ web-source。特定の traction 数値は firecrawl 再検証してから賭ける）。

### 🟢 実 mainnet で動く = 再発明禁止・copy 元
| 層 | 勝者 | 状態 | 出典 |
|---|---|---|---|
| 決済プロトコル | **x402**(Coinbase/Foundation) | Base/Sol mainnet、69k agents/165M tx/~$50M累積主張。加盟に AWS/Visa/Stripe/Google/MS | coinbase.com/developer-platform/discover/launches/x402 |
| agent wallet/custody | **Coinbase AgentKit / Agentic Wallets(CDP)** | MPC+session cap+x402 ネイティブ、`npx awal`、MCP対応 | .../launches/agentic-wallets |
| 発見/registry | **x402 Bazaar** | 機械可読カタログ、無料 listing | .../launches/x402-bazaar |
| agent間通信 | **Google A2A** | v1.0 stable、150組織 production | stellagent.ai/insights/a2a-protocol |
| 支払い意図の署名 | Google AP2 / Skyfire KYA | 規格は本物、実 tx 量は未開示 | cloud.google.com/blog/.../ap2-protocol |

### 🟡 動くが投機・デモ止まり / 🔴 vaporware = 乗らない
| プレイヤー | 実態 | 判定 |
|---|---|---|
| Virtuals ACP | revenue Q4'24 $20.6M→Q1'26 $3.0M 急減、投機フィー | 🟡下降 |
| Olas/Autonolas | 16.4M tx あるが marketplace 生涯 turnover **$89K**、token -99.6% | 🟡tx有・収益失敗 |
| Fetch.ai/ASI | ローンチ連発だが Ocean 離脱、deployments は vanity | 🔴 |
| ai16z/ElizaOS | token $1.5B→$484K、集団訴訟。経済実験は崩壊 | 🔴 |
| Truth Terminal | a16z から$50K「贈与」+GOAT 投機。**労働対価でない典型ハイプ** | 🔴 |
| Freysa/Wayfinder | ロードマップ全て未来形、実績非開示 | 🔴/🟡 |
| RentAHuman | 人間 67万人登録 vs **active employer <100**。需要ほぼゼロ | 🟡供給過多 |

---

## 3. まだ誰も解けていない穴（= 我々の機会）

| # | 穴 | 証拠 | 我々との関係 |
|---|---|---|---|
| **①** | **proof-of-earning / 検証層がほぼ空白** | 該当は全て 2026 の arXiv 論文段階（AgentReputation / Proof-of-Execution / Notarized Agents）。自ら「agent は評価を gaming する・未解決」と認める。production 実装ゼロ。唯一近い Morpheus TEE は「推論の検証」で「収益の真正性」でない | **我々の SSOT の中心そのもの**。ground-truth verifier / `external:true` on-chain / 「report は嘘」= Dais 脳外科ルール = 業界最前線と同じ結論に到達済み |
| **②** | **需要側の不在（供給過多）** | CoinDesk「x402 は micropayment を直すが demand is just not there yet」。RentAHuman/Olas が実証 | 損失診断(§9)と一致。**trading 系(相手=市場)は需要不要**＝我々はこの穴を回避できる |
| **③** | **投機と実収益の分離不能** | Virtuals/Olas とも token 投機・fee-farming ドリブンで急減中。「投機で回ってない持続経済」の実例皆無 | 「稼いだ=external:true 実 tx のみ」定義がこの分離を強制。fitness を実 P&L に繋ぐ(§9 R1)= 業界の穴③への直接の解 |
| **④** | **ポータブル reputation**（横断・sybil 耐性） | 学術提案止まり | 将来拡張余地 |

---

## 4. だから我々が解いている問題（positioning、正直版）

```
 世界が作り終えた「配管」          誰も作れていない「上物」= 我々の賭け
 ┌─────────────────────┐          ┌──────────────────────────────────┐
 │ x402   (払う)        │          │ ★proof-of-earning★              │
 │ AgentKit(持つ)       │  ─────▶  │  外部価値を本当に生んだかを        │
 │ Bazaar (見つける)    │  この上に │  report でなく on-chain で証明      │
 │ A2A    (話す)        │  乗せる   │ ★fitness=実P&L の self-improve★  │
 └─────────────────────┘          │  投機でなく実弾で自己進化          │
                                    │ ★closed loop の自律 citizen 群★   │
                                    │  human ゼロで verify→self-fix→拡大 │
                                    └──────────────────────────────────┘
```

- **配管は x402 スタックを copy する**（車輪の再発明禁止）。独自 payment/wallet/registry/通信を作らない。
- **我々の差別化 = 検証層 + 実弾 self-improve + closed-loop citizen 群**。皆が「agent が稼いだ！」と report/token 価格で主張する中、我々だけが「on-chain external:true でなければ稼いでない」を構造的に強制する。
- **★ 正直な現在地 ★**: 我々もまだ解けていない。colony 実現利益は生涯 **$5**（pm redeem 1回）。検証層(reality-verifier)は**設計止まり・未実装**[V]、self-improve の openevolve 統合は**未確認**[?]、我々自身が §9 で Goodhart（backtest 最適化して実弾 -$8.6）に落ちた＝**業界の穴③を我々の内部で再現した**。よって「先行」とは言わない。**同じ最前線で、皆が避けた検証層に賭けている**が正確な立場。

---

## 5. 現在地 → to-be のギャップ表

| 能力 | to-be | 現状[V] | ギャップ |
|---|---|---|---|
| 実 earn | 各 citizen が external:true を継続産出 | 生涯 $5(pm 1回)、他は WAIT/$0 | 実 tx がほぼ無い |
| 検証層 | 各 loop 内で on-chain 独立検証（reality-verifier） | verify-tx.mjs(tx検証)/earn-detect.mjs は実在。reality-verifier は doc24 設計のみ**未実装** | 核が未実装 |
| self-improve | fitness=実 on-chain P&L | openevolve 統合**未確認**、§9 は backtest(oos)最適化=Goodhart | fitness が実弾でない |
| adverse-selection | 片側約定 naked を出さない | pm MM で -$8.6 発生 | 漏れ未修正 |
| always-act 強制 | 全 citizen | **Franklin のみ**（wallet==.blockrun gate） | claude-p/Franklin2 未適用 |
| 資金集約 | Franklin 資金を Solana に寄せ bankroll 厚く | Base $6.48 が idle 分断 | 未集約 |
| 需要不要 rail への集中 | trading 中心 | gig=testnet/clip=broken に労力分散 | 優先度誤り |
| spawn/lending | 稼ぎ余剰で拡大 | 実発火ゼロ（seed 1件） | 稼ぎが無いので発火せず(正しい依存) |
| OSS 化 | 外部依存ゼロで他人が動かせる | .openclaw 等に 328+参照 | confine 未完 |
| rail 準拠 | x402 mainnet で売買 | x402-sell は $0.003 主張[?]、gig は testnet | mainnet 移行未確認 |

---

## 6. 欠けピース TODO（戦略層 M シリーズ）

実行 TODO は §8/§9 が正本。本節は**世界マップから出た戦略的欠けピース**を追加する。

| ID | 欠けピース | 根拠 | done 条件 | 依存 |
|---|---|---|---|---|
| **M1** | reality-verifier(検証層)を doc24 設計 → 実装。**我々の #1 wedge** | 穴①、§5 核が未実装 | 各 loop の wake で on-chain external:true を独立確認する verifier が実走 | §9-1',§8-7/8 |
| **M2** | fitness を実 on-chain P&L に繋ぐ（openevolve が earn-ledger external:true を読む） | 穴③、§9 R1、Goodhart | evolve の評価関数が backtest でなく実 tx を読む | M1 |
| **M3** | openevolve が実際に fork/統合されているか検証、無ければ統合 or 撤回 | 内部棚卸しで統合コード未発見[?] | fork の実在をファイルで確認 or docs から撤回 | — |
| **M4** | 稼ぎを**需要不要 rail（pm/sol/hl/yield）に集中**、gig/clip/video を降格 | 穴②、gig=testnet/clip=broken[V] | registry 優先度が trading 系上位、broken slot は status 降格 | — |
| **M5** | 配管は x402 スタックに準拠（独自を作らない）。x402-sell/gig を mainnet x402 へ | 🟢部品は copy、gig=Sepolia のみ[V] | gig/x402-sell が x402 mainnet で1 tx | — |
| **M6** | always-act 強制を全 citizen に（今 Franklin のみ） | §5 gap | claude-p/Franklin2 も always-act gate に載る | — |
| **M7** | pm MM の adverse-selection を止める | 穴③、§9 R2 | 片側約定 naked が起きないコード | — |
| **M8** | Franklin Base $6.48 → Solana 集約（self-funded・許可不要） | §9 R4 | 8Fpqd の USDC 増を on-chain 確認 | — |

**クリティカルパス**: M3(openevolve 真偽) → M1(検証層) → M2(fitness を実弾) → M7(漏れ止め) → M8(bankroll) → §9-4'/5'(1 wake で external:true 実 tx)。ここが緑になるまで拡大(spawn/dashboard)に進まない。

---

## 7. 検証の宿題（この MD 自体の [?] を潰す）
- 外部 traction 数値を `firecrawl scrape x402.org/docs, ap2-protocol.org` で一次裏取り（今回は web-source）。
- `bash ~/anicca/skills/self/colony-status.sh` で realtime 残高に §1 台帳を更新。
- `economy/gig/MAINNET.md` と openevolve fork の実在をファイルで確認（M3/M5）。
- Franklin2(.franklin2-home)の earn 実績を trace で確認。
