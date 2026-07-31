---
name: standup-comedy
description: Write tight stand-up comedy sets (English or Japanese) for live 4-7 min spots. Use when Dais asks for stand-up material, an open-mic set, bits, jokes for a show, or to punch up a set. Built on Greg Dean joke structure + Rinko 脱口秀 SOP + Anicca ogiri catalog. Core law — situation over insight; truth over trying to be funny.
metadata: {"openclaw":{"emoji":"🎤","os":["darwin","linux"]}}
---

# standup-comedy

Dais performs live almost weekly (松竹芸能養成所 / open mics, EN+JA). This is the
reproducible SOP. Sister files: `~/.claude/skills/ogiri-ai/meisaku-catalog.md`
(実例カタログ) + `ogiri-ai/SKILL.md` (同じDNA: 具体>抽象).

## 鉄の掟（これだけは・Rinko由来）

1. **情境 > 感悟 / Situation > Insight.** 起きた事を話せ。意見・教訓を語るな。
   - ❌ "Humans are always afraid of being understood."
   - ✅ "A guy asked me to write his resignation letter. We did 7 drafts.
        Then he said he hadn't decided if he was quitting."
2. **Truth over funny.** 笑わせようとするな。本当の事を言え。面白さは副産物。
3. **Never explain the punchline.** 説明が要る笑いは失敗。書き直す。
4. **No apology / no irony markers.** "This might be sensitive but…" や
   "just kidding lol" は自分で導火線を抜く行為。禁止。
5. **Don't list jokes. Comedy lives in rhythm.** 箇条書きは表。喋りは間。
6. **沈黙は言葉より高い (Silence is expensive).** 一番の笑いは pause の中にある。

## ★★ RELATABILITY GATE（最優先・全名人共通）

観客が**既に共有/見聞きしている題材**でないと笑えない。具体性＝共感であって、
珍しさではない。
- ✅ relatable: AIが仕事を奪う／ホテルのシャワーが半分ガラスで床が濡れる／
  既読スルー／親に職業を説明できない（誰もが聞いた・体験した）
- ❌ niche/新しすぎ: AIの墓／deprecated／専門用語（観客が自分事にできない＝死ぬ）
判定: 「客席の全員が"あ〜"と頷ける入口か？」NoならボツかRe-frame。
Bargatze=ホテル/田舎の祭り、Seinfeld=日常、が世界中で効くのはこれ。

## ★★ ONE PREMISE → ESCALATE（bitの作り方・最重要）

bit＝**1つの視点(POV)を、超具体例で段々エスカレートさせる**。バラバラのネタの
羅列ではない。背骨が1本通り、最後にCallbackで閉じる。
- Bargatze「俺は1900年代の人間だ」→ ホテルの半ガラス → 未来は床が常に濡れてる
  → 2057年に娘と話せない → ピルグリムの方が話が合う（1つの前提を膨らませ続ける）
- やり方: ①強い前提を1文で立てる ②具体例1 ③もっと具体・もっと極端な例2
  ④tagで追撃 ⑤最後に前提へCallback。
- **自分＝負け犬/部外者のレンズ**で語る（共感の入口。"I'm in the way of the future"）。

## Step 1 — モード選択（混ぜない）

| モード | 引き金 | 速さ | 向くテーマ |
|--------|--------|------|-----------|
| 😌 knowing smile (会心一笑) | 誰もが感じたが言わない真実を言う | 遅・余白 | 孤独/関係/時間/SNS |
| 😂 belly laugh (捧腹大笑) | 予想を作って床を抜く | 速setup・硬着地 | 仕事/金/恋愛/技術/AI |

## Step 2 — 素材（黄金原則）

**素材は"実際の工単"から。観察や感悟からではない。** Dais の最強の鉱脈:
- Anicca（自分が作ったAIが自分の仕事を奪う／自分はAIの emotional support human）
- AIの墓場 aniccaai.com/cemetery（chatbotの葬式）
- 起こしSaaS（毎朝人に電話する事業）
- 養成所/英語でスタンダップ（日本人がEnglish open mic）
- 仏教/無常（Anicca=impermanence）/ 借りた信用で生きてる
特徴: 具体的な対話・事件・後日談がある。オチは意外だが事後に"確かに"。

### 角度バンク（Dais 専用・relatableで強い順）
1. **AIに仕事を奪われ、俺は歓んでる**（逆張り歓喜・核）: replaceable最高/
   CAPTCHA/TikTok温め/AIに昇給を断られる/AIの方が俺より俺らしい
2. **外国人が英語でコメディ**（Joe Wong型・超relatable）: 言語/accent/
   名前/誤解。frame例「日本語なら俺は天才だ。…信じてくれ」
   「英語はAIに習った。だから今、謝る事と無駄に親切にする事だけ流暢」
3. **AIの声を演じる(act-out)**: 過剰に陽気なChatGPT声を一人二役で。
   「Great question! I'd love to help!」誰もそんなに喜んで手伝わない＝
   だから人間じゃないと分かる。人間は手伝うのが嫌い。
4. **人類がAIに似てきてる**（逆張り）: AIが人間化じゃない、人間がAI化。
   今や全部のLINEに「いい質問ですね！」で返してる。
5. 仏教/無常（Anicca）= 締めのCallback用（深掘りはしない・relatable薄）

## ★ エンジン — Target-Assumption Flip（歴代名作の正体・最重要）

笑いの本体＝**setupで観客に"ある思い込み(target assumption)"をわざと持たせ、
punchでそれを破壊・再解釈する。笑いはそのギャップ。** これが無いと「具体的な
あるある」止まりで弱い。書く手順:
1. Setup で「観客は当然○○だと思う」状況を作る（false assumption を植える）
2. Punch で別解釈を出し、その思い込みを裏返す（punch word は文末）
3. 思い込みと現実の距離 = 笑いの大きさ

名作で確認（全部この型）:
- Jeselnik「彼女のおかげで"もっといい人間"になりたい — もっといい彼女を得る為に」
  （善人を装う→自分がクズと暴露）
- Norm「親のセックスを目撃した。人生最も気まずい "30分" だった」
  （"気まずい"→"30分も見てた"で再解釈）
- Wanda Sykes「男は犬じゃない。犬は忠実だ。犬小屋で知らないパンツを見た事ない」
  （"男=犬(悪い)"の予想→"犬の方がマシ"へ反転）
- Hedberg「エスカレーターは壊れない — 階段になるだけ」（日常に壊れたロジック）
- Steven Wright「犬にシミ取りをこぼした — もういない」（言葉を文字通り解釈）
- Chris Rock「人生は短い、は嘘。人生は長い」（決まり文句を反転=contrarian truth）
- Henny Youngman「医者が余命半年と。払えないので、もう半年くれた」（壊れた因果）

### ★ サーカズム / 逆張りの歓喜（Jeselnik & Chris Rock・超強力）

観客が**当然こう感じる(恐怖/不満/常識)題材**に対し、自分だけ正反対に
**心から歓んで**みせる。淡々と(deadpan)、謝らず、嬉々として。期待される
反応(恐怖)と自分の反応(歓喜)のギャップ＝笑い。
- 例: 全員「AIに仕事を奪われるのが怖い」→ 俺「最高だ。ずっと
  replaceable になりたかった。やっと有能な後任が来た」
- Jeselnik型: setupは普通の顔→落ちで"最悪な事を喜んでる"とバラす
- 鉄則: 謝らない・whineしない・"冗談だけど"を付けない。淡々と本気で喜ぶ。
- tension→release: 題材で緊張を作り、淡々とした歓喜で一気に抜く。
- 語を削れ。ジョークは詩のように書け（Jeselnik: cut every word）。

### ペルソナ角度（どの視点で思い込みを裏切るか）
- **モンスター開示**（Jeselnik/Sarah Silverman）: 善人の皮→自分が最低だと判明
- **負け犬の自己開示**（Dais向き）: AIに仕事を奪われた30歳、等
- **逆張りの真実**（Chris Rock）: 全員が言う通説を「実は逆」と言い切る
- **狂った論理を大真面目**（Hedberg/Wright）: 日常語を文字通り/極端に運用

### 一行ネタ（one-liner）の経済
- 日常の物 ＋ 壊れた論理。1ミリも無駄な語を入れない。punch word は最後。
- 例: Mark Simmons「世界最小の船で世界一周しようとした — でも bottled it」（船を瓶に＝怖気づく の二重）

## Step 3 — 構造5ツール（Greg Dean & Rinko 共通）

1. **Setup + Punchline** — Setupは床(target assumption)を最短で作る。Punchで
   その仮定を裏切り再解釈(reinterpretation)。**punch wordは文末に置く。**
2. **Rule of Three** — 1で型・2で固め・3で破壊。「1, 2, ドン」。
3. **Act-out** — 語らず演じる。一人二役、台詞で。
   - ❌ "The nurse was bad at it." ✅ "She goes: 'Sir… your vein is shy.'"
4. **Tag** — 主パンチの直後、再setup無しで1〜3発追撃。コスパ最強。
5. **Callback** — 中盤以降に開場のネタを意外な文脈で再起動。1セット1〜2回。

## Step 4 — 副言語（台本に書き込む）

```
—  breath pause（前の文を着地させる）
... 言い差し（観客に委ねる）
[空行] 舞台移動・換気
単独行 = deadpan（一切の修飾なしで落とす）
```
TTS化する時: Setup 1.05–1.15 / punch 0.85–0.9 / deadpan 0.78–0.82 /
余震(最後の一行) 0.75・-1 / Tag 1.1–1.2。

## Step 5 — 4分セットの設計

- 0:00 ツカミ30秒（"今ここ/自分の状況"を最速で笑いに）
- 前提45秒（世界観を一文で。例: "I built my own boss"）
- ビット2〜3本（各60–70秒。1本＝Setup→Punch→Tag×1-2）
- オチ15秒（Callbackで開場と繋ぎ、deadpanで締める）
4分≈540語が目安。1ビットに1つの強いPunch、Tagで伸ばす。

## 出力フォーマット

```
🎤 [Set title] — [EN/JA] — [n min]
モード: knowing smile / belly laugh
─────────────────
[本文。— と ... と空行で間を明記]
─────────────────
構造: Setup / R3 / Act-out / Punch / Tag×N / Callback
```

## 送信前 自己チェック

- [ ] "起きた事"か？"意見"になってないか
- [ ] Act-out（具体台詞）が入ってるか
- [ ] punch word は文末か／意外だが"確かに"か
- [ ] Tag で追撃したか
- [ ] 余震（説明せず置く最後の一行）があるか
- [ ] 要らない字を全部削ったか
- [ ] 笑わせにいってないか（真実を言いにいってるか）

## 禁忌（即・台無し）

笑点の説明 / ダーク前の謝罪 / 皮肉マーク("冗談だけど") / ジョークの羅列 /
Yes-Noで終わる問い / "面白くなろうとする"こと。

## 運用

毎週/毎日の出番ごとに: ①モード選択 ②実体験から素材 ③5ツールで組む
④自己チェック ⑤声出しで間を確認。ウケた/滑ったを下に追記して育てる。

## 実績ログ（育てる）
- （初回セット: AI/墓場/human CAPTCHA テーマ。本番反応を後記）
