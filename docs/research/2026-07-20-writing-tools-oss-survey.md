# Writing-tools OSS 調査（記事 / X post / 書籍） — 2026-07-20

目的: writer loop の base 戦略（taste / verifier）を既存 OSS の copy+tweak で強化する。
車輪の再発明禁止の実践。W5 bakeoff（同一題材でタイトル+第1段落を各ツールに生成させ比較 → 記事化 → 統合 skill → OSS 化）の候補確定。
関連 spec: `docs/loop-engineering/47-writer-loop-quality-and-self-improvement.md`

## 実測サマリ（gh search / gh api / raw README、2026-07-20 実測）

| repo | stars | 最終push | 何者か | 品質の作り方 | 盗むべき部分 |
|---|---|---|---|---|---|
| **stanford-oval/storm** | 30,157 | 2025-09-30 | 研究→outline→執筆の Wikipedia 級記事生成（NAACL 2024 論文） | ①perspective-guided question asking（類似記事から視点を収穫して質問を制御）②simulated conversation（writer×topic-expert の対話で理解を深める）③outline→citation付き執筆の2段 | **pre-writing の研究工程**。記事の「中身の深さ」はここ。dspy 実装、`pip install knowledge-storm` |
| **artemnovitckii/content-skills** | 67 | 2026-06-20 | Claude Code skill 5本: dumbify / storytelling / viral-hooks / anti-ai-writing / voice-dna | 「5 diseases」診断（vagueness compression / significance inflation / hedged confidence / rhythmic flatness / borrowed authority）+ specificity ladder（Vague→Specific→Concrete→Lived、level 3 必須）+ negative parallelism ban | **anti-ai-writing を最終フィルタとして verifier に移植**。rubric が「上手いか」でなく「AI 臭いか」を診断できるようになる。SKILL.md 形式なのでそのまま chain 可能 |
| **rediumvex/viral-hooks-skill** | 62 | 2026-05-05 | フック 100 formula × 10 心理トリガー（curiosity gap / contrarian / authority / …） | Four Hook Killers 診断（DELAY / vague / off-target / flat）+ platform 別 deadline（reel 2秒 / LinkedIn fold / newsletter 件名） | **X post・タイトルの opener 診断**。短文フォームの taste 層の骨格 |
| **langchain-ai/social-media-agent** | 2,686 | 2026-07-20 | URL→投稿文生成→スケジュール（LangGraph、Twitter+LinkedIn） | human-in-the-loop 前提の curation flow | 投稿レールは自前 CDP があるので本体は不要。**content-generation prompt 群のみ**参照価値 |
| **rockscy/solo-skills** | (~小規模) | 2026-07 現役 | solo founder 向け 7 skill（launch tweets / customer emails、EN+中文バイリンガル） | 各 skill に「Do NOT use when…」節を強制 | **negative trigger（使うな条件）を skill に書く規律**。launch-tweet skill は X フォームの参考 |
| datacrystals/AIStoryWriter | 256 | 2025-11-24 | 長文小説の高品質生成 | outline→chapter→revision loop | 書籍フォーム拡張時の一貫性管理の参考（今は保留） |
| mshumer/gpt-author | 2,530 | 2024-04-03 | 数分で小説1冊 | 章 outline→生成の直列 | 古い（2024 で停止）。構造だけ参考、採用しない |
| BlinkDL/AI-Writer | 3,798 | 2025-05-15 | 中文網文の RWKV 生成 | 事前学習モデル | 不採用（LLM API 前提の我々と別世界） |

検索で出なかった/薄かった領域: 日本語記事執筆の体系的 OSS（zenn/note 向け）はほぼ空白。
→ **ここが我々の OSS の差別化スロット**（日本語 taste は自前 exemplar 帰納で埋める。zenn/devto/note 実物収穫 = commit ab490b0 の路線が正しい）。

## 単一推奨

- **記事（英語・研究の深さ）**: STORM の pre-writing（perspective→質問→outline）を STEP2(研究) に移植。
- **記事（文章の質・全言語）**: content-skills の anti-ai-writing + specificity ladder を verifier(rubric) に移植。これが「verifier が良くなれば書き手は勝手に良くなる」の実弾。
- **X post**: viral-hooks-skill の Four Hook Killers + content-skills の storytelling。Postiz 不要、投稿は既存 CDP レール。
- **書籍**: 新ツール不要。記事30本を章に束ねる再編集フォーム。AIStoryWriter の一貫性管理だけ将来参照。

棄却案の最強論拠: 「LangGraph 系フルパイプライン(social-media-agent 等)を丸ごと採用」→ 投稿レール・queue・ledger は既に自前があり、重複 infra の輸入は負債。プロンプト/rubric 層だけ盗むのが正。
自分が間違うとしたら: content-skills（67★）の rubric が英語 SNS 向けに過適合しており、日本語 zenn 記事に効かない筋。→ bakeoff で日本語題材も並走させて実測する。

## W5 bakeoff 設計（次アクション）

1. セットアップ: content-skills(5本) + viral-hooks-skill を `.claude/skills/` に、STORM は `pip install knowledge-storm`
2. 同一 topic（queue の loop-engineering-explainer）で各構成に「タイトル + 第1段落」だけ生成させる
   - 構成: A=現行 article-writer / B=+anti-ai-writing / C=+viral-hooks / D=+STORM outline / E=全部
3. 判定: fresh spawn の blind 比較（どれが良いか + なぜ）× ja/en 両方
4. 結果 → ①勝者を article-writer の taste/verifier に統合 ②比較記事を queue に投入 ③統合 skill を profitable-claude で OSS 化

## 注記

- gh API rate limit（5,000/hr）に当日到達。追加検索は reset 後。"zenn article" / "buzz tweet" クエリは未実行。
- content-skills の README にある voice-dna（自分の過去投稿20本から声を学習）は、exemplar 帰納（T6）と同思想 — 我々の路線の裏付け。
