# SessionStart hook audit

計測日: 2026-07-20。入力は synthetic SessionStart JSON、各 command は独立実行した。
Cozempic は自己更新だけ `COZEMPIC_NO_AUTO_UPDATE=1` で抑止した。tokenizer の BPE
data が network sandbox 内に無かったため、PLAN の既存実測と同じく stdout 文字数 / 4
を token 近似値とした。改行末尾は command substitution により除外される。

## 全列挙と stdout 実測

| scope / JSONPath | matcher | command | chars | approx tok |
|---|---:|---|---:|---:|
| user `.hooks.SessionStart[0].hooks[0]` | `*` | `~/.claude/hooks/ssot-guard.sh` | 476 | 119 |
| user `.hooks.SessionStart[0].hooks[1]` | `*` | `~/.claude/hooks/disk-guard.sh` | 165 | 42 |
| user `.hooks.SessionStart[1].hooks[0]` | empty | Cozempic v14 digest injection + guarded background reload/daemon command（settings 内の inline command） | 22 | 6 |
| user `.hooks.SessionStart[1].hooks[1]` | empty | token-optimizer `measure.py compact-restore --new-session-only` launcher | 298 | 75 |
| user `.hooks.SessionStart[2].hooks[0]` | `compact` | token-optimizer `measure.py compact-restore --compact` launcher | 261 | 66 |
| user `.hooks.SessionStart[3].hooks[0]` | none | `python3 ~/.claude/scripts/floor-guard.py || true` | 269 | 68 |
| project `.hooks.SessionStart[0].hooks[0]` | none | `.claude/hooks/scripts/session-start.sh` | 977 | 245 |

通常 startup で発火する近似合計は 555 tok（`compact` matcher の 66 tok は除外）。
実 command の完全な文字列は `~/.claude/settings.json` と
`.claude/settings.json` の上記 JSONPath が SSOT である。長い inline command を
この監査へ複製すると drift するため、JSONPath と固有引数で列挙した。

## 削減提案

| hook | 判断 | 根拠と変更 |
|---|---|---|
| ssot-guard | 削除 | stdout は global/project CLAUDE.md と重複する静的規律。必要な開発規律は path-scoped rules にある。119 tok/呼出を削減。 |
| disk-guard | 維持 | 実ディスク残量に依存する動的警告。通常時は silent、今回の 42 tok は low-disk 警告。 |
| Cozempic v14 | 維持 | session transcript に依存する動的 digest。今回 6 tok。 |
| token-optimizer new-session / compact | 削除 | plugin は settings で disabled なのに stale hook が残存。通常 75 tok、compact 66 tok を削減。 |
| floor-guard | 1行化 | guard は実行し、stdout は最後の summary 1行だけにする。 |
| project session-start | command を1行化 | branch/date/rule数だけを出す。静的 DEV DISCIPLINE は path-scoped rules と重複。245 tok を削減。 |

設定変更案は [sessionstart-hooks.patch](sessionstart-hooks.patch) に、両 settings へ適用可能な
consumable jq rewrite patch として置いた。T4 の指定どおり自動適用せず、Fable が review/apply する。
