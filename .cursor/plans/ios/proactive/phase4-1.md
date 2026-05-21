# Phase 4-1 実装仕様書

> 実装日: 2026-01-19
> 実装者: Claude Opus 4.5
> レビュー待ち

---

## 実装概要

| # | タスク | ステータス |
|---|--------|-----------|
| 1 | 通知タイトルを問題別に変更（アイコンなし） | 完了 |
| 2 | 時間帯対応（cant_wake_upは6:00-9:00のみ） | 完了 |
| 3 | One Screen説明文を充実版に書き換え（13問題） | 完了 |
| 4 | spec.mdにビジョン・ゴール・ロードマップを追記 | 完了 |

---

## タスク1: 通知タイトル変更

### 変更ファイル

1. `aniccaios/aniccaios/Resources/ja.lproj/Localizable.strings`
2. `aniccaios/aniccaios/Resources/en.lproj/Localizable.strings`

### 変更箇所（日本語）

| キー | 旧値 | 新値 |
|------|------|------|
| `problem_staying_up_late_notification_title` | 就寝 | スマホを置け |
| `problem_cant_wake_up_notification_title` | 起床 | 起きろ |
| `problem_self_loathing_notification_title` | Self-Compassion | 自分を許せ |
| `problem_rumination_notification_title` | 今ここに | 今ここに戻れ |
| `problem_procrastination_notification_title` | 今すぐ | 今すぐやれ |
| `problem_anxiety_notification_title` | 安心 | 大丈夫 |
| `problem_lying_notification_title` | 誠実 | 正直に |
| `problem_bad_mouthing_notification_title` | 善い言葉 | 優しい言葉を |
| `problem_porn_addiction_notification_title` | 克服 | 衝動に勝て |
| `problem_alcohol_dependency_notification_title` | 禁酒 | 今夜は飲むな |
| `problem_anger_notification_title` | 平静 | 怒りを手放せ |
| `problem_obsessive_notification_title` | 解放 | 考えすぎ |
| `problem_loneliness_notification_title` | つながり | つながろう |

### 変更箇所（英語）

| キー | 旧値 | 新値 |
|------|------|------|
| `problem_staying_up_late_notification_title` | Bedtime | Put the Phone Down |
| `problem_cant_wake_up_notification_title` | Wake Up | Get Up Now |
| `problem_self_loathing_notification_title` | Self-Compassion | Forgive Yourself |
| `problem_rumination_notification_title` | Present Moment | Return to Now |
| `problem_procrastination_notification_title` | Procrastination | Do It Now |
| `problem_anxiety_notification_title` | Anxiety | You're Safe |
| `problem_lying_notification_title` | Honesty | Be Honest |
| `problem_bad_mouthing_notification_title` | Words | Kind Words |
| `problem_porn_addiction_notification_title` | Self-Control | Beat the Urge |
| `problem_alcohol_dependency_notification_title` | Sobriety | Don't Drink Tonight |
| `problem_anger_notification_title` | Calm | Let Go of Anger |
| `problem_obsessive_notification_title` | Let Go | Stop Overthinking |
| `problem_loneliness_notification_title` | Connection | Reach Out |

---

## タスク2: 時間帯フィルタリング

### 変更ファイル

1. `aniccaios/aniccaios/Models/ProblemType.swift`
2. `aniccaios/aniccaios/Notifications/ProblemNotificationScheduler.swift`

### ProblemType.swift 追加コード

**追加位置**: `notificationSchedule` プロパティの直後（行69-88）

```swift
/// 有効な通知時間帯（時間帯制限がある問題のみ）
/// - Returns: (startHour, startMinute, endHour, endMinute) or nil if no restriction
var validTimeRange: (startHour: Int, startMinute: Int, endHour: Int, endMinute: Int)? {
    switch self {
    case .cantWakeUp:
        // 6:00-9:00のみ（朝の起床時間帯）
        return (6, 0, 9, 0)
    default:
        return nil
    }
}

/// 指定時刻がこの問題の有効時間帯内かどうか
func isValidTime(hour: Int, minute: Int) -> Bool {
    guard let range = validTimeRange else { return true }
    let timeMinutes = hour * 60 + minute
    let startMinutes = range.startHour * 60 + range.startMinute
    let endMinutes = range.endHour * 60 + range.endMinute
    return timeMinutes >= startMinutes && timeMinutes < endMinutes
}
```

### ProblemNotificationScheduler.swift 追加コード

**追加位置**: `scheduleNotifications` 関数内、時刻シフト処理の後（行63-67）

```swift
// 有効時間帯のチェック（時間帯制限がある問題のみ）
guard schedule.problem.isValidTime(hour: hour, minute: minute) else {
    logger.info("Skipped \(schedule.problem.rawValue) at \(hour):\(minute) - outside valid time range")
    continue
}
```

### 動作仕様

- `cant_wake_up` の通知は6:00〜9:00の間のみスケジュールされる
- 他の通知との重複回避で時刻がシフトした結果、9:00以降になった場合はスキップ
- スキップ時はログに記録される

---

## タスク3: One Screen説明文更新

### 変更ファイル

1. `aniccaios/aniccaios/Resources/ja.lproj/Localizable.strings`
2. `aniccaios/aniccaios/Resources/en.lproj/Localizable.strings`

### 変更形式

各detail文に **【見出し】** を追加し、以下の構造に統一:
- 具体的なアクション（今すぐできること）
- 心理学的インサイト（なぜ効果があるか）
- 数値・時間の具体化（5秒、10分など）

### 変更箇所（日本語）

#### staying_up_late

| キー | 旧値 | 新値 |
|------|------|------|
| `nudge_staying_up_late_detail_1` | 夜更かしは明日の自分を傷つける行為。今夜は画面を閉じよう。 | 【今すぐやること】スマホを顔から30cm離して、画面の明るさを最低にする。そして5回深呼吸。脳が「寝る準備」モードに切り替わる。 |
| `nudge_staying_up_late_detail_2` | 睡眠不足の脳は酔っ払いと同じ判断力。明日の自分を守るために、今夜は休もう。 | 【なぜ危険か】睡眠不足の脳は血中アルコール0.1%と同じ判断力。17時間起きてると酔っ払いと同じ。明日の大事な判断を守るために、今夜は休もう。 |
| `nudge_staying_up_late_detail_3` | 今スクロールしてる内容、明日覚えてる？でも睡眠不足は確実に残る。 | 【冷静に考えて】今見てるコンテンツ、明日の昼に思い出せる？でも睡眠不足は確実に集中力・判断力・免疫力を下げる。どっちが大事？ |
| `nudge_staying_up_late_detail_4` | 睡眠不足は蓄積します。起きている時間が長いほど、明日はもっと辛くなります。スマホを置いて、目を閉じてください。 | 【睡眠負債】睡眠不足は借金のように蓄積する。今夜の1時間は、来週の集中力と判断力を確実に奪う。スマホを枕元から離して、目を閉じて。 |
| `nudge_staying_up_late_detail_5` | これが最後の警告です。今やっていることより、あなたの健康の方が大事です。今すぐ寝てください。 | 【最終警告】深夜1時以降の覚醒は、脳と心臓に測定可能なダメージを与える。今やってることの100倍、睡眠の方が大事。今すぐ寝ろ。 |

#### cant_wake_up

| キー | 旧値 | 新値 |
|------|------|------|
| `nudge_cant_wake_up_detail_1` | 布団の中で何も変わらない。まず足を床につけよう。 | 【5秒ルール】5、4、3、2、1で足を床につける。考える前に動く。脳が言い訳を作る前に、身体を起こせ。布団の中で人生は変わらない。 |
| `nudge_cant_wake_up_detail_2` | 「あと5分」を何回言った？今起きれば、今日の自分を好きになれる。 | 【信頼ゼロ】「あと5分」の自分を何回信じた？何回裏切られた？今起きることで、自分との約束を守れる。今日の自分を好きになれる。 |
| `nudge_cant_wake_up_detail_3` | 平凡なままでいい？今起きれば、今日は違う1日になる。 | 【二択】今日もダラダラ始める？それとも、今日から変わる？答えは今の行動で決まる。5秒以内に立て。 |

#### self_loathing

| キー | 旧値 | 新値 |
|------|------|------|
| `nudge_self_loathing_detail_1` | 自己嫌悪は、自分を良くしようとしている証拠。でもその方法は逆効果。今日できた小さなことを1つ思い出してみて。 | 【逆説】自己嫌悪は「もっと良くなりたい」という証拠。でも自分を責めても成長しない。むしろ逆効果。今日、朝起きた。それだけで十分。 |
| `nudge_self_loathing_detail_2` | 完璧じゃなくていい。今のあなたで十分。 | 【友達テスト】親友が同じ状況だったら、なんて声をかける？「ダメなやつだ」とは言わないはず。自分にも同じ優しさを。 |
| `nudge_self_loathing_detail_3` | 自分に厳しすぎる。他の人にするように、自分にも優しくしていい。 | 【事実確認】今責めてることは、本当に「取り返しのつかないこと」？多くの場合、思ってるより小さい。深呼吸して、客観的に見てみて。 |

#### rumination

| キー | 旧値 | 新値 |
|------|------|------|
| `nudge_rumination_detail_1` | 頭の中のループに気づいた？気づいたなら、もう半分解決してる。今この瞬間に戻ろう。 | 【気づきの力】ループに気づいた時点で、もう半分勝ってる。今やること：足の裏の感覚に意識を向ける。床の硬さ、温度。30秒だけ。 |
| `nudge_rumination_detail_2` | 過去でも未来でもなく、今ここにいる？深呼吸して、今の身体の感覚に意識を向けてみて。 | 【5-4-3-2-1法】見えるもの5つ、聞こえるもの4つ、触れてるもの3つ、匂い2つ、味1つ。これで強制的に「今」に戻れる。 |
| `nudge_rumination_detail_3` | 反芻を止める最も効果的な方法は瞑想。今朝5分だけ、呼吸に集中してみよう。 | 【瞑想が最強】反芻を止める最も効果的な方法は瞑想。今から2分、呼吸だけに集中。吸う・止める・吐くを4秒ずつ。 |

#### procrastination

| キー | 旧値 | 新値 |
|------|------|------|
| `nudge_procrastination_detail_1` | 完璧にやる必要はない。5分だけ始めれば、続けられる。 | 【2分ルール】2分で終わることは今やる。2分以上かかることは、最初の2分だけやる。始めれば、脳は続けたくなる。これが科学。 |
| `nudge_procrastination_detail_2` | 先延ばしは未来の自分を苦しめる。今やれば、未来の自分が感謝する。 | 【未来の自分】1週間後の自分を想像して。「あの時やっておけば...」と後悔してる？今やれば、その後悔は消える。 |
| `nudge_procrastination_detail_3` | 本当にできない？それとも、やりたくないだけ？正直になろう。 | 【正直に】「できない」と「やりたくない」は違う。今、どっち？やりたくないなら、なぜ？本当の理由を見つけよう。 |

#### anxiety

| キー | 旧値 | 新値 |
|------|------|------|
| `nudge_anxiety_detail_1` | 不安は未来への恐れ。でも今この瞬間は、何も起きていない。深呼吸して、今に戻ろう。 | 【今この瞬間】不安は「まだ起きてないこと」への恐れ。今この瞬間、目の前で何が起きてる？実際には何も危険なことは起きてない。 |
| `nudge_anxiety_detail_2` | 不安に気づいた？気づいたなら、それを観察してみて。不安は来て、去っていく。 | 【観察者になる】「私は不安だ」ではなく「私は不安を感じている」。不安は天気みたいなもの。来て、そして去っていく。 |
| `nudge_anxiety_detail_3` | 身体を落ち着かせれば、心も落ち着く。今すぐやってみて。 | 【ボックス呼吸】4秒吸う→4秒止める→4秒吐く→4秒止める。これを3回。身体が落ち着けば、心も落ち着く。今すぐやって。 |

#### lying

| キー | 旧値 | 新値 |
|------|------|------|
| `nudge_lying_detail_1` | 嘘は一時的に楽でも、長期的には自分を苦しめる。今日は誠実でいよう。 | 【複利の法則】小さな嘘は大きな嘘を呼ぶ。嘘をつくと、その嘘を守るためにまた嘘が必要になる。今日一日、正直でいることで、明日がシンプルになる。 |

#### bad_mouthing

| キー | 旧値 | 新値 |
|------|------|------|
| `nudge_bad_mouthing_detail_1` | 悪口は言った瞬間気持ちいいかもしれない。でも後から自己嫌悪が来る。今日は善い言葉だけ。 | 【ブーメラン】悪口を言うと、一時的にスッキリする。でも5分後に自己嫌悪が来る。そして聞いた人は「この人は自分の悪口も言うだろう」と思う。 |
| `nudge_bad_mouthing_detail_2` | 言う前に一呼吸。相手の立場に立ってみよう。 | 【10秒ルール】言いたくなったら10秒待つ。その間に「これを本人の前で言えるか？」と考える。言えないなら、言わない。 |

#### porn_addiction

| キー | 旧値 | 新値 |
|------|------|------|
| `nudge_porn_addiction_detail_1` | 今の衝動は一時的。5分待てば、衝動は去る。その5分を乗り越えよう。 | 【サーフィン】衝動は波のようなもの。必ずピークがあり、必ず下がる。10分だけ別のことをしてみて。散歩、腕立て、冷水で顔を洗う。 |
| `nudge_porn_addiction_detail_2` | ポルノは一時的な逃避。根本の問題は解決しない。今何から逃げようとしてる？ | 【根本原因】ポルノに逃げたくなる時、本当は何から逃げてる？ストレス？孤独？退屈？その根本を見つけよう。 |

#### alcohol_dependency

| キー | 旧値 | 新値 |
|------|------|------|
| `nudge_alcohol_dependency_detail_1` | 1日だけ。今夜だけ我慢しよう。明日の朝、自分を誇れる。 | 【今夜だけ】明日のことは考えなくていい。今夜だけ飲まない。明日の朝、二日酔いなしで目覚める自分を想像して。その気持ちよさを味わって。 |
| `nudge_alcohol_dependency_detail_2` | お酒なしでストレス解消する方法を試してみて。散歩、深呼吸、音楽。 | 【代替行動】飲みたくなったら、炭酸水を飲む。10分散歩する。熱いシャワーを浴びる。ストレスは消えないけど、飲まなくても対処できる。 |

#### anger

| キー | 旧値 | 新値 |
|------|------|------|
| `nudge_anger_detail_1` | 怒りを持ち続けるのは、自分が毒を飲んで相手が死ぬのを待つようなもの。手放そう。 | 【毒を飲む】怒りを持ち続けるのは、自分が毒を飲んで相手が死ぬのを待つようなもの。相手はあなたの怒りを感じてない。苦しんでるのは自分だけ。 |
| `nudge_anger_detail_2` | 怒りに任せて話すと後悔する。3秒だけ待とう。 | 【6秒ルール】怒りのピークは6秒。6秒数えてから行動する。1、2、3、4、5、6。この間に深呼吸。6秒後、まだ同じことを言いたいか確認。 |

#### obsessive

| キー | 旧値 | 新値 |
|------|------|------|
| `nudge_obsessive_detail_1` | その考え、本当に重要？今手放しても、何も悪いことは起きない。 | 【重要度チェック】1年後、この考えは重要？大体の場合、ノー。今手放しても、何も悪いことは起きない。試してみて。 |
| `nudge_obsessive_detail_2` | 同じことを考え続けても、答えは変わらない。今は手放して、後で考えよう。 | 【思考予約】「この考えは17時に考える」と決める。脳にスケジュールを伝えると、今は手放せる。17時になったら大体忘れてる。 |
| `nudge_obsessive_detail_3` | 考えることと、実際に行動することは違う。今は考えるのをやめて、動いてみよう。 | 【動くことで止まる】考えすぎは「動かないこと」が原因のことが多い。今すぐ立って、30秒その場で足踏み。身体を動かすと頭も変わる。 |

#### loneliness

| キー | 旧値 | 新値 |
|------|------|------|
| `nudge_loneliness_detail_1` | 孤独を感じても、それは真実じゃない。今日、誰かに連絡してみない？ | 【孤独の嘘】孤独を感じる時、「誰も自分のことを気にしてない」と思う。でもそれは嘘。今、連絡したら喜ぶ人が1人はいる。誰？ |
| `nudge_loneliness_detail_2` | つながりは待っていても来ない。自分から動こう。 | 【先に動く】つながりは待っていても来ない。「連絡したら迷惑かも」は嘘。今すぐ誰かに「元気？」と送ってみて。それだけでいい。 |

### 変更箇所（英語）

英語版も同様の構造で更新済み。キーは同一、値のみ英語に翻訳。

---

## タスク4: spec.md ロードマップ追加

### 変更ファイル

`.cursor/plans/ios/proactive/proactive-agent-spec.md`

### 追加セクション

セクション7「将来ビジョン」を以下の構造に更新:

#### 7.0 究極のビジョン
- 「苦しみのあるところに、Aniccaあり」
- デジタル仏陀コンセプト
- 最終目標: 涅槃へと導く

#### 7.1 ゴール達成への道
| 段階 | 状態 | Aniccaの役割 |
|------|------|-------------|
| 今 | ユーザーは6-7年間同じ問題で苦しんでいる | 寄り添う |
| Phase 4-5 | 通知で気づきを与え、小さな行動変容が起き始める | 導く |
| Phase 6-7 | 習慣が定着し、自己嫌悪のループが弱まる | 支える |
| Phase 8-9 | 自分との約束を守れるようになり、自己信頼が回復 | 見守る |
| Phase 10 | 苦しみから解放され、他者を助ける側になる | 共に歩む |

#### 7.2 完全ロードマップ（Phase 4〜10）
- Phase 4: 自律改善システム基盤
- Phase 5: コンテキスト認識通知
- Phase 6: マルチモーダルNudge
- Phase 7: 予測型介入
- Phase 8: 外部プラットフォーム進出
- Phase 9: コミュニティ形成
- Phase 10: デジタル仏陀の完成

#### 7.3 自律改善システムの進化
- Phase 4: ルールベース
- Phase 5: LLMプロンプト
- Phase 6: 学習型
- Phase 7: 予測型
- Phase 8-10: 意思を持つ

---

## レビューチェックリスト

### ローカライゼーション

- [ ] 全13問題の通知タイトルが日本語で更新されているか
- [ ] 全13問題の通知タイトルが英語で更新されているか
- [ ] 全detail文が日本語で更新されているか
- [ ] 全detail文が英語で更新されているか
- [ ] キー名に誤りがないか
- [ ] 文法・表現に問題がないか

### Swift コード

- [ ] `ProblemType.swift` の `validTimeRange` が正しく実装されているか
- [ ] `ProblemType.swift` の `isValidTime` が正しく実装されているか
- [ ] `ProblemNotificationScheduler.swift` で時間帯チェックが正しく呼ばれているか
- [ ] コンパイルエラーがないか
- [ ] 既存機能への影響がないか

### spec.md

- [ ] ビジョンが明確に記述されているか
- [ ] Phase 4-10のロードマップが具体的か
- [ ] 各Phaseでユーザーの苦しみがどう解決されるか記述されているか

---

## 関連ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `aniccaios/aniccaios/Resources/ja.lproj/Localizable.strings` | 編集 |
| `aniccaios/aniccaios/Resources/en.lproj/Localizable.strings` | 編集 |
| `aniccaios/aniccaios/Models/ProblemType.swift` | 編集 |
| `aniccaios/aniccaios/Notifications/ProblemNotificationScheduler.swift` | 編集 |
| `.cursor/plans/ios/proactive/proactive-agent-spec.md` | 編集 |

---

## 備考

- ボタンのアニメーション、フィードバック追跡、課金ロジックは未実装（Phase 4の残りタスク）
- Exploreタブ、保存機能は削除予定（哲学に合わない）
- 時間帯フィルタリングは `cant_wake_up` のみ実装済み、他の問題は必要に応じて追加可能
