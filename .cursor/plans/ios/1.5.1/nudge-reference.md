# Nudge コンテンツ・タイミング リファレンス（TO-BE）

> v1.5.1 修正後の設計を反映。カスケード完全削除、全67スロットユニーク（バッティングゼロ）、Day 1 決定論的割り当て。
> 内容やタイミングを変更したら、このファイルも更新すること。

## サマリー

| # | 問題タイプ | タイトル | スロット数 | スロット | バリアント数 | ボタン |
|---|-----------|---------|-----------|---------|-------------|--------|
| 1 | staying_up_late | Put the Phone Down | 6 | 20:00, 21:00, 22:00, 23:00, 0:00, 1:00 | 10 | 2択 |
| 2 | cant_wake_up | Get Up Now | 5 | 6:00, 6:15, 6:30, 8:00, 22:15 | 8 | 2択 |
| 3 | self_loathing | Forgive Yourself | 5 | 7:00, 12:00, 14:45, 17:00, 19:00 | 8 | 1択 |
| 4 | rumination | Return to Now | 5 | 8:30, 18:00, 19:30, 21:15, 22:45 | 8 | 2択 |
| 5 | procrastination | Do It Now | 5 | 9:00, 11:00, 13:00, 15:00, 18:30 | 8 | 2択 |
| 6 | anxiety | You're Safe | 5 | 7:30, 10:00, 14:00, 17:30, 20:45 | 8 | 1択 |
| 7 | lying | Be Honest | 5 | 8:15, 11:30, 14:30, 16:30, 19:15 | 8 | 2択 |
| 8 | bad_mouthing | Kind Words | 5 | 9:30, 12:30, 15:30, 18:15, 21:45 | 8 | 2択 |
| 9 | porn_addiction | Beat the Urge | 6 | 20:30, 21:30, 22:30, 23:30, 0:30, 1:30 | 8 | 2択 |
| 10 | alcohol_dependency | Don't Drink Tonight | 5 | 16:00, 17:15, 18:45, 19:45, 20:15 | 8 | 2択 |
| 11 | anger | Let Go of Anger | 5 | 7:45, 10:45, 13:30, 15:45, 16:45 | 8 | 2択 |
| 12 | obsessive | Stop Overthinking | 5 | 8:45, 10:30, 12:15, 14:15, 17:45 | 8 | 2択 |
| 13 | loneliness | Reach Out | 5 | 9:15, 11:15, 13:45, 15:15, 16:15 | 8 | 1択 |

**合計:** 67 スロット（全てユニーク）、212 ユニークコンテンツ（106 通知 + 106 カード詳細）

---

## Day 1 バリアント割り当てルール

| スロット順 | バリアント# | 説明 |
|-----------|-----------|------|
| 1st | 0 | 最初のスロット → バリアント 0 |
| 2nd | 1 | 2番目 → バリアント 1 |
| 3rd | 2 | 3番目 → バリアント 2 |
| 4th | 3 | 4番目 → バリアント 3 |
| 5th | 4 | 5番目 → バリアント 4 |
| 6th（該当時） | 5 | 6番目 → バリアント 5 |

- Day 1 は Thompson Sampling を使わない
- 同じ日に同じバリアントは絶対に来ない
- Day 2+ は LLM コンテンツ優先、LLM 無しなら Thompson Sampling（usedVariants で重複排除）

---

## タイムスロット設計ルール

| ルール | 内容 |
|--------|------|
| バッティング | **ゼロ** — 全67スロットがユニーク |
| ルールベース最低間隔（異なる問題間） | **15分**（設計保証済み） |
| ルールベース最低間隔（同一問題内） | **30分以上**（cant_wake_up wake window のみ15分許可） |
| LLM DON'T間隔（異なる問題間） | **30分**（プロンプトで指示、違反時は警告ログ） |
| 同一問題 wake window | **15分**（cantWakeUp 6:00-6:30） |
| カスケード | **完全削除**（バッティングしないので不要） |
| iOS 制限 | 最大64通知（13問題全選択 = 67 → ソート順で末尾3件ドロップ）。**ソート順:** 日跨ぎスロット（0:00-1:30）は翌日扱い（=当日最遅）。ソートキー: `翌日フラグ(0/1)` → `時刻昇順`。末尾3件 = porn_addiction 1:30, staying_up_late 1:00, porn_addiction 0:30 |

---

## 深夜許可ルール

| 問題タイプ | 許可時間帯 | 理由 |
|-----------|-----------|------|
| staying_up_late | 6:00-01:30 | ピーク 22:00-01:00、深夜介入が核心 |
| porn_addiction | 6:00-01:30 | 同じ深夜ピーク帯 |
| その他11問題 | 6:00-23:00 | 23:00以降は sleep 問題（staying_up_late/porn_addiction）のみ |

---

## 1. STAYING_UP_LATE（TO-BE: 6スロット）

**タイトル:** Put the Phone Down
**ボタン:** Protect Tomorrow / Hurt Myself
**スロット:** 20:00, 21:00, 22:00, 23:00, 0:00, 1:00
**深夜許可:** 6:00-01:30

### Day 1 バリアント割り当て

| スロット | 時間 | バリアント# | 通知テキスト |
|---------|------|-----------|-------------|
| 1 | 20:00 | 0 | "Breathe, don't scroll." |
| 2 | 21:00 | 1 | "How many years have you lost to 'just 5 more minutes'?" |
| 3 | 22:00 | 2 | "Tomorrow's you will regret this." |
| 4 | 23:00 | 5 | "Put down your phone. Now." |
| 5 | 0:00 | 3 | "It's past midnight. Your body needs rest now." |
| 6 | 1:00 | 4 | "It's 1 AM. Every minute awake costs you tomorrow." |

> **注意:** スロット4-6は時間依存テキストとスロット時刻を一致させるため、順番割り当て（3,4,5）ではなく時間対応割り当て（5,3,4）を使用。Day 2+ は LLM が時刻に合った内容を生成するため影響なし。

### 通知テキスト（10バリアント）

| # | テキスト |
|---|---------|
| 0 | Breathe, don't scroll. |
| 1 | How many years have you lost to 'just 5 more minutes'? |
| 2 | Tomorrow's you will regret this. |
| 3 | It's past midnight. Your body needs rest now. |
| 4 | It's 1 AM. Every minute awake costs you tomorrow. |
| 5 | Put down your phone. Now. |
| 6 | Your future self is watching. What do they see? |
| 7 | Sleep is not optional. It's medicine. |
| 8 | The screen can wait. Your dreams can't. |
| 9 | Every hour of sleep = better decisions tomorrow. |

### カード詳細（10バリアント）

| # | テキスト |
|---|---------|
| 0 | Move your phone 30cm from your face. Turn brightness to minimum. Take 5 deep breaths. Your brain will switch to 'sleep prep' mode. |
| 1 | A sleep-deprived brain has the same judgment as 0.1% blood alcohol. 17 hours awake = legally drunk. Protect tomorrow's decisions by sleeping tonight. |
| 2 | Will you remember this content tomorrow at noon? But sleep deprivation will definitely hurt your focus, judgment, and immunity. Which matters more? |
| 3 | Sleep deprivation compounds like debt. Tonight's lost hour will steal next week's focus and judgment. Move your phone away from bed. Close your eyes. |
| 4 | Staying awake past 1 AM causes measurable damage to your brain and heart. What you're doing is 100x less important than sleep. Go to bed now. |
| 5 | Your willpower is at its lowest right now. Don't fight the urge to scroll—just remove the phone. Put it in another room. |
| 6 | Imagine waking up refreshed vs. waking up exhausted. Which version of tomorrow do you want? You decide right now. |
| 7 | Sleep repairs your brain, consolidates memories, and resets emotions. Skipping it is like skipping maintenance on a car you drive daily. |
| 8 | The blue light is telling your brain it's noon. Your body is confused. Help it by putting the screen away. |
| 9 | One hour of sleep tonight = 3 hours of productivity tomorrow. The math is simple. Go to bed. |

---

## 2. CANT_WAKE_UP

**タイトル:** Get Up Now
**ボタン:** Start Today / Stay in bed
**スロット:** 6:00, 6:15, 6:30, 8:00, 22:15
**Wake Window:** 6:00-6:30（15分間隔許可）

### Day 1 バリアント割り当て

| スロット | 時間 | バリアント# | 通知テキスト |
|---------|------|-----------|-------------|
| 1 | 6:00 | 0 | "Your day won't start until you get up." |
| 2 | 6:15 | 1 | "The 'just 5 more minutes' you has zero credibility." |
| 3 | 6:30 | 2 | "Stay Mediocre" |
| 4 | 8:00 | 3 | "Feet on the floor. 5, 4, 3, 2, 1." |
| 5 | 22:15 | 4 | "The blanket is lying to you." |

### 通知テキスト（8バリアント）

| # | テキスト |
|---|---------|
| 0 | Your day won't start until you get up. |
| 1 | The 'just 5 more minutes' you has zero credibility. |
| 2 | Stay Mediocre |
| 3 | Feet on the floor. 5, 4, 3, 2, 1. |
| 4 | The blanket is lying to you. |
| 5 | Your alarm is a promise. Keep it. |
| 6 | Morning wins build confidence. |
| 7 | Get up now, or regret it at noon. |

### カード詳細（8バリアント）

| # | テキスト |
|---|---------|
| 0 | Count 5, 4, 3, 2, 1 and put your feet on the floor. Move before you think. Get up before your brain makes excuses. Nothing changes under the blanket. |
| 1 | How many times have you trusted the '5 more minutes' you? How many times were you betrayed? Getting up now keeps a promise to yourself. You'll like today's you. |
| 2 | Start today sloppy again? Or change starting now? Your action in the next 5 seconds decides. Stand up. |
| 3 | Your body is awake. Your mind is making excuses. Override it. Feet on the floor. Now. |
| 4 | The blanket feels safe, but it's a trap. Comfort now = regret later. Rip off the blanket like a bandaid. |
| 5 | Every morning you hit snooze, you break a promise to yourself. Small betrayals compound. Start today with integrity. |
| 6 | People who win mornings win days. People who win days win weeks. It starts with getting up when you said you would. |
| 7 | Noon-you will be grateful. Evening-you will be proud. But only if morning-you gets up now. |

---

## 3. SELF_LOATHING

**タイトル:** Forgive Yourself
**ボタン:** Forgive Myself（1択）
**スロット:** 7:00, 12:00, 14:45, 17:00, 19:00

### Day 1 バリアント割り当て

| スロット | 時間 | バリアント# | 通知テキスト |
|---------|------|-----------|-------------|
| 1 | 7:00 | 0 | "You're alive today. That's enough." |
| 2 | 12:00 | 1 | "It's okay to stop blaming yourself." |
| 3 | 14:45 | 2 | "Would you say this to a friend? Then don't say it to yourself." |
| 4 | 17:00 | 3 | "You're a much better person than you think." |
| 5 | 19:00 | 4 | "Self-criticism won't make you better. Compassion will." |

### 通知テキスト（8バリアント）

| # | テキスト |
|---|---------|
| 0 | You're alive today. That's enough. |
| 1 | It's okay to stop blaming yourself. |
| 2 | You're a much better person than you think. |
| 3 | Self-criticism won't make you better. Compassion will. |
| 4 | Would you say this to a friend? Then don't say it to yourself. |
| 5 | You're trying. That's what matters. |
| 6 | Your worth isn't measured by productivity. |
| 7 | Be kind to yourself. Just for today. |

### カード詳細（8バリアント）

| # | テキスト |
|---|---------|
| 0 | Self-loathing proves you want to be better. But self-criticism doesn't lead to growth—it backfires. You woke up today. That's enough. |
| 1 | If your best friend was in your situation, what would you say? You wouldn't say 'You're worthless.' Give yourself the same kindness. |
| 2 | Is what you're blaming yourself for truly 'irreparable'? Most things are smaller than they feel. Take a deep breath and look objectively. |
| 3 | Research shows self-compassion leads to more growth than self-criticism. Being harsh on yourself doesn't work. Try kindness instead. |
| 4 | You wouldn't let anyone else talk to your friend this way. Why do you let yourself talk to you this way? Protect yourself like you'd protect a friend. |
| 5 | Progress isn't linear. Bad days don't erase good days. You're trying, and that's more than most people do. |
| 6 | You are not your productivity. You are not your achievements. You are worthy of love and rest just by existing. |
| 7 | Just for today, speak to yourself like you'd speak to someone you love. Just for today. Tomorrow you can go back to being hard on yourself if you want. |

---

## 4. RUMINATION

**タイトル:** Return to Now
**ボタン:** Return to Now / Keep Thinking
**スロット:** 8:30, 18:00, 19:30, 21:15, 22:45

### Day 1 バリアント割り当て

| スロット | 時間 | バリアント# | 通知テキスト |
|---------|------|-----------|-------------|
| 1 | 8:30 | 0 | "What are you feeling right now?" |
| 2 | 18:00 | 1 | "The loop is a trap. Step out." |
| 3 | 19:30 | 2 | "Your thoughts are not facts." |
| 4 | 21:15 | 3 | "You've been here before. You survived." |
| 5 | 22:45 | 4 | "Name 5 things you can see right now." |

### 通知テキスト（8バリアント）

| # | テキスト |
|---|---------|
| 0 | What are you feeling right now? |
| 1 | The loop is a trap. Step out. |
| 2 | Your thoughts are not facts. |
| 3 | You've been here before. You survived. |
| 4 | Name 5 things you can see right now. |
| 5 | This moment will pass. Everything does. |
| 6 | Stop replaying. Start living. |
| 7 | The past is a story. You're writing the present. |

---

## 5. PROCRASTINATION

**タイトル:** Do It Now
**ボタン:** Do 5 min / Later
**スロット:** 9:00, 11:00, 13:00, 15:00, 18:30

### Day 1 バリアント割り当て

| スロット | 時間 | バリアント# | 通知テキスト |
|---------|------|-----------|-------------|
| 1 | 9:00 | 0 | "Just 5 minutes. That's all you need." |
| 2 | 11:00 | 1 | "Start ugly. Refine later." |
| 3 | 13:00 | 2 | "Done is better than perfect." |
| 4 | 15:00 | 3 | "Every reason not to do it is an excuse." |
| 5 | 18:30 | 4 | "Future you is begging present you to start." |

### 通知テキスト（8バリアント）

| # | テキスト |
|---|---------|
| 0 | Just 5 minutes. That's all you need. |
| 1 | Start ugly. Refine later. |
| 2 | Done is better than perfect. |
| 3 | Every reason not to do it is an excuse. |
| 4 | Future you is begging present you to start. |
| 5 | The hardest part is starting. Do it now. |
| 6 | You don't need motivation. You need movement. |
| 7 | 5 minutes of action beats 5 hours of planning. |

---

## 6. ANXIETY

**タイトル:** You're Safe
**ボタン:** Deep Breath（1択）
**スロット:** 7:30, 10:00, 14:00, 17:30, 20:45

### Day 1 バリアント割り当て

| スロット | 時間 | バリアント# | 通知テキスト |
|---------|------|-----------|-------------|
| 1 | 7:30 | 0 | "In this moment, you are safe." |
| 2 | 10:00 | 1 | "Anxiety lies. Right now, you are okay." |
| 3 | 14:00 | 2 | "You've survived 100% of your worst days." |
| 4 | 17:30 | 3 | "Name 3 things you can see right now." |
| 5 | 20:45 | 4 | "Your body is safe. Your mind is lying." |

### 通知テキスト（8バリアント）

| # | テキスト |
|---|---------|
| 0 | In this moment, you are safe. |
| 1 | Anxiety lies. Right now, you are okay. |
| 2 | You've survived 100% of your worst days. |
| 3 | Name 3 things you can see right now. |
| 4 | Your body is safe. Your mind is lying. |
| 5 | Breathe in 4, hold 4, out 4. |
| 6 | This feeling is temporary. It always passes. |
| 7 | You are stronger than your anxiety. |

---

## 7. LYING

**タイトル:** Be Honest
**ボタン:** Be Honest / Lie
**スロット:** 8:15, 11:30, 14:30, 16:30, 19:15

### Day 1 バリアント割り当て

| スロット | 時間 | バリアント# | 通知テキスト |
|---------|------|-----------|-------------|
| 1 | 8:15 | 0 | "One truth builds more trust than ten lies." |
| 2 | 11:30 | 1 | "Lies compound. Truth simplifies." |
| 3 | 14:30 | 2 | "Honesty is the shortcut to respect." |
| 4 | 16:30 | 3 | "The truth is lighter than the weight of a lie." |
| 5 | 19:15 | 4 | "Be the person who keeps their word." |

### 通知テキスト（8バリアント）

| # | テキスト |
|---|---------|
| 0 | One truth builds more trust than ten lies. |
| 1 | Lies compound. Truth simplifies. |
| 2 | Honesty is the shortcut to respect. |
| 3 | The truth is lighter than the weight of a lie. |
| 4 | Be the person who keeps their word. |
| 5 | Every lie is a debt you'll have to pay. |
| 6 | Integrity starts with small truths. |
| 7 | The person you lie to most is yourself. |

---

## 8. BAD_MOUTHING

**タイトル:** Kind Words
**ボタン:** Kind Words / Bad-mouth
**スロット:** 9:30, 12:30, 15:30, 18:15, 21:45

### Day 1 バリアント割り当て

| スロット | 時間 | バリアント# | 通知テキスト |
|---------|------|-----------|-------------|
| 1 | 9:30 | 0 | "Gossip hurts you more than them." |
| 2 | 12:30 | 1 | "What you say about others says more about you." |
| 3 | 15:30 | 2 | "Speak about people as if they were listening." |
| 4 | 18:15 | 3 | "Build people up. Tearing down is easy and weak." |
| 5 | 21:45 | 4 | "Kind words cost nothing but mean everything." |

### 通知テキスト（8バリアント）

| # | テキスト |
|---|---------|
| 0 | Gossip hurts you more than them. |
| 1 | What you say about others says more about you. |
| 2 | Speak about people as if they were listening. |
| 3 | Build people up. Tearing down is easy and weak. |
| 4 | Kind words cost nothing but mean everything. |
| 5 | Would you say this to their face? |
| 6 | Your words shape your character. |
| 7 | Choose to be someone who lifts others. |

---

## 9. PORN_ADDICTION（TO-BE: 6スロット）

**タイトル:** Beat the Urge
**ボタン:** Overcome / Give In
**スロット:** 20:30, 21:30, 22:30, 23:30, 0:30, 1:30
**深夜許可:** 6:00-01:30

### Day 1 バリアント割り当て

| スロット | 時間 | バリアント# | 通知テキスト |
|---------|------|-----------|-------------|
| 1 | 20:30 | 0 | "The urge is a wave. It will pass in 10 minutes." |
| 2 | 21:30 | 1 | "Your brain is lying. You don't need it." |
| 3 | 22:30 | 2 | "Every time you resist, you get stronger." |
| 4 | 23:30 | 3 | "Think about how you'll feel after." |
| 5 | 0:30 | 4 | "This moment of weakness doesn't define you." |
| 6 | 1:30 | 5 | "You're better than this urge. Prove it." |

### 通知テキスト（8バリアント）

| # | テキスト |
|---|---------|
| 0 | The urge is a wave. It will pass in 10 minutes. |
| 1 | Your brain is lying. You don't need it. |
| 2 | Every time you resist, you get stronger. |
| 3 | Think about how you'll feel after. |
| 4 | This moment of weakness doesn't define you. |
| 5 | You're better than this urge. Prove it. |
| 6 | Your future self will thank you for stopping now. |
| 7 | Replace the urge. Do 20 push-ups. Now. |

---

## 10. ALCOHOL_DEPENDENCY

**タイトル:** Don't Drink Tonight
**ボタン:** Stay Sober / Drink
**スロット:** 16:00, 17:15, 18:45, 19:45, 20:15

### Day 1 バリアント割り当て

| スロット | 時間 | バリアント# | 通知テキスト |
|---------|------|-----------|-------------|
| 1 | 16:00 | 0 | "One day at a time. You can do this." |
| 2 | 17:15 | 1 | "The bottle is not your friend." |
| 3 | 18:45 | 2 | "Sobriety is a gift to tomorrow's you." |
| 4 | 19:45 | 3 | "You don't need alcohol to relax." |
| 5 | 20:15 | 4 | "Every sober night is a victory." |

### 通知テキスト（8バリアント）

| # | テキスト |
|---|---------|
| 0 | One day at a time. You can do this. |
| 1 | The bottle is not your friend. |
| 2 | Sobriety is a gift to tomorrow's you. |
| 3 | You don't need alcohol to relax. |
| 4 | Every sober night is a victory. |
| 5 | Your body is healing every hour you don't drink. |
| 6 | The craving will pass. Wait 10 minutes. |
| 7 | You're choosing freedom over dependence. |

---

## 11. ANGER

**タイトル:** Let Go of Anger
**ボタン:** Let Go / Stay Angry
**スロット:** 7:45, 10:45, 13:30, 15:45, 16:45

### Day 1 バリアント割り当て

| スロット | 時間 | バリアント# | 通知テキスト |
|---------|------|-----------|-------------|
| 1 | 7:45 | 0 | "Pause. 3 seconds before you speak." |
| 2 | 10:45 | 1 | "Is this worth your peace?" |
| 3 | 13:30 | 2 | "Anger is a fire that burns you first." |
| 4 | 15:45 | 3 | "Take a deep breath. You're in control." |
| 5 | 16:45 | 4 | "Let it go. It's not worth carrying." |

### 通知テキスト（8バリアント）

| # | テキスト |
|---|---------|
| 0 | Pause. 3 seconds before you speak. |
| 1 | Is this worth your peace? |
| 2 | Anger is a fire that burns you first. |
| 3 | Take a deep breath. You're in control. |
| 4 | Let it go. It's not worth carrying. |
| 5 | Respond, don't react. |
| 6 | Your peace is more valuable than being right. |
| 7 | Holding anger is like drinking poison. |

---

## 12. OBSESSIVE

**タイトル:** Stop Overthinking
**ボタン:** Let Go / Keep Thinking
**スロット:** 8:45, 10:30, 12:15, 14:15, 17:45

### Day 1 バリアント割り当て

| スロット | 時間 | バリアント# | 通知テキスト |
|---------|------|-----------|-------------|
| 1 | 8:45 | 0 | "The thought is not you. Let it pass." |
| 2 | 10:30 | 1 | "Let go of control. Trust the process." |
| 3 | 12:15 | 2 | "Perfection is the enemy of peace." |
| 4 | 14:15 | 3 | "You've checked enough. It's okay." |
| 5 | 17:45 | 4 | "Your mind is on a loop. Break it." |

### 通知テキスト（8バリアント）

| # | テキスト |
|---|---------|
| 0 | The thought is not you. Let it pass. |
| 1 | Perfection is the enemy of peace. |
| 2 | You've checked enough. It's okay. |
| 3 | Your mind is on a loop. Break it. |
| 4 | Let go of control. Trust the process. |
| 5 | Not every thought deserves your attention. |
| 6 | The uncertainty is okay. You can handle it. |
| 7 | Redirect your mind. Move your body. |

---

## 13. LONELINESS

**タイトル:** Reach Out
**ボタン:** Reach Out（1択）
**スロット:** 9:15, 11:15, 13:45, 15:15, 16:15

### Day 1 バリアント割り当て

| スロット | 時間 | バリアント# | 通知テキスト |
|---------|------|-----------|-------------|
| 1 | 9:15 | 0 | "You're not alone in feeling alone." |
| 2 | 11:15 | 1 | "Text someone. Even just 'hey'." |
| 3 | 13:45 | 2 | "Connection starts with one message." |
| 4 | 15:15 | 3 | "Someone is thinking about you right now." |
| 5 | 16:15 | 4 | "Loneliness is a feeling, not a fact." |

### 通知テキスト（8バリアント）

| # | テキスト |
|---|---------|
| 0 | You're not alone in feeling alone. |
| 1 | Text someone. Even just 'hey'. |
| 2 | Connection starts with one message. |
| 3 | Someone is thinking about you right now. |
| 4 | Loneliness is a feeling, not a fact. |
| 5 | You matter to more people than you think. |
| 6 | Reach out. The worst they can say is 'busy'. |
| 7 | Being alone and being lonely are different things. |

---

## 変更点まとめ（As-Is → TO-BE）

| 項目 | As-Is | TO-BE |
|------|-------|-------|
| staying_up_late スロット | (20:30, 21:30, 22:30, 23:30, 7:30) | (20:00, 21:00, 22:00, 23:00, 0:00, 1:00) |
| porn_addiction スロット | (20:00, 21:30, 22:30, 23:30, 7:30) | (20:30, 21:30, 22:30, 23:30, 0:30, 1:30) |
| 全問題のタイムスロット | バッティングあり（20以上の衝突） | **全67スロットがユニーク、バッティングゼロ** |
| Day 1 バリアント選択 | Thompson Sampling（ランダム） | **決定論的**（スロット順 = バリアント順） |
| カスケード | シフトして解消 | **完全削除**（バッティングしないので不要） |
| validTimeRange | nil（死コード） | **実装済み**（問題タイプ別） |
| 日内重複コンテンツ | 防止なし | **usedVariants で排除** |

---

最終更新: 2026-01-30
