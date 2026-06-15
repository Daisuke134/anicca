# OSS Launch X Posts (drafts, 投稿前 Dais 承認 + verbatim-guard 通し)

> Status: draft, NOT auto-posted. Dais reviews + approves before any X post.
> verbatim-guard run as of 2026-06-04 — see verification at end.

## anicca-monk-factory (X post, EN, account @aniccaxxx)

Built a skill that generates AI monk videos like @yangmun2 — locked face, locked voice, 30-script bank rotation → HeyGen render → caption burn → TikTok + IG. One `bash install.sh`.

Inspired by https://x.com/shalevhvs/status/2042242260784537736

github.com/Daisuke134/anicca-monk-factory

---

## mau-clipping (X post, EN, account @aniccaxxx)

Built a skill that clones what @maboroshi_app is running on YouTube — grab the first 3s of a viral Short, stitch your CTA, post to TikTok + IG + YT. One `bash install.sh`.

Inspired by https://x.com/maubaron/status/2030716132093460742

github.com/Daisuke134/mau-clipping

---

## Anti-borrow check (verbatim-guard)

Run before Dais approval:

```bash
. /Users/anicca/.openclaw/skills/_shared/lib/verbatim-guard.sh
vg_check "$(cat <draft-text>)"
```

Both drafts MUST exit 0 (clean) before Dais approval.

## Approval workflow

1. Anicca posts both drafts to Slack #metrics for Dais review.
2. Dais says "OK to post" → post to X @aniccaxxx via twitter-automation skill.
3. No auto-post.

## Verification (2026-06-04)

| draft | verbatim-guard | timestamp |
|---|---|---|
| anicca-monk-factory | CLEAN | 2026-06-04 |
| mau-clipping | CLEAN | 2026-06-04 |
