# Fable plan / Luna execute / Sol review — Claude Code 内で GPT-5.6 を分業させるハーネス

作成 2026-07-17。全行程 E2E 実測済み（Mac Mini `anicca-mac-mini-1`、Claude Code v2.1.210、CLIProxyAPI on :8317）。
元ネタ: tweet 2026-07-14「Fable to plan / Luna xhigh to execute / Sol xhigh to review. Don't overcomplicate.」

## 結論（動く形）

| 役割 | モデル | 呼び方 |
|---|---|---|
| 采配・plan・要件チェック | Claude Fable 5 | `claudexmix` で起動した main セッション |
| 実装 executor | GPT-5.6 Luna | claudexmix 内の**全 subagent**（env 既定）。xhigh が要る時は `luna-executor` agent を指名 |
| review・セカンドオピニオン | GPT-5.6 Sol xhigh | `solx "<プロンプト>"` one-shot（fresh context。どのセッションからでも可） |

追加 API 課金なし: Claude = Max サブスク OAuth、GPT-5.6 = ChatGPT Plus (Codex 枠) OAuth。両方 CLIProxyAPI が翻訳。

## 構成ファイル（このマシンの実物）

| 物 | 場所 |
|---|---|
| CLIProxyAPI（brew service、127.0.0.1:8317） | config = `/opt/homebrew/etc/cliproxyapi.conf` |
| proxy API キー | `~/.cli-proxy-api-key`（chmod 600） |
| OAuth creds（Claude Max + Codex Plus） | `~/.cli-proxy-api/` |
| `claudexmix` / `claudex` / `claudefable` / `solx` 関数 | `~/.zshrc`（「CLIProxyAPI / Claudex」節） |
| executor agent | `~/.claude/agents/luna-executor.md`（`model: sonnet` + `effort: xhigh` — proxy 内では env が model を Luna に上書き、direct では Sonnet に自然フォールバック） |
| 規則の焼き込み | `~/.claude/CLAUDE.md` モデル分業表 |

## zshrc（コピペ用。キーは各自の値に）

```zsh
export CLIPROXY_API_KEY="$(cat ~/.cli-proxy-api-key 2>/dev/null)"

# main = Fable 5、全 subagent = Luna
claudexmix() {
  env \
    ANTHROPIC_BASE_URL="http://127.0.0.1:8317" \
    ANTHROPIC_AUTH_TOKEN="$CLIPROXY_API_KEY" \
    CLAUDE_CODE_SUBAGENT_MODEL="gpt-5.6-luna" \
    CLAUDE_CODE_ALWAYS_ENABLE_EFFORT=1 \
    CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY=3 \
    ENABLE_TOOL_SEARCH=false \
    claude --model "claude-fable-5" "$@"
}

# Sol xhigh one-shot（review / セカンドオピニオン）
solx() {
  env \
    ANTHROPIC_BASE_URL="http://127.0.0.1:8317" \
    ANTHROPIC_AUTH_TOKEN="$CLIPROXY_API_KEY" \
    claude --model "gpt-5.6-sol" --effort xhigh -p "$@"
}
```

使い方例:

```
claudexmix          # Fable が采配、実装 subagent は勝手に Luna になる
solx "git diff HEAD~1 を読んで blocking bug を列挙。最後に PASS/FAIL だけ言え"
```

## ゼロから再現する手順（友人向け）

1. **CLIProxyAPI を入れる**: `brew install cliproxyapi`（または github.com/router-for-me/CLIProxyAPI のリリース）。config に `port: 8317` と自作 api-key を書き、`brew services start cliproxyapi`。
2. **認証2本通す**: `cliproxyapi --claude-login`（Claude サブスク）と `cliproxyapi --codex-login`（ChatGPT Plus）。ブラウザで承認するだけ。
3. **確認**: `curl -s -H "Authorization: Bearer <キー>" http://localhost:8317/v1/models` に `gpt-5.6-sol` / `gpt-5.6-luna` / `claude-fable-5` が並べば OK。
4. **上の zshrc をコピペ** → `source ~/.zshrc` → `claudexmix` で起動。
5. （任意）executor agent: `~/.claude/agents/luna-executor.md` を作り frontmatter に `model: sonnet` + `effort: xhigh`、本文に「spec 通り実装しテストを回してから返せ」系の指示。

## E2E 証跡（2026-07-17、全て実 tool_result）

| テスト | 結果 |
|---|---|
| `claude --model gpt-5.6-luna -p` one-shot | `LUNA-OK` |
| `claude --model gpt-5.6-sol -p` one-shot | `SOL-OK` |
| `--effort xhigh` 付き Sol one-shot | `SOLX-XHIGH-OK`、modelUsage = `gpt-5.6-sol` |
| claudexmix 構成で `luna-executor` を spawn | modelUsage に `gpt-5.6-luna`（in 4,861 / out 10 tok を実測） |

## ハマりどころ（全部実測で踏んだ。同じ穴を掘るな）

1. **`~/.claude/settings.json` の `env.CLAUDE_CODE_SUBAGENT_MODEL` が最強**。shell からの同名 env を潰す。ここに `claude-sonnet-5` が残っていたせいで subagent が全部 Sonnet に化けた。settings.json からは削除し、zshrc 関数側だけで渡す。
2. **agent frontmatter の `model: gpt-5.6-luna` は効かない**（未知 ID → Sonnet 5 に silent fallback。docs は gateway pass-through を謳うが v2.1.210 実測で否）。frontmatter に書いてよいのは Anthropic の alias/ID だけ。
3. **Agent tool の per-invocation `model` param は enum 固定**（sonnet/opus/haiku/fable）。`gpt-5.6-sol` を渡すと `InputValidationError`。
4. **`ANTHROPIC_DEFAULT_SONNET_MODEL` 等の alias redirect も subagent には効かない**（実測: sonnet-5 のまま）。
5. **`--model gpt-5.6-luna-xhigh` のような effort suffix はハング**（3分 timeout）。effort は `--effort xhigh`（one-shot）か agent frontmatter `effort: xhigh`（[docs](https://code.claude.com/docs/en/sub-agents): "effort — Overrides the session effort level. Options: low, medium, high, xhigh, max"）で渡す。
6. 帰結: **subagent に異種モデルを同時に混ぜる経路は存在しない**。生存経路 = `CLAUDE_CODE_SUBAGENT_MODEL`（全 subagent 一律）のみ。だから Sol review は subagent でなく one-shot（fresh context なのでレビュー品質的にもむしろ正解）。

## 実タスク通し証跡（2026-07-17、wordfreq ミニ spec で全ループ実走）

| 段 | 実測 |
|---|---|
| Fable 采配（headless claudexmix 構成） | spec を読み luna-executor に brief を出した |
| Luna 実装 | wordfreq.py + test_wordfreq.py 作成、modelUsage=`gpt-5.6-luna` |
| テスト | `uvx pytest` で **4 passed** を自分の目で確認、commit `7bb5dab` |
| Sol review（adversary 型 one-shot） | verdict.json を実書き込み、`{"verdict":"PASS","findings":[]}`、modelUsage=`gpt-5.6-sol` |

## VCSDD への配線（2026-07-17）

- **executor（vcsdd-builder）**: 編集不要。claudexmix の `CLAUDE_CODE_SUBAGENT_MODEL=gpt-5.6-luna` が subagent を強制 Luna 化（env は frontmatter より強い、という同じ物理で保証）。direct セッションでは従来どおり sonnet。
- **adversary**: subagent のままだと同じ env で Luna に潰されるため、plugin の command 3 ファイル（`vcsdd-adversary.md` / `vcsdd-spec-review.md` / `vcsdd-contract-review.md`、場所 = `~/.claude/plugins/marketplaces/vcsdd-claude-code/commands/`）に routing を追記: **proxy セッション（`$ANTHROPIC_BASE_URL` に 8317）なら Sol xhigh one-shot（Bash 経由の別プロセス = 完全ゼロ文脈で fresh context 要件はむしろ強化）、direct セッションなら従来の agent spawn**。上の表の Sol review 行が one-shot 型の実走証跡。
- 注意: この plugin は外部 clone（sc30gsw/vcsdd-claude-code）。marketplace 更新で上書きされたらこの節を見て再適用する。

## 別ルート（今日は未検証、後日）

- **Route A（公式 plugin）**: `claude plugin marketplace add openai/codex-plugin-cc` → `claude plugin install codex@openai-codex`（両方実行・インストール済み）。`/codex:review` / `/codex:adversarial-review` / `/codex:rescue` が生える。動作未検証。
- **agmsg（fujibee/agmsg v1.1.8）**: `npx agmsg` でインストール済み（`~/.agents/skills/agmsg/`）。Codex CLI で自走する Sol が plan 元の Fable に相談する Cross-agent messaging。E2E 未検証。
- Codex CLI 0.143.0 は ChatGPT ログイン済み（`codex login status` = "Logged in using ChatGPT"）。
