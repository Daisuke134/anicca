# Title-writing best practices (write-time reference)

Why this file exists: previous version was self-referential — every rule was
derived from our own rubric-judge FAIL cases, never from what the market
actually rewards. This version is exemplar-based: Section 1 is real titles
with real engagement numbers, harvested live and re-verified daily (spec 47
§12-3). **Imitate the nearest pattern's structure, swap in your topic** —
don't invent a title from theory.

Full raw harvest (all titles + metrics + URLs + platform, with scrape gaps
noted): `skills/article-writer/vendor/exemplars/<date>-title-harvest.md`
(latest: `2026-07-20-title-harvest.md`). Re-harvest before reusing patterns
that are more than ~2 weeks old — markets move.

## 1. BASE = 実在パターン（模倣元。この構造を丸ごとコピーしてトピックだけ差し替える）

### JA

**常識逆張り命令形** — 定説を否定する命令文、理由は本文で。
- 「一人前のエンジニアなら、PRでコメントをもらうな。」(Zenn, 191 likes)
- 「GitHub Release 作成をパッケージリリースのトリガーにするな！」(Zenn, 48 likes)
- なぜ効く: 読者の「当たり前」を名指しで壊すので続きを読まないと気が済まない。

**疑問形→数字で殴る** — 固有名詞+疑問符で立てて、具体数字で答えを叩きつける。
- 「AIに「レビューして」はもう古い？「敵対的検証」のすすめ」(Zenn, 198 likes)
- 「中国AI「Kimi-K3」ショック？日経平均は最高値から11％超の下落」(note, 113 likes)
- なぜ効く: 疑問符が「答えを知りたい」を作り、数字がその場で満たす。

**実測数字を前面化「〜したら〜だった/〜になった」** — 検証した行為+結果の数字を見出しに出す。
- 「AI臭は語彙よりリズムに出る - 自然な日本語を書くAgent Skillと7モデル×406本の実測」(Zenn, 201 likes)
- 「Claude Codeのスキル×サブエージェントで開発ワークフローを丸ごと自動化したらデリバリー速度が3倍になった」(Zenn, 18 likes)
- なぜ効く: 「やってみた系」の中でも数字があるものだけが再現性の証拠になる。

**驚きの動詞+固有名詞** — 主語(ツール名など)+予想外の動詞(化けた/消えた/バレる)。
- 「Claude Codeが化けた。今使っている3つのプラグイン+標準機能の活用法」(Zenn, 191 likes)
- 「Cursorに「不要なブランチを整理して」と頼んだら、Dドライブが消えた話」(Zenn, 181 likes)
- なぜ効く: 動詞の意外性がクリックの動機そのものになる。固有名詞は聞き慣れたツール名限定（未定義の専門用語ではない）。

**リスト型+数字** — 「〜選」「〜個」で内容量を約束する。
- 「AIが作って、採点して、直して仕上げる。コピペで使えるプロンプト10選」(note, 177 likes)
- なぜ効く: 読む前に得られる分量と即使える実利が見える。

**人間味・感情吐露型** — 一人称の痛み/実感を隠さない。
- 「舌が腐る　AI文章を浴び続けた書き手の末路」(note, 68 likes)
- 「よく戻ってきたな。今日を生き抜いたあんたへ贈る、魂の生存証明。」(note, 178 likes)
- なぜ効く: 技術ネタでも感情の一文があると「人が書いた」実感が生まれ足を止める。

### EN

**Blunt myth-busting declarative** — "The Myth of X" / flat claim that a common belief is wrong.
- "The Myth of the Post-Documentation Era" (dev.to, 77 reactions)
- "Every AI-Generated Line of Code Is a Small Loan — And Eventually, You Have to Pay It Back" (dev.to, 37 reactions)
- Why it works: names the belief being attacked in the first clause, so the reader self-selects instantly.

**Quantified claim + twist clause (em dash)** — a number, then an em dash that complicates it.
- "How I made a Rust hot path 27x faster, and the AI fix I refused to merge" (dev.to, 30 reactions)
- Why it works: the twist after the number promises a story is different from a plain benchmark post.

**Curated-list + urgency** — a count plus a reason to act now.
- "51 websites that feel illegal to know. Bookmark this before it gets buried." (Substack Notes, 1.3K likes)
- Why it works: concrete count + loss-aversion line ("before it gets buried") in the same breath.

**First-person confessional, short declaratives** — two short blunt sentences, no hedging.
- "I Could Review It. I Couldn't Write It." (dev.to, 39 reactions)
- "Stop Saying You Want Ownership Mindset" (dev.to, 41 reactions)
- Why it works: terse rhythm reads as a real admission, not marketing copy.

**Behavior-change narrative** — "I stopped X. Here's what changed."
- "I Stopped Debugging at My Desk. Here's What Changed" (dev.to, 46 reactions)
- Why it works: promises a before/after the reader can compare to their own habit.

**Direct-address provocative question** — names who should be asking, then a question.
- "Two questions every CEO should ask about AI" (Substack Notes, 109 likes)
- Why it works: naming the reader's role makes the question feel personally addressed, not generic.

## 2. 禁則（実測で裏取りされたものだけ）

1. **未定義の固有名詞/製品名/頭字語を見出しに出さない。** 見出しは本文なしの他人として読まれる（2026-07-19 run: ja/en とも「Mech」「Requester」で `title_jargon` gate に FAIL — `state/runs/20260719-2100/gates/rubric-judge-{en,ja}.json`）。固有名詞は平易な機能語の後にしか置けない。
2. **「徹底解説/完全ガイド」型の説明フレーミング禁止。** 何を見つけたかを約束するのが見出しの仕事で、説明が存在することを約束しても情報量ゼロ。
3. **見出し単体で、その分野を知らない他人が主語を分解できること。** 本文で定義されるから許される、は成立しない — 見出しは本文より先に読まれる。
4. **計測レポート型の禁止。**「AをN回比べたらXは○%、Yは○%だった」/「Tests: A x% shorter, B y% longer」。何を測ったかしか言っておらず、それを知って読者の何が変わるのかを言っていない（2026-07-26 run: この形を採用し、「バイブコーディングの本質は速度ではない」「The major sufferer becomes the major builder」「24年間ダメだった僕が〜」を却下 — `state/runs/daily-2026-07-26/article-{ja,en}.md` の title 行）。数字そのものは禁則ではない。数字が効くのは落差・逆説を作っている時だけで（「4万人飛んでいただいた結果、売上はゼロ」）、落差の無い数字は仕様表示。見出しに数字が無いことは FAIL ではなく、同点のタイブレークにも使わない。

**この §2 が禁則の唯一の正本。** 他ファイル（SKILL.md、article-daily.sh の prompt）は禁則の本文を持たず、ここを参照する1行だけを持つ。prompt が禁則を言い換えて厳しく変異させたのが 2026-07-26 の計測レポート型固着の原因（spec 47 §20 の漂流クラス）。

## 2.5 日本語タイトルの実測分布（2026-07-27 harvest、239本収集 → 上位25本を分析）

出典: はてブ人気エントリ（IT / 総合 / 新着人気）、Zenn トレンド、Qiita トレンド、note トップ。

| 指標 | 実測値 |
|---|---|
| 文字数 | 中央値 **37字**（最短12・最長93） |
| 「本質」「変革」「未来」「可能性」 | 25本中 **0本** |
| 「時代」 | 25本中 1本のみ |
| 数字を前面に出す | 25本中 6本（「週2,241件を読んで選んだ」「なぜ10日で復旧できたのか」） |
| かぎ括弧「」で引用・皮肉 | 25本中 6本 |
| 疑問形 | 25本中 4本 |
| 長文ナラティブ型（80字超） | 25本中 4本。全て「〜した話」等で着地 |

読み方: 日本語の実物は**長く、具体的で、オチまでタイトルに入っている**。英語のリズムで20字前後に短く抽象的に切ると必ず外す。抽象語で殴る型は実測でほぼ存在しない。

- **JP タイトルを EN の直訳にしない。ただし主張そのものは両言語で同一にする。** 変えるのは長さと具体性であって、言っている内容ではない（2026-07-27 是正: 「翻訳しない」を主張の変更まで拡大解釈し、JP だけ別の記事のタイトルになっていた）。
- **例が主題を乗っ取っていないか毎回見る。** 記事が広い主張なら、タイトルに1つの事例を出した瞬間、記事はその事例の記事に縮む（2026-07-27 実例: 「あらゆる問題」の記事なのに JP 案が毎回「先延ばしアプリ」の話に落ちた）。
- 通説の否定形は日本語でも機能する（実測: note「AI時代に生き残る会社は、AIを使う会社ではない」91スキ）。落とすのは読者を否定する時だけ。

## 2.6 X 告知ポストの解剖（2026-07-26 harvest、高エンゲージ投稿14本）

記事タイトルと告知ポストは**別物**。ポストは記事の要約ではない。

- 4〜8行、1行1節、行間に空行。密な段落は14本中0本。
- 冒頭は3型のみ: 断定（"SaaS is not dead"）／場面・告白（「3か月前に作った。3日で飽きた。」）／数字（"A year and a half."）。
- 中盤で必ず反転する。期待と現実、自慢を次の行で自分で潰す。
- **意見投稿はリンクを貼らない**（貼るのは「作ったよ」報告だけ）。EN はハッシュタグ0。JP の devlog は `#個人開発` を付けるが意見投稿には不要。
- 終わり方は3つ: 断ち切る／静かな一言／命令形。**疑問形で終わる投稿は14本中0本**。

## 3. 更新規約

この BASE セクションは生きたファイル。真実の源泉は harvest の実測データであり、
理論から作った規則ではない。spec 47 §12-3 の exemplar loop が **毎日1教訓** を
このファイルに書き足す/上書きする運用: 新しい harvest で確認できた実パターンを
追加し、直近2週間 harvest で再現しなかったパターンは消す（併記しない、消して
是正を書く）。harvest の生データは `vendor/exemplars/` に日付ファイルで蓄積する。
