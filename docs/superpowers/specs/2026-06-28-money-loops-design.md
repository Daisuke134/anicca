# Money Loops Design — earn > spend, no-human (2026-06-28)

★★★ SUPERSEDED for ARCHITECTURE by `~/anicca/docs/superpowers/specs/2026-06-28-anicca-master-architecture-one-repo-two-modes.md` 2026-06-28. ★★★
This spec proposed Monk Factory → Ebook Funnel (= JP note paid articles + EN Payhip PDF). Dais clarified
2026-06-28 that the ebook funnel relies on his specific note / Substack accounts and is NOT replicable
for the OSS repo where every Claude install must start from zero with only the user's Claude sub. The
LOOP MECHANICS (cost-$0 production, video → DM → email → product, ban-avoid via varied structure) are
still useful but applied per-install (= each user's own note / Substack / Payhip), not Dais's accounts.
The chosen first earn rail is now Amazon Associates affiliate (W1–W8 in three-earn-skills-loops-design.md,
also superseded for architecture, content kept). Kept here as the failure-mode lesson on per-install
credentials.

研究4本(faceless短尺収益 / ebook funnel JP+EN / Veo黒字化 / 自動投稿ループ)を実数値+ソースで実施。本specはその統合と、最初に作る利益ループの設計。

## 0. 核心の真実（全ソース収束）

1. **生成は解決済み&無料**。MoneyPrinterTurbo(93.7k★)+VOICEVOX(無料)+ffmpeg で動画コストは実質$0。moat は生成ではなく **①配信(ban回避) ②マネタイズ**。
2. **広告収益(ad-revenue)は罠**。YouTube 2025/7「inauthentic content」でテンプレ濫造=チャンネルごと demonetize。TikTok Creator Rewards もAI無価値テンプレ除外。Shorts RPM は $30-100/1M(雀の涙)。閾値到達まで数ヶ月$0。
3. **確実な黒字 = ①デジタル製品(ebook/journal)funnel ②B2Bサービス ③ループ自体を売る**。広告ではなく**製品を売る**ので demonetization を回避できる(=views→email→販売、YPP不要)。

## 1. ツール別 money model（earn vs spend）

| ツール | コスト | 稼ぎ方(黒字の道) | earn>spend |
|---|---|---|---|
| **MoneyPrinterTurbo / monk-factory** | ~$0/本 | faceless mindfulness動画→comment-to-DM→email→**ebook/journal販売**(EN $7-27 Payhip/Stan + note ¥1,800 + ¥500/月 membership + KDP $4.99) | ◎ コスト$0なので1販売=純利益 |
| **ViMax (Veo)** | $0.8-3.2/8sクリップ(fast/std)、75%失敗で実$8-12/usable | **B2Bサービス**(広告/商品/不動産動画 $50-1,500/本)。faceless広告収益は負マージンの罠 | ◎ 粗利80-95% だが要クライアント |
| **Agent-Reach** | $0 | 直接は稼がない。**ループのトレンド/source入力**として組込む | — (部品) |
| **VOICEVOX 青山龍星** | $0 | コスト削減(JP音声無料化)。revenueではなくmargin拡大 | — (コスト↓) |

## 2. 採用する最初の利益ループ = 「Monk Factory → Ebook Funnel」

理由: **①コスト$0(=earn>spend保証) ②最も no-human ③既存資産(monk-factory pipeline + VOICEVOX)を再利用 ④製品販売なのでdemonetization回避**。ViMaxサービスは高収益だがクライアント獲得が要る=フェーズ2。

### アーキテクチャ（no-human ループ）
```
[トレンド/テーマ] DeepSeek (Agent-Reachでsource可)
   → [台本] DeepSeek が "value-add" な実用台本 (テンプレ禁止、毎回構造を変える=ban回避)
   → [動画] monk-factory 無料stack: 静止画/Kling i2v + VOICEVOX(JP青山龍星)/ElevenLabs(EN) + ffmpeg karaoke字幕、≥60秒
   → [投稿] Postiz(self-host無料) / upload-post(無料10/月)。★MEDIA_UPLOAD方式(アプリ内でtrending音源仕上げ)=reach最大、DIRECT_POSTは reach減★
   → [funnel] 概要欄/コメント固定 → comment-to-DM(CTR 12-18% = bio-linkの4-6倍) → email捕捉
   → [製品] DeepSeekが生成した ebook/journal を販売:
        EN: $7-27 PDF (Payhip 5%/Stan) + $4.99 KDP (70%帯 $2.99-9.99)
        JP: note 有料記事 ¥1,800(実用how-to framing) + ¥500/月マガジン + KDP JP
   → [計測] 販売/views を記録 → 次テーマへ
```

### ユニットエコノミクス（実数値）
- コスト/本: ~$0(VOICEVOX無料+Kling cached+ffmpeg) + DeepSeek数円。
- 収益: ebook 1販売 = $5-25 純利益(コスト$0)。faceless wellness の実例: ReciMe 113M views $1M/月、Headspace は faceless TikTokで$200M+ブランド化。
- 変換: views→DM click 12-18% → landing 0.7-4.5% 販売。製品AOV $15-27。
- 早期KDP単体は$50-500/月。**チャンネル供給funnelで$1k+/月へ**。
- JP: note top1000 平均¥1,515万/年、有料記事+26.8%/membership+81.3% YoY、新規参入可。

### ban回避(必須制約)
- ≥60秒動画(TikTok Rewards対象)、毎回 hook/構造/サムネ変える("10本テスト"で見分けつかない=危険)、upload-flooding禁止、1チャンネル1ニッチ、複数チャンネルで AdSense ID共有禁止。
- ★製品販売モデルなので広告demonetizationの影響は限定的(views→emailが回ればよい)★。

## 3. フェーズ2 = ViMax B2B動画サービス
Veo fast/lite + image-to-video でコスト$1-80/本 → $50-1,500で販売(広告/商品/不動産/UGC)。粗利80-95%。要: ポートフォリオ + 営業(cold email skill保有)。autonomousではないので後回し。

## 4. マイルストーン（build順）
1. **monk-factory 無料stack復活**: HeyGen除去→静止画/Kling i2v + VOICEVOX/ElevenLabs + ffmpeg字幕。1本 no-human生成 verify。
2. **最初のebook製品をDeepSeekで生成**(EN mindfulness journal PDF + JP実用瞑想how-to) → Payhip/note に出品。
3. **funnel配線**: 動画概要/コメント → product link + email捕捉(comment-to-DM)。
4. **投稿自動化**: Postiz/upload-post で TikTok/YT/IG に MEDIA_UPLOAD。1本実投稿 verify(POST_ID)。
5. **ループcron化**: 1日1-2本、テーマfresh生成、販売記録。earn>spend を実測。

## ソース（全実数値はサブ調査に記録、主要URL）
- TikTok Rewards RPM $0.40-6/1k: flowshorts.app, focalml.com
- YouTube inauthentic policy: support.google.com/youtube/answer/1311392, tubebuddy.com
- Veo価格 $0.10-0.40/s: ai.google.dev/gemini-api/docs/pricing
- ebook funnel: hustlemarketers.com(faceless wellness), creatorflow.so(CTR), note.jp(JP統計), kdp.amazon
- 自動投稿: upload-post.com, blotato.com, github.com/gitroomhq/postiz-app(32.4k★)

---
# ADDENDUM (2026-06-28) — Skill Roster（確定: 4 skills, ViMax=受注専用）

手持ちツールを「稼ぐ skill」に落とし込んだ確定版。各 skill は ①`~/.openclaw/skills/`(本番cron) ②`~/.claude/skills/`(Claude Code から手動) の両方に install(dual-install、HyperFrames方式)。

| # | skill | tools | 稼ぎ方 | cost | autonomous | priority |
|---|---|---|---|---|---|---|
| 1 | **anicca-monk-earn** | monk-factory改 + VOICEVOX + HyperFrames + ElevenLabs/DeepSeek | ebook funnel + 再生報酬 | $0/本 | ◎ cron | NOW |
| 2 | **ebook-factory** | DeepSeek + Payhip/note/KDP | 製品販売=純利益(skill1の集金先) | $0 | ◎ | NOW |
| 3 | faceless-explainer-earn | HyperFrames /faceless-explainer | 高RPMニッチ横展開・複数ch | $0 | ◎ | next |
| 4 | vimax-video-service | ViMax+Veo | 広告/商品動画 受注 $50-1500 | 有料 | △客要 | later |

★ViMax決定: 日次無料ループに入れない(faceless Veo=赤字の罠)。Skill4の受注B2Bサービス専用。日次で勝手に課金しない。
★Skill 1+2 のペアだけで完結した money machine。動画は無料の客寄せ、稼ぐのはebook。動画コスト$0 → ebook1冊でも黒字 = earn>spend保証。
★monk改造の中身 = 死んだHeyGen Avatar IV を「静止画/Kling i2v + VOICEVOX(JP)/ElevenLabs(EN) + HyperFrames字幕」に差し替え。account/投稿経路/skill骨格は流用。

---
# EXECUTION TASK LIST (SDD, one-by-one) — 2026-06-28

## 確定した事実（実調査済み）
- monk-factory の **死んでる箇所 = HeyGen の `render-submit.sh`+`render-download.sh` のみ**（run-daily.sh L51-63）。
- 生きてる: `pick-next-script.sh`(台本ローテ) / whisper品質ゲート / `burn-captions.sh` / `gen-caption.sh` / `post-tiktok.sh`(browser) / `post-ig-postiz.sh`(Postiz) / mark / report。
- watercolor の Kling cache も消失(0本)。→ 両factory とも **視覚生成だけ**が穴。
- 置換 = `render-free.sh`($SCRIPT+lang → TTS[ElevenLabs EN/VOICEVOX JP] → 僧侶静止画+ffmpeg Ken Burns → $OUT/$ID.mp4)。drop-in で run-daily が丸ごと蘇る。
- 既存アカウント: EN/JP TikTok+IG (`@monk_anicca`等)。投稿経路: Postiz(`POSTIZ_TIKTOK_INTEGRATION_ID`) + TikTok Studio。

## SKILL 1 — anicca-monk-earn（復活+投稿）★最優先
- [ ] **S1-1** `render-free.sh` を作る: 台本+lang → TTS(ElevenLabs EN/VOICEVOX JP) → 僧侶静止画(既存renders_v3 or 生成)+ffmpeg Ken Burns(音声尺に合わせる) → mux → `$OUT/$ID.mp4`。検証: ffprobe で audio+video、dur≈音声。
- [ ] **S1-2** render-free.sh 単体テスト(EN台本1本)→ mp4。検証: frame+音声。
- [ ] **S1-3** run-daily.sh に配線(L51-63 を render-free.sh に置換、whisper品質ゲート/burn-captions/投稿はそのまま)。
- [ ] **S1-4** run-daily.sh を burn-captions まで E2E(投稿前で停止)→ captioned mp4 検証。
- [ ] **S1-5** ★実投稿★: post-tiktok.sh + post-ig-postiz.sh → TIKTOK_URL / IG reel URL 取得(=「本当に投稿できる」POST_ID検証)。
- [ ] **S1-6** funnel: gen-caption.sh の bio/概要に ebook リンク差込。
- [ ] **S1-7** dual-install → `~/.claude/skills/anicca-monk-earn`(私=Claude Code からも叩ける)。
- [ ] **S1-8** cron 設置(jobs.json, 日次 EN+JP)。1回 fire して実 POST_ID 確認。

## SKILL 2 — ebook-factory（売り物=収益）
- [ ] **S2-1** DeepSeek で EN ebook 全10章フル生成(現状ch1のみ)。
- [ ] **S2-2** md→PDF(整形)。
- [ ] **S2-3** Payhip 出品 EN $9 → product URL 取得。
- [ ] **S2-4** JP ebook(note ¥1,800 実用framing)→ note URL。

## SKILL 3/4（後）
- faceless-explainer-earn(高RPMニッチ横展開) / vimax-video-service(受注B2B)。

## ONGOING
- disk hygiene(>10GB維持)。

---
# CRITERIA 確定版 (2026-06-28) — anicca-monk-earn = end-to-end self-funding skill

目的: ★ 各 Anicca(Claude) が「自分を動かすコスト」より多く稼ぐ = self-funding ★。human-funded AI → 黒字 → その黒字が次の self-funded AI を生む(colony)。

## 全ノブ確定
| ノブ | 確定値 | 理由 |
|---|---|---|
| **台本** | ★毎回 DeepSeek でフレッシュ生成★ (bank rotation 廃止) | 「scripts is everything」。毎回 構造/hook を変える = YouTube/TikTok の inauthentic/テンプレ濫造 demonetize 回避 (HARD: 0.16 ROTATION廃止と整合)。Agent-Reach でトレンド注入可 |
| **音声 EN** | 既定 edge-tts(無料) / 任意 ElevenLabs(高品質, ~$0.1/本) | $0でearn>spend保証。retentionが要るなら ElevenLabs 昇格(売上が賄う) |
| **音声 JP** | VOICEVOX 青山龍星(無料) | 既配線・完全無料 |
| **映像** | photoreal 僧侶 still + Ken Burns (将来 fresh生成で多様化) | $0・faceless |
| **字幕** | whisper(base)→ASS TikTok風 焼込 | $0・retention必須 |
| **尺** | ≥60秒 | TikTok Creator Rewards 対象 |
| **投稿** | 3回/日 (07/12/19), MEDIA_UPLOAD方式 | reach最大・upload-flooding回避の上限 |
| **配信先** | TikTok + IG Reels (EN: anicca_en/monk_anicca, JP別) | 既存アカウント流用 |
| **集金** | caption/bio に ebook link ($7-27) + comment→DM | 製品販売=純利益(動画$0) |
| **記録** | views/sales → dashboard.json | 翌runが別角度を選ぶ |

## 新スクリプト(要ビルド)
- `gen-script.sh` = DeepSeek でフレッシュ台本生成(best-practice prompt, 毎回別hook/構造)。pick-next-script.sh(bank rotation) を置換。
- `gen-caption.sh` = DeepSeek で description + hook + ebook link 生成(再建要、gutされてた)。

## self-funding 数式
1本コスト ≒ $0 (edge-tts/VOICEVOX + still + whisper + ffmpeg、全ローカル無料) + DeepSeek 数円。
3本/日 × 30日 = 90本/月 ≒ $0。ebook 1冊販売($5-25純益)で黒字。再生報酬は後乗せ。
→ ★ skill の稼働コスト < 売上 = self-funding 成立。余剰が次instanceの燃料 ★。

---
# VERIFICATION GATE (2026-06-28) — slop を投稿しない（VCSDD式 maker≠checker）

「scripts is everything」かつ「slop投稿は罪」なので、★投稿の前に2段の関門★を置く。maker(生成) ≠ checker(検証) を別コンテキストで。★ここに余ってる Sonnet 枠を使う(claude -p = adversary)★ = 賢い使い道(bash実行ではなく judgment)。

## GATE 1 — SCRIPT GATE（gen-script 直後、render 前）
checker = `claude -p` Sonnet（fresh context, maker と別）。binary PASS/FAIL:
- 独自性: 直近N本(ledger)と構造/hook/テーマが被ってない（dedup）
- hook: 最初3秒で掴む best-practice か
- 構造: 毎回違うか（テンプレ濫造=ban → FAIL）
- ★禁止: 医療/治療 claim（TikTok shadowban/72h shop-ban リスク）→ 即FAIL★
- ブランド: Anicca の無常/瞑想に忠実
FAIL → gen-script を別角度で再生成（最大3回ループ）→ それでもFAILなら skip(投稿しない)。

## GATE 2 — VIDEO GATE（render+caption 後、post 前）
### 2a 決定論(deterministic, bash):
- 尺 ≥60秒 / video stream有 / audio stream有 / 字幕cue ≥10 / ffprobe再生OK / MD5 が前回と不一致(重複防止)
### 2b ビジョン検査(claude -p vision、3フレーム抽出):
- 僧侶が映ってる・破綻なし / 字幕が読める・画面内 / アーティファクト無し → PASS/FAIL
どちらか FAIL → 投稿せず再render or skip。★FAIL を post に通さない★。

## 通過後 = NO-MOCK E2E（HARD 0.31）
post → 実 POST_ID/URL 取得 → 取れなければ exit 1。これが最終の deterministic 検証。

## ループ全体（VCSDD と同型）
```
gen-script(maker) → GATE1 Sonnet adversary(checker) ──FAIL──► 再生成(≤3)
        │PASS
render+caption(maker) → GATE2 determ + vision(checker) ──FAIL──► 再render/skip
        │PASS
post → POST_ID 取得(no-mock E2E) → 記録(ledger)
```
★ maker ≠ checker、binary PASS/FAIL、loop til pass、最後に実投稿E2E ★ = VCSDD の 4-D 収束を投稿パイプラインに適用。
