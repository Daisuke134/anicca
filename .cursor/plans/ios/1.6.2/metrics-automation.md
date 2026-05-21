# Metrics Automation v2 — Anicca Runtime + MCP Porter

> 目的: Anicca が自律改善に使う日次メトリクスを、GitHub Actions ではなく **Anicca 実行基盤**で毎日確実に取得し、RevenueCat / Mixpanel / App Store Connect を同一期間で統合する。

**最終更新**: 2026-02-09
**実行主体**: Anicca (OpenClaw/OpenCline wrapper)
**接続方式**: MCP Porter 経由で各データソース MCP を呼び出す

---

## 1. 決定事項（この仕様の前提）

1. 日次レポートのオーケストレーションは GitHub Actions を使わない。Anicca の定常実行（Cron/定期実行）で完結させる。
2. データ取得は直接 API 呼び出しを混在させず、MCP Porter から統一的に呼び出す。
3. レポートの計算窓は「過去7日」で統一する。
4. Revenue 指標・Funnel 指標・Conversion 指標は、同じ期間ラベルで並べる。
5. 欠損データを 0 扱いしない。取得不能時は `N/A` と欠損理由を明示する。

---

## 2. 実行アーキテクチャ

Anicca が毎朝 1 回 `daily-metrics-reporter` を実行し、同一ジョブ内で 3 ソースを収集・正規化・集計・配信する。

```text
Anicca Scheduler
  -> daily-metrics-reporter
    -> MCP Porter
      -> RevenueCat MCP
      -> Mixpanel MCP
      -> App Store Connect MCP
    -> normalize(window=7d, timezone=Asia/Tokyo)
    -> compute funnel/conversion
    -> post #metrics
    -> persist snapshot (for trend/comparison)
```

### 実行時刻
- 毎日 05:00 JST
- 期間は「前日 23:59:59 JST で閉じた直近7日」を対象
- 例: 2026-02-09 05:00 実行時は `2026-02-02 00:00 JST` から `2026-02-08 23:59:59 JST`

---

## 3. データ契約（7日窓で統一）

## 3.1 App Store Connect MCP

取得対象:
- Downloads 合計（7d）
- 国別 Downloads 内訳（7d）

必須出力:
- `downloads_total_7d`
- `downloads_by_country_7d`

欠損時:
- `downloads_total_7d = N/A`
- レポート下部に `ASC: missing/partial` を表示

## 3.2 RevenueCat MCP

取得対象:
- MRR（実行時スナップショット）
- Active Subscriptions（実行時スナップショット）
- Active Trials（実行時スナップショット）
- Trial Started（7d）

必須出力:
- `mrr_snapshot`
- `active_subscriptions_snapshot`
- `active_trials_snapshot`
- `trial_started_7d`

注意:
- MRR/Active は本質的に snapshot 指標。7d 集計値ではないため、ラベルを `snapshot` と明示する。

## 3.3 Mixpanel MCP

取得対象（7d, unique users）:
- `onboarding_started`
- `onboarding_struggles_completed`
- `onboarding_live_demo_completed`
- `onboarding_notifications_completed`
- `onboarding_completed`
- `onboarding_paywall_viewed`
- `onboarding_paywall_dismissed_free`
- `onboarding_paywall_purchased`

必須出力:
- `funnel_counts_7d` (上記イベントのユーザー数)

欠損時:
- Funnel 行を `N/A` として出し、Conversion も `N/A` にする
- 0 と N/A は厳密に区別する

---

## 4. Funnel / Conversion 定義

計算対象はすべて同一7日窓。

- Onboarding → Paywall Rate
  - `onboarding_paywall_viewed / onboarding_started`
- Paywall → Trial Rate
  - `trial_started_7d / onboarding_paywall_viewed`

出力ルール:
- 分母が 0 または欠損なら `N/A`
- 小数点 1 桁パーセントで表示（例: `27.1%`）
- 併せて raw count を表示（例: `39 / 144`）

---

## 5. レポートフォーマット（固定）

```text
📊 Anicca Daily Report (YYYY-MM-DD)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 APP STORE (7日): Downloads {total}, Top: {country}({count})
💰 REVENUE: MRR ${mrr_snapshot}, Subs {active_subscriptions_snapshot}, Trials {active_trials_snapshot}
📈 FUNNEL (7日): onboarding {onboarding_started}, paywall {onboarding_paywall_viewed}, trial {trial_started_7d}
📊 変換率: オンボ→Paywall {rate1}, Paywall→Trial {rate2}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Data Quality: ASC {ok|partial|missing} / RC {ok|partial|missing} / MP {ok|partial|missing}
🧘 Anicca Bot
```

補足:
- 既存の `FUNNEL (14日)` は廃止し、`FUNNEL (7日)` に統一。
- `trial` は Mixpanel の疑似イベントではなく RevenueCat 由来の 7d trial started を優先採用。

---

## 6. 品質保証要件

1. 同一実行で 3 ソースすべてに対して同じ `window_start/window_end` を渡すこと。
2. 各ソースのレスポンス件数・取得時刻・クエリ条件を実行ログに残すこと。
3. 欠損時でもレポート送信は止めない（fail-open）。ただし `Data Quality` 行で必ず警告する。
4. 日次スナップショット（JSON）を保存し、翌日以降の週次比較に再利用できる形にする。

---

## 7. 受け入れ基準

1. 2026-02-09 基準で、レポート内の APP STORE / FUNNEL / 変換率がすべて 7 日窓で一致する。
2. Mixpanel が一部失敗した場合、`N/A` と `Data Quality: MP partial/missing` が表示される。
3. Revenue が取得できる場合、MRR/Subs/Trials は snapshot と明示され、trial は 7d 値で表示される。
4. GitHub Actions に依存せず、Anicca 実行基盤のみで日次送信が継続する。

---

## 8. 実装境界

この仕様は「Anicca が何を毎日取得・計算・表示すべきか」を定義する。
実装詳細（どの skill ファイルでどう呼ぶか、MCP Porter の接続設定値、秘密情報の配置）は別ドキュメントで管理する。
