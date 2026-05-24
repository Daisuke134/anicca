# Ogiri → Flip 自己改善スペック (v1, 2026-05-17)

固定お題: 「これは無常すぎる、と感じるものは?」 / EN: "What is too impermanent — to the point of being absurd?"
出典・根拠: ogiri-ai SKILL.md (gyu-don) / フリップ芸バイブル (Google Doc 2024) /
arxiv 2512.21494 Oogiri-Master / arxiv 2601.03103 Who Laughs with Whom /
Humor-Research/Humor-detection (RoBERTa, HF humor-detection-comb-23) /
pskoett self-improvement dual-loop。

## 0. 問題定義 (なぜ今 SHIT か)

1. ogiri-ai の loop が事実上 1 パス。「妥協するなら[2]に戻る」が回数で
   縛られておらず再投入が強制されない。
2. 出力が一文だけ。**意味 (どう無常か) と なぜ面白いか の reasoning が
   無い** → 自分で eval できない → 改善できない。
3. 一文が完結していない (例「さっき覚えた韓国アイドルの名前」= 文が
   終わってない。落ちていない)。完結した punchline になっていない。
4. 抽象お題から直生成 → ベタ混入。実事実シードが無い。
5. 機械 eval (Humor-detection) も BTL クラスタも独立ペルソナ採点も無い。

## 1. 出力フォーマット (必須・例外なし)

各回答は次の 3 ブロックを必ず持つ:

```
【回答N】<完結した一文の punchline>
  ▸ 意味: <これがどういう状況/解釈なのか。3〜6 行。読者が
          「あー、そういうことか」と分かるまで具体的に。物理/時事/
          言葉の二義性など、笑いの仕掛けの種明かしを書く>
  ▸ なぜ面白い(or 面白くない): <短さ/絵が浮かぶ/2段跳び/共感/
          無常の芯 のどれがどう効いてるか。滑る場合は何が足りないか。
          3〜6 行>
  ▸ 点: <0-100> / クラスタ: <C0-C6 のどれに刺さるか> /
        機械eval: <Humor-detection 二値の想定>
```

一文ルール: punchline は **それ単体で文として完結し落ちている**こと。
体言止めで宙ぶらりんは禁止 (例 NG「韓国アイドルの名前」→
OK「韓国アイドル、覚えた頃には改名済み」)。

## 2. INNER LOOP (セッション内・面白くなるまで反復)

```
固定お題
  ▼
[G] 生成: insight 先出し(なぜ可笑しいかを先に書く: arxiv2512
    insight-augmented prompting) → 連想20+/最初10捨て/2段跳び。
    種に「無常すぎる現実」crawl 30 件を必須混入 (実事実シード)。
  ▼ 候補 15〜20 (各 3 ブロック付き)
[E] 評価: 短/絵/2段/共感/無常芯 を各 0-100 + Humor-detection
    RoBERTa 二値 + BTL クラスタ(C0-C6) 判定。
  ▼
[D] 判定: TOP の平均 < 85 ?
    ├ YES → [R] 弱点診断して [G] へ戻す。最大 5 周。
    │        ・「説明不足」→ 意味ブロックを具体化、必要なら
    │          flip 多面前提に作り直し
    │        ・「ベタ」→ 2段跳びを増やす / 実事実シード差替
    │        ・「未完結」→ 文を落とし切る
    │        ・機械eval低 → incongruity/言葉遊び強化
    └ NO  → TOP8 確定
  ▼
[A] 敵対テスト: 独立3ペルソナ(他人票を見せず単独採点:
    arxiv2601 設計)= 懐疑客 / 同業芸人 / 3秒スクロール客。
    1つでも FAIL → [R] へ。
  ▼ TOP8 (reasoning 付き)
```

## 3. FLIP 化 (バイブル準拠の実装)

詳細は本リポ FLIP_DESIGN_RULES.md。スペック上の決定:

- TOP8 の「意味ブロック」を面数設計の素にする。1 文で弱いネタほど
  flip で 2〜6 面に展開すると化ける (鏡=光速図 / 確定申告=3月→6月修正
  / 韓国アイドル=同じ顔連打)。
- 面数型 (バイブル分類): 1面=即完結 / 2面=対比反転(中山功太型) /
  3面=三段 / 4面=起承転結 / 6面=連続めくりで動き。
- 遷移 = **HARD CUT 一択**。fade/zoom/slide 禁止 (フリップは物理の
  「めくり」= 瞬間切替。緩い遷移は緊張を殺す)。
- 主題型 = 「ことば/発想型」を採用 (中山功太型)。AI は手書き線画が
  弱いので絵依存を避ける。
- 体裁: 白 #FFFFFF / 黒 #1A1A1A / Klee One SemiBold / 200-340pt /
  1-3 行 / ±3-5° 傾き / 装飾ゼロ。
- 「逆に変わらない物」(例: サブスク解約画面) は最終面のオチに固定配置。
  2000年代→2010年代→2020年代で「ずっと変わってない」を見せる構成可。
- 出力: Slack に flip 画像 + TikTok に slideshow。daily cron のみ実投稿
  (smoke/today は draft: HARD RULE #9)。

## 4. OUTER LOOP (セッション跨ぎ恒久学習: pskoett self-improvement)

```
TikTok 実績(再生/いいね/コメント) → .learnings/HUMOR.md 記録
  → learning-aggregator: 勝ち/負けパターン抽出
  → harness-updater: ogiri-ai 運用知見を本スペック+SKILL の鉄則へ昇格
  → eval-creator: 過去の名作を regression テスト化
  → pre-flight: 次回生成前に過去学習を読み込む
  = 知識ギャップが毎サイクル縮む (複利)
```

## 5. 2 論文から判明した「現状の欠落」

| 論文 | 欠落している点 | 入れる対策 |
|---|---|---|
| 2512.21494 Oogiri-Master | 客観指標が無い (length / ambiguity / incongruity resolution)。1お題の候補が少ない。人気バイアス。生成前の insight が無い | [E] に 3 客観指標を追加。候補を 15-20 に増やす。採点は独立。生成 [G] の前に insight を書かせる |
| 2601.03103 Who Laughs with Whom | "万人ウケ"前提で persona/クラスタ分けが無い。評価者自身の偏りを無視 | BTL C0-C6 をターゲット明示。flip(無常)と conte で別 persona。採点を複数 persona 平均に |
| Humor-Research/Humor-detection | 機械的な「面白い/面白くない」二値シグナルが無い | RoBERTa humor-detection-comb-23 を [E] の補助シグナルに |

## 6. conte との分岐 (別系統)

flip = 無常 100% / ogiri TOP を面数設計 / 日本語のみ (当面)。
conte = 無常は隠し味 / キャラ駆動 (lazy ゴッドファーザー・バカ版
Peter Thiel) / JA+EN / seedance・kling + ElevenLabs で AI 動画。
Dais 自演台本は不要 (script で完結)。
共通: ogiri TOP8 を種に / recursive-improver で採点。

## 7. 受け入れ基準

- 全出力が 3 ブロック (回答/意味/なぜ面白い+点) を持つ
- 一文が完結している (体言止め宙ぶらりん 0 件)
- INNER LOOP が閾値駆動で最大 5 周回る (1 パス禁止)
- 実事実シードが [G] に混入している
- TOP8 → flip 面設計まで自動で繋がる
- daily cron で Slack + TikTok、smoke は draft
