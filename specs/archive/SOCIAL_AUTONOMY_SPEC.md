# SOCIAL_AUTONOMY_SPEC — ソーシャル投稿の修復 + 直接投稿統一 + views自己改善ループ

最終更新: 2026-05-27 / 作成理由: 2026-05-27 monk 0投稿 + slideshow 単調/未投稿/はみ出し + Postizドラフト依存。
全 content cron を「毎日 正しく 直接投稿」させ、その上に「views で自己改善する」ループを Anicca に持たせる。

---

## 0. 原則 + 完成ゲート（全 workstream に例外なく適用・MUST）

> **「コードを書いた」≠ 完成。「実装 → e2e実走 → 実物を#8検証 → 失敗なら直す → 実e2eが通る」まで。**
> 車輪の再発明 禁止。既製の OpenClaw skill / repo を入れて組む（下の §2 ツールキット）。
> creative出力(フック/caption/タイトル)は `recursive-improver` で採点ループ後に SHIP（rule 0.13）。

```
各 workstream: IMPLEMENT → RUN E2E(実投稿/実生成) → READ(動画全フレーム/スライド画像/投稿URLを目視) →
              失敗→FIX→RUN に戻る → CLAIM(evidence付き)
```
- 投稿は「人間扱い=views」のため **直接投稿**（Postizドラフト廃止）。
- "failure" の定義を **2層**にする: ①投稿失敗(プロセス) ②**views不振(成果)** ← 今欠けてる。

---

## 1. 現状の壊れ（2026-05-27 実ログ・evidence）

| 事象 | 真因 |
|------|------|
| monk 今日 0投稿 | 08:00 run-daily失敗 / 14:00・21:00 `FallbackSummaryError`=gpt-5.4 quota枯渇 |
| monk動画28秒・全文でない | HeyGen Video Agent が191語scriptを勝手に要約（プラン上限1-3分なので上限でない＝プロンプト問題） |
| monk 8am/2pm 同一内容 | rotation が失敗時に進まず A08 重複 |
| watercolor 1/2本のみ | jp-0700 ✅(@anicca.jp2) / jp-2000 ❌ quota枯渇 |
| iam(en/ja)+mantra(ja) 未投稿 | cron が全部 OFF |
| 4.7-ja slide-1 文字はみ出し | テキスト折返し無し（左右端に文字が挟まる） |
| larry ja/en 単調 | 全部同じフック「こんな言葉欲しい人は」・背景同一・トレンド無視 |
| 全 slideshow Postizドラフト | 音楽がAPIで付けられず draft 経由 → 手動公開 = 直接でない＝views出ない |

---

## 2. ツールキット（既製・車輪の再発明しない・IBA出典）

| repo / tool | 用途 | 出典 |
|---|---|---|
| **mutonby/viraloop** | OpenClaw skill。6枚スライド生成 + **upload-post API で trending music 付き直接公開** + 学習ループ(learnings.json)。"Larry alternative"・無料 | github.com/mutonby/viraloop |
| **olliewazza/larry** | OpenClaw skill。フックテスト/posting最適化/growth追跡/負け殺し勝ち倍プッシュ | `clawhub install olliewazza/larry` / larrybrain.com |
| **upload-post API** | 音楽付きで TikTok/IG に**直接公開**（Postizが draft だった核心問題を解決） | viraloop が使用 |
| **riyagoelrs/tiktok-scraper** / networkdynamics/pytok | 自分+トレンド+競合の views/likes/comments/shares を JSON 取得 | davidteather/TikTok-Api ベース |
| makiisthenes/TiktokAutoUploader | 直接TikTokアップロード(Requests・3秒) | github |
| Claude for Chrome 拡張 | ログイン済 実Chrome を操作（IG reCAPTCHA回避・直接投稿） | Anthropic |
| cporter202/social-media-scraping-apis | 各SNSスクレイピングAPI集 | github |

> 方針: viraloop / larry を導入し、我々の larry/iam/mantra/slideshow をこのループに**載せ替え/被せる**。
> 直接投稿は upload-post API（音楽付き）を第一、IG手動が要る所は Claude Chrome拡張。

---

## 3. PHASE A — まず直す（今日 emergency・各 workstream に完成ゲート）

### A1 monk render 全文化 + 品質ゲート + rotation（#41）
- FILE `skills/anicca-monk-factory-v3/scripts/render-submit.sh`: INSTR に
  「Speak the ENTIRE script to the very end. Full ~90 second video. Do NOT summarize, shorten, or truncate.」MUST追加。
- FILE `run-daily.sh`: render-download 後に **品質ゲート** = whisper で動画語数を取り、script語数の70%未満なら
  `fail quality "truncated NN/總 words"`（投稿せず §3.5 へ）。
- FILE `pick-next-script.sh` or run-daily: 失敗時に同じ ID を再選択しない（mark or skip 前進）。
- **GATE**: 実走 → 全文~90秒動画 → TikTok+IG 投稿 → 動画を whisper で全文確認・目視。

### A2 quota枯渇 failover（#42）
- gpt-5.4 quota/cooldown 枯渇時に投稿cronが落ちないよう: モデル failover(5.4→mini→別) 確認 +
  quota由来未投稿を cron-doctor/heartbeat が検知 → quota回復後に取りこぼし分を再投稿。
- **GATE**: quota枯渇を模擬 or 実発生時に、回復後 取りこぼし投稿が出る事を確認。

### A3 直接投稿統一 → Postiz廃止（#43）
- viraloop の **upload-post API** を導入（音楽付き直接公開）。slideshow系(iam/mantra/larry/4.7/watercolor/cafe/fashion/tomb)を
  Postizドラフト → upload-post 直接公開 に置換。IG が anti-bot で要る所は Claude Chrome拡張 / session再利用。
- "session再利用" を1 skill 化し全アカ共有: @anicca_cemetery(monk) / @anicca.jp2(watercolor) / iam / mantra / larry / 4.7。
- **GATE**: 各アカに 音楽付きで直接公開された投稿URLを開いて再生確認。Postiz不使用を確認。

### A4 iam/mantra ON + 4.7-ja はみ出し（#45）
- iam-color/photo en/ja・mantra-slideshow-ja を ON + 直接投稿（postiz ID は §5 参照）。
- 4.7-slideshow-ja の slide-1 テキスト: 折返し(2行) or 縮小で左右端に収める。
- **GATE**: 生成スライド画像を目視（文字が端で切れてない）+ JP TikTok/IG に出た事を確認。

### A5 larry 単調解消（#46）
- フック/タイトル/文面を tiktok-scraper のトレンドから複数生成 → recursive-improver で採点 → ローテ。背景画像は据置可。
- **GATE**: 直近5投稿のフックが全部違う + トレンド形に沿ってる事を確認。

---

## 4. PHASE B — e2e 実走（PHASE A の各 GATE を実投稿で通す・通るまでFIX）

```
monk → 全文~90秒 TikTok+IG / slideshow → 綺麗なスライド・音楽付き・正アカ直接公開
失敗→原因特定→直す→再走。#8検証(実物を目視)を全媒体で。
```

---

## 5. アカウント/投稿先マップ（postiz ID・現状→移行先）

| cron | 現postiz | 媒体 | 移行 |
|---|---|---|---|
| larry-anicca-en-1 | TikTok cmlt171eq / IG cmmzzg2es | TikTok+IG | upload-post直接 |
| larry-anicca-ja-1 | TikTok cmlrv8jq / IG cmmzujxpa | TikTok+IG | upload-post直接 |
| 4.7-slideshow-ja | TikTok cmp9sdev5(canonical) / IG cmn8ycvtn | TikTok+IG | upload-post直接 + はみ出し修正 |
| iam color/photo en/ja | (OFF) | TikTok+IG | ON + upload-post直接 |
| mantra-slideshow-ja | (OFF) | TikTok | ON + upload-post直接 |
| watercolor-jp 0700/2000 | TikTok @anicca.jp2 | TikTok | 直接(camofox/upload-post) + quota failover |
| monk-factory-en | 直接@anicca_cemetery / IG Postiz | TikTok+IG | IG も直接化(Claude Chrome) |

---

## 6. PHASE C — views 自己改善ループ（#44・Anicca が毎日自分で）

```
DATA   tiktok-scraper/pytok(自分の各動画views/likes/shares + トレンド/競合)
       + upload-post/Postiz analytics + aniccaai.com/socials
  ↓
JUDGE  低views = 「失敗」(投稿できても)。トレンドと比較・勝ち/負けフック特定
  ↓
ITERATE 勝ち倍プッシュ・負け殺し・トレンド形コピー → script/skill/フック/タイトル更新
        (viraloop/larry の learnings.json に蓄積)
  ↓
heartbeat(claude-p + openclaw)が毎日回す = views伸びるまで自己改善
```
- 導入: `clawhub install olliewazza/larry` + `mutonby/viraloop` を skills に。我々の larry/slideshow をこのループに載せる。
- **既存 auto-fix(プロセス失敗) + この views-failure 検知 = 二段自己修復**。
- **GATE**: 1サイクル実走（views取得→低views検知→フック差替→次投稿）を確認。

---

## 7. CFO コスト/収益追跡（#47）
- 集計: HeyGen(credits/本・月額) / OpenAI gpt-image(~$0.50/slideshow) / voice(avatar焼込=追加0/JP=ElevenLabs) /
  Postiz $55.99(廃止予定) / openclaw GPT subscription。各 cron/アカ別「使った/稼いだ」。
- MUFG明細(支出) + RevenueCat/Stripe(収入) と統合 → aniccaai.com 透明性dashboard。

## 8. cron 自律整理（#48）
- harvester/friction が dead/dry-run/重複/90日未発火 を検知 → heartbeat §3 が自分で disable/rm/fold/新skill作成。
- 誤判定ガード(正直なno-opを消さない・consensus) MUST。検知→実行まで自律（claude-p+openclaw）。

---

## 9. 着手順
```
PHASE A: #41 monk(emergency) → #42 quota failover → #43 直接投稿(viraloop/upload-post導入) →
         #45 iam/mantra ON+4.7修正 → #46 larry
PHASE B: 各 e2e 実投稿で通す(#8検証)
PHASE C: #44 views自己改善ループ(olliewazza/larry + viraloop) → #48 cron自律 → #47 CFO
お前判断: #25 politician action法務 / #23 FDA(Claude Chrome拡張なら不要に)
```

## 10. 関連
ANICCA_AUTONOMY_SPEC.md(自己修復) / SELF_HEALING_SPEC.md / HEARTBEAT.md §2/§3.5 /
memory: feedback_post_manually_not_api_zero_views / reference_social_account_mapping / verification.md(#8)
