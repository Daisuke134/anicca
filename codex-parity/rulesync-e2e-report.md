# rulesync Phase 1 E2E report

実測日: 2026-07-20  
固定版: `rulesync@14.1.0`  
対象: Claude Code から import、Codex CLI のみ generate

## 結論

`npx -y rulesync@14.1.0 --version` は、隔離した npm cache を使うと `14.1.0` を返した。Phase 1 の方向性は妥当だが、現状の `.claude/skills` をそのまま「`.claude` だけコピーした sandbox」で import すると symlink が切れ、skills import が途中で停止する。本適用前に symlink の参照先も staging へ含める必要がある。

また、生成された `AGENTS.md` は現行の短い手書き版を置き換える 493 行の全文結合になる。自動適用前に、グローバル Claude 設定への参照、Claude 固有 hook/agent 記述、重複見出しが Codex に適切かを人間が確認すべきである。

## 実測手順

repo の `.claude/{rules,skills,commands}`、`CLAUDE.md`、`.mcp.json` だけを `mktemp -d` 配下へ `cp -a` し、実 HOME を使わず実行した。既存 `~/.npm/_cacache` は root-owned で `EPERM` になったため、`npm_config_cache` も別の一時 directory にした。

```bash
npm_config_cache="$TEMP_CACHE" npx -y rulesync@14.1.0 --version
npm_config_cache="$TEMP_CACHE" npx -y rulesync@14.1.0 import --targets claudecode --features '*' --verbose
HOME="$TEMP_HOME" npm_config_cache="$TEMP_CACHE" npx -y rulesync@14.1.0 generate --targets codexcli --features '*' --dry-run --verbose
```

dry-run 後には `AGENTS.md`、`.agents/`、`.codex/` のいずれも存在せず、書込み0件であることも確認した。その後、生成物を検分するため同じ sandbox と一時 HOME で dry-run なしの generate を行った。実 repo と実際の `~/.claude` / `~/.codex` には適用していない。

## import 結果

### 拾えたもの

- root `CLAUDE.md` 1件と `.claude/rules/*.md` 9件を `.rulesync/rules/` の計10件へ変換。
- `.claude/commands` の Markdown 30件を `.rulesync/commands/` へコピー。
- `.mcp.json` の `conway` と `serena` を `.rulesync/mcp.json` へ import。
- ignore configuration 1件を `.rulesync/.aiignore` へ import。

### `paths` frontmatter

Claude Code の `paths:` は消失せず、Rulesync 共通形式の `globs:` と `claudecode.paths:` の両方へ変換された。例:

```yaml
# source
paths:
  - "**/*.ts"

# imported
root: false
targets:
  - '*'
globs:
  - '**/*.ts'
claudecode:
  paths:
    - '**/*.ts'
```

したがって意味は保持される。ただしキーと quote style はそのまま保持されるわけではない。また Codex CLI は path-scoped rules をネイティブに分割せず、今回の generate では全10 rules が単一 `AGENTS.md` に連結された。つまり Codex 側では Claude の `paths` と同じ条件付き読込みにはならない。

### 落としたもの / 中断点

- source の `.claude/skills` は top-level 108 entries（40 symlinks、66 real directories、ほか2 entries）。
- `.claude` だけをコピーした sandbox では、`../../.agents/skills/...` を指す相対 symlink が参照先不在になった。
- import は `SKILL.md not found in .../.claude/skills/humanizer-ja` で停止した。
- その時点で `.rulesync/skills` は作られず、skill は0件。symlink 自体も `.rulesync` へ保持されなかった。
- import は原子的ではない。失敗前に rules、commands、MCP、ignore を書き終えており、部分生成物を残した。
- `.claude/agents` は入力に含めていないため subagents は0件。hooks と permissions も `.rulesync` には生成されなかった。

この試験だけから「rulesync が有効な symlink を追跡できない」とは断定できない。確実に言えるのは、symlink referent を含めない隔離コピーでは追跡不能になり、最初の不正 skill で全 skills import が止まること。本適用スクリプトは `.agents` も staging へコピーし、`find -L` で broken link を先に拒否する。

## Codex CLI 生成物

skills import 中断後の `.rulesync` からの dry-run は次の2ファイルだけを予告した。

- `AGENTS.md`: rules 10件を連結、493行。
- `.codex/config.toml`: MCP 2件、8行。

`.agents/` は生成されなかった。Codex CLI target は `ignore`、`commands`、`checks` を未対応として skip した。subagents と skills は入力0件、hooks と permissions は対応ファイル不在のエラーを表示した。

`.codex/config.toml` は `conway` と `serena` を保持したが、Serena の引数には元の絶対 project path `/Users/anicca/anicca-project` が残るため portable ではない。

## 現行手書き `AGENTS.md` との差分要約

- 現行は40行、生成版は493行。unified diff は523行。
- 現行の「ツール既定」「検索優先」「Push 規律」「spec = SSOT」「Skills」という Codex 向け要約は、root `CLAUDE.md` と9 rules の全文連結に置換される。
- 生成版には現行要約の趣旨の一部はあるが、現行の明示的な CodeGraph → Serena → `rg` 順序、skill root の説明などは同一文面では保持されない。
- `CLAUDE.md` 内の `~/.claude/CLAUDE.md`、Claude hook、Claude agent、TaskCreate/TaskUpdate など Claude 固有の参照が Codex 側にも入る。
- root rule と個別 rule の双方に参照があるため、「ANICCA COLONY」「開発」「ブランチ & デプロイ」などが重複する。
- Claude の path-scoped rules も Codex では常時読み込まれる単一文書になるため、context 固定費と適用範囲が増える。

## 本適用の推奨手順

1. `rulesync@14.1.0` は range や `latest` を使わず完全固定する。
2. Phase 1 は package install を増やさず `npx -y rulesync@14.1.0` 固定を推奨する。理由は、移行・検証用の低頻度 tool であり、今回の repo に root `package.json` があることを前提に dependency graph や lockfile を変更する必要がないため。CI で常用する段階になったら root package manager を確定した上で exact devDependency (`"rulesync": "14.1.0"`) に移し、lockfile も review する。
3. `codex-parity/apply-rulesync.sh` を repo root から実行する。script は一時 repo/HOME/cache で import と dry-run を先に行い、broken symlink または import failure で停止する。
4. 固定 `.bak` が作られたこと、変更パスが `.rulesync/**`、`AGENTS.md`、`.agents/**`、`.codex/**` の allowlist 内だけであることを確認する。
5. 生成 `AGENTS.md` を人間が review し、Claude 固有記述と path-scoped rule の常時化を許容できる場合だけ commit する。Phase 1 では `generate --targets claudecode` を実行しない。

## 落とし穴

- npm cache の ownership 問題でも `npx` は失敗する。一時 `npm_config_cache` なら実 HOME を変更せず回避できる。
- import は部分書込みを残すため、終了 code の確認なしに `.rulesync` を採用してはいけない。
- symlink の見かけ上の copy だけでは不十分。referent を staging の同じ相対位置へ置く必要がある。
- 1つの欠損 `SKILL.md` が skills 全体を0件にし得る。
- `--features '*'` は target 非対応 feature の skip や、入力ファイル不在の警告を出す。成功表示だけで coverage を判断しない。
- `--dry-run` は生成内容そのものを保存しない。実物 review には隔離 sandbox で通常 generate が必要。
- MCP の絶対 path、秘密値、環境依存 command/args がそのまま生成され得る。
- `.bak` は初回 snapshot を保持する設計なので、再実行しても上書きしない。新しい backup が必要なら既存 `.bak` を明示的に退避する。

