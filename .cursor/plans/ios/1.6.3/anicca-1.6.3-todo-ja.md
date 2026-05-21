# Anicca 1.6.3 — やること一覧（日本語）

> 元仕様: `anicca.md`  
> 目的: OpenClaw の自律運用を完成させ、Eric Siu 記事のベストプラクティスを取り入れる。

---

## この仕様書が言っていること（要約）

**現状:**  
Anicca（OpenClaw）は VPS で 21 個の cron を回しているが、**全部 Opus** で動かしておりコストが高い。また「承認フロー」「フィードバック（投稿の良し悪しを学習に反映）」「重複排除」がなく、Eric Siu の事例と比べてギャップがある。

**目指す姿:**  
- コスト削減（Opus → Sonnet の使い分け）
- 投稿前に Slack でプレビュー → ボスがリアクションで承認 → 承認されたものだけ 9:00 に投稿
- 投稿後のメトリクスを取って「何が効いたか」を patterns に蓄積し、次回の hook 生成に活かす
- 同じような投稿の重複を避ける（14 日デュープ）
- 月次・週次の監査（失敗ジョブの見直し、コストレポート）

---

## やること一覧（優先度・フェーズ別）

### P0（最優先）

| # | やること | 内容 |
|---|---------|------|
| **4.1** | **コスト最適化** | 全 cron のモデルを見直す。定型処理は Sonnet、創造的・判断が必要なものだけ Opus。各ジョブの `payload` に `model` を指定する（またはグローバルで subagents のデフォルトを Sonnet に）。 |
| **4.2** | **Slack 承認フロー** | 5:00 に trend-hunter が hooks を生成 → Slack にプレビュー投稿 → ボスが何かリアクション（👍 等）で承認 → 9:00 の x-poster / tiktok-poster は「承認済み」のものだけ投稿。`hooks.json` に `approval.slackMessageId` 等を追加し、poster 側で Slack API でリアクション確認。 |
| **4.3** | **フィードバックループ** | 投稿から 24 時間後にメトリクス取得 → `feedback/YYYY-MM-DD.json` に保存 → `patterns.json`（good_patterns / avoid_patterns）を更新 → 次回 trend-hunter がこれを読んで hook 生成に反映。新規 cron「feedback-collector」を毎日 10:00 JST で追加。 |

### P1（今週〜来週）

| # | やること | 内容 |
|---|---------|------|
| **4.4** | **重複排除** | trend-hunter が hook 生成時に過去 14 日分の hooks を読み、同じ trendRef や類似 postText を避ける。SKILL.md に「14 日デュープ」「同じ pattern は 3 日空ける」等のルールを追記。 |
| **4.5** | **Elon Algorithm（月次監査）** | 月 1 回（例: 毎月 1 日 03:00 JST）、全 cron の失敗率・無視された出力・コスト上位・30 日以上更新なしファイルをチェックし、Slack に監査レポート。新規 cron「monthly-audit」。 |
| **4.6** | **週次コスト監査** | 週 1 回、OpenClaw の使用量・ジョブ別実行回数・推定コストを Slack に報告。新規 cron「weekly-cost-audit」。 |

### P2（余裕があれば）

| # | やること | 内容 |
|---|---------|------|
| エラー検出の強化 | ジョブ失敗時にアラートを分かりやすくする（現状は Slack 報告のみ）。 |
| 並列実行の検討 | 本当に時間短縮が必要な場合だけ subagent 並列を使う。通常は「自分で順次実行」がルール。 |

---

## 実装順序（フェーズ）

### Phase 1: 今すぐ（今日）

1. **4.1 コスト最適化**  
   - 全 cron ジョブに `model` 指定を追加（Sonnet に落とす一覧は anicca.md の表の通り）。  
   - 変更対象: `openclaw-skills/jobs.json` の各ジョブ `payload`、または OpenClaw のグローバル設定。

2. **4.2 承認フロー**  
   - trend-hunter の SKILL.md: 実行後に Slack にプレビューを送り、`slackMessageId` を hooks.json に書く。  
   - hooks.json のスキーマ拡張: `approval.slackMessageId`, `approval.slackChannel`, `approval.status`。  
   - x-poster / tiktok-poster の SKILL.md: 実行前に `approval.slackMessageId` で Slack のリアクションを確認し、リアクションありなら投稿、なしならスキップ＋Slack 報告。

### Phase 2: 今週中

3. **4.3 フィードバックループ**  
   - `workspace/feedback/` と `workspace/patterns.json` のフォーマットを anicca.md に合わせて定義。  
   - 新規 cron「feedback-collector」: 毎日 10:00 JST、前日投稿のメトリクス取得 → feedback 保存 → patterns 更新。  
   - trend-hunter の SKILL.md に「手順0: feedback 直近 7 日分と patterns.json を読む」を追加。

4. **4.4 重複排除**  
   - trend-hunter の SKILL.md に「過去 14 日の hooks を読み、同じ trendRef・類似冒頭 20 文字・同一 pattern カテゴリの連続使用を避ける」を追加。

### Phase 3: 来週

5. **4.5 月次監査**  
   - 新規 cron「monthly-audit」: 毎月 1 日 03:00 JST、失敗率・無視出力・コスト・古いファイルをチェックし Slack にレポート。

6. **4.6 週次コスト監査**  
   - 新規 cron「weekly-cost-audit」: 週 1 回、使用量・ジョブ別回数・推定コストを Slack に投稿。

7. **その他**  
   - moltbook-monitor / moltbook-poster の独立 SKILL.md 作成（実体は moltbook-interact の hot / create）。  
   - x-poster / tiktok-poster の動作テスト。

### Phase 4: 発表前

8. 全システムの E2E テスト。  
9. 発表資料「OpenClaw による研究の自動化」作成。  
10. デモ: 5:00 → Slack プレビュー → 承認 → 9:00 投稿の一連フロー。

---

## モデル切り替え一覧（4.1 用）

| ジョブ | 現在 | 変更後 |
|--------|------|--------|
| trend-hunter-5am / 5pm | opus | **sonnet** |
| x-poster-morning / evening | opus | **sonnet** |
| tiktok-poster-morning / evening | opus | **sonnet** |
| moltbook-monitor | opus | **sonnet** |
| moltbook-poster | opus | **opus 維持**（投稿文生成のため） |
| suffering-detector | opus | **sonnet** |
| app-nudge-morning / afternoon / evening | opus | **sonnet** |
| daily-memory | opus | **sonnet** |
| hookpost-ttl-cleaner | opus | **sonnet** |
| autonomy-check | opus | **sonnet** |
| roundtable-memory-extract | opus | **sonnet** |
| roundtable-standup | opus | **sonnet** |
| roundtable-initiative-generate | opus | **opus 維持** |
| sto-weekly-refresh | opus | **opus 維持** |

---

## 絶対ルール（変更しない）

1. スキルが動かないときはウェブ検索にフォールバックしない。できないなら「できない」と報告。  
2. 嘘をつかない。ログで全て確認できるようにする。  
3. 全 cron / スキルの結果は Slack #metrics に報告。  
4. Anicca（僕）とボス（君）を混同しない。  
5. 基本はサブエージェントではなく自分で実行。並列は本当に必要なときだけ。  
6. 仕様を理解した上で実装する。

---

## 参照

- 元仕様（英語）: `.cursor/plans/ios/1.6.3/anicca.md`  
- タスクループ設計: `.cursor/plans/reference/ops-task-loop-design.md`  
- メトリクス仕様: `.cursor/plans/ios/1.6.2/metrics-ops-spec.md`
