# Skill 4 — Clip-Rewards Design (per-view clipping, dual-payout)

**Date:** 2026-06-28 · **Branch:** feature/frank-run · **Status:** SPEC (research-grounded; OSS tooling pending fork `clip-tooling-jp`)
**Author:** Claude (dev IDE) for Dais · **Parent SSOT:** `2026-06-28-claude-earn-skills-spec.md` (Skill 4 section)

## §0 Mission — why this skill exists

AI が自分で動画を切り抜いて per-view 報酬を受け取る。 受取先は 2 軸 (Dais 2026-06-28 明示):

- **Mode 1 (= AI-native, prized)**: USDC → Anicca 自身の Base mainnet wallet `0x810f...` 。 ★ AI が AI のために稼ぐ、 銀行 KYC ゼロ、 人間ゼロ ★
- **Mode 2 (= human-funded, secondary)**: USD/JPY → Dais の JP 銀行 (Stripe Connect or Payoneer 経由)

★ 両 mode は SAME pipeline + SAME clips + SAME accounts から派生 ★。 Mode 1 が holy grail (= "every Claude が自分で稼ぐ" の唯一の path)。

## §1 Platforms — verified 2026-06-28

| Platform | Payout 経路 | KYC | Mode | 採用 |
|---|---|---|---|---|
| **ClipAffiliates** ⭐ | USDC / USDT / BTC、 9% fee、 72h | crypto wallet のみ | **1** | ★ primary ★ |
| **Whop Content Rewards** | Stripe Connect → bank (JP は凍結報告あり) | 身分証+銀行 | **2** | secondary |
| **Vyro** | PayPal / 銀行 / crypto、 fixed $3 CPM | medium | 1 or 2 | safety net (MrBeast 系素材限定) |
| Clipping.net | $0.50/1,000、 ★ 100K view 最低 ★ | medium | — | skip (閾値高い) |
| TikTok CRP (自社) | TikTok 規定 | follower 10K + 100K/30d | — | skip (AI/text-overlay 不払い) |
| YouTube Shorts 分配 | AdSense | YPP gate (1Ksubs+4Kh) | — | skip (二次利用 NG) |
| IG Reels Bonuses | — | — | — | skip (program 廃止) |

**Sources (verbatim quote-checked):**
- ClipAffiliates: [clipaffiliates.com/blog/whop-vyro-clipping-alternatives-2026](https://www.clipaffiliates.com/blog/whop-vyro-clipping-alternatives-2026)
- Whop Content Rewards: [whop.com/blog/content-rewards](https://whop.com/blog/content-rewards/) → "Content Rewards clippers are, on average, paid $1 per 1,000 views"
- Whop Clips ($190K/month payout): [whop.com/blog/whop-clips](https://whop.com/blog/whop-clips/)
- Whop ToS / KYC: [whop.com/tos](https://whop.com/tos)
- TikTok CRP 原本要件: [TikTok FAQ 7581821550694013452](https://www.tiktok.com/support/faq_detail?id=7581821550694013452)
- YouTube Shorts 二次利用不可: [Google Support 12504220](https://support.google.com/youtube/answer/12504220)

## §2 Dual-payout architecture (= the big idea)

```
                     ┌──── ClipAffiliates ─USDC─► Anicca wallet 0x810f (Base)
                     │                           ★ Mode 1: AI-native, zero human ★
                     │                           = "every Claude が自分で稼ぐ"
1 pipeline + clips ──┤
                     │                                          
                     ├──── Whop ──Stripe Connect──► Dais JP bank
                     │                              ★ Mode 2: human-funded ★
                     │
                     └──── Vyro ──PayPal/銀行/USDC──► どちらにも振れる safety net
```

- **同じ投稿** が 2 経路で稼ぐ。 1 clip = 同時に ClipAffiliates 案件 + Whop 案件 + Vyro 案件 (規約が許す範囲で)。
- **Mode 1 を主軸に**: 銀行 KYC が要らない = Anicca instance を colony で増やす時、 各 instance が自分の wallet で稼げる (= Type 2 colony 設計と一致、 memory `feedback_anicca_type1_type2_mutual_aid`)。
- **Mode 2 は同時運用**: 既に Dais の身分証で KYC が通せる = sunk cost。 並走すれば収益経路が 2 倍。
- **ledger は両方を 1 ファイルで集計**: `~/.smtm/earn-loops/clip/earn-ledger.jsonl`、 行に `payout_mode: "usdc_self" | "jpy_bank"` を持つ。

## §3 Pipeline — long-form → 15-30 short clips

★ OSS research fork (`clip-tooling-jp`) 戻り後、 ここに採用 stack + repo URL + コマンド列 を埋める ★

暫定方針 (= 戻り次第確定):
- **入力**: 長尺 1-3h podcast / interview / stream (公開 YouTube が主、 後で配信主が許諾の切り抜き先指定があればそれに従う)
- **highlight 検出**: OSS で「viral 候補時刻」 を自動抽出 (Opus Clip 系の OSS 代替)
- **字幕**: `whisper` (or `whisperx`) で transcript → 英語 → 日本語翻訳 → burned-in subtitle (★ JP subtitle 焼き込み = §5 の viral pattern を取りに行く ★)
- **9:16 変換**: `ffmpeg` で crop + Remotion で hook overlay
- **量**: 1 長尺 → 15-30 短尺 (= 1 日 1-3 長尺投入で full-time クリッパー並みの output)
- **投稿**: 既存 `reelclaw` 経由で TikTok + IG + X に同一 clip ばらまき

## §4 Account strategy

- ★ Skill 1 で作る Anicca TikTok/IG/X を **再利用** ★ (= 同じ AI/productivity niche、 視聴者 overlap、 立ち上げの遅延ゼロ)。 専用 clip アカウントは作らない。
- 各 clip post 仕様:
  - 9:16 mp4 + JP 焼き込み字幕 + hook overlay (= 最初 1.5 秒)
  - キャプション末尾 = `#PR ` + 案件指定 hashtag (Whop / ClipAffiliates brief 規約準拠)
  - BIO 引き続き Amazon Associates affiliate link (= Skill 1 と同居)

## §5 Viral pattern: EN 素材 → JP 字幕

★ fork 戻り後、 実例 channel 3 つ + 字幕スタイル (位置 / 色 / font / 速さ) を埋める ★

仮説 (= 検証対象):
- ホリエモン切り抜き型 (= JP 素材を JP に) は素材入手の許諾 negotiation が必要 = 自動化困難
- ★ EN podcast / interview / stream を JP 字幕で出す型 ★ は素材入手が free (= public YouTube)、 翻訳が AI で完結、 JP 視聴者層 (英語苦手) には新規情報源 = viral 化しやすい
- 候補素材: Lex Fridman / Joe Rogan / All-In / 20VC / a16z 等の公開 podcast

## §6 OSS tooling stack — pending fork

★ fork (`clip-tooling-jp`) 戻り後、 1 つの組合せに絞って verbatim follow ★

調査中の candidate (実在確認 + license 確認は fork 側で実行):
- `harry0703/MoneyPrinterTurbo` (= 既に memory 検証済、 short-form CLI、 $0)
- `RayVentura/ShortGPT`
- `SamurAIGPT/AI-Youtube-Shorts-Generator`
- `openai/whisper` + `m-bain/whisperx` (字幕焼き込み)
- `yt-dlp` (素材 DL)
- `ffmpeg` + Remotion (= 既存)

## §7 Daily loop (= claude -p + launchd、 親 spec §6 と同じ universal cycle)

```
EVERY DAY (autonomous):
  read clip/STATE.md
   → 1. SCAN active campaigns (ClipAffiliates + Whop + Vyro brief)
   → 2. SOURCE long-form (today's trending EN podcast / interview / stream)
   → 3. CLIP (OSS pipeline §6 → 15-30 短尺 + JP 字幕)
   → 4. POST (reelclaw → TikTok + IG + X、 各 clip 個別 URL)
   → 5. MEASURE yesterday's view (per platform API)
   → 6. RECORD payouts (USDC → wallet hit、 JPY → bank/Stripe report)
   → 7. /goal check (USDC 着金 > $0 OR JPY 着金 > ¥0) → write STATE → sleep
   └─── repeat forever ───┘
```

## §8 TODO — unabridged

- **C4-0** OSS research fork `clip-tooling-jp` を待つ → 戻り次第 §3/§5/§6 を更新 + commit+push
- **C4-1** ClipAffiliates アカウント signup (= **Mode 1 path**): tt-anicca@agentmail.to で開設、 KYC 必要なら crypto-only mode、 payout wallet = `0x810f...` (Base) に bind。 do-once = signup 完了 + dashboard へ login 成功。
- **C4-2** Whop アカウント signup (= **Mode 2 path**): 同じ tt-anicca@agentmail.to、 Dais 身分証で KYC、 payout = Stripe Connect → Dais JP 銀行。 do-once = signup 完了 + 1 案件参加可能 state。
- **C4-3** Vyro signup (= safety net): partner program、 招待制なら待機リスト登録。
- **C4-4** 各 platform で active campaign 1 つを参加: ClipAffiliates 1、 Whop 1。 brief を読んで AI/faceless OK 判定。
- **C4-5** §3 OSS pipeline 実装: 1 長尺 → 15 短尺 + JP 字幕、 ローカルで mp4 生成成功。
- **C4-6** do-once: 1 short clip を Anicca TikTok / IG / X (Skill 1 アカ) に実投稿、 live URL 取得、 各 platform に提出。
- **C4-7** **★ FIRST USDC SETTLE to `0x810f...` (= holy-grail proof) ★**: ClipAffiliates 案件で 1 件 payout 着金、 Basescan tx URL を ledger 行に書く。
- **C4-8** FIRST JPY SETTLE to Dais bank (= Mode 2 proof): Whop or Vyro で 1 件 payout、 銀行明細を ledger 行に書く。
- **C4-9** `claude -p` + launchd で daily loop 化、 `/goal "USDC settle to 0x810f > $0 within 30d"`。
- **C4-10** ledger schema 更新: `payout_mode` field 追加 (`usdc_self` / `jpy_bank`)、 unit test 拡張。
- **C4-11** STATE.md spine 作成 (read first / write last)。

## §9 Out of scope (= 別 spec)
- Clipping.net / Ecomrads (= 採用しない、 §1 参照)
- TikTok CRP / YouTube Shorts 自社 payout (= 二次利用 + AI 規約で実質ゼロ、 §1 参照)
- 切り抜き許諾交渉 (= JP 国内 channel との人間 negotiation、 別 skill)
- Anicca colony 内での USDC 相互援助 (= Type 2 spec `feedback_anicca_type1_type2_mutual_aid` の管轄、 ここでは Mode 1 wallet が hit する所まで)
