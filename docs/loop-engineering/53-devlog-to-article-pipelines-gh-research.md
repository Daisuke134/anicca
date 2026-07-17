# 53 — devlog→記事 自動化の先行事例（GH 実測研究、2026-07-17）

対象: article loop レーンA（dev-digest → 記事カード）の設計裏付け。`gh search repos` + README 実読。

## 発見 repo と手法

| Repo | Input | コンテキスト不足の埋め方 | 記事の型 |
|---|---|---|---|
| [wiggitywhitney/commit-story](https://github.com/wiggitywhitney/commit-story) | commit diff + **AI アシスタントとの実会話ログ** + commit msg | 会話ログを主データにする（post-commit hook で自動） | 教訓抽出型（decision + why） |
| [wiggitywhitney/mcp-commit-story](https://github.com/wiggitywhitney/mcp-commit-story) | commit + AI チャット + README + 過去 journal | 「No Hallucinated Summaries: Everything ... grounded in real actions and conversations」+ 日次→週次→月次→トーク素材の段階抽象化 | **失敗談型**。実例記事 [blog-post-castle-unstable-ground.md](https://github.com/wiggitywhitney/mcp-commit-story/blob/main/blog-post-castle-unstable-ground.md) を同梱 |
| [qingxuantang/bip-daily](https://github.com/qingxuantang/bip-daily) | 複数 repo の commit + 音声メモ | morning meeting（横断日次要約） | 進捗報告型（X/小紅書自動投稿） |
| [lucianfialho/build-in-public-mcp](https://github.com/lucianfialho/build-in-public-mcp) | Claude Code セッション | セッション単位解析 → tweet 候補 | 進捗報告型（tweet 粒度） |
| [goswamiSiddharth/devlog-ai](https://github.com/goswamiSiddharth/devlog-ai) | git log + **GitHub Issues** | 未消化 Issue で「積み残し」文脈を補完、Ollama で $0 | 進捗報告型 |
| [CMXX648/clgen](https://github.com/CMXX648/clgen) | git log/diff | diff の意味論理解で分類（commit 文言に頼らない） | リリースノート型 |
| [PEACEBINFLOW/mindseye-google-devlog](https://github.com/PEACEBINFLOW/mindseye-google-devlog) | Google Sheet 台帳（git log 不使用） | 実行ログをノード/ラン単位で構造化 | 教訓抽出型 |

## 結論（うちのパイプラインへの適用）

1. **source**: commit message / git diff だけでは記事にならない、が業界共通の壁。最有力解 = **AI アシスタントとの実会話ログを主データにする**（commit-story 方式）。うちの make-diary-digest.sh は transcript サンプリングで既に同型。**足すべき**: ①未消化タスク一覧（TaskList/spec TODO — devlog-ai 方式）②README/プロジェクト目的の毎回注入（mcp-commit-story 方式）。
2. **売れる型**: 失敗談型（何が間違っていて、どう気づき、どう直したか）> 教訓抽出型 > 進捗報告型。進捗報告は量産できるが商品価値が低い。digest の抽出プロンプト（症状→誤った本能→正しい手→一般法則）は失敗談型と一致 — 現設計は正しい。
3. **copy 元**: `wiggitywhitney/mcp-commit-story`。コンテキスト合成（commit+チャット+README+過去journal）と段階的抽象化（日次→週次→月次→トーク）が同型で、生成物→実ブログ記事の実例が同梱。
4. **収益の構造**: 7 repo とも**ツール自体の課金例ゼロ**。金は全て下流（本人の newsletter/Substack 有料・登壇・キャリア）で発生。= 「ツールを売る」ではなく「ツールが生む記事の質」で稼ぐのが業界標準。profitable-claude の設計（loop が記事で稼ぐ）はこの構造と整合。

## make-diary-digest.sh への具体反映（TODO #55b）

- 収集部に追加: ①当日の TaskList / spec TODO 表の diff ②profitable-claude README の先頭 N 行（プロジェクト文脈）③過去 7 日の devlog カード（連続性）
- 抽出プロンプトに追加: 「失敗談として書けるものを最優先しろ（何を間違え、どの瞬間に気づき、どう直したか）。時系列のドラマがあるものが最上」
