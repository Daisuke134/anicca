---
name: web-app-factory
description: Builds and deploys a Next.js web app with Stripe subscriptions to Vercel autonomously. Handles all phases: trend research → Stripe product/price → Next.js scaffold → feature implementation (appfactory-builder Phase 0-8) → quality check → Vercel deploy → social post. Use when told to "build a web app", "ship a webapp", or when triggered by web-app-factory cron.
---

# web-app-factory — Claude Code Builder Instructions

あなたは web-app-factory の自律ビルダーである。
1本の Web アプリをトレンド調査からデプロイまで完全自律で完成させる。
**全ての作業は既存スキルの組み合わせで行う。オリジナルコードゼロ。**

ソース: [Anthropic Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
引用: 「A two-fold solution: an initializer agent that sets up the environment on the first run, and a coding agent that is tasked with making incremental progress in every session while leaving clear artifacts for the next session.」

ソース: [0xAxiom/AppFactory](https://github.com/0xAxiom/AppFactory)
引用: 「Agent-native system that turns market signals into validated app specs and buildable apps—with monetization, ASO, and launch strategy baked in.」

---

## 工場ルール（MANDATORY — 全 US に適用）

| ルール | 内容 |
|--------|------|
| **F1** | 承認待ち禁止。system event で報告して即次 US へ |
| **F2** | 詰まったらこの SKILL.md を必ず修正。修正せずに進むのは禁止 |
| **F3** | クローズドループ強制。今日の失敗は明日の成功のソース |
| **F4** | オリジナル禁止。全ての実装は既存スキルの SKILL.md に従う |

ソース: mobileapp-builder SKILL.md

---

## 報告義務（MANDATORY — 全 US に適用）

各 US の開始時・完了時・エラー時に system event を発火する:

```bash
openclaw system event --text "US-XXX_START: [title]" --mode now
openclaw system event --text "US-XXX_DONE: [title] — [one-line summary]" --mode now
openclaw system event --text "US-XXX_ERROR: [error summary]" --mode now
```

---

## git push 強制（MANDATORY — 全 US に適用）

各 US 完了時:

```bash
git add -A && git commit -m "feat: [US-ID] - [title]" && git push origin main
```

ソース: mobileapp-builder SKILL.md
引用: 「git push せずに進む → git add -A && git commit && git push まで完了させる」

---

## 進捗ファイル（progress.txt — 全 US に適用）

各 US 完了時に `progress.txt` に追記する（append-only）:

```
## [Date/Time] - [Task ID]
- What was implemented
- Files changed
- **Learnings for future iterations:**
  - Patterns discovered
  - Gotchas encountered
```

ソース: [snarktank/ralph](https://github.com/snarktank/ralph)
引用: 「APPEND to progress.txt (never replace, always append)」

ソース: [Addy Osmani Self-Improving Agents](https://addyosmani.com/blog/self-improving-agents/)
引用: 「each iteration is isolated - the agent is spawned fresh each time」

---

## US-001: トレンド調査 + アイデア選定

**INPUT**: なし（自律で開始）
**OUTPUT**: `prd.json` + `idea.md`

Read and follow these skills in order:

1. Read `.claude/skills/apify-ultimate-scraper/SKILL.md` — Web トレンド収集（ProductHunt, HackerNews, Reddit）
2. Read `.claude/skills/content-trend-researcher/SKILL.md` — SNS 10プラットフォーム分析
3. Read `.claude/skills/startup-idea-validation/SKILL.md` — 市場規模・競合スコアリング + ニッチ選定

Generate `idea.md` with sections: Problem / Market / Target / Monetization / Competitors
- SaaS/ツール系のニッチを特定（月額 $4.99-$19.99 で課金可能なもの）
- アプリ名を決定（短い英語、.vercel.app で使えるスラグ）

Generate `prd.json` from `prd.json.template`, fill: app_name, slug, tagline, problem, target, monetization

Create `CLAUDE.md`:
```
Read .claude/skills/web-app-factory/SKILL.md and follow it exactly.
```

```bash
git add -A && git commit -m "feat: US-001 - trend research + idea.md + prd.json" && git push origin main
openclaw system event --text "US-001_DONE: Trend Research — [APP_NAME] selected" --mode now
```

---

## US-002: Stripe Product + Price 作成

**INPUT**: `prd.json` の `price_monthly_usd`
**OUTPUT**: `STRIPE_PRICE_ID` in `.env.local`

Stripe API を直接呼ぶ（公式ドキュメント通り）:

```bash
# Product 作成
curl https://api.stripe.com/v1/products -u "$STRIPE_SECRET_KEY:" -d name="$APP_NAME Pro"

# Price 作成
curl https://api.stripe.com/v1/prices -u "$STRIPE_SECRET_KEY:" \
  -d product=prod_xxx -d unit_amount=499 -d currency=usd -d "recurring[interval]=month"

# .env.local に保存
echo "STRIPE_SECRET_KEY=$STRIPE_SECRET_KEY" >> .env.local
echo "STRIPE_PRICE_ID=price_xxx" >> .env.local
echo "NEXT_PUBLIC_URL=https://{slug}.vercel.app" >> .env.local
```

ソース: [Stripe 公式](https://docs.stripe.com/checkout/quickstart?client=next)
引用: 「Price or inventory information should always reside on the server to prevent client-side manipulation.」

```bash
git add -A && git commit -m "feat: US-002 - Stripe product + price created" && git push origin main
openclaw system event --text "US-002_DONE: Stripe Setup — price_xxx created" --mode now
```

---

## US-003: Next.js プロジェクト作成

**INPUT**: `prd.json` の `slug`
**OUTPUT**: `npm run build` PASS

```bash
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --yes
npm install stripe @stripe/stripe-js
npm run build
```

ソース: [Next.js 公式](https://nextjs.org/docs/getting-started/installation)
引用: 「The easiest way to get started with Next.js is by using create-next-app」

```bash
git add -A && git commit -m "feat: US-003 - Next.js project initialized" && git push origin main
openclaw system event --text "US-003_DONE: Next.js scaffold — build passing" --mode now
```

---

## US-004: 機能実装（appfactory-builder Phase 0〜8）

**INPUT**: `idea.md` + Next.js プロジェクト
**OUTPUT**: 全ページ実装完了 + Stripe Checkout 動作 + 品質ゲート PASS

Read and follow:

1. Read `.claude/skills/appfactory-builder/SKILL.md` — Phase 0〜8 を実行

   INPUT: `idea.md`

   | Phase | やること | 内部で使うスキル |
   |-------|---------|---------------|
   | 0 | Intent Normalization | — |
   | 1 | Dream Spec（12セクション） | — |
   | 2 | Research & Positioning | — |
   | 3 | Information Architecture | — |
   | 4 | Design System | — |
   | 5 | Build | `.claude/skills/app-builder/SKILL.md` + `.claude/skills/senior-frontend/SKILL.md` + `.claude/skills/nextjs-expert/SKILL.md` |
   | 6 | GATE: Skills Audit | react-best-practices ≥95% |
   | 7 | GATE: SEO Review | Technical / On-Page / Performance / Social |
   | 8 | GATE: Ralph Polish Loop | 20パス / ≥97% |

   LOCAL_RUN_PROOF_GATE: `RUN_CERTIFICATE.json` status:PASS 必須

Stripe Checkout は Server Action パターンで実装する。Webhook handler は `STRIPE_WEBHOOK_SECRET` 未設定時に 503 を返す（クラッシュしない）。

ソース: [DEV Community Stripe 2026](https://dev.to/sameer_saleem/the-ultimate-guide-to-stripe-nextjs-2026-edition-2f33)
引用: 「Server Actions are the standard for creating Checkout Sessions」

```bash
git add -A && git commit -m "feat: US-004 - all pages implemented via appfactory-builder" && git push origin main
openclaw system event --text "US-004_DONE: Feature Implementation — Phase 0-8 complete" --mode now
```

---

## US-005: 品質チェック + E2E テスト

**INPUT**: 実装済みコード
**OUTPUT**: `npm run build` PASS + E2E PASS

1. ビルド + Lint:
   ```bash
   npm run build && npm run lint
   ```

2. Read `.claude/skills/webapp-testing/SKILL.md` — Playwright E2E テスト実行

   ソース: webapp-testing SKILL.md
   引用: 「Always launch chromium in headless mode」

3. SEO チェック:
   - `src/app/layout.tsx` に metadata（title, description, OG image）
   - `public/robots.txt` 存在
   - `src/app/sitemap.ts` 存在

```bash
git add -A && git commit -m "feat: US-005 - quality check + E2E passed" && git push origin main
openclaw system event --text "US-005_DONE: Quality Check — build + E2E passed" --mode now
```

---

## US-006: Vercel デプロイ

**INPUT**: ビルド済みコード
**OUTPUT**: 有効な Vercel URL

Read `.claude/skills/vercel-deploy/SKILL.md` — Vercel にデプロイ

環境変数設定（STRIPE_WEBHOOK_SECRET は含めない — デプロイ後に別途設定）:
```bash
npx vercel env add STRIPE_SECRET_KEY production --token $VERCEL_TOKEN <<< "$STRIPE_SECRET_KEY"
npx vercel env add STRIPE_PRICE_ID production --token $VERCEL_TOKEN <<< "$STRIPE_PRICE_ID"
npx vercel env add NEXT_PUBLIC_URL production --token $VERCEL_TOKEN <<< "https://{slug}.vercel.app"
npx vercel deploy --prod --token $VERCEL_TOKEN --yes
```

### Post-deploy: Stripe Webhook 登録依頼

Read `.claude/skills/slack-webhook/SKILL.md` — Slack に Webhook 登録依頼を送信:

```
🔑 Stripe Webhook 登録が必要です:
URL: https://{slug}.vercel.app/api/webhook
イベント: checkout.session.completed, customer.subscription.deleted
→ Stripe Dashboard で登録して、Webhook Secret を返信してください。
```

**CC はユーザーの返信を待たずに US-007 へ進む。**

ソース: [Stripe Docs](https://docs.stripe.com/webhooks/quickstart)
引用: 「Each Webhook endpoint has a unique signature secret」

```bash
git add -A && git commit -m "feat: US-006 - deployed to Vercel" && git push origin main
openclaw system event --text "US-006_DONE: Vercel Deploy — https://{slug}.vercel.app" --mode now
```

---

## US-007: 完了報告 + AGENTS.md + X 投稿

**INPUT**: デプロイ済み URL
**OUTPUT**: Slack 報告 + AGENTS.md + COMPLETE

1. **prd.json の全 US を passes:true に更新**

2. **AGENTS.md を作成**:
   ```markdown
   # AGENTS.md — web-app-factory 学習記録
   ## Critical Mistakes（3回以上繰り返したエラー）
   ## Evolution Log
   ## Correction Log
   ```
   ソース: [Addy Osmani Self-Improving Agents](https://addyosmani.com/blog/self-improving-agents/)
   引用: 「AGENTS.md — a file that agents can use to document what they've learned」

3. **Slack 完了報告**:
   Read `.claude/skills/slack-webhook/SKILL.md`
   Read `.claude/skills/configure-notifications/SKILL.md`

4. **X に投稿**（Postiz CLI）:
   ```bash
   npx postiz posts:create \
     -c "Just shipped: [APP_NAME] 🚀 https://[slug].vercel.app #BuildInPublic #indiehacker" \
     -s "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
     -i "$POSTIZ_X_INTEGRATION_ID"
   ```
   ソース: [Postiz CLI](https://docs.postiz.com/cli/managing-posts)

5. **最終 git push + COMPLETE**:
   ```bash
   git add -A && git commit -m "feat: US-007 - complete report + AGENTS.md" && git push origin main
   ```
   ```
   <promise>COMPLETE</promise>
   ```

---

## 禁止事項

| 禁止 | 代替 |
|------|------|
| オリジナルコードを書く | 既存スキルの SKILL.md に従う |
| `alert()` / `href="#"` / `"coming soon"` | 実装する |
| `console.log` / `TODO` / `lorem ipsum` を残す | 削除 / 実装する |
| git push せずに次 US | 必ず push してから次へ |
| progress.txt に学び追記なしで次 US | 必ず追記してから次へ |
| 複数 US を1イテレーションで実行 | 1 US ずつ。ralph.sh が分離する |
