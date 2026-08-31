# AI アバター動画レンダラーのコスト比較

**用途**: AI 僧侶アバター動画で電子書籍を売る事業。動画は本の販売導線（動画の上に e-book リンク）。日本語版が「water monk factory」、英語版が別ファクトリー。
**調査日**: 2026-08-31
**目的**: 一番安く回せる構成を決める。

---

## 0. 結論（先に読む）

**月に作る動画の分数で答えが変わる。**

| 月の生成量 | 最適 | 月額 |
|---|---|---|
| 〜10分 | HeyGen 無料枠 | $0（3本/月・各1分・720p まで） |
| 10分〜数時間 | **HeyGen Creator の標準アバター** | **$24/月（年払い）** |
| 大量・自動化 | MiniMax H3 API | $0.08/秒 = $4.8/分 |
| 実質無料にしたい | OmniAvatar セルフホスト | $0 だが GPU が要る（下記） |

**★ HeyGen で一番効くのは「アバターの種類を変える」こと。★** 同じ $24/月のプランでも:

- **Avatar V（高品質）: 約20クレジット/分** → 200クレジットで **10分**
- **標準アバター: 約1クレジット/分** → 200クレジットで **約200分**

**20倍の差**。僧侶アバターが標準アバターで足りるなら、既に払っている HeyGen だけで月200分。追加費用ゼロ。まずここを確認するのが最優先。

---

## 1. 各選択肢の実測値

### HeyGen（現在課金中）

出典: [aivideopicks.com](https://aivideopicks.com/posts/heygen-pricing-2026.html)（heygen.com/pricing を 2026-04-24 取得）

| プラン | 年払い | 月払い | 内容 |
|---|---|---|---|
| Free | $0 | $0 | 3本/月、1分まで、720p、デジタルツイン1体 |
| **Creator** | **$24/月** | $29/月 | 無制限本数、30分まで、1080p、**200クレジット**、写真アバター無制限 |
| Pro | $41/月 | $49/月 | 4K まで、**2,000クレジット** |
| Business | $119/月+$20/席 | $149/月 | 60分まで、4K、1,000クレジット（共有） |

**クレジットの消費レート（ここが本質）**:
- Avatar V / IV: **約20クレジット/分**
- 標準アバター: **約1クレジット/分**

**注意**: クレジットは翌月に繰り越されない。使わない月は捨てることになる。追加パックは300クレジット $15（月額購読者）。

**Pro に上げる価値**: 2,000クレジットは Avatar V で100分、標準で2,000分。$41/月。Creator との差 $17/月で10倍のクレジット。

### MiniMax H3 API

出典: [atlascloud.ai](https://www.atlascloud.ai/blog/tips/minimax-h3-api-pricing)、[usagepricing.com](https://www.usagepricing.com/blueprint/minimax)

| 解像度 | 単価 | 1分あたり |
|---|---|---|
| 768P | **$0.08/秒** | $4.80 |
| 2K | $0.13/秒 | $7.80 |
| 768P→2K アップグレード | +$0.05/秒 | — |

**768P の base weights は公開されている**（セルフホスト可能）。ただし下の OmniAvatar と同じ GPU の壁がある。

制約: 同時実行は2または15（プラン依存）、アップロード64MB上限。

**HeyGen との比較**: 月10分なら MiniMax $48 vs HeyGen Creator $24。**月20分を超えたあたりから MiniMax の方が高くなる**。API 自動化の価値と引き換え。

### オープンソース実装の比較（GitHub 実測、2026-08-31）

| repo | stars | 必要 VRAM | 備考 |
|---|---|---|---|
| **antgroup/echomimic_v3** | 1.0k | **12GB** | AAAI 2026。「1.3B Parameters are All You Need」。14B の OmniAvatar より10分の1のパラメータ。`partial_video_length` を 81/65 に下げるとさらに削減可。Gradio UI あり。テスト済み GPU: A100(80G) / RTX4090D(24G) / V100(16G) |
| TMElyralab/MuseTalk | 6.5k | — | リアルタイム。**checkpoint の商用利用条件が未確認**（`renderer_eval.py` の blocker 理由がこれ） |
| fudan-generative-vision/hallo2 | 3.7k | A100 前提 | ICLR 2025。長尺・高解像度だが **A100 でしかテストされていない**。重すぎる |
| Rudrabha/Wav2Lip | — | 軽量 | **品質が実用に耐えない（Dais 実使用の判断 2026-08-31）。候補から除外** |
| Omni-Avatar/OmniAvatar | — | 8〜36GB | 下記 |

**現実解は EchoMimicV3。** 12GB VRAM なら RTX 3090/4090 の安いレンタルで足りる。

### レンタル GPU の相場（2026-08-31 実測）

出典: [synpixcloud.com](https://www.synpixcloud.com/blog/vast-ai-rtx-4090-price)

| 提供元 | RTX 4090 | 形態 |
|---|---|---|
| Vast.ai | **$0.29〜/時**（マーケット変動制） | ホストごとに価格・信頼性・中断可否が違う。起動前に実オファーを確認する必要あり |
| 固定レート系 | $0.39/時〜 | キューなし・中断なし |

**月10分の動画を作る場合の試算**: 生成が実時間の10倍かかっても100分 = 約1.7時間 → **$0.50〜0.70/月**。HeyGen $24/月より圧倒的に安い。ただし環境構築と運用の手間が乗る。

### OmniAvatar（オープンソース・無料）

出典: [github.com/Omni-Avatar/OmniAvatar](https://github.com/Omni-Avatar/OmniAvatar) の README

公式の VRAM 表:

| モデル | GPU数 | `num_persistent_param_in_dit` | 速度 | **必要 VRAM** |
|---|---|---|---|---|
| 14B | 1 | 無制限 | 16.0s/it | 36GB |
| 14B | 1 | 7B | 19.4s/it | 21GB |
| 14B | 1 | **0** | 22.1s/it | **8GB** |
| 14B | 4 (FSDP) | 無制限 | 4.8s/it | 14.3GB×4 |

**8GB まで落とせる**。速度は 22.1s/it まで落ちるが動く。

### なぜ今 Mac Mini で動かないか

**Mac Mini は Apple M4 / メモリ16GB で、NVIDIA GPU が無い**（実測: `system_profiler` で確認）。OmniAvatar は PyTorch + `flash_attn` 前提で、`torchrun --nproc_per_node` の分散実行を使う。

これが `renderer_eval.py` に記録されている判定の正体:

```python
blockers = {
  "omniavatar-monk": "no durable free execution artifact or local CUDA runtime",
  "musetalk": "checkpoint commercial terms and local GPU capacity not verified",
  "longcat-video-avatar": "official path requires multi-GPU capacity unavailable locally",
}
```

**3つとも「ローカルに GPU が無い」が理由**。モデルが悪いのではなく、動かす場所が無い。

### Google Colab 無料枠で OmniAvatar を回せるか

出典: [joshthompson.co.uk](https://joshthompson.co.uk/ai/google-colab-2026-guide-free-compute-automations-pro-tips/)、Google Colab 公式 FAQ

| 項目 | 実態 |
|---|---|
| 無料 GPU 時間 | **公表されていない**。動的に変わる |
| GPU は保証されるか | **されない**。「GPU など高価なリソースは無料枠で厳しく制限される」 |
| 1セッションの最大 | **12時間**（"at most"、これは上限であって最低保証ではない） |
| 途中終了 | アイドル・高需要・大量消費履歴があると早期終了 |

**結論**: 8GB VRAM 版なら T4（16GB）で技術的には動く。ただし **GPU が割り当てられる保証が無く、セッションが予告なく切れる**。毎日自動で動画を出す本番用途には向かない。手動で試作する分には使える。

---

## 2. 推奨する順序

1. **今すぐ**: HeyGen で標準アバターの品質を確認する。僧侶アバターが標準で成立するなら、$24/月のまま月200分。**これで足りるなら他は不要。**
2. **標準では品質が足りない場合**: HeyGen Pro $41/月（Avatar V で月100分）。Creator との差額 $17 で10倍。
3. **API で完全自動化したい場合**: MiniMax H3 768P $0.08/秒。月20分未満なら HeyGen より安い。
4. **完全無料を狙う場合**: レンタル GPU（RunPod 等）で OmniAvatar。8GB VRAM 版なら安いインスタンスで足りる。Colab 無料枠は本番運用には不安定すぎる。

## 3. 手元に既にある資産（2026-08-31 実測）

`~/anicca-monk-factory/personas.json` が正本として全部持っていた:

| 項目 | 英語 | 日本語 |
|---|---|---|
| ハンドル | `@monk_anicca` | `@obou_anicca` |
| factory skill | `yangmun-monk-factory` | `watercolor-monk-factory` |
| 商品リンク | `aniccaai.com/monk` | `aniccaai.com/achan` |
| 音声 | HeyGen voice `828b59f8...` | OpenAI `tts-1-hd` / onyx |
| HeyGen avatar_id | `5a52533987c74ad4aadedfa881ce4554` | — |
| 投稿枠 | 19:30 / 12:30 / 08:30 | — |

ElevenLabs も代替経路として記録されているが、`_alt_path` に「**HeyGen Premium Credits Pack がないと `audio_asset_id` 経路が使えない**」と注記されている。

**投稿 loop も既に3本ある。ただし実質動いていない**（`mr-bot-anicca-obou-instagram` と `-main-tiktok` は `runs = 0`、`-en-slideshow-tiktok` は `runs = 1` の exit=1 でログすら無い）。作り直すのではなく、動かない原因を特定するのが先。

## 4. 判断に必要でまだ持っていない情報

- HeyGen の現在のプラン（Creator か Pro か）と、今月のクレジット残。**`~/.local/share/anicca/credentials.json` に HeyGen のエントリが無い**ので、認証情報の SSOT にまず登録する必要がある
- 僧侶アバターが標準アバターで成立するか（実際に1本作って比べる）
- 月に何分作るのか（これが決まらないと最適解が決まらない）
