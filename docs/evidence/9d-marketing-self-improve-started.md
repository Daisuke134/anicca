# 9d Marketing self-improve — started

## Result

The permanent `ai.anicca.life-manager-daily` route now measures the exact Instagram/TikTok
creative pair after deterministic distribution and appends one closed, idempotent metrics row per
real JST date. It reaches `done` only after seven consecutive distinct real dates; gaps reset the
streak and neither backfill nor simulation is accepted.

The controlled launchd run finishes with exit `0` through
`codex/gpt-5.6-luna/medium`, attempt `1`. The job is restored to the canonical
`/Users/anicca/Projects/life-manager-main/...` path after the controlled worktree run.

## Real Day 1 readback

- Status: `started`, day `1/7`; private append-only ledger mode `0600`, one row.
- Creative: `A03`; next creative: `A04`.
- Video SHA-256: `d9e97b386e8ae9098c0f6b92a1824a2060f054e654a284c1cc42fa15bb668ab3`.
- Caption SHA-256: `0f34758f04cecfa16baf8d3e761e464096638bdea4a42c92d80d2d38a69777b2`.
- Instagram: <https://www.instagram.com/reel/DbKkdfjsaTZ/> — views `17`, likes `0`,
  comments `0`, provider readback.
- TikTok: <https://www.tiktok.com/@anicca_buddha/video/7665973874504256785> — views `9`,
  likes `0`, comments `0`, logged-out `yt-dlp` readback.
- Unavailable values remain JSON `null`: watch-time, completion, clicks, signups. They are not
  inferred from views.
- Recorded reason: combined baseline views `26`; establish the first measured reference, then
  change only the next bank creative to `A04`.
- Same-date direct rerun keeps the ledger at one row. Controlled launchd keeps the distribution
  ledger at three rows and the self-improve ledger at one row, so it reposts neither platform.
- The existing one-screen Telegram report is delivered as real message id `3379`.

## TDD and failure isolation

- Core contract: `5/5` PASS. It rejects hash mismatch, nonnumeric views, same-day duplication,
  simulated date backfill, and a nonconsecutive seven-row sequence.
- Daily runtime contract: `8/8` PASS. Generation-only mode never measures; distribution or metric
  failure stops before the agent; successful measurement is immutable input to Luna.
- Controlled method 1 exits `2` before the agent because the shell's inherited `errexit` hides the
  parse boundary. Corrective parsing makes all three closed-schema boundaries observable.
- Controlled method 2 reaches both providers but exits `70` before the agent: integration expects
  `reason`, while the ledger schema emits `next_change_reason`.
- A corrective RED reproduces that schema mismatch. The minimal key fix returns all tests to GREEN.
  Controlled method 3 finishes exit `0`; failed methods create no post, agent report, or Telegram
  side effect.

## Upstream basis

- instagrapi maps provider fields directly: “`media["play_count"] =
  media.get("play_count", media.get("video_play_count", 0))`” and preserves like/comment counts.
  Source: [instagrapi extractors](https://github.com/subzeroid/instagrapi/blob/master/instagrapi/extractors.py).
- yt-dlp's TikTok extractor maps “`view_count`: `play_count`”, “`like_count`: `digg_count`”, and
  “`comment_count`: `comment_count`”.
  Source: [yt-dlp TikTok extractor](https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/tiktok.py).

## Remaining real-time gate

9d stays pending. Six more distinct real daily runs must append their actual IG/TT URLs, metrics,
and next-change reasons. The seventh consecutive real row alone may change the status to `done`.
