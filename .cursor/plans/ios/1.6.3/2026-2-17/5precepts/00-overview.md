# Anicca 1.6.2 Five Precepts Pivot - Overview

- Version: draft-1
- Date: 2026-02-08
- Owner: iOS/App + API

## 1. Final Product Decision

Anicca 1.6.2 は「5ドルで五戒を守る」単一価値にピボットする。

- App name: `Anicca`
- Product motto (EN): `Follow 5 Precepts for $5`
- Product motto (JA): `5ドルで五戒を守る`
- Pricing default: monthly `$9.99` (既存課金設定は維持。訴求コピーとしては「$5」を使用)

## 2. Onboarding Decision (確定)

2案のうち、以下を採用する。

1. `Welcome (五戒訴求)`
2. `Notification permission`（ボタンタップでシステム許可ダイアログ）
3. `Hard paywall`（閉じる不可）
4. `Main screen`（購読管理ボタンのみ）

### Why this is best

- App Review観点: 通知許可を求める前に目的説明がある。
- UX観点: 「通知アプリ」であることを最初に明示できる。
- 実装観点: 現在フロー（通知→Paywall）を最短改修でハード化できる。

## 3. Main Screen Decision (確定)

ホームは単機能にする。

- Active/trial user: `Cancel Subscription` ボタンのみ
- Expired/free user: `Resubscribe` ボタンのみ
- Nudge Card UIは廃止
- 通知タップ時はカードを出さず、メイン画面を開くのみ

## 4. Notification Strategy Decision (確定)

- 13 problem types を廃止し、5 precepts に統合
- ルールベースのみ（LLM生成は停止）
- 1 preceptあたり 3 通知/日
- 30日間で同文面重複なし

必要在庫:

- 1 precept: `3 x 30 = 90` hooks
- 5 precepts合計: `450 hooks / language`
- 6 languages (EN/JA/ES/FR/DE/PT-BR): `2700 hooks`

## 5. Scope

この仕様セットで定義する対象:

- iOS導線（Onboarding/Paywall/Main）
- 通知ドメイン再定義（五戒）
- 不要機能削除方針（NudgeCard/LLM/Free導線）
- API/ジョブ側のルールベース固定化
- テスト更新

この時点で実施しない対象:

- 五戒全文言の実データ作成（`2700 hooks`）自体は別ファイルで次フェーズ

## 6. External References

- Buddhist five precepts (core wording):
  - https://www.accesstoinsight.org/ptf/dhamma/sila/pancasila.html
  - https://en.wikipedia.org/wiki/Five_precepts
- Apple notification permission UX guidance:
  - https://developer.apple.com/design/human-interface-guidelines/notifications
