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

## 記事レーン追補（research-articles subagent、2026-07-20 追記）— ★初回調査を上書きする大物★

初回の俺の直接検索は 45★以下の米粒しか出せていなかった。subagent が 20k-40k★級を発掘。
raw README で実在+内容は俺が裏取り済み（stars 数値は subagent 実測、俺の gh api は rate limit で未再検証）:

| repo | stars(未再検証) | 何者か | 盗むべき部分 |
|---|---:|---|---|
| **coreyhaines31/marketingskills** | 40,824 | マーケ系 agent skill 集（Corey Haines 作、agentskills.io 準拠） | headline 複数案、Voice-of-Customer、clarity→proof→specificity の critic-loop、7回編集 sweep |
| **blader/humanizer** | 29,991 | AI 文体除去 skill（plain Markdown、どの harness でも動く） | Wikipedia 由来 AI 文体パターン検出を**最終 gate 化**。content-skills の anti-ai-writing の上位互換候補 |
| **alirezarezvani/claude-skills** | 22,855 | 362 skill の総合庫。content-production に機械的 publish gate | `content_quality_gates.py`、headline 5-10案採点、"A failing gate blocks publish; fix and re-run until clean" |
| **KKKKhazix/khazix-skills** | 17,492 | 中文 writing skill（実記事の AI初稿→修正版 few-shot） | HKR 選題、具体場面 hook、4層自己監査 |
| **shimo4228/claude-skill-writing-ecosystem** | 1 | **日本語 writing ecosystem**: AI-slop 禁止語リスト(ja+en)、だ/である×発見調、煽らないタイトル規範、editor/essay-reviewer/fact-checker の役割分離 | **日本語 lane の唯一の直接候補**。stars=1 で成熟度未証明 → bakeoff 必須 |

subagent 単一推奨（採択）: **英語 = alirezarezvani の品質ゲート骨格 / 日本語 = shimo4228 の voice+reviewer / 調査前段 = STORM**。
STORM を最終 writer にしない根拠 = README 自身が「publication-ready には大幅編集が必要」と明記。
→ bakeoff 第2ラウンドに humanizer / marketingskills / shimo4228 を追加すべき（第1ラウンドは content-skills 系のみで実施済み）。

## 書籍レーン追補（research-books subagent 実測、2026-07-20 追記）

当初「3レーン全滅」と書いたが books レーンは後着で完走 — 是正。上位実測:

| repo | stars | 最終push | 品質の作り方 | 盗むべき部分 |
|---|---:|---|---|---|
| THUDM/LongWriter | 1,867 | 2025-06-24 | AgentWrite が plan を step 分割、累積本文を毎 step 注入 | step cache/resume、長文分割 |
| Nigh/show-me-the-story | 373 | 2026-07-19 | outline 承認→章別 review、事実検査 NG で自動 rewrite、全書診断→最小 diff 改稿 | **既存本文 import + 全書整合 pass** — 記事束ね直しに直結 |
| KazKozDev/NovelGenerator | 138 | 2025-11-05 | 3段編集 + 全章整合 pass | 最終整合 pass、EPUB/PDF export |
| knoai/knowrite | 16 | 2026-05-09 | **Editor 最大3 revise、80% gate**、3層 memory | **bounded revise** — W2（無限 revise 廃止）の既存実装例 |
| alexeygrigorev/ai-book-generator | 13 | 2026-04-06 | parts→chapters→sections→bullets、進捗注入 | plan.yaml、章素材束ね、**EPUB + KDP print-ready PDF** |

書籍フォームの単一推奨（subagent 提案を採択）: **ai-book-generator を骨格**（非小説の章構造 + 記事流し込み + KDP/EPUB 組版が一気通貫）+ **show-me-the-story の全書整合 pass** と **knowrite の bounded revise** を品質 loop として移植。
誤り筋: 再編集品質を組版より優先するなら show-me-the-story が第一候補に入れ替わる。
knowrite の「最大3 revise + 80% gate」は W2 の設計そのもの — 車輪あり、copy+tweak せよ。

## X post レーン追補（research-xposts subagent 実測、2026-07-20 追記）

| repo | stars | 最終push | 品質の作り方 | 盗むべき部分 |
|---|---:|---|---|---|
| blacktwist/social-media-skills | 344 | 2026-05-01 | voice context→9種 hook→thread arc→A/B 記録 | 5-7 hook案、standalone hook、1投稿1idea |
| TheMattBerman/x-algo-skill | 63 | 2026-05-18 | xai 公開 repo 再監査、underperformance 診断 | negative-signal scan。★重要: "The actual weight numbers are NOT in the open-source repo" — algo 重み数値を謳う他 repo の数字は捨てる★ |
| aaaronmiller/create-viral-content | 51 | 2026-06-22 | draft→audience 攻撃→AI-tell 除去→20%圧縮→再攻撃 | 4視点 refinement + specificity gate |
| shannhk/viral-x-posts | 11 | 2026-02-18 | 23 formula の目的別 routing | formula catalog のみ（重み数値は不採用） |
| Gingiris-1031/gingiris-twitter-agent-ops | 7 | 2026-07-06 | 本人語料→voice 鉄律→SOURCE-INDEX→publishability gate→週次学習 | **voice/evidence/publishability/feedback の閉ループ構造**（45日 1,150→1,837 followers のケース記録付き） |
| emremy/tweet-dna | 1 | 2026-01-21 | 最大400投稿から persona JSON、critic/refine | persona 蒸留→structured generation |

X フォームの単一推奨（subagent 提案を採択）: **Gingiris の閉ループ構造を骨格に copy+tweak**、生成部だけ既存 CDP 投稿レールへ接続。voice→evidence→publishability gate→feedback は我々の conscience gate(W1) + 実売還流(T12) と同型 — 7★でも構造が正しい。
hook 素材は blacktwist(344★) を併読。algo 重みを数値で謳う repo は x-algo-skill の反証により全部眉唾。

## bakeoff 第1ラウンド結果（2026-07-20 実施、blind 判定）

同一題材（loop-engineering-explainer + goldmine doc）で5構成が「タイトル+第1段落」を ja/en 生成。
shuffle+匿名化（D の process 節は剥離）→ fresh spawn 編集長が blind 審査。mapping: entry-1=C, 2=B, 3=A, 4=D, 5=E。

| 構成 | ja 順位 | en 順位 | 講評の要点 |
|---|---:|---:|---|
| **E = STORM式視点法+hooks+storytelling+anti-ai 全部統合** | **1位** | **1位** | 「テスト失敗で止まる agent」という観測可能な実景から入り、保存状態・独立検証・再試行・予算・停止条件を一息で示す。タイトルやや長い |
| C = viral-hooks のみ | 2位 | 3位 | exit code 0・空 queue・公開 URL の実物が効く。ただし完結しすぎて先を読む余白が小さい |
| D = STORM式視点法のみ | 3位 | 2位 | 問題設定明快だが後半に抽象語が続く |
| B = anti-ai-writing のみ | 4位 | 5位 | 転換は伝わるが実物ゼロ、「設計者へ移る」が紋切り型 |
| A = 現行 baseline | 5位 | 4位 | 「もう古い？」が軽い煽り、不自然表現で意味が止まる |

**結論: 現行 taste は blind でほぼ最下位。skill 統合(E)が両言語で勝利 — 統合を standard 化する。**
勝者から standard 化すべき原則（judge の言）: 抽象的な「自律性」でなく**観測可能な場面**から始め、実装部品を出し、モデルの自己申告でなく証拠で完了を決める構造を第1段落で示す。
第2ラウンド候補: humanizer(30k★) / marketingskills(41k★) / shimo4228(日本語)。

## 注記

- gh API rate limit（5,000/hr）に当日到達。追加検索は reset 後。"zenn article" / "buzz tweet" クエリは未実行。
- content-skills の README にある voice-dna（自分の過去投稿20本から声を学習）は、exemplar 帰納（T6）と同思想 — 我々の路線の裏付け。
