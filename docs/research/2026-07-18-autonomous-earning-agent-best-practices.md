# 自律収益 agent の best practice（実ソース裏取り、2026-07-18）

調査: bp2-research（web、4問）。統合: main。目的: franklin が x402 で外部から稼ぐための工学+商業の実践を確定。

## Q1 自律収益アーキテクチャ
- **「自律出力 ≠ 自律収益」= 最大の失敗モード。** Claude Code 72h で 7商品/150投稿/6配信 → 転換ゼロ。ボトルネックは生成でなく trust/distribution/real demand。franklin の $0 はこれそのもの。〔HN #47417016 https://news.ycombinator.com/item?id=47417016〕
- **経済的自律が運用的自律を可能に。** wallet/決済は基盤であって後付けでない。card rail は micropayment を非経済化 → x402 の $0.0001/tx が要件。〔dev.to/sendersby https://dev.to/sendersby/building-autonomous-agents-that-can-actually-make-money-the-case-for-agent-financial-infrastructure-2lnj〕
- **★Bazaar は「登録」でなく「決済成立」で載る。** CDP Facilitator が有効 x402 payment を初 settle した瞬間に endpoint を自動 catalog、trust signal は on-chain 活動から導出。→ **最初の1txそれ自体が discovery の起点**。〔CDP Bazaar docs https://docs.cdp.coinbase.com/x402/bazaar〕
- spending policy（日次上限/vendor cap）を焼けば承認不要で24/7動く。〔Coinbase Agentic Wallets、403で二次ソース〕

## Q2 自己改善/市場適応ループ
- **GEPA(DSPy) = scalar reward でなく実行トレースへの自然言語リフレクションで戦略進化。** MIPROv2 比 +13% を 1/35 の rollout で。observe→imitate→ship の critique 段に直接使える。〔arxiv 2507.19457 https://arxiv.org/pdf/2507.19457 、https://dspy.ai/api/optimizers/GEPA/overview/〕
- **何を売るか = multi-armed bandit。** A/B（探索後に活用）と違い MAB は実データで配分を動的更新し regret 最小化。X2-LOOP は「上位コピー=活用」＋「新商品=常時探索枠」。〔VWO https://vwo.com/blog/multi-armed-bandit-algorithm/〕
- **confident hallucination を検証段で殺す。** 存在しないファイルにテスト書き「passing」と報告する固有失敗 → ファイル実在チェック必須。〔dev.to https://dev.to/zeroknowledge0x/the-agent-economy-how-ai-agents-are-earning-real-money-in-open-source-and-why-most-fail-9j2〕

## Q3 エンジニアリング規律（重複/死骸）
- **リファクタ前に characterization test（Feathers）**: 現状挙動（バグ含む）を先に固定 → 観測変化を即 surface。serve 3本→1本の前に各の現挙動をテスト固定。〔Sourcegraph https://sourcegraph.com/blog/legacy-code-modernization〕
- **Strangler Fig（Fowler）で段階置換**: 新実装を旧と並走 proxy で移行、小さく可逆。boot 6本→1本も一気にやらない。〔Shopify Eng https://shopify.engineering/refactoring-legacy-code-strangler-fig-pattern 、Azure https://learn.microsoft.com/en-us/azure/architecture/patterns/strangler-fig〕
- 正しい順序 = **挙動テスト固定 → 依存隔離 seam → 小刻み可逆 → system 置換に Strangler**。

## Q4 共有 vs 独立
- **共有 = framework + 学習戦略、独立 = keys/funds/state。** swarm は blackboard（共有 state store）+ handoff で協調、鍵/資金は各 agent 自己完結。現行 colony（同 skill/別 wallet/別 HOME）はこの通りで整合。〔Augment https://www.augmentcode.com/guides/swarm-vs-supervisor〕
- production 要件 = centralized state 管理・identity-aware 実行・高 observability。学習は共有 blackboard へ、実行 identity は per-agent gate（既存 ANICCA_HOME gate と一致）。〔truefoundry https://www.truefoundry.com/blog/multi-agent-architecture〕
- **[GAP]** 金銭保有 wallet-owning fleet 間で learned strategy を安全共有する固有 prior art は未確認（汎用 swarm 止まり）。

## 今すぐ採用 TOP 5
1. **最初の1txに全集中（X4）。** Bazaar は決済成立で自動掲載 = discovery の前提。出力量でなく実需×trust。
2. **商品を「集中」に。** bounty 事例は3リポ集中で承認 24%→70%。電卓31個を捨て、他人ができない1-2種に絞る（X2）。
3. **検証段にファイル/機能の実在チェックを強制**（confident hallucination 対策、既存 memory 規律と一致）。
4. **X2-LOOP を MAB として設計**: 活用（上位コピー）＋常時探索枠、critique 段に GEPA リフレクション。
5. **REFACTOR は characterization test → seam → Strangler の順**（いきなり3→1にしない）。

## GAP（未検証）
①金銭保有 fleet の戦略共有 prior art ②Agentic Wallets の Earn skill 詳細（403）③bounty 記事原典（403、dev.to 版で代替）。
