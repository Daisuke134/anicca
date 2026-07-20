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
| 3 | floor削減実施（agents剪定・plugin/MCP無効化・MEMORY剪定） | Sol | pending |
| 4 | E2E検証（floor-guard + /context + handoverテンプレ） + push | Fable | pending |

## 実測メモ
- /context 実測（2026-07-20）: system prompt 27k / tools 38.9k / MCP 28.9k / agents 53.6k（26体×~2k） / memory 22.1k / skills 3k。free 20.7k。
- agents はプロジェクト `.claude/agents/` 26体が全ロード。plugin由来（caveman/vcsdd/codex/superpowers）含む。
