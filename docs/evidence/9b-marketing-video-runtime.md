# 9b marketing video runtime evidence

## Scope

- Atomic: `9b` / `MKT-b` / `M-2`
- Branch: `atomic/9b-marketing-video`
- Accepted base: `origin/main@4209a66c58dc49125bcdac986788c58d10ec7c3a`
- Code head before evidence closure: `cd95bf1e9a0f0624daa1194f47c8c87528350f7b`
- Distribution remains locked with `LM_DAILY_GENERATION_ONLY=1`; atomic 9c owns public posting.

## Upstream decisions

- [MoneyPrinterTurbo README](https://github.com/harry0703/MoneyPrinterTurbo/blob/main/README.md):
  “自动生成视频脚本、匹配素材、生成字幕和背景音乐，并合成高清短视频。”
  The implementation reuses this local composition shape: existing footage, real call audio,
  Whisper subtitles, proof image, and FFmpeg. It does not add a new account or loop.
- [Apple launchd.plist manual](https://github.com/apple-oss-distributions/launchd/blob/main/man/launchd.plist.5):
  “StartCalendarInterval <dictionary of integers or array of dictionary of integers>”.
  The existing label and 10:15 calendar interval remain unchanged.
- [FFmpeg ffprobe documentation](https://github.com/FFmpeg/FFmpeg/blob/master/doc/ffprobe.texi):
  “a positive exit code is returned” when input cannot be opened or recognized.
  The runtime validates JSON `show_streams`/`show_format` output and propagates failures.

## TDD and verification

- RED 1: generator test errors because `daily-lm-video/generate.py` is absent.
- RED 2: runtime test returns 127 because `life-manager-daily.sh` is absent.
- GREEN: generator tests `5/5`; runtime/launchd tests `6/6`.
- Regression found in controlled launchd method 1: Luna invokes the daily wrapper recursively.
  Corrective RED covers prompt contract and `LM_DAILY_ACTIVE`; GREEN blocks recursion with exit 73.
- Regression found in method 2: a combined generation/distribution prompt self-monitors the active
  route instead of terminating. The process is stopped before public/provider mutation.
- Corrective method 3 separates the 9b generation gate from 9c distribution. The prompt receives
  exact bank/state/output paths, forbids broad search and mutation, and terminates after validation.
- Life Manager full test command exits 0 with fail 0.
- `npm run eval` remains 100% across calendar, late, context, score, intent, mental, and physical.
- Secret scan: gitleaks reports no leaks in `skills/life-manager` and `skills/video`.

## Real provider and launchd evidence

- Fresh provider probe: `gpt-5.6-luna` returns `LM_LUNA_PROVIDER_OK`, exit 0.
- launchd label: `ai.anicca.life-manager-daily`.
- launchd cadence: hour 10, minute 15.
- Controlled method 3: run count `0→1`, last exit code `0`.
- Corrective readback run: run count `1→2`, last exit code `0`.
- Agent summary:
  - task class: `marketing-agent`
  - route: `luna-medium-decision`
  - provider/model/effort: `codex` / `gpt-5.6-luna` / `medium`
  - status/attempts: `success` / `1`
- Latest usage row:
  - provider-reported tokens: input 44,328; cached input 27,136; output 1,241;
    reasoning output 379; total 45,569
  - cost tier: subscription
  - actual marginal cost: USD 0
  - provider API-equivalent cost: unavailable, recorded as null rather than invented
- Private evidence hashes:
  - summary: `5f2af462cf64658e60f1f48551f052fcb518685304b3da19674d7434129324eb`
  - attempts: `06d225c7604073f621a7e739622efd90a5d3c047d09ef5ac51d319e6d818d1ce`
  - result: `8906d84a6a7bb366701aa23d247558dbe6cd94bd0514828d34afc15d57f5725e`
  - private evidence and both runtime ledgers use mode `0600`

## Consecutive automatic generation

The append-only production rotation ledger reads back three consecutive launchd-time selections.
Each file is 1080×1920 H.264/AAC, 34.666667 seconds, and passes a fresh full decode with exit 0.

| Logical day | Creative | SHA-256 | Decode |
| --- | --- | --- | --- |
| day 1 | A01 | `a990f79ba67e085db1a5b023b6f75658231ed6832dcee4167c2ad5a2a3d1c627` | 0 |
| day 2 | A02 | `01e6c9a7d6647c135adb93cd0a705de275bfb86cc254447cc8f2b1b3066eabf1` | 0 |
| day 3 | A03 | `d9e97b386e8ae9098c0f6b92a1824a2060f054e654a284c1cc42fa15bb668ab3` | 0 |

The latest daily run ledger binds creative `A03` to the exact production output, Luna summary,
exit 0, and subscription marginal cost USD 0. No Instagram, TikTok, Reddit, Telegram, calendar,
email, call, DB, or wallet side effect is counted for this atomic.
