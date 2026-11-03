# Manager article publication adapter

The canonical source is `Daisuke134/life-manager`. The existing full-site Next.js build and Netlify deployment remain in `Daisuke134/anicca-products`; no new hosting or second Manager implementation is created.

The reviewed article package is `docs/research/manager/publication/2026-10-19/manifest.json` in the same immutable canonical revision. Its article metadata and Markdown bytes become `data/research/manager-<topic>-ja/en.json`; hash-addressed images become `public/blog/manager/media/<sha256>.<extension>`. Internal source/evidence paths are not published in the public receipt.

Before the publishing repository's existing Next build, CI downloads `scripts/install.mjs` at a full canonical commit, checks the installer's pinned SHA-256, then sets `MANAGER_BLOG_REVISION` and runs the installer. The installer verifies `release-manifest.json` modules, validates the reviewed article package and all content hashes, stages the article JSON/media and applies narrowly guarded changes to the existing blog flow. A changed legacy interface fails the build instead of silently omitting Manager integration. The existing post-build marketing overlay, other businesses, Netlify functions and payment smoke remain intact.

`/blog/manager` groups English and Japanese articles in newest-first publication-date order. `/blog/c/manager` remains a category alias with canonical metadata pointing to `/blog/manager`. The main blog index stays topic-first without a standalone latest-articles list. Topic previews and collections retain publication-date order, and the archive remains available. The main index, article breadcrumbs and sitemap link to the canonical Manager collection. Article URLs stay flat, using the existing article renderer route. Only records with `project: "Manager"` opt into the safe extended renderer (tables, numbered lists, fenced code; raw HTML is escaped). Other articles use their original renderer.

Regenerate module integrity hashes after source edits:

```sh
node apps/landing/manager-blog/scripts/build-release-manifest.mjs
node --test apps/landing/manager-blog/tests/*.test.mjs
```

Test fixtures snapshot the pre-integration publishing blog interfaces for repeatability; they are not alternate production source. Production synchronization must run against the current publishing branch and preserve its unrelated posts/routes.

Promotion requires reviewed content, canonical PR/checks/merge, a publishing bridge-only PR/checks/merge, then live article/media hash readback and existing payment smoke. `public/blog/manager/release.json` binds the deployed articles and media to the canonical revision. A preview or local test is not a publication receipt.

Renderer-only releases may set `MANAGER_BLOG_CONTENT_REVISION` to an independently reviewed immutable publication commit while `MANAGER_BLOG_REVISION` selects installer/modules. Both must be full commit hashes. The public receipt records both. Without a separate content pin, content follows the code revision for backward compatibility. To publish new content when a separate pin exists, deliberately update the content pin after content review; changing only the renderer pin must not publish or remove articles.

Manager social metadata uses the reviewed Markdown’s first image as its Open Graph and Twitter card image. Language and publication date follow article metadata. The installer preserves an optional `character_count` so Japanese reading length is not presented as whitespace-delimited words.

## Editorial and production publication runbook (2026-11-03)

**Why this section exists:** Future Codex, Grok, Muse, Dots and ChatGPT agents should be able to revise and publish a Manager article to the **existing** `aniccaai.com/blog/manager` without guessing the procedure. This README is the durable operating reference for the blog pipeline, **not** a second Manager research/TODO SSOT. Do not create a parallel website or publication database.

### Know the reader and use the writing skills before drafting

The primary reader is an **AI-curious founder, builder, student or general technical reader who knows ChatGPT but does not yet know Persimmon, Ampersand, Rothko, Artificial Societies or statistical jargon.** Secondary readers are researchers and YC partners who want enough primary sources and reproducibility details to scrutinize claims.

The desired outcome is understanding and informed curiosity. The editorial voice is **accessible, scene-led, evidence-based science journalism**, not a lab status report, a YC fundraising pitch, or an academic abstract.

The 2026-11-03 editorial upgrade used three open skills from `coreyhaines31/marketingskills` pinned at `88c79f6528a9347420e57ceb1fff9a60de651768`:
- `content-strategy`: the searchable/shareable information-gain test, audience, question and unique insight;
- `copywriting`: concrete scene, one argument per section, claims that can be checked, no generic AI-marketing filler;
- `copy-editing`: seven separate passes for clarity, voice, reader value, proof, specificity, humane detail and removing friction.

On the connected Mac mini the skills are installed in `~/.agents/skills/{content-strategy,copywriting,copy-editing}/SKILL.md`; on another machine install/read the same audited upstream skills, or use the durable prose requirements here. The existing local `~/.agents/skills/content-research-brief/SKILL.md` collects primary sources before writing. Skill files are agent instructions, not source evidence; verify technical and company claims against primary sources.

**Article acceptance gate:** (1) first 150 words let a stranger see the scene and why it matters; (2) the company and model are introduced before their names become jargon; (3) methods and statistics are taught through a tangible example; (4) at least one original, informative illustration has alt text and is source-correct; (5) real experimental outputs, third-party marketing claims and hypothetical examples are unmistakably distinct; (6) each consequential assertion has a primary link; (7) a useful closing insight/invitation replaces a boilerplate executive summary. Do not write a laboratory report with a more exciting title.

### Canonical source files (one source, immutable publishing pins)

**Source repo**: `Daisuke134/life-manager` (current `main`), paths:
- Editable article source: `docs/research/manager/articles/<dated-name>-en.md` (Japanese companion where appropriate).
- Release package: `docs/research/manager/publication/2026-10-19/manifest.json` plus `en/<slug>.md` or `ja/<slug>.md`.
- Original figures: `docs/research/manager/publication/artwork/render-editorial.py` creates standalone PNGs. Hash every image's bytes with SHA-256; copy to `publication/2026-10-19/media/<sha256>.png`. Add `{package_path, sha256, public_url}` to top-level `manifest.media`. In article Markdown, link the live URL `https://aniccaai.com/blog/manager/media/<sha256>.png` and add accurate alt text. Do not hotlink watermarked stock images or copy proprietary company visuals.
- `manifest.articles` entry keeps the **stable slug**, matching `lang`, `canonical_url`, title/description/date, `markdown`, computed `word_count`, character_count, and matching `sha256` of the packaged Markdown bytes. The source file gets a matching `source_sha256`.
- Canonical validation code is `apps/landing/manager-blog/scripts/package-contract.mjs`.

**Site build/deploy repo**: `Daisuke134/anicca-products`. Existing production GitHub Actions deploy the full Next.js site to Netlify. Both `.github/workflows/landing-pr-build.yml` and `.github/workflows/netlify-deploy.yml` set `MANAGER_BLOG_CONTENT_REVISION`. They also pin `MANAGER_BLOG_REVISION` for the installer code: **do not modify the installer pin to publish content**. Never use `Daisuke134/anicca-products` as a second authoring source for Manager articles.

### Exact sequence for safely editing AND publishing

1. Update/clone `Daisuke134/life-manager` from current `main`; work in a fresh review branch, not a dirty production worktree.
2. Edit the article source. For a revision, keep its existing slug to avoid breaking public URLs. Rebuild its paired packaged Markdown, recompute SHA-256 and embedded Markdown in the existing manifest, and add unique content-addressed media as above. Avoid private person-level records, raw API keys, unlicensed media, and competitor output not authorized for public reproduction.
3. Run these source-side checks:
   ```bash
   node --input-type=module -e "import {validatePublication} from './apps/landing/manager-blog/scripts/package-contract.mjs';import fs from 'node:fs';let p=validatePublication(JSON.parse(fs.readFileSync('docs/research/manager/publication/2026-10-19/manifest.json')));console.log('Validated',p.articles.length,'articles,',p.media.length,'media')"
   node --test apps/landing/manager-blog/tests/*.test.mjs
   git diff --check
   ```
   Read each edited article for reader comprehension and source truth before release.
4. Push a **canonical content PR** to `life-manager`, confirm the `manager-blog-contract` and all required checks pass; merge through its normal review flow. Record the **merge commit SHA** (40 hexadecimal characters), not the old feature branch SHA.
5. On a fresh branch in `anicca-products` from current `main`, update **only** `MANAGER_BLOG_CONTENT_REVISION` in BOTH `.github/workflows/landing-pr-build.yml` and `.github/workflows/netlify-deploy.yml` to the same **merged content SHA**. Keep the installer and unrelated workflows, redirects, products and payment features untouched.
6. Push the site bridge PR, wait for `Landing PR build` success (it stages the exact hashed articles and builds the whole site), then merge. Main's `Netlify Deploy (Landing)` must succeed; its **Post-deploy money-path smoke + rollback (prod only)** must pass before claiming success.
7. **Verify from the public site** rather than trusting the PR: `https://aniccaai.com/blog/manager/release.json` must contain the intended `content_revision` and the desired article slugs/hashes. Each `https://aniccaai.com/blog/<slug>` must return HTTP 200 with the article's unique headline/body and original diagram. Every referenced `/blog/manager/media/<sha256>.png` must also return 200, and the existing homepage/payment paths must remain healthy.
8. In the final reply, link the **real verified live article URLs** and the two reviewed PRs plus the successful deploy run. If CI/build/release is incomplete, say **prepared, not published**; never invent a success or promise later delivery.

The 2026-11-03 flow was exercised using source PR #9154 and site PR #848 with green Next.js build, successful Netlify deployment `41620230068`, production money-path smoke, and 200 readback for all three new English articles. This example is historical; future edits still require their own checks and immutable pin updates. The production articles are accessible at the canonical URLs as long as they remain deployed. Study/lesson progress remains in the existing independent learning SSOT; do not copy it here.
