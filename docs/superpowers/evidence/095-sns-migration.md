# #9.5 SNS factory 移行 — 準備（退役は Dais 明示 go まで着手禁止）

正本: spec §8 #9.5。Done = **準備済かつ Dais go で正しく blocked**。退役/削除は Dais 明示 go まで着手しない。

## 移行対象の実態（2026-07-11 実測）
- **SNS factory live cron = 51本**（`openclaw cron list` で larry/reelclaw/watercolor/lm-video 系を grep）。
- **launchd 依存 = 5**（larry/reelclaw/watercolor/clip 系）。
- これらは現在 `~/.openclaw`(OpenClaw body)で稼働。移行先 = claude-p manager loop（profitable-claude、§11 評価バー装着で self-improve 開始）。

## 移行計画（準備のみ、実行は go 後）
1. **各 SNS factory loop を claude-p 管理化**: larry/reelclaw/lm-video/watercolor を profitable-claude の registry に live loop として登録し、self-heal(cadence-deadline-check)+ §11 バー(BROKEN/STANDARD/IMPROVE)を装着。core spawn は今回修正した `env -u ANTHROPIC_API_KEY` + launchd PATH 込みの健全な形を使う（本 session の runtime 土台修正が前提）。
2. **cron を openclaw CLI で claude-p 側へ移設**（jobs.json 手編集禁止）。51本を段階移行し、二重稼働を避ける（OpenClaw 側を disable してから claude-p 側を enable、connector の一本化と同じ規律）。
3. **state/ledger を push で保全**（07-08 spec の gate: state/ledger push 確認）。
4. **OpenClaw 退役**: live cron 0 + launchd 依存 0 を確認 → OpenClaw body 削除。**← ここは Dais 明示 go まで絶対に着手しない**。

## 現在の状態: BLOCKED（正しく blocked）
- ✅ 準備（対象実態把握 + 移行計画 + 前提の runtime 土台修正は本 session で完了）済。
- ⛔ **退役/削除/cron 移設の実行は Dais 明示 go 待ち**（spec §8 #9.5 の gate、`~/.openclaw` 削除は CLAUDE.md 不可侵 store 規約 + go 必須）。
- go が出たら: 上記 1→2→3→4 を段階実行し、各段で live cron 本数を実測して二重稼働ゼロを確認。

## 次の Dais action
「#9.5 go」= SNS factory を claude-p へ移行し OpenClaw を退役してよい、の明示指示。それまで着手しない。
