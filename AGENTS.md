<!-- この file は .rulesync 正本から将来生成される。手編集は当面OK。 -->

# Anicca agent rules

## ツール既定（HARD）

| 用途 | 既定 |
|---|---|
| Web検索・URL取得 | `crwl <url> -o markdown`（crawl4ai CLI。firecrawl は credit 切れのため既定から外す） |
| ライブラリ・SDK docs | `npx ctx7@latest library <name>` → `npx ctx7@latest docs <id> "<質問>"` |
| X検索 | skill `x-search-cdp`（その `SKILL.md` に従う） |
| GitHub | `gh` CLI |

- `WebSearch` / `WebFetch` は禁止。Web取得は `crwl` を使う。
- GitHub の探索・issue・PR・API 操作は `gh` を優先する。
- fleet全体の現状（context floor / skills単一化 / chezmoi / cloud移行）→ `docs/reference/local-env-and-architecture.md`（tracked、全 session 共通）。

## 検索優先

- 既定の姿勢は「自分の仮説は間違っている」。断定・設計・実装前に検索し、対象を実測する。
- repo 内は CodeGraph（`.codegraph/` がある場合）→ Serena → `rg` / Read の順で調べる。
- 外部の判断は一次資料を優先し、ソース名・URL・核心の引用を残す。
- 作る前に既存解を web と GitHub で探し、車輪を再発明しない。

## Push 規律

- 意味のある編集は、検証後に `git fetch` →対象だけを stage→commit→push する。
- ユーザーの既存変更を混ぜない。`git add -A` は使わず、対象パスを明示する。
- push 済みの commit と、必要なら deployment の commit hash を実測して完了とする。

## spec = SSOT

- 会話ではなく spec が正本。実測で事実・状態・失敗・TODO が変わった turn 内に spec を更新する。
- 古い誤記は併記せず是正し、何が誤りだったかを短く残す。
- 実装・テスト・完了の断定は、その session の tool output のみを根拠にする。

## Skills

- User/global skills: `~/.agents/skills`
- Repository/Claude skills: `.claude/skills`
- skill 名が指定された、または内容が明確に一致する場合は、作業前に対象 `SKILL.md` を全文読む。
