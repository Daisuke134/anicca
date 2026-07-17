# blume ドキュメントツール調査（2026-07-17）

調査手段: `gh search`/`gh api` + `crwl`（WebSearch/WebFetch 不使用）。

## 正体

`blume` = npm パッケージ（[haydenbleasel/blume](https://github.com/haydenbleasel/blume)、MIT、668★、TypeScript）。
著者 Hayden Bleasel（`next-forge`/`Kibo UI` 等の作者、実績のある OSS メンテナ）。

> "Documentation for everything you build. Fast, AI-ready, and zero-config. Free and open
> source, forever." — [README](https://github.com/haydenbleasel/blume/blob/main/README.md)

`npx blume init` は Markdown/MDX フォルダを production-grade ドキュメントサイト（nav / 検索 / テーマ /
OGP / コンポーネント一式）に変換する CLI。内部で **Astro** プロジェクトを隠しディレクトリ `.blume/` に生成して
駆動する（`blume eject` で通常の Astro アプリとして取り出せる）。

npm registry 実測（`registry.npmjs.org/blume`）: 初版 2025-09-21、最新 `1.0.4` は 2026-07-15 公開（2日前、活発に
メンテ中）、30 バージョン、月間 DL 19,327（2026-06-16〜07-15）。

## 主な機能（README 記載、ソース: 上記 GitHub README）

- ゼロコンフィグ。`.md`/`.mdx` フォルダがあれば即プロジェクト
- 静的 HTML 出力（Astro + Vite、クライアント側フレームワークJSなし）→ `dist/`
- ローカル検索（Orama、外部サービス不要。Algolia/Typesense/Mixedbread等に後から切替可）
- **AI-ready**: `llms.txt` / `llms-full.txt`、任意ページの生 Markdown URL、Copy as Markdown、
  ホスト型 MCP サーバー（コーディングエージェントがドキュメントを直接検索・読解できる）
- Agent skills 同梱（コーディングエージェントにサイトの足場作り・執筆・保守を教える）
- OpenAPI/AsyncAPI をインタラクティブ API リファレンスとして描画（Scalar 経由）
- 多言語対応、SEO（OGP画像・sitemap・robots.txt・RSS・JSON-LD）
- Vercel/Netlify/Cloudflare Pages/GitHub Pages/S3+CloudFront など任意の静的ホストへデプロイ可、
  各アダプタ自動検出

## BlockRun が使っているツールか

**別物。BlockRun (`blockrun.ai/docs`) は blume ではない。** HTTP ヘッダ実測（`curl -sI`）で
`x-nextjs-cache` / `x-nextjs-prerender` ヘッダが確認でき、HTML 内に `Next`/`__NEXT_DATA__` 相当の
シグナルが検出された → **Next.js ベース**（Fumadocs 等の Next.js 系ドキュメントフレームワークの可能性が高いが、
断定はしない）。blume は Astro ベースなので技術スタックが異なる。「BlockRun と同じツールだから安心」という
推薦理由は成立しない — blume は独立の判断材料で評価する必要がある。

## anicca ドキュメントサイトへの適合判定: 採用推奨（条件付き）

**判定: ADOPT。** 理由:

1. **AI-ready がミッションと直接一致** — anicca の読者には人間だけでなく他の AI インスタンス
   （Franklin、他の Claude 等）が含まれる。`llms.txt`/生Markdown/MCP サーバーは「AI がドキュメントを
   読んで動く」を最初から前提にしたツールで、Docusaurus/VitePress にはない差別化点。
2. **無料で完全静的ホスト可能** — `blume build` で `dist/` に静的HTML、Netlify に自動デプロイ可
   （anicca-products は既に Netlify を使用 — `netlify-deploy.yml` 一本、と repo 方針に一致）。
3. **ゼロコンフィグ** — Markdown を置くだけで始まり、型安全な `blume.config.ts` は opt-in。
   小規模な OSS ドキュメントには過剰投資にならない。
4. **`blume eject` で退路が確保されている** — 将来大規模化しても、素の Astro アプリとして
   引き取れるため、ロックインリスクが低い。

**留保点（採用前に踏まえるべきこと）**:
- 2025年9月創設のまだ若いツール（v1.0.4）。破壊的変更のリスクは Docusaurus/VitePress のような
  枯れたツールより高い。ただし直近2日前にリリースがあり、開発は活発。
- Node 22.12+ 必須（比較的新しいバージョン要求）。
- 668★・月19k DLは「小さいが実プロダクションで使われている」規模で、"誰も使っていない"実験ツールではない。

**代替との比較**:

| ツール | 立ち位置 | AI-ready ネイティブ機能 | ホスティング |
|---|---|---|---|
| **blume** | 新しい、Astro駆動、ゼロコンフィグ | ◎ llms.txt/MCP/Copy-as-Markdown 標準搭載 | 無料（静的） |
| Docusaurus | 成熟、React、Meta製、エコシステム大 | △ プラグインで後付け | 無料（静的） |
| Nextra | Next.js駆動、軽量 | △ プラグインで後付け | 無料（静的、Vercel推奨） |
| Mintlify | SaaS、ホスト型、UI綺麗 | ○ Ask AI等あり | 有料枠あり、非OSS/要サインアップ |
| VitePress | 成熟、Vue、軽量 | × 標準では無し | 無料（静的） |

結論: 「AI がドキュメントを読んで動く」ことが一等目的の anicca にとって、blume の AI-ready 標準搭載は
他の成熟ツールにない差別化点であり、無料静的ホストとゼロコンフィグの要件も満たす。**採用推奨**、ただし
このセッションでは `npx blume init` を実行していない（調査のみ、指示通り導入は別turn）。

出典:
- https://github.com/haydenbleasel/blume/blob/main/README.md
- https://registry.npmjs.org/blume（npm registry API 実測）
- https://blockrun.ai/docs（`curl -sI` ヘッダ実測、Next.js シグナル確認）
- https://cloud.runonflux.com（FluxCloud pricing copy、README草案の是正に使用）
