# 9f — the launch post is live on X, read back logged out

Dais posted the one-time launch himself. The agent must not post it again; a second post would
duplicate a launch that already happened. This file records the public readback that closes the row.

## The post

| | |
|---|---|
| URL | `https://x.com/diceai0/status/2080975554862530564` |
| Posted | 2026-07-25T11:16:49Z (2026-07-25 20:16 JST) |
| Account | `@diceai0` — display name Dice, user id `1731468246094905344` |
| Media | one video, 1080x1920, 25.37s, media id `2080975531315691520` |
| Follow-up | `https://x.com/diceai0/status/2080975867220754517` — self-reply one minute later carrying `https://aniccaai.com/life-manager` |

First line of the post body, as fetched:

> "You have said sorry for being late so many times the word stopped meaning anything."

The body goes on to state that Life Manager calls ten minutes before you need to leave and keeps
ringing until you answer, that it reads the calendar together with travel time, and that it mails the
other party before you do when you are going to be late. It closes on "I stopped managing my day. It
manages me." The "Try Life Manager" line required by §10.0-8 is the narration's closing phrase in the
video, not text in the post body.

## Logged-out readback

Three unauthenticated paths, no cookies:

1. X's own syndication endpoint used for embeds — `https://cdn.syndication.twimg.com/tweet-result?id=2080975554862530564`
   returns `user: diceai0`, `created_at: 2026-07-25T11:16:49.000Z`, `video: true (25370ms)`.
2. fxtwitter's unauthenticated reader returns `code: 200` with `author.protected: false` and the full body.
3. The video file itself fetches unauthenticated: `http=206`, `content_type=video/mp4`.

Fetching `https://x.com/…` directly with a browser user-agent returns empty OG meta, because X withholds
meta from unapproved crawlers. That is a crawler policy, not a visibility one — path 1 is X's own
unauthenticated endpoint and it serves the post.

## Correction to the spec's account assumption

§10 recorded that Postiz had `aniccaxxx` connected and `diceai0` unregistered, implying two accounts.
There is one: `aniccaxxx` is a former handle of the same account now called `diceai0`. Every
`from:aniccaxxx` search returns diceai0's posts, and no separate `aniccaxxx` account exists.

The launch was posted by hand, so no Postiz published-state row exists for it. The nearby diceai0 post
ids in `~/.openclaw/logs/article-resume.log` (`2081001000085991425`, `2081053548348121161`) belong to the
article-writer pipeline's X Articles and are unrelated.

## Not verified

The video's narration audio was not played back, so the spoken "Try Life Manager" closer is inferred from
the format ruling rather than heard. `crwl` could not be used for the logged-out read — its Playwright
install is missing `chromium_headless_shell-1228` and the binary cannot launch, so the default
logged-out verification tool is currently broken and wants `playwright install chromium`.
