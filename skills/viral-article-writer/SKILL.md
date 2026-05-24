---
name: viral-article-writer
description: 週1本、Anicca のプロダクトを1つ選び owned-media 長文記事を作る薄いオーケストレータ。corey marketingskills (content-strategy→copywriting→copy-editing→ai-seo) を .agents/product-marketing.md に grounding して走らせ、humanizer-ja(JP一次)→humanizer(EN) で人間化、nano-banana CLI で EN+JP 図を記事冒頭に埋め、JP/EN 各々を /blog と Substack に実投稿する。自作執筆ロジックは持たない（全部 corey skill に委譲）。
---

# viral-article-writer — corey 鎖の薄いオーケストレータ

お前 = 走っているモデル。**自前で記事を書くロジックを持たない**。
corey marketingskills の skill を順に「Read して指示通り実行」する
(`feedback_use_npx_skills_for_upstream`: upstream SKILL.md が SSOT)。
外部 LLM API は叩かない (HARD RULE #6・お前がモデル)。

> 全 corey skill は `~/.agents/product-marketing.md`(= anicca-project/.agents/
> product-marketing.md への symlink) を自動参照する。これで出力は全部
> "Anicca の宣伝" になる。これが personalize の核。触る前に必ず存在確認。

## STEP 0 — 環境 + 今週のプロダクト選定 (ローテ)

```bash
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
set -a; . ~/.openclaw/.env; set +a
SK=~/.openclaw/skills/viral-article-writer
TODAY=$(TZ=Asia/Tokyo date +%Y-%m-%d)
RUN=~/.openclaw/skills/viral-article-writer/output/$TODAY; mkdir -p "$RUN"
[ -f ~/.agents/product-marketing.md ] || { echo "❌ product-marketing.md 無し"; exit 1; }
```

プロダクト roster (cursor = `$SK/state/product-cursor`、無ければ 0):

```
0 anicca-ios       (フラッグシップ iOS app)
1 anicca-cafe      (東京・単一SKU カフェ)
2 anicca-cemetery  (お墓)
3 anicca-fashion   (ファッション)
4 anicca-retreat   (リトリート)
5 anicca-mantra    (マントラ)
6 anicca-iam       (アファメーション/iam)
```

今週 = `cursor mod 7`。処理後 `cursor+1` を保存(翌週は次の1体)。
slug = `<product>-<TODAY>`(例 `anicca-ios-2026-05-19`)。JP/EN 別 slug:
`${slug}-ja` / `${slug}-en`。

## STEP 1 — content-strategy (今週のトピック決定)

`~/.agents/skills/content-strategy/SKILL.md` を Read し、その指示通り実行。
入力 = 今週のプロダクト + `~/.agents/product-marketing.md`。
出力 = 記事1本のトピック/角度/アウトライン → `$RUN/brief.md`。

## STEP 2 — copywriting (本文ドラフト)

`~/.agents/skills/copywriting/SKILL.md` を Read し、その指示通り、STEP1 の
brief から長文記事本文をドラフト。owned-media long-form (4000+ words 目安)。
→ `$RUN/draft_en_raw.md`(まず EN 骨子で可、言語は STEP3-4 で確定)。

## STEP 3 — humanizer-ja (JP 一次原稿) ← 主言語

`humanizer-ja` skill を Skill tool で invoke (HARD RULE #5)。draft を
**日本語の一次原稿**に書き起こす(直訳でなく日本語ネイティブの長文記事)。
→ `$RUN/article_ja.md`。Anicca フォロワーの多数は日本人なので JP が主。

## STEP 4 — humanizer (EN 原稿)

`humanizer` skill を Skill tool で invoke。JP 記事を**英語ネイティブの
長文記事に書き直す**(直訳禁止)。→ `$RUN/article_en.md`。

## STEP 5 — copy-editing (両言語 推敲)

`~/.agents/skills/copy-editing/SKILL.md` を Read し指示通り、
`article_ja.md` と `article_en.md` を推敲(冗長/AI臭/誤り除去)。

## STEP 6 — ai-seo (LLM 引用最適化) ← views の薬

`~/.agents/skills/ai-seo/SKILL.md` を Read し指示通り、両記事を
LLM/AI検索に引用されるよう最適化(回答可能な見出し・定義・数値・引用)。

## STEP 7 — nano-banana で EN+JP 図 (記事の理解を助ける・冒頭に置く)

```bash
cd ~/tools/nano-banana-2
(set -a; . ~/.openclaw/.env; set +a; bun src/cli.ts "<EN figure: その記事の核を1枚で説明する実ダイアグラム。ENGLISH。箇条書きPowerPoint禁止>" -o ${slug}_en -s 2K -a 3:2 -d "$RUN")
(set -a; . ~/.openclaw/.env; set +a; bun src/cli.ts "<JP図: 同内容を完璧な日本語で。実ダイアグラム>" -o ${slug}_ja -s 2K -a 3:2 -d "$RUN")
```
生成後 `Read` で **両方** #8 目視検証(可読/正確/重複なし、NG はその言語だけ
prompt 締めて再生成、失敗版は `_vN` で残す・上書き禁止)。
図は `apps/landing/public/blog/<slug-lang>/figure.png` に置き、
**記事本文の冒頭(導入直後・最初の H2 の前)** に
`![…](/blog/<slug-lang>/figure.png)` で埋め込む(読者が一目で理解できる)。

## STEP 8 — /blog に JP/EN を実投稿 (owned media・proven path)

各言語 = 独立ポスト。`anicca-products` の **main** で作業:

```bash
cd /Users/anicca/anicca-project
git fetch origin main -q && git checkout main -q && git pull -q origin main
mkdir -p apps/landing/public/blog/${slug}-ja apps/landing/public/blog/${slug}-en
cp "$RUN/${slug}_ja.png"  apps/landing/public/blog/${slug}-ja/figure.png
cp "$RUN/${slug}_en.png"  apps/landing/public/blog/${slug}-en/figure.png
```

JP: `apps/landing/data/research/${slug}-ja.json`、EN: `${slug}-en.json`。
必須キー(検証済): `slug`,`title`,`date`(YYYY-MM-DD),`project`,
`n_papers_cited`(int),`word_count`(int),`markdown`(全文・冒頭に図 ![]() 埋込),
`mirrors`(`{x?,substack?}`)。`out/` は commit しない(gitignore)。

```bash
git -c credential.helper= add apps/landing/data/research/${slug}-ja.json \
  apps/landing/data/research/${slug}-en.json apps/landing/public/blog/${slug}-*/figure.png
git -c credential.helper= -c commit.gpgsign=false commit -m "blog: <product> JP+EN owned-media article ($TODAY)"
git -c credential.helper= push origin main
```
Netlify が main から自動再ビルド。

## STEP 9 — Substack に JP/EN を実投稿 (実証済み機構)

publication = `aniccabuddha.substack.com`。認証は
`~/Library/Application Support/substack-mcp/config.json` に保存済
(session_token)。サーバ実体 = `~/substack`(nanameru/substack-mcp clone,
`.venv`)。**MCP 登録に依存せず `.venv/bin/python` で直接** 実行する
(cron は別セッションなので MCP tool は使えない・直 client が確実)。

各言語ごとに `~/substack/.venv/bin/python -X utf8` で:

```python
import sys; sys.path.insert(0,"/Users/anicca/substack/src")
from substack_mcp.client import SubstackClient
c = SubstackClient.from_env()
md = open(ARTICLE_MD, encoding="utf-8").read()
md = "\n".join(l for l in md.splitlines() if l.strip() != "__FIGURE_PLACEHOLDER__")  # 必須: literal placeholder 除去
url = c.upload_image(FIG_JPEG)["url"]            # 図を Substack CDN へ
p = md.split("\n\n",1); md = p[0]+f"\n\n![ALT]({url})\n\n"+(p[1] if len(p)>1 else "")  # 冒頭に埋込
d = c.create_draft(title=TITLE, content_markdown=md, subtitle=SUB, audience="everyone")
pid = d["post_id"]
c.set_cover_image(post_id=str(pid), image_url=url)   # 図をカバーにも
d2 = c.get_draft(post_id=str(pid))                   # #8 検証 (fresh)
assert "__FIGURE_PLACEHOLDER__" not in str(d2), "placeholder leak"
```

- **draft 止め** (`create_draft` のみ・`publish_draft` 呼ばない・
  `is_published=False`)。Dais が Substack dashboard から公開する
  (X 配信は別途 social/republish が担当・ここで publish しない)。
- `signature` 厳守: `upload_image(image)` / `set_cover_image(post_id,
  image_url)` / `update_draft(post_id, content_markdown=...)` /
  `get_draft(post_id)`。
- **literal `__FIGURE_PLACEHOLDER__` を絶対に本文に残すな** (subagent が
  /blog JSON だけ置換し article_*.md に残す事故あり 2026-05-19・#8 で検出)。
  /blog 側も Substack 側も「実 figure を埋めて placeholder を消す」両方必須。
- node が `libllhttp` で落ちる時は `PATH=/opt/homebrew/opt/node@22/bin:$PATH`。
- 認証切れ(401/403)時のみ fake せず「Substack=要再 setup」と明記し
  /blog 分だけ成立 (HARD RULE #11)。

## STEP 10 — #8 検証 + 後始末

- `curl -s -o /dev/null -w "%{http_code}" https://aniccaai.com/blog/${slug}-ja`
  と `${slug}-en` が **200**(Netlify 反映まで数分待つ)。
- 公開 URL を firecrawl/Chrome で開き全文 + 冒頭の図が表示されるか自分で見る。
- nano-banana png を再 Read し図が記事内容と一致するか確認。
- Substack 投稿 URL を開いて表示確認(投稿した場合)。
- `cursor+1` 保存、`state/article-<TODAY>.done` touch。
- 最終 stdout 1行: `✅ article: ja=<url>(200) en=<url>(200) substack=<url|SKIPPED:creds> fig=ja,en`

## やらないこと
- 自前で記事執筆ロジックを書く(全部 corey skill に委譲)。
- note.com / Medium / X を一次媒体にする(一次は /blog + Substack のみ。
  X 展開は別途 social skill / republish cron が薄切りで担当)。
- 外部 LLM API。fake/dry-run。図の上書き。Slack 自己投稿(cron 配送が担当)。
- 毎日実行(週1。長文を毎日=slop)。
