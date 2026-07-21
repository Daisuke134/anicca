# I Returned My Laptop. From Today, I Build AI on an iPhone.

Orca is an Agent IDE that turns a phone into a remote control for a computer at home. This is my setup and an honest account of the first day.

## The day I returned my MacBook

I returned my MacBook to my university. When I leave home now, the only computer in my hand is an iPhone. I still have a Mac Mini at home, so I decided to leave the computation there and control my AI coding agents from the phone.

The tool I tried is Orca. It is an Agent IDE that runs Claude Code, Codex, and other coding agents in separate git worktrees. Its mobile companion is deliberately a remote control for the desktop app, not a full code editor squeezed onto a small screen.

On July 20, I installed Orca v1.4.146 on the Mac Mini and paired it with my iPhone 15 over Tailscale. It does not feel like development happening inside the phone. It feels like carrying my home development environment in my pocket.

## The mobile development landscape

I initially framed the choice as home machine versus cloud. That was too simple. Some products let the same mobile interface control either a local machine or a cloud VM.

The useful questions are where the canonical code and state live, whose computer executes the agent, and what path connects the phone to that computer.

| Option | Code and execution | Connection | Best fit |
|---|---|---|---|
| Orca | Your desktop | Direct device connection | Agent workflows |
| Happy | Your PC | End-to-end encrypted relay | Claude Code |
| SSH + tmux | Home machine | SSH or mosh | Terminal workflows |
| Claude Code on the web | Anthropic VM | App or browser | Cloud sessions |
| Codex cloud | OpenAI sandbox | ChatGPT app | Cloud tasks |
| Codespaces | GitHub-managed environment | Browser | Cloud dev environment |
| Remote Tunnels | Your machine | Microsoft relay | VS Code |
| Cursor | Cloud or your own machine | Native iOS app | Agent control |

Claude Code Remote Control executes on your own computer and relays messages through the Anthropic API. Cursor's iOS beta can control cloud VMs or your own machines. There is a spectrum, not a clean split.

I chose Orca because I wanted to keep using the repositories, credentials, tools, and half-finished state already living on my Mac Mini.

## What Orca is

Orca gives every task its own git worktree and dedicated terminal. It supports Claude Code, Codex, OpenCode, OpenClaw, Pi, and several other agents.

```mermaid
flowchart TD
    A[iPhone] --> B[Tailscale]
    B --> C[Mac Mini]
    C --> D[Orca]
    D --> E[git worktree]
    E --> F[AI coding agent]
```

From the phone, I can reply to an agent, browse files, stage and commit changes, and create a workspace. Orca intentionally leaves out a full editor. In my setup, the Mac Mini and iPhone join the same Tailscale network and connect directly. Orca Relay stays off.

![Official Orca mobile companion screen](assets/orca/orca-mobile-official.jpg)

*Orca's official mobile screen puts the connected desktop, recent worktree, and Claude or Codex usage in one view.*

## Setup, Homebrew, and the pairing QR code

The first trap was the Homebrew package name. Plain `brew install --cask orca` installs an old Plotly tool with the same name, not the Agent IDE. I had to include Orca's tap.

```sh
brew install --cask stablyai/orca/orca
xattr -dr com.apple.quarantine /Applications/Orca.app
open -a Orca
```

I removed the quarantine attribute to get past Gatekeeper, allowed the following access prompts, selected Claude as the default agent, kept the system theme, and skipped notifications. I added `/Users/anicca/anicca-project` as a project. Once its branches and terminal appeared, the desktop side was ready.

Pairing starts from “Orca Mobile” in the desktop sidebar. The important choice is the network address. I selected the Tailscale address, `100.99.82.95 (utun0)`, instead of the LAN address, and enabled Tailscale on the iPhone. Because Orca Relay stayed off, this was a peer-to-peer connection over Tailscale.

The QR code expires after a few minutes. I sent fresh copies to the iPhone through Telegram and Gmail. The Gmail copy worked, and the phone paired at about 8:40 p.m. If the desktop app closes, the connection drops. It reconnects automatically after the app opens again.

## First-day notes

My notes after using Orca iOS for a day were blunt:

> It creates worktrees automatically, and the base branch for each session is easy to understand. That is excellent.
>
> I can connect to Claude, Codex, or OpenClaw with one tap. It also appears to integrate with GitHub Issues and Linear.
>
> I can return to a recent session with one tap. The connection to the Mac Mini has been solid, and parallel development is much easier. The bottom of the screen also shows my remaining Codex and Claude usage.
>
> I can finally leave PC-based development behind without worrying about it.

The mapping between a session and its base branch matters more than I expected. A phone interface that merely exposes a terminal still makes me remember which shell belongs to which job. Orca creates a worktree per task and gives every session a visible entry point, so I lose track less often.

The usage meters are not estimates based on local session time. Orca asks each provider for live usage. For Claude, it calls Anthropic's OAuth usage endpoint and falls back to reading `/usage` from the Claude CLI. For Codex, it calls ChatGPT's usage endpoint and can fall back to `codex app-server` rate-limit data.

Before Orca, I had used Cmux, a Ghostty-based macOS terminal with vertical tabs, notifications, a browser, workspaces, splits, and a CLI. Cmux gives me primitives and stays out of the way. Orca makes stronger decisions about worktrees, agents, diff review, and external service integrations.

I found Orca easier because I wanted the second kind of tool. Someone who enjoys assembling a terminal workflow may prefer Cmux.

This is still a first-day impression. I need a week to judge long-running connection stability, terminal interaction from the phone, and notifications while I am away from home.

## Cloud execution and the location of state

Claude Code on the web clones a GitHub repository into an Anthropic-managed VM. My local `~/.claude/CLAUDE.md` does not travel with it, and Anthropic documents no secrets store for the environment. Network access can be None, Trusted, or Full. With Orca and Tailscale, the repository, tools, and execution all remain on my Mac Mini.

| Question | Orca + Mac Mini | Claude Code on the web | Codex cloud |
|---|---|---|---|
| Execution | Home Mac Mini | Anthropic VM | OpenAI sandbox |
| Repository | Existing local environment | Fresh GitHub clone | Cloud sandbox |
| Connection | Tailscale peer-to-peer | App or browser | ChatGPT app |
| Home dependency | Mac Mini must stay available | Environment must be recreated | Environment must be recreated |

The real difference is the location of state. Orca is straightforward when the settings, tools, credentials, and working repositories I care about already exist on one machine. A cloud session makes more sense when the goal is to remove that home-machine dependency.

There is a technical loophole. Reaching a home machine from a cloud sandbox through Tailscale is not structurally impossible. Tailscale can run without a TUN device in userspace mode and expose a SOCKS5 or HTTP proxy. Its DERP relays can build a tunnel from any device that can open an HTTPS connection to an arbitrary host.

Claude Code on the web sends all outbound traffic through Anthropic's HTTP/HTTPS security proxy. None blocks outbound access, and Tailscale hosts are not in the default Trusted allowlist. Full access or a custom allowlist is the plausible route. SSH traffic would also need a `ProxyCommand` pointed at the local SOCKS5 proxy because userspace mode does not add a normal network interface.

In theory, Full network access, userspace `tailscaled`, and DERP over port 443 could work. I found no report of anyone successfully starting that path inside a Claude Code web VM. I also have not verified whether Anthropic's proxy permits the required HTTPS CONNECT behavior or whether `tailscaled` can use that proxy correctly.

Tailscale publishes an official GitHub Codespaces setup, but that method provides `/dev/net/tun`, so it is not the same environment. I cannot honestly claim that a Claude cloud session always can or never can reach a home machine. I can say that the Orca and Tailscale path already connected my iPhone to my Mac Mini.

## Who should use it

Orca makes sense for someone with an always-available computer at home or at work, with repositories and agent tooling already configured there. It also fits people running Claude Code and Codex in parallel who want the branch and worktree relationship visible from a phone. The mobile app is for instructions, approvals, and diff review more than precise code editing.

It is a poor fit if the goal is to eliminate dependence on a home computer. It is also a poor fit if you want to edit code line by line on the iPhone. Closing the desktop app cuts the connection, so keeping the Mac Mini and Tailscale available is part of the deal.

For a flexible terminal, SSH, mosh, tmux, and Cmux remain good options. VibeTunnel and code-server cover browser-based access. Happy and Remote Tunnels control your own computer through a vendor relay. The choice comes down to which parts you want to own: the canonical code, the execution machine, and the connection path.

On day one, Orca did not replace my MacBook. It turned the iPhone into a clear control panel for several agents running on the Mac Mini. That narrower promise is exactly why it has worked well so far.

I will update this after a week with connection stability, terminal usability, and agent visibility measured in actual use. Then I will know whether the first-day enthusiasm survived or whether I moved more work into the cloud.

## Sources

- https://www.onorca.dev/docs/mobile
- https://www.onorca.dev/whats-new/posters/orca-mobile.jpg
- https://github.com/stablyai/orca
- https://code.claude.com/docs/en/remote-control
- https://code.claude.com/docs/en/claude-code-on-the-web
- https://tailscale.com/docs/concepts/userspace-networking
- https://tailscale.com/docs/reference/connection-types
- https://tailscale.com/docs/integrations/github/github-codespaces
- https://github.com/stablyai/orca/blob/main/src/main/rate-limits/claude-fetcher.ts
- https://github.com/stablyai/orca/blob/main/src/main/rate-limits/codex-fetcher.ts
- https://github.com/manaflow-ai/cmux
- https://happy.engineering
- https://github.com/omnara-ai/omnara
- https://mosh.org
- https://cursor.com/docs
- https://docs.github.com
- https://code.visualstudio.com/docs/remote/tunnels
- https://coder.com/docs
- https://ona.com/docs
- https://openai.com
- https://jules.google/docs/faq
- https://docs.devin.ai/get-started/devin-intro
