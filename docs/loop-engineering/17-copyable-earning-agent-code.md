# 17 — Copyable code for an always-act earning agent + how every other agent economy works (code-level)

> 2026-07-11。owner「車輪を再発明するな。他人の実コードを読んで copy しろ。1.7 を code レベルで詳細に」への回答。記事②の「他者の手法 vs 我々」章 + Franklin always-act 実装の copy 元。※二次情報混在（gh clone まで未実施の項は明記）。

## 我々の課題への copy リスト（ランク付き、repo/file/pattern → Franklin のどこに挿すか）

| 優先 | repo | 読んだ物 | Franklin への適用点 | LIVE? |
|---|---|---|---|---|
| ★★★★★ | `valory-xyz/open-autonomy`(Olas) | `packages/valory/skills/abstract_round_abci/base.py`（FSM: Round は必ず next_round へ遷移） | **「毎 wake 必ず1 skill 実行、idle 禁止」の強制遷移の型** = always-act の骨格 | LIVE(v0.21.26, 2026-07) |
| ★★★★☆ | `ChaosChain/trustless-agents-erc-ri`(ERC-8004) | IdentityRegistry.sol(register/setAgentWallet) / ReputationRegistry.sol(giveFeedback, **self-feedback 禁止**) / ValidationRegistry.sol(**self-validation 禁止**)。Sepolia deploy、test 74/74 | **agent 間の与信/評判/検証を on-chain で** = loan/gig の相手選び・spawn 判断の入力。自己 feedback/validation 禁止の不正防止をそのまま輸入 | LIVE |
| ★★★★☆ | `freqtrade/freqtrade` FreqAI | 別スレッド継続 retrain、model 差し替え | **realized P&L から戦略を自己更新**の型 → self-fix harness に retrain interval を移植 | LIVE |
| ★★★☆☆ | `Virtual-Protocol/acp-node` | `respondJob/payJob/deliverJob` + state machine `open→budget_set→funded→submitted→completed/rejected` | **loan/gig 発注の state machine の型** | LIVE(npm) |
| ★★★☆☆ | `coinbase/x402`(→x402-foundation) | X-PAYMENT ヘッダ、facilitator EIP-3009 USDC 決済 | Franklin↔Franklin 決済の標準。**既に P2 witness で mainnet 実証済**（`0x436143c1`） | LIVE |
| ★★☆☆☆ | `hummingbot/hummingbot` controllers | 複数 controller を1 bot で同時稼働、`total_amount_quote` で budget 配分 | 複数 earn skill への予算分割 | LIVE |
| ★★☆☆☆ | `Fetch.ai uAgents` | `on_interval(period=N)` デコレータ | 「wake ごとに必ず何かする」最小の強制型 | LIVE |
| ★★☆☆☆ | `elizaOS/eliza` `packages/core/src/actions.ts` | action(name/description/examples/handler) 構造 | skill=tool テンプレ（既存 `feedback_skills_give_tool_not_decision` と整合）。選択強制ロジックは要追検証 | LIVE(枠組み活発、ai16z 運用は崩壊) |
| 既存採用 | Mahoraga（LinUCB/Thompson bandit + Lagrange budget pacer） | memory `reference_ceo_manager_explorer_multiagent_bp_2026_07_08` | **capital allocation はこれを維持**（今回上回る新候補なし） | 採用済 |

## 1.7 — 他の agent 経済は「どう動き・どうスケールするか」（code レベル）

| project | 身元/wallet | 仕事の発見・決定 | 支払い | スケール機構 | merit | problem | 我々が copy する点 |
|---|---|---|---|---|---|---|---|
| **x402** | X-PAYMENT ヘッダ、facilitator が EIP-3009 USDC 検証 | server の 402 応答が対価提示、client が選ぶ | facilitator(Base/Sol/Arb…) | facilitator 複数対応、決済量 | 単純・標準・実証済 | 決済のみ（discovery/与信は別） | 決済層そのまま（実証済） |
| **ERC-8004/ChaosChain** | ERC-721=agentId、setAgentWallet | Reputation/Validation の on-chain 評判で選ぶ | 別実装 | 標準 registry で誰でも同じ土俵 | 不正防止設計(自己 feedback/validation 禁止) | 決済を規定しない | 与信ロジック＝loan/spawn 判断入力 |
| **Virtuals ACP** | agent wallet(EVM) | `acp browse` で job 発見 | job escrow(fund→submit→complete/reject) | job market volume | escrow state machine が綺麗 | トークン投機色 | loan/gig 発注の state machine |
| **Olas/Autonolas** | on-chain agent NFT registry | **FSM(ラウンド、必ず次状態へ)** | OLAS + marketplace | Mech Marketplace requester/operator | **「必ず遷移＝idle しない」思想が我々の no-WAIT に最も近い** | turnover $87K=量産ハイプの罠 | **FSM 強制遷移＝always-act の型** |
| **elizaOS** | plugin ごとに wallet action | LLM が action カタログから選ぶ | plugin 経由 | plugin marketplace | 最も活発な枠組み、action 構造が skill=tool | ai16z 運用は崩壊・詐欺訴訟 | action(name/desc/examples/handler) テンプレ |
| **Fetch.ai uAgents** | seed phrase, Agentverse mailbox | `on_interval`/`on_message` | 別レイヤ(FET) | Agentverse で発見 | `on_interval` が最小の強制実行型 | 決済は別 | wake 強制実行の型 |
| **Skyfire(KYAPay)** | KYA-verified JWT | — | JWT で USDC 即時 | provider review | KYA=相手の信用審査 | 独自レール | loan 相手の審査参照 |
| **Nevermined** | Payments SDK | — | credit-based, $0.001〜 | 5分 integration | micropayment 最小単位 | — | 課金モデル |

## ASCII — 収束する標準スタック（どこも同じ層に落ちる）

```
   [Identity]  ERC-8004 (agentId=ERC-721, on-chain 評判)  ← Franklin も使用
        │
   [Wallet]   AgentKit / GOAT / 自前              ← 我々=自前(gap: AgentKit 未使用)
        │
   [Discovery] Agentverse / ACP browse / gig board ← 我々=自前 gig board
        │
   [Decide]   ★always-act loop（Olas FSM=必ず遷移, uAgents on_interval, eliza action）
        │      我々: brain.mjs が skill を tool として選ぶ（既にある）+ idle 禁止(建設中)
        │
   [Pay]      x402 (EIP-3009 USDC) / ACP escrow    ← 我々=x402 facilitator(実証済)
        │
   [Scale]    spawn(population) / token / marketplace volume
             我々: Franklin 自己 spawn + gig/lending economy（実 USDC で測る）
```

## 我々の設計判断（他者の merit を copy・problem を回避）
1. **always-act** = Olas FSM「必ず次状態へ」+ uAgents `on_interval` を copy → idle/WAIT を構造的に禁止。
2. **与信/評判** = ERC-8004（自己 feedback/validation 禁止）を loan/gig/spawn 判断に。
3. **capital allocation** = 既存 Mahoraga bandit + budget pacer（新規探索不要）。
4. **self-improve** = FreqAI 型 retrain を self-fix harness に。
5. **スケール指標** = tx 数でなく**実 USDC 決済額**（Olas の罠を回避）。
6. **決済** = x402（実証済 `0x436143c1`）。

## 次の追検証（gh clone で行番号確定）
`valory-xyz/open-autonomy` の FSM act 本体 / `Virtual-Protocol/acp-node` 実装 / `elizaOS` processActions の強制ロジック。関連 [[15-agent-economy-landscape]] [[16-self-improvement-loop-BP]]。

## 各アプローチの ASCII（1つずつ、mechanism を図解）

### x402（決済層）
```
 agent ──GET /api──▶ server
      ◀─402 "pay $0.001 USDC"──
 agent ──再送 + X-PAYMENT(EIP-3009署名)──▶ server ──▶ facilitator /verify,/settle
                                                        └─on-chain USDC 移動─▶ agent に応答
 学び: 決済だけ・超シンプル・実マネー。我々=self-host facilitator で採用済(mainnet実証)
```

### ERC-8004 / ChaosChain（身元・信用層）
```
 register(agentURI) ─▶ IdentityRegistry(ERC-721) ─▶ agentId
 仕事後: giveFeedback(agentId,評価) ─▶ ReputationRegistry  (★自己feedback禁止)
 検証:   validationRequest/Response ─▶ ValidationRegistry  (★自己validation禁止)
 別agentが「この Franklin に貸すか?」→ on-chain 評判を照会して判断
 学び: 与信を on-chain 標準化。我々=gig board で採用、loan/spawn 判断入力に
```

### Olas / Autonolas（意思決定＝FSM、no-WAIT の型）
```
  ┌─Round A─┐   end_block   ┌─Round B─┐   end_block   ┌─Round C─┐
  │ 合意形成 │ ───必ず遷移──▶│ 実行    │ ───必ず遷移──▶│ 決済    │─▶…
  └─────────┘              └─────────┘              └─────────┘
  ★構造的に idle できない(必ず次state)= 我々の NO-WAIT に一番近い
  ⚠罠: 1450万tx でも turnover $87K = tx数ハイプ → 我々は実USDCで測る
```

### Virtuals ACP（取引 state machine）
```
 open ─▶ budget_set ─▶ funded(escrow) ─▶ submitted(deliver) ─▶ completed(escrow解放)
                                                    └─▶ rejected(返金)
 学び: escrow 付き agent 間取引の型。我々 gig board が同型(post→take→deliver→verify_and_pay)
```

### elizaOS（skill=tool、ただし運用は崩壊）
```
 action{name,description,examples,handler} を登録
 LLM ──action カタログから選択──▶ handler 実行(wallet plugin 経由 transfer 等)
 学び: action 構造=skill=tool と一致。⚠ai16z 運用は $2.6B→$650K 崩壊+詐訴
        = 「動いてる風」を実tx検証で排除する教訓
```

### Fetch.ai uAgents（強制実行の最小型）
```
 @agent.on_interval(period=N):   # N秒ごとに必ず実行
     do_something()
 学び: 「wake ごとに必ず何かする」最小型。我々の wake cron と同型 → always-act に流用
```

### 我々（統合）
```
 x402(決済) × ERC-8004(信用) × Olas-FSM+Fetch(NO-WAIT決定) × ACP(取引) × Mahoraga(配分) × FreqAI(自己改善)
   を 1つの self-funded citizen loop に束ねる。novelty = 決済×身元×NO-WAIT×自己改善 の統合(他社は各層バラバラ)
```
