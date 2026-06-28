# Money Loops Design — earn > spend, no-human (2026-06-28)

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
