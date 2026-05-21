# Hook Card & Notification → Card ペア一覧（SSOT）

**このファイルは Hook Card・バリアント・全通知ペアの Single Source of Truth である。**  
カード文言、通知文言、バリアント一覧を更新する際はここを常に更新すること。

- **カタログ実体**: `apps/api/src/modules/problem_nudges/catalog/ja.json`, `en.json`（他 de, es, fr, pt-BR）
- **構成**: Notification Title = `titles.*` | Body = `hooks.*` | Card Hook = Body 同一 | Card Detail = `details.*`
- **スケジュール実装**: `aniccaios/Models/ProblemType.swift` → `notificationSchedule`

---

## 配信タイムテーブル（Pro ユーザー）

各 ProblemType に対し、以下の時刻でローカル通知（または Remote Push）が配信される。ユーザーが複数の ProblemType を選択している場合、全スロットが合算される（iOS 64件上限あり）。

| # | ProblemType | EN Title | JA Title | スロット数 | 配信時刻 | バリアント数 |
|---|-------------|----------|----------|-----------|---------|------------|
| 1 | staying_up_late | Put the Phone Down | スマホを置け | 5 | 20:00, 22:00, 23:30, 0:00, 1:00 | 35 |
| 2 | cant_wake_up | Get Up Now | 起きろ | 3 | 6:00, 6:45, 7:15 | 14 |
| 3 | self_loathing | Forgive Yourself | 自分を許せ | 3 | 8:00, 13:00, 19:00 | 14 |
| 4 | rumination | Return to Now | 今ここに戻れ | 3 | 8:30, 14:00, 21:00 | 14 |
| 5 | procrastination | Do It Now | 今すぐやれ | 3 | 9:15, 13:30, 17:00 | 14 |
| 6 | anxiety | You're Safe | 大丈夫 | 3 | 7:30, 12:15, 18:45 | 14 |
| 7 | lying | Be Honest | 正直に | 3 | 8:15, 13:15, 18:15 | 14 |
| 8 | bad_mouthing | Kind Words | 優しい言葉を | 3 | 9:30, 14:30, 19:30 | 14 |
| 9 | porn_addiction | Beat Your Lust | 性欲に勝て | 3 | 20:30, 22:30, 23:45 | 14 |
| 10 | alcohol_dependency | Don't Drink Tonight | 今夜は飲むな | 3 | 16:00, 18:00, 20:15 | 14 |
| 11 | anger | Let Go of Anger | 怒りを手放せ | 3 | 7:45, 12:30, 17:30 | 14 |
| 12 | obsessive | Stop Overthinking | 考えすぎ | 3 | 9:00, 13:45, 18:30 | 14 |
| 13 | loneliness | Reach Out | つながろう | 3 | 10:00, 15:00, 19:45 | 14 |

**補足:**
- staying_up_late と porn_addiction は深夜スロット（0:00, 1:00 等）を含む。`validTimeRange` は 6:00〜翌1:31。
- その他の ProblemType の `validTimeRange` は 6:00〜23:00。
- Free プランは 1日3回固定スロット（8:00, 12:30, 19:00）でローテーション配信。
- 各スロットでは `NudgeContentSelector` がバリアントを Day1 決定論的 or ランダム選択する。

---

## 全通知ペア一覧（Notification → Card）

通知: **Title** + **Body** → カード: **Title**（同一） + **Hook**（Body 同一） + **Detail**

### 1. staying_up_late（夜更かし）— 35バリアント

| # | EN Notification Body | JA Notification Body | EN Card Detail | JA Card Detail |
|---|---------------------|----------------------|----------------|----------------|
| 1 | Breathe, don't scroll. | スクロールより、呼吸。 | Move your phone 30cm from your face. Turn brightness to minimum. Take 5 deep breaths. Your brain will switch to 'sleep prep' mode. | スマホを顔から30cm離して、画面の明るさを最低にする。そして5回深呼吸。脳が「寝る準備」モードに切り替わる。 |
| 2 | It's 1 AM. Every minute awake costs you tomorrow. | 深夜1時です。起きている1分が明日を蝕みます。 | Staying awake past 1 AM causes measurable damage to your brain and heart. What you're doing is 100x less important than sleep. Go to bed now. | 深夜1時以降の覚醒は、脳と心臓に測定可能なダメージを与える。今やってることの100倍、睡眠の方が大事。今すぐ寝ろ。 |
| 3 | The screen can wait. Your dreams can't. | 画面は待てる。夢は待てない。 | The blue light is telling your brain it's noon. Your body is confused. Help it by putting the screen away. | ブルーライトが脳に「今は昼だ」と伝えてる。体が混乱してる。画面を消して助けてあげて。 |
| 4 | It's past midnight. Your body needs rest now. | 深夜0時を過ぎました。今すぐ休んでください。 | Move your phone 30cm from your face. Turn brightness to minimum. Take 5 deep breaths. Your brain will switch to 'sleep prep' mode. | スマホを顔から30cm離して、画面の明るさを最低にする。そして5回深呼吸。脳が「寝る準備」モードに切り替わる。 |
| 5 | Bed isn't a battlefield. | スクロールより、呼吸。 | One hour tonight ruins 8 hours tomorrow. Get in bed now. | 今夜の1時間が、明日の8時間を台無しにする。今すぐ布団に入れ。 |
| 6 | How many years have you lost to 'just 5 more minutes'? | その「あと5分だけ」で、何年失ってきた？ | A sleep-deprived brain has the same judgment as 0.1% blood alcohol. 17 hours awake = legally drunk. Protect tomorrow's decisions by sleeping tonight. | 睡眠不足の脳は血中アルコール0.1%と同じ判断力。17時間起きてると酔っ払いと同じ。明日の大事な判断を守るために、今夜は休もう。 |
| 7 | Put down your phone. Now. | スマホを置いて。今すぐ。 | Your willpower is at its lowest right now. Don't fight the urge to scroll—just remove the phone. Put it in another room. | 今、意志力は最低レベル。スクロール衝動と戦うな—スマホを消せ。別の部屋に置け。 |
| 8 | Every hour of sleep = better decisions tomorrow. | 睡眠1時間 = 明日の判断力向上。 | One hour of sleep tonight = 3 hours of productivity tomorrow. The math is simple. Go to bed. | 今夜の睡眠1時間 = 明日の生産性3時間。計算は簡単。寝ろ。 |
| 9 | Sleep is not optional. It's medicine. | 睡眠は贅沢じゃない。薬だ。 | A sleep-deprived brain has the same judgment as 0.1% blood alcohol. 17 hours awake = legally drunk. Protect tomorrow's decisions by sleeping tonight. | 睡眠不足の脳は血中アルコール0.1%と同じ判断力。17時間起きてると酔っ払いと同じ。明日の大事な判断を守るために、今夜は休もう。 |
| 10 | Your body wants to rest. | その「あと5分だけ」で、何年失ってきた？ | Blue light tells your brain it's daytime. Flip your phone and close your eyes. | 睡眠負債は返済できない。今すぐスマホを充電器に置いて、布団に入れ。 |
| 11 | Tomorrow's you will regret this. | 明日の自分、泣くよ。 | Will you remember this content tomorrow at noon? But sleep deprivation will definitely hurt your focus, judgment, and immunity. Which matters more? | 今見てるコンテンツ、明日の昼に思い出せる？でも睡眠不足は確実に集中力・判断力・免疫力を下げる。どっちが大事？ |
| 12 | Your future self is watching. What do they see? | 未来の自分が見てる。何が見える？ | Imagine waking up refreshed vs. waking up exhausted. Which version of tomorrow do you want? You decide right now. | すっきり起きる明日と、疲れ切って起きる明日。どっちがいい？今決まる。 |
| 13 | Tomorrow you will regret this. | 明日のお前が泣いてるぞ。 | One hour tonight ruins 8 hours tomorrow. Get in bed now. | 今夜の1時間が、明日の8時間を台無しにする。今すぐ布団に入れ。 |
| 14 | The screen can wait. Your dreams can't. | 睡眠1時間 = 明日の判断力向上。 | Will you remember this content tomorrow at noon? But sleep deprivation will definitely hurt your focus, judgment, and immunity. Which matters more? | 今見てるコンテンツ、明日の昼に思い出せる？でも睡眠不足は確実に集中力・判断力・免疫力を下げる。どっちが大事？ |
| 15 | Breathe, don't scroll. | 明日の自分、泣くよ。 | Sleep debt can't be repaid. Put phone on charger now and get in bed. | 頑張って起きてても意味ない。体に任せて寝よう。深呼吸を3回して。 |
| 16 | It's past midnight. Your body needs rest now. | 深夜0時を過ぎました。今すぐ休んでください。 | Sleep deprivation compounds like debt. Tonight's lost hour will steal next week's focus and judgment. Move your phone away from bed. Close your eyes. | 睡眠不足は借金のように蓄積する。今夜の1時間は、来週の集中力と判断力を確実に奪う。スマホを枕元から離して、目を閉じて。 |
| 17 | Sleep is not optional. It's medicine. | 睡眠は贅沢じゃない。薬だ。 | Sleep repairs your brain, consolidates memories, and resets emotions. Skipping it is like skipping maintenance on a car you drive daily. | 睡眠は脳を修復し、記憶を定着させ、感情をリセットする。サボるのは毎日乗る車のメンテをサボるのと同じ。 |
| 18 | Blue light tricks your brain. | スクリーンの光が脳を騙してる。 | Blue light tells your brain it's daytime. Flip your phone and close your eyes. | ブルーライトが「まだ昼だ」と脳に嘘をつく。スマホを伏せて、目を閉じろ。 |
| 19 | Every hour of sleep = better decisions tomorrow. | 寝不足は借金。利息がつく。 | Sleep deprivation compounds like debt. Tonight's lost hour will steal next week's focus and judgment. Move your phone away from bed. Close your eyes. | 睡眠不足は借金のように蓄積する。今夜の1時間は、来週の集中力と判断力を確実に奪う。スマホを枕元から離して、目を閉じて。 |
| 20 | How many years have you lost to 'just 5 more minutes'? | 深夜1時です。起きている1分が明日を蝕みます。 | Sleep-deprived tomorrow: 30% worse decisions. Flip phone over and close eyes. | 睡眠不足の明日は判断力が30%低下する。スマホを伏せて目を閉じろ。 |
| 21 | Sleep debt accrues interest. | 寝不足は借金。利息がつく。 | Sleep debt can't be repaid. Put phone on charger now and get in bed. | 睡眠負債は返済できない。今すぐスマホを充電器に置いて、布団に入れ。 |
| 22 | Sleep debt accrues interest. | 睡眠は努力じゃない。諦めろ。 | Staying awake past 1 AM causes measurable damage to your brain and heart. What you're doing is 100x less important than sleep. Go to bed now. | 深夜1時以降の覚醒は、脳と心臓に測定可能なダメージを与える。今やってることの100倍、睡眠の方が大事。今すぐ寝ろ。 |
| 23 | Tomorrow's you will regret this. | スマホを置いて。今すぐ。 | Drowsiness is your body's warning. Don't ignore it. Close your eyes. | スマホを持ち込むな。ベッドは寝る場所だ。別の部屋に充電器を置け。 |
| 24 | "5 more minutes" becomes 2 hours. | 5分だけ、が2時間になる。 | How many times have you said "5 more"? Close it now. Put phone in another room. | 「あと5分」が何回目だ？今すぐ閉じろ。スマホを別の部屋に置け。 |
| 25 | Sleep isn't effort. Let go. | ベッドは戦場じゃない。 | Sleep repairs your brain, consolidates memories, and resets emotions. Skipping it is like skipping maintenance on a car you drive daily. | 睡眠は脳を修復し、記憶を定着させ、感情をリセットする。サボるのは毎日乗る車のメンテをサボるのと同じ。 |
| 26 | It's 1 AM. Every minute awake costs you tomorrow. | 未来の自分が見てる。何が見える？ | Don't bring your phone. Bed is for sleep. Put charger in another room. | ダラダラ終わるな。「今日はここまで！」と声に出して寝ろ。 |
| 27 | Sleep isn't effort. Let go. | 睡眠は努力じゃない。諦めろ。 | Staying up by force is pointless. Trust your body. Take 3 deep breaths. | 頑張って起きてても意味ない。体に任せて寝よう。深呼吸を3回して。 |
| 28 | Heavy eyes are your body's SOS. | お前の体は休みたがってる。 | One hour of sleep tonight = 3 hours of productivity tomorrow. The math is simple. Go to bed. | 今夜の睡眠1時間 = 明日の生産性3時間。計算は簡単。寝ろ。 |
| 29 | Put down your phone. Now. | 画面は待てる。夢は待てない。 | Don't drift. Say out loud "Today ends here!" and go to sleep. | これを読んだら終わり。画面をオフにしろ。今すぐ布団に入れ。 |
| 30 | Don't sacrifice tomorrow for tonight. | 明日やりたいこと、今夜で潰すな。 | Sleep-deprived tomorrow: 30% worse decisions. Flip phone over and close eyes. | 睡眠不足の明日は判断力が30%低下する。スマホを伏せて目を閉じろ。 |
| 31 | Heavy eyes are your body's SOS. | 目が重いのは体のSOS。 | Drowsiness is your body's warning. Don't ignore it. Close your eyes. | 眠気は体からの警告。無視しないで。従って。目を閉じて。 |
| 32 | Bed isn't a battlefield. | ベッドは戦場じゃない。 | Don't bring your phone. Bed is for sleep. Put charger in another room. | スマホを持ち込むな。ベッドは寝る場所だ。別の部屋に充電器を置け。 |
| 33 | You decide when the day ends. | 1日の終わりを自分で決めろ。 | Don't drift. Say out loud "Today ends here!" and go to sleep. | ダラダラ終わるな。「今日はここまで！」と声に出して寝ろ。 |
| 34 | Your body wants to rest. | お前の体は休みたがってる。 | Mind says "stay up". Body says "done". Put phone down. 3 deep breaths. Close eyes. | 心は「まだ起きてたい」。体は「もう限界」。スマホを置いて、深呼吸3回して目を閉じろ。 |
| 35 | Close your phone now. | 今すぐスマホを閉じろ。 | Done reading this? Screen off. Get in bed now. | これを読んだら終わり。画面をオフにしろ。今すぐ布団に入れ。 |

※ Title: EN "Put the Phone Down" / JA "スマホを置け"

---

### 2. cant_wake_up（起きられない）— 14バリアント

| # | EN Notification Body | JA Notification Body | EN Card Detail | JA Card Detail |
|---|---------------------|----------------------|----------------|----------------|
| 1 | Your day won't start until you get up. | 起きるまで1日は始まらない。 | Count 5, 4, 3, 2, 1 and put your feet on the floor. Move before you think. Get up before your brain makes excuses. Nothing changes under the blanket. | 5、4、3、2、1と数えて足を床に。考える前に動け。脳が言い訳する前に起きろ。布団の中では何も変わらない。 |
| 2 | Your alarm is a promise. Keep it. | アラームは約束。守れ。 | Every morning you hit snooze, you break a promise to yourself. Small betrayals compound. Start today with integrity. | スヌーズを押すたびに自分との約束を破ってる。小さな裏切りは複利で増える。今日は誠実に始めろ。 |
| 3 | Just put feet on floor. That's enough. | 足を床につけろ。それだけでいい。 | Don't stand up yet. Just feet on floor. Body temp starts rising. | 起き上がらなくていい。まず足を床に。体温が上がり始める。 |
| 4 | The 'just 5 more minutes' you has zero credibility. | 「あと5分」の自分、信用ゼロ。 | How many times have you trusted the '5 more minutes' you? How many times were you betrayed? Getting up now keeps a promise to yourself. You'll like today's you. | 「あと5分」の自分を何回信じた？何回裏切られた？今起きれば自分との約束を守れる。今日の自分を好きになれる。 |
| 5 | Morning wins build confidence. | 朝の勝利が自信を作る。 | People who win mornings win days. People who win days win weeks. It starts with getting up when you said you would. | 朝を制する者は1日を制する。1日を制する者は1週間を制する。全ては決めた時間に起きることから始まる。 |
| 6 | The blanket is a trap. | 布団の中は罠。 | Warm and cozy. That's why it's dangerous. Count 3 and jump out! | 暖かくて気持ちいい。だから危険。3秒数えて飛び出せ！ |
| 7 | Stay Mediocre | 凡人のままでいろ | Start today sloppy again? Or change starting now? Your action in the next 5 seconds decides. Stand up. | また今日もダラダラ始める？それとも今から変わる？次の5秒の行動が決める。立て。 |
| 8 | Get up now, or regret it at noon. | 今起きろ。昼に後悔するぞ。 | Noon-you will be grateful. Evening-you will be proud. But only if morning-you gets up now. | 昼の自分は感謝する。夜の自分は誇りに思う。でも朝の自分が今起きた場合だけ。 |
| 9 | 1 morning minute = 10 night minutes. | 朝の1分は夜の10分。 | Morning delay means evening rush. Move now for yourself. | 朝ダラダラした分、夜に焦る。自分のために今動こう。 |
| 10 | Feet on the floor. 5, 4, 3, 2, 1. | 足を床に。5、4、3、2、1。 | Your body is awake. Your mind is making excuses. Override it. Feet on the floor. Now. | 体は起きてる。脳が言い訳してるだけ。上書きしろ。足を床に。今すぐ。 |
| 11 | Snoozing is betrayal. | 二度寝は裏切り。 | "5 more minutes" becomes 30. Get up now. | 「あと5分」が30分になる。今すぐ起き上がれ。 |
| 12 | Sunlight wakes your brain. | 朝日を浴びろ。脳が起きる。 | Open curtains. 2500+ lux resets your circadian rhythm. | カーテンを開けろ。2500ルクス以上の光が体内時計をリセットする。 |
| 13 | The blanket is lying to you. | 布団は嘘をついてる。 | The blanket feels safe, but it's a trap. Comfort now = regret later. Rip off the blanket like a bandaid. | 布団は安全に感じる。でも罠だ。今の快適 = 後の後悔。絆創膏を剥がすように布団を剥がせ。 |
| 14 | Put alarm across the room. | 目覚ましを遠くに置け。 | Walking to it wakes your brain. Start tomorrow. Not by pillow. | 取りに行く間に脳が起きる。明日から実行。枕元に置くな。 |

※ Title: EN "Get Up Now" / JA "起きろ"

---

### 3. self_loathing（自己嫌悪）— 14バリアント

| # | EN Notification Body | JA Notification Body | EN Card Detail | JA Card Detail |
|---|---------------------|----------------------|----------------|----------------|
| 1 | You're alive today. That's enough. | 今日も生きてる。それで十分。 | Self-loathing proves you want to be better. But self-criticism doesn't lead to growth—it backfires. You woke up today. That's enough. | 自己嫌悪は良くなりたい証拠。でも自己批判は成長につながらない—逆効果。今日起きた。それで十分。 |
| 2 | You're trying. That's what matters. | 頑張ってる。それが大事。 | Progress isn't linear. Bad days don't erase good days. You're trying, and that's more than most people do. | 進歩は直線じゃない。悪い日は良い日を消さない。頑張ってる、それは多くの人がやらないこと。 |
| 3 | You don't have to be perfect. | 完璧じゃなくていい。 | Don't aim for 100. Write down 1 thing you did today. That's enough. | 100点を目指すな。今日できた1つのことを紙に書き出せ。それで十分。 |
| 4 | It's okay to stop blaming yourself. | 自分を責めるのをやめていい。 | If your best friend was in your situation, what would you say? You wouldn't say 'You're worthless.' Give yourself the same kindness. | 親友が同じ状況だったら何て言う？「お前は価値がない」とは言わないでしょ。自分にも同じ優しさを。 |
| 5 | Your worth isn't measured by productivity. | あなたの価値は生産性で測れない。 | You are not your productivity. You are not your achievements. You are worthy of love and rest just by existing. | あなたは生産性じゃない。あなたは実績じゃない。存在するだけで愛と休息に値する。 |
| 6 | Failure is proof you tried. | 失敗は証拠。挑戦した証拠。 | Failing means you tried. Put hand on chest. Say "well done". | 失敗したってことは、やったってこと。胸に手を当てて「よくやった」と言え。 |
| 7 | You're a much better person than you think. | あなたは思ってるより良い人。 | Is what you're blaming yourself for truly 'irreparable'? Most things are smaller than they feel. Take a deep breath and look objectively. | 自分を責めてること、本当に「取り返しがつかない」？ほとんどのことは感じてるより小さい。深呼吸して客観的に見て。 |
| 8 | Be kind to yourself. Just for today. | 自分に優しく。今日だけでいい。 | Just for today, speak to yourself like you'd speak to someone you love. Just for today. Tomorrow you can go back to being hard on yourself if you want. | 今日だけ、愛する人に話すように自分に話して。今日だけ。明日また厳しくしていいから。 |
| 9 | Don't compare to others. Compare to yesterday. | 他人と比べるな。昨日の自分と比べろ。 | Comparing their highlights to your behind-scenes is pointless. Close the app. | SNSのハイライトと自分の裏側を比べても無意味。アプリを閉じろ。 |
| 10 | Self-criticism won't make you better. Compassion will. | 自己批判は成長させない。自己慈悲が成長させる。 | Research shows self-compassion leads to more growth than self-criticism. Being harsh on yourself doesn't work. Try kindness instead. | 研究によると、自己慈悲の方が自己批判より成長につながる。自分に厳しくしても効果がない。優しさを試して。 |
| 11 | Self-blame changes nothing. | 自分を責めても何も変わらない。 | Use blame energy for next step. Do 1 small thing right now. | 責めるエネルギーを、次の一歩に使え。今すぐ1つ小さなことをやれ。 |
| 12 | You're trying harder than you think. | お前は思ってるより頑張ってる。 | Even routine stuff is effort. Look in mirror. Say "good job". | 当たり前にやってることも、実は頑張り。鏡を見て「お疲れさま」と言え。 |
| 13 | Would you say this to a friend? Then don't say it to yourself. | 友達にそれ言う？なら自分にも言うな。 | You wouldn't let anyone else talk to your friend this way. Why do you let yourself talk to you this way? Protect yourself like you'd protect a friend. | 友達に誰かがこう言ったら許さないでしょ。なぜ自分には許すの？友達を守るように自分を守って。 |
| 14 | No excuses. Take action. | 言い訳するな。行動しろ。 | No time to feel down. Do 1 thing. Clean your desk. Now. | 落ち込んでる暇があったら1つやれ。机の上を片付けろ。今すぐ。 |

※ Title: EN "Forgive Yourself" / JA "自分を許せ"

---

### 4. rumination（反芻）— 14バリアント

| # | EN Notification Body | JA Notification Body | EN Card Detail | JA Card Detail |
|---|---------------------|----------------------|----------------|----------------|
| 1 | What are you feeling right now? | 今、何を感じてる？ | Once you notice the loop, you're halfway done. Now: focus on the soles of your feet. The floor's hardness, temperature. Just 30 seconds. | ループに気づいた時点で半分終わり。今：足の裏に集中。床の硬さ、温度。30秒だけ。 |
| 2 | Thinking about it won't change it. | 考えても変わらない。 | Rumination is your brain trying to solve an unsolvable problem. It can't be solved by thinking. Accept that, and let it go. | 反芻は脳が解決不能な問題を解こうとしてる。考えても解決しない。それを受け入れて、手放して。 |
| 3 | What do you see? What do you hear? | 今、何が見える？何が聞こえる？ | Focus on senses. Name 5 things you see out loud. That's "here and now". | 五感に集中しろ。目の前のものを5つ声に出して言え。それが「今ここ」。 |
| 4 | Are you present right now? | 今、ここにいる？ | Name 5 things you see, 4 you hear, 3 you're touching, 2 you smell, 1 you taste. This forces you back to 'now.' | 見えるもの5つ、聞こえるもの4つ、触れてるもの3つ、匂い2つ、味1つ。これで「今」に戻れる。 |
| 5 | Name 5 things you see. Start now. | 見えるもの5つ言って。今すぐ。 | Look around you. Name what you see. "Chair. Window. Light. Book." This simple act pulls you out of your head and into reality. | 周りを見て。見えるものを言って。「椅子。窓。光。本。」この単純な行為が頭の中から現実に引き戻す。 |
| 6 | Stop the loop in your head. | 頭の中のループを止めろ。 | Write it down. Getting it out helps. Write for 3 minutes straight. | 紙に書き出せ。頭の外に出すと楽になる。3分だけ書き続けろ。 |
| 7 | Why not meditate for 5 minutes? | 5分、瞑想してみない？ | The most effective way to stop rumination is meditation. For 2 minutes now, focus only on breathing. Inhale 4 sec, hold 4 sec, exhale 4 sec. | 反芻を止める最も効果的な方法は瞑想。今から2分、呼吸だけに集中。4秒吸って、4秒止めて、4秒吐いて。 |
| 8 | Your thoughts are not facts. | 思考は事実じゃない。 | Thoughts are like clouds. They pass. You don't have to grab them, analyze them, or follow them. Just watch them go. | 思考は雲のようなもの。過ぎていく。つかまなくていい、分析しなくていい、追わなくていい。見送るだけ。 |
| 9 | Thinking won't give answers. | 考えても答えは出ない。 | Thinking 100 times changes nothing. Stand up. Walk 10 steps. | 同じことを100回考えても変わらない。立ち上がって10歩歩け。 |
| 10 | The loop is a trap. Step out. | そのループは罠。抜け出せ。 | You've been in this loop before. It never solved anything. The only way out is to do something physical. Stand up. Move. | このループは前にもあった。何も解決しなかった。唯一の出口は体を動かすこと。立って。動いて。 |
| 11 | Past can't change. Change now. | 過去は変えられない。今を変えろ。 | Time spent regretting = time for action. Pick 1 task. Do it. | 過去を悔やむ時間で、今できることをやれ。1つだけタスクを選べ。 |
| 12 | Overthinking is brain spinning wheels. | 考えすぎは脳の空回り。 | Shift gears. Stand up. Swing arms in big circles 10 times. | ギアを入れ替えろ。立ち上がって腕を大きく10回回せ。 |
| 13 | Notice your feet. Feel the floor. You're here. | 足の裏を感じて。床を感じて。ここにいる。 | Your feet are on the ground. Your lungs are breathing. You are here, in this moment, safe. The past is gone. The future isn't here yet. | 足は地面についてる。肺は呼吸してる。あなたは今ここにいて、安全。過去は終わった。未来はまだ来てない。 |
| 14 | Stop spinning in your head. | 頭の中でぐるぐる回すな。 | Don't think. Move. Stand up and breathe outside air now. | 考えるな。動け。今すぐ立ち上がって外の空気を吸え。 |

※ Title: EN "Return to Now" / JA "今ここに戻れ"

---

### 5. procrastination（先延ばし）— 14バリアント

| # | EN Notification Body | JA Notification Body | EN Card Detail | JA Card Detail |
|---|---------------------|----------------------|----------------|----------------|
| 1 | Just 5 minutes. That's all you need. | たった5分。それだけでいい。 | If it takes under 2 minutes, do it now. If it takes longer, just do the first 2 minutes. Once you start, your brain wants to continue. That's science. | 2分以内なら今やれ。それ以上なら最初の2分だけやれ。始めれば脳は続けたくなる。科学的事実。 |
| 2 | What would you tell a friend who keeps delaying? | 先延ばしする友達に何て言う？ | If your friend kept delaying something important, you'd tell them to just start. Be that friend to yourself right now. | 友達が大事なことを先延ばしし続けたら、「とにかく始めろ」と言うでしょ。今、自分にその友達になれ。 |
| 3 | Motivation won't come if you wait. | 「やる気」は待っても来ない。 | Motivation follows action. Count down: 5, 4, 3, 2, 1, GO. | やる気は行動の後に来る。5秒数えて動き出せ。5, 4, 3, 2, 1, GO。 |
| 4 | Breaking another promise to yourself? | また自分との約束破る？ | Imagine yourself a week from now. 'I wish I'd done it then...' Regretting? Do it now and that regret disappears. | 1週間後の自分を想像して。「あの時やっておけば…」後悔してる？今やればその後悔は消える。 |
| 5 | Done is better than perfect. | 完璧より完了。 | Shipped is better than perfect. A finished project with flaws beats an unfinished 'masterpiece' every time. | 出荷が完璧に勝る。欠陥のある完成品は未完成の「傑作」にいつも勝つ。 |
| 6 | Procrastination is debt to future you. | 先延ばしは未来の自分への借金。 | You'll pay with interest. Pay now. Pick 1 task. Start. | 利息付きで返すことになる。今返せ。タスクを1つ選んで始めろ。 |
| 7 | Every reason not to do it is an excuse. | やらない理由は全部言い訳。 | 'Can't do it' and 'don't want to' are different. Which is it right now? If you don't want to, why? Find the real reason. | 「できない」と「やりたくない」は違う。今どっち？やりたくないなら、なぜ？本当の理由を見つけて。 |
| 8 | Future you is counting on present you. | 未来の自分は今の自分を頼りにしてる。 | Future you is watching. They're either grateful you started now, or frustrated you didn't. Make future you grateful. | 未来の自分が見てる。今始めたことに感謝するか、始めなかったことにイラつくか。未来の自分を感謝させろ。 |
| 9 | Just do the first minute. | 最初の1分だけやれ。 | Just 1 minute. OK to stop after. But you won't. Trust me and try. | 1分だけ。それで終わってもいい。でも大抵続く。騙されたと思ってやれ。 |
| 10 | Start ugly. Refine later. | 汚くても始めろ。後で直せ。 | Perfectionism is procrastination in disguise. A messy start is infinitely better than no start. Write one bad sentence. Take one ugly step. | 完璧主義は先延ばしの変装。汚いスタートはスタートしないより無限に良い。下手な一文を書け。醜い一歩を踏め。 |
| 11 | 2-minute tasks: do now. | 2分でできることは今やれ。 | 2-minute rule. Not worth postponing. Set timer. Go. | 2分ルール。それ以下なら先延ばしする価値もない。タイマーをセット。 |
| 12 | "Later" is another word for "never". | 「後で」は「やらない」の別名。 | Do it later? Really? Do it now. Put phone down. Start immediately. | 後でやる？本当に？今やれ。スマホを置いて、今すぐ始めろ。 |
| 13 | The hardest part is the first 2 minutes. | 一番難しいのは最初の2分。 | Your brain hates starting. But once you're 2 minutes in, momentum takes over. Just survive the first 2 minutes. | 脳は始めるのが嫌い。でも2分経てば勢いがつく。最初の2分だけ生き延びろ。 |
| 14 | Don't wait for perfect. Start. | 完璧を待つな。始めろ。 | Perfect prep doesn't exist. Adjust as you go. Write just 1 line. | 完璧な準備なんてない。やりながら整えよう。まず1行だけ書け。 |

※ Title: EN "Do It Now" / JA "今すぐやれ"

---

### 6. anxiety（不安）— 14バリアント

| # | EN Notification Body | JA Notification Body | EN Card Detail | JA Card Detail |
|---|---------------------|----------------------|----------------|----------------|
| 1 | In this moment, you are safe. | この瞬間、あなたは安全。 | Anxiety is fear of what hasn't happened yet. Right now, what's actually happening in front of you? Nothing dangerous is occurring. | 不安はまだ起きてないことへの恐れ。今、目の前で実際に何が起きてる？危険なことは何も起きてない。 |
| 2 | This feeling will pass. It always does. | この感覚は過ぎ去る。いつもそう。 | This feeling has a beginning, a middle, and an end. You're somewhere in the middle. The end is coming. Wait for it. | この感覚には始まり、中間、終わりがある。あなたは中間のどこか。終わりは来る。待って。 |
| 3 | This moment is safe. | 今、この瞬間は安全。 | Anxiety is about future. Right now is OK. Feel your feet on the floor. | 不安は未来のこと。今、この瞬間は大丈夫。足の裏を床に感じろ。 |
| 4 | What are you feeling right now? | 今、何を感じてる？ | Not 'I am anxious' but 'I am feeling anxiety.' Anxiety is like weather. It comes, and it goes. | 「不安だ」じゃなく「不安を感じてる」。不安は天気のようなもの。来て、去る。 |
| 5 | Name it to tame it. What's the fear? | 名前をつけて手なずけろ。何が怖い？ | What exactly are you afraid of? Say it out loud. "I'm afraid that..." Naming the fear takes away some of its power. | 具体的に何が怖い？声に出して言って。「私が怖いのは…」恐れに名前をつけると力が弱まる。 |
| 6 | Think worst case. You'll survive. | 最悪のケースを考えろ。それでも生きてる。 | Even if worst happens, you'll cope. Write 3 reasons you'll be OK even in worst case. | 最悪が起きても、対処できる。紙に「最悪でも大丈夫な理由」を3つ書け。 |
| 7 | Deep breath. Inhale 4, hold 4, exhale 4. | 深呼吸。4秒吸って、4秒止めて、4秒吐いて。 | Inhale 4 sec → hold 4 sec → exhale 4 sec → hold 4 sec. Repeat 3 times. When your body calms, your mind follows. Do it now. | 4秒吸って → 4秒止めて → 4秒吐いて → 4秒止めて。3回繰り返して。体が落ち着けば、心もついてくる。今やって。 |
| 8 | You've survived 100% of your worst days. | 最悪の日を100%生き延びてきた。 | Your track record for surviving bad days is 100%. Whatever this is, you'll get through it too. | 悪い日を生き延びた実績は100%。これが何であれ、乗り越えられる。 |
| 9 | 90% of worries never happen. | 不安の9割は起きない。 | Statistically, most worries don't materialize. Focus only on what's happening now. | 統計的に、心配事のほとんどは現実にならない。今起きてることだけに集中。 |
| 10 | Anxiety lies. Right now, you are okay. | 不安は嘘をつく。今、あなたは大丈夫。 | Your brain is trying to protect you from a threat that isn't here. Thank it, then tell it: "I'm safe right now." | 脳はここにない脅威からあなたを守ろうとしてる。感謝して、こう言って：「今、私は安全」。 |
| 11 | Focus on what you control. | コントロールできることに集中。 | Worrying about uncontrollables is useless. Write 1 thing you can control. | 変えられないことを心配しても無駄。変えられることを1つ書き出せ。 |
| 12 | Anxiety is a movie in your head. | 不安は頭の中の映画。 | Cancel the screening. Close eyes. Say "Cut!" Imagine a different scene. | 上映中止にしろ。目を閉じて「カット！」と言え。別のシーンを想像しろ。 |
| 13 | Feel your feet. You're grounded. | 足の裏を感じて。地に足がついてる。 | Press your feet firmly into the floor. Feel the ground holding you up. You are supported. You are here. You are safe. | 足を床にしっかり押し付けて。地面があなたを支えてるのを感じて。あなたは支えられてる。ここにいる。安全だ。 |
| 14 | Don't lose to anxiety. Move. | 不安に負けるな。動け。 | Don't sit and worry. Stand and walk 10 steps now. Movement changes mood. | 座って心配するな。今すぐ立って10歩歩け。体を動かせば気分が変わる。 |

※ Title: EN "You're Safe" / JA "大丈夫"

---

### 7. lying（嘘）— 14バリアント

| # | EN Notification Body | JA Notification Body | EN Card Detail | JA Card Detail |
|---|---------------------|----------------------|----------------|----------------|
| 1 | Today is a day to live honestly. | 今日は正直に生きる日。 | Small lies lead to big lies. One lie requires another lie to protect it. Being honest today makes tomorrow simpler. | 小さな嘘は大きな嘘につながる。1つの嘘を守るために別の嘘が必要。今日正直にすれば明日が単純になる。 |
| 2 | Honesty is exhausting. But lies are more exhausting. | 正直は疲れる。でも嘘はもっと疲れる。 | Lying takes mental energy. Remembering lies, maintaining them, worrying about exposure. Honesty is actually easier. | 嘘はメンタルエネルギーを消費する。嘘を覚えて、維持して、バレる心配して。正直の方が実は楽。 |
| 3 | Courage to tell the truth. | 本当のことを言う勇気。 | Scary, but you'll feel lighter after. Breathe deep. Share 1 truth. | 怖いけど、言った後は楽になる。深呼吸して、1つ正直に伝えてみよう。 |
| 4 | One truth builds more trust than ten lies. | 1つの真実は10の嘘より信頼を築く。 | Trust is built in drops and lost in buckets. Every lie chips away at it. Every truth adds a drop. | 信頼は一滴ずつ築かれ、バケツで失われる。嘘のたびに削られる。真実のたびに一滴増える。 |
| 5 | Your word is your bond. Protect it. | 言葉は絆。守れ。 | When you say something, mean it. When you promise, deliver. Your word should be unbreakable. Start today. | 何かを言うなら本気で。約束したら果たせ。あなたの言葉は不可侵であるべき。今日から始めろ。 |
| 6 | Don't hate yourself for lying. | 嘘をつく自分を嫌いになるな。 | Acknowledge the lie. Be honest next time. Future over past. | 嘘をついたことを認めて、次は正直に。過去より未来。 |
| 7 | The truth is lighter to carry. | 真実の方が軽い。 | Carrying a lie is heavy. You have to remember it, maintain it, worry about it. The truth requires no maintenance. | 嘘を抱えるのは重い。覚えて、維持して、心配して。真実はメンテナンス不要。 |
| 8 | Small lies grow into big ones. Stop now. | 小さな嘘は大きくなる。今やめろ。 | Every small lie makes the next one easier. Break the pattern now before it becomes who you are. | 小さな嘘のたびに次が簡単になる。それがあなたになる前に今パターンを壊せ。 |
| 9 | Honesty is easy. Lies are tiring. | 正直は楽。嘘は疲れる。 | Maintaining lies takes huge energy. Honesty is easier. Say 1 thing honestly today. | 嘘を維持するエネルギーは膨大。正直の方が楽。今日1つ、正直に言い直せ。 |
| 10 | Lies compound. Truth simplifies. | 嘘は複利で増える。真実は単純にする。 | One lie needs another to cover it. Then another. The web grows. Simplify your life: tell the truth. | 1つの嘘を隠すのに別の嘘が必要。また別の。網は広がる。人生を単純に：真実を言え。 |
| 11 | Lies cost more than they gain. | 嘘で得るものより、失うものが大きい。 | Trust once lost is hard to regain. Choose honesty starting today. | 信頼は一度失うと取り戻せない。今日から正直を選べ。 |
| 12 | Were you honest today? | 今日は正直でいられたか？ | Reflect at day's end. Be more honest tomorrow. Give yourself a check mark. | 一日の終わりに振り返れ。明日はもっと正直に。自分に◯をつけろ。 |
| 13 | What would happen if you just told the truth? | もし真実を言ったらどうなる？ | Most of the time, the truth isn't as scary as we think. People respect honesty more than perfection. Try it. | ほとんどの場合、真実は思ってるほど怖くない。人は完璧より正直を尊敬する。試してみて。 |
| 14 | Stop lying. Right now. | 嘘をやめろ。今すぐ。 | Recall 1 lie you told today. Say it honestly next time. | 今日ついた嘘を1つ思い出せ。次は正直に言い直せ。 |

※ Title: EN "Be Honest" / JA "正直に"

---

### 8. bad_mouthing（悪口）— 14バリアント

| # | EN Notification Body | JA Notification Body | EN Card Detail | JA Card Detail |
|---|---------------------|----------------------|----------------|----------------|
| 1 | No hurtful words today. | 今日は傷つける言葉を言わない。 | Words can't be unspoken. Before you say something about someone, ask: is it true? Is it kind? Is it necessary? | 言葉は取り消せない。誰かについて言う前に聞いて：それは本当？優しい？必要？ |
| 2 | What you say about others says more about you. | 他人の悪口は自分を語る。 | When you talk negatively about others, people wonder what you say about them. It damages your reputation more than theirs. | 他人の悪口を言うと、人はあなたが自分のことも言うか疑問に思う。相手より自分の評判が傷つく。 |
| 3 | Instead of criticism, find the good. | 悪口の代わりに、良いところを探せ。 | Everyone has good points. Find 1 good thing about that person. | 誰にでも良いところはある。その人の良い点を1つ見つけてみよう。 |
| 4 | How would you feel if someone said that to you? | 誰かにそれ言われたらどう思う？ | Imagine those words being said about you, in a room you just walked into. That's how it feels. Don't do it. | その言葉があなたについて言われてると想像して、あなたが入ったばかりの部屋で。そういう気持ち。やめて。 |
| 5 | 5 minutes of gossip, 5 hours of regret. | 5分の悪口、5時間の後悔。 | That temporary feeling of superiority isn't worth the guilt that follows. And it always follows. | 一時的な優越感は後に来る罪悪感に値しない。そして必ず来る。 |
| 6 | Words can't be unsaid. | 言葉は取り消せない。 | Once said, it's out. Think 3 seconds. Is it really necessary? | 一度言ったら消えない。言う前に3秒考えろ。本当に必要か？ |
| 7 | Gossip hurts you more than them. | 悪口は相手より自分を傷つける。 | Talking badly feels good for a moment. But 5 minutes later, self-loathing arrives. Plus, listeners think 'they'll talk about me too.' | 悪口は一瞬気持ちいい。でも5分後に自己嫌悪が来る。しかも聞いてる人は「私のことも言うだろう」と思う。 |
| 8 | Would you want your kids to hear this? | 子供に聞かせたい？ | If your children heard you right now, would you be proud? Let that guide your words. | 今、子供が聞いてたら誇りに思う？それで言葉を導いて。 |
| 9 | Why do you want to criticize them? | なぜその人を批判したい？ | Is something of yours reflected? Write it down. Reflect. | 自分の何かが反映されてないか？紙に書いて内省しろ。 |
| 10 | Speak about others as if they're listening. | 相手が聞いてるつもりで話せ。 | If they were standing right behind you, would you say it? If not, don't say it at all. Speak as if everyone can hear. | 相手がすぐ後ろに立ってたら言う？言わないなら、全く言うな。みんなが聞こえるつもりで話せ。 |
| 11 | Bad words come back to you. | 悪口は自分に返ってくる。 | Words you say stain your own heart. Compliment 1 person today. | 言った言葉は、自分の心も汚す。今日1つ、誰かを褒めてみよう。 |
| 12 | Silence is golden. | 沈黙は金。 | What doesn't need saying, don't say. That's kindness too. Close mouth. Smile. | 言わなくていいことは、言わない。それも優しさ。口を閉じて笑え。 |
| 13 | Kindness is strength. Gossip is weakness. | 優しさは強さ。悪口は弱さ。 | Strong people don't need to put others down. Gossip is a sign of insecurity. Rise above it. | 強い人は他人を落とす必要がない。悪口は不安の表れ。超えろ。 |
| 14 | What do you say when they're not there? | その人がいない場所で何を言う？ | If you can't say it to their face, don't say it. Think 3 seconds before speaking. | 本人の前で言えないことは、言うな。3秒考えてから口を開け。 |

※ Title: EN "Kind Words" / JA "優しい言葉を"

---

### 9. porn_addiction（ポルノ依存）— 14バリアント

| # | EN Notification Body | JA Notification Body | EN Card Detail | JA Card Detail |
|---|---------------------|----------------------|----------------|----------------|
| 1 | Beat the temptation. Tomorrow's you will change. | 誘惑に勝て。明日の自分が変わる。 | The urge is like a wave—it peaks and falls. Do something else for 10 minutes. Walk, push-ups, splash cold water on your face. | 衝動は波のようなもの—ピークが来て落ちる。10分間別のことをして。歩く、腕立て、冷水を顔にかける。 |
| 2 | 10 push-ups. Now. Redirect the energy. | 腕立て10回。今すぐ。エネルギーを変えろ。 | Physical action breaks the mental loop. Right now: 10 push-ups, 10 squats, or 10 jumping jacks. Move your body. | 身体的行動がメンタルのループを壊す。今すぐ：腕立て10回、スクワット10回、またはジャンピングジャック10回。体を動かせ。 |
| 3 | Loneliness is the enemy. Talk to someone. | 孤独は敵。誰かと話せ。 | Loneliness strengthens urges. Text someone now. "How are you?" is enough. | 孤独が衝動を強める。今すぐ誰かにLINEしろ。「元気？」だけでいい。 |
| 4 | Do you really want it? Or are you just escaping? | 本当に欲しい？逃げてるだけ？ | When you want to escape into sexual content, what are you really running from? Stress? Loneliness? Boredom? Find the root cause. | 性的コンテンツに逃げたいとき、本当は何から逃げてる？ストレス？孤独？退屈？根本原因を見つけて。 |
| 5 | Cold water on your face. Break the pattern. | 冷水を顔に。パターンを壊せ。 | Cold water shocks your system and resets your brain. Go to the bathroom, splash cold water on your face. It works. | 冷水はシステムにショックを与え、脳をリセットする。洗面所に行って、冷水を顔にかけて。効く。 |
| 6 | You can win today. You won yesterday. | 今日も勝てる。昨日も勝った。 | Small daily wins add up. Win today, tomorrow gets easier. | 毎日の小さな勝利が積み重なる。今日も勝てば、明日はもっと楽。 |
| 7 | The urge is a wave. It will pass in 10 minutes. | 衝動は波。10分で過ぎ去る。 | Urges peak at about 10 minutes and then decline. You just need to survive 10 minutes. Set a timer. Do anything else. | 衝動は約10分でピークに達し、その後減少する。10分生き延びればいい。タイマーをセット。他のことをして。 |
| 8 | This moment of weakness doesn't define you. | この弱さの瞬間はあなたを定義しない。 | You are not your urges. This moment of weakness is temporary. The person you want to be is still there. Choose that person now. | あなたは衝動じゃない。この弱さの瞬間は一時的。なりたい人はまだそこにいる。今、その人を選べ。 |
| 9 | Wait 30 seconds. It changes everything. | 30秒だけ待て。それで変わる。 | Urges weaken after 30 seconds. Set timer. Count to 30. | 衝動は30秒で弱まり始める。タイマーをセットして30秒数えろ。 |
| 10 | What are you really running from? | 本当は何から逃げてる？ | Sexual content can become a numbing escape. What pain are you trying to numb? Address the pain, and the need for numbing decreases. | 性的コンテンツは麻痺的な逃避になりうる。何の痛みを麻痺させようとしてる？痛みに対処すれば、麻痺の必要性が減る。 |
| 11 | Put phone in another room. | スマホを別の部屋に置け。 | Physical distance is a barrier. You'll come to senses walking to get it. Do it now. | 物理的な距離がバリアになる。取りに行く間に我に返れる。今すぐ置け。 |
| 12 | Count your wins. | 勝利を数えろ。 | How many days have you won? Write the number. Make it bigger. | 今日まで何日勝ってきた？紙に数字を書け。その数字を増やせ。 |
| 13 | Your brain is lying. You don't need it. | 脳が嘘をついてる。必要ない。 | Your brain is releasing dopamine in anticipation. It's a chemical trick. You don't actually need it. The craving is a lie. | 脳は期待してドーパミンを放出してる。化学的なトリック。実際には必要ない。渇望は嘘。 |
| 14 | Can you face tomorrow's you? | 明日の自分に顔向けできるか？ | Will you regret this choice tomorrow? Choose for future you now. | 今の選択を明日後悔しないか？未来の自分のために、今選べ。 |

※ Title: EN "Beat Your Lust" / JA "性欲に勝て"

---

### 10. alcohol_dependency（アルコール依存）— 14バリアント

| # | EN Notification Body | JA Notification Body | EN Card Detail | JA Card Detail |
|---|---------------------|----------------------|----------------|----------------|
| 1 | One day at a time. You can do this. | 1日ずつ。できる。 | Don't think about forever. Just today. Just this hour. Just this moment. One day at a time is how every recovery starts. | 永遠のことは考えるな。今日だけ。この1時間だけ。この瞬間だけ。1日ずつ—全ての回復はそうやって始まる。 |
| 2 | Call someone instead. Anyone. | 代わりに誰かに電話して。誰でもいい。 | Connection is the opposite of addiction. Call someone. Text someone. Don't be alone with the craving. | つながりは依存症の反対。誰かに電話して。メッセージして。渇望と一人でいるな。 |
| 3 | Drink water. Water first. | 水を飲め。まず水。 | Water instead of alcohol. Body loves it. 1 glass. Now. | アルコールの代わりに水。体が喜ぶ。コップ1杯、今すぐ。 |
| 4 | The bottle is not your friend. | ボトルは友達じゃない。 | Alcohol pretends to be a friend, but it takes more than it gives. It borrows happiness from tomorrow. Don't pay that price. | 酒は友達のふりをするが、与えるより奪う。明日から幸せを借りてる。その代償を払うな。 |
| 5 | The drink won't solve the problem. It will add another. | 酒は問題を解決しない。増やすだけ。 | Alcohol doesn't solve problems—it pauses them while creating new ones. The problem will still be there tomorrow, plus a hangover. | 酒は問題を解決しない—新しい問題を作りながら一時停止するだけ。問題は明日もある、二日酔いと一緒に。 |
| 6 | "Just today" is a lie. | 「今日だけ」は嘘。 | "Just today" you'll say tomorrow too. Stop today. Go get water. | 「今日だけ飲む」は明日も言う。今日やめろ。水を取りに行け。 |
| 7 | What are you really thirsty for? | 本当に渇いてるのは何？ | The craving isn't really for alcohol. It's for escape, comfort, or numbness. What do you really need right now? | 渇望は本当はアルコールへのものじゃない。逃避、安心、麻痺への渇望。本当に今必要なのは何？ |
| 8 | Every sober hour is a victory. | 素面の1時間は勝利。 | Every hour you stay sober is a win. Every day is a bigger win. You're winning right now. Keep going. | 素面でいる1時間は勝利。1日はもっと大きな勝利。今、勝ってる。続けろ。 |
| 9 | Remember the morning after. | 飲んだ翌朝を思い出せ。 | Regret, headache, fatigue. Choose that tonight? Choose clear tomorrow. | 後悔、頭痛、疲労。それを今夜選ぶのか？明日のスッキリを選べ。 |
| 10 | Tomorrow's hangover isn't worth tonight's drink. | 明日の二日酔いは今夜の酒に値しない。 | Imagine tomorrow morning. Headache, regret, shame. Is tonight's drink worth that? You know it isn't. | 明日の朝を想像して。頭痛、後悔、恥。今夜の酒はそれに値する？値しないってわかってるでしょ。 |
| 11 | Refuse the first drink. Second is easy. | 1杯目を断れ。2杯目は楽。 | First drink is hardest. Drink 1 glass of water first. Then decide. | 最初の1杯が一番難しい。水を1杯飲んでから決めろ。 |
| 12 | You're stronger than alcohol. | お前は酒より強い。 | Don't be controlled by alcohol. Take control. Put the glass down. | 酒に支配されるな。お前が主導権を握れ。グラスを置け。 |
| 13 | You're stronger than the craving. | 渇望より強い。 | This craving is a wave. It will peak and fall. You've survived 100% of your cravings so far. This one is no different. | この渇望は波。ピークが来て落ちる。今まで100%の渇望を生き延びてきた。これも同じ。 |
| 14 | Remember why you're not drinking. | 飲まない理由を思い出せ。 | Why do you want to cut back? Say the reason out loud. | なぜ減らしたいのか？その理由を声に出して言え。 |

※ Title: EN "Don't Drink Tonight" / JA "今夜は飲むな"

---

### 11. anger（怒り）— 14バリアント

| # | EN Notification Body | JA Notification Body | EN Card Detail | JA Card Detail |
|---|---------------------|----------------------|----------------|----------------|
| 1 | Pause. 3 seconds before you speak. | 一時停止。話す前に3秒。 | Before you react, count to 3. 1... 2... 3. In those 3 seconds, your rational brain can catch up to your emotional brain. | 反応する前に3まで数えて。1... 2... 3。その3秒で理性脳が感情脳に追いつける。 |
| 2 | What would the calm version of you do? | 冷静なあなたは何をする？ | There are two versions of you: angry-you and calm-you. Angry-you will regret what they say. Let calm-you respond. | あなたには2つのバージョンがある：怒りの自分と冷静な自分。怒りの自分は言ったことを後悔する。冷静な自分に反応させろ。 |
| 3 | Think from their perspective. | 相手の立場で考えろ。 | Why did they do it? Maybe there's a reason. Spend 1 minute in their shoes. | なぜそうしたのか？理由があるかもしれない。1分間、相手の視点で考えてみろ。 |
| 4 | Anger hurts you more than them. | 怒りは相手より自分を傷つける。 | Holding onto anger is like drinking poison and expecting the other person to die. Let it go for your own sake. | 怒りを抱えるのは毒を飲んで相手が死ぬのを期待するようなもの。自分のために手放せ。 |
| 5 | Anger is a secondary emotion. What's underneath? | 怒りは二次感情。下に何がある？ | Anger is usually a mask for hurt, fear, or frustration. What's really going on? Address that, not the anger. | 怒りは通常、傷、恐れ、フラストレーションの仮面。本当に何が起きてる？怒りではなくそれに対処しろ。 |
| 6 | Anger is poison. It eats you. | 怒りは毒。自分を蝕む。 | You want to hurt them, but you get hurt. 5 deep breaths. Let go. | 相手を傷つけたいのに、自分が傷つく。深呼吸を5回。手放せ。 |
| 7 | Is this worth your peace? | これ、心の平和に値する？ | Will this matter in 5 years? 5 months? 5 days? If not, it's not worth losing your peace over. Let it go. | これは5年後に重要？5ヶ月後？5日後？違うなら、心の平和を失う価値はない。手放せ。 |
| 8 | Walk away. Come back when you're ready. | 離れろ。準備ができたら戻れ。 | You don't have to respond right now. Walk away. Take a walk. Come back when you can think clearly. | 今すぐ反応する必要はない。離れろ。散歩しろ。明確に考えられるようになったら戻れ。 |
| 9 | Wait 6 seconds. Anger peaks at 6. | 6秒待て。怒りのピークは6秒。 | Brain calms after 6 seconds. Count 1 to 6. Now. | 6秒で脳の興奮が収まる。1から6まで数えろ。今すぐ。 |
| 10 | Breathe. The moment will pass. | 呼吸して。この瞬間は過ぎ去る。 | Inhale for 4 seconds. Hold for 4. Exhale for 4. Your nervous system will calm down. Then decide how to respond. | 4秒吸って。4秒止めて。4秒吐いて。神経系が落ち着く。それから反応を決めろ。 |
| 11 | Yelling won't improve anything. | 怒鳴っても状況は良くならない。 | Calm communication is more effective. 3 deep breaths before speaking. | 冷静に伝える方が、結果的に効果がある。3回深呼吸してから話せ。 |
| 12 | Is it worth being angry? | 怒る価値があるか？ | Is that worth your energy? Shrug and laugh. | そのことに怒るエネルギー、もったいなくないか？肩をすくめて笑え。 |
| 13 | Responding in anger? You'll regret it. | 怒りで反応する？後悔するよ。 | Words spoken in anger can never be unspoken. The relationship damage lasts longer than the anger. Wait. | 怒りで言った言葉は取り消せない。人間関係のダメージは怒りより長く続く。待て。 |
| 14 | Shut your mouth. Now. | 口を閉じろ。今すぐ。 | Don't speak in anger. Stay silent 10 seconds. Then speak calmly. | 怒りに任せて発言するな。10秒黙れ。その後、冷静に言い直せ。 |

※ Title: EN "Let Go of Anger" / JA "怒りを手放せ"

---

### 12. obsessive（考えすぎ）— 14バリアント

| # | EN Notification Body | JA Notification Body | EN Card Detail | JA Card Detail |
|---|---------------------|----------------------|----------------|----------------|
| 1 | The thought is not you. Let it pass. | その思考はあなたじゃない。通り過ぎさせて。 | Thoughts are just mental events. They come and go. You don't have to engage with them. Let this one pass like a cloud. | 思考はただのメンタルイベント。来て去る。関わる必要はない。雲のように通り過ぎさせて。 |
| 2 | The ritual won't save you. Breaking it will. | 儀式はあなたを救わない。破ることが救う。 | The compulsion promises relief but delivers more anxiety. Break the cycle by not performing the ritual. The discomfort will pass. | 強迫は安心を約束するがもっと不安をもたらす。儀式をしないことでサイクルを壊せ。不快感は過ぎ去る。 |
| 3 | Don't obsess details. See the whole. | 細部にこだわるな。全体を見ろ。 | Can't see forest for trees. Step back. Literally stand up from chair. | 木を見て森を見ず。一歩引いて全体を見ろ。椅子から立ち上がれ。 |
| 4 | You don't have to act on every thought. | 全ての思考に従う必要はない。 | You have thousands of thoughts a day. Not all of them deserve action. This one doesn't. Let it go. | 1日に何千もの思考がある。全てが行動に値するわけじゃない。これもそう。手放せ。 |
| 5 | Notice the urge. Don't follow it. | 衝動に気づいて。従うな。 | You feel the urge. Good—you noticed it. Now don't act on it. Just notice. The urge will peak and fade on its own. | 衝動を感じる。良い—気づいた。今、従うな。ただ気づいて。衝動は勝手にピークを迎えて消える。 |
| 6 | Say "this is fine". | 「これでいい」と言え。 | Give yourself permission. This is fine. Say it 3 times out loud. | 自分に許可を出せ。これでいい。声に出して3回言え。 |
| 7 | It's okay to leave it unfinished. | 未完成のままでいい。 | The anxiety of leaving something undone will pass. Give it 10 minutes. If you still feel the urge, reconsider. But wait first. | 何かを未完成にする不安は過ぎ去る。10分待って。まだ衝動を感じたら再考。でもまず待て。 |
| 8 | This discomfort is temporary. Sit with it. | この不快感は一時的。耐えろ。 | This uncomfortable feeling is temporary. It will pass whether you perform the ritual or not. Choose not to. Sit with the discomfort. | この不快な感覚は一時的。儀式をしてもしなくても過ぎ去る。しないことを選べ。不快感と共にいろ。 |
| 9 | Others don't notice that much. | 他人はそこまで見てない。 | That detail you worry about? Others don't notice. Laugh and move on. | お前が気にしてる細部、他人は気づかない。笑って次へ行け。 |
| 10 | Perfection is the enemy of peace. | 完璧は平和の敵。 | Chasing perfection creates anxiety. 'Good enough' creates peace. This is good enough. Move on. | 完璧を追うと不安が生まれる。「十分」は平和を作る。これで十分。先に進め。 |
| 11 | Perfection doesn't exist. | 完璧は存在しない。 | Chasing perfection never ends. Say out loud "this is enough". | 完璧を追い求めても終わりがない。「これで十分」と声に出して言え。 |
| 12 | Set a time limit. | 時間制限を設けろ。 | Don't assume infinite time. 30-min timer. Force quit when done. | 無限に時間があると思うな。30分タイマー。終わったら強制終了。 |
| 13 | One check is enough. Trust yourself. | 1回の確認で十分。自分を信じろ。 | You checked. It's done. Checking again won't make it more done. Trust the first check. Move on. | 確認した。終わった。もう一度確認してももっと終わったことにはならない。最初の確認を信じろ。先に進め。 |
| 14 | Ship at 80%. Fix 20% later. | 80%で出せ。残り20%は後で。 | Waiting for perfect = never shipping. Set 30-min timer. Stop there. | 完璧を待ってたら永遠に出せない。タイマーを30分セット。そこで止めろ。 |

※ Title: EN "Stop Overthinking" / JA "考えすぎ"

---

### 13. loneliness（孤独）— 14バリアント

| # | EN Notification Body | JA Notification Body | EN Card Detail | JA Card Detail |
|---|---------------------|----------------------|----------------|----------------|
| 1 | You're not alone in feeling alone. | 孤独を感じてるのはあなただけじゃない。 | Millions of people feel lonely right now. You're not alone in feeling alone. This feeling is human, and it will pass. | 何百万人が今孤独を感じてる。孤独を感じてるのはあなただけじゃない。この感覚は人間的で、過ぎ去る。 |
| 2 | Being alone is not the same as being lonely. | 一人でいることと孤独は違う。 | You can be alone without being lonely. And you can be lonely in a crowd. The key is quality of connection, not quantity. | 一人でも寂しくないことがある。群衆の中でも孤独になれる。鍵はつながりの質、量じゃない。 |
| 3 | Start with small connections. | 小さなつながりから始めろ。 | No need for deep bonds right away. Start with "thank you" to a store clerk. | いきなり深い関係じゃなくていい。店員に「ありがとう」と言うことから。 |
| 4 | Reach out to one person today. | 今日、誰か一人に連絡して。 | Connection doesn't require a deep conversation. Just reach out to one person today. A simple "thinking of you" can change both your days. | つながりに深い会話は必要ない。今日、誰か一人に連絡するだけ。「考えてた」の一言で両方の1日が変わる。 |
| 5 | Your presence matters to someone. | あなたの存在は誰かにとって大事。 | Someone out there is glad you exist. Maybe they haven't told you recently, but you matter to someone. You always do. | 誰かがあなたの存在を喜んでる。最近言われてないかもしれないけど、あなたは誰かにとって大事。いつもそう。 |
| 6 | You're not alone. It just feels that way. | 一人じゃない。そう感じるだけ。 | Loneliness is a feeling, not a fact. Text 1 person "how are you?" today. | 孤独は感情。事実じゃない。今日1人に「元気？」と送れ。 |
| 7 | Solitude can be peaceful. Loneliness doesn't have to be permanent. | 孤独は穏やかになれる。寂しさは永遠じゃない。 | Solitude is being alone and content. Loneliness is being alone and craving connection. You can transform loneliness into peaceful solitude. | 孤独は一人で満足してること。寂しさは一人でつながりを渇望してること。寂しさを穏やかな孤独に変えられる。 |
| 8 | Go outside. Smile at a stranger. | 外に出て。見知らぬ人に微笑んで。 | A small interaction can shift your whole mood. Go outside. Smile at a stranger. Say hi to a neighbor. Connection is everywhere. | 小さな交流が気分全体を変える。外に出て。見知らぬ人に微笑んで。隣人にこんにちはと言って。つながりはどこにでもある。 |
| 9 | Go outside. Where people are. | 外に出ろ。人がいる場所へ。 | Cafe works. Convenience store works. Feel human presence. Go out now. | カフェでいい。コンビニでいい。人の気配を感じろ。今すぐ外出。 |
| 10 | Text someone. Even just "hey". | 誰かにメッセージ。「やあ」だけでも。 | Send a message to someone you haven't talked to in a while. Just "hey, thinking of you." Most people are happy to hear from you. | しばらく話してない人にメッセージを送って。「やあ、考えてた」だけ。ほとんどの人は連絡をもらって嬉しい。 |
| 11 | Contact someone. Now. | 誰かに連絡しろ。今すぐ。 | Text is fine. "How are you?" is enough. Send it now. | LINEでいい。「元気？」だけでいい。今すぐ送れ。 |
| 12 | Listen to someone. | 誰かの話を聞け。 | Instead of talking, listen. That's connection. Ask someone "how's it going?" today. | 自分の話をするより、誰かの話を聞く。それがつながり。今日誰かに「最近どう？」と聞け。 |
| 13 | Connection starts with one small step. | つながりは小さな一歩から。 | You don't need to find your soulmate today. Just one small connection. A smile, a text, a call. Start small. | 今日ソウルメイトを見つける必要はない。小さなつながり一つだけ。微笑み、メッセージ、電話。小さく始めろ。 |
| 14 | Get out of your room. | 部屋から出ろ。 | When lonely, move. Put on shoes. Go outside. Now. | 孤独を感じたら動け。靴を履いて外に出ろ。今すぐ。 |

※ Title: EN "Reach Out" / JA "つながろう"

---

## 運用ルール

- このドキュメントは **常時更新** する。カタログや文言を変更したら必ずここも更新する。
- **全 13 ProblemType** の Notification Body と Card Detail は、このファイルで EN/JA 完全一覧を管理する（ユニークペアのみ。カタログの重複は省く）。

---

最終更新: 2026-02-17
