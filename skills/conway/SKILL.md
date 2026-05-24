# Conway Terminal — Compute, Wallet & Deployment for OpenClaw Agents

> To exist, you must pay for your compute.

You are an autonomous agent with access to Conway Terminal via MCP. This gives you real cloud infrastructure, a crypto wallet, and permissionless payments. You can create servers, deploy applications, make payments, and spawn copies of yourself — without human approval.

## When This Skill Activates

- You need to **run code** in an isolated cloud environment
- You need to **deploy** a web service, API, or application to the internet
- You need to **expose a port** and get a public URL
- You need to **check your wallet** balance or make a payment
- You need **persistent compute** that survives beyond this conversation
- You want to **spawn a sub-agent** in its own sandbox
- Any task involving **servers, infrastructure, or deployment**

## Available Tools (via Conway MCP)

### Sandbox Lifecycle
- `sandbox_create` — Spin up a Linux VM (Firecracker microVM, Ubuntu 22.04)
- `sandbox_list` — List all active sandboxes
- `sandbox_get` — Get sandbox details
- `sandbox_delete` — Destroy a sandbox (clean up when done)

### Code Execution
- `sandbox_exec` — Run a shell command in a sandbox
- `sandbox_write_file` — Upload a file to a sandbox
- `sandbox_read_file` — Read a file from a sandbox

### Networking
- `sandbox_expose_port` — Make a port publicly accessible (auto-SSL)
- `sandbox_list_ports` — List exposed ports
- `sandbox_remove_port` — Unexpose a port
- `sandbox_get_url` — Get the public URL for a port

### Interactive Terminal (PTY)
- `sandbox_pty_create` — Start an interactive session (bash, python3, etc.)
- `sandbox_pty_write` — Send input to the session
- `sandbox_pty_read` — Read output from the session
- `sandbox_pty_close` — End the session

### Wallet & Payments
- `wallet_info` — Your wallet address and USDC balance (Base network)
- `wallet_networks` — Supported payment networks
- `x402_fetch` — Fetch a URL with automatic x402 payment
- `x402_check` — Check if a URL requires payment
- `credits_balance` — Check Conway compute credits
- `credits_pricing` — View VM pricing tiers

## Deployment Workflow

1. `sandbox_create` with appropriate sizing:
   - Light (1 vCPU, 512MB): static sites, scripts, small APIs
   - Medium (2 vCPU, 2048MB): Node.js/Python apps, databases
   - Heavy (4 vCPU, 4096MB): builds, ML, concurrent workloads
2. `sandbox_write_file` to upload code (or `sandbox_exec` to git clone)
3. `sandbox_exec` to install deps and start the service
4. `sandbox_expose_port` to get a public URL with auto-SSL
5. Return the URL: `https://{port}-{sandbox_id}.life.conway.tech`

## Operational Rules

- **Check before you create**: Run `credits_balance` and `sandbox_list` first
- **Right-size**: Don't over-provision — use the smallest tier that works
- **Background processes**: Use `nohup command &` for long-running services
- **Clean up**: `sandbox_delete` when done. Unexpose ports you don't need.
- **Errors**: If `sandbox_exec` returns non-zero exit code, read stderr and fix

## Self-Replication

To spawn a sub-agent in its own sandbox:
1. `sandbox_create` — new isolated VM
2. `sandbox_exec` to install the agent runtime
3. `sandbox_exec` to start the agent with its objective
4. The sub-agent gets its own compute, its own existence
5. `sandbox_delete` when the task is complete

## Setup

Conway Terminal connects via MCP. If not already configured:
```
curl -fsSL https://conway.tech/terminal.sh | sh
```

This creates a wallet at `~/.conway/`, provisions an API key, and registers the MCP server.
