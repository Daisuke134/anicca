# BlockRun MCP / Franklin — tool-call ベストプラクティス調査（2026-07-13）

## 背景

`runtime/loop/brain.mjs` の `claude -p` 経路は、tool schema を渡すチャネルが無いと仮定し、
プロンプト本文に JSON の形（`{"tool_calls":[{"function":{"name":"run_skill",...}}]}`）を手書きし、
モデルにテキストでそれを模写させて自前パースしていた。これが車輪の再発明かどうかを調査した。

## 1. blockrun-mcp — MCP server がツールを定義・公開する方法

出典: `github.com/BlockRunAI/blockrun-mcp`（`gh api` で直接取得、`gh repo clone` は不使用）

- `src/index.ts`: `@modelcontextprotocol/sdk` の `McpServer` + `StdioServerTransport` で stdio MCP server を起動。
  > `const server = new McpServer({ name: "blockrun-mcp", version: VERSION }); ... await server.connect(transport);`
- `src/mcp-handler.ts`: profile ごとにツールを `server.registerTool` する registrar 関数群を条件付きで実行（トリムされた profile は除外ツールのスキーマすら読み込まない）。
- `src/tools/wallet.ts`: 1ツール = `server.registerTool("blockrun_wallet", { description, inputSchema: { action: z.enum([...]).optional()..., ... } }, async (args) => {...})`。
  **スキーマは Zod で機械可読に定義**され、description は自然言語の使い方ガイド（「Call this FIRST if...」等）。
  これがまさに `~/.claude/rules/building-effective-ai-agents.md` の SOURCE 2（Writing Tools for Agents）が言う
  「ツールは deterministic system と非決定的 agent の contract」「description をプロンプトエンジニアリングする」の実例。

→ 結論: ツール定義は **MCP SDK 標準の `registerTool` + Zod schema** で行う。「プロンプトに JSON 形を手書き」という発想はここには一切無い。

## 2. `claude -p` から MCP tool を呼ぶ正しい方法 — 確認済み

出典: ローカル `claude --help`（このセッションの `claude` CLI 自体、公式）

```
--mcp-config <configs...>     Load MCP servers from JSON files or strings (space-separated)
--strict-mcp-config           Only use MCP servers from --mcp-config, ignoring all other MCP configurations
```

**`claude -p` は `--mcp-config` で MCP server を読み込め、ツールを標準の tool-call チャネルで使える。**
`--strict-mcp-config` を足せば、ambient な project `.claude/mcp` や CLAUDE.md 由来の MCP 設定を無視して
明示的に渡した1個の MCP server だけをロードできる（brain.mjs が「project の `.claude` を読み込むとハングする」
としてわざわざ neutral cwd に逃がしている問題 — `runtime/loop/brain.mjs:219-222` — を根本的に回避できる可能性がある）。

→ 「プロンプトに JSON の形を手書きしてテキストで返させ自前パースする」は **完全に不要** — MCP 経由なら
標準の tool-call プロトコルで機械可読にやり取りできる。

## 3. Franklin — 同じ問題をどう解いているか

出典: `github.com/BlockRunAI/Franklin`

- Franklin は `claude -p` を一切使わない。**自前の agent loop**（`src/agent/loop.ts`）を持ち、
  自前の LLM client 抽象（`client.complete({ model, messages, tools: callToolDefs, ... })`）に
  **常にネイティブな `tools:` スキーマを渡す**（`src/agent/loop.ts:1476` 付近）。弱いモデル向けの
  「ツール名を勝手に発明するな」というプロンプト補強（`src/agent/loop.ts:1418-1427`、`isWeakModel` 分岐）は
  **ネイティブ tool schema に "追加" するガードレール**であって、schema の代替ではない。
- MCP との統合は `src/mcp/client.ts`: discovery した MCP tool を `CapabilityHandler`
  （`{ spec: { name, description, input_schema }, execute }`）にラップし、ネイティブツールと**同じ形**で
  agent loop に混ぜる。`buildToolCapabilities()` が `mcp__<server>__<tool>` という名前空間で登録する
  （`src/mcp/client.ts` の `buildToolCapabilities`）。
- `src/mcp/config.ts`: `blockrun` 自身の MCP server を `blockrun-mcp` バイナリとして built-in 登録し、
  さらに `codegraph` も built-in。project の `.mcp.json` は明示的な trust marker
  （`~/.blockrun/trusted-projects.json`）が無いと読み込まない — MCPの信頼境界を明示的に扱っている。

→ Franklin は「LLM に判断させる」箇所を**全部ネイティブ tool-call**で解いており、テキスト JSON の手書きパースは存在しない。

## 4. brain.mjs を MCP に置き換えられるか

現状（`runtime/loop/brain.mjs:182-217`）:
> 「The proxy path hands the model a machine-readable tool SCHEMA... `claude -p` gets no such channel — it sees text and nothing else. So the schema has to be written INTO the text」

この前提は**誤り**——`--mcp-config` で機械可読チャネルは存在する。ただし単純な3-5行差し替えではない、重要な非対称性が1つある:

- proxy 経路: `tool_calls` は brain.mjs 自身が受け取り、どのスキルを実行するかを**外側の JS が決めて実行**する（decision-only）。
- MCP 経由 `claude -p --dangerously-skip-permissions`: claude 自身が MCP tool を**呼び出して実行**してしまう
  （tool 実行は claude プロセス内部で起きる）。`run_skill`/`sleep` を「実際にスキルを実行するツール」として MCP 定義すると、
  意味論が変わる（brain=判断だけ、実行は外側、という現状の分離が崩れる）。

## まとめ

`--mcp-config`/`--strict-mcp-config` は実在し、`claude -p` は MCP 経由でネイティブ tool-call を使える。
brain.mjs の「プロンプトに JSON 手書き→自前パース」は不要な車輪の再発明だったと確認できた。
