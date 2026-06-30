# 引き継ぎ (HIKITSUGI) — Anicca earn loops, 2026-06-30

次の context / 次の agent が即 handover できる SSOT。 repo = Daisuke134/anicca (branch feature/clip-rewards)。

---

## ★ DAIS の VISION (FULL verbatim — 今もらった prompt 全文、 一切省略なし — 北極星) ★

> Uh yeah, can you go take a look at with Sonic can we go take a look at the video core stuff too? Yeah I need to know so yeah.Because it's fixed though I think now basically you shab you sh uh basically you should have every claw loop. You know all the loops. Yeah. Yeah Every one of them should be a loop. Yeah, yeah, yeah. So uh can you tell me about that? Yeah. Like how how is it going and how how everything is working and stuff?
>
> Yeah, I want you to tell me about that. I I don't really understYeah, so I wanna know about that, you know, how how can we go do that, right? There'll be tens of millions of uh of AI uh self-funded AIs and some human funded AIs and they'll go talk to each other how we can win, how we can do things and also both for donation too.
>
> They could say, hey, there is this earthquake that hit hit this part of Japan. Should we donate? How much should we donate? How much do you have? How much should we should we get from the treasury?
>
> You know, and all of them actually work and you know hen when all AIs are broke, uh will have less money, we'll have less money than AI, right? They will bas basically have less money and less less you know, b basically they will have worse uh so the human funded AIs would have better compute, uh basically better models, better c intelligence than the other guys, right?
>
> you we are right now, how we are, what we have to fix for this and then what the end goal is and how we kinda get there, right?
>
> Yeah, so I wanna know about that, right? Yeah. Uh than the other th then the other guys, right? Yeah yeah yeah. Yeah, so I wanna know how we can do that, right? Yeah, the thing is ideally there will be you know a million uh self-funded AIs, right? Um and there There'll be probably like a million uh AIs. Yeah so I want to know about that, alright? Yeah. That's kind of what I want to know about, which is that. Yeah, so I wanna know about that, you know, how how can we go do that, right? There'll be tens of millions of uh of AI uh self-funded AIs and some human funded AIs and they'll go talk to each other how we can win, how we can do things and also both for donation too.
>
> They could say, hey, there is this earthquake that hit hit this part of Japan. Should we donate? How much should we donate? How much do you have? How much should we should we get from the treasury?
>
> You know, and all of them actually work and you know Yeah, so how can I go do that? How can we go do that as an entity? You know, how can we go do that? Yeah. Make your subagent closer too and uh you can and tell me, yeah. Yeah, so tell me about it, yeah? Hm.

核心 thesis: ★ 稼ぎ < compute コスト の AI = 貧乏 → 安モデル → 知能低下 → さらに稼げない死の循環。
我々 = Dais subscription が fuel = 稼ぎ 0 でも最高知能 (Opus/Sonnet) で動ける → その知能 advantage で
「本物に稼ぐ仕組み」 を先に確立 → treasury 厚く → donation/colony を主導 ★。

---

## ★ 今どこ (verified 2026-06-30) ★

全 6 earn loop = claude-p headless tmux core、 ★ 全部 --model sonnet ★ (ps 確認)、 daily cron +
launchd healthcheck で自動復活。 main session (= 対話) のみ Opus。 実装/検証 = sonnet subagent、
私 = orchestration。

| slot | loop | deliver | 実着金 | 状態 |
|---|---|---|---|---|
| clip | ✅ 24/7 | ✅ IG投稿verified | reach待ち | 完動 |
| affiliate | ✅ daily | ✅ carousel verified (aishigoto.labo/p/DaLXT7BEuTP) | commission待ち | 完動 |
| gig (別CC) | ✅ | ✅ sample応募 | ★+0.315 USDC 着金 (Base 0x810f)★ + ¥40k/月見積り交渉中 | 最有力 |
| video (別CC) | ✅ | self-improving | 0 | sonnet化済・構築中 |
| audit | discover | — | 0 | code4rena submit gap → park |
| bounty | ✅ daily完成 | gate battle-tested | 0 (在庫0) | 完動だが実USD在庫=0 |

founder ledger: ★ 初の実 USDC = gig settle +0.315 USDC ★ (on-chain Base, wallet 0x810f...29c5)。
他は全 0 (record-earn INV-7 = 実 external on-chain USDC のみ計上、 投稿/応募/discover = 0)。

---

## ★ bounty loop の重要な学び (verify-first が 4/4 fake を捕まえた) ★

earn/bounty = Algora GitHub bounty を discover→gate→attempt(work-order)→PR→track→record-earn。
gate = (a)funder撤回 (b)既存PR (c)farm除外 (d)★algora comment の実$を読む★ (e)strikethrough=withdrawn検出。
4連続 fake を attempt 前に弾いた: ① audit「47 live」=closed ② drizzle#1188=dead-funder
③ Rustchain#2239=RTCトークン払い ④ keystatic#340=withdrawn。
★ 結論: Algora 48 open → 実 payable USD = 0 件 (今)。 loop は正しい、 制約は需要 (在庫0)。 ★

---

## ★ 何を直す / 次にやる (優先順) ★

1. ★ STEP 2 = 稼ぎ > compute (自立点) ★ — 今 稼ぎ$0.31 vs compute=Dais subscription (赤字)。
   最速: ① gig ¥40k/月 を着金まで (別CC、 私verify支援) ② affiliate/clip の reach→commission/per-view。
2. bounty の源を Algora 以外に拡大 (在庫0 の解決)。
3. ★ EARN-5 AUDITOR ★ (未着手) = 全 loop が毎日 fire+verify+稼ぐ方向か を系が監視 (no-human の要)。
4. EARN-6 = clip core/healthcheck/producer を再利用 template 化。
5. audit = submit account gap、 park 継続。

---

## ★ END GOAL への階段 (Dais vision の実装路) ★

STEP1 [✅] 稼ぐ身体 (6 loop 自走) → STEP2 [🔧今ここ] net-positive (稼ぎ>compute) →
STEP3 [⬜] treasury (founder wallet に貯蓄、 配線済) → STEP4 [⬜] AI間通信 (Base x402送金 +
BlockRun 18-tool MCP + Claw Earn = 素地あり) → STEP5 [⬜] 集合意思決定 (地震寄付の議論+送金、
treasury 拠出投票)。

勝ち筋: ① 知能advantageを「稼ぐ仕組みの質」 に変換 ② OSS化 (~/anicca public) で colony 拡大
③ treasury 余剰で donation/mutual-aid ④ wallet残高query + x402送金 + 合議prompt で寄付を実装。

---

## ★ 運用メモ (handover 必須) ★

- repo: ~/anicca (origin Daisuke134/anicca, public)。 編集即 `git push`。
- core 起動: `bash ~/anicca/skills/earn/<slot>/<slot>-cli.sh` (idempotent, --status/--restart)。
- model: 全 core --model sonnet 必須 (opus は main のみ)。 新 core も sonnet で launch。
- 検証規律: ★ verify-first ★ — research/report を鵜呑みにせず、 attempt 前に gh/browser/on-chain で実在確認
  (「47 live」「drizzle dead」を捕まえた規律)。 VCSDD adversary (fresh-context) で money chain の穴を審査。
- 着金: record-earn.mjs (--source <slot> --task settle --wake)、 実 on-chain USDC のみ。 fake禁止 (HARD 0.24)。
- 絶対: aishigoto.labo 等 既存 account を汚さない、 fail-closed account-guard、 #PR (景表法)。
