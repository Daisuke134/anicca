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

結論: **「自宅遠隔 vs cloud の 2 系統しかない」は不正確。** 同一 UI が両方を選べる製品（Claude Code app、Cursor mobile）や自社 VPC 実行（Ona）が存在する。分類は 3 軸:
①コード（状態）の正本がどこにあるか ②誰の計算機で実行するか ③接続経路（direct P2P / vendor relay / SSH / public tunnel / browser）。

**主要プレイヤー（一次情報で確認済み、2026-07-20 時点）:**

| 製品 | 実行場所 | 接続経路 | 根拠 |
|---|---|---|---|
| Orca (stablyai/orca, MIT, 22,980★, v1.4.146) | 自分の desktop | device token 直結、relay 無し | onorca.dev/docs/mobile "The pairing exchange happens directly between desktop and phone… there is no cloud relay." |
| Happy (slopus/happy, MIT, 22,742★) | 自分の PC | Happy Server relay（E2EE） | happy.engineering "We store and relay opaque ciphertext. We never receive the key." |
| Omnara (2,651★, **archived**、新 platform へ移行) | 自分の machine | Omnara API/DB 経由 relay | github.com/omnara-ai/omnara "We've migrated to a new… platform" |
| VibeTunnel (**amantus-ai**/vibetunnel、steipete は 404、4,600★) | 自宅 Mac/Linux | browser。推奨 Tailscale P2P | README "Tailscale creates a secure peer-to-peer VPN" |
| SSH 古典解: Termius / Blink (6,861★) / mosh (14,191★) + tmux (47,898★) | 自宅マシン | SSH/UDP 直結 | mosh.org "logs in… via SSH… connects… over UDP" |
| Claude Code web/iOS | Anthropic VM（cloud session）。app は "client… rather than a place where code runs" | browser/app。**Remote Control なら自分の PC 実行 + Anthropic relay** | code.claude.com/docs/en/mobile + /remote-control "All traffic travels through the Anthropic API over TLS" |
| OpenAI Codex cloud | OpenAI cloud sandbox | ChatGPT mobile app | openai.com "on the cloud via the Codex web, GitHub, and the ChatGPT mobile app" |
| Google Jules | Google cloud VM（task ごとに fresh VM） | web。mobile 正式対応は未確認 | jules.google/docs/faq "Each task runs in a fresh virtual machine" |
| Cursor Cloud Agents (iOS beta) | **選べる**: cloud VM / Self-Hosted Pool / My Machines | native iOS app | cursor.com/docs "controlling agents running in the cloud and on your local computer" |
| Devin | cloud（"cloud Devin"、local CLI から /handoff） | mobile 正式仕様 **未確認** | docs.devin.ai/get-started/devin-intro |
| GitHub Codespaces | GitHub 管理 container/Azure VM（永続 storage） | browser | docs.github.com "hosted by GitHub in a Docker container" |
| vscode.dev + Remote Tunnels | **自分の machine**（hybrid） | Microsoft dev tunnels relay、SSH 不要 | code.visualstudio.com/docs/remote/tunnels "secure tunnel… without SSH" |
| code-server (78,451★, v4.129.0) | 自分の machine/VM に self-host | browser（経路は自分で用意） | coder.com/docs "Run VS Code on any machine anywhere" |
| Gitpod→**Ona**（Classic 終了 2025-10-15） | Ona Cloud or 自社 AWS/GCP VPC | browser VS Code | ona.com/docs "Deploy on Ona Cloud or in your own AWS or GCP account" |

**2026 年の新顔（stars>100、抜粋）:** CloudCLI/claudecodeui 12,758★（self-host/cloud 両対応）、Paseo 10,914★（自分の machine + relay）、Agent of Empires 2,847★（local tmux + Tailscale Funnel/Cloudflare Tunnel）、CC Pocket 981★（self-host Bridge + Tailscale）、handmux 116★（自分の tmux を phone browser へ）他多数 — この 1 年で「自宅マシン + phone」系 OSS が爆発的に増えている。

**記事上の扱い:** [2] の表は代表 8 個程度に絞る（Orca / Happy / SSH古典 / Claude Code web / Codex cloud / Codespaces / Remote Tunnels / Cursor）。軸は「コードの正本がどこ × 誰のマシンで走る × 経路」を平易に。「2 系統」でなくスペクトラムであることを一言。

## 未確認事項（記事で断定しない）

- Devin の native mobile app 正式仕様 / Jules の mobile 正式対応 / Codespaces の GitHub Mobile app 内 full editor
- Claude Code web sandbox 内での tailscaled 実起動（報告 0 件）
