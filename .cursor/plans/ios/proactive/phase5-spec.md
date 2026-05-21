# Phase 5: Thompson Sampling + バリアント拡充 仕様書

> **バージョン**: 1.2.0
>
> **最終更新**: 2026-01-21
>
> **目的**: 固定ルールベースのバリアント選択をThompson Samplingに置き換え、バリアントを拡充してLLMの学習データを準備する

---

## 目次

1. [概要](#1-概要)
2. [タスクリスト](#2-タスクリスト)
3. [バリアント拡充](#3-バリアント拡充)
4. [BetaDistribution実装](#4-betadistribution実装)
5. [NudgeContentSelector変更](#5-nudgecontentselector変更)
6. [タイミング最適化改善](#6-タイミング最適化改善)
7. [全くタップしない人への対処](#7-全くタップしない人への対処)
8. [デバッグメニュー](#8-デバッグメニュー)
9. [テスト手順](#9-テスト手順)
10. [Phase 6 詳細](#10-phase-6-詳細)
11. [Phase 7 詳細](#11-phase-7-詳細)
12. [哲学](#12-哲学)

---

## 1. 概要

### 1.1 背景

Phase 4で実装した固定ルールベースの選択（80%活用/20%探索）には以下の問題がある：

| 問題 | 説明 |
|------|------|
| 固定比率 | データ量に関係なく同じ探索率（20%） |
| 非効率な探索 | 明らかに効果が低いバリアントにも20%の確率で選ばれる |
| 確信度無視 | データが少ないバリアントと多いバリアントを同等に扱う |
| バリアント不足 | 各問題に3個程度しかない。多様性が足りない |

### 1.2 解決策

1. **Thompson Sampling**: 確信度ベースの選択アルゴリズム
2. **バリアント拡充**: 各問題に8-10個のバリアント（英語・日本語）
3. **タイミング最適化改善**: 15分判定、30分単位、最大シフト2時間
4. **全くタップしない人への対処**: タイミングシフトではなくバリアントを変える

### 1.3 ユーザーの問題をどう解決するか

| 問題 | 解決策 |
|------|--------|
| 「この人に刺さる言葉」が見つからない | 8-10個のバリアントで多様性を確保 |
| 効果が低いバリアントが選ばれ続ける | Thompson Samplingで自動的に避ける |
| データが少ないのに決めつける | 確信度が低いときは探索を増やす |
| 全くタップしない人が放置される | バリアントを変えて試す |

---

## 2. タスクリスト

| # | タスク | 担当 | 状態 |
|---|--------|------|------|
| 1 | 1.1.0をApp Storeに提出 | ユーザー | 未着手 |
| 2 | バリアント拡充（Localizable.strings） | AI | 未着手 |
| 3 | BetaDistribution.swift作成 | AI | 未着手 |
| 4 | NudgeContentSelector.swiftをTS対応に変更 | AI | 未着手 |
| 5 | NudgeStatsManager.swiftのタイミング最適化改善 | AI | 未着手 |
| 6 | 全くタップしない人への対処実装 | AI | 未着手 |
| 7 | デバッグメニュー追加 | AI | 未着手 |
| 8 | 単体テスト作成 | AI | 未着手 |
| 9 | ビルド確認 | AI | 未着手 |
| 10 | 実機テスト | ユーザー | 未着手 |

---

## 3. バリアント拡充

### 3.1 staying_up_late（夜更かし）

| # | English | 日本語 | トーン |
|---|---------|--------|--------|
| 1 | Breathe, don't scroll. | スクロールより、呼吸。 | gentle |
| 2 | How many years lost to 'just 5 more minutes'? | 「あと5分」で何年失った？ | provocative |
| 3 | Tomorrow's you will regret this. | 明日の自分、泣くよ。 | strict |
| 4 | It's past midnight. Your body needs rest now. | 深夜0時を過ぎました。体を休めて。 | gentle |
| 5 | It's 1 AM. Every minute awake costs you tomorrow. | 深夜1時です。起きてる1分が明日を削る。 | strict |
| 6 | Put down your phone. Now. | スマホを置いて。今すぐ。 | strict |
| 7 | Your future self is watching. What do they see? | 未来の自分が見てる。何が見える？ | questioning |
| 8 | Sleep is not optional. It's medicine. | 睡眠は贅沢じゃない。薬だ。 | logical |
| 9 | The screen can wait. Your dreams can't. | 画面は待てる。夢は待てない。 | gentle |
| 10 | Every hour of sleep = better decisions tomorrow. | 睡眠1時間 = 明日の判断力向上。 | logical |

**Content（detail）**:

| # | English | 日本語 |
|---|---------|--------|
| 1 | Move your phone 30cm from your face. Turn brightness to minimum. Take 5 deep breaths. Your brain will switch to 'sleep prep' mode. | スマホを顔から30cm離して。明るさを最低に。深呼吸5回。脳が「睡眠準備モード」に切り替わる。 |
| 2 | A sleep-deprived brain has the same judgment as 0.1% blood alcohol. 17 hours awake = legally drunk. Protect tomorrow's decisions by sleeping tonight. | 睡眠不足の脳は血中アルコール0.1%と同じ判断力。17時間起きてる = 法的に酔っ払い。今夜寝て明日の判断を守れ。 |
| 3 | Will you remember this content tomorrow at noon? But sleep deprivation will definitely hurt your focus, judgment, and immunity. Which matters more? | 明日の昼、この内容を覚えてる？でも睡眠不足は確実に集中力、判断力、免疫力を傷つける。どっちが大事？ |
| 4 | Sleep deprivation compounds like debt. Tonight's lost hour will steal next week's focus and judgment. Move your phone away from bed. Close your eyes. | 睡眠不足は借金のように複利で増える。今夜の1時間が来週の集中力と判断力を奪う。スマホをベッドから離して。目を閉じて。 |
| 5 | Staying awake past 1 AM causes measurable damage to your brain and heart. What you're doing is 100x less important than sleep. Go to bed now. | 深夜1時以降の覚醒は脳と心臓に測定可能なダメージを与える。今やってることは睡眠の100分の1も大事じゃない。今すぐ寝ろ。 |
| 6 | Your willpower is at its lowest right now. Don't fight the urge to scroll—just remove the phone. Put it in another room. | 今、意志力は最低レベル。スクロール衝動と戦うな—スマホを消せ。別の部屋に置け。 |
| 7 | Imagine waking up refreshed vs. waking up exhausted. Which version of tomorrow do you want? You decide right now. | すっきり起きる明日と、疲れ切って起きる明日。どっちがいい？今決まる。 |
| 8 | Sleep repairs your brain, consolidates memories, and resets emotions. Skipping it is like skipping maintenance on a car you drive daily. | 睡眠は脳を修復し、記憶を定着させ、感情をリセットする。サボるのは毎日乗る車のメンテをサボるのと同じ。 |
| 9 | The blue light is telling your brain it's noon. Your body is confused. Help it by putting the screen away. | ブルーライトが脳に「今は昼だ」と伝えてる。体が混乱してる。画面を消して助けてあげて。 |
| 10 | One hour of sleep tonight = 3 hours of productivity tomorrow. The math is simple. Go to bed. | 今夜の睡眠1時間 = 明日の生産性3時間。計算は簡単。寝ろ。 |

---

### 3.2 cant_wake_up（起きられない）

| # | English | 日本語 | トーン |
|---|---------|--------|--------|
| 1 | Your day won't start until you get up. | 起きるまで1日は始まらない。 | logical |
| 2 | The 'just 5 more minutes' you has zero credibility. | 「あと5分」の自分、信用ゼロ。 | provocative |
| 3 | Stay Mediocre | 凡人のままでいろ | provocative |
| 4 | Feet on the floor. 5, 4, 3, 2, 1. | 足を床に。5、4、3、2、1。 | strict |
| 5 | The blanket is lying to you. | 布団は嘘をついてる。 | questioning |
| 6 | Your alarm is a promise. Keep it. | アラームは約束。守れ。 | strict |
| 7 | Morning wins build confidence. | 朝の勝利が自信を作る。 | logical |
| 8 | Get up now, or regret it at noon. | 今起きろ。昼に後悔するぞ。 | strict |

**Content（detail）**:

| # | English | 日本語 |
|---|---------|--------|
| 1 | Count 5, 4, 3, 2, 1 and put your feet on the floor. Move before you think. Get up before your brain makes excuses. Nothing changes under the blanket. | 5、4、3、2、1と数えて足を床に。考える前に動け。脳が言い訳する前に起きろ。布団の中では何も変わらない。 |
| 2 | How many times have you trusted the '5 more minutes' you? How many times were you betrayed? Getting up now keeps a promise to yourself. You'll like today's you. | 「あと5分」の自分を何回信じた？何回裏切られた？今起きれば自分との約束を守れる。今日の自分を好きになれる。 |
| 3 | Start today sloppy again? Or change starting now? Your action in the next 5 seconds decides. Stand up. | また今日もダラダラ始める？それとも今から変わる？次の5秒の行動が決める。立て。 |
| 4 | Your body is awake. Your mind is making excuses. Override it. Feet on the floor. Now. | 体は起きてる。脳が言い訳してるだけ。上書きしろ。足を床に。今すぐ。 |
| 5 | The blanket feels safe, but it's a trap. Comfort now = regret later. Rip off the blanket like a bandaid. | 布団は安全に感じる。でも罠だ。今の快適 = 後の後悔。絆創膏を剥がすように布団を剥がせ。 |
| 6 | Every morning you hit snooze, you break a promise to yourself. Small betrayals compound. Start today with integrity. | スヌーズを押すたびに自分との約束を破ってる。小さな裏切りは複利で増える。今日は誠実に始めろ。 |
| 7 | People who win mornings win days. People who win days win weeks. It starts with getting up when you said you would. | 朝を制する者は1日を制する。1日を制する者は1週間を制する。全ては決めた時間に起きることから始まる。 |
| 8 | Noon-you will be grateful. Evening-you will be proud. But only if morning-you gets up now. | 昼の自分は感謝する。夜の自分は誇りに思う。でも朝の自分が今起きた場合だけ。 |

---

### 3.3 self_loathing（自己嫌悪）

| # | English | 日本語 | トーン |
|---|---------|--------|--------|
| 1 | You're alive today. That's enough. | 今日も生きてる。それで十分。 | gentle |
| 2 | It's okay to stop blaming yourself. | 自分を責めるのをやめていい。 | gentle |
| 3 | You're a much better person than you think. | あなたは思ってるより良い人。 | gentle |
| 4 | Self-criticism won't make you better. Compassion will. | 自己批判は成長させない。自己慈悲が成長させる。 | logical |
| 5 | Would you say this to a friend? Then don't say it to yourself. | 友達にそれ言う？なら自分にも言うな。 | questioning |
| 6 | You're trying. That's what matters. | 頑張ってる。それが大事。 | gentle |
| 7 | Your worth isn't measured by productivity. | あなたの価値は生産性で測れない。 | logical |
| 8 | Be kind to yourself. Just for today. | 自分に優しく。今日だけでいい。 | gentle |

**Content（detail）**:

| # | English | 日本語 |
|---|---------|--------|
| 1 | Self-loathing proves you want to be better. But self-criticism doesn't lead to growth—it backfires. You woke up today. That's enough. | 自己嫌悪は良くなりたい証拠。でも自己批判は成長につながらない—逆効果。今日起きた。それで十分。 |
| 2 | If your best friend was in your situation, what would you say? You wouldn't say 'You're worthless.' Give yourself the same kindness. | 親友が同じ状況だったら何て言う？「お前は価値がない」とは言わないでしょ。自分にも同じ優しさを。 |
| 3 | Is what you're blaming yourself for truly 'irreparable'? Most things are smaller than they feel. Take a deep breath and look objectively. | 自分を責めてること、本当に「取り返しがつかない」？ほとんどのことは感じてるより小さい。深呼吸して客観的に見て。 |
| 4 | Research shows self-compassion leads to more growth than self-criticism. Being harsh on yourself doesn't work. Try kindness instead. | 研究によると、自己慈悲の方が自己批判より成長につながる。自分に厳しくしても効果がない。優しさを試して。 |
| 5 | You wouldn't let anyone else talk to your friend this way. Why do you let yourself talk to you this way? Protect yourself like you'd protect a friend. | 友達に誰かがこう言ったら許さないでしょ。なぜ自分には許すの？友達を守るように自分を守って。 |
| 6 | Progress isn't linear. Bad days don't erase good days. You're trying, and that's more than most people do. | 進歩は直線じゃない。悪い日は良い日を消さない。頑張ってる、それは多くの人がやらないこと。 |
| 7 | You are not your productivity. You are not your achievements. You are worthy of love and rest just by existing. | あなたは生産性じゃない。あなたは実績じゃない。存在するだけで愛と休息に値する。 |
| 8 | Just for today, speak to yourself like you'd speak to someone you love. Just for today. Tomorrow you can go back to being hard on yourself if you want. | 今日だけ、愛する人に話すように自分に話して。今日だけ。明日また厳しくしていいから。 |

---

### 3.4 rumination（反芻思考）

| # | English | 日本語 | トーン |
|---|---------|--------|--------|
| 1 | What are you feeling right now? | 今、何を感じてる？ | questioning |
| 2 | Are you present right now? | 今、ここにいる？ | questioning |
| 3 | Why not meditate for 5 minutes? | 5分、瞑想してみない？ | gentle |
| 4 | The loop is a trap. Step out. | そのループは罠。抜け出せ。 | strict |
| 5 | Notice your feet. Feel the floor. You're here. | 足の裏を感じて。床を感じて。ここにいる。 | gentle |
| 6 | Thinking about it won't change it. | 考えても変わらない。 | logical |
| 7 | Name 5 things you see. Start now. | 見えるもの5つ言って。今すぐ。 | gentle |
| 8 | Your thoughts are not facts. | 思考は事実じゃない。 | logical |

**Content（detail）**:

| # | English | 日本語 |
|---|---------|--------|
| 1 | Once you notice the loop, you're halfway done. Now: focus on the soles of your feet. The floor's hardness, temperature. Just 30 seconds. | ループに気づいた時点で半分終わり。今：足の裏に集中。床の硬さ、温度。30秒だけ。 |
| 2 | Name 5 things you see, 4 you hear, 3 you're touching, 2 you smell, 1 you taste. This forces you back to 'now.' | 見えるもの5つ、聞こえるもの4つ、触れてるもの3つ、匂い2つ、味1つ。これで「今」に戻れる。 |
| 3 | The most effective way to stop rumination is meditation. For 2 minutes now, focus only on breathing. Inhale 4 sec, hold 4 sec, exhale 4 sec. | 反芻を止める最も効果的な方法は瞑想。今から2分、呼吸だけに集中。4秒吸って、4秒止めて、4秒吐いて。 |
| 4 | You've been in this loop before. It never solved anything. The only way out is to do something physical. Stand up. Move. | このループは前にもあった。何も解決しなかった。唯一の出口は体を動かすこと。立って。動いて。 |
| 5 | Your feet are on the ground. Your lungs are breathing. You are here, in this moment, safe. The past is gone. The future isn't here yet. | 足は地面についてる。肺は呼吸してる。あなたは今ここにいて、安全。過去は終わった。未来はまだ来てない。 |
| 6 | Rumination is your brain trying to solve an unsolvable problem. It can't be solved by thinking. Accept that, and let it go. | 反芻は脳が解決不能な問題を解こうとしてる。考えても解決しない。それを受け入れて、手放して。 |
| 7 | Look around you. Name what you see. "Chair. Window. Light. Book." This simple act pulls you out of your head and into reality. | 周りを見て。見えるものを言って。「椅子。窓。光。本。」この単純な行為が頭の中から現実に引き戻す。 |
| 8 | Thoughts are like clouds. They pass. You don't have to grab them, analyze them, or follow them. Just watch them go. | 思考は雲のようなもの。過ぎていく。つかまなくていい、分析しなくていい、追わなくていい。見送るだけ。 |

---

### 3.5 procrastination（先延ばし）

| # | English | 日本語 | トーン |
|---|---------|--------|--------|
| 1 | Just 5 minutes. That's all you need. | たった5分。それだけでいい。 | gentle |
| 2 | Breaking another promise to yourself? | また自分との約束破る？ | provocative |
| 3 | Every reason not to do it is an excuse. | やらない理由は全部言い訳。 | strict |
| 4 | Start ugly. Refine later. | 汚くても始めろ。後で直せ。 | logical |
| 5 | The hardest part is the first 2 minutes. | 一番難しいのは最初の2分。 | logical |
| 6 | What would you tell a friend who keeps delaying? | 先延ばしする友達に何て言う？ | questioning |
| 7 | Done is better than perfect. | 完璧より完了。 | logical |
| 8 | Future you is counting on present you. | 未来の自分は今の自分を頼りにしてる。 | gentle |

**Content（detail）**:

| # | English | 日本語 |
|---|---------|--------|
| 1 | If it takes under 2 minutes, do it now. If it takes longer, just do the first 2 minutes. Once you start, your brain wants to continue. That's science. | 2分以内なら今やれ。それ以上なら最初の2分だけやれ。始めれば脳は続けたくなる。科学的事実。 |
| 2 | Imagine yourself a week from now. 'I wish I'd done it then...' Regretting? Do it now and that regret disappears. | 1週間後の自分を想像して。「あの時やっておけば…」後悔してる？今やればその後悔は消える。 |
| 3 | 'Can't do it' and 'don't want to' are different. Which is it right now? If you don't want to, why? Find the real reason. | 「できない」と「やりたくない」は違う。今どっち？やりたくないなら、なぜ？本当の理由を見つけて。 |
| 4 | Perfectionism is procrastination in disguise. A messy start is infinitely better than no start. Write one bad sentence. Take one ugly step. | 完璧主義は先延ばしの変装。汚いスタートはスタートしないより無限に良い。下手な一文を書け。醜い一歩を踏め。 |
| 5 | Your brain hates starting. But once you're 2 minutes in, momentum takes over. Just survive the first 2 minutes. | 脳は始めるのが嫌い。でも2分経てば勢いがつく。最初の2分だけ生き延びろ。 |
| 6 | If your friend kept delaying something important, you'd tell them to just start. Be that friend to yourself right now. | 友達が大事なことを先延ばしし続けたら、「とにかく始めろ」と言うでしょ。今、自分にその友達になれ。 |
| 7 | Shipped is better than perfect. A finished project with flaws beats an unfinished 'masterpiece' every time. | 出荷が完璧に勝る。欠陥のある完成品は未完成の「傑作」にいつも勝つ。 |
| 8 | Future you is watching. They're either grateful you started now, or frustrated you didn't. Make future you grateful. | 未来の自分が見てる。今始めたことに感謝するか、始めなかったことにイラつくか。未来の自分を感謝させろ。 |

---

### 3.6 anxiety（不安）

| # | English | 日本語 | トーン |
|---|---------|--------|--------|
| 1 | In this moment, you are safe. | この瞬間、あなたは安全。 | gentle |
| 2 | What are you feeling right now? | 今、何を感じてる？ | questioning |
| 3 | Deep breath. Inhale 4, hold 4, exhale 4. | 深呼吸。4秒吸って、4秒止めて、4秒吐いて。 | gentle |
| 4 | Anxiety lies. Right now, you are okay. | 不安は嘘をつく。今、あなたは大丈夫。 | logical |
| 5 | Feel your feet. You're grounded. | 足の裏を感じて。地に足がついてる。 | gentle |
| 6 | This feeling will pass. It always does. | この感覚は過ぎ去る。いつもそう。 | gentle |
| 7 | Name it to tame it. What's the fear? | 名前をつけて手なずけろ。何が怖い？ | questioning |
| 8 | You've survived 100% of your worst days. | 最悪の日を100%生き延びてきた。 | logical |

**Content（detail）**:

| # | English | 日本語 |
|---|---------|--------|
| 1 | Anxiety is fear of what hasn't happened yet. Right now, what's actually happening in front of you? Nothing dangerous is occurring. | 不安はまだ起きてないことへの恐れ。今、目の前で実際に何が起きてる？危険なことは何も起きてない。 |
| 2 | Not 'I am anxious' but 'I am feeling anxiety.' Anxiety is like weather. It comes, and it goes. | 「不安だ」じゃなく「不安を感じてる」。不安は天気のようなもの。来て、去る。 |
| 3 | Inhale 4 sec → hold 4 sec → exhale 4 sec → hold 4 sec. Repeat 3 times. When your body calms, your mind follows. Do it now. | 4秒吸って → 4秒止めて → 4秒吐いて → 4秒止めて。3回繰り返して。体が落ち着けば、心もついてくる。今やって。 |
| 4 | Your brain is trying to protect you from a threat that isn't here. Thank it, then tell it: "I'm safe right now." | 脳はここにない脅威からあなたを守ろうとしてる。感謝して、こう言って：「今、私は安全」。 |
| 5 | Press your feet firmly into the floor. Feel the ground holding you up. You are supported. You are here. You are safe. | 足を床にしっかり押し付けて。地面があなたを支えてるのを感じて。あなたは支えられてる。ここにいる。安全だ。 |
| 6 | This feeling has a beginning, a middle, and an end. You're somewhere in the middle. The end is coming. Wait for it. | この感覚には始まり、中間、終わりがある。あなたは中間のどこか。終わりは来る。待って。 |
| 7 | What exactly are you afraid of? Say it out loud. "I'm afraid that..." Naming the fear takes away some of its power. | 具体的に何が怖い？声に出して言って。「私が怖いのは…」恐れに名前をつけると力が弱まる。 |
| 8 | Your track record for surviving bad days is 100%. Whatever this is, you'll get through it too. | 悪い日を生き延びた実績は100%。これが何であれ、乗り越えられる。 |

---

### 3.7 lying（嘘）

| # | English | 日本語 | トーン |
|---|---------|--------|--------|
| 1 | Today is a day to live honestly. | 今日は正直に生きる日。 | gentle |
| 2 | One truth builds more trust than ten lies. | 1つの真実は10の嘘より信頼を築く。 | logical |
| 3 | The truth is lighter to carry. | 真実の方が軽い。 | gentle |
| 4 | Lies compound. Truth simplifies. | 嘘は複利で増える。真実は単純にする。 | logical |
| 5 | What would happen if you just told the truth? | もし真実を言ったらどうなる？ | questioning |
| 6 | Honesty is exhausting. But lies are more exhausting. | 正直は疲れる。でも嘘はもっと疲れる。 | logical |
| 7 | Your word is your bond. Protect it. | 言葉は絆。守れ。 | strict |
| 8 | Small lies grow into big ones. Stop now. | 小さな嘘は大きくなる。今やめろ。 | strict |

**Content（detail）**:

| # | English | 日本語 |
|---|---------|--------|
| 1 | Small lies lead to big lies. One lie requires another lie to protect it. Being honest today makes tomorrow simpler. | 小さな嘘は大きな嘘につながる。1つの嘘を守るために別の嘘が必要。今日正直にすれば明日が単純になる。 |
| 2 | Trust is built in drops and lost in buckets. Every lie chips away at it. Every truth adds a drop. | 信頼は一滴ずつ築かれ、バケツで失われる。嘘のたびに削られる。真実のたびに一滴増える。 |
| 3 | Carrying a lie is heavy. You have to remember it, maintain it, worry about it. The truth requires no maintenance. | 嘘を抱えるのは重い。覚えて、維持して、心配して。真実はメンテナンス不要。 |
| 4 | One lie needs another to cover it. Then another. The web grows. Simplify your life: tell the truth. | 1つの嘘を隠すのに別の嘘が必要。また別の。網は広がる。人生を単純に：真実を言え。 |
| 5 | Most of the time, the truth isn't as scary as we think. People respect honesty more than perfection. Try it. | ほとんどの場合、真実は思ってるほど怖くない。人は完璧より正直を尊敬する。試してみて。 |
| 6 | Lying takes mental energy. Remembering lies, maintaining them, worrying about exposure. Honesty is actually easier. | 嘘はメンタルエネルギーを消費する。嘘を覚えて、維持して、バレる心配して。正直の方が実は楽。 |
| 7 | When you say something, mean it. When you promise, deliver. Your word should be unbreakable. Start today. | 何かを言うなら本気で。約束したら果たせ。あなたの言葉は不可侵であるべき。今日から始めろ。 |
| 8 | Every small lie makes the next one easier. Break the pattern now before it becomes who you are. | 小さな嘘のたびに次が簡単になる。それがあなたになる前に今パターンを壊せ。 |

---

### 3.8 bad_mouthing（悪口）

| # | English | 日本語 | トーン |
|---|---------|--------|--------|
| 1 | No hurtful words today. | 今日は傷つける言葉を言わない。 | gentle |
| 2 | How would you feel if someone said that to you? | 誰かにそれ言われたらどう思う？ | questioning |
| 3 | Gossip hurts you more than them. | 悪口は相手より自分を傷つける。 | logical |
| 4 | Speak about others as if they're listening. | 相手が聞いてるつもりで話せ。 | gentle |
| 5 | Kindness is strength. Gossip is weakness. | 優しさは強さ。悪口は弱さ。 | logical |
| 6 | What you say about others says more about you. | 他人の悪口は自分を語る。 | logical |
| 7 | 5 minutes of gossip, 5 hours of regret. | 5分の悪口、5時間の後悔。 | strict |
| 8 | Would you want your kids to hear this? | 子供に聞かせたい？ | questioning |

**Content（detail）**:

| # | English | 日本語 |
|---|---------|--------|
| 1 | Words can't be unspoken. Before you say something about someone, ask: is it true? Is it kind? Is it necessary? | 言葉は取り消せない。誰かについて言う前に聞いて：それは本当？優しい？必要？ |
| 2 | Imagine those words being said about you, in a room you just walked into. That's how it feels. Don't do it. | その言葉があなたについて言われてると想像して、あなたが入ったばかりの部屋で。そういう気持ち。やめて。 |
| 3 | Talking badly feels good for a moment. But 5 minutes later, self-loathing arrives. Plus, listeners think 'they'll talk about me too.' | 悪口は一瞬気持ちいい。でも5分後に自己嫌悪が来る。しかも聞いてる人は「私のことも言うだろう」と思う。 |
| 4 | If they were standing right behind you, would you say it? If not, don't say it at all. Speak as if everyone can hear. | 相手がすぐ後ろに立ってたら言う？言わないなら、全く言うな。みんなが聞こえるつもりで話せ。 |
| 5 | Strong people don't need to put others down. Gossip is a sign of insecurity. Rise above it. | 強い人は他人を落とす必要がない。悪口は不安の表れ。超えろ。 |
| 6 | When you talk negatively about others, people wonder what you say about them. It damages your reputation more than theirs. | 他人の悪口を言うと、人はあなたが自分のことも言うか疑問に思う。相手より自分の評判が傷つく。 |
| 7 | That temporary feeling of superiority isn't worth the guilt that follows. And it always follows. | 一時的な優越感は後に来る罪悪感に値しない。そして必ず来る。 |
| 8 | If your children heard you right now, would you be proud? Let that guide your words. | 今、子供が聞いてたら誇りに思う？それで言葉を導いて。 |

---

### 3.9 porn_addiction（ポルノ依存）

| # | English | 日本語 | トーン |
|---|---------|--------|--------|
| 1 | Beat the temptation. Tomorrow's you will change. | 誘惑に勝て。明日の自分が変わる。 | gentle |
| 2 | Do you really want it? Or are you just escaping? | 本当に欲しい？逃げてるだけ？ | questioning |
| 3 | The urge is a wave. It will pass in 10 minutes. | 衝動は波。10分で過ぎ去る。 | logical |
| 4 | What are you really running from? | 本当は何から逃げてる？ | questioning |
| 5 | Your brain is lying. You don't need it. | 脳が嘘をついてる。必要ない。 | logical |
| 6 | 10 push-ups. Now. Redirect the energy. | 腕立て10回。今すぐ。エネルギーを変えろ。 | strict |
| 7 | Cold water on your face. Break the pattern. | 冷水を顔に。パターンを壊せ。 | strict |
| 8 | This moment of weakness doesn't define you. | この弱さの瞬間はあなたを定義しない。 | gentle |

**Content（detail）**:

| # | English | 日本語 |
|---|---------|--------|
| 1 | The urge is like a wave—it peaks and falls. Do something else for 10 minutes. Walk, push-ups, splash cold water on your face. | 衝動は波のようなもの—ピークが来て落ちる。10分間別のことをして。歩く、腕立て、冷水を顔にかける。 |
| 2 | When you want to escape to porn, what are you really running from? Stress? Loneliness? Boredom? Find the root cause. | ポルノに逃げたいとき、本当は何から逃げてる？ストレス？孤独？退屈？根本原因を見つけて。 |
| 3 | Urges peak at about 10 minutes and then decline. You just need to survive 10 minutes. Set a timer. Do anything else. | 衝動は約10分でピークに達し、その後減少する。10分生き延びればいい。タイマーをセット。他のことをして。 |
| 4 | Porn is a numbing agent. What pain are you trying to numb? Address the pain, and the need for numbing decreases. | ポルノは麻酔剤。何の痛みを麻痺させようとしてる？痛みに対処すれば、麻痺の必要性が減る。 |
| 5 | Your brain is releasing dopamine in anticipation. It's a chemical trick. You don't actually need it. The craving is a lie. | 脳は期待してドーパミンを放出してる。化学的なトリック。実際には必要ない。渇望は嘘。 |
| 6 | Physical action breaks the mental loop. Right now: 10 push-ups, 10 squats, or 10 jumping jacks. Move your body. | 身体的行動がメンタルのループを壊す。今すぐ：腕立て10回、スクワット10回、またはジャンピングジャック10回。体を動かせ。 |
| 7 | Cold water shocks your system and resets your brain. Go to the bathroom, splash cold water on your face. It works. | 冷水はシステムにショックを与え、脳をリセットする。洗面所に行って、冷水を顔にかけて。効く。 |
| 8 | You are not your urges. This moment of weakness is temporary. The person you want to be is still there. Choose that person now. | あなたは衝動じゃない。この弱さの瞬間は一時的。なりたい人はまだそこにいる。今、その人を選べ。 |

---

### 3.10 alcohol_dependency（アルコール依存）

| # | English | 日本語 | トーン |
|---|---------|--------|--------|
| 1 | One day at a time. You can do this. | 1日ずつ。できる。 | gentle |
| 2 | The bottle is not your friend. | ボトルは友達じゃない。 | logical |
| 3 | What are you really thirsty for? | 本当に渇いてるのは何？ | questioning |
| 4 | Tomorrow's hangover isn't worth tonight's drink. | 明日の二日酔いは今夜の酒に値しない。 | logical |
| 5 | You're stronger than the craving. | 渇望より強い。 | gentle |
| 6 | Call someone instead. Anyone. | 代わりに誰かに電話して。誰でもいい。 | gentle |
| 7 | The drink won't solve the problem. It will add another. | 酒は問題を解決しない。増やすだけ。 | logical |
| 8 | Every sober hour is a victory. | 素面の1時間は勝利。 | gentle |

**Content（detail）**:

| # | English | 日本語 |
|---|---------|--------|
| 1 | Don't think about forever. Just today. Just this hour. Just this moment. One day at a time is how every recovery starts. | 永遠のことは考えるな。今日だけ。この1時間だけ。この瞬間だけ。1日ずつ—全ての回復はそうやって始まる。 |
| 2 | Alcohol pretends to be a friend, but it takes more than it gives. It borrows happiness from tomorrow. Don't pay that price. | 酒は友達のふりをするが、与えるより奪う。明日から幸せを借りてる。その代償を払うな。 |
| 3 | The craving isn't really for alcohol. It's for escape, comfort, or numbness. What do you really need right now? | 渇望は本当はアルコールへのものじゃない。逃避、安心、麻痺への渇望。本当に今必要なのは何？ |
| 4 | Imagine tomorrow morning. Headache, regret, shame. Is tonight's drink worth that? You know it isn't. | 明日の朝を想像して。頭痛、後悔、恥。今夜の酒はそれに値する？値しないってわかってるでしょ。 |
| 5 | This craving is a wave. It will peak and fall. You've survived 100% of your cravings so far. This one is no different. | この渇望は波。ピークが来て落ちる。今まで100%の渇望を生き延びてきた。これも同じ。 |
| 6 | Connection is the opposite of addiction. Call someone. Text someone. Don't be alone with the craving. | つながりは依存症の反対。誰かに電話して。メッセージして。渇望と一人でいるな。 |
| 7 | Alcohol doesn't solve problems—it pauses them while creating new ones. The problem will still be there tomorrow, plus a hangover. | 酒は問題を解決しない—新しい問題を作りながら一時停止するだけ。問題は明日もある、二日酔いと一緒に。 |
| 8 | Every hour you stay sober is a win. Every day is a bigger win. You're winning right now. Keep going. | 素面でいる1時間は勝利。1日はもっと大きな勝利。今、勝ってる。続けろ。 |

---

### 3.11 anger（怒り）

| # | English | 日本語 | トーン |
|---|---------|--------|--------|
| 1 | Pause. 3 seconds before you speak. | 一時停止。話す前に3秒。 | gentle |
| 2 | Anger hurts you more than them. | 怒りは相手より自分を傷つける。 | logical |
| 3 | Is this worth your peace? | これ、心の平和に値する？ | questioning |
| 4 | Breathe. The moment will pass. | 呼吸して。この瞬間は過ぎ去る。 | gentle |
| 5 | Responding in anger? You'll regret it. | 怒りで反応する？後悔するよ。 | strict |
| 6 | What would the calm version of you do? | 冷静なあなたは何をする？ | questioning |
| 7 | Anger is a secondary emotion. What's underneath? | 怒りは二次感情。下に何がある？ | logical |
| 8 | Walk away. Come back when you're ready. | 離れろ。準備ができたら戻れ。 | strict |

**Content（detail）**:

| # | English | 日本語 |
|---|---------|--------|
| 1 | Before you react, count to 3. 1... 2... 3. In those 3 seconds, your rational brain can catch up to your emotional brain. | 反応する前に3まで数えて。1... 2... 3。その3秒で理性脳が感情脳に追いつける。 |
| 2 | Holding onto anger is like drinking poison and expecting the other person to die. Let it go for your own sake. | 怒りを抱えるのは毒を飲んで相手が死ぬのを期待するようなもの。自分のために手放せ。 |
| 3 | Will this matter in 5 years? 5 months? 5 days? If not, it's not worth losing your peace over. Let it go. | これは5年後に重要？5ヶ月後？5日後？違うなら、心の平和を失う価値はない。手放せ。 |
| 4 | Inhale for 4 seconds. Hold for 4. Exhale for 4. Your nervous system will calm down. Then decide how to respond. | 4秒吸って。4秒止めて。4秒吐いて。神経系が落ち着く。それから反応を決めろ。 |
| 5 | Words spoken in anger can never be unspoken. The relationship damage lasts longer than the anger. Wait. | 怒りで言った言葉は取り消せない。人間関係のダメージは怒りより長く続く。待て。 |
| 6 | There are two versions of you: angry-you and calm-you. Angry-you will regret what they say. Let calm-you respond. | あなたには2つのバージョンがある：怒りの自分と冷静な自分。怒りの自分は言ったことを後悔する。冷静な自分に反応させろ。 |
| 7 | Anger is usually a mask for hurt, fear, or frustration. What's really going on? Address that, not the anger. | 怒りは通常、傷、恐れ、フラストレーションの仮面。本当に何が起きてる？怒りではなくそれに対処しろ。 |
| 8 | You don't have to respond right now. Walk away. Take a walk. Come back when you can think clearly. | 今すぐ反応する必要はない。離れろ。散歩しろ。明確に考えられるようになったら戻れ。 |

---

### 3.12 obsessive（強迫観念）

| # | English | 日本語 | トーン |
|---|---------|--------|--------|
| 1 | The thought is not you. Let it pass. | その思考はあなたじゃない。通り過ぎさせて。 | gentle |
| 2 | You don't have to act on every thought. | 全ての思考に従う必要はない。 | logical |
| 3 | It's okay to leave it unfinished. | 未完成のままでいい。 | gentle |
| 4 | Perfection is the enemy of peace. | 完璧は平和の敵。 | logical |
| 5 | One check is enough. Trust yourself. | 1回の確認で十分。自分を信じろ。 | gentle |
| 6 | The ritual won't save you. Breaking it will. | 儀式はあなたを救わない。破ることが救う。 | logical |
| 7 | Notice the urge. Don't follow it. | 衝動に気づいて。従うな。 | strict |
| 8 | This discomfort is temporary. Sit with it. | この不快感は一時的。耐えろ。 | strict |

**Content（detail）**:

| # | English | 日本語 |
|---|---------|--------|
| 1 | Thoughts are just mental events. They come and go. You don't have to engage with them. Let this one pass like a cloud. | 思考はただのメンタルイベント。来て去る。関わる必要はない。雲のように通り過ぎさせて。 |
| 2 | You have thousands of thoughts a day. Not all of them deserve action. This one doesn't. Let it go. | 1日に何千もの思考がある。全てが行動に値するわけじゃない。これもそう。手放せ。 |
| 3 | The anxiety of leaving something undone will pass. Give it 10 minutes. If you still feel the urge, reconsider. But wait first. | 何かを未完成にする不安は過ぎ去る。10分待って。まだ衝動を感じたら再考。でもまず待て。 |
| 4 | Chasing perfection creates anxiety. 'Good enough' creates peace. This is good enough. Move on. | 完璧を追うと不安が生まれる。「十分」は平和を作る。これで十分。先に進め。 |
| 5 | You checked. It's done. Checking again won't make it more done. Trust the first check. Move on. | 確認した。終わった。もう一度確認してももっと終わったことにはならない。最初の確認を信じろ。先に進め。 |
| 6 | The compulsion promises relief but delivers more anxiety. Break the cycle by not performing the ritual. The discomfort will pass. | 強迫は安心を約束するがもっと不安をもたらす。儀式をしないことでサイクルを壊せ。不快感は過ぎ去る。 |
| 7 | You feel the urge. Good—you noticed it. Now don't act on it. Just notice. The urge will peak and fade on its own. | 衝動を感じる。良い—気づいた。今、従うな。ただ気づいて。衝動は勝手にピークを迎えて消える。 |
| 8 | This uncomfortable feeling is temporary. It will pass whether you perform the ritual or not. Choose not to. Sit with the discomfort. | この不快な感覚は一時的。儀式をしてもしなくても過ぎ去る。しないことを選べ。不快感と共にいろ。 |

---

### 3.13 loneliness（孤独）

| # | English | 日本語 | トーン |
|---|---------|--------|--------|
| 1 | You're not alone in feeling alone. | 孤独を感じてるのはあなただけじゃない。 | gentle |
| 2 | Reach out to one person today. | 今日、誰か一人に連絡して。 | gentle |
| 3 | Solitude can be peaceful. Loneliness doesn't have to be permanent. | 孤独は穏やかになれる。寂しさは永遠じゃない。 | logical |
| 4 | Text someone. Even just "hey". | 誰かにメッセージ。「やあ」だけでも。 | gentle |
| 5 | Connection starts with one small step. | つながりは小さな一歩から。 | gentle |
| 6 | Being alone is not the same as being lonely. | 一人でいることと孤独は違う。 | logical |
| 7 | Your presence matters to someone. | あなたの存在は誰かにとって大事。 | gentle |
| 8 | Go outside. Smile at a stranger. | 外に出て。見知らぬ人に微笑んで。 | gentle |

**Content（detail）**:

| # | English | 日本語 |
|---|---------|--------|
| 1 | Millions of people feel lonely right now. You're not alone in feeling alone. This feeling is human, and it will pass. | 何百万人が今孤独を感じてる。孤独を感じてるのはあなただけじゃない。この感覚は人間的で、過ぎ去る。 |
| 2 | Connection doesn't require a deep conversation. Just reach out to one person today. A simple "thinking of you" can change both your days. | つながりに深い会話は必要ない。今日、誰か一人に連絡するだけ。「考えてた」の一言で両方の1日が変わる。 |
| 3 | Solitude is being alone and content. Loneliness is being alone and craving connection. You can transform loneliness into peaceful solitude. | 孤独は一人で満足してること。寂しさは一人でつながりを渇望してること。寂しさを穏やかな孤独に変えられる。 |
| 4 | Send a message to someone you haven't talked to in a while. Just "hey, thinking of you." Most people are happy to hear from you. | しばらく話してない人にメッセージを送って。「やあ、考えてた」だけ。ほとんどの人は連絡をもらって嬉しい。 |
| 5 | You don't need to find your soulmate today. Just one small connection. A smile, a text, a call. Start small. | 今日ソウルメイトを見つける必要はない。小さなつながり一つだけ。微笑み、メッセージ、電話。小さく始めろ。 |
| 6 | You can be alone without being lonely. And you can be lonely in a crowd. The key is quality of connection, not quantity. | 一人でも寂しくないことがある。群衆の中でも孤独になれる。鍵はつながりの質、量じゃない。 |
| 7 | Someone out there is glad you exist. Maybe they haven't told you recently, but you matter to someone. You always do. | 誰かがあなたの存在を喜んでる。最近言われてないかもしれないけど、あなたは誰かにとって大事。いつもそう。 |
| 8 | A small interaction can shift your whole mood. Go outside. Smile at a stranger. Say hi to a neighbor. Connection is everywhere. | 小さな交流が気分全体を変える。外に出て。見知らぬ人に微笑んで。隣人にこんにちはと言って。つながりはどこにでもある。 |

---

## 4. BetaDistribution実装

### 4.1 新規ファイル: BetaDistribution.swift

**パス**: `aniccaios/aniccaios/Services/BetaDistribution.swift`

```swift
import Foundation

/// Beta分布からのサンプリング
///
/// Thompson Sampling で使用。
/// アルゴリズム: Gamma分布経由（Marsaglia and Tsang's method）
struct BetaDistribution {
    let alpha: Double
    let beta: Double

    /// 初期化
    /// - Parameters:
    ///   - alpha: 成功回数 + 1（事前分布として1を加算済み想定）
    ///   - beta: 失敗回数 + 1（事前分布として1を加算済み想定）
    init(alpha: Double, beta: Double) {
        precondition(alpha > 0, "alpha must be positive")
        precondition(beta > 0, "beta must be positive")
        self.alpha = alpha
        self.beta = beta
    }

    /// Beta分布からサンプリング（0〜1の値を返す）
    func sample() -> Double {
        let x = gammaSample(shape: alpha)
        let y = gammaSample(shape: beta)
        guard x + y > 0 else { return 0.5 }
        return x / (x + y)
    }

    /// 期待値を計算
    var mean: Double {
        alpha / (alpha + beta)
    }

    /// Gamma分布からのサンプリング（Marsaglia and Tsang's method）
    /// 参考: https://www.hongliangjie.com/2012/12/19/how-to-generate-gamma-random-variables/
    private func gammaSample(shape: Double) -> Double {
        // shape < 1 の場合は変換
        if shape < 1 {
            let u = Double.random(in: Double.leastNonzeroMagnitude..<1)
            return gammaSample(shape: shape + 1) * pow(u, 1.0 / shape)
        }

        let d = shape - 1.0 / 3.0
        let c = 1.0 / sqrt(9.0 * d)

        while true {
            var x: Double
            var v: Double

            repeat {
                x = gaussianSample()
                v = 1.0 + c * x
            } while v <= 0

            v = v * v * v
            let u = Double.random(in: 0..<1)

            if u < 1.0 - 0.0331 * (x * x) * (x * x) {
                return d * v
            }

            if log(u) < 0.5 * x * x + d * (1.0 - v + log(v)) {
                return d * v
            }
        }
    }

    /// 標準正規分布からのサンプリング（Box-Muller法）
    private func gaussianSample() -> Double {
        let u1 = Double.random(in: Double.leastNonzeroMagnitude..<1)
        let u2 = Double.random(in: 0..<1)
        return sqrt(-2.0 * log(u1)) * cos(2.0 * .pi * u2)
    }
}
```

---

## 5. NudgeContentSelector変更

### 5.1 As-Is（現状）

**パス**: `aniccaios/aniccaios/Services/NudgeContentSelector.swift`

```swift
// 行 87-136: selectByDataLevel メソッド

/// データ量に応じた選択戦略
private func selectByDataLevel(variants: [Int], problem: ProblemType, hour: Int) -> Int {
    // 80%活用 / 20%探索の固定ルール
    // ...
}
```

### 5.2 To-Be（変更後）

```swift
// MARK: - Thompson Sampling

/// Thompson Sampling でバリアント選択
///
/// 各バリアントの tapped/ignored 履歴から Beta 分布を構築し、
/// サンプリングして最大値のバリアントを選択する。
///
/// - Beta(alpha, beta) where:
///   - alpha = tappedCount + 1
///   - beta = ignoredCount + 1
/// - 事前分布: Beta(1, 1) = 一様分布
private func selectByThompsonSampling(variants: [Int], problem: ProblemType, hour: Int) -> Int {
    let samples = variants.map { variantIndex -> (variantIndex: Int, sample: Double, alpha: Double, beta: Double) in
        let stats = NudgeStatsManager.shared.getStats(
            problemType: problem.rawValue,
            variantIndex: variantIndex,
            hour: hour
        )

        // alpha = tapped + 1, beta = ignored + 1
        let alpha = Double(stats?.tappedCount ?? 0) + 1.0
        let beta = Double(stats?.ignoredCount ?? 0) + 1.0

        let distribution = BetaDistribution(alpha: alpha, beta: beta)
        let sample = distribution.sample()

        logger.debug("Variant \(variantIndex): alpha=\(alpha), beta=\(beta), sample=\(String(format: "%.3f", sample))")

        return (variantIndex, sample, alpha, beta)
    }

    if let best = samples.max(by: { $0.sample < $1.sample }) {
        logger.info("Thompson Sampling: selected variant \(best.variantIndex) with sample \(String(format: "%.3f", best.sample))")

        // Mixpanelにログ
        AnalyticsManager.shared.track(.nudgeScheduled, properties: [
            "problem_type": problem.rawValue,
            "variant_index": best.variantIndex,
            "scheduled_hour": hour,
            "selection_method": "thompson_sampling",
            "alpha": best.alpha,
            "beta": best.beta,
            "sample_value": best.sample,
            "tap_rate_estimate": best.alpha / (best.alpha + best.beta)
        ])

        return best.variantIndex
    }

    return variants[0]
}
```

### 5.3 削除するメソッド

| メソッド | 理由 |
|---------|------|
| `selectByDataLevel` | Thompson Sampling に置き換え |
| `selectByTapRate` | Thompson Sampling に統合 |

### 5.4 getGenericVariantIndicesの更新

```swift
/// 汎用バリアントのインデックス配列を返す
private func getGenericVariantIndices(for problem: ProblemType) -> [Int] {
    switch problem {
    case .stayingUpLate:
        return [0, 1, 2, 5, 6, 7, 8, 9]  // 3,4は時刻固定
    case .cantWakeUp:
        return [0, 1, 2, 3, 4, 5, 6, 7]
    case .selfLoathing:
        return [0, 1, 2, 3, 4, 5, 6, 7]
    case .rumination:
        return [0, 1, 2, 3, 4, 5, 6, 7]
    case .procrastination:
        return [0, 1, 2, 3, 4, 5, 6, 7]
    case .anxiety:
        return [0, 1, 2, 3, 4, 5, 6, 7]
    case .lying:
        return [0, 1, 2, 3, 4, 5, 6, 7]
    case .badMouthing:
        return [0, 1, 2, 3, 4, 5, 6, 7]
    case .pornAddiction:
        return [0, 1, 2, 3, 4, 5, 6, 7]
    case .alcoholDependency:
        return [0, 1, 2, 3, 4, 5, 6, 7]
    case .anger:
        return [0, 1, 2, 3, 4, 5, 6, 7]
    case .obsessive:
        return [0, 1, 2, 3, 4, 5, 6, 7]
    case .loneliness:
        return [0, 1, 2, 3, 4, 5, 6, 7]
    }
}
```

---

## 6. タイミング最適化改善

### 6.1 As-Is（現状）

```swift
// NudgeStatsManager.swift

// 24時間以上前 & 未tapped = ignored
if hoursDiff >= 24 && !nudge.wasTapped {
    recordIgnored(...)
}
```

### 6.2 To-Be（変更後）

```swift
// NudgeStatsManager.swift

#if DEBUG
/// デバッグ用: ignored判定の時間（分）
static let ignoredThresholdMinutes = 1  // 本番は15分
#else
static let ignoredThresholdMinutes = 15
#endif

/// ignored判定（アプリ起動時に呼び出す）
func checkAndRecordIgnored() async {
    let now = Date()
    let calendar = Calendar.current

    for (key, nudge) in scheduledNudges {
        guard !nudge.wasTapped else { continue }

        let minutesDiff = calendar.dateComponents([.minute], from: nudge.scheduledDate, to: now).minute ?? 0

        // 15分（デバッグ時は1分）以上経過 & 未tapped = ignored
        if minutesDiff >= Self.ignoredThresholdMinutes {
            recordIgnored(
                problemType: nudge.problemType,
                variantIndex: nudge.variantIndex,
                scheduledHour: nudge.scheduledHour
            )

            // Mixpanelに送信
            AnalyticsManager.shared.track(.nudgeIgnored, properties: [
                "problem_type": nudge.problemType,
                "variant_index": nudge.variantIndex,
                "scheduled_hour": nudge.scheduledHour
            ])

            // scheduledNudgesから削除
            scheduledNudges.removeValue(forKey: key)
        }
    }

    saveToStorage()
}
```

### 6.3 最大シフト量の制限

```swift
// ProblemNotificationScheduler.swift

/// 最大シフト量（分）
private let maxShiftMinutes = 120  // 2時間まで

// タイミング最適化
let consecutiveIgnored = await MainActor.run {
    NudgeStatsManager.shared.getConsecutiveIgnoredDays(problemType: problemRaw, hour: time.hour)
}

let currentShift = getCurrentShiftMinutes(for: problemRaw, hour: time.hour)

if consecutiveIgnored >= 2 && currentShift < maxShiftMinutes {
    // 30分後ろにシフト
    adjustedMinute += 30
    if adjustedMinute >= 60 {
        adjustedMinute -= 60
        adjustedHour = (adjustedHour + 1) % 24
    }
    logger.info("Shifted \(problemRaw) from \(time.hour):\(time.minute) to \(adjustedHour):\(adjustedMinute)")
}
```

---

## 7. 全くタップしない人への対処

### 7.1 判定ロジック

```swift
// NudgeStatsManager.swift

/// 過去7日間の全通知がignoredかチェック
func isCompletelyUnresponsive(for problem: ProblemType) -> Bool {
    let allStats = stats.values.filter { $0.problemType == problem.rawValue }
    let totalTapped = allStats.reduce(0) { $0 + $1.tappedCount }
    let totalIgnored = allStats.reduce(0) { $0 + $1.ignoredCount }

    // 7日以上のデータがあり、tap率が0%
    let hasEnoughData = (totalTapped + totalIgnored) >= 7
    let tapRate = (totalTapped + totalIgnored) > 0
        ? Double(totalTapped) / Double(totalTapped + totalIgnored)
        : 1.0

    return hasEnoughData && tapRate == 0
}

/// まだ試していないトーンのバリアントを優先的に選択
func selectUntriedVariant(for problem: ProblemType) -> Int? {
    let allStats = stats.values.filter { $0.problemType == problem.rawValue }
    let triedVariants = Set(allStats.map { $0.variantIndex })

    let allVariants = Set(0..<8)  // 0-7
    let untriedVariants = allVariants.subtracting(triedVariants)

    return untriedVariants.randomElement()
}
```

### 7.2 使用方法

```swift
// NudgeContentSelector.swift

func selectVariant(for problem: ProblemType, scheduledHour: Int) -> Int {
    // 完全無反応ユーザーの場合
    if NudgeStatsManager.shared.isCompletelyUnresponsive(for: problem) {
        logger.info("Completely unresponsive user detected for \(problem.rawValue)")

        // まだ試していないバリアントを選択
        if let untriedVariant = NudgeStatsManager.shared.selectUntriedVariant(for: problem) {
            logger.info("Selecting untried variant: \(untriedVariant)")
            return untriedVariant
        }
    }

    // 通常のThompson Sampling
    // ...
}
```

---

## 8. デバッグメニュー

### 8.1 追加するデバッグ機能

```swift
// DebugMenuView.swift

#if DEBUG
struct DebugMenuView: View {
    var body: some View {
        List {
            Section("Nudge Stats") {
                Button("Record 10 ignored for variant_0") {
                    Task {
                        await NudgeStatsManager.shared.debugRecordIgnored(
                            problemType: "staying_up_late",
                            variantIndex: 0,
                            scheduledHour: 21,
                            count: 10
                        )
                    }
                }

                Button("Record 7 days ignored for all variants") {
                    Task {
                        for variant in 0..<8 {
                            await NudgeStatsManager.shared.debugRecordIgnored(
                                problemType: "staying_up_late",
                                variantIndex: variant,
                                scheduledHour: 21,
                                count: 7
                            )
                        }
                    }
                }

                Button("Reset all stats") {
                    NudgeStatsManager.shared.resetAllStats()
                }
            }

            Section("Notifications") {
                Button("Trigger midnight notification") {
                    // 0:00の通知を即座に発火
                    NotificationCenter.default.post(
                        name: .debugTriggerMidnightNotification,
                        object: nil
                    )
                }

                Button("Reschedule all notifications") {
                    Task {
                        await ProblemNotificationScheduler.shared.rescheduleAllNotifications()
                    }
                }
            }
        }
        .navigationTitle("Debug Menu")
    }
}
#endif
```

---

## 9. テスト手順

### 9.1 テスト1: バリアントが正しく表示される

**前提**: `staying_up_late` を選択済み

| ステップ | 操作 | 期待結果 |
|---------|------|---------|
| 1 | 設定 → 言語を日本語に変更 | 言語が日本語に変わる |
| 2 | Xcodeでビルド（Cmd+R） | ビルド成功、アプリが起動 |
| 3 | アプリを開く | My Pathタブが表示される |
| 4 | 21:00頃に通知が来る | 通知が表示される |
| 5 | 通知を長押し | 通知プレビューが表示される |
| 6 | 通知のタイトルを確認 | 10個のバリアントのいずれか（日本語） |
| 7 | 通知をタップ | NudgeCardViewが表示される |
| 8 | detailテキストを確認 | 対応するコンテンツ（日本語） |

---

### 9.2 テスト2: Thompson Samplingが動作する

| ステップ | 操作 | 期待結果 |
|---------|------|---------|
| 1 | Xcodeコンソールを開く | コンソールが表示される |
| 2 | アプリ → 設定 → 7回タップ | デバッグメニューが表示される |
| 3 | 「Record 10 ignored for variant_0」をタップ | コンソールに「DEBUG: Recorded 10 ignored」が出力 |
| 4 | 「Reschedule notifications」をタップ | 通知が再スケジュールされる |
| 5 | 次の通知を待つ or 時刻を進める | 通知が来る |
| 6 | コンソールを確認 | 「Thompson Sampling: selected variant X」が出力（X ≠ 0） |

---

### 9.3 テスト3: 時刻固定バリアントが動作する

| ステップ | 操作 | 期待結果 |
|---------|------|---------|
| 1 | デバッグメニューで「Trigger midnight notification」をタップ | 0:00の通知が即座に発火 |
| 2 | 通知のタイトルを確認 | 「深夜0時を過ぎました」（日本語）または「It's past midnight」（英語） |
| 3 | コンソールを確認 | 「Selected time-specific variant 3」が出力 |

---

### 9.4 テスト4: ignored判定が動作する

| ステップ | 操作 | 期待結果 |
|---------|------|---------|
| 1 | 通知を受信 | 通知が表示される |
| 2 | タップせずに**2分待つ**（デバッグ時は1分判定） | - |
| 3 | アプリを開く | - |
| 4 | コンソールを確認 | 「Recorded ignored: staying_up_late_X_21」が出力 |

---

### 9.5 テスト5: 全くタップしない人への対処

| ステップ | 操作 | 期待結果 |
|---------|------|---------|
| 1 | デバッグメニューで「Record 7 days ignored for all variants」をタップ | 全バリアントに7日分のignoredが記録される |
| 2 | 「Reschedule notifications」をタップ | - |
| 3 | コンソールを確認 | 「Completely unresponsive user detected」が出力 |
| 4 | 選択されたバリアントを確認 | まだ試していないバリアントが選ばれる（「Selecting untried variant」が出力） |

---

## 10. Phase 6 詳細

### 10.1 背景

Phase 5でThompson Samplingが動き、データが溜まる。Phase 6ではLLMがそのデータを見て、新しいバリアントを生成する。

### 10.2 決定事項

| 項目 | 決定 |
|------|------|
| 生成頻度 | 毎朝5:00（ユーザーが起きる前） |
| 生成内容 | その日の全スロット（時刻、通知、コンテンツ、reasoning） |
| 比率 | 初期: 80%既存 / 20%LLM → LLMが勝ったら逆転 |
| 移行条件 | 500 nudgeイベント以上、LLMのtap率 > 既存 + 5% |

### 10.3 LLMに渡すデータ

```json
{
  "user_id": "xxx",
  "problem_type": "staying_up_late",
  "yesterday_results": [
    {"variant": 2, "hour": 21, "result": "tapped", "feedback": "thumbs_up"},
    {"variant": 0, "hour": 22, "result": "ignored"}
  ],
  "user_preferences": {
    "preferred_tone": "strict",
    "avoided_tone": "gentle",
    "most_active_hours": [21, 22, 23]
  }
}
```

### 10.4 LLMの出力

```json
{
  "schedule": [
    {
      "hour": 21,
      "minute": 0,
      "notification": "スマホを置け。今すぐ。",
      "content": "画面を見る時間を15分減らすだけで、睡眠の質が20%上がる研究がある。今夜試してみろ。",
      "reasoning": "この人はstrictトーンに反応が良い。21時は最も反応が良い時間帯。"
    }
  ]
}
```

---

## 11. Phase 7 詳細

### 11.1 背景

Phase 6ではLLMがコンテンツを生成するが、選択はまだThompson Sampling。Phase 7ではLLMが選択も行う（タイミングも含む）。

### 11.2 決定事項

| 項目 | 決定 |
|------|------|
| LLMが決めること | 時刻、通知、コンテンツ、全て |
| 固定スケジュール | なし（LLMが判断） |
| reasoningの記録 | 必須（フィードバック用） |

### 11.3 LLMに渡す追加データ

```json
{
  "time_based_results": {
    "21:00": {"tap_rate": 0.8, "samples": 20},
    "22:00": {"tap_rate": 0.3, "samples": 15},
    "23:00": {"tap_rate": 0.6, "samples": 10}
  },
  "nudge_effectiveness": {
    "strict_tone_21h": {"tap_rate": 0.9},
    "gentle_tone_21h": {"tap_rate": 0.4}
  }
}
```

---

## 12. 哲学

### 12.1 重要なこと

- 何が最適なNudgeか
- いつ送るべきか
- この人の苦しみをどう終わらせるか

### 12.2 重要じゃないこと

- モダリティ（テキスト/画像/音声/動画）
- ツールの数
- アプリ内滞在時間

### 12.3 理想の状態

```
ユーザーがアプリをダウンロード
    ↓
オンボーディング（1-2画面）
    ↓
通知が来る（タップすらしない）
    ↓
その通知だけで行動が変わる
    ↓
苦しみが減る
    ↓
最終的に通知すら不要になる（苦しみが終わった）
```

### 12.4 Inceptionの例え

15分の夢で人生が変わるように、1つの通知で苦しみが終わる可能性がある。
Robert Fischerは15分の夢で根本的に変わった。
Aniccaも、正しいタイミングで正しい通知があれば、それができる。

### 12.5 LSDの例え

正しいタイミングで正しい介入があれば、短時間で根本的な変化が起きる。
末期癌患者がLSDで死の恐怖を克服したように、
Aniccaも苦しみの構造を一瞬で変える可能性がある。

### 12.6 目標

通知だけで、タップすらせずに、苦しみが終わる。
アプリを開く必要すらない。
それが最高の状態。

---

*この仕様書は Phase 5 の完全な実装を定義する。*
