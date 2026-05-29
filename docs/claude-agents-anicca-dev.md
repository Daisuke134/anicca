# Claude Agents — Anicca 並列開発セッション集約 (#28)

> Dais 用 quick-reference。Claude Code 2.1.153 で `claude agents` 利用可能。

## なぜ要るか

Anicca 開発は同時に複数 task を進めることが多い:

- Phase B/C: #22 Recall.ai POC / #23 Avatar / #24 reveal.js / #25 deck-gen / #34 flip-render を並走
- HyperAgent 採択後: $20k 推論枠を消化するため N event 並列実演 (#26/#38)
- 課金 SaaS cutover (#32) 中の旧/新 bridge 並走運用

これらを1つの terminal で「Working / Needs Input / Completed」で集約するのが `claude agents`。

## 起動

```bash
claude agents
```

各セッションへの引数(`--model`, `--add-dir` 等)はそのまま渡せる。例:

```bash
# Anicca プロジェクト配下のセッションだけ集約
claude agents --cwd /Users/anicca/anicca-project

# 並列実装するときは bypass permissions で噛みつかせない
claude agents --dangerously-skip-permissions --effort high

# Anicca dev で必要な MCP は serena (lsp) と GitHub
claude agents --mcp-config ~/.claude/mcp-anicca.json
```

## Anicca 開発のおすすめ session 構成

| Session | 担当 | 起動例 |
|---------|------|--------|
| 1 | 起こし電話/lateness Pipecat 監視 | `claude --cwd /Users/anicca/anicca-oss-pipecat` |
| 2 | Phase B 会議 Recall+HeyGen 実装 | `claude --cwd /Users/anicca/anicca-oss-pipecat` |
| 3 | Phase C flip-render + reveal.js | `claude --cwd /Users/anicca/anicca-oss-pipecat` |
| 4 | spec / docs 更新 | `claude --cwd /Users/anicca/anicca-oss-livekit` (spec ファイル所在) |
| 5 | HyperAgent fund 後の inference 予算管理 | `claude --cwd /Users/anicca/anicca-project` |

`claude agents` を立ち上げてから、各 session の prompt を貼って実行 → 自動で「Working」状態でリストに並ぶ → 完了 / 入力待ちで自動カテゴリ移動。

## キーバインド

| key | 動作 |
|-----|------|
| ↑↓ | session 選択 |
| ↩ | session に enter |
| ← | session 一覧に戻る |
| q | 終了 |

## 並列実装は禁止 (HARD RULE)

Claude Code agent view = Dais の「俯瞰する」ツールであって、実装そのものを並列に投げる場ではない。

memory `feedback_no_parallel_implementation.md` 参照: **実装は1個ずつ順次、サブエージェントへの並列 dispatch は中途半端な garbage を生む**。Claude agents は調査・docs 整理・別 worktree の git 操作など独立な作業を並走させる用途で使う。

## 公式ドキュメント

- https://code.claude.com/docs/en/agent-view
- `claude agents --help` (出力 30 行、全 option 表示)

---

最終更新: 2026-05-29 (Claude Code 2.1.153 検証済)
