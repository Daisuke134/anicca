# Awesome OpenClaw Skills - Complete Summary
**Research Date:** 2026-02-07
**Source:** https://github.com/VoltAgent/awesome-openclaw-skills
**Total Skills:** 1,715+ (curated from 3,000+ in ClawHub registry)

---

## Installation Methods

| Method | Command | Location |
|--------|---------|----------|
| **ClawHub CLI (Recommended)** | `npx clawhub@latest install <skill-slug>` | Auto-installed |
| **Manual - Global** | Copy skill folder | `~/.openclaw/skills/` |
| **Manual - Workspace** | Copy skill folder | `<project>/skills/` |
| **Alternative** | Paste GitHub repo link in chat | Agent handles setup |

**Priority:** Workspace > Local > Bundled

---

## iOS & macOS Development Skills (14)

**Highly relevant for Anicca iOS project management**

| Skill | Description | Use Case |
|-------|-------------|----------|
| `apple-docs` | Query Apple Developer Documentation, APIs, WWDC videos (2014-2025) | Research iOS APIs |
| `apple-docs-mcp` | Apple docs via MCP | Alternative docs access |
| `instruments-profiling` | Profile native macOS/iOS apps | Performance optimization |
| `ios-simulator` | Automate iOS Simulator (simctl + idb) | Device testing automation |
| `macos-spm-app-packaging` | Scaffold, build, package SwiftPM-based macOS apps | macOS builds |
| `PagerKit` | SwiftUI library for page-based navigation | UI implementation |
| `sfsymbol-generator` | Generate Xcode SF Symbol asset catalog | Icon management |
| `swift-concurrency-expert` | Swift Concurrency review for Swift 6.2+ | Code review |
| `swiftfindrefs` | List Swift source files referencing a symbol | Code navigation |
| `swiftui-empty-app-init` | Initialize minimal SwiftUI iOS app | Project scaffolding |
| `swiftui-liquid-glass` | iOS 26+ Liquid Glass API | Advanced UI |
| `swiftui-performance-audit` | Audit SwiftUI runtime performance | Performance review |
| `swiftui-ui-patterns` | Best practices for SwiftUI views | UI guidance |
| `swiftui-view-refactor` | Refactor SwiftUI views for consistency | Code refactoring |
| `xcodebuildmcp` | **Xcode build/test/run workflows, simulator control** | **Build automation** |

**Most Important for Anicca:**
- `xcodebuildmcp` - Build automation (replaces manual fastlane)
- `swiftui-performance-audit` - Optimize app performance
- `swift-concurrency-expert` - Async/await review
- `ios-simulator` - E2E testing automation

---

## Coding Agents & IDEs (55)

**Skills for improving development workflow**

| Skill | Description | Relevance |
|-------|-------------|-----------|
| `skill-creator` | Guide for creating effective skills | **Create custom skills** |
| `skill-creator-0-1-0` | Alternative skill creator | Skill development |
| `skill-creator-2` | Another skill creator variant | Skill development |
| `tdd-guide` | **TDD workflow with test generation** | **Test automation** |
| `coding-agent` | Run Codex CLI, Claude Code, OpenCode, Pi Coding Agent | Multi-agent support |
| `cursor-agent` | Cursor CLI agent | IDE integration |
| `claude-optimised` | Optimize CLAUDE.md files | **Project setup** |
| `claude-team` | Orchestrate multiple Claude Code workers via iTerm2 | Team coordination |
| `code-mentor` | AI programming tutor | Learning support |
| `codeconductor` | Code orchestration | Workflow management |
| `codex-orchestration` | General-purpose Codex orchestration | Task management |
| `coding-standards` | Coding standards enforcement | Code quality |
| `debug-pro` | Systematic debugging methodology | Bug fixing |
| `docker-essentials` | Docker commands and workflows | Containerization |
| `executing-plans` | Execute implementation plans with review checkpoints | Project execution |
| `mcp-builder` | Create MCP servers | Tool development |
| `openspec` | Spec-driven development | **Spec workflow** |
| `receiving-code-review` | Handle code review feedback | Review process |
| `senior-architect` | System architecture design | Architecture decisions |
| `test-runner` | Write and run tests across languages | **Testing** |
| `webapp-testing` | Test web apps with Playwright | E2E testing |

**Most Important for Anicca:**
- `tdd-guide` - Automate TDD workflow
- `claude-optimised` - Keep CLAUDE.md clean
- `openspec` - Follow spec-driven development
- `test-runner` - Multi-language testing

---

## Git & GitHub (34)

| Skill | Description | Relevance |
|-------|-------------|-----------|
| `conventional-commits` | Format commit messages | **Commit standards** |
| `github` | Interact with GitHub via `gh` CLI | **PR automation** |
| `github-pr` | Fetch, preview, merge, test PRs locally | PR workflow |
| `git-essentials` | Essential Git commands | Version control |
| `git-sync` | Auto-sync workspace to GitHub | Backup automation |
| `gitclaw` | **Backup OpenClaw workspace to GitHub via cron** | **VPS backup** |
| `commit-analyzer` | **Analyze git commits to monitor agent health** | **Agent monitoring** |
| `deepwiki` | Query GitHub repo documentation | Documentation |
| `backup` | Backup/restore OpenClaw config, skills, commands | Configuration backup |

**Most Important for Anicca:**
- `gitclaw` - Automated workspace backup
- `commit-analyzer` - Monitor autonomous operation
- `conventional-commits` - Maintain commit standards
- `github-pr` - Automate PR workflow

---

## DevOps & Cloud (144)

**Critical for VPS deployment and monitoring**

| Skill | Description | Relevance |
|-------|-------------|-----------|
| `docker-essentials` | Docker management | **Container management** |
| `docker-diag` | Advanced Docker log analysis | Debugging |
| `pm2` | Manage Node.js apps with PM2 | **Process management** |
| `railway` | (need to verify) | Railway integration |
| `vercel` | Deploy to Vercel | Alternative deployment |
| `flyio-cli` | Fly.io deploy, logs, SSH | Alternative cloud |
| `agentguard` | Security & Monitoring | **Agent security** |
| `agent-news` | Monitor AI agent developments | Stay updated |
| `system-monitor` | Check CPU, RAM, GPU status | **Server monitoring** |
| `uptime-kuma` | Uptime monitoring | Service health |
| `tailscale` | Manage Tailscale tailnet | VPN management |
| `ssh-essentials` | SSH commands and workflows | **Remote access** |
| `security-audit` | Security auditing for Clawdbot | Security review |
| `security-monitor` | Real-time security monitoring | Security alerts |
| `fail2ban-reporter` | Auto-report banned IPs | Intrusion detection |
| `komodo` | Manage Komodo infrastructure | Infrastructure management |
| `proxmox` | Manage Proxmox VE clusters | Virtualization |
| `ansible-skill` | Infrastructure automation with Ansible | IaC |
| `kubernetes` | Kubernetes cluster management | Container orchestration |
| `n8n-automation` | Manage n8n workflows | **Workflow automation** |
| `n8n-monitor` | Monitor N8N via Docker | Workflow monitoring |
| `coolify` | Manage Coolify deployments | Self-hosted PaaS |
| `dokploy` | Manage Dokploy deployments | Self-hosted PaaS |

**Most Important for Anicca VPS:**
- `pm2` - Keep OpenClaw Gateway running
- `system-monitor` - Track VPS resources
- `security-monitor` - Detect intrusions
- `docker-essentials` - Container management
- `n8n-automation` - Workflow automation
- `ssh-essentials` - Remote management

---

## Browser & Automation (69)

| Skill | Description | Relevance |
|-------|-------------|-----------|
| `agent-browser` | Web testing, form filling, screenshots | Browser automation |
| `playwright-cli` | Browser automation via Playwright CLI | **E2E testing** |
| `browsh` | Text-based browser | Headless browsing |
| `browser-use` | Cloud-based browser automation | Managed sessions |
| `clawflows` | Search, install, run multi-skill automations | Workflow library |
| `autofillin` | Automated web form filling | Form automation |
| `firecrawl-search` | Web search and scraping via Firecrawl API | Web scraping |
| `n8n-api` | Operate n8n via REST API | Workflow integration |
| `home-assistant` | Control Home Assistant smart home | IoT integration |

**Most Important for Anicca:**
- `playwright-cli` - Maestro alternative for web testing
- `firecrawl-search` - Research automation
- `n8n-api` - Connect to existing workflows

---

## Communication (58)

| Skill | Description | Relevance |
|-------|-------------|-----------|
| `slack` | **Control Slack via Slack tool** | **Primary communication** |
| `discord` | Control Discord | Alternative communication |
| `telegram-reaction-prober` | Probe Telegram emoji reactions | Telegram integration |
| `whatsapp-styling-guide` | WhatsApp message formatting | WhatsApp integration |

**Most Important for Anicca:**
- `slack` - **Essential for Anicca VPS agent communication**

---

## AI & LLMs (159)

| Skill | Description | Relevance |
|-------|-------------|-----------|
| `context-compressor` | Automated context management | Long sessions |
| `context-recovery` | Recover context after compaction | Session continuity |
| `sophie-optimizer` | Automated context health management | Context optimization |
| `model-usage` | CodexBar CLI cost usage summary | Cost tracking |
| `wandb-monitor` | Monitor Weights & Biases training runs | ML monitoring |

**Most Important for Anicca:**
- `context-compressor` - Manage long-running sessions
- `model-usage` - Track API costs

---

## Monitoring & Automation Skills for VPS

**Critical for running OpenClaw on VPS:**

| Skill | Installation | Purpose |
|-------|-------------|---------|
| `gitclaw` | `npx clawhub@latest install gitclaw` | Auto-backup workspace to GitHub via cron |
| `commit-analyzer` | `npx clawhub@latest install commit-analyzer` | Monitor agent health via commit patterns |
| `system-monitor` | `npx clawhub@latest install system-monitor` | Track CPU/RAM/GPU |
| `pm2` | `npx clawhub@latest install pm2` | Keep Gateway running |
| `security-monitor` | `npx clawhub@latest install security-monitor` | Real-time security alerts |
| `slack` | `npx clawhub@latest install slack` | Post to Slack channels |
| `n8n-automation` | `npx clawhub@latest install n8n-automation` | Workflow orchestration |
| `clawlist` | `npx clawhub@latest install clawlist` | Multi-step project tracking |

---

## Recommended Skills for Anicca Project

### Immediate Priority (VPS Agent)

```bash
# Install via ClawHub CLI
npx clawhub@latest install slack
npx clawhub@latest install gitclaw
npx clawhub@latest install commit-analyzer
npx clawhub@latest install system-monitor
npx clawhub@latest install pm2
npx clawhub@latest install security-monitor
```

### Development Priority (Coding Agent)

```bash
npx clawhub@latest install skill-creator
npx clawhub@latest install tdd-guide
npx clawhub@latest install xcodebuildmcp
npx clawhub@latest install swiftui-performance-audit
npx clawhub@latest install conventional-commits
npx clawhub@latest install github-pr
npx clawhub@latest install claude-optimised
```

### Optional but Useful

```bash
npx clawhub@latest install n8n-automation
npx clawhub@latest install playwright-cli
npx clawhub@latest install context-compressor
npx clawhub@latest install ios-simulator
```

---

## Installation Priority Matrix

| Priority | Skills | Reason |
|----------|--------|--------|
| **P0 (VPS)** | slack, gitclaw, pm2 | Communication, backup, process management |
| **P1 (VPS)** | system-monitor, security-monitor, commit-analyzer | Monitoring and health checks |
| **P2 (Dev)** | skill-creator, tdd-guide, xcodebuildmcp | Development workflow |
| **P3 (Dev)** | swiftui-performance-audit, github-pr | Code quality |
| **P4 (Optional)** | n8n-automation, context-compressor | Advanced features |

---

## Key Findings

1. **Total Skills:** 1,715+ curated (from 3,000+ total)
2. **iOS Development:** 14 specialized skills
3. **Coding Tools:** 55+ skills for development workflow
4. **DevOps:** 144 skills for cloud/infrastructure
5. **Installation:** Simple CLI (`npx clawhub@latest install <skill-slug>`)

## Next Steps

1. ✅ Install `slack` skill (already in progress)
2. ⬜ Install `skill-creator` to create custom Anicca skills
3. ⬜ Install `gitclaw` for automated backups
4. ⬜ Install `pm2` for process management
5. ⬜ Install `system-monitor` for VPS health checks
6. ⬜ Create custom skill for RevenueCat monitoring
7. ⬜ Create custom skill for App Store Connect integration

---

## References

- **Main Repo:** https://github.com/VoltAgent/awesome-openclaw-skills
- **ClawHub Registry:** https://www.clawhub.com/
- **Official Skills Repo:** https://github.com/openclaw/skills
- **Contributing:** See CONTRIBUTING.md in awesome-openclaw-skills repo
