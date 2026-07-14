# Cold-start 自己改善 bible（2026-07-14、一次情報で確定）

無シグナル（views 30-300）から content をどう改善するか。**全 marketing loop(clip/video/slideshow) + 一般に全 earn loop の L3(SELF-IMPROVE)の正本。** spec INV-5(外部学習>内部学習)の具体化。

## 結論（Dais 仮説=確定）
cold-start は「自分の指標から学ぶ」でなく「**勝者を研究・模倣→逸脱率を上げる**」が業界コンセンサス。下敷き = **守破離(Shu-Ha-Ri) / Steal Like an Artist / Imitate-then-Innovate**（Forbes）。

## 3-phase ステートマシン（loop に実装する判定条件）
```
 Phase1 IMITATE（投稿0-10本 or 累計views < platform テストプール閾値。TikTok目安500）
   ├ 上位3-5アカを niche で探す
   ├ その ★outlier★ 投稿を選ぶ = 自平均の 3-10倍 跳ねた投稿（OutlierKit/vidIQ 定義）
   ├ hook/構造/字幕/尺/投稿時間を transcribe・解析
   └ 高忠実度で copy（型を playbook に。自分の metrics でなく winner 基準で iterate）
        ▼ traction 出た
 Phase2 VALIDATE BATCH（10本刻み・2週間ごと）
   └ retention 60%+ を基準に pivot（型を捨てる）or double-down（型を強化）
        ▼ 自分の投稿が自平均×3倍の outlier を出した
 Phase3 SELF-OPTIMIZE（内部学習に切替）
   └ その勝った自分の投稿を新たな模倣ソースに。$/post・retention で A/B 内部最適化
```
★切替点は単一 view 数でなく「自分の outlier(自平均×3-10倍)が出たか」。それまでは母数不足＝外部参照が正しい。★

## レバー（重要度順、複数ソース収斂）
1. **最初の3秒 hook**（完了率=ランキングの 40-50%。最大要因）
2. パターン割り込み/視覚刺激（ハードカット/ズーム/不一致で好奇心）
3. サムネ/タイトル packaging（MrBeast: 本編より先に50案、1000サムネ×輝度と再生の相関）
4. 中盤 retention move（~7s の離脱防止）
5. script 構造/尺（skeleton 化して論理構造だけ抽出）
6. 投稿頻度/CTA（下位）

## cadence
- 量が先・質は後（3投稿/日 >> 3投稿/月。Hormozi volume）。
- hook A/B: 動画毎に 3案 or 3-4本毎に新 hook format 1つ。
- 判定: 10本バッチ・2週間・retention 60% で pivot/double-down。
- 期間: 60-90日 consistent posting してから benchmark 比較が意味を持つ。

## 実例（medium 90日 faceless IG）
Day30: follower 1,200 / views 50-200（完全ノイズ）→ Day45-60 で hook の心理角度を変えたのが転機 → Day90: follower 18,700 / 最高 42万 views。★hook が転機★。

## tools / repo（copy 元）
| repo/tool | ★ | 用途 |
|---|---|---|
| shixinzhang/tiktok-viral-hooks | 8 | 日次でバイラル動画を transcript→hook パターン命名→2文テンプレ。「imitate now」設計 |
| jakeolschewski/social-media-hooks-database | 2 | 200+ hook フォーミュラ DB（platform/niche/心理トリガー別）|
| drawrowfly/tiktok-scraper / Douyin_TikTok_Download_API(18.8k) | — | 動画/メタ DL 基盤 |
| OutlierKit / Shortimize / vidIQ Outliers（SaaS）| — | outlier(自平均×3-10倍)抽出アルゴ |

一気通貫 OSS は薄い（tiktok-viral-hooks が唯一級、★一桁）→ この bible を自前 loop に実装するのが差別化。

## loop への実装（clip_pass.sh LEARN step に埋め込み済）
LEARN step が: reflection 読 → 上位アカの outlier を scout・transcribe → 型を playbook.json に(tier:core) → PRODUCE がそれで作る。REFLECT が「自分の outlier 出たか」で phase 判定。

## 出典
d3mfollow.com(TikTok 200-500 test) / go-viral.app(3秒hook) / virvid.ai(10本60%) / medium.com/@vireuoess(90日実数) / fluxnote.io(90日plan) / outlierkit.com + vidiq.com(outlier定義) / github shixinzhang/tiktok-viral-hooks / winsomemarketing.com(量>質) / forbes.com(imitate-then-innovate) / danielscrivner.com(MrBeast)
