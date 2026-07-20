# Orca 記事リサーチ（★未検証5項目★の一次情報検証、2026-07-20）

執筆用の唯一の材料。カード = `topics/in-progress/orca-phone-coding-setup.md`、セットアップ実測 = `docs/reference/orca-mac-mini-mobile-setup.md`。

## 件3: cloud sandbox から Tailscale で自宅マシンに入れるか（[6] の材料）

結論: **「構造的に不可能」ではない。原理上可能（条件付き）だが、Claude Code web sandbox での実起動報告はゼロ = E2E 未確認。**

- Tailscale userspace networking は TUN device 不要で、`tailscaled` が SOCKS5/HTTP proxy として動く。引用: "userspace networking mode offers a different way of running, where `tailscaled` functions as a SOCKS5 or HTTP proxy" — https://tailscale.com/docs/concepts/userspace-networking
- DERP relay は HTTPS で通る: "Any device that can open an HTTPS connection to an arbitrary host can build a tunnel using DERP relays." — https://tailscale.com/docs/reference/connection-types
- Claude Code on the web の network 設定は None / Trusted(allowlist) / Full。ただし全 outbound が Anthropic の HTTP/HTTPS proxy 経由: "Environments run behind an HTTP/HTTPS network proxy… All outbound internet traffic passes through this proxy" — https://code.claude.com/docs/en/claude-code-on-the-web#security-proxy
- 従って None=不可、Trusted=Tailscale ホストが既定 allowlist に無く不可、**Full（または custom allowlist）のみ候補**。さらに SSH は userspace TUN では自動 routing されず、`ProxyCommand` で localhost の SOCKS5 に通す必要がある。
- GitHub Codespaces には公式実績があるが `/dev/net/tun` を渡す方式で条件が違う: https://tailscale.com/docs/integrations/github/github-codespaces
- Claude sandbox 内での tailscaled 実起動の報告は gh search 0 件。**未確認**。最大の不確実性 = Anthropic proxy が tailscaled の HTTPS CONNECT を許すか + tailscaled がその proxy 設定を使えるか。

記事上の扱い: 「理屈の上では穴がある（Full network + userspace tailscaled + DERP over 443）が、動いたという報告は見つからなかった。私は未検証」と書く。「構造的に不可能」とは書かない。

## 件4: Orca の残量表示の仕組み（[5] の 1 行裏取り）

結論: **各 provider の live rate-limit API を直接読んでいる（ローカル session データ集計ではない）。**

- Claude: `https://api.anthropic.com/api/oauth/usage` を OAuth Bearer で fetch。失敗時は Claude CLI の `/usage` を hidden PTY で読む fallback。 — https://github.com/stablyai/orca/blob/main/src/main/rate-limits/claude-fetcher.ts
- Codex: `https://chatgpt.com/backend-api/wham/usage`（ソースコメント: "reuse Codex's own get_rate_limit_status endpoint"）、fallback = `codex app-server` の `account/rateLimits/read`。 — https://github.com/stablyai/orca/blob/main/src/main/rate-limits/codex-fetcher.ts

## 件5: Cmux とは（乗り換え元の名指し 1 行）

- **manaflow-ai/cmux** — "Open source Ghostty-based macOS terminal with vertical tabs and notifications for AI coding agents."（repo 説明）。24,833 stars、Swift/AppKit、main 最終 commit 2026-07-20（現役）。 — https://github.com/manaflow-ai/cmux
- README: "cmux is a primitive, not a solution… terminal, browser, notifications, workspaces, splits, tabs, and a CLI"。Orca（Electron 系 Agent IDE、workflow 込み）に対し、Cmux は native terminal multiplexer + embedded browser で workflow を強制しない設計。

## 件1-2: 競合全数調査 + 分類軸（[2] の材料）

（research-landscape の結果をここに追記する）
