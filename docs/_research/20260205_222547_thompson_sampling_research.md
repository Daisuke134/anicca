# Thompson Sampling ベストプラクティス調査 (2026年2月版)

## 調査情報

| 項目 | 値 |
|------|-----|
| 調査日時 | 2026-02-05 22:25:47 |
| 調査対象 | Thompson Sampling for Content/Hook Selection |
| 対象バージョン | 2025-2026年の最新研究 |

---

## エグゼクティブサマリー

Thompson Sampling は Multi-Armed Bandit 問題における最も効果的なアルゴリズムの1つであり、特に**非定常環境（Non-Stationary）**や**コールドスタート問題**において優れたパフォーマンスを発揮します。

### 主要な発見

| 項目 | 推奨事項 |
|------|---------|
| **アルゴリズム選択** | Thompson Sampling > UCB > Epsilon-greedy（ほとんどのケースで） |
| **コールドスタート対策** | Dynamic Prior Thompson Sampling（2026年2月発表） |
| **非定常環境** | Discounted Thompson Sampling または Sliding-Window Thompson Sampling |
| **Prior設定** | Beta(1,1)の代わりに、ベースライン成功率を反映したDynamic Prior |
| **探索率** | ε=10%（moderate）、保守的な場合は1-3% |

---

## 1. Discounted Thompson Sampling（非定常環境向け）

### 概要

**非定常環境**とは、報酬分布が時間とともに変化する環境を指します。例えば、ユーザーの嗜好が変わる、新しいコンテンツが登場する、トレンドが移り変わるなど。

### 実装方法

| 手法 | 説明 | 適用シーン |
|------|------|-----------|
| **Discounted TS** | 過去の報酬に割引係数を適用して、古いデータの影響を減衰させる | 急激に変化する環境（Abruptly Changing） |
| **Sliding-Window TS** | 直近N個のサンプルのみを使用 | 定期的に変化する環境 |

### パフォーマンス

2025年1月の研究によると、Discounted Thompson Sampling は以下のアルゴリズムよりも**累積リグレット（Cumulative Regret）が低い**：

- Epsilon Greedy
- SoftMax
- Upper Confidence Bound (UCB)
- 標準 Thompson Sampling（非割引）

### Regret Bound

両手法（Discounted TS と Sliding-Window TS）のリグレット上限は以下の通り：

```
O(√(T * B_T))
```

- T: 時間ホライズン
- B_T: ブレークポイント数（分布が変化する回数）

この上限は、理論的な下限と対数因子を除いて一致しています。

---

## 2. Dynamic Prior Thompson Sampling（コールドスタート対策）

### 問題点

**標準 Thompson Sampling の致命的な欠陥：**

標準的な Thompson Sampling は **Beta(1,1)** の一様分布を Prior として使用します。これは、新しいアイテムが**50%の確率で成功する**という暗黙の仮定を意味します。

しかし、実際の大規模プラットフォームでは：

| 環境 | ベースライン成功率 | Beta(1,1)の仮定 | 結果 |
|------|------------------|----------------|------|
| マーケットプレイス（コンテンツ推薦） | 数% | 50% | **体系的に過探索（Over-Explore）** |
| 広告配信 | 1-5% | 50% | 弱いアイテムに過剰露出 |
| レコメンデーション | 10-20% | 50% | 新規アイテムを過大評価 |

### Dynamic Prior Thompson Sampling（2026年2月発表）

#### 核心的なアイデア

**新しいアイテムが現在の勝者を上回る確率を明示的にコントロールする。**

```
P(新規アイテム > 現在の勝者) = ε
```

- ε: 探索率（1-10%が推奨）

#### 実装方法

1. **Prior Mean (q_j) を解く**

   正規近似を用いた二次方程式の閉形式解を使用：

   ```
   q_j = 探索率ε と 現在の勝者のパフォーマンス に基づいて計算
   ```

2. **Prior Strength (r) を設定**

   Prior の強度をコントロール：

   ```
   α_prior = n_k * r * q_j
   β_prior = n_k * r * (1 - q_j)
   ```

   - n_k: 現在の勝者のサンプル数
   - r: Prior Strength（推奨値: 0.1）

3. **Fallback メカニズム**

   計算された q_j が有効範囲外の場合：

   ```
   q_j = ε * p̂_k
   ```

   - p̂_k: 現在の勝者の推定成功率

#### 推奨設定（Production Validated）

| パラメータ | 推奨値 | 説明 |
|-----------|--------|------|
| **ε** | 10% | 中程度の探索（Moderate Exploration） |
| **r** | 0.1 | Prior Strength |
| **保守的な場合** | ε = 1-3% | 新規アイテムが低品質の可能性が高い場合 |

#### 実証結果（ゲームプラットフォームでの実験）

| メトリクス | 改善率 |
|-----------|--------|
| Qualified Play-Through Rate | **+0.19%** |
| Regretted Impressions（無駄な露出） | **-21%** |

#### 利点

| 項目 | 説明 |
|------|------|
| **透明性** | 探索率εを明示的にコントロール可能 |
| **適応性** | Posterior Evidence が蓄積されると自然に移行 |
| **安定性** | バッチ更新（2-8時間ごと）の現実に対応 |
| **精度** | 4桁のサンプルサイズと多様な成功率で ±0.01 の精度 |

---

## 3. Novelty Bonus と探索戦略

### Novelty Bonus の基本原理

**Reachability に基づくボーナス：**

エージェントは、現在の状態が「新奇（Novel）」である場合にボーナスを受け取ります。新奇性は、メモリ内の観測からその状態に到達するまでのステップ数がしきい値を超えるかどうかで判定されます。

### Thompson Sampling における探索強度

**重要な洞察：**

探索強度は、既存コンテンツのパフォーマンスベースラインに適応すべきであり、固定された Prior を仮定すべきではありません。

これが、Dynamic Prior Thompson Sampling がコールドスタート課題に対処する根本的な理由です。

---

## 4. Thompson Sampling vs UCB vs Epsilon-greedy

### 総合比較

| アルゴリズム | リグレット | 計算コスト | パラメータ調整 | 探索の質 |
|-------------|-----------|-----------|--------------|---------|
| **Thompson Sampling** | 最小 | 高い | 不要 | 最適（不確実性ベース） |
| **UCB** | 小さい | 中程度 | 必要（信頼値） | 良い（効率的） |
| **Epsilon-greedy** | 大きい | 低い | 必要（ε値） | 劣る（ブラインド探索） |

### いつ使うべきか

#### Thompson Sampling を使うべき場合

| シーン | 理由 |
|--------|------|
| **非定常環境** | ユーザーの嗜好が変化、新しいコンテンツが登場、トレンドが移り変わる |
| **パラメータ調整を避けたい** | 自動的に探索と活用のバランスを取る |
| **多数の選択肢 + 小さい報酬スプレッド** | 他のアルゴリズムを凌駕するパフォーマンス |
| **不確実性に基づく探索** | 不確実な選択肢を自然に探索、証明された勝者を活用 |

**利点：**
- 学習に応じて自動的に適応（不確実なときは探索、確信があるときは活用）
- 手動での探索率調整が不要
- 数百万の決定を行う際の意思決定品質

**欠点：**
- 計算コストが高い（特に複雑な報酬構造）
- 時に過度に探索的
- 毎回の決定で確率分布からサンプリングが必要
- 毎秒数百万の決定を行う場合、UCBが10%のコストで90%の利益を提供する可能性

#### UCB を使うべき場合

| シーン | 理由 |
|--------|------|
| **計算リソースが制約** | 計算効率が重要 |
| **効率的な探索** | Epsilon-greedy より効率的（信頼区間がデータ蓄積で縮小） |

**欠点：**
- パラメータ設定が必要（信頼値）
- 誤った選択でパフォーマンス低下
- 初期ラウンドで各選択肢を1回ずつテスト（多数の選択肢で遅延）

#### Epsilon-greedy を使うべき場合

| シーン | 理由 |
|--------|------|
| **最も単純な実装** | コインフリップで探索か活用かを決定 |
| **迅速な実装** | シンプルさを最適パフォーマンスより優先 |

**欠点：**
- ブラインド探索（既に1000回テストした選択肢でも探索し続ける）
- 最大パフォーマンス到達に時間がかかる
- 探索期間の勝者が最適とは限らない（リグレット増加、報酬減少）

### 重要な結論

**Thompson Sampling は、Epsilon-greedy よりもリグレット値がはるかに小さく、より良い割り当てポリシーを学習します。** そのため、計算コストが禁止的でない限り、または極度のシンプルさが求められない限り、ほとんどのアプリケーションで推奨されるアルゴリズムです。

---

## 5. 実装上の推奨事項

### Anicca プロジェクトへの適用

#### 現在の状況

| 項目 | 現状 |
|------|------|
| **ユースケース** | Nudge Content / Hook 選択 |
| **環境** | 非定常（ユーザーの嗜好が変化） |
| **コールドスタート** | 新しいコンテンツ/フックが定期的に追加 |
| **成功率** | ProblemType ごとに異なる（おそらく10-30%） |

#### 推奨実装

| 項目 | 推奨 |
|------|------|
| **アルゴリズム** | **Dynamic Prior Thompson Sampling** |
| **探索率（ε）** | 10%（moderate exploration） |
| **Prior Strength (r)** | 0.1 |
| **割引（Discount）** | 検討可（ユーザーの嗜好変化が急激な場合） |

#### 実装ステップ

1. **ベースライン成功率を測定**

   各 ProblemType における現在の成功率を計算：

   ```
   - staying_up_late: X%
   - cant_wake_up: Y%
   - anxiety: Z%
   - ...
   ```

2. **Dynamic Prior を実装**

   ```
   q_j = solve_for_prior_mean(ε, incumbent_performance)
   α_prior = n_k * r * q_j
   β_prior = n_k * r * (1 - q_j)
   ```

3. **Discounted Thompson Sampling を検討**

   ユーザーの嗜好が時間とともに変化する場合、過去の報酬に割引を適用：

   ```
   weighted_success = sum(discount^i * success_i)
   weighted_total = sum(discount^i)
   ```

4. **A/B テスト**

   - Control: 現在の実装
   - Treatment: Dynamic Prior Thompson Sampling
   - メトリクス: Engagement Rate, Regret, User Satisfaction

---

## 6. セキュリティ・パフォーマンス考慮事項

### セキュリティ

| 項目 | 対策 |
|------|------|
| **Prior の妥当性** | Prior パラメータが有効範囲内か検証 |
| **Fallback メカニズム** | 計算エラー時の安全な Fallback |
| **ログ記録** | 探索決定の監査ログ |

### パフォーマンス最適化

| 項目 | 推奨 |
|------|------|
| **サンプリング** | Beta分布のサンプリングを最適化（正規近似を使用） |
| **キャッシング** | Prior 計算結果をキャッシュ |
| **バッチ処理** | 複数アイテムの Prior を一括計算 |

---

## 7. 公式ドキュメント・参考文献

### 主要論文（2025-2026）

1. **Dynamic Prior Thompson Sampling for Cold-Start Exploration in Recommender Systems**
   - URL: [https://arxiv.org/html/2602.00943](https://arxiv.org/html/2602.00943)
   - 発表日: 2026年2月（最新）
   - 核心的貢献: コールドスタート問題に対する Dynamic Prior の導入

2. **Thompson Sampling for Non-Stationary Bandit Problems**
   - URL: [https://www.mdpi.com/1099-4300/27/1/51](https://www.mdpi.com/1099-4300/27/1/51)
   - 発表日: 2025年1月
   - 核心的貢献: Discounted TS と Sliding-Window TS の理論的保証

3. **A Tutorial on Thompson Sampling (Stanford)**
   - URL: [https://web.stanford.edu/~bvr/pubs/TS_Tutorial.pdf](https://web.stanford.edu/~bvr/pubs/TS_Tutorial.pdf)
   - 著者: Daniel J. Russo, Benjamin Van Roy, et al.
   - ステータス: 定番チュートリアル

### 実装ガイド・比較記事

4. **Thompson sampling: Balancing exploration and exploitation**
   - URL: [https://www.statsig.com/perspectives/thompson-sampling-balance-exploration-exploitation](https://www.statsig.com/perspectives/thompson-sampling-balance-exploration-exploitation)
   - 内容: 実装における実践的なガイダンス

5. **Exploring Multi-Armed Bandit Problem: Epsilon-Greedy, UCB, and Thompson Sampling**
   - URL: [https://medium.com/@ym1942/exploring-multi-armed-bandit-problem-epsilon-greedy-epsilon-decreasing-ucb-and-thompson-02ad0ec272ee](https://medium.com/@ym1942/exploring-multi-armed-bandit-problem-epsilon-greedy-epsilon-decreasing-ucb-and-thompson-02ad0ec272ee)
   - 内容: 3つのアルゴリズムの詳細比較

6. **How to Deal with Multi-Armed Bandit Problem**
   - URL: [https://rklymentiev.com/tutorial/mab-problem/](https://rklymentiev.com/tutorial/mab-problem/)
   - 内容: チュートリアルと実装例

---

## 8. 次のステップ

### 短期（1-2週間）

| アクション | 優先度 |
|-----------|--------|
| 現在の成功率ベースラインを測定 | 高 |
| Dynamic Prior Thompson Sampling の PoC 実装 | 高 |
| シミュレーションによる効果検証 | 中 |

### 中期（1-2ヶ月）

| アクション | 優先度 |
|-----------|--------|
| A/B テストの設計と実施 | 高 |
| Discounted Thompson Sampling の評価 | 中 |
| パフォーマンス最適化 | 中 |

### 長期（3ヶ月以降）

| アクション | 優先度 |
|-----------|--------|
| Multi-Armed Bandit の継続的改善 | 低 |
| 新しい研究論文のモニタリング | 低 |

---

## 9. まとめ

### 技術判断

| 質問 | 回答 |
|------|------|
| **どのアルゴリズムを使うべきか？** | **Dynamic Prior Thompson Sampling** |
| **なぜ？** | コールドスタート対策、非定常環境、パラメータ調整不要、実証済みの効果 |
| **代替案は？** | 計算コストが問題ならUCB、極度のシンプルさが必要ならEpsilon-greedy |
| **リスクは？** | 計算コストの増加（ただし最適化可能） |

### 最終推奨

**Anicca プロジェクトでは、Dynamic Prior Thompson Sampling を採用すべき。**

理由：
1. **コールドスタート問題を解決**（新しいフック/コンテンツが定期的に追加される）
2. **非定常環境に対応**（ユーザーの嗜好が変化する）
3. **実証済みの効果**（+0.19% Play-Through Rate、-21% Regretted Impressions）
4. **透明性と制御**（探索率εを明示的にコントロール可能）
5. **2026年2月の最新研究**（最先端のアプローチ）

### 実装優先度

| 優先度 | タスク |
|--------|--------|
| P0 | ベースライン成功率の測定 |
| P0 | Dynamic Prior Thompson Sampling の PoC 実装 |
| P1 | シミュレーションによる検証 |
| P1 | A/B テスト |
| P2 | Discounted Thompson Sampling の評価 |

---

**調査完了日時**: 2026-02-05 22:25:47
**最終更新日**: 2026-02-05
