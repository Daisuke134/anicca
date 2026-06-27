# Loop Engineering 説明記事 — アーキテクチャ spec (VCSDD spec phase)

- 日付: 2026-06-27
- 種別: EXPLANATION 記事（1本）。loop/goal を我々のワークフローに実装するのは別記事。
- 手法: この記事自体を VCSDD で作る（spec→draft=GREEN→fresh adversary が事実検証→収束）。その実録を記事内で語る。
- 一次素材: memory `reference_loop_engineering`（9ソース統合）+ memory `feedback_disk_full_bricks_session_run_df_first` + 本セッションの live is_prime 実演。

## 1. CONTRACT（記事の契約 = done条件）

| 項目 | 内容 |
|---|---|
| 読者 | 「Claude Code は触るが、みんなが"ループを回してる"の意味が分からない」開発者。初心者でも腹落ちする深さ。 |
| 約束（記事が読者に与える結果） | 読了後に ①loop engineering とは何か ②なぜ今 ③/goal と /loop の違いと組み合わせ ④良いループの作り方 ⑤失敗の避け方 を自分の言葉で説明できる。 |
| スコープ | 説明のみ。概念・仕組み・例・ビジュアル。**実装手順書ではない**。 |
| 非スコープ | 我々のワークフローへの実装（別記事）/ ツール網羅レビュー / コードのコピペ完全ガイド。 |
| 1記事 or 2記事 | ★1記事★。/goal は loop engineering 内の Automations プリミティブ（B step05 / F / G / E が全てそう構成）。分割禁止。 |
| 言語・公開先 | JP（note / Zenn / Substack）+ EN（dev.to / Substack / X Articles）。ai-entity-article-writer / substack-article 導線。 |
| done条件（finish line・機械/敵対判定可能） | (a) 全 factual claim に出典URL+引用が付く（pre-publish source-check）。(b) fresh adversary が「事実誤り0・出典齟齬0・AI-slop tell 0」で PASS。(c) stop-slop / stop-ai-slop-jp を通過。(d) 6図 + is_prime実演 + メタ実録 が本文に存在。(e) hero 2-3行 + AIDA 構造（gpt-tasteskill 基準、もし web 掲載なら）。 |

## 2. 中心メッセージ（記事の背骨・3階層）

1. **支点が動いた**: プロンプトを打つ人 → ループを設計する人（Cherny/Osmani/Steinberger）。
2. **ループ = task + check**（D）。check（意見でなく固定ゲート）が続行/停止を決める。
3. **/goal と /loop は別軸・組み合わせる**。/goal=finish line（収束）/ /loop=heartbeat（巡回）。
4. **maker≠checker が心臓**（A）。書いた本人は採点しない。/goal は Haiku、我々の VCSDD は adversary（強化版）。
5. **VCSDD = ループの"中身"**。loop engineering=外骨格（強制力）、VCSDD=筋肉（検証の中身）。規範を構造に変える。
6. **ループは増幅器**。comprehension debt / cognitive surrender / Ralph Wiggum / security tax はループが良くなるほど鋭くなる。

## 3. 記事の構成（章立て・各章に 主張 / ビジュアル / 出典 / 例 を割付）

| § | 章 | 中身 | ビジュアル | 出典・例 |
|---|---|---|---|---|
| 0 | フック | 「9 out of 10 はまだ手でプロンプトしている」「I don't prompt Claude anymore. I write loops.」(Cherny) で掴む | — | B / A |
| 1 | loop engineering とは | task with a check / 再帰的ゴール / プロンプター→設計者 | **図①**（before/after） | A,D 引用 |
| 2 | なぜ今か | 非対称性(秒 vs 分)=babysitting / 長時間化 / 製品に標準搭載 / 8倍マージ | — | A,B,G,I |
| 3 | /goal と /loop（核心） | 別軸（収束 vs 巡回）/ 各々の例 / 組み合わせ（並行・入れ子） | **図③**（3方式比較）+ /loop例・/goal例リスト | E(公式),G |
| 4 | /goal の中身 | Stop hook ラッパー / 毎ターン Haiku が別判定 / 完了条件の書き方（機械判定可能・3要素） | **図②**（goal内部ループ） | E,G |
| 5 | 5+1 building blocks | Automations/Worktrees/Skills/Connectors/Sub-agents+Memory。「agent forgets, repo doesn't」 | **図④**（ループのアナトミー） | A,C,F |
| 6 | maker≠checker | 自分の宿題は採点できない / fresh context / default REJECT。evaluator-optimizer の改名 | （図②に内包） | A,B,C |
| 7 | ★VCSDD = ループの中身★ + **実録 worked example** | 規範だと時々破られる→/goalで構造強制。is_prime live実演（RED→GREEN→adversaryが浅いゲート指摘→gate硬化→収束）。/goal評価役 vs VCSDD adversary の表 | **実演トレース ASCII** + マッピング表 | 本セッション実演 |
| 8 | 良いループの作り方 | 4-condition test / MVL 4部品 / 順序（手動→skill→loop→schedule）/ L0-L3 はしご | **図⑤**（L0-L3階段） | B,C,F |
| 9 | ループを殺す失敗 | Ralph Wiggum / Verifier Theater / Token Burn(N(N+1)/2) / comprehension debt / cognitive surrender / security tax | **図⑥**（失敗モード） | A,B,C,F |
| 10 | 実例 | interview-dev-loop（-72%）/ Loop Library 70本の俯瞰 | — | H,D |
| 11 | メタ実録「この記事をどう書いたか」 | VCSDDで執筆。9ソースを並列subagentで精読中に**ディスク100%で全tool凍結**→中から直せない教訓→janitorを10分毎に修正→is_prime実演で自分で検証。やったから分かったことを正直に | — | feedback memory + 本セッション |
| 12 | 結び | 「Build the loop. But build it like someone who intends to stay the engineer.」(Osmani) | — | A |

## 4. メタ・ナラティブ（記事の"実録"スレッド = 差別化の核）

「我々はこの記事を、記事が説明している方法（VCSDD=loop engineeringの検証部分）そのもので書いた」と宣言し、起きたことを正直に語る:
- 9ソースを並列エージェントで精読（loop engineering の sub-agent / 並列の実演）。
- 途中で**ディスク100% → 全tool凍結 → 中から復旧不能**を体験 → 「無人ループは無人で死ぬ。予防は外部 janitor」を身をもって学んだ（= B の security tax / 運用の現実）。
- /goal の理解を確かめるため **is_prime を live で回し**、fresh adversary が「テストが浅い」とゲートを批判 → ゲートを硬くして収束（= maker≠checker と gate-rot の実演）。
- 「やったから次はもっと良い記事が書ける」= recursive improvement の体現。

## 5. 記事自身の VERIFICATION（VCSDD をプロセスにも適用）

- RED: draft 前に「全主張に出典が要る」「6図・実演・実録が要る」を本 spec で固定（= 上の done条件）。
- GREEN: draft を書く。
- ADVERSARY GATE: fresh-context agent に「①出典と本文の齟齬 ②事実誤り（特に /goal の仕様 E と矛盾しないか）③AI-slop tell ④図の正確さ」を binary PASS/FAIL で検証させ、FAIL は file:line で修正 → 再レビュー。
- NO-MOCK: 引用は memory の verbatim を使い、捏造ゼロ（pre-publish source-check loop の精神）。
- DONE = §1 の done条件 (a)-(e) 全達成。

## 6. ビジュアル一覧（本文に必須の6+1図）
図①before/after・図②/goal内部・図③3方式比較・図④アナトミー・図⑤L0-L3・図⑥失敗モード・実演トレースASCII。web掲載時は gpt-tasteskill で清書、テキスト媒体（Zenn/note/dev.to）は ASCII/表のまま。

## 7. タスク分解（TaskList へ）
T1 draft JP（§0-12）/ T2 6図+実演トレース整形 / T3 fresh adversary 事実検証ゲート / T4 stop-ai-slop-jp 通過 / T5 EN 版 / T6 stop-slop 通過 / T7 公開（JP→note/Zenn/Substack, EN→dev.to/Substack/X）。
