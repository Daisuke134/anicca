# TikTok広告予算スケーリング調査レポート

**調査日時**: 2026年2月6日 10:11:18
**調査対象**: TikTok Ads予算スケーリングのベストプラクティス（2025-2026年版）
**調査者**: Claude Code (tech-spec-researcher agent)

---

## 📊 調査結果サマリー

```
調査完了: TikTok Ads Budget Scaling Best Practices 2025-2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 最新版: 2026年2月時点の公式ガイドライン + 専門家BP
📌 学習フェーズ: 50コンバージョン/7日間で完了
⚠️  破壊的変更: 予算を急激に増やすと再学習モードに突入
🔧 推奨増加率: 15-20%を2-3日ごと（安全）、20%を24時間ごと（標準）
🔒 最低予算: キャンペーン$50/日、広告グループ$20/日
```

---

## 1. 予算増加ルール（Budget Increase Rules）

### 公式TikTokガイドライン

| フェーズ | 最大増加率 | 最低待機時間 | 根拠 |
|---------|-----------|-------------|------|
| **学習フェーズ中** | 40%/回 | 2日ごと | [TikTok公式: About Budget](https://ads.tiktok.com/help/article/budget) |
| **学習フェーズ後** | 30%/回 | 2日ごと | [TikTok公式: About Budget](https://ads.tiktok.com/help/article/budget) |
| **推奨（安全）** | 15-20% | 2-3日ごと | [Emplicit Guide](https://emplicit.co/scaling-tiktok-ads-budget-optimization-guide/) |
| **推奨（標準）** | 20% | 24時間ごと | [TikAdSuite 2026 Guide](https://tikadsuite.com/blog/how-to-scale-tiktok-ads/) |

### 具体的な増加例

```
Day 1: $50/日
Day 3: $60/日 (+20%)
Day 5: $72/日 (+20%)
Day 7: $86/日 (+20%)
```

**重要**: 予算変更は1日1回まで。毎朝確認するだけでは変更しない（「退屈だから触る」は禁止）。

### 予算増加の「ショック」を防ぐルール

| 変更幅 | 結果 | 例 |
|--------|------|-----|
| 小さい増加（$100→$110） | アルゴリズムがスムーズに追加オーディエンスを発見 | 再学習なし |
| 大きな増加（$100→$300） | 新しいユーザー群を大量に探す必要 | **再学習モード突入** |

**出典**: [TikTok公式: Scaling Auction Ad Spend](https://ads.tiktok.com/help/article/scaling-auction-ad-spend-solutions)

---

## 2. タイミング（Timing）

### 最適なレビュー・調整スケジュール

| 時刻 | アクション | 条件 |
|------|-----------|------|
| **12:00 PM** | 前日のパフォーマンスをレビュー | アカウントタイムゾーン基準 |
| 12:00 PM | 予算を20%増加 | 前日がROAS目標達成の場合のみ |
| 翌24-48時間 | 結果を判断 | パフォーマンスの一時的低下は正常 |

**出典**: [TikAdSuite 2026 Guide](https://tikadsuite.com/blog/how-to-scale-tiktok-ads/)

### 待機時間の重要性

| ルール | 理由 |
|--------|------|
| 最低2日間待つ | アルゴリズムが調整する時間を確保 |
| 3日間のローリングウィンドウで分析 | 単日の変動に惑わされない |
| 即座のパフォーマンス低下は正常 | 2-3日で回復するのが通常 |

**出典**: [AdManage 2026 Guide](https://admanage.ai/blog/how-to-scale-tiktok-ads)

---

## 3. 学習フェーズ（Learning Phase）

### 学習フェーズとは

TikTokのアルゴリズムが最適なオーディエンス、入札、配信戦略を学習する期間。

| 項目 | 詳細 |
|------|------|
| **完了条件** | 7日間で50コンバージョン達成 |
| **状態** | Learning → Learning Limited → Learned |
| **最適化** | 学習中は配信が不安定、完了後に安定 |
| **再学習トリガー** | 大幅な予算変更、ターゲティング変更、入札変更 |

**出典**: [TikTok公式: Learning Phase](https://ads.tiktok.com/help/article/learning-phase)

### 学習フェーズ中の禁止事項

| 禁止行為 | 理由 |
|---------|------|
| スケーリング開始 | 50コンバージョン未達成では最適化されていない |
| 40%以上の予算増加 | 再学習モード突入のリスク |
| 毎日の設定変更 | アルゴリズムが学習を完了できない |

### 学習フェーズ後のルール

| ルール | 詳細 |
|--------|------|
| 予算は50%範囲内に保つ | 前回予算の±50%を超えない |
| 最低20%増加を推奨 | TikTok公式推奨（ただしCPR一時的上昇あり） |

**出典**: [TikTok公式: Scaling Auction Ad Spend](https://ads.tiktok.com/help/article/scaling-auction-ad-spend-solutions)

---

## 4. 警告サイン（Warning Signs: When NOT to Scale）

### 即座に停止すべきレッドフラグ

| 警告サイン | 詳細 | アクション |
|-----------|------|-----------|
| **CPAスパイク** | 予算増加直後にCPAが急上昇 | 予算を前の水準に戻す |
| **CTR低下** | クリック率が徐々に下がる | オーディエンス飽和のサイン |
| **CPM急上昇** | インプレッション単価が急騰 | オーディエンス枯渇のサイン |
| **50コンバージョン未達** | 過去7日間で50未満 | スケーリング禁止 |
| **CPA余裕なし** | 損益分岐点の20-30%以内にない | スケーリング禁止 |

**出典**: [TikAdSuite 2026 Guide](https://tikadsuite.com/blog/how-to-scale-tiktok-ads/)

### ストップロスルール

```
IF 支出 > $30 AND コンバージョン < 1（同日）
THEN 広告グループを一時停止
```

**理由**: 1日の悪いパフォーマンスで予算を浪費しない

**出典**: [TikAdSuite 2026 Guide](https://tikadsuite.com/blog/how-to-scale-tiktok-ads/)

### スケーリング前のチェックリスト

| # | チェック項目 | 理由 |
|---|-------------|------|
| 1 | 学習フェーズ完了（50コンバージョン/7日）？ | 未完了なら配信不安定 |
| 2 | 現在のCPAが損益分岐点の20-30%以下？ | スケーリングで10-15%上昇する |
| 3 | クリエイティブを7-10日以内に更新した？ | 広告疲労は3-5日で発生 |
| 4 | トラッキング正常（Pixel + Events API）？ | 壊れたトラッキングでは最適化不可 |
| 5 | 今後1-2週間の新クリエイティブ準備済み？ | スケール後の継続に必要 |

**出典**: [AdManage 2026 Guide](https://admanage.ai/blog/how-to-scale-tiktok-ads)

---

## 5. スケーリング戦略（Scaling Strategies）

### Vertical Scaling（縦方向スケーリング）

既存の勝ちキャンペーンの予算を増やす手法。

| 項目 | 詳細 |
|------|------|
| **方法** | 既存広告グループの予算増加 |
| **最大増加率** | 20%/日 |
| **利点** | 既に成功しているキャンペーンを拡大 |
| **欠点** | オーディエンス上限あり、急増でアルゴリズムショック |
| **リスク** | 高リスク（元のキャンペーンが影響を受ける） |

**出典**: [TikAdSuite 2026 Guide](https://tikadsuite.com/blog/how-to-scale-tiktok-ads/)

### Horizontal Scaling（横方向スケーリング）

新しいキャンペーンを並行して立ち上げる手法。

| 項目 | 詳細 |
|------|------|
| **方法** | 勝ちキャンペーンの複製 + 新オーディエンス |
| **ターゲティング** | Lookalike (1%, 1-3%, 5-10%)、Broad targeting |
| **利点** | 元のキャンペーンは無傷、リスク分散 |
| **欠点** | 新規学習フェーズが必要 |
| **リスク** | 低リスク（新キャンペーンが失敗しても元は無傷） |

**出典**: [Admetrics Guide](https://www.admetrics.io/en/post/how-to-scale-tiktok-ads)

### アグレッシブ手法: Surf Scaling

**注意**: 経験者向け。Campaign Budget Optimization (CBO)使用時のみ。

| 時刻 | アクション | 条件 |
|------|-----------|------|
| 10:00 AM | +20%増加 | ROASが3.0以上の場合 |
| 2:00 PM | さらに+20%増加 | パフォーマンス維持の場合 |
| 6:00 PM | 増加停止 | メトリクスが低下した場合 |
| 深夜0:00 | ベースライン予算に戻す | 新しいオークションサイクル前にリセット |

**理由**: 高予算のまま放置すると、低パフォーマンス日に損失拡大。

**出典**: [TikAdSuite 2026 Guide](https://tikadsuite.com/blog/how-to-scale-tiktok-ads/)

---

## 6. Daily Budget vs Lifetime Budget

### アプリインストールキャンペーンの推奨

| 項目 | Daily Budget | Lifetime Budget |
|------|-------------|-----------------|
| **推奨度（アプリインストール）** | ⭐⭐⭐⭐⭐ 強く推奨 | ⭐⭐ 非推奨 |
| **最適化** | 日次で動的最適化 | 期間全体で最適化 |
| **学習フェーズ** | 柔軟に調整可能 | 調整しにくい |
| **用途** | 継続的キャンペーン、コンバージョン重視 | 期間限定プロモーション、イベント |
| **モニタリング** | 毎日のパフォーマンス追跡が容易 | 期間全体での配分 |

**TikTok公式推奨**: アプリインストールキャンペーンには**Daily Budgetを使用する**ことを推奨。

**出典**:
- [TikTok公式: About Budget](https://ads.tiktok.com/help/article/budget)
- [Emplicit Guide](https://emplicit.co/scaling-tiktok-ads-budget-optimization-guide/)

### Daily Budget（日次予算）の利点

| 利点 | 詳細 |
|------|------|
| 学習フェーズでの柔軟性 | 日々の調整が可能 |
| パフォーマンス変動への対応 | 悪い日を早期に検出して調整 |
| 予算コントロール | 毎日の支出上限を確実に管理 |
| テストに最適 | 新キャンペーンの初期テストに適している |

### Lifetime Budget（通算予算）の使用ケース

| 用途 | 例 |
|------|-----|
| 期間限定キャンペーン | 7日間フラッシュセール（予算$2,000） |
| イベントプロモーション | 製品ローンチ、ホリデーセール |
| 締切がある場合 | 特定日までに予算を使い切りたい |

### 最低予算要件

| レベル | Daily Budget | Lifetime Budget |
|--------|-------------|-----------------|
| **キャンペーン** | $50/日 以上 | $50 以上 |
| **広告グループ** | $20/日 以上 | $20 × スケジュール日数 |

**出典**: [TikTok公式: About Budget](https://ads.tiktok.com/help/article/budget)

### 推奨予算（最低要件を超える）

| 目的 | 推奨予算 | 理由 |
|------|---------|------|
| **学習フェーズ通過** | 目標CPA × 10 | アルゴリズムに十分なシグナルを提供 |
| **北米市場** | 最低 $30/日 | 市場CPMに対応 |
| **初期テスト** | $50/日（Broadキャンペーン） | ベスト3クリエイティブで開始 |
| **データ収集** | 約$500のBurn Budget | 失っても良い予算で学習 |

**出典**:
- [Emplicit Guide](https://emplicit.co/scaling-tiktok-ads-budget-optimization-guide/)
- [TikAdSuite Minimum Budget](https://tikadsuite.com/blog/minimum-budget-for-tiktok-ads/)

---

## 7. Campaign Budget Optimization (CBO)

### CBOとは

TikTokが自動的に、複数の広告グループ間で予算を最適配分する機能。

| 項目 | 詳細 |
|------|------|
| **対応目的** | App Promotion（アプリインストール）に対応 |
| **推奨広告グループ数** | 3-5個の広告グループを有効化 |
| **待機時間** | 最低3日間 or 50コンバージョン |
| **調整上限** | 各調整を現在予算の30%以内に抑える |

**出典**:
- [TikTok公式: Campaign Budget Optimization](https://ads.tiktok.com/help/article/campaign-budget-optimization)
- [Admetrics Guide](https://www.admetrics.io/en/post/how-to-scale-tiktok-ads)

### CBOの利点

| 利点 | 詳細 |
|------|------|
| 自動最適化 | パフォーマンスの良い広告グループに自動で予算シフト |
| 手動調整不要 | 個別広告グループの予算管理が不要 |
| 効率向上 | 60%以上のブランドがROI 10%以上改善（TikTok内部テスト） |

### CBOの使用タイミング

| 条件 | 推奨 |
|------|------|
| 複数の広告グループを運用 | CBO推奨 |
| 単一広告グループのみ | CBO不要 |
| 支出目標達成が困難 | Horizontal Scaling（新キャンペーン）と組み合わせ |

---

## 8. クリエイティブ管理

### クリエイティブ更新サイクル

| 項目 | 推奨頻度 | 理由 |
|------|---------|------|
| **広告ビジュアル更新** | 7-10日ごと | 広告疲労対策 |
| **スケール後の更新** | 5-7日ごと | スケール後は燃焼が早い |
| **エンゲージメント低下** | 同じ広告を3回以上見ると43%低下 | ユーザー飽和防止 |

**出典**:
- [Emplicit Guide](https://emplicit.co/scaling-tiktok-ads-budget-optimization-guide/)
- [TikAdSuite 2026 Guide](https://tikadsuite.com/blog/how-to-scale-tiktok-ads/)

### クリエイティブ最適化戦略

| 戦略 | 詳細 |
|------|------|
| **フック変更** | オープニング3秒を変更（コンセプト全変更は不要） |
| **フォーマット変更** | 縦動画 → 横動画 → スライド形式 |
| **メッセージング調整** | 角度やトーンを微調整 |
| **新規クリエイティブ準備** | 1-2週間分のストックを常に確保 |

---

## 9. 自動化ツール

### Smart+ (TikTok公式AI最適化)

| 項目 | 詳細 |
|------|------|
| **機能** | AI駆動の配信最適化（有料＋オーガニック） |
| **効果** | 60%以上のブランドがROI 10%以上向上 |
| **推奨用途** | Maximum Delivery目的（リード、コンバージョン、アプリインストール） |

**出典**:
- [Emplicit Guide](https://emplicit.co/scaling-tiktok-ads-budget-optimization-guide/)
- [TikTok公式: Smart+ App Best Practices](https://ads.tiktok.com/help/article/best-practices-for-smart-plus-app-campaigns)

### VBO (Value-Based Optimization) Bidding

| 項目 | 詳細 |
|------|------|
| **用途** | 高価値ユーザーの獲得優先 |
| **推奨** | アプリ内購入、サブスクリプション重視の場合 |

---

## 10. 実装推奨事項（Anicca アプリ向け）

### アプリインストールキャンペーン設定

| 項目 | 推奨設定 | 理由 |
|------|---------|------|
| **予算タイプ** | Daily Budget | 学習フェーズでの柔軟性、日次最適化 |
| **初期予算** | $50/日（北米）、目標CPA × 10 | 学習フェーズ通過に十分なシグナル |
| **最適化目標** | Maximum Delivery（アプリインストール） | TikTok推奨 |
| **CBO** | 3-5広告グループで有効化 | 自動最適化の利点を活用 |

### スケーリングプロトコル

| ステップ | アクション | タイミング |
|---------|-----------|-----------|
| 1 | 学習フェーズ完了を待つ | 50コンバージョン/7日達成 |
| 2 | CPA確認 | 損益分岐点の70-80%以下であることを確認 |
| 3 | クリエイティブ準備 | 1-2週間分のストックを確保 |
| 4 | 予算を20%増加 | 12:00 PM（前日ROAS目標達成時） |
| 5 | 24-48時間待機 | パフォーマンス回復を観察 |
| 6 | ステップ4-5を繰り返し | 目標予算またはCPA上昇まで |

### 警告サインモニタリング

| メトリクス | 正常範囲 | 警告閾値 | アクション |
|----------|---------|---------|-----------|
| **CPA** | 損益分岐点の70-80% | 90%以上 | スケーリング停止 |
| **CTR** | 安定またはゆるやかな上昇 | 2日連続で10%以上低下 | クリエイティブ更新 |
| **CPM** | 安定 | 急上昇（30%以上） | オーディエンス拡大検討 |
| **コンバージョン/7日** | 50以上 | 50未満 | スケーリング延期 |

### Horizontal Scalingプラン

| フェーズ | アクション |
|---------|-----------|
| Phase 1 | Broadキャンペーン（$50/日）でテスト |
| Phase 2 | 勝ちキャンペーンをLookalike 1%で複製 |
| Phase 3 | Lookalike 1-3%, 5-10%で拡大 |
| Phase 4 | 新地域展開（段階的） |

---

## 11. 参考文献（Sources）

### TikTok公式ドキュメント

- [About Learning Phase | TikTok Ads Manager](https://ads.tiktok.com/help/article/learning-phase)
- [About Budget | TikTok Ads Manager](https://ads.tiktok.com/help/article/budget)
- [Scaling Auction Ad Spend | TikTok Ads Manager](https://ads.tiktok.com/help/article/scaling-auction-ad-spend-solutions)
- [Tips to select your budget | TikTok Ads Manager](https://ads.tiktok.com/help/article/budget-best-practices)
- [How to set up Campaign Budget Optimization | TikTok Ads Manager](https://ads.tiktok.com/help/article/campaign-budget-optimization)
- [About daily budgets](https://ads.tiktok.com/help/article/about-daily-budgets)
- [About lifetime budgets](https://ads.tiktok.com/help/article/about-lifetime-budgets)
- [Best practices Smart+ App | TikTok for Business](https://ads.tiktok.com/help/article/best-practices-for-smart-plus-app-campaigns)

### 専門家ガイド（2025-2026年版）

- [How to Scale TikTok Ads Without Losing ROAS (2026 Ultimate Guide) - TikAdSuite](https://tikadsuite.com/blog/how-to-scale-tiktok-ads/)
- [How to Scale TikTok Ads in 2026 (Without Killing Your CPA) | AdManage Blog](https://admanage.ai/blog/how-to-scale-tiktok-ads)
- [Scaling TikTok Ads: Budget Optimization Guide - Emplicit](https://emplicit.co/scaling-tiktok-ads-budget-optimization-guide/)
- [How to Scale TikTok Ads: The Complete Guide to Explosive Growth - Admetrics](https://www.admetrics.io/en/post/how-to-scale-tiktok-ads)
- [TikTok Ads in 2026: Strategy, Costs & Best Practices - Shopify](https://www.shopify.com/blog/tiktok-ads)
- [Minimum Budget for TikTok Ads: How Much Do You Really Need in 2026? - TikAdSuite](https://tikadsuite.com/blog/minimum-budget-for-tiktok-ads/)
- [How to Optimize TikTok Ad Campaigns for Scale: 9 Proven Ways (2025 Guide) - TLinky](https://tlinky.com/how-to-optimize-tiktok-ad-campaigns-for-scale/)

---

## 12. 更新履歴

| 日付 | 更新内容 |
|------|---------|
| 2026-02-06 | 初回調査完了。TikTok公式ガイドライン + 2025-2026年専門家ベストプラクティスを網羅。 |

---

## 13. 次のステップ

1. **Aniccaアプリ向けのTikTok広告キャンペーン設計**
   - Daily Budgetで初期$50/日から開始
   - 学習フェーズ完了（50コンバージョン/7日）を待つ
   - 20%/24時間の安全なスケーリングプロトコルを実装

2. **クリエイティブパイプラインの構築**
   - 7-10日サイクルで新クリエイティブを準備
   - フック変更を中心とした効率的な制作体制

3. **モニタリングダッシュボード作成**
   - CPA、CTR、CPM、コンバージョン数を日次トラッキング
   - 警告閾値でアラート設定

4. **Horizontal Scalingロードマップ**
   - Lookalike Audienceの段階的展開計画
   - 新地域展開のタイミング設計
