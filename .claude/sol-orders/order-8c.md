# 発注: spec §10 順8c — LM-33c panel UI（5要素、read-only 鏡）

正本: /Users/anicca/anicca-project/docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md
必読節: §9.9（5要素と「鏡」原則）、§9.6（gate 表 — gate 画面は discovery の Web 側入口）。前提: 8a 認証 + 8b API 5本が origin/dev に merge 済み（PR #326/#327）。
必読 skill（順序厳守 — global CLAUDE.md「フロントエンド作成順序」）: まず ~/.claude 系 skills の `gpt-tasteskill`（設計規律）を読み、次に `frontend-design` skill に従って実装。順序を変えるな。
役割: Sol = build+execute+verify+spec 更新+commit+push。質問 = bash ~/.agents/skills/agmsg/scripts/send.sh lm-p0 sol-order8c fable-main '<msg>'。
対象: anicca-products、worktree .worktrees/lm-p0-order8c（base = 最新 origin/dev）、branch feature/lm33c-panel-ui → PR to dev。GHA 追加可。

## 仕様
1. GET /panel（session 必須）が返す server-rendered ページ（既存 server.js は素の node http — 重い framework を持ち込まない。template literal + 最小 CSS/JS で足りる。React/Next 等の新規依存は禁止）。
2. 5要素を §9.9 の順で: ①今日 timeline（call 実績✅マーク付き）②3 organ スコア（no_data の organ は「準備中」と正直表示 — 偽メーター禁止）③FINANCIAL 台帳（空なら「まだ収益はありません」）④gates 状態（未解錠 gate は §9.11 discovery copy の解錠方法つき）⑤設定（read-only 表示。call_language / call_schedule / 接続状態）。
3. データは 8b の /api/panel/* を fetch（同一 origin、session cookie）。
4. モバイル幅（375px）で崩れない。dark 対応は不要（v1）。
5. i18n: 文言は ja。§9.11 と同じ voice（有能な秘書兼友人）。

## 検証
npm test 全 green。ローカルで server 起動 + fixture session で /panel を **実ブラウザ相当（playwright-cli か curl + HTML 検証 script）** で取得し、5要素の DOM 存在を assert する test/script の exit 0 実出力。full-page screenshot が撮れる環境なら撮って path を報告（Fable が見る）。

## 禁止
新規 heavy 依存（React/Next/Tailwind CDN 等）/ 書き込み UI / 偽データ表示 / prod deploy / secret 出力。

DONE 報告 agmsg: test 実出力 + 5要素 assert 結果 + screenshot path（あれば）+ PR URL。
