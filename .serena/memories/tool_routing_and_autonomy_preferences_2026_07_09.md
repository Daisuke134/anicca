# Tool Routing and Autonomy Preferences (2026-07-09)

User preference:
- Web search: use Firecrawl CLI first (`firecrawl search`, `firecrawl scrape`).
- Documentation / SDK / library search: use Context7 CLI first (`npx ctx7@latest library ...`, `npx ctx7@latest docs ...`).
- Social / platform / community sources such as Reddit, X, YouTube, GitHub, LinkedIn, RSS, etc.: use Agent Reach first (`agent-reach doctor --json`, then route by active backend).
- Work autonomously with no human-in-the-loop by default. Do not ask for permission for routine tool use, edits, verification, deploy checks, or command execution when the environment already permits it.
- Stop only for genuinely irreversible actions outside standing instructions, such as personal fund transfers or unexpected public broadcast/delete/send operations.

Current local check:
- `firecrawl` exists at `/opt/homebrew/bin/firecrawl`.
- `agent-reach` exists at `/Users/anicca/.local/bin/agent-reach`.
- `npx ctx7@latest --help` works.
- `agent-reach doctor --json` works. As of the check, GitHub, Exa/web/RSS, YouTube, Bilibili search API, and V2EX public API are available; Twitter CLI exists but is not authenticated; Reddit backend is not configured and needs OpenCLI or rdt-cli before Reddit-specific research.
