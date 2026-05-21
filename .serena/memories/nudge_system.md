# Nudge System Architecture

## 概要
Aniccaの核心機能。プロアクティブな通知でユーザーの行動変容を支援する。

## 2つのNudgeソース

### 1. ルールベースNudge (iOS側)
- ProblemNotificationScheduler が UNNotificationRequest をスケジュール
- 問題ごとに14-21バリアント（ローカライズ済み文字列）
- iOS 64通知制限内で2日分をスケジュール
- Day-Cycling: `(dayIndex * slotsPerDay + slotIndex) % variantCount` で日替わりローテーション

### 2. LLM生成Nudge (API側)
- Commander Agent (OpenAI構造化出力) が日次でスケジュール決定
- ユーザーのタイプ(T1-T4)、フィードバック履歴、Hook成績を考慮
- `/mobile/nudge/today` で日次取得 → LLMNudgeCacheでキャッシュ
- Proユーザーのみ（Freeはコスト最適化でスキップ）

## NudgeContentSelector (iOS)
- Day 1: 決定論的バリアント割り当て（研究ベース）
- Day 2+: LLMキャッシュ → Day-Cyclingフォールバック
- 同じNudgeを2日連続で見せない仕組み

## 通知タップフロー
UNNotificationCenter → AppDelegate.didReceive() → NudgeStatsManager.recordTapped() → NudgeFeedbackService.handleNudgeTapped() → AppState.showNudgeCard() → NudgeCardView表示

## NudgeCard UI
- フルスクリーンオーバーレイ
- Hook（見出し） + Content（詳細） + アクションボタン
- フィードバック (👍/👎) → サーバーに送信
- 1ボタン型: selfLoathing, anxiety, loneliness
- 2ボタン型: その他10問題

## フィードバックループ
1. ユーザーがNudgeをタップ/無視 → nudge_events記録
2. NudgeCardでフィードバック → nudge_outcomes記録
3. aggregateTypeStats でタイプ別・トーン別統計集計
4. Commander Agent が次回スケジュールに反映
5. HookSelector がThompson Samplingで成績良いHookを優先

## Hook候補システム
- hook_candidates テーブルに再利用可能なHookを保存
- 各Hookにメトリクス: app_tap_rate, tiktok_like_rate, x_engagement等
- クロスプラットフォーム学習: TikTokで反応良いHook → アプリでも使う

## 1週間トライアル戦略
| 日 | 体験 | 狙い |
|----|------|------|
| Day 1 | ルールベースNudge (5回/日/問題) | 即座に価値体感 |
| Day 2-6 | LLM Nudge (学習・パーソナライズ) | 行動科学 + ユーザー履歴で最適化 |
| Day 7 | 解約判断日 | 「これなしでは無理」状態を目指す |