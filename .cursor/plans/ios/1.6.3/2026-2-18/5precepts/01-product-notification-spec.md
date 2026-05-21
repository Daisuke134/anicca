# Anicca 1.6.2 Five Precepts - Product & Notification Spec

## 1. Five Precepts Definition (product canonical)

アプリ内の5分類は以下を canonical にする。

1. `no_killing`
   - EN: Do not kill
   - JA: 不殺生（殺さない）
   - Includes: 他者・動物・虫への加害、自傷・自殺企図を含む「命を害する行為」
2. `no_stealing`
   - EN: Do not steal
   - JA: 不偸盗（盗まない）
   - Includes: 金銭/物品/デジタル資産/時間搾取など不正取得
3. `no_sexual_misconduct`
   - EN: Do not commit sexual misconduct
   - JA: 不邪淫（性的に逸脱しない）
   - Includes: 欲望衝動、対象化、依存的性的行動
4. `no_false_speech`
   - EN: Do not lie
   - JA: 不妄語（嘘をつかない）
   - Includes: 嘘、誹謗、中傷、悪口、分断発言
5. `no_intoxicants`
   - EN: Do not use intoxicants
   - JA: 不飲酒（酩酊を避ける）
   - Includes: 酒、薬物濫用、喫煙・過度な酩酊誘発行動

## 2. Notification Titles (fixed)

タイトルは precept 固定、本文で変化を出す。

1. `no_killing`: `Do Not Harm` / `害さない`
2. `no_stealing`: `Take Only What Is Given` / `与えられたものだけ受け取る`
3. `no_sexual_misconduct`: `Guard Your Desire` / `欲を見張る`
4. `no_false_speech`: `Speak Truth` / `正直に語る`
5. `no_intoxicants`: `Stay Clear` / `酔わずに明晰でいる`

## 3. Schedule Design (reuse current time-slot architecture)

既存の「problemごとの3スロット/日」構造を維持し、preceptに割り当てる。

1. `no_killing`: 07:45 / 12:30 / 17:30
2. `no_stealing`: 09:00 / 13:45 / 18:30
3. `no_sexual_misconduct`: 20:30 / 22:30 / 23:45
4. `no_false_speech`: 08:15 / 13:15 / 18:15
5. `no_intoxicants`: 16:00 / 18:00 / 20:15

## 4. Message Inventory Requirement

30日重複なし要件:

- each precept: `90 hooks` required
- all precepts: `450 hooks / language`
- 6 languages (EN/JA/ES/FR/DE/PT-BR): `2700 hooks total`

命名規則:

- title: `problem_<precept>_notification_title`
- hook: `nudge_<precept>_notification_<1...90>`
- NudgeCard廃止のため detail は 1.6.2 で不要（`nudge_*_detail_*` は削除対象）

## 5. Tone Architecture (90 messages / precept)

各precept 90本は以下配分で作る。

1. `compassionate` 18本
2. `strict` 18本
3. `reflective` 18本
4. `practical` 18本
5. `consequence-based` 18本

### Tone guardrails

- 同日3本は tone 重複禁止
- 連続2日で同 tone 順序を禁止
- 命令口調（strict）は1日最大1本
- 自己否定・羞恥煽り・人格否定は禁止

## 6. Day Rotation Rule

LLM/Thompsonを使わず、決定論で回す。

- `variant = (dayIndex * slotsPerDay + slotIndex) % 90`
- 同日重複: なし（slotIndexが異なるため）
- 30日重複: なし（必要在庫90本を満たせば成立）

## 7. Onboarding Copy Requirement

Welcome copy は五戒アプリとして統一する。

- Title EN: `Welcome to Anicca`
- Subtitle EN: `Follow 5 Precepts for a better life`
- CTA EN: `Enable Notifications`
- Title JA: `アニッチャへようこそ`
- Subtitle JA: `よりよく生きるために、五戒を守る`
- CTA JA: `通知を有効にする`

注意:

- CTAは `Get Started` を廃止
- pre-promptボタンは通知許可目的が明示される文言に固定

## 8. Main Screen Button Copy Requirement

メイン画面の購読ボタン文言は固定する。

1. Active/trial: `Cancel Subscription`
2. Expired/canceled/free: `Resubscribe`

`Manage Subscription` は使わない。

## 9. Analytics Simplification

残すイベント:

1. onboarding_started
2. onboarding_notifications_completed
3. onboarding_paywall_viewed
4. onboarding_paywall_purchased
5. notification_tapped
6. subscription_cancelled / subscription_renewed

削除対象:

- nudge card thumbs up/down 系
- nudge card completion 回数依存 paywall 表示系
- free plan limit 指標
