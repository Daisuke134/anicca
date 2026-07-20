# Context floor 監査（2026-07-20 実測）

新session 起動時 134.5k/200k (67%) の内訳監査と削減根拠。spec: `docs/superpowers/specs/2026-07-20-context-floor-and-handover-simplify-spec.md`

## 公式仕様（確定・出典付き）

| 事実 | 出典 |
|---|---|
| `permissions.deny` の bare tool 名は schema を context から**除去**する。scoped（`Bash(rm *)`）は実行拒否のみ | code.claude.com/docs/en/permissions.md "As a deny rule, both forms remove the tool from Claude's context." |
| `includeGitInstructions: false` で git instructions + status snapshot が system prompt から消える（~2.2k） | settings.md |
| `.claude/rules/*.md` + frontmatter `paths:` は起動時ロードされない。該当ファイルを読む時のみ | memory.md "Path-scoped rules trigger when Claude reads files matching the pattern" |
| `@import` は launch 時にロードされる = floor 削減にならない | memory.md "imported files still load at launch" |
| serena は `~/.serena/serena_config.yml` の `excluded_tools:` で global 除外可 | oraios/serena serena_config.template.yml |
| plugin agent の完全 unload は plugin 単位 disable のみ | plugins-reference.md |
| SessionStart hook stdout は毎 session context 注入（上限10k chars） | hooks.md |

## SessionStart hooks 実測（11本、安全実行6本 = ~1,331 tok）

最大 = token-saver `git-context-lite.sh` ~588 tok、project session-start.sh ~279 tok、token-saver session-architecture.md ~243 tok。未実測5本（副作用持ち）: cozempic inline / floor-guard / token compact / statusline patch / caveman activate。

## Loaded agents 14体（desc計 ~1.4k tok、body計 ~12k tok）

project 4 + user 2 + plugin 8（vcsdd 4 / superpowers 1 / caveman 3）。floor に常時載るのは description 側。body は起動時のみ。

## Memory files 4本 = ~6.5k tok（floor-guard 換算）

- global CLAUDE.md 2,134 tok（大節: TOKENの物理 334 / モデル分業 341 / No-human-loop 212 / GLVS 211 / ツール既定 207）
- project CLAUDE.md 1,497 tok（COLONY SSOT 306 / 実行環境 269 / spec=SSOT 242）
- MEMORY.md 2,800 tok（規律 911 / 運用の地雷 506 / 作り方 493 / 金 309 / browser 216）
- CLAUDE.local.md 83 tok

### paths: 化候補（高優先のみ）
| 節 | 移設先 paths | 削減 |
|---|---|---:|
| project Life Manager 行 | `apps/life-call/**` | 101 tok |
| project iOS deploy/E2E | `aniccaios/**` | 49 |
| project GHA 禁止 | `.github/workflows/**` | 26 |
| global frontend 順序 | `**/*.tsx` 等 | 28 |
| MEMORY 金セクション | `**/earn/**` 等 | 309（file 非依存の質問で取りこぼしリスクあり） |
| MEMORY browser/OS | browser 系 paths | 216（同上） |

### paths 化より先: MEMORY.md ↔ CLAUDE.md 重複削除候補
「次を聞かない」「Task登録」「検索優先」「token/adversary 制限」「研究即MD化」「捏造禁止」の6項目が global/project CLAUDE.md と重複。索引1行化 or 削除で ~200-400 tok。

## 落とし穴（棄却済み含む）
- agent 本文短縮 → floor に載らないので無効（棄却）
- scoped deny（`Read(**/*.pem)` 等）→ schema 削減にならない
- `/context` 表示は raw 課金と乖離（issue #71301）。効果測定は window と raw の両方で
- window 削減 ≠ 課金削減（今回 46.5k window 減でも raw floor は不変を実測済み）
