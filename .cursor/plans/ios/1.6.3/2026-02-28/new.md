べた。チャットで全部ビジュアルに答える。

  ---
  1. webapp-factory フルフロー（現在の状態）

  ┌──────────────────────────────────────────────────────────────────┐
  │                    webapp-factory v2 フロー                       │
  └──────────────────────────────────────────────────────────────────┘

  cron 09:00 JST（Anicca OpenClaw jobs.json）
      │
      ▼
  ┌─ Anicca（監督 — SKILL.md を読む）─────────────────────────────────┐
  │                                                                   │
  │  STEP 1: coding-agent スキルを読む                                │
  │  STEP 2: Claude Code を起動                                       │
  │     exec pty:true background:true                                │
  │     command: "source .env && claude -p '$(cat prompt.md)'        │
  │              --dangerously-skip-permissions"                      │
  │  STEP 3: Slack #metrics に「:factory: 起動」報告                          │
  │  STEP 4: system event 監視ループ                                  │
  │     ├─ US-XXX_START 受信 → Slack「:building_construction: 開始」                       │
  │     ├─ US-XXX_DONE 受信 → Slack「:white_check_mark: 完了」                         │
  │     ├─ US-XXX_ERROR 受信 → Slack「:x: エラー」                      │
  │     ├─ 10分無音 → process(log) → Slack に報告                     │
  │     └─ COMPLETE 受信 → Slack「:tada: 完成」                            │
  │  STEP 5: 完了処理                                                 │
  │                                                                   │
  └───────────────────────────────────────────────────────────────────┘
      │
      ▼
  ┌─ Claude Code Opus（選手 — prompt.md を読む）──────────────────────┐
  │                                                                   │
  │  US-001: トレンド調査 + アプリ名決定                               │
  │     Web検索 → ニッチ特定 → prd.json 生成                          │
  │     → git commit + push → system event                           │
  │                                                                   │
  │  US-002: Stripe Product + Price 作成                              │
  │     curl → prod_xxx + price_xxx → .env.local                     │
  │     → git commit + push → system event                           │
  │                                                                   │
  │  US-003: Next.js プロジェクト作成                                  │
  │     npx create-next-app → npm install stripe                     │
  │     → npm run build → git commit + push → system event           │
  │                                                                   │
  │  US-004: 機能実装（1ページずつ）                                   │
  │     Landing → Pricing（Server Action） → 機能ページ → Success    │
  │     各ページ: 実装 → L0 Gate → git commit                        │
  │     → git push → system event                                    │
  │                                                                   │
  │  US-005: 品質チェック                                              │
  │     L0 Gate（8パターン grep） + SEO + npm run build               │
  │     → git commit + push → system event                           │
  │                                                                   │
  │  US-006: Vercel デプロイ                                           │
  │     npx vercel deploy --prod + env vars                           │
  │     → git commit + push → system event                           │
  │                                                                   │
  │  US-007: 完了報告                                                  │
  │     AGENTS.md 作成 + git push                                     │
  │     → system event「COMPLETE」                                    │
  │                                                                   │
  │  【各 US 末尾で】自己改善 BLOCKING GATE                            │
  │     エラーあった？                                                 │
  │     ├─ YES → prompt.md 修正 + Evolution marker → git push → 次   │
  │     └─ NO → 次の US へ                                            │
  │                                                                   │
  └───────────────────────────────────────────────────────────────────┘

  ---
  2. :red_circle: オリジナリティ発見（全て修正が必要）

  調べた結果、5つのオリジナリティが見つかった。全部ベストプラクティスに反している。

  ┌─────┬─────────────────────────────────┬───────────────────────────────────────────┬───────────────────────────────────────────────┐
  │  #  │ オリジナリティ（俺たちが勝手に  │            ベストプラクティス             │                    ソース                     │
  │     │          やったこと）           │                                           │                                               │
  ├─────┼─────────────────────────────────┼───────────────────────────────────────────┼───────────────────────────────────────────────┤
  │     │                                 │ Ralph ループ（bash スクリプトで -p        │ https://github.com/snarktank/ralph — 「Each   │
  │ O-1 │ 単発 -p 呼び出しで全7 US        │ を繰り返し実行。各イテレーションが新鮮な  │ iteration is a fresh instance with clean      │
  │     │ を1回で実行                     │ コンテキスト）                            │ context. Memory persists via git history,     │
  │     │                                 │                                           │ progress.txt, and prd.json.」                 │
  ├─────┼─────────────────────────────────┼───────────────────────────────────────────┼───────────────────────────────────────────────┤
  │     │                                 │ Postiz CLI で X に自動投稿（v1 spec       │ v1 spec LAYER 4 +                             │
  │ O-2 │ X 投稿がない                    │ には書いてあったのに prompt.md            │ https://docs.postiz.com/usage/cli             │
  │     │                                 │ に入れてない）                            │                                               │
  ├─────┼─────────────────────────────────┼───────────────────────────────────────────┼───────────────────────────────────────────────┤
  │     │ E2E テストがない（L0 Gate =     │ Playwright E2E                            │ https://github.com/0xAxiom/AppFactory —       │
  │ O-3 │ grep のみ）                     │ テストで実際のブラウザ動作を確認          │ 「UI-generating pipelines support automated   │
  │     │                                 │                                           │ Playwright E2E testing」                      │
  ├─────┼─────────────────────────────────┼───────────────────────────────────────────┼───────────────────────────────────────────────┤
  │     │ vercel-deploy                   │ インストール済みの vercel-deploy          │ https://skills.sh/supercent-io/skills-templat │
  │ O-4 │ スキルを使ってない（npx vercel  │ スキルを使う                              │ e/vercel-deploy — 1.6K installs               │
  │     │ deploy 直打ち）                 │                                           │                                               │
  ├─────┼─────────────────────────────────┼───────────────────────────────────────────┼───────────────────────────────────────────────┤
  │     │ Anicca → Claude Code            │ OpenClaw + Ralph ループ統合（OpenClaw RFC │ https://github.com/openclaw/openclaw/discussi │
  │ O-5 │ の起動方式が単発（OpenClaw exec │  で議論済み）                             │ ons/10320 — 「RFC: Claude Code + Ralph Loop   │
  │     │  で1回起動して終わり）          │                                           │ skill for autonomous development」            │
  └─────┴─────────────────────────────────┴───────────────────────────────────────────┴───────────────────────────────────────────────┘

  ---
  3. 各質問への回答

  Q1: 対話モード vs 非対話モード

  ┌────────────────┬───────────────────────────────┬───────────────────────────────────────────────────┐
  │      比較      │   対話モード（interactive）   │           非対話モード（-p / --print）            │
  ├────────────────┼───────────────────────────────┼───────────────────────────────────────────────────┤
  │ 実行方法       │ claude で REPL 起動           │ claude -p "prompt" --dangerously-skip-permissions │
  ├────────────────┼───────────────────────────────┼───────────────────────────────────────────────────┤
  │ コンテキスト   │ 1セッション内で蓄積（溢れる） │ 各呼び出しが新鮮（Ralph パターン）                │
  ├────────────────┼───────────────────────────────┼───────────────────────────────────────────────────┤
  │ 自動化         │ 手動入力が前提                │ CI/CD・cron・スクリプトに最適                     │
  ├────────────────┼───────────────────────────────┼───────────────────────────────────────────────────┤
  │ Ralph          │ 使わない                      │ :white_check_mark: Ralph は --print を使う                        │
  ├────────────────┼───────────────────────────────┼───────────────────────────────────────────────────┤
  │ Anthropic 推奨 │ 開発時                        │ Headless/自動化時は -p                            │
  └────────────────┴───────────────────────────────┴───────────────────────────────────────────────────┘

  結論: 非対話モード（-p）が正解。

  ソース: https://code.claude.com/docs/en/headless — 「The --print flag runs Claude Code in non-interactive mode for automation,
  scripting, and CI/CD integration.」
  ソース: https://github.com/snarktank/ralph/blob/main/ralph.sh — claude --dangerously-skip-permissions --print < "$SCRIPT_DIR/CLAUDE.md"
  ソース: https://github.com/openclaw/openclaw/blob/main/skills/coding-agent/SKILL.md — pty:true + -p の組み合わせ

  現在の webapp-factory: 既に -p を使っている :white_check_mark: ただし単発呼び出し（O-1）

  ---
  Q2: Ralph ループ vs 単発呼び出し

  これが最大のオリジナリティ。

  ┌─ 現状（オリジナル = 悪い）──────────────────────────────┐
  │                                                         │
  │  claude -p "US-001〜US-007 全部やれ" で1回呼び出し       │
  │     │                                                   │
  │     ├─ コンテキストが US-004 あたりで溢れる              │
  │     ├─ 1回クラッシュしたら全部終わり                     │
  │     └─ リカバリ不可                                     │
  │                                                         │
  └─────────────────────────────────────────────────────────┘

  ┌─ Ralph パターン（ベストプラクティス）────────────────────┐
  │                                                         │
  │  ralph.sh ループ:                                       │
  │                                                         │
  │  while prd.json に passes:false がある:                  │
  │     ① prd.json から次の US（passes:false）を取得        │
  │     ② claude -p "この US をやれ" で1回呼び出し          │
  │     ③ 完了 → prd.json の passes を true に              │
  │     ④ git commit + push                                │
  │     ⑤ progress.txt に追記                               │
  │     ⑥ 次のイテレーション（新鮮なコンテキスト）          │
  │                                                         │
  │  利点:                                                  │
  │  ├─ 各 US が新鮮なコンテキストで実行される              │
  │  ├─ 1回クラッシュしても次のイテレーションで続行          │
  │  └─ prd.json + git history がメモリの役割               │
  │                                                         │
  └─────────────────────────────────────────────────────────┘

  ソース: https://github.com/snarktank/ralph — 「Each iteration is a fresh instance with clean context. Memory persists via git history,
  progress.txt, and prd.json.」
  ソース: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents — 「Every token you add to the context window
  competes for the model's attention—stuff a hundred thousand tokens of history into the window and the model's ability to reason about
  what actually matters degrades」

  ---
  Q3: E2E テスト

  今: L0 Gate（grep 8パターン）+ npm run build のみ。ブラウザテストゼロ。

  ベストプラクティス: Playwright で実際のブラウザ動作を確認する。

  ┌─ あるべき E2E フロー ──────────────────────────────────┐
  │                                                         │
  │  US-005 で:                                             │
  │  ① L0 Gate（grep 8パターン）                            │
  │  ② npm run build                                       │
  │  ③ npx playwright test（NEW — 追加必須）                │
  │     ├─ トップページ表示確認                              │
  │     ├─ Pricing ページのボタンクリック                    │
  │     ├─ Stripe Checkout へのリダイレクト確認              │
  │     └─ 全ページの 404 チェック                           │
  │                                                         │
  └─────────────────────────────────────────────────────────┘

  ソース: https://github.com/0xAxiom/AppFactory — 「UI-generating pipelines support automated Playwright E2E testing when configured」
  ソース: https://www.browserstack.com/guide/automation-pipeline — 「Automated end-to-end tests verify the complete user journey」

  ---
  Q4: Slack 報告 + X 投稿

  Slack: openclaw system event → Anicca が受信 → Slack #metrics に転送。:white_check_mark: これは OpenClaw パターンで正しい。

  X 投稿: :x: prompt.md に入ってない。 v1 spec には書いてあった（Postiz CLI）のに俺が入れ忘れた。

  ┌─ あるべき LAYER 4 ────────────────────────────────────┐
  │                                                        │
  │  US-007 で:                                            │
  │  ① AGENTS.md 作成                                     │
  │  ② Slack 報告（system event → Anicca → Slack）         │
  │  ③ X 投稿（Postiz CLI）← 今ない、追加必須              │
  │     postiz posts:create                                │
  │     「Just shipped: {app} — {pitch} :rocket: {url}           │
  │      #BuildInPublic #indiehacker」                     │
  │  ④ COMPLETE system event                               │
  │                                                        │
  └────────────────────────────────────────────────────────┘

  ソース: https://docs.postiz.com/usage/cli — 「CLI-based social media posting」

  ---
  Q5: テスト実行の方法（temporal cron）

  やるべきこと: 今日だけの一時 cron を Anicca（OpenClaw）の jobs.json に追加して、webapp-factory を1回テスト実行する。

  ┌─ テスト実行フロー ─────────────────────────────────────┐
  │                                                        │
  │  ① jobs.json に一時エントリ追加（5分後に1回だけ実行）   │
  │  ② Anicca が SKILL.md を読む                           │
  │  ③ Claude Code を -p で起動                            │
  │  ④ Claude Code が prompt.md を読んで全 US を実行       │
  │  ⑤ Slack に進捗報告が流れる                             │
  │  ⑥ 完了後、一時エントリを削除                           │
  │                                                        │
  │  確認方法:                                              │
  │  ssh anicca@100.99.82.95 -t "tmux attach -t webapp"   │
  │                                                        │
  └────────────────────────────────────────────────────────┘

  ---
  4. オリジナリティ修正アクション（全5件）

  ┌─────┬───────────────────┬──────────────────────────────────────────┬──────────────────────────────────────────────────────────────┐
  │  #  │  オリジナリティ   │                 修正内容                 │                            ソース                            │
  ├─────┼───────────────────┼──────────────────────────────────────────┼──────────────────────────────────────────────────────────────┤
  │ O-1 │ 単発 -p 呼び出し  │ Ralph ループ（ralph.sh）を導入。各 US    │ https://github.com/snarktank/ralph                           │
  │     │                   │ を独立した -p イテレーションで実行       │                                                              │
  ├─────┼───────────────────┼──────────────────────────────────────────┼──────────────────────────────────────────────────────────────┤
  │ O-2 │ X 投稿なし        │ prompt.md の US-007 に Postiz CLI で X   │ https://docs.postiz.com/usage/cli                            │
  │     │                   │ 投稿を追加                               │                                                              │
  ├─────┼───────────────────┼──────────────────────────────────────────┼──────────────────────────────────────────────────────────────┤
  │ O-3 │ E2E テストなし    │ prompt.md の US-005 に Playwright        │ https://github.com/0xAxiom/AppFactory                        │
  │     │                   │ テストを追加                             │                                                              │
  ├─────┼───────────────────┼──────────────────────────────────────────┼──────────────────────────────────────────────────────────────┤
  │ O-4 │ vercel-deploy     │ npx vercel deploy → vercel-deploy        │ https://skills.sh/supercent-io/skills-template/vercel-deploy │
  │     │ スキル未使用      │ スキルを使うに変更                       │                                                              │
  ├─────┼───────────────────┼──────────────────────────────────────────┼──────────────────────────────────────────────────────────────┤
  │ O-5 │ 単発起動          │ OpenClaw + Ralph ループ統合。SKILL.md    │ https://github.com/openclaw/openclaw/discussions/10320       │
  │     │                   │ の起動コマンドを ralph.sh パターンに変更 │                                                              │
  └─────┴───────────────────┴──────────────────────────────────────────┴──────────────────────────────────────────────────────────────┘

  ---
  結論: 今の状態は 5つのオリジナリティ がある。全部修正しないと「ベストプラクティス完コピ」にならない。特に O-1（Ralph ループ）
  が最も重要。単発呼び出しでコンテキストが溢れたら全部死ぬ。

  Sources:
  - https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
  - https://www.anthropic.com/engineering/claude-code-best-practices
  - https://github.com/snarktank/ralph
  - https://github.com/snarktank/ralph/blob/main/ralph.sh
  - https://github.com/openclaw/openclaw/blob/main/skills/coding-agent/SKILL.md
  - https://github.com/openclaw/openclaw/discussions/10320
  - https://code.claude.com/docs/en/headless
  - https://github.com/0xAxiom/AppFactory
  - https://docs.postiz.com/usage/cli
  - https://skills.sh/supercent-io/skills-template/vercel-deploy