# grok-context-research 統合 spec

**目的:** 日次オート開発で「X の空気を Grok で 1 本にまとめたコンテキスト」を使えるようにする。検索の軸・#metrics の文章・spec のネタに使う。

**対象:** VPS OpenClaw（Anicca）＋ anicca-auto-development スキル。

---

## 1. スコープ

| 項目 | 内容 |
|------|------|
| 追加するもの | Hayatti の x-research-skills（Grok で X コンテキストをまとめる）を VPS で実行し、OpenClaw と anicca-auto-development から使えるようにする。 |
| スキル名（OpenClaw） | `grok-context-research` |
| リポジトリ | https://github.com/HayattiQ/x-research-skills |
| 実行スクリプト | `scripts/grok_context_research.ts`（CLI: `--topic`, `--locale`, `--audience`） |

---

## 2. VPS での配置

| 項目 | 値 |
|------|-----|
| クローン先 | `/home/anicca/.openclaw/skills/x-research-grok` |
| クローン方法 | `cd ~/.openclaw/skills && git clone https://github.com/HayattiQ/x-research-skills.git x-research-grok` |
| 環境変数 | `XAI_API_KEY` を `/home/anicca/.openclaw/.env` に記載（既存でよい）。 |

**理由:** 既存の x-research（rohunvora）が `skills/x-research` なので、別名 `x-research-grok` で被らないようにする。

---

## 3. 依存関係（VPS）

| 項目 | 対応 |
|------|------|
| Node.js | 既存の OpenClaw 用 Node を利用。 |
| tsx | `x-research-grok` 直下で `npm init -y && npm install tsx` する。またはリポに package.json があれば `npm install` のみ。 |
| 実行コマンド | `cd /home/anicca/.openclaw/skills/x-research-grok && npx tsx scripts/grok_context_research.ts --topic "<トピック>" --locale ja` |

`.env` は OpenClaw ルートのものを読む。実行前に `export $(grep -v '^#' /home/anicca/.openclaw/.env | xargs)` などで読み込むか、gateway/cron が .env を読む前提とする。

---

## 4. 実行の仕様

| 項目 | 内容 |
|------|------|
| トピック | 日次では Anicca が決める（例: 「Anicca 習慣化アプリ」「OpenClaw エージェント」「今日の iOS 開発トレンド」）。 |
| デフォルト引数 | `--locale ja`。`--audience` はリポのデフォルト（both 等）に従う。 |
| 出力先 | リポの `data/context-research/` 配下（例: `YYYYMMDD_HHMMSSZ_context.md`）。 |
| 利用者 | Anicca。この .md を読んでステップ 1（検索の軸）・ステップ 2（#metrics の要約）・ステップ 3（spec のネタ）に使う。 |

---

## 5. OpenClaw への登録

| 項目 | 内容 |
|------|------|
| 登録名 | `grok-context-research` |
| 実体パス | `/home/anicca/.openclaw/skills/x-research-grok` |
| openclaw.json | `skills.entries` に `"grok-context-research": { "enabled": true }` を追加する。 |
| 呼び方 | Anicca が「grok-context-research を使って今日の X コンテキストを取れ」と指示したときに、上記コマンドを実行し、出力 .md のパスを報告する。 |

OpenClaw がスキルを「ディレクトリ名＝スキル名」で解決する場合、`x-research-grok` を `grok-context-research` として alias するか、または `x-research-grok` の直下に SKILL.md を 1 本置き、その SKILL の名前を `grok-context-research` として登録する。いずれにせよ **OpenClaw 上で Anicca が参照する名前は `grok-context-research`** とする。

---

## 6. anicca-auto-development の更新

| 対象 | 変更内容 |
|------|----------|
| ステップ 1（検索） | 「**grok-context-research** を先に実行し、`data/context-research/` の .md を読んだうえで、**x-research** と **Firecrawl** で深掘りする」と明記する。 |
| ステップ 2（学習 → #metrics） | 「Grok の .md を要約の種にして、#metrics に『X の空気・気になった記事・注意点』を書く」と明記する。 |
| 「使うスキル・ツール」 | **grok-context-research** を追加する。「Grok で X の空気を 1 本の .md にまとめる。`npx tsx scripts/grok_context_research.ts --topic ...` で実行し、`data/context-research/` の .md を検索・#metrics・spec の材料に使う。」 |

編集するファイル: `openclaw-skills/anicca-auto-development/SKILL.md`（リポの openclaw-skills を VPS に同期する前提）。

---

## 7. 日次フローでの位置づけ

1. 毎朝の cron で「今日の X リサーチ」が走る。
2. Anicca が **grok-context-research** を実行し、トピックを 1 つ決めて `grok_context_research.ts` に渡す。
3. `data/context-research/` に .md ができる。
4. Anicca がその .md を読んでから **x-research** と **Firecrawl** で検索（ステップ 1）。
5. 学習し、Grok の .md を種に **#metrics** に投稿（ステップ 2）。
6. 必要なら spec 作成・Codex 依頼へ（ステップ 3 以降）。

---

## 8. 受け入れ条件

| # | 条件 |
|---|------|
| 1 | VPS の `/home/anicca/.openclaw/skills/x-research-grok` に Hayatti の x-research-skills が clone されている。 |
| 2 | `XAI_API_KEY` が `/home/anicca/.openclaw/.env` に設定され、`npx tsx scripts/grok_context_research.ts --topic "test" --locale ja` で .md が生成される。 |
| 3 | openclaw.json の `skills.entries` に `grok-context-research` が追加され、Anicca がこの名前でスキルを参照できる。 |
| 4 | anicca-auto-development の SKILL.md が上記のとおり更新され、ステップ 1・2 と「使うスキル・ツール」に grok-context-research が含まれている。 |

---

## 9. ファイル一覧

| 役割 | パス |
|------|------|
| 本 spec | `.cursor/plans/reference/grok-context-research-spec.md` |
| 更新するスキル定義 | `openclaw-skills/anicca-auto-development/SKILL.md` |
| VPS の .env | `/home/anicca/.openclaw/.env`（XAI_API_KEY） |
| VPS のスキル実体 | `/home/anicca/.openclaw/skills/x-research-grok` |
| VPS の OpenClaw 設定 | `/home/anicca/.openclaw/openclaw.json` |

---

**最終更新:** 2026-02-10
