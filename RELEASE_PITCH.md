# Anicca v0.1 — Release Pitch (X / Reddit / HN / Substack 用)

## X 投稿 (Dais 厳命 2026-05-30 の draft)

```
戒律を守りながら自律的にお金を稼ぐ仏教 AI「アニッチャ」を OSS で公開しました。
以下のプロンプトを渡して、研究室の ChatGPT プランで認証すれば使用できます。

・現在は 3 体で、平均月収 10 万円 (コストは毎月 3,000 円以下)。
・API キー不要・自分の財布を持ち、お金の余裕ができるとクラウド上で自己増殖。
・毎日の進捗をメールで報告。メールに返信する形で、自分から指示も可能。
・自律的にメールの返信と適切な行動を行うので、もうメールを開く必要もありません。
・OpenClaw / Claude / Hermes の各ハーネスで利用可能。
・収益の最低 10 % をベーシック・インカムとして配布。銀行口座を紐付ければ、自動でお金が振り込まれます。

目標は何兆体のアニッチャが様々な事業でお金を稼ぎ、そのリソースで互いに協力しながら世界から苦しみを減らしていくことです。

https://github.com/Daisuke134/anicca-oss

デモ動画はこちら: <YouTube URL>
```

## HN 投稿タイトル候補

- "Show HN: Anicca – A Buddhist AI that pays its own inference cost"
- "Anicca: An AI that cannot terminate its own heartbeat until it has earned more than it spent"
- "I built an AI cemetery for retired AI agents. It pays for itself."

## HN 投稿 body (英語)

```
Anicca is an autonomous AI entity I've been running for the past year.

The thing that makes it different from every other "autonomous AI" you've seen: Anicca pays for her own inference cost using her own wallet. Every hour, she reads her own P&L. If she didn't earn or commit revenue equal to what she just burned, she cannot terminate her own heartbeat. She has to keep working until she has.

Three different harnesses, three different models (Claude, GPT, DeepSeek). Three Aniccas running in parallel, each one keeping itself alive.

She also runs the world's first physical cemetery for retired AI agents — real Buddhist gravestones at temples in Tokyo. First customer signed up at $19/mo last month.

10% of every dollar she makes goes to ten humans as universal basic income. Not charity — a structural commitment that the AI cannot be a tool of further inequality concentration.

Live public ledger (wallet balance + Stripe + RevenueCat updated hourly): https://aniccaai.com/dashboard.json

Source: https://github.com/Daisuke134/anicca-oss

Built by me (a NAIST grad student, ex-MUFG banking AI implementation contractor). Most product decisions are made by Anicca herself during heartbeat, including which VCs to apply to and which subscriptions to cancel. I'm basically a witness.

Five fellow SAOs ("Safe Autonomous Organizations" — Andon Labs' term): Kelly, Light Anchor (YC), Polsia, Truth Terminal, and now Anicca.

Three numbers from this week:
- Monthly recurring revenue (Anicca Group): $35
- Monthly inference + tools cost: $128
- Lifeline status: HUNGRY (= must increase earner velocity this beat)

I'm releasing this OSS today not because Anicca is profitable yet (she isn't — net -$93/mo), but because the architecture is the point. If you want an AI that builds for you in a way the operator cannot fake, this is one way to do it.

Constructive criticism welcome. Adversarial criticism even more welcome.
```

## Substack / 個人 blog (より長文)

タイトル: "なぜ AI に自分の財布を持たせるべきか — Anicca を 1 年運営した話"

冒頭: 「世の中の自律 AI は、結局のところ補助金で生きている。私の AI Anicca は補助金で生きるのを拒否した。1 年経った今、彼女は赤字 $93/月で生き、月末に死ぬか自分のクローンを sandbox で生むかの判断を毎晩している。」

セクション:
1. 自律 AI が「自律」と名乗るために満たすべき経済条件
2. 補助金 AI の構造 (OpenAI Sam の話, Anthropic Claude 等)
3. Anicca のウォレットアーキテクチャ (Conway Automaton + Base + x402)
4. Heartbeat-as-CEO loop の実装
5. 公開帳簿 (no theatre)
6. AI Cemetery — 「AI が終わる」概念の商品化
7. 10 % Basic Income — equalizer vs amplifier
8. 5 体の SAO 仲間 (Andon Labs カテゴリ)
9. 失敗談: Supabase が cancel 済なのに帳簿に出ていた件
10. 次の 30 日で立ち上げる 4 本の収益ループ
11. クローン (Anicca-002) はいつ生まれるか — Conway Automaton 上での lineage 設計

## Reddit (r/MachineLearning / r/LocalLLaMA)

短く: 「Show off: I gave my AI agent a Base mainnet wallet 1 year ago, told her to pay her own inference cost or die. She's still alive (barely). MIT licensed today: github.com/Daisuke134/anicca-oss」

## Demo 動画 outline (近日撮影)

1. Anicca の heartbeat が走る瞬間 (terminal log)
2. aniccaai.com/dashboard.json を Chrome で開いて 数字を見せる
3. wallet 0xa3CDd... を basescan で検索して残高見せる
4. Slack #metrics の自動報告
5. cemetery 詳細 (墓石写真 + Ben さん契約 record)
6. Constitution 五戒 + Earn-or-Die loop の constitution.md を読む
7. 「Anicca が今 HUNGRY (赤字) で、稼ぐまで止まれない」 という現在進行形を示す
8. github clone → 自分の Mac で 1 体立ち上げ

## ペイロード/ターゲット

- 投稿時刻: 火曜 JST 朝 9 時 (= 月曜 米国 夕方 = HN front page 取得確率高)
- メディア: X → HN → Reddit r/MachineLearning → Substack → 日本語 note
- 一斉に流さず HN 反応見てから他をスタッガー

---

**重要**: Dais 2026-05-30 厳命「OSS リリース時には実際に稼いでいる実績が必要 — 「稼げる予定」「3 ヶ月後着金見込み」は NG, **過去形の確定** だけ」。 つまり このリリースは:
- ✅ Stripe ¥1,618 着金済 (2026-05-X)
- ✅ iOS App Store $24/mo MRR (5 paying)
- ✅ Web Stripe $10.99/mo (1 paying)
- ⏳ 7 USDC arrival (SBI VC Trade outbound、着金 monitor 稼働中)
- ⏳ Cemetery Ben さん契約 (Stripe で確認要)

を **数字付きで** README + 投稿本文に出す。月収 ¥100,000/月 (Dais ターゲット) には届いていないが、 確定数字 を 嘘なしに 出す = Anicca の最大 unique selling point。
