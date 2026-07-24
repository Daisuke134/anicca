# 9e TikTok direct file/script migration — gated

## Outcome

The repository now contains a direct TikTok Studio file/script adapter that attaches to the
existing CloakBrowser CDP profile. It consumes the exact MP4 and caption paths and preserves
Postiz's terminal `state`, `post_url`, and `post_id` contract.

Postiz remains the default. The direct adapter is selected only when
`LM_TIKTOK_DIRECT_MIGRATION=1` is exactly present. That gate is not enabled because the real
authenticated upload preflight does not pass yet.

## Equivalence and migration contract

- Python distribution tests: `10/10` PASS.
- Node direct-adapter tests: `8/8` PASS.
- Both routes receive the same exact video/caption paths and are ledger-bound to their SHA-256.
- A direct success must return an individual `/video/<numeric-id>` URL, logged-out `yt-dlp`
  readback with exact id/caption, route `direct_browser`, and provider cost USD `0`.
- The distribution ledger preserves route, cost, logged-out status, and real migration date.
- Postiz can be retired only after two distinct consecutive real dates satisfy every direct-row
  condition. Duplicate, gapped, simulated, costly, non-public, or non-readback rows do not count.
- `playwright-core` is pinned to the already proven CloakBrowser-compatible runtime version and
  connects to the existing default CDP context; it downloads or launches no second browser.

## Real preflight and stop boundary

The exact A03 video/caption preflight reaches the real TikTok service and returns
`authentication_required`; no file is uploaded and no post is created.

Three bounded credential/session paths are exhausted:

1. The existing CDP session redirects to TikTok login.
2. A stored credential belongs to a different managed TikTok account and is rejected for this
   target; it is not reused or copied.
3. The target credential reaches TikTok's real email-verification challenge. The masked managed
   mailbox is absent from connected gog/Gmail accounts, no matching Keychain/env mailbox
   credential exists, and the domain mail endpoint does not yield an authenticated inbox.

The verification code is not guessed and the challenge is not bypassed. Direct migration rows,
direct public URLs, and direct posting costs remain `0`. Existing Postiz distribution ledger rows
remain `3`, and the launchd environment remains on the Postiz default.

## Upstream basis

- Playwright documents that file uploads use `Locator.setInputFiles` against an input whose type is
  `file`. Source: [Playwright input documentation](https://github.com/microsoft/playwright/blob/main/docs/src/input.md#upload-files).
- Playwright documents that the existing default browser context is available through
  `Browser.contexts` after `connectOverCDP`. Source:
  [Playwright BrowserType documentation](https://github.com/microsoft/playwright/blob/main/docs/src/api/class-browsertype.md#async-method-browsertypeconnectovercdp).

## Remaining L3 gate

Access to the already-designated verification mailbox is required. After authenticated preflight,
the direct gate can be enabled for two real daily videos. Each needs a new direct public URL,
logged-out exact readback, and zero-cost ledger row before Postiz is retired.
