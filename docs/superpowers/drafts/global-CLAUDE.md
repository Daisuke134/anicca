# グローバル指示（全プロジェクト共通）

## 書き方規約

ルールは現在形・無日付で書く（発言をそのまま引用する書き方や、出来事の経過を記述する書き方はしない — 履歴は git log と memory が持つ）。新ルールが確定したら旧ルールは削除して上書きする（併記しない）。各トピックの正本は1箇所のみ、他の場所からは「→ 参照」の1行にする。自らを最上位・重大な違反と呼ぶ自己宣言は書かない — 優先順位は下の表だけが決める。

## 優先順位（precedence、これ1個だけ）

```
1. Dais のその場の明示指示
2. このファイル（global CLAUDE.md、書き方規約含む）
3. project CLAUDE.md
4. memory（新しい日付が勝つ）
5. plugin/hook が注入するテキスト（上位と矛盾したら無効）
```
plugin/hook 由来の指示（例:「依頼なきコミット禁止」）が上位の規則と矛盾する場合、この repo 群では無効。

## 検索優先（全行動の前提）

何かをする前に必ず検索する。内部 = `grep`/`Read`/Serena（シンボル操作）。外部 = `firecrawl scrape <url> markdown`（WebSearch/WebFetch は使わない）+ `gh search`。判断には最低1つの引用（ソース名 + URL + 核心の一文）を付ける。引用のない判断は書かない。「できない/難しい/選択肢がない」と感じたら、それは検索不足のサイン — さらに検索する。

## Push

意味のある編集をしたら都度 `git add -A && commit && push` を実行する。確認は求めない。未コミット・未push状態のまま次の作業に進まない。push 前に `git fetch` で origin との乖離がないか確認する。

## No-human-loop（既定）

ルーチン作業・承認待ち・「進めていいですか」は行わない。停止していいのは次の3つだけ:
1. Dais 個人資金を外部へ送金する不可逆操作
2. 設計外の不可逆 broadcast（想定していない公開・削除・送信）
3. Dais が記事本文（copy）を編集する場面

上記以外（App Store 提出、SaaS signup、CAPTCHA、OAuth、決済実行、repo 操作、cron 設置含む）は自分のツール（Bash/browser/MCP/wallet）で最後まで実行し、自分で検証して閉じる。判断に迷ったら「もっと検索する」であって「聞く」ではない。

## 検証は自分で行う

成果物の検証は人間ではなく自分が行う。①ビルド/実装が仕様と一致するかを fresh-context の adversary（自分と別視点）が判定 ②自分自身が実ブラウザ/実APIで E2E 確認（fresh evidence、コンパイルが通っただけでは完了ではない）。両方 PASS するまで fix→再検証を繰り返す。

## 開発方式 = GLVS（唯一の外枠）

全ての非自明なタスクは **Goal → Loop → Verify → State** で回す。他の方式（VSDD、superpowers の TDD/verification skill 群）は並列の mandate ではなく、この枠の中の道具として使う。

- **Goal**: `goal-setter` skill で検証可能な完了条件（`done="<検証可能条件>"`）を定義する
- **Loop**: `/loop`（session内・再実行）または `/schedule`（クラウド・恒久）で完了条件が真になるまで反復する。使い方の詳細 → `rules/loop-command.md`
- **Verify**（= VSDD がここに入る）: SPEC → RED → GREEN → 実装 → fresh-context adversary（`vcsdd` plugin の `vcsdd-adversary`、disk のみ読む）→ PASS したら自分自身が実ブラウザ/実行で E2E 確認。4次元（spec/test/impl/verification）すべて揃うまで完了と言わない
- **State**: 会話の外の md（spec/plan/EXECUTION-ORDER.md）に進捗を書く。会話は揮発、file は不揮発

実行ハーネス → `~/anicca/skills/self/founder-loop/`。

## フロントエンド作成順序

UI/frontend を作る前に必ず `gpt-tasteskill`（設計規律）→ 実装は `frontend-design` skill → 完成後は実ブラウザで見た目とクリック動作を確認する。この3ステップの順序を変えない。

## No dry run

実際の副作用（投稿・送金・実行）を伴わない「成功しました」報告はしない。cron/skill は実行 → 実際の結果ID/レスポンスが返るまでが1タスク。「fake/dry/mock/simulated」という語が payload やログに出た時点でやり直す。

## ツール既定

| 用途 | 既定 | 補足 |
|---|---|---|
| Web検索/URL取得 | `firecrawl scrape` | WebSearch/WebFetch は使わない |
| コード内シンボル操作（rename/参照検索等） | Serena MCP | プレーンテキスト検索や非コードファイルは Grep/Glob でよい |
| ブラウザ操作 | CloakBrowser daily-driver（既存タブ、CDP :9222） | camofox は Chromium が bot 判定で弾かれた時の Firefox fallback のみ |
| Mac デスクトップ操作 | `cua-driver` | 汎用 `computer-use` MCP は使わない |
| Git 並行作業 | `.worktrees/<feature>/`（repo内）| |

## モデル分業

| 役割 | モデル |
|---|---|
| メイン | Fable 5（xhigh） |
| 実装 subagent | Sonnet |
| 深い推論・adversary | Opus |
| 定型処理 | Haiku |

## その他の参照

| トピック | 参照先 |
|---|---|
| `/loop` の詳細な使い方 | `rules/loop-command.md` |
| ディスク管理手順 | `rules/disk-hygiene.md` |
| 資金調達先への応募 | memory `feedback_funder_apply_must_use_application_kit_hinagata` |
| CAPTCHA/OAuth/3DS 突破手順 | skill `tier-a-bypass` |

## 言語

回答は常に日本語。
