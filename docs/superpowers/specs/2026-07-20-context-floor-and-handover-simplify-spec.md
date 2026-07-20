# 2026-07-20 Context Floor削減 + /handover簡素化 spec

## 不変条件（全てMUST）
1. 起動時context消費（messages除く固定費）を現状 ~173k から **100k以下**へ。実測 = `/context` のカテゴリ合計。
2. Custom agents 53.6k（26体）: 使用実績のない agent 定義を削除 or plugin無効化で **20k以下**。
3. MCP tools 28.9k: 本sessionで常用しないserverを settings で無効化（blockrun はcolony作業時のみ必要 → project scopeから外しopt-inに）。Serena は残す。
4. Memory files 22.1k: MEMORY.md を索引密度を落とさず剪定（floor-guard 予算 9k 内）。
5. **/handover 出力 = 2ブロックのみ**:
   - **A. Start prompt**（talk-it-out用）: handover file path + spec file path を含み、新sessionへの指示は「specを読み、残TODO全件を列挙し、全TODO完了後のTO-BE像をASCIIで提示し、Daisと議論待ち」のみ。
   - **B. Go prompt**（全自走用）: 同じpath群 + 「残TODOを1番から全件完遂、no-human-loop」。
   - **禁止**: やったこと要約・経緯・成果リスト（spec=SSOTに書く。handoverに書くのは罪）。
6. 検証: 新形式で1回 /handover を dry生成し、2ブロック以外が無いことをFableが目視確認。floor は floor-guard.py + 新session `/context` 実測。

## TODO
| # | task | owner | state |
|---|---|---|---|
| 1 | best practice調査（agents/MCP/memory削減） | subagent | in_progress |
| 2 | /handover skill 書き換え | Sol | in_progress |
| 3 | floor削減実施（agents剪定・plugin/MCP無効化） | Sol | done |
| 4 | E2E検証（新session /context 実測） + push | Fable | done |

## 結果（2026-07-20 実測、新session /context）
- 179.3k/200k (90%) → **132.8k/200k (66%)**。free 20.7k → 67.2k（+46.5k）。
- MCP tools 28.9k → 10.5k（blockrun を project settings.local の disabledMcpjsonServers で停止。serena は残存）。
- Custom agents 53.6k → 29.1k（project agents 15→4体、plugin 7本 disable: codex/ccteams/revenuecat/security-guidance/clangd-lsp/token-optimizer/ui-ux-pro-max）。
- System tools 38.9k → 35.1k、Skills 3k → 2.9k（plugin disable の副次効果）。
- raw API floor 実測: total 60.5k（cache_read 51.3k + input 9.3k）— /context 表示より実請求はずっと小さい（表示過大バグ #71301 と整合）。
- Memory files 22.1k は未剪定（残TODO候補だが floor-guard 予算内のため今回は見送り）。
- 注意: .claude/agents は .cursor/agents への symlink だった。archive は .cursor/agents 側から git mv 済み。

## 調査結果（2026-07-20 subagent実測）
- `/context` の agents 53.6k は過大計上バグ疑い（issue #71301: 表示83.2kに対しraw API ~24k、agent各2k表示が実際59–174 tok）。raw裏取りまで削減見積りに使わない。
- agent 本文は main floor に載らない（name/description/toolsのみ）→ 本文短縮は効果なし（棄却）。
- 確定値: plugin always-on 合計 26,436 tok/session（vcsdd 6,117 + caveman 3,365 + superpowers 3,095 + codex 2,393 が上位）。`claude plugin details` 実測。
- MCP Tool Search: custom base URL（CLIProxyAPI :8317）では既定OFF。`ENABLE_TOOL_SEARCH=true` で試せるが proxy が tool_reference 非対応なら壊れる（要小実験）。
- `permissions.deny: ["Agent(name)"]` は実行禁止のみで floor は減らない。
- 裁定: plugin 7本 disable（codex/ccteams/revenuecat/security-guidance/clangd-lsp/token-optimizer/ui-ux-pro-max）、keep 6本（vcsdd/caveman/superpowers/swift-lsp/fablize/claude-code-token-saver）。project agents 15→4体（builder/qa-reviewer/fact-checker/deploy-checker、他は agents-archive へ）。blockrun は project settings.local で無効化を試行。

## 実測メモ
- /context 実測（2026-07-20）: system prompt 27k / tools 38.9k / MCP 28.9k / agents 53.6k（26体×~2k） / memory 22.1k / skills 3k。free 20.7k。
- agents はプロジェクト `.claude/agents/` 26体が全ロード。plugin由来（caveman/vcsdd/codex/superpowers）含む。
