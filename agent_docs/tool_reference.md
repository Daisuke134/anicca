# Tool Reference

## Priority Tools

| Task | Tool | Forbidden |
|------|------|-----------|
| Web/URL | `/opt/homebrew/bin/firecrawl scrape <url> markdown` | WebSearch, WebFetch |
| Code search/edit | Serena MCP (`mcp__serena__*`) | Grep/Read (when Serena works) |
| iOS E2E | Maestro MCP (`mcp__maestro__*`) | CLI (CI/CD only) |
| Apple docs | `mcp__apple-docs__*` | WebFetch |
| RevenueCat | `mcp__revenuecat__*` | — |
| App Store Connect | `mcp__app-store-connect__*` | — |

## Skill Search

| Order | Tool | Command |
|-------|------|---------|
| 1st | find-skills | `npx skills find "<query>"` |
| 2nd | clawhub | `clawhub search "<query>"` (fallback) |

## Bundled Skills

| Skill | Usage |
|-------|-------|
| `/simplify` | Review changed code for quality and efficiency |
| `/batch` | Process multiple similar tasks in sequence |
| `/debug` | Systematic debugging with hypothesis testing |

## Fastlane Lanes

| Lane | Command |
|------|---------|
| test | `fastlane test` |
| build_for_device | `fastlane build_for_device` |
| build_for_simulator | `fastlane build_for_simulator` |
| build | `fastlane build` |
| full_release | `fastlane full_release` |
| set_version | `fastlane set_version version:X.Y.Z` |

## CLI Flags

| Flag | Purpose |
|------|---------|
| `--model` | Override model (e.g., `claude-opus-4-6`) |
| `--allowedTools` | Restrict tool access |
| `--max-turns` | Limit conversation turns |
| `--verbose` | Debug output |
| `--resume` | Continue previous session |

## Environment Variables

| Var | Purpose |
|-----|---------|
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | Max output tokens |
| `ANTHROPIC_API_KEY` | API key |
| `DISABLE_PROMPT_CACHING` | Disable caching |
