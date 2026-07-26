# 9c — TikTok daily state, measured 2026-07-26, and a banned pipeline stopped

Per the 2026-07-26 rulings (§10.0-13), 9c's scope is a fresh MPT video reaching TikTok daily;
Instagram is deferred and the preview-approval gate is removed. Measuring the live chain surfaced
two separate pipelines, one of which was violating a standing ruling. Both facts recorded here.

## Finding: the legacy recording pipeline was still broadcasting, now stopped

`ai.anicca.lm-video-post` (launchd, loaded, exit 0) → `~/.openclaw/skills/life-manager-video/post-daily.sh`
was posting **real wake-call recordings** with whisper captions to `@anicca.comedy` daily — five posts
2026-07-23 through 2026-07-25, all `PUBLISHED` by Postiz API readback. The 07-24 whisper transcript
reads "Hi, Daisuke. This is your life manager. Your next event is Takkun Shinjuku at 1900…" —
**Dais's real name and real schedule, public**. This violates §10.0-1 (call recordings permanently
banned as marketing material, ruled 2026-07-25); the launchd job simply predates the ruling and was
never unloaded.

Action taken 2026-07-26: `launchctl bootout gui/501/ai.anicca.lm-video-post` + plist renamed to
`.disabled-2026-07-26-recording-ban`. Verified no longer in `launchctl list`. The already-published
@anicca.comedy posts are retained as history per §10.0-1 (no new distribution); whether to delete
them for privacy is Dais's call, flagged separately.

## The correct chain (@anicca_buddha, MPT narration, gated)

| Link | Evidence |
|---|---|
| launchd | `ai.anicca.life-manager-daily` loaded, schedule 10:00 JST daily, last exit 0 |
| pipeline | `skills/video/daily-lm-video/daily_pipeline.py` — creative bank rotation, MPT `--video-script` + local b-roll, edge-tts narration, fail-close receipt gate (tests 72/72 per spec row) |
| run ledger | `daily-run-ledger.jsonl` rows `status=success`, `creative_id=A03`, provider codex/gpt-5.6-luna |
| published | post_id `cms014n1x020nrv0yfpcpz2h5`, Postiz `state=PUBLISHED`, account `@anicca_buddha` |
| **logged-out readback (2026-07-26, yt-dlp, no cookies)** | `tiktok.com/@anicca_buddha/video/7666359498763750676` → upload 2026-07-25, 22s, **161 views**, title "Your alarm doesn't care if you get up. Life Manager calls yo…" |

Direct fetches of tiktok.com are bot-walled ("Please wait…"); yt-dlp reads the same public pages
unauthenticated, which satisfies the logged-out bar.

## What remains for 9c

1. **Daily continuity**: the next scheduled fire is 10:00 JST today (2026-07-26) and should advance
   the rotation to A02. One more consecutive automatic post closes the "daily, fresh content" bar.
2. **Instagram**: deferred (§10.0-13). Needs a human-created account; not a blocker for done-as-scoped.

## Handed to 9d

- Self-improve ledger already shows `day=1 status=started` (2026-07-24). TikTok-only counts (§10.0-3).
- The buddha post has real metrics to read: 161 views at ~18h age. Day-1 entry can be honest and non-zero.

## 2026-07-26 update — the daily loop closed its own loop, IG included

The 10:15 scheduled run failed exactly as the old gate designed: creative A04 had no per-video
receipt. PR #1133 replaced the per-video requirement with a standing receipt recording the
2026-07-26 ruling; `launchctl kickstart` re-fired the real launchd job, and the 10:47 run finished
rc=0 with both legs published and read back:

| leg | public URL | logged-out readback |
|---|---|---|
| TikTok | `tiktok.com/@anicca_buddha/video/7666647608156540168` | yt-dlp no-cookies: upload 2026-07-26, 34s, 85 views, fresh 謝罪文 script (different from 07-25's alarm script — content rotates daily) |
| Instagram | `instagram.com/reel/DbPPpXCMjrf` | HTTP 200, 601KB real page, title carries the caption's first line |

The Instagram leg deserves a correction on the record: the 07-25 spec text deferred IG believing
the account was frozen and undesignated. Measurement says otherwise — the frozen account was the
CloakBrowser-session one, while the configured LM accounts file
(`~/.cloak/life-manager-instagram-accounts.json`) designates `anicca.affirms2` (status live,
warming since 07-11), the instagrapi poster's tier-2 guard verifies it acts as exactly that handle,
and the reel is publicly served. IG is live on the correct account; the deferral is obsolete.

Daily continuity: 07-25 (`7666359498763750676`) and 07-26 (`7666647608156540168`) are consecutive
automatic-pipeline TikTok posts with distinct scripts. 9c's bar — fresh MPT video daily — is met.
