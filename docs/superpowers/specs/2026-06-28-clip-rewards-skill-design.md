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

## §3 Pipeline — long-form → 15-30 short clips (CONFIRMED 2026-06-28)

**入力 (= 3 sources、 §10 Path A/B/C 参照)**:
- Path A: ひろゆき / 加藤純一 等の公式許諾済 JP 配信者 (= 公開 YouTube から DL)
- Path B: EN public podcast (Lex Fridman / Joe Rogan / Huberman / Diary of a CEO)
- Path C: ClipAffiliates / Whop 案件 brief 配布素材

**Stack (= 各 step の repo + 役割)**:
```
yt-dlp                                          ← source DL ($0, MIT)
  ↓
SamurAIGPT/AI-Youtube-Shorts-Generator           ← ★ Opus Clip OSS 完全代替 ★
(--mode local; 4,036⭐, 2026-06-22 active)        URL → LLM virality-scored 9:16 clips
  ・faster-whisper (ASR)                        + hook + reason + JSON 出力
  ・LLM virality score (OpenAI/Gemini key)      
  ・ffmpeg crop 9:16                            
  ・OpenCV face-track                           
  ↓
m-bain/whisperX                                  ← ★ word-level karaoke 字幕 ★
(22,747⭐, BSD-2)                                70x realtime batched, diarization
  ↓
VOICEVOX 青山龍星                                 ← ★ 必須 ★ (繰り返しコンテンツ ban 回避)
(VOICEVOX_API_KEY 既設定)                        独自 JP narration で原本扱い化
  ↓
Remotion                                         ← hook overlay / brand 焼き込み / サムネ
(既存資産)                                       
  ↓
chatgpt-imagegen ($0)                            ← サムネ / アイキャッチ
  ↓
ffmpeg 合成                                       ← 出力 mp4 (9:16 + JP 字幕 + 龍星 narration)
  ↓
reelclaw                                         ← TikTok + IG + X に同一 clip ばらまき
```

**Repo URL (実在確認 + Firecrawl で README 読了)**:
- AI-Youtube-Shorts-Generator: https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator
- whisperX: https://github.com/m-bain/whisperx
- VOICEVOX key 場所: memory `reference_video_gen_stack_turbo_vimax_voicevox`

**Volume**: 1 長尺 (1-3h) → **15-30 短尺 / 日 / Path** = full-time クリッパー水準 (= ClipAffiliates blog "Full-time $3,000-10,000/月" の前提)。 3 Path 並走で 45-90 短尺 / 日 ceiling。

**NG repo (= 採用しない)**: `RayVentura/ShortGPT` (1.5年 push なし、 README 404、 stale) / `m1guelpf/yt-whisper` (2024-01 で停止) / `radamson/video-clipper`, `Speedy11CD/auto-clip-it`, `nicolas-dufour/whisper-clip`, `m1k1o/blive` (実在しない repo、 `gh repo view` で 404 を catch — memory `feedback_dont_clone_read_readme_and_setup` の再発防止)。

## §4 Account strategy

- ★ Skill 1 で作る Anicca TikTok/IG/X を **再利用** ★ (= 同じ AI/productivity niche、 視聴者 overlap、 立ち上げの遅延ゼロ)。 専用 clip アカウントは作らない。
- 各 clip post 仕様:
  - 9:16 mp4 + JP 焼き込み字幕 + hook overlay (= 最初 1.5 秒)
  - キャプション末尾 = `#PR ` + 案件指定 hashtag (Whop / ClipAffiliates brief 規約準拠)
  - BIO 引き続き Amazon Associates affiliate link (= Skill 1 と同居)

## §5 Viral pattern: EN 素材 → JP 字幕 (CONFIRMED 2026-06-28)

**逆方向 (= JP→EN) で成立を証明している success channel** (出典: [UserLocal](https://virtual-youtuber.userlocal.jp/office/kirinuki) / [kirari.io 切り抜き調査](https://www.kirari.io/blog/vtuber-clip-guide)):

| ch | 登録者 | パターン | URL |
|---|---|---|---|
| Sashimi Clips | 28.6万 | JP VTuber → EN 字幕、 word-by-word karaoke | YouTube 検索 |
| Cooksie | 37.5万 | JP ホロライブ → EN 字幕、 顔アップサムネ | 同上 |
| とりぷる/Tripl3 | 37.6万 | JP→EN バイリンガル字幕 同時表示 | 同上 |

→ TOP10 切り抜き ch 中 **4 ch が英語圏向け** ([UserLocal ランキング](https://virtual-youtuber.userlocal.jp/office/kirinuki)) = **逆方向 (EN→JP) の同パターンも成立する強い根拠**。

**Anicca が採用する viral 仕様** (= 共通テンプレ):
- 1-2 分 highlight (= SamurAIGPT が LLM score で抽出)
- 顔アップ サムネ (= chatgpt-imagegen)
- **word-by-word karaoke 字幕** (= whisperX で生成、 ffmpeg で焼き込み)
- **VOICEVOX 龍星 ナレーション** (★ 字幕+SE+BGM だけ では「繰り返しコンテンツ」 判定 = 収益化停止 ★、 §11 警告参照)
- hook = 最初 1.5 秒で結論を出す

**★ 法的注意 (= §11 と重複だがここでも明示) ★**:
- EN podcast (Lex Fridman / Joe Rogan / Huberman / Diary of a CEO) の JP 字幕版 = ★ 日本法に fair use 規定なし ★ ([kirari.io 明言](https://www.kirari.io/blog/vtuber-clip-guide#%E5%89%8D%E6%8F%90%E6%97%A5%E6%9C%AC%E3%81%AB%E3%83%95%E3%82%A7%E3%82%A2%E3%83%A6%E3%83%BC%E3%82%B9%E3%81%AF%E3%81%AA%E3%81%84) "日本の著作権法にフェアユースの規定はありません")
- → **Path B (= EN→JP) は YouTube に再投稿しない**、 ClipAffiliates / Whop 案件への提出 + Anicca own SNS (TikTok/IG/X) 配信 のみ
- → **YouTube に上げて稼ぐ ch は Path A (= JP 公式許諾) を使う**

## §6 OSS tooling stack (CONFIRMED 2026-06-28)

→ §3 と同内容。 stack = SamurAIGPT/AI-Youtube-Shorts-Generator (local mode) + whisperX + VOICEVOX 龍星 + Remotion + chatgpt-imagegen + ffmpeg。 全部 $0。

**なぜこの組合せか (1 文)**: AI-Youtube-Shorts-Generator が唯一 「商用 Opus Clip 完全代替 + 完全オフライン可 + active maintenance + Python lib として import 可」 を 4 要件全部満たす唯一の repo (= fork で他 6 候補 fall through 確認済)。 + whisperX で word-level karaoke、 + VOICEVOX 龍星 で 2025 YouTube 「繰り返しコンテンツ」 ban 回避 — Anicca 既存資産 (Remotion / chatgpt-imagegen / reelclaw / VOICEVOX_API_KEY) と完全 fit。

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
- **C4-12** **Path A**: ガジェット通信 MCN 申請 (= ひろゆき / 加藤純一 / 釈迦 公式切り抜き枠、 50:50 折半)。 [getnews.jp/mcn/kirinuki](https://getnews.jp/mcn/kirinuki) で application form fill (camofox)。 do-once = MCN 承認 = Anicca 用 channel が MCN 配下に紐付け済。
- **C4-13** **Path A**: にじさんじ 切り抜き事前登録 (= 2025-5 必須化に準拠)。 [nijisanji.jp/news/91e6vigs180e](https://www.nijisanji.jp/news/91e6vigs180e) の手順で channel を登録。 do-once = 登録番号取得。 ホロライブは個人 OK = 登録不要だが ★ AI 音声抽出 は禁止 ★ 明記。
- **C4-14** **Path A 用 dedicated YouTube channel 開設**: niche = JP 配信者切り抜き (= 既存 Anicca AI/productivity ch とは分離、 視聴者層が違う)。 AgentMail + SMS phone + CloakBrowser。 1000subs+4000h で YPP → AdSense → JP 銀行 = Path A の Mode 2 入口。
- **C4-15** **VOICEVOX 龍星 を §3 pipeline に必須 integrate**: 全 clip に独自ナレーション挿入 (script = LLM が要約 → VOICEVOX 合成 → ffmpeg で元音声と mix or 全置換)。 これが無いと 2025 YouTube 「繰り返しコンテンツ」 ban で収益化停止 (= がるぜん 10万人 ch 実例、 §11)。 unit test = 「ナレーション無し clip = pipeline reject」。

## §9 Out of scope (= 別 spec)
- Clipping.net / Ecomrads (= 採用しない、 §1 参照)
- TikTok CRP / YouTube Shorts 自社 payout (= 二次利用 + AI 規約で実質ゼロ、 §1 参照)
- 個別配信者との直接許諾 negotiation (= 別 skill。 MCN application は §10 Path A で含む)
- Anicca colony 内での USDC 相互援助 (= Type 2 spec `feedback_anicca_type1_type2_mutual_aid` の管轄、 ここでは Mode 1 wallet が hit する所まで)

## §10 三層並走戦略 (= Path A / B / C、 同 stack 1 つで 3 収益源 cover)

★ 全 Path が §3 の同 OSS stack を使う。 素材 source と payout 先だけ swap ★ = 開発工数 1 倍で 3 layer 収益。

### Path A — JP 公式許諾切り抜き (= 確実な ¥、 月実勢 10-20万)

| 配信者 | 許諾 | 収益分配 | 出典 |
|---|---|---|---|
| **ひろゆき** | 公式 OK | **50:50 折半** (ガジェット通信 MCN) | [getnews.jp/mcn/kirinuki](https://getnews.jp/mcn/kirinuki) |
| **加藤純一** | 公式 OK | 50:50 折半 | [note.com/chask](https://note.com/chask/n/nb79c5164d07a) |
| **釈迦** | 公式 OK (条件付) | — | [bloomeria.jp](https://bloomeria.jp/blog/clip-video-monetization-guide) |
| **ホロライブ (Cover)** | 個人 OK | 個人収益化 OK、 ★ 法人 NG ★ + ★ AI 音声抽出 NG ★ | [hololivepro.com/terms](https://hololivepro.com/terms/) |
| **にじさんじ (ANYCOLOR)** | 個人 OK | ★ 2025-5 から事前登録必須 ★ | [nijisanji.jp/news/91e6vigs180e](https://www.nijisanji.jp/news/91e6vigs180e) |

**実勢年収 (SocialBlade ベース)** ([note.com/chask](https://note.com/chask/n/nb79c5164d07a)):
- 切り抜き ch 5万登録 = **年 763万 〜 1,500万円**
- ひろゆき切り抜き 28万 = **年 800万 〜 1,600万円 (折半後)**
- 加藤純一切り抜き 47万 = **年 800万 〜 1,600万円 (折半後)**

★ 月収 60万円超のクリッパーは「多い」レベル ★ = サラリーマン平均 (450万/年) を余裕で超える生態系が実在。

payout: YouTube YPP → AdSense → JP 銀行 (= Mode 2、 50:50 折半は MCN 経由で自動配分)。

### Path B — EN podcast → JP 字幕 (= 青い海、 ClipAffiliates / Whop 受け)

- 素材: Lex Fridman / Joe Rogan / Huberman / Diary of a CEO (公開 YouTube)
- 翻訳: AI 完結 (whisperX + LLM)
- ★ YouTube 投稿 NG ★ (= JP 法 fair use 不可)
- 投稿先 = Anicca own SNS (TikTok / IG / X) + ClipAffiliates / Whop 案件提出 のみ
- payout: ClipAffiliates USDC (Mode 1) + Whop Stripe Connect (Mode 2)

### Path C — Whop / ClipAffiliates 案件素材 (= 既調査済、 §1 参照)

- 素材: 案件 brief 配布素材 (= ブランド許諾済)
- 投稿先 = 案件指定 SNS
- payout: ClipAffiliates USDC (Mode 1 主) + Whop Stripe Connect (Mode 2 副)
- 法的 = ブランドが配布した素材 → 規約準拠で完全 safe

→ **同 stack + 投稿アカ重複 + 素材切替だけ** で 3 layer 並走。

## §11 ★ CRITICAL WARNINGS (= 違反 → 即収益化停止 / BAN) ★

1. **VOICEVOX ナレーション必須** — YouTube 「繰り返しコンテンツ」 判定で **ホロライブ切り抜き「がるぜん」 (10万人 ch) が収益化停止** ([kirari.io](https://www.kirari.io/blog/vtuber-clip-guide))。 「字幕 + SE + BGM 追加だけ」 では不可。 ★ 独自ナレーション (VOICEVOX 龍星) を全 clip に挿入 ★。
2. **中田敦彦 切り抜き 全面 NG** — **2024-12 / 2025-02 禁止に転換、 9割動画一時非公開** ([livedoor news](https://news.livedoor.com/topics/detail/28075577/))。 ★ 候補から除外 ★。
3. **にじさんじ 事前登録必須** — **2025-5 から** ([nijisanji.jp/news/91e6vigs180e](https://www.nijisanji.jp/news/91e6vigs180e))。 未登録投稿 = 規約違反。
4. **ホロライブ AI 音声抽出 NG** — 規約明記 ([hololivepro.com/terms](https://hololivepro.com/terms/))。 音声 → 文字起こしは OK、 ★ AI で音声再合成 → 再投稿 は NG ★。
5. **EN podcast の JP 投稿は YouTube 不可** — JP 法に fair use 規定なし ([kirari.io](https://www.kirari.io/blog/vtuber-clip-guide))。 ★ Path B は ClipAffiliates / Whop / Anicca own SNS のみ ★。
6. **ボット視聴 / fake metric = 全 platform 即 BAN** — [Whop guidelines](https://whop.com/guidelines/) verbatim "Platform manipulation"。 view ブーストは絶対やらない、 投稿の自動化のみ。
7. **#PR / 「広告」 表記必須** — 景表法 (JP) + FTC (US)、 affiliate / 案件 clip 全部対象。
