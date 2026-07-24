# 9c exact Instagram/TikTok distribution evidence

## Scope

- Atomic: `9c` / `MKT-c` / `M-3`
- Accepted base: `origin/main@a342ca5c1e9bc01fe72298649569a75a6db811f4`
- Branch: `atomic/9c-marketing-distribution`
- Existing Instagram account: `anicca.affirms2`
- Existing TikTok Postiz integration: `cmp9txjdp01c8oh0yb6dhlarr`
- No account, marketing loop, renderer, or launchd label is created.

## Upstream decisions

- [Postiz TikTok provider](https://github.com/gitroomhq/postiz-app/blob/main/libraries/nestjs-libraries/src/integrations/social/tiktok.provider.ts):
  “content_posting_method=DIRECT_POST publishes the post to the account.” The adapter therefore
  uses `DIRECT_POST` and `PUBLIC_TO_EVERYONE`, and rejects a Postiz id without `PUBLISHED`.
- [instagrapi upload example](https://github.com/subzeroid/instagrapi/blob/master/examples/upload_media.py):
  `cl.clip_upload(path, caption, thumbnail=thumbnail, trial=True)`. The implementation reuses the
  repository's shared `poster.py` and its `clip_upload` route instead of adding another IG client.
- [yt-dlp TikTok extractor](https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/tiktok.py):
  the public extractor returns the individual `/video/<id>` URL and caption metadata. This is used
  only for logged-out readback when Postiz returns a profile URL instead of the artifact URL.

## TDD and failure handling

- RED: distribution module absent.
- GREEN: both adapters receive the same video path and caption path; the append-only ledger binds
  each platform to the same creative id, video SHA-256, and caption SHA-256.
- Corrective RED: Postiz returned `PUBLISHED` with only
  `https://www.tiktok.com/@anicca_buddha`. A profile URL is not L3 evidence.
- Corrective GREEN: a recent caption-matching public entry must resolve to
  `https://www.tiktok.com/@<handle>/video/<numeric-id>`; old or mismatched entries fail closed.
- Instagram non-publish prevents TikTok invocation. TikTok non-publish preserves the honest IG row
  and exits nonzero. An exact successful contract is idempotent per platform.
- Existing Instagram credential files using `password` and legacy files using `pw` are both covered;
  a missing password fails closed.
- Controlled launchd method 1 found a new self-monitor deadlock in the Luna report step. The exact
  job was terminated before a duplicate post; a regression test then requires the prompt to forbid
  inspecting/waiting for its own PID, launchd state, or evidence.
- Targeted final tests: distribution `8/8`, Postiz `6/6`, IG credential `3/3`, daily runtime/launchd
  `7/7`.
- After `npm ci`, the complete Life Manager test chain reports fail 0. Calendar, late, context,
  score, intent, mental, and physical evals all report 100%.

## Exact creative contract

- Creative id: `A03`
- Local video SHA-256:
  `d9e97b386e8ae9098c0f6b92a1824a2060f054e654a284c1cc42fa15bb668ab3`
- Caption SHA-256:
  `0f34758f04cecfa16baf8d3e761e464096638bdea4a42c92d80d2d38a69777b2`
- Local media: H.264/AAC, 1080×1920, 34.666667 seconds, full decode exit 0.
- Private caption, account registry, and distribution ledger are mode `0600`.

## Real publication and logged-out readback

### Instagram

- Public Reel:
  https://www.instagram.com/reel/DbKkdfjsaTZ/
- Provider code: `DbKkdfjsaTZ`
- The existing deterministic logged-out checker reports `found=true` and
  `verdictMaterial=pass` for account `anicca.affirms2` and this claimed code.

### TikTok

- Public video:
  https://www.tiktok.com/@anicca_buddha/video/7665973874504256785
- Postiz post id: `cmryjod3q0193pe0yastxx34h`
- Integration readback: `disabled=false`, profile `anicca_buddha`.
- Logged-out yt-dlp readback returns id `7665973874504256785`, the exact A03 caption content,
  timestamp `1784873636`, and duration 34 seconds.
- A fresh public download is H.264/AAC, 720×1280 provider transcode, 34.668005 seconds, and passes
  full decode with exit 0.
- The first profile-only Postiz release row remains in the private append-only ledger as an honest
  failed evidence shape. A later row with the same provider id and hashes records the resolved
  individual video URL. It is not rewritten or hidden.

## Real launchd readback

- Label/cadence remain `ai.anicca.life-manager-daily` at 10:15.
- Corrective controlled pass: launchd run count `1→2`, final state `not running`, exit `0`.
- Distribution ledger row count stays `3→3` during the corrective pass, proving that neither
  platform is reposted.
- Agent summary: `marketing-agent / luna-medium-decision / codex / gpt-5.6-luna / medium /
  attempt 1 / success`.
- Daily run ledger records `A03`, exact local output, subscription cost tier, and actual marginal
  cost USD 0.
- Existing one-screen Telegram report is delivered with real message id `3378`.

No email, calendar, call, DB, wallet, on-chain, or new-account side effect is counted for 9c.
