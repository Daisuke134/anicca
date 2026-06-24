# F4a — publish-to-zenn (draft → verify → publish) — spec (VSDD) — 2026-06-24

Zenn is FUNDAMENTALLY different from note: it is GIT-based, not browser-based. Existing assets (found):
- Content repo: `~/.openclaw/workspace/zenn-articles/` → GitHub `Daisuke134/zenn-articles` → Zenn auto-renders
  every `articles/*.md`. (Dais already connected this; Zenn publishes on push.)
- Existing script: `~/.openclaw/skills/article-writer/scripts/post-zenn.py` (copies a draft → articles/<slug>.md,
  commit + push; frontmatter must have published:true).
- Local preview: `~/.openclaw/external/zenn-editor` (zenn-cli) → `npx zenn preview` renders locally.

## How Zenn publishing works (the mental model — git, declarative)
- An article = `articles/<slug>.md` with frontmatter: `title, emoji, type(tech|idea), topics[], published`.
- `published: false` = DRAFT — pushed to GitHub but Zenn shows it ONLY to the author (not public).
- `published: true` = LIVE — public on zenn.dev.
- Publishing = a git commit + push. There is NO browser, NO eyecatch upload, NO paywall. Mermaid renders
  NATIVELY (```mermaid), so NO PNG conversion (unlike note). Images = repo-relative or URLs.
- Monetization on Zenn = バッジ (readers tip) on a FREE article. No paywall. So the Zenn article is the FREE
  reach/SEO piece that LINKS to the paid note (for the experiment logs). (Zenn Books = paid, out of scope.)

## The pipeline (draft → verify → publish) — mirrors note's discipline, git-native
1. ADAPT the markdown for Zenn: Zenn frontmatter; keep ```mermaid native (drop the note PNG figures); drop
   note-only bits (eyecatch slot, membership/paywall, the auto-目次 — Zenn auto-renders a 目次 from headings,
   and our heading rule already keeps it short: section titles = ## , sub-points = bold). End with a link to
   the paid note. Write `articles/<slug>.md` with `published: false`.
2. ★ VERIFY (vision, BEFORE public) ★: `npx zenn preview` (zenn-cli, localhost) → open it in cloakbrowser →
   screenshot → Read it → judge: layout, mermaid renders, images, headings/目次, Japanese not slop, the
   note link present. Deterministic: the md has `published: false` at this point. (No GitHub login needed —
   local preview.)
3. PUBLISH: only after the vision check passes → set `published: true` → git commit + push → Zenn live.
   Verify the live URL (HTTP 200, renders).

## Safety gate (the Zenn analogue of note's publish_guard)
- DRAFT-SAFE BY DEFAULT: a script/agent writes `published: false`. Going public = flipping ONE flag to true +
  push. The scheduled/unattended path NEVER flips to true (same idea as NOTE_FORCE_DRAFT) — it leaves drafts.
- Deterministic gate: `publish-to-zenn.sh publish` refuses to set `published: true` / push-as-published unless
  NOTE_MODE=go AND a fresh sentinel (reuse the F3 publish_guard pattern), so an unattended agent can only draft.
- ★ SECURITY (VSDD finding, pre-spec): the repo remote embeds a GitHub PAT in the URL (https://ghp_...@github).
  FIX in build: rotate the token + move it to a git credential helper / SSH (post-zenn.py already references an
  SSH key — make the remote SSH and drop the inline PAT). Do not commit/echo the token. ★

## Build plan (NOT this turn — Dais reviews the flow first)
- `publish-to-zenn.sh draft <md> --slug <s>` → adapt + write articles/<slug>.md (published:false), commit+push.
- `publish-to-zenn.sh verify <slug>` → npx zenn preview + cloakbrowser screenshot → evidence for the agent vision.
- `publish-to-zenn.sh publish <slug>` → (gated) set published:true + commit + push; then live-URL check.
- Reuse F2's claude -p agent loop (write → draft → vision verify → publish-when-go) with the Zenn scripts.
- VSDD: spec (this) → adversary review of the spec → build → adversary review of the build → converge.

## Acceptance
A draft pushed with published:false is NOT public; `zenn preview` + screenshot lets the agent judge; flipping to
published:true + push makes it live (verified by HTTP 200). Unattended path can only ever draft. PAT rotated.
