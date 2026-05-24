
#compdef openclaw

_openclaw_root_completion() {
  local -a commands
  local -a options
  
  _arguments -C \
    "(--version -V)"{--version,-V}"[output the version number]" \
    "--container[Run the CLI inside a running Podman/Docker container named <name> (default: env OPENCLAW_CONTAINER)]" \
    "--dev[Dev profile: isolate state under ~/.openclaw-dev, default gateway port 19001, and shift derived ports (browser/canvas)]" \
    "--profile[Use a named profile (isolates OPENCLAW_STATE_DIR/OPENCLAW_CONFIG_PATH under ~/.openclaw-<name>)]" \
    "--log-level[Global log level override for file + console (silent|fatal|error|warn|info|debug|trace)]" \
    "--no-color[Disable ANSI colors]" \
    "1: :_values 'command' 'mcp[Manage embedded Pi MCP servers]' 'completion[Generate shell completion script]' 'setup[Initialize ~/.openclaw/openclaw.json and the agent workspace]' 'onboard[Interactive onboarding for the gateway, workspace, and skills]' 'configure[Interactive configuration for credentials, channels, gateway, and agent defaults]' 'config[Non-interactive config helpers (get/set/unset/file/validate). Run without subcommand for guided setup.]' 'backup[Create and verify local backup archives for OpenClaw state]' 'doctor[Health checks + quick fixes for the gateway and channels]' 'dashboard[Open the Control UI with your current token]' 'reset[Reset local config/state (keeps the CLI installed)]' 'uninstall[Uninstall the gateway service + local data (CLI remains)]' 'message[Send, read, and manage messages and channel actions]' 'memory[Search, inspect, and reindex memory files]' 'agent[Run an agent turn via the Gateway (use --local for embedded)]' 'agents[Manage isolated agents (workspaces + auth + routing)]' 'status[Show channel health and recent session recipients]' 'health[Fetch health from the running gateway]' 'sessions[List stored conversation sessions]' 'browser[Manage OpenClaw'\''s dedicated browser (Chrome/Chromium)]' 'acp[Run an ACP bridge backed by the Gateway]' 'gateway[Run, inspect, and query the WebSocket Gateway]' 'daemon[Manage the Gateway service (launchd/systemd/schtasks)]' 'logs[Tail gateway file logs via RPC]' 'system[System tools (events, heartbeat, presence)]' 'models[Model discovery, scanning, and configuration]' 'approvals[Manage exec approvals (gateway or node host)]' 'nodes[Manage gateway-owned nodes (pairing, status, invoke, and media)]' 'devices[Device pairing and auth tokens]' 'node[Run and manage the headless node host service]' 'sandbox[Manage sandbox containers (Docker-based agent isolation)]' 'tui[Open a terminal UI connected to the Gateway]' 'cron[Manage cron jobs (via Gateway)]' 'dns[DNS helpers for wide-area discovery (Tailscale + CoreDNS)]' 'docs[Search the live OpenClaw docs]' 'hooks[Manage internal agent hooks]' 'webhooks[Webhook helpers and integrations]' 'qr[Generate an iOS pairing QR code and setup code]' 'clawbot[Legacy clawbot command aliases]' 'pairing[Secure DM pairing (approve inbound requests)]' 'plugins[Manage OpenClaw plugins and extensions]' 'channels[Manage connected chat channels and accounts]' 'directory[Lookup contact and group IDs (self, peers, groups) for supported chat channels]' 'security[Audit local config and state for common security foot-guns]' 'secrets[Secrets runtime controls]' 'skills[List and inspect available skills]' 'update[Update OpenClaw and inspect update channel status]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (mcp) _openclaw_mcp ;;
        (completion) _openclaw_completion ;;
        (setup) _openclaw_setup ;;
        (onboard) _openclaw_onboard ;;
        (configure) _openclaw_configure ;;
        (config) _openclaw_config ;;
        (backup) _openclaw_backup ;;
        (doctor) _openclaw_doctor ;;
        (dashboard) _openclaw_dashboard ;;
        (reset) _openclaw_reset ;;
        (uninstall) _openclaw_uninstall ;;
        (message) _openclaw_message ;;
        (memory) _openclaw_memory ;;
        (agent) _openclaw_agent ;;
        (agents) _openclaw_agents ;;
        (status) _openclaw_status ;;
        (health) _openclaw_health ;;
        (sessions) _openclaw_sessions ;;
        (browser) _openclaw_browser ;;
        (acp) _openclaw_acp ;;
        (gateway) _openclaw_gateway ;;
        (daemon) _openclaw_daemon ;;
        (logs) _openclaw_logs ;;
        (system) _openclaw_system ;;
        (models) _openclaw_models ;;
        (approvals) _openclaw_approvals ;;
        (nodes) _openclaw_nodes ;;
        (devices) _openclaw_devices ;;
        (node) _openclaw_node ;;
        (sandbox) _openclaw_sandbox ;;
        (tui) _openclaw_tui ;;
        (cron) _openclaw_cron ;;
        (dns) _openclaw_dns ;;
        (docs) _openclaw_docs ;;
        (hooks) _openclaw_hooks ;;
        (webhooks) _openclaw_webhooks ;;
        (qr) _openclaw_qr ;;
        (clawbot) _openclaw_clawbot ;;
        (pairing) _openclaw_pairing ;;
        (plugins) _openclaw_plugins ;;
        (channels) _openclaw_channels ;;
        (directory) _openclaw_directory ;;
        (security) _openclaw_security ;;
        (secrets) _openclaw_secrets ;;
        (skills) _openclaw_skills ;;
        (update) _openclaw_update ;;
      esac
      ;;
  esac
}


_openclaw_mcp() {
  _arguments -C \
    
}

_openclaw_completion() {
  _arguments -C \
    "(--shell -s)"{--shell,-s}"[Shell to generate completion for (default: zsh)]" \
    "(--install -i)"{--install,-i}"[Install completion script to shell profile]" \
    "--write-state[Write completion scripts to $OPENCLAW_STATE_DIR/completions (no stdout)]" \
    "(--yes -y)"{--yes,-y}"[Skip confirmation (non-interactive)]"
}

_openclaw_setup() {
  _arguments -C \
    "--workspace[Agent workspace directory (default: ~/.openclaw/workspace; stored as agents.defaults.workspace)]" \
    "--wizard[Run interactive onboarding]" \
    "--non-interactive[Run onboarding without prompts]" \
    "--mode[Onboard mode: local|remote]" \
    "--remote-url[Remote Gateway WebSocket URL]" \
    "--remote-token[Remote Gateway token (optional)]"
}

_openclaw_onboard() {
  _arguments -C \
    "--workspace[Agent workspace directory (default: ~/.openclaw/workspace)]" \
    "--reset[Reset config + credentials + sessions before running onboard (workspace only with --reset-scope full)]" \
    "--reset-scope[Reset scope: config|config+creds+sessions|full]" \
    "--non-interactive[Run without prompts]" \
    "--accept-risk[Acknowledge that agents are powerful and full system access is risky (required for --non-interactive)]" \
    "--flow[Onboard flow: quickstart|advanced|manual]" \
    "--mode[Onboard mode: local|remote]" \
    "--auth-choice[Auth: chutes|litellm-api-key|custom-api-key|skip|setup-token|oauth|claude-cli|codex-cli|token|apiKey|byteplus-api-key|chutes-api-key|cloudflare-ai-gateway-api-key|copilot-proxy|deepseek-api-key|github-copilot|gemini-api-key|google-gemini-cli|huggingface-api-key|kilocode-api-key|kimi-code-api-key|minimax-global-oauth|minimax-global-api|minimax-cn-oauth|minimax-cn-api|mistral-api-key|modelstudio-standard-api-key-cn|modelstudio-standard-api-key|modelstudio-api-key-cn|modelstudio-api-key|moonshot-api-key|moonshot-api-key-cn|ollama|openai-codex|openai-api-key|opencode-zen|opencode-go|openrouter-api-key|qianfan-api-key|sglang|synthetic-api-key|together-api-key|venice-api-key|ai-gateway-api-key|vllm|volcengine-api-key|xai-api-key|xiaomi-api-key|zai-api-key|zai-coding-global|zai-coding-cn|zai-global|zai-cn|qwen-portal]" \
    "--token-provider[Token provider id (non-interactive; used with --auth-choice token)]" \
    "--token[Token value (non-interactive; used with --auth-choice token)]" \
    "--token-profile-id[Auth profile id (non-interactive; default: <provider>:manual)]" \
    "--token-expires-in[Optional token expiry duration (e.g. 365d, 12h)]" \
    "--secret-input-mode[API key persistence mode: plaintext|ref (default: plaintext)]" \
    "--cloudflare-ai-gateway-account-id[Cloudflare Account ID]" \
    "--cloudflare-ai-gateway-gateway-id[Cloudflare AI Gateway ID]" \
    "--litellm-api-key[LiteLLM API key]" \
    "--anthropic-api-key[Anthropic API key]" \
    "--byteplus-api-key[BytePlus API key]" \
    "--chutes-api-key[Chutes API key]" \
    "--cloudflare-ai-gateway-api-key[Cloudflare AI Gateway API key]" \
    "--deepseek-api-key[DeepSeek API key]" \
    "--fal-api-key[fal API key]" \
    "--gemini-api-key[Gemini API key]" \
    "--huggingface-api-key[Hugging Face API key (HF token)]" \
    "--kilocode-api-key[Kilo Gateway API key]" \
    "--kimi-code-api-key[Kimi Code API key]" \
    "--minimax-api-key[MiniMax API key]" \
    "--mistral-api-key[Mistral API key]" \
    "--modelstudio-standard-api-key-cn[Alibaba Cloud Model Studio Standard API key (China)]" \
    "--modelstudio-standard-api-key[Alibaba Cloud Model Studio Standard API key (Global/Intl)]" \
    "--modelstudio-api-key-cn[Alibaba Cloud Model Studio Coding Plan API key (China)]" \
    "--modelstudio-api-key[Alibaba Cloud Model Studio Coding Plan API key (Global/Intl)]" \
    "--moonshot-api-key[Moonshot API key]" \
    "--openai-api-key[OpenAI API key]" \
    "--opencode-zen-api-key[OpenCode API key (Zen catalog)]" \
    "--opencode-go-api-key[OpenCode API key (Go catalog)]" \
    "--openrouter-api-key[OpenRouter API key]" \
    "--qianfan-api-key[QIANFAN API key]" \
    "--synthetic-api-key[Synthetic API key]" \
    "--together-api-key[Together AI API key]" \
    "--venice-api-key[Venice API key]" \
    "--ai-gateway-api-key[Vercel AI Gateway API key]" \
    "--volcengine-api-key[Volcano Engine API key]" \
    "--xai-api-key[xAI API key]" \
    "--xiaomi-api-key[Xiaomi API key]" \
    "--zai-api-key[Z.AI API key]" \
    "--custom-base-url[Custom provider base URL]" \
    "--custom-api-key[Custom provider API key (optional)]" \
    "--custom-model-id[Custom provider model ID]" \
    "--custom-provider-id[Custom provider ID (optional; auto-derived by default)]" \
    "--custom-compatibility[Custom provider API compatibility: openai|anthropic (default: openai)]" \
    "--gateway-port[Gateway port]" \
    "--gateway-bind[Gateway bind: loopback|tailnet|lan|auto|custom]" \
    "--gateway-auth[Gateway auth: token|password]" \
    "--gateway-token[Gateway token (token auth)]" \
    "--gateway-token-ref-env[Gateway token SecretRef env var name (token auth; e.g. OPENCLAW_GATEWAY_TOKEN)]" \
    "--gateway-password[Gateway password (password auth)]" \
    "--remote-url[Remote Gateway WebSocket URL]" \
    "--remote-token[Remote Gateway token (optional)]" \
    "--tailscale[Tailscale: off|serve|funnel]" \
    "--tailscale-reset-on-exit[Reset tailscale serve/funnel on exit]" \
    "--install-daemon[Install gateway service]" \
    "--no-install-daemon[Skip gateway service install]" \
    "--skip-daemon[Skip gateway service install]" \
    "--daemon-runtime[Daemon runtime: node|bun]" \
    "--skip-channels[Skip channel setup]" \
    "--skip-skills[Skip skills setup]" \
    "--skip-search[Skip search provider setup]" \
    "--skip-health[Skip health check]" \
    "--skip-ui[Skip Control UI/TUI prompts]" \
    "--node-manager[Node manager for skills: npm|pnpm|bun]" \
    "--json[Output JSON summary]"
}

_openclaw_configure() {
  _arguments -C \
    "--section[Configuration sections (repeatable). Options: workspace, model, web, gateway, daemon, channels, skills, health]"
}

_openclaw_config_get() {
  _arguments -C \
    "--json[Output JSON]"
}

_openclaw_config_set() {
  _arguments -C \
    "--strict-json[Strict JSON parsing (error instead of raw string fallback)]" \
    "--json[Legacy alias for --strict-json]" \
    "--dry-run[Validate changes without writing openclaw.json (checks run in builder/json/batch modes; exec SecretRefs are skipped unless --allow-exec is set)]" \
    "--allow-exec[Dry-run only: allow exec SecretRef resolvability checks (may execute provider commands)]" \
    "--ref-provider[SecretRef builder: provider alias]" \
    "--ref-source[SecretRef builder: source (env|file|exec)]" \
    "--ref-id[SecretRef builder: ref id]" \
    "--provider-source[Provider builder: source (env|file|exec)]" \
    "--provider-allowlist[Provider builder (env): allowlist entry (repeatable)]" \
    "--provider-path[Provider builder (file): path]" \
    "--provider-mode[Provider builder (file): mode (singleValue|json)]" \
    "--provider-timeout-ms[Provider builder (file|exec): timeout ms]" \
    "--provider-max-bytes[Provider builder (file): max bytes]" \
    "--provider-command[Provider builder (exec): absolute command path]" \
    "--provider-arg[Provider builder (exec): command arg (repeatable)]" \
    "--provider-no-output-timeout-ms[Provider builder (exec): no-output timeout ms]" \
    "--provider-max-output-bytes[Provider builder (exec): max output bytes]" \
    "--provider-json-only[Provider builder (exec): require JSON output]" \
    "--provider-env[Provider builder (exec): env assignment (repeatable)]" \
    "--provider-pass-env[Provider builder (exec): pass host env var (repeatable)]" \
    "--provider-trusted-dir[Provider builder (exec): trusted directory (repeatable)]" \
    "--provider-allow-insecure-path[Provider builder (exec): bypass strict path permission checks]" \
    "--provider-allow-symlink-command[Provider builder (exec): allow command symlink path]" \
    "--batch-json[Batch mode: JSON array of set operations]" \
    "--batch-file[Batch mode: read JSON array of set operations from file]"
}

_openclaw_config_unset() {
  _arguments -C \
    
}

_openclaw_config_file() {
  _arguments -C \
    
}

_openclaw_config_validate() {
  _arguments -C \
    "--json[Output validation result as JSON]"
}

_openclaw_config() {
  local -a commands
  local -a options
  
  _arguments -C \
    "--section[Configuration sections for guided setup (repeatable). Use with no subcommand.]" \
    "1: :_values 'command' 'get[Get a config value by dot path]' 'set[Set config values by path (value mode, ref/provider builder mode, or batch JSON mode).
Examples:
openclaw config set gateway.port 19001 --strict-json
openclaw config set channels.discord.token --ref-provider default --ref-source env --ref-id DISCORD_BOT_TOKEN
openclaw config set secrets.providers.vault --provider-source file --provider-path /etc/openclaw/secrets.json --provider-mode json
openclaw config set --batch-file ./config-set.batch.json --dry-run]' 'unset[Remove a config value by dot path]' 'file[Print the active config file path]' 'validate[Validate the current config against the schema without starting the gateway]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (get) _openclaw_config_get ;;
        (set) _openclaw_config_set ;;
        (unset) _openclaw_config_unset ;;
        (file) _openclaw_config_file ;;
        (validate) _openclaw_config_validate ;;
      esac
      ;;
  esac
}

_openclaw_backup_create() {
  _arguments -C \
    "--output[Archive path or destination directory]" \
    "--json[Output JSON]" \
    "--dry-run[Print the backup plan without writing the archive]" \
    "--verify[Verify the archive after writing it]" \
    "--only-config[Back up only the active JSON config file]" \
    "--no-include-workspace[Exclude workspace directories from the backup]"
}

_openclaw_backup_verify() {
  _arguments -C \
    "--json[Output JSON]"
}

_openclaw_backup() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'create[Write a backup archive for config, credentials, sessions, and workspaces]' 'verify[Validate a backup archive and its embedded manifest]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (create) _openclaw_backup_create ;;
        (verify) _openclaw_backup_verify ;;
      esac
      ;;
  esac
}

_openclaw_doctor() {
  _arguments -C \
    "--no-workspace-suggestions[Disable workspace memory system suggestions]" \
    "--yes[Accept defaults without prompting]" \
    "--repair[Apply recommended repairs without prompting]" \
    "--fix[Apply recommended repairs (alias for --repair)]" \
    "--force[Apply aggressive repairs (overwrites custom service config)]" \
    "--non-interactive[Run without prompts (safe migrations only)]" \
    "--generate-gateway-token[Generate and configure a gateway token]" \
    "--deep[Scan system services for extra gateway installs]"
}

_openclaw_dashboard() {
  _arguments -C \
    "--no-open[Print URL but do not launch a browser]"
}

_openclaw_reset() {
  _arguments -C \
    "--scope[config|config+creds+sessions|full (default: interactive prompt)]" \
    "--yes[Skip confirmation prompts]" \
    "--non-interactive[Disable prompts (requires --scope + --yes)]" \
    "--dry-run[Print actions without removing files]"
}

_openclaw_uninstall() {
  _arguments -C \
    "--service[Remove the gateway service]" \
    "--state[Remove state + config]" \
    "--workspace[Remove workspace dirs]" \
    "--app[Remove the macOS app]" \
    "--all[Remove service + state + workspace + app]" \
    "--yes[Skip confirmation prompts]" \
    "--non-interactive[Disable prompts (requires --yes)]" \
    "--dry-run[Print actions without removing files]"
}

_openclaw_message_send() {
  _arguments -C \
    "(--message -m)"{--message,-m}"[Message body (required unless --media is set)]" \
    "(--target -t)"{--target,-t}"[Recipient/channel: E.164 for WhatsApp/Signal, Telegram chat id/@username, Discord/Slack channel/user, or iMessage handle/chat_id]" \
    "--media[Attach media (image/audio/video/document). Accepts local paths or URLs.]" \
    "--interactive[Shared interactive payload as JSON (buttons/selects rendered natively by supported channels)]" \
    "--buttons[Telegram inline keyboard buttons as JSON (array of button rows)]" \
    "--components[Discord components payload as JSON]" \
    "--card[Adaptive Card JSON object (when supported by the channel)]" \
    "--reply-to[Reply-to message id]" \
    "--thread-id[Thread id (Telegram forum thread)]" \
    "--gif-playback[Treat video media as GIF playback (WhatsApp only).]" \
    "--force-document[Send media as document to avoid Telegram compression (Telegram only). Applies to images and GIFs.]" \
    "--silent[Send message silently without notification (Telegram + Discord)]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]"
}

_openclaw_message_broadcast() {
  _arguments -C \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--targets[Recipient/channel targets (same format as --target); accepts ids or names when the directory is available.]" \
    "--message[Message to send]" \
    "--media[Media URL]"
}

_openclaw_message_poll() {
  _arguments -C \
    "(--target -t)"{--target,-t}"[Recipient/channel: E.164 for WhatsApp/Signal, Telegram chat id/@username, Discord/Slack channel/user, or iMessage handle/chat_id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--poll-question[Poll question]" \
    "--poll-option[Poll option (repeat 2-12 times)]" \
    "--poll-multi[Allow multiple selections]" \
    "--poll-duration-hours[Poll duration in hours (Discord)]" \
    "--poll-duration-seconds[Poll duration in seconds (Telegram; 5-600)]" \
    "--poll-anonymous[Send an anonymous poll (Telegram)]" \
    "--poll-public[Send a non-anonymous poll (Telegram)]" \
    "(--message -m)"{--message,-m}"[Optional message body]" \
    "--silent[Send poll silently without notification (Telegram + Discord where supported)]" \
    "--thread-id[Thread id (Telegram forum topic / Slack thread ts)]"
}

_openclaw_message_react() {
  _arguments -C \
    "(--target -t)"{--target,-t}"[Recipient/channel: E.164 for WhatsApp/Signal, Telegram chat id/@username, Discord/Slack channel/user, or iMessage handle/chat_id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--message-id[Message id]" \
    "--emoji[Emoji for reactions]" \
    "--remove[Remove reaction]" \
    "--participant[WhatsApp reaction participant]" \
    "--from-me[WhatsApp reaction fromMe]" \
    "--target-author[Signal reaction target author (uuid or phone)]" \
    "--target-author-uuid[Signal reaction target author uuid]"
}

_openclaw_message_reactions() {
  _arguments -C \
    "(--target -t)"{--target,-t}"[Recipient/channel: E.164 for WhatsApp/Signal, Telegram chat id/@username, Discord/Slack channel/user, or iMessage handle/chat_id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--message-id[Message id]" \
    "--limit[Result limit]"
}

_openclaw_message_read() {
  _arguments -C \
    "(--target -t)"{--target,-t}"[Recipient/channel: E.164 for WhatsApp/Signal, Telegram chat id/@username, Discord/Slack channel/user, or iMessage handle/chat_id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--limit[Result limit]" \
    "--before[Read/search before id]" \
    "--after[Read/search after id]" \
    "--around[Read around id]" \
    "--include-thread[Include thread replies (Discord)]"
}

_openclaw_message_edit() {
  _arguments -C \
    "--message-id[Message id]" \
    "(--message -m)"{--message,-m}"[Message body]" \
    "(--target -t)"{--target,-t}"[Recipient/channel: E.164 for WhatsApp/Signal, Telegram chat id/@username, Discord/Slack channel/user, or iMessage handle/chat_id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--thread-id[Thread id (Telegram forum thread)]"
}

_openclaw_message_delete() {
  _arguments -C \
    "--message-id[Message id]" \
    "(--target -t)"{--target,-t}"[Recipient/channel: E.164 for WhatsApp/Signal, Telegram chat id/@username, Discord/Slack channel/user, or iMessage handle/chat_id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]"
}

_openclaw_message_pin() {
  _arguments -C \
    "(--target -t)"{--target,-t}"[Recipient/channel: E.164 for WhatsApp/Signal, Telegram chat id/@username, Discord/Slack channel/user, or iMessage handle/chat_id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--message-id[Message id]"
}

_openclaw_message_unpin() {
  _arguments -C \
    "(--target -t)"{--target,-t}"[Recipient/channel: E.164 for WhatsApp/Signal, Telegram chat id/@username, Discord/Slack channel/user, or iMessage handle/chat_id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--message-id[Message id]"
}

_openclaw_message_pins() {
  _arguments -C \
    "(--target -t)"{--target,-t}"[Recipient/channel: E.164 for WhatsApp/Signal, Telegram chat id/@username, Discord/Slack channel/user, or iMessage handle/chat_id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--limit[Result limit]"
}

_openclaw_message_permissions() {
  _arguments -C \
    "(--target -t)"{--target,-t}"[Recipient/channel: E.164 for WhatsApp/Signal, Telegram chat id/@username, Discord/Slack channel/user, or iMessage handle/chat_id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]"
}

_openclaw_message_search() {
  _arguments -C \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--guild-id[Guild id]" \
    "--query[Search query]" \
    "--channel-id[Channel id]" \
    "--channel-ids[Channel id (repeat)]" \
    "--author-id[Author id]" \
    "--author-ids[Author id (repeat)]" \
    "--limit[Result limit]"
}

_openclaw_message_thread_create() {
  _arguments -C \
    "--thread-name[Thread name]" \
    "(--target -t)"{--target,-t}"[Recipient/channel: E.164 for WhatsApp/Signal, Telegram chat id/@username, Discord/Slack channel/user, or iMessage handle/chat_id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--message-id[Message id (optional)]" \
    "(--message -m)"{--message,-m}"[Initial thread message text]" \
    "--auto-archive-min[Thread auto-archive minutes]"
}

_openclaw_message_thread_list() {
  _arguments -C \
    "--guild-id[Guild id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--channel-id[Channel id]" \
    "--include-archived[Include archived threads]" \
    "--before[Read/search before id]" \
    "--limit[Result limit]"
}

_openclaw_message_thread_reply() {
  _arguments -C \
    "(--message -m)"{--message,-m}"[Message body]" \
    "(--target -t)"{--target,-t}"[Recipient/channel: E.164 for WhatsApp/Signal, Telegram chat id/@username, Discord/Slack channel/user, or iMessage handle/chat_id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--media[Attach media (image/audio/video/document). Accepts local paths or URLs.]" \
    "--reply-to[Reply-to message id]"
}

_openclaw_message_thread() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'create[Create a thread]' 'list[List threads]' 'reply[Reply in a thread]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (create) _openclaw_message_thread_create ;;
        (list) _openclaw_message_thread_list ;;
        (reply) _openclaw_message_thread_reply ;;
      esac
      ;;
  esac
}

_openclaw_message_emoji_list() {
  _arguments -C \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--guild-id[Guild id (Discord)]"
}

_openclaw_message_emoji_upload() {
  _arguments -C \
    "--guild-id[Guild id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--emoji-name[Emoji name]" \
    "--media[Emoji media (path or URL)]" \
    "--role-ids[Role id (repeat)]"
}

_openclaw_message_emoji() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'list[List emojis]' 'upload[Upload an emoji]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (list) _openclaw_message_emoji_list ;;
        (upload) _openclaw_message_emoji_upload ;;
      esac
      ;;
  esac
}

_openclaw_message_sticker_send() {
  _arguments -C \
    "(--target -t)"{--target,-t}"[Recipient/channel: E.164 for WhatsApp/Signal, Telegram chat id/@username, Discord/Slack channel/user, or iMessage handle/chat_id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--sticker-id[Sticker id (repeat)]" \
    "(--message -m)"{--message,-m}"[Optional message body]"
}

_openclaw_message_sticker_upload() {
  _arguments -C \
    "--guild-id[Guild id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--sticker-name[Sticker name]" \
    "--sticker-desc[Sticker description]" \
    "--sticker-tags[Sticker tags]" \
    "--media[Sticker media (path or URL)]"
}

_openclaw_message_sticker() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'send[Send stickers]' 'upload[Upload a sticker]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (send) _openclaw_message_sticker_send ;;
        (upload) _openclaw_message_sticker_upload ;;
      esac
      ;;
  esac
}

_openclaw_message_role_info() {
  _arguments -C \
    "--guild-id[Guild id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]"
}

_openclaw_message_role_add() {
  _arguments -C \
    "--guild-id[Guild id]" \
    "--user-id[User id]" \
    "--role-id[Role id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]"
}

_openclaw_message_role_remove() {
  _arguments -C \
    "--guild-id[Guild id]" \
    "--user-id[User id]" \
    "--role-id[Role id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]"
}

_openclaw_message_role() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'info[List roles]' 'add[Add role to a member]' 'remove[Remove role from a member]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (info) _openclaw_message_role_info ;;
        (add) _openclaw_message_role_add ;;
        (remove) _openclaw_message_role_remove ;;
      esac
      ;;
  esac
}

_openclaw_message_channel_info() {
  _arguments -C \
    "(--target -t)"{--target,-t}"[Recipient/channel: E.164 for WhatsApp/Signal, Telegram chat id/@username, Discord/Slack channel/user, or iMessage handle/chat_id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]"
}

_openclaw_message_channel_list() {
  _arguments -C \
    "--guild-id[Guild id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]"
}

_openclaw_message_channel() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'info[Fetch channel info]' 'list[List channels]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (info) _openclaw_message_channel_info ;;
        (list) _openclaw_message_channel_list ;;
      esac
      ;;
  esac
}

_openclaw_message_member_info() {
  _arguments -C \
    "--user-id[User id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--guild-id[Guild id (Discord)]"
}

_openclaw_message_member() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'info[Fetch member info]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (info) _openclaw_message_member_info ;;
      esac
      ;;
  esac
}

_openclaw_message_voice_status() {
  _arguments -C \
    "--guild-id[Guild id]" \
    "--user-id[User id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]"
}

_openclaw_message_voice() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'status[Fetch voice status]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (status) _openclaw_message_voice_status ;;
      esac
      ;;
  esac
}

_openclaw_message_event_list() {
  _arguments -C \
    "--guild-id[Guild id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]"
}

_openclaw_message_event_create() {
  _arguments -C \
    "--guild-id[Guild id]" \
    "--event-name[Event name]" \
    "--start-time[Event start time]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--end-time[Event end time]" \
    "--desc[Event description]" \
    "--channel-id[Channel id]" \
    "--location[Event location]" \
    "--event-type[Event type]"
}

_openclaw_message_event() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'list[List scheduled events]' 'create[Create a scheduled event]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (list) _openclaw_message_event_list ;;
        (create) _openclaw_message_event_create ;;
      esac
      ;;
  esac
}

_openclaw_message_timeout() {
  _arguments -C \
    "--guild-id[Guild id]" \
    "--user-id[User id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--duration-min[Timeout duration minutes]" \
    "--until[Timeout until]" \
    "--reason[Moderation reason]"
}

_openclaw_message_kick() {
  _arguments -C \
    "--guild-id[Guild id]" \
    "--user-id[User id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--reason[Moderation reason]"
}

_openclaw_message_ban() {
  _arguments -C \
    "--guild-id[Guild id]" \
    "--user-id[User id]" \
    "--channel[Channel: telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line]" \
    "--account[Channel account id (accountId)]" \
    "--json[Output result as JSON]" \
    "--dry-run[Print payload and skip sending]" \
    "--verbose[Verbose logging]" \
    "--reason[Moderation reason]" \
    "--delete-days[Ban delete message days]"
}

_openclaw_message() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'send[Send a message]' 'broadcast[Broadcast a message to multiple targets]' 'poll[Send a poll]' 'react[Add or remove a reaction]' 'reactions[List reactions on a message]' 'read[Read recent messages]' 'edit[Edit a message]' 'delete[Delete a message]' 'pin[Pin a message]' 'unpin[Unpin a message]' 'pins[List pinned messages]' 'permissions[Fetch channel permissions]' 'search[Search Discord messages]' 'thread[Thread actions]' 'emoji[Emoji actions]' 'sticker[Sticker actions]' 'role[Role actions]' 'channel[Channel actions]' 'member[Member actions]' 'voice[Voice actions]' 'event[Event actions]' 'timeout[Timeout a member]' 'kick[Kick a member]' 'ban[Ban a member]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (send) _openclaw_message_send ;;
        (broadcast) _openclaw_message_broadcast ;;
        (poll) _openclaw_message_poll ;;
        (react) _openclaw_message_react ;;
        (reactions) _openclaw_message_reactions ;;
        (read) _openclaw_message_read ;;
        (edit) _openclaw_message_edit ;;
        (delete) _openclaw_message_delete ;;
        (pin) _openclaw_message_pin ;;
        (unpin) _openclaw_message_unpin ;;
        (pins) _openclaw_message_pins ;;
        (permissions) _openclaw_message_permissions ;;
        (search) _openclaw_message_search ;;
        (thread) _openclaw_message_thread ;;
        (emoji) _openclaw_message_emoji ;;
        (sticker) _openclaw_message_sticker ;;
        (role) _openclaw_message_role ;;
        (channel) _openclaw_message_channel ;;
        (member) _openclaw_message_member ;;
        (voice) _openclaw_message_voice ;;
        (event) _openclaw_message_event ;;
        (timeout) _openclaw_message_timeout ;;
        (kick) _openclaw_message_kick ;;
        (ban) _openclaw_message_ban ;;
      esac
      ;;
  esac
}

_openclaw_memory_status() {
  _arguments -C \
    "--agent[Agent id (default: default agent)]" \
    "--json[Print JSON]" \
    "--deep[Probe embedding provider availability]" \
    "--index[Reindex if dirty (implies --deep)]" \
    "--verbose[Verbose logging]"
}

_openclaw_memory_index() {
  _arguments -C \
    "--agent[Agent id (default: default agent)]" \
    "--force[Force full reindex]" \
    "--verbose[Verbose logging]"
}

_openclaw_memory_search() {
  _arguments -C \
    "--query[Search query (alternative to positional argument)]" \
    "--agent[Agent id (default: default agent)]" \
    "--max-results[Max results]" \
    "--min-score[Minimum score]" \
    "--json[Print JSON]"
}

_openclaw_memory() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'status[Show memory search index status]' 'index[Reindex memory files]' 'search[Search memory files]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (status) _openclaw_memory_status ;;
        (index) _openclaw_memory_index ;;
        (search) _openclaw_memory_search ;;
      esac
      ;;
  esac
}

_openclaw_agent() {
  _arguments -C \
    "(--message -m)"{--message,-m}"[Message body for the agent]" \
    "(--to -t)"{--to,-t}"[Recipient number in E.164 used to derive the session key]" \
    "--session-id[Use an explicit session id]" \
    "--agent[Agent id (overrides routing bindings)]" \
    "--thinking[Thinking level: off | minimal | low | medium | high | xhigh]" \
    "--verbose[Persist agent verbose level for the session]" \
    "--channel[Delivery channel: last|telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line (omit to use the main session channel)]" \
    "--reply-to[Delivery target override (separate from session routing)]" \
    "--reply-channel[Delivery channel override (separate from routing)]" \
    "--reply-account[Delivery account id override]" \
    "--local[Run the embedded agent locally (requires model provider API keys in your shell)]" \
    "--deliver[Send the agent'\''s reply back to the selected channel]" \
    "--json[Output result as JSON]" \
    "--timeout[Override agent command timeout (seconds, default 600 or config value)]"
}

_openclaw_agents_list() {
  _arguments -C \
    "--json[Output JSON instead of text]" \
    "--bindings[Include routing bindings]"
}

_openclaw_agents_bindings() {
  _arguments -C \
    "--agent[Filter by agent id]" \
    "--json[Output JSON instead of text]"
}

_openclaw_agents_bind() {
  _arguments -C \
    "--agent[Agent id (defaults to current default agent)]" \
    "--bind[Binding to add (repeatable). If omitted, accountId is resolved by channel defaults/hooks.]" \
    "--json[Output JSON summary]"
}

_openclaw_agents_unbind() {
  _arguments -C \
    "--agent[Agent id (defaults to current default agent)]" \
    "--bind[Binding to remove (repeatable)]" \
    "--all[Remove all bindings for this agent]" \
    "--json[Output JSON summary]"
}

_openclaw_agents_add() {
  _arguments -C \
    "--workspace[Workspace directory for the new agent]" \
    "--model[Model id for this agent]" \
    "--agent-dir[Agent state directory for this agent]" \
    "--bind[Route channel binding (repeatable)]" \
    "--non-interactive[Disable prompts; requires --workspace]" \
    "--json[Output JSON summary]"
}

_openclaw_agents_set_identity() {
  _arguments -C \
    "--agent[Agent id to update]" \
    "--workspace[Workspace directory used to locate the agent + IDENTITY.md]" \
    "--identity-file[Explicit IDENTITY.md path to read]" \
    "--from-identity[Read values from IDENTITY.md]" \
    "--name[Identity name]" \
    "--theme[Identity theme]" \
    "--emoji[Identity emoji]" \
    "--avatar[Identity avatar (workspace path, http(s) URL, or data URI)]" \
    "--json[Output JSON summary]"
}

_openclaw_agents_delete() {
  _arguments -C \
    "--force[Skip confirmation]" \
    "--json[Output JSON summary]"
}

_openclaw_agents() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'list[List configured agents]' 'bindings[List routing bindings]' 'bind[Add routing bindings for an agent]' 'unbind[Remove routing bindings for an agent]' 'add[Add a new isolated agent]' 'set-identity[Update an agent identity (name/theme/emoji/avatar)]' 'delete[Delete an agent and prune workspace/state]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (list) _openclaw_agents_list ;;
        (bindings) _openclaw_agents_bindings ;;
        (bind) _openclaw_agents_bind ;;
        (unbind) _openclaw_agents_unbind ;;
        (add) _openclaw_agents_add ;;
        (set-identity) _openclaw_agents_set_identity ;;
        (delete) _openclaw_agents_delete ;;
      esac
      ;;
  esac
}

_openclaw_status() {
  _arguments -C \
    "--json[Output JSON instead of text]" \
    "--all[Full diagnosis (read-only, pasteable)]" \
    "--usage[Show model provider usage/quota snapshots]" \
    "--deep[Probe channels (WhatsApp Web + Telegram + Discord + Slack + Signal)]" \
    "--timeout[Probe timeout in milliseconds]" \
    "--verbose[Verbose logging]" \
    "--debug[Alias for --verbose]"
}

_openclaw_health() {
  _arguments -C \
    "--json[Output JSON instead of text]" \
    "--timeout[Connection timeout in milliseconds]" \
    "--verbose[Verbose logging]" \
    "--debug[Alias for --verbose]"
}

_openclaw_sessions_cleanup() {
  _arguments -C \
    "--store[Path to session store (default: resolved from config)]" \
    "--agent[Agent id to maintain (default: configured default agent)]" \
    "--all-agents[Run maintenance across all configured agents]" \
    "--dry-run[Preview maintenance actions without writing]" \
    "--enforce[Apply maintenance even when configured mode is warn]" \
    "--fix-missing[Remove store entries whose transcript files are missing (bypasses age/count retention)]" \
    "--active-key[Protect this session key from budget-eviction]" \
    "--json[Output JSON]"
}

_openclaw_sessions() {
  local -a commands
  local -a options
  
  _arguments -C \
    "--json[Output as JSON]" \
    "--verbose[Verbose logging]" \
    "--store[Path to session store (default: resolved from config)]" \
    "--agent[Agent id to inspect (default: configured default agent)]" \
    "--all-agents[Aggregate sessions across all configured agents]" \
    "--active[Only show sessions updated within the past N minutes]" \
    "1: :_values 'command' 'cleanup[Run session-store maintenance now]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (cleanup) _openclaw_sessions_cleanup ;;
      esac
      ;;
  esac
}

_openclaw_browser_status() {
  _arguments -C \
    
}

_openclaw_browser_start() {
  _arguments -C \
    
}

_openclaw_browser_stop() {
  _arguments -C \
    
}

_openclaw_browser_reset_profile() {
  _arguments -C \
    
}

_openclaw_browser_tabs() {
  _arguments -C \
    
}

_openclaw_browser_tab_new() {
  _arguments -C \
    
}

_openclaw_browser_tab_select() {
  _arguments -C \
    
}

_openclaw_browser_tab_close() {
  _arguments -C \
    
}

_openclaw_browser_tab() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'new[Open a new tab (about:blank)]' 'select[Focus tab by index (1-based)]' 'close[Close tab by index (1-based); default: first tab]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (new) _openclaw_browser_tab_new ;;
        (select) _openclaw_browser_tab_select ;;
        (close) _openclaw_browser_tab_close ;;
      esac
      ;;
  esac
}

_openclaw_browser_open() {
  _arguments -C \
    
}

_openclaw_browser_focus() {
  _arguments -C \
    
}

_openclaw_browser_close() {
  _arguments -C \
    
}

_openclaw_browser_profiles() {
  _arguments -C \
    
}

_openclaw_browser_create_profile() {
  _arguments -C \
    "--name[Profile name (lowercase, numbers, hyphens)]" \
    "--color[Profile color (hex format, e.g. #0066CC)]" \
    "--cdp-url[CDP URL for remote Chrome (http/https)]" \
    "--user-data-dir[User data dir for existing-session Chromium attach]" \
    "--driver[Profile driver (openclaw|existing-session). Default: openclaw]"
}

_openclaw_browser_delete_profile() {
  _arguments -C \
    "--name[Profile name to delete]"
}

_openclaw_browser_screenshot() {
  _arguments -C \
    "--full-page[Capture full scrollable page]" \
    "--ref[ARIA ref from ai snapshot]" \
    "--element[CSS selector for element screenshot]" \
    "--type[Output type (default: png)]"
}

_openclaw_browser_snapshot() {
  _arguments -C \
    "--format[Snapshot format (default: ai)]" \
    "--target-id[CDP target id (or unique prefix)]" \
    "--limit[Max nodes (default: 500/800)]" \
    "--mode[Snapshot preset (efficient)]" \
    "--efficient[Use the efficient snapshot preset]" \
    "--interactive[Role snapshot: interactive elements only]" \
    "--compact[Role snapshot: compact output]" \
    "--depth[Role snapshot: max depth]" \
    "--selector[Role snapshot: scope to CSS selector]" \
    "--frame[Role snapshot: scope to an iframe selector]" \
    "--labels[Include viewport label overlay screenshot]" \
    "--out[Write snapshot to a file]"
}

_openclaw_browser_navigate() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_resize() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_click() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]" \
    "--double[Double click]" \
    "--button[Mouse button to use]" \
    "--modifiers[Comma-separated modifiers (Shift,Alt,Meta)]"
}

_openclaw_browser_type() {
  _arguments -C \
    "--submit[Press Enter after typing]" \
    "--slowly[Type slowly (human-like)]" \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_press() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_hover() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_scrollintoview() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]" \
    "--timeout-ms[How long to wait for scroll (default: 20000)]"
}

_openclaw_browser_drag() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_select() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_upload() {
  _arguments -C \
    "--ref[Ref id from snapshot to click after arming]" \
    "--input-ref[Ref id for <input type=file> to set directly]" \
    "--element[CSS selector for <input type=file>]" \
    "--target-id[CDP target id (or unique prefix)]" \
    "--timeout-ms[How long to wait for the next file chooser (default: 120000)]"
}

_openclaw_browser_waitfordownload() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]" \
    "--timeout-ms[How long to wait for the next download (default: 120000)]"
}

_openclaw_browser_download() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]" \
    "--timeout-ms[How long to wait for the download to start (default: 120000)]"
}

_openclaw_browser_dialog() {
  _arguments -C \
    "--accept[Accept the dialog]" \
    "--dismiss[Dismiss the dialog]" \
    "--prompt[Prompt response text]" \
    "--target-id[CDP target id (or unique prefix)]" \
    "--timeout-ms[How long to wait for the next dialog (default: 120000)]"
}

_openclaw_browser_fill() {
  _arguments -C \
    "--fields[JSON array of field objects]" \
    "--fields-file[Read JSON array from a file]" \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_wait() {
  _arguments -C \
    "--time[Wait for N milliseconds]" \
    "--text[Wait for text to appear]" \
    "--text-gone[Wait for text to disappear]" \
    "--url[Wait for URL (supports globs like **/dash)]" \
    "--load[Wait for load state]" \
    "--fn[Wait for JS condition (passed to waitForFunction)]" \
    "--timeout-ms[How long to wait for each condition (default: 20000)]" \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_evaluate() {
  _arguments -C \
    "--fn[Function source, e.g. (el) => el.textContent]" \
    "--ref[Ref from snapshot]" \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_console() {
  _arguments -C \
    "--level[Filter by level (error, warn, info)]" \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_pdf() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_responsebody() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]" \
    "--timeout-ms[How long to wait for the response (default: 20000)]" \
    "--max-chars[Max body chars to return (default: 200000)]"
}

_openclaw_browser_highlight() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_errors() {
  _arguments -C \
    "--clear[Clear stored errors after reading]" \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_requests() {
  _arguments -C \
    "--filter[Only show URLs that contain this substring]" \
    "--clear[Clear stored requests after reading]" \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_trace_start() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]" \
    "--no-screenshots[Disable screenshots]" \
    "--no-snapshots[Disable snapshots]" \
    "--sources[Include sources (bigger traces)]"
}

_openclaw_browser_trace_stop() {
  _arguments -C \
    "--out[Output path within openclaw temp dir (e.g. trace.zip or /tmp/openclaw/trace.zip)]" \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_trace() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'start[Start trace recording]' 'stop[Stop trace recording and write a .zip]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (start) _openclaw_browser_trace_start ;;
        (stop) _openclaw_browser_trace_stop ;;
      esac
      ;;
  esac
}

_openclaw_browser_cookies_set() {
  _arguments -C \
    "--url[Cookie URL scope (recommended)]" \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_cookies_clear() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_cookies() {
  local -a commands
  local -a options
  
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]" \
    "1: :_values 'command' 'set[Set a cookie (requires --url or domain+path)]' 'clear[Clear all cookies]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (set) _openclaw_browser_cookies_set ;;
        (clear) _openclaw_browser_cookies_clear ;;
      esac
      ;;
  esac
}

_openclaw_browser_storage_local_get() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_storage_local_set() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_storage_local_clear() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_storage_local() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'get[Get localStorage (all keys or one key)]' 'set[Set a localStorage key]' 'clear[Clear all localStorage keys]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (get) _openclaw_browser_storage_local_get ;;
        (set) _openclaw_browser_storage_local_set ;;
        (clear) _openclaw_browser_storage_local_clear ;;
      esac
      ;;
  esac
}

_openclaw_browser_storage_session_get() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_storage_session_set() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_storage_session_clear() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_storage_session() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'get[Get sessionStorage (all keys or one key)]' 'set[Set a sessionStorage key]' 'clear[Clear all sessionStorage keys]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (get) _openclaw_browser_storage_session_get ;;
        (set) _openclaw_browser_storage_session_set ;;
        (clear) _openclaw_browser_storage_session_clear ;;
      esac
      ;;
  esac
}

_openclaw_browser_storage() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'local[localStorage commands]' 'session[sessionStorage commands]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (local) _openclaw_browser_storage_local ;;
        (session) _openclaw_browser_storage_session ;;
      esac
      ;;
  esac
}

_openclaw_browser_set_viewport() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_set_offline() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_set_headers() {
  _arguments -C \
    "--headers-json[JSON object of headers]" \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_set_credentials() {
  _arguments -C \
    "--clear[Clear credentials]" \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_set_geo() {
  _arguments -C \
    "--clear[Clear geolocation + permissions]" \
    "--accuracy[Accuracy in meters]" \
    "--origin[Origin to grant permissions for]" \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_set_media() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_set_timezone() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_set_locale() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_set_device() {
  _arguments -C \
    "--target-id[CDP target id (or unique prefix)]"
}

_openclaw_browser_set() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'viewport[Set viewport size (alias for resize)]' 'offline[Toggle offline mode]' 'headers[Set extra HTTP headers (JSON object)]' 'credentials[Set HTTP basic auth credentials]' 'geo[Set geolocation (and grant permission)]' 'media[Emulate prefers-color-scheme]' 'timezone[Override timezone (CDP)]' 'locale[Override locale (CDP)]' 'device[Apply a Playwright device descriptor (e.g. "iPhone 14")]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (viewport) _openclaw_browser_set_viewport ;;
        (offline) _openclaw_browser_set_offline ;;
        (headers) _openclaw_browser_set_headers ;;
        (credentials) _openclaw_browser_set_credentials ;;
        (geo) _openclaw_browser_set_geo ;;
        (media) _openclaw_browser_set_media ;;
        (timezone) _openclaw_browser_set_timezone ;;
        (locale) _openclaw_browser_set_locale ;;
        (device) _openclaw_browser_set_device ;;
      esac
      ;;
  esac
}

_openclaw_browser() {
  local -a commands
  local -a options
  
  _arguments -C \
    "--browser-profile[Browser profile name (default from config)]" \
    "--json[Output machine-readable JSON]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--expect-final[Wait for final response (agent)]" \
    "1: :_values 'command' 'status[Show browser status]' 'start[Start the browser (no-op if already running)]' 'stop[Stop the browser (best-effort)]' 'reset-profile[Reset browser profile (moves it to Trash)]' 'tabs[List open tabs]' 'tab[Tab shortcuts (index-based)]' 'open[Open a URL in a new tab]' 'focus[Focus a tab by target id (or unique prefix)]' 'close[Close a tab (target id optional)]' 'profiles[List all browser profiles]' 'create-profile[Create a new browser profile]' 'delete-profile[Delete a browser profile]' 'screenshot[Capture a screenshot (MEDIA:<path>)]' 'snapshot[Capture a snapshot (default: ai; aria is the accessibility tree)]' 'navigate[Navigate the current tab to a URL]' 'resize[Resize the viewport]' 'click[Click an element by ref from snapshot]' 'type[Type into an element by ref from snapshot]' 'press[Press a key]' 'hover[Hover an element by ai ref]' 'scrollintoview[Scroll an element into view by ref from snapshot]' 'drag[Drag from one ref to another]' 'select[Select option(s) in a select element]' 'upload[Arm file upload for the next file chooser]' 'waitfordownload[Wait for the next download (and save it)]' 'download[Click a ref and save the resulting download]' 'dialog[Arm the next modal dialog (alert/confirm/prompt)]' 'fill[Fill a form with JSON field descriptors]' 'wait[Wait for time, selector, URL, load state, or JS conditions]' 'evaluate[Evaluate a function against the page or a ref]' 'console[Get recent console messages]' 'pdf[Save page as PDF]' 'responsebody[Wait for a network response and return its body]' 'highlight[Highlight an element by ref]' 'errors[Get recent page errors]' 'requests[Get recent network requests (best-effort)]' 'trace[Record a Playwright trace]' 'cookies[Read/write cookies]' 'storage[Read/write localStorage/sessionStorage]' 'set[Browser environment settings]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (status) _openclaw_browser_status ;;
        (start) _openclaw_browser_start ;;
        (stop) _openclaw_browser_stop ;;
        (reset-profile) _openclaw_browser_reset_profile ;;
        (tabs) _openclaw_browser_tabs ;;
        (tab) _openclaw_browser_tab ;;
        (open) _openclaw_browser_open ;;
        (focus) _openclaw_browser_focus ;;
        (close) _openclaw_browser_close ;;
        (profiles) _openclaw_browser_profiles ;;
        (create-profile) _openclaw_browser_create_profile ;;
        (delete-profile) _openclaw_browser_delete_profile ;;
        (screenshot) _openclaw_browser_screenshot ;;
        (snapshot) _openclaw_browser_snapshot ;;
        (navigate) _openclaw_browser_navigate ;;
        (resize) _openclaw_browser_resize ;;
        (click) _openclaw_browser_click ;;
        (type) _openclaw_browser_type ;;
        (press) _openclaw_browser_press ;;
        (hover) _openclaw_browser_hover ;;
        (scrollintoview) _openclaw_browser_scrollintoview ;;
        (drag) _openclaw_browser_drag ;;
        (select) _openclaw_browser_select ;;
        (upload) _openclaw_browser_upload ;;
        (waitfordownload) _openclaw_browser_waitfordownload ;;
        (download) _openclaw_browser_download ;;
        (dialog) _openclaw_browser_dialog ;;
        (fill) _openclaw_browser_fill ;;
        (wait) _openclaw_browser_wait ;;
        (evaluate) _openclaw_browser_evaluate ;;
        (console) _openclaw_browser_console ;;
        (pdf) _openclaw_browser_pdf ;;
        (responsebody) _openclaw_browser_responsebody ;;
        (highlight) _openclaw_browser_highlight ;;
        (errors) _openclaw_browser_errors ;;
        (requests) _openclaw_browser_requests ;;
        (trace) _openclaw_browser_trace ;;
        (cookies) _openclaw_browser_cookies ;;
        (storage) _openclaw_browser_storage ;;
        (set) _openclaw_browser_set ;;
      esac
      ;;
  esac
}

_openclaw_acp_client() {
  _arguments -C \
    "--cwd[Working directory for the ACP session]" \
    "--server[ACP server command (default: openclaw)]" \
    "--server-args[Extra arguments for the ACP server]" \
    "--server-verbose[Enable verbose logging on the ACP server]" \
    "(--verbose -v)"{--verbose,-v}"[Verbose client logging]"
}

_openclaw_acp() {
  local -a commands
  local -a options
  
  _arguments -C \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--token-file[Read gateway token from file]" \
    "--password[Gateway password (if required)]" \
    "--password-file[Read gateway password from file]" \
    "--session[Default session key (e.g. agent:main:main)]" \
    "--session-label[Default session label to resolve]" \
    "--require-existing[Fail if the session key/label does not exist]" \
    "--reset-session[Reset the session key before first use]" \
    "--no-prefix-cwd[Do not prefix prompts with the working directory]" \
    "--provenance[ACP provenance mode: off, meta, or meta+receipt]" \
    "(--verbose -v)"{--verbose,-v}"[Verbose logging to stderr]" \
    "1: :_values 'command' 'client[Run an interactive ACP client against the local ACP bridge]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (client) _openclaw_acp_client ;;
      esac
      ;;
  esac
}

_openclaw_gateway_run() {
  _arguments -C \
    "--port[Port for the gateway WebSocket]" \
    "--bind[Bind mode (\"loopback\"|\"lan\"|\"tailnet\"|\"auto\"|\"custom\"). Defaults to config gateway.bind (or loopback).]" \
    "--token[Shared token required in connect.params.auth.token (default: OPENCLAW_GATEWAY_TOKEN env if set)]" \
    "--auth[Gateway auth mode (\"none\"|\"token\"|\"password\"|\"trusted-proxy\")]" \
    "--password[Password for auth mode=password]" \
    "--password-file[Read gateway password from file]" \
    "--tailscale[Tailscale exposure mode (\"off\"|\"serve\"|\"funnel\")]" \
    "--tailscale-reset-on-exit[Reset Tailscale serve/funnel configuration on shutdown]" \
    "--allow-unconfigured[Allow gateway start without gateway.mode=local in config]" \
    "--dev[Create a dev config + workspace if missing (no BOOTSTRAP.md)]" \
    "--reset[Reset dev config + credentials + sessions + workspace (requires --dev)]" \
    "--force[Kill any existing listener on the target port before starting]" \
    "--verbose[Verbose logging to stdout/stderr]" \
    "--claude-cli-logs[Only show claude-cli logs in the console (includes stdout/stderr)]" \
    "--ws-log[WebSocket log style (\"auto\"|\"full\"|\"compact\")]" \
    "--compact[Alias for \"--ws-log compact\"]" \
    "--raw-stream[Log raw model stream events to jsonl]" \
    "--raw-stream-path[Raw stream jsonl path]"
}

_openclaw_gateway_status() {
  _arguments -C \
    "--url[Gateway WebSocket URL (defaults to config/remote/local)]" \
    "--token[Gateway token (if required)]" \
    "--password[Gateway password (password auth)]" \
    "--timeout[Timeout in ms]" \
    "--no-probe[Skip RPC probe]" \
    "--require-rpc[Exit non-zero when the RPC probe fails]" \
    "--deep[Scan system-level services]" \
    "--json[Output JSON]"
}

_openclaw_gateway_install() {
  _arguments -C \
    "--port[Gateway port]" \
    "--runtime[Daemon runtime (node|bun). Default: node]" \
    "--token[Gateway token (token auth)]" \
    "--force[Reinstall/overwrite if already installed]" \
    "--json[Output JSON]"
}

_openclaw_gateway_uninstall() {
  _arguments -C \
    "--json[Output JSON]"
}

_openclaw_gateway_start() {
  _arguments -C \
    "--json[Output JSON]"
}

_openclaw_gateway_stop() {
  _arguments -C \
    "--json[Output JSON]"
}

_openclaw_gateway_restart() {
  _arguments -C \
    "--json[Output JSON]"
}

_openclaw_gateway_call() {
  _arguments -C \
    "--params[JSON object string for params]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--password[Gateway password (password auth)]" \
    "--timeout[Timeout in ms]" \
    "--expect-final[Wait for final response (agent)]" \
    "--json[Output JSON]"
}

_openclaw_gateway_usage_cost() {
  _arguments -C \
    "--days[Number of days to include]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--password[Gateway password (password auth)]" \
    "--timeout[Timeout in ms]" \
    "--expect-final[Wait for final response (agent)]" \
    "--json[Output JSON]"
}

_openclaw_gateway_health() {
  _arguments -C \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--password[Gateway password (password auth)]" \
    "--timeout[Timeout in ms]" \
    "--expect-final[Wait for final response (agent)]" \
    "--json[Output JSON]"
}

_openclaw_gateway_probe() {
  _arguments -C \
    "--url[Explicit Gateway WebSocket URL (still probes localhost)]" \
    "--ssh[SSH target for remote gateway tunnel (user@host or user@host:port)]" \
    "--ssh-identity[SSH identity file path]" \
    "--ssh-auto[Try to derive an SSH target from Bonjour discovery]" \
    "--token[Gateway token (applies to all probes)]" \
    "--password[Gateway password (applies to all probes)]" \
    "--timeout[Overall probe budget in ms]" \
    "--json[Output JSON]"
}

_openclaw_gateway_discover() {
  _arguments -C \
    "--timeout[Per-command timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_gateway() {
  local -a commands
  local -a options
  
  _arguments -C \
    "--port[Port for the gateway WebSocket]" \
    "--bind[Bind mode (\"loopback\"|\"lan\"|\"tailnet\"|\"auto\"|\"custom\"). Defaults to config gateway.bind (or loopback).]" \
    "--token[Shared token required in connect.params.auth.token (default: OPENCLAW_GATEWAY_TOKEN env if set)]" \
    "--auth[Gateway auth mode (\"none\"|\"token\"|\"password\"|\"trusted-proxy\")]" \
    "--password[Password for auth mode=password]" \
    "--password-file[Read gateway password from file]" \
    "--tailscale[Tailscale exposure mode (\"off\"|\"serve\"|\"funnel\")]" \
    "--tailscale-reset-on-exit[Reset Tailscale serve/funnel configuration on shutdown]" \
    "--allow-unconfigured[Allow gateway start without gateway.mode=local in config]" \
    "--dev[Create a dev config + workspace if missing (no BOOTSTRAP.md)]" \
    "--reset[Reset dev config + credentials + sessions + workspace (requires --dev)]" \
    "--force[Kill any existing listener on the target port before starting]" \
    "--verbose[Verbose logging to stdout/stderr]" \
    "--claude-cli-logs[Only show claude-cli logs in the console (includes stdout/stderr)]" \
    "--ws-log[WebSocket log style (\"auto\"|\"full\"|\"compact\")]" \
    "--compact[Alias for \"--ws-log compact\"]" \
    "--raw-stream[Log raw model stream events to jsonl]" \
    "--raw-stream-path[Raw stream jsonl path]" \
    "1: :_values 'command' 'run[Run the WebSocket Gateway (foreground)]' 'status[Show gateway service status + probe the Gateway]' 'install[Install the Gateway service (launchd/systemd/schtasks)]' 'uninstall[Uninstall the Gateway service (launchd/systemd/schtasks)]' 'start[Start the Gateway service (launchd/systemd/schtasks)]' 'stop[Stop the Gateway service (launchd/systemd/schtasks)]' 'restart[Restart the Gateway service (launchd/systemd/schtasks)]' 'call[Call a Gateway method]' 'usage-cost[Fetch usage cost summary from session logs]' 'health[Fetch Gateway health]' 'probe[Show gateway reachability + discovery + health + status summary (local + remote)]' 'discover[Discover gateways via Bonjour (local + wide-area if configured)]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (run) _openclaw_gateway_run ;;
        (status) _openclaw_gateway_status ;;
        (install) _openclaw_gateway_install ;;
        (uninstall) _openclaw_gateway_uninstall ;;
        (start) _openclaw_gateway_start ;;
        (stop) _openclaw_gateway_stop ;;
        (restart) _openclaw_gateway_restart ;;
        (call) _openclaw_gateway_call ;;
        (usage-cost) _openclaw_gateway_usage_cost ;;
        (health) _openclaw_gateway_health ;;
        (probe) _openclaw_gateway_probe ;;
        (discover) _openclaw_gateway_discover ;;
      esac
      ;;
  esac
}

_openclaw_daemon_status() {
  _arguments -C \
    "--url[Gateway WebSocket URL (defaults to config/remote/local)]" \
    "--token[Gateway token (if required)]" \
    "--password[Gateway password (password auth)]" \
    "--timeout[Timeout in ms]" \
    "--no-probe[Skip RPC probe]" \
    "--require-rpc[Exit non-zero when the RPC probe fails]" \
    "--deep[Scan system-level services]" \
    "--json[Output JSON]"
}

_openclaw_daemon_install() {
  _arguments -C \
    "--port[Gateway port]" \
    "--runtime[Daemon runtime (node|bun). Default: node]" \
    "--token[Gateway token (token auth)]" \
    "--force[Reinstall/overwrite if already installed]" \
    "--json[Output JSON]"
}

_openclaw_daemon_uninstall() {
  _arguments -C \
    "--json[Output JSON]"
}

_openclaw_daemon_start() {
  _arguments -C \
    "--json[Output JSON]"
}

_openclaw_daemon_stop() {
  _arguments -C \
    "--json[Output JSON]"
}

_openclaw_daemon_restart() {
  _arguments -C \
    "--json[Output JSON]"
}

_openclaw_daemon() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'status[Show service install status + probe the Gateway]' 'install[Install the Gateway service (launchd/systemd/schtasks)]' 'uninstall[Uninstall the Gateway service (launchd/systemd/schtasks)]' 'start[Start the Gateway service (launchd/systemd/schtasks)]' 'stop[Stop the Gateway service (launchd/systemd/schtasks)]' 'restart[Restart the Gateway service (launchd/systemd/schtasks)]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (status) _openclaw_daemon_status ;;
        (install) _openclaw_daemon_install ;;
        (uninstall) _openclaw_daemon_uninstall ;;
        (start) _openclaw_daemon_start ;;
        (stop) _openclaw_daemon_stop ;;
        (restart) _openclaw_daemon_restart ;;
      esac
      ;;
  esac
}

_openclaw_logs() {
  _arguments -C \
    "--limit[Max lines to return]" \
    "--max-bytes[Max bytes to read]" \
    "--follow[Follow log output]" \
    "--interval[Polling interval in ms]" \
    "--json[Emit JSON log lines]" \
    "--plain[Plain text output (no ANSI styling)]" \
    "--no-color[Disable ANSI colors]" \
    "--local-time[Display timestamps in local timezone]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--expect-final[Wait for final response (agent)]"
}

_openclaw_system_event() {
  _arguments -C \
    "--text[System event text]" \
    "--mode[Wake mode (now|next-heartbeat)]" \
    "--json[Output JSON]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--expect-final[Wait for final response (agent)]"
}

_openclaw_system_heartbeat_last() {
  _arguments -C \
    "--json[Output JSON]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--expect-final[Wait for final response (agent)]"
}

_openclaw_system_heartbeat_enable() {
  _arguments -C \
    "--json[Output JSON]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--expect-final[Wait for final response (agent)]"
}

_openclaw_system_heartbeat_disable() {
  _arguments -C \
    "--json[Output JSON]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--expect-final[Wait for final response (agent)]"
}

_openclaw_system_heartbeat() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'last[Show the last heartbeat event]' 'enable[Enable heartbeats]' 'disable[Disable heartbeats]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (last) _openclaw_system_heartbeat_last ;;
        (enable) _openclaw_system_heartbeat_enable ;;
        (disable) _openclaw_system_heartbeat_disable ;;
      esac
      ;;
  esac
}

_openclaw_system_presence() {
  _arguments -C \
    "--json[Output JSON]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--expect-final[Wait for final response (agent)]"
}

_openclaw_system() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'event[Enqueue a system event and optionally trigger a heartbeat]' 'heartbeat[Heartbeat controls]' 'presence[List system presence entries]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (event) _openclaw_system_event ;;
        (heartbeat) _openclaw_system_heartbeat ;;
        (presence) _openclaw_system_presence ;;
      esac
      ;;
  esac
}

_openclaw_models_list() {
  _arguments -C \
    "--all[Show full model catalog]" \
    "--local[Filter to local models]" \
    "--provider[Filter by provider]" \
    "--json[Output JSON]" \
    "--plain[Plain line output]"
}

_openclaw_models_status() {
  _arguments -C \
    "--json[Output JSON]" \
    "--plain[Plain output]" \
    "--check[Exit non-zero if auth is expiring/expired (1=expired/missing, 2=expiring)]" \
    "--probe[Probe configured provider auth (live)]" \
    "--probe-provider[Only probe a single provider]" \
    "--probe-profile[Only probe specific auth profile ids (repeat or comma-separated)]" \
    "--probe-timeout[Per-probe timeout in ms]" \
    "--probe-concurrency[Concurrent probes]" \
    "--probe-max-tokens[Probe max tokens (best-effort)]" \
    "--agent[Agent id to inspect (overrides OPENCLAW_AGENT_DIR/PI_CODING_AGENT_DIR)]"
}

_openclaw_models_set() {
  _arguments -C \
    
}

_openclaw_models_set_image() {
  _arguments -C \
    
}

_openclaw_models_aliases_list() {
  _arguments -C \
    "--json[Output JSON]" \
    "--plain[Plain output]"
}

_openclaw_models_aliases_add() {
  _arguments -C \
    
}

_openclaw_models_aliases_remove() {
  _arguments -C \
    
}

_openclaw_models_aliases() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'list[List model aliases]' 'add[Add or update a model alias]' 'remove[Remove a model alias]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (list) _openclaw_models_aliases_list ;;
        (add) _openclaw_models_aliases_add ;;
        (remove) _openclaw_models_aliases_remove ;;
      esac
      ;;
  esac
}

_openclaw_models_fallbacks_list() {
  _arguments -C \
    "--json[Output JSON]" \
    "--plain[Plain output]"
}

_openclaw_models_fallbacks_add() {
  _arguments -C \
    
}

_openclaw_models_fallbacks_remove() {
  _arguments -C \
    
}

_openclaw_models_fallbacks_clear() {
  _arguments -C \
    
}

_openclaw_models_fallbacks() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'list[List fallback models]' 'add[Add a fallback model]' 'remove[Remove a fallback model]' 'clear[Clear all fallback models]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (list) _openclaw_models_fallbacks_list ;;
        (add) _openclaw_models_fallbacks_add ;;
        (remove) _openclaw_models_fallbacks_remove ;;
        (clear) _openclaw_models_fallbacks_clear ;;
      esac
      ;;
  esac
}

_openclaw_models_image_fallbacks_list() {
  _arguments -C \
    "--json[Output JSON]" \
    "--plain[Plain output]"
}

_openclaw_models_image_fallbacks_add() {
  _arguments -C \
    
}

_openclaw_models_image_fallbacks_remove() {
  _arguments -C \
    
}

_openclaw_models_image_fallbacks_clear() {
  _arguments -C \
    
}

_openclaw_models_image_fallbacks() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'list[List image fallback models]' 'add[Add an image fallback model]' 'remove[Remove an image fallback model]' 'clear[Clear all image fallback models]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (list) _openclaw_models_image_fallbacks_list ;;
        (add) _openclaw_models_image_fallbacks_add ;;
        (remove) _openclaw_models_image_fallbacks_remove ;;
        (clear) _openclaw_models_image_fallbacks_clear ;;
      esac
      ;;
  esac
}

_openclaw_models_scan() {
  _arguments -C \
    "--min-params[Minimum parameter size (billions)]" \
    "--max-age-days[Skip models older than N days]" \
    "--provider[Filter by provider prefix]" \
    "--max-candidates[Max fallback candidates]" \
    "--timeout[Per-probe timeout in ms]" \
    "--concurrency[Probe concurrency]" \
    "--no-probe[Skip live probes; list free candidates only]" \
    "--yes[Accept defaults without prompting]" \
    "--no-input[Disable prompts (use defaults)]" \
    "--set-default[Set agents.defaults.model to the first selection]" \
    "--set-image[Set agents.defaults.imageModel to the first image selection]" \
    "--json[Output JSON]"
}

_openclaw_models_auth_add() {
  _arguments -C \
    
}

_openclaw_models_auth_login() {
  _arguments -C \
    "--provider[Provider id registered by a plugin]" \
    "--method[Provider auth method id]" \
    "--set-default[Apply the provider'\''s default model recommendation]"
}

_openclaw_models_auth_setup_token() {
  _arguments -C \
    "--provider[Provider id (default: anthropic)]" \
    "--yes[Skip confirmation]"
}

_openclaw_models_auth_paste_token() {
  _arguments -C \
    "--provider[Provider id (e.g. anthropic)]" \
    "--profile-id[Auth profile id (default: <provider>:manual)]" \
    "--expires-in[Optional expiry duration (e.g. 365d, 12h). Stored as absolute expiresAt.]"
}

_openclaw_models_auth_login_github_copilot() {
  _arguments -C \
    "--yes[Overwrite existing profile without prompting]"
}

_openclaw_models_auth_order_get() {
  _arguments -C \
    "--provider[Provider id (e.g. anthropic)]" \
    "--agent[Agent id (default: configured default agent)]" \
    "--json[Output JSON]"
}

_openclaw_models_auth_order_set() {
  _arguments -C \
    "--provider[Provider id (e.g. anthropic)]" \
    "--agent[Agent id (default: configured default agent)]"
}

_openclaw_models_auth_order_clear() {
  _arguments -C \
    "--provider[Provider id (e.g. anthropic)]" \
    "--agent[Agent id (default: configured default agent)]"
}

_openclaw_models_auth_order() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'get[Show per-agent auth order override (from auth-profiles.json)]' 'set[Set per-agent auth order override (locks rotation to this list)]' 'clear[Clear per-agent auth order override (fall back to config/round-robin)]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (get) _openclaw_models_auth_order_get ;;
        (set) _openclaw_models_auth_order_set ;;
        (clear) _openclaw_models_auth_order_clear ;;
      esac
      ;;
  esac
}

_openclaw_models_auth() {
  local -a commands
  local -a options
  
  _arguments -C \
    "--agent[Agent id for auth order get/set/clear]" \
    "1: :_values 'command' 'add[Interactive auth helper (setup-token or paste token)]' 'login[Run a provider plugin auth flow (OAuth/API key)]' 'setup-token[Run a provider CLI to create/sync a token (TTY required)]' 'paste-token[Paste a token into auth-profiles.json and update config]' 'login-github-copilot[Login to GitHub Copilot via GitHub device flow (TTY required)]' 'order[Manage per-agent auth profile order overrides]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (add) _openclaw_models_auth_add ;;
        (login) _openclaw_models_auth_login ;;
        (setup-token) _openclaw_models_auth_setup_token ;;
        (paste-token) _openclaw_models_auth_paste_token ;;
        (login-github-copilot) _openclaw_models_auth_login_github_copilot ;;
        (order) _openclaw_models_auth_order ;;
      esac
      ;;
  esac
}

_openclaw_models() {
  local -a commands
  local -a options
  
  _arguments -C \
    "--status-json[Output JSON (alias for `models status --json`)]" \
    "--status-plain[Plain output (alias for `models status --plain`)]" \
    "--agent[Agent id to inspect (overrides OPENCLAW_AGENT_DIR/PI_CODING_AGENT_DIR)]" \
    "1: :_values 'command' 'list[List models (configured by default)]' 'status[Show configured model state]' 'set[Set the default model]' 'set-image[Set the image model]' 'aliases[Manage model aliases]' 'fallbacks[Manage model fallback list]' 'image-fallbacks[Manage image model fallback list]' 'scan[Scan OpenRouter free models for tools + images]' 'auth[Manage model auth profiles]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (list) _openclaw_models_list ;;
        (status) _openclaw_models_status ;;
        (set) _openclaw_models_set ;;
        (set-image) _openclaw_models_set_image ;;
        (aliases) _openclaw_models_aliases ;;
        (fallbacks) _openclaw_models_fallbacks ;;
        (image-fallbacks) _openclaw_models_image_fallbacks ;;
        (scan) _openclaw_models_scan ;;
        (auth) _openclaw_models_auth ;;
      esac
      ;;
  esac
}

_openclaw_approvals_get() {
  _arguments -C \
    "--node[Target node id/name/IP]" \
    "--gateway[Force gateway approvals]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_approvals_set() {
  _arguments -C \
    "--node[Target node id/name/IP]" \
    "--gateway[Force gateway approvals]" \
    "--file[Path to JSON file to upload]" \
    "--stdin[Read JSON from stdin]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_approvals_allowlist_add() {
  _arguments -C \
    "--node[Target node id/name/IP]" \
    "--gateway[Force gateway approvals]" \
    "--agent[Agent id (defaults to \"*\")]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_approvals_allowlist_remove() {
  _arguments -C \
    "--node[Target node id/name/IP]" \
    "--gateway[Force gateway approvals]" \
    "--agent[Agent id (defaults to \"*\")]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_approvals_allowlist() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'add[Add a glob pattern to an allowlist]' 'remove[Remove a glob pattern from an allowlist]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (add) _openclaw_approvals_allowlist_add ;;
        (remove) _openclaw_approvals_allowlist_remove ;;
      esac
      ;;
  esac
}

_openclaw_approvals() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'get[Fetch exec approvals snapshot]' 'set[Replace exec approvals with a JSON file]' 'allowlist[Edit the per-agent allowlist]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (get) _openclaw_approvals_get ;;
        (set) _openclaw_approvals_set ;;
        (allowlist) _openclaw_approvals_allowlist ;;
      esac
      ;;
  esac
}

_openclaw_nodes_status() {
  _arguments -C \
    "--connected[Only show connected nodes]" \
    "--last-connected[Only show nodes connected within duration (e.g. 24h)]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_describe() {
  _arguments -C \
    "--node[Node id, name, or IP]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_list() {
  _arguments -C \
    "--connected[Only show connected nodes]" \
    "--last-connected[Only show nodes connected within duration (e.g. 24h)]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_pending() {
  _arguments -C \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_approve() {
  _arguments -C \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_reject() {
  _arguments -C \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_rename() {
  _arguments -C \
    "--node[Node id, name, or IP]" \
    "--name[New display name]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_invoke() {
  _arguments -C \
    "--node[Node id, name, or IP]" \
    "--command[Command (e.g. canvas.eval)]" \
    "--params[JSON object string for params]" \
    "--invoke-timeout[Node invoke timeout in ms (default 15000)]" \
    "--idempotency-key[Idempotency key (optional)]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_run() {
  _arguments -C \
    "--node[Node id, name, or IP]" \
    "--cwd[Working directory]" \
    "--env[Environment override (repeatable)]" \
    "--raw[Run a raw shell command string (sh -lc / cmd.exe /c)]" \
    "--agent[Agent id (default: configured default agent)]" \
    "--ask[Exec ask mode (off|on-miss|always)]" \
    "--security[Exec security mode (deny|allowlist|full)]" \
    "--command-timeout[Command timeout (ms)]" \
    "--needs-screen-recording[Require screen recording permission]" \
    "--invoke-timeout[Node invoke timeout in ms (default 30000)]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_notify() {
  _arguments -C \
    "--node[Node id, name, or IP]" \
    "--title[Notification title]" \
    "--body[Notification body]" \
    "--sound[Notification sound]" \
    "--priority[Notification priority]" \
    "--delivery[Delivery mode]" \
    "--invoke-timeout[Node invoke timeout in ms (default 15000)]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_push() {
  _arguments -C \
    "--node[Node id, name, or IP]" \
    "--title[Push title]" \
    "--body[Push body]" \
    "--environment[Override APNs environment]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_canvas_snapshot() {
  _arguments -C \
    "--node[Node id, name, or IP]" \
    "--format[Image format]" \
    "--max-width[Max width in px (optional)]" \
    "--quality[JPEG quality (optional)]" \
    "--invoke-timeout[Node invoke timeout in ms (default 20000)]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_canvas_present() {
  _arguments -C \
    "--node[Node id, name, or IP]" \
    "--target[Target URL/path (optional)]" \
    "--x[Placement x coordinate]" \
    "--y[Placement y coordinate]" \
    "--width[Placement width]" \
    "--height[Placement height]" \
    "--invoke-timeout[Node invoke timeout in ms]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_canvas_hide() {
  _arguments -C \
    "--node[Node id, name, or IP]" \
    "--invoke-timeout[Node invoke timeout in ms]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_canvas_navigate() {
  _arguments -C \
    "--node[Node id, name, or IP]" \
    "--invoke-timeout[Node invoke timeout in ms]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_canvas_eval() {
  _arguments -C \
    "--js[JavaScript to evaluate]" \
    "--node[Node id, name, or IP]" \
    "--invoke-timeout[Node invoke timeout in ms]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_canvas_a2ui_push() {
  _arguments -C \
    "--jsonl[Path to JSONL payload]" \
    "--text[Render a quick A2UI text payload]" \
    "--node[Node id, name, or IP]" \
    "--invoke-timeout[Node invoke timeout in ms]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_canvas_a2ui_reset() {
  _arguments -C \
    "--node[Node id, name, or IP]" \
    "--invoke-timeout[Node invoke timeout in ms]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_canvas_a2ui() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'push[Push A2UI JSONL to the canvas]' 'reset[Reset A2UI renderer state]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (push) _openclaw_nodes_canvas_a2ui_push ;;
        (reset) _openclaw_nodes_canvas_a2ui_reset ;;
      esac
      ;;
  esac
}

_openclaw_nodes_canvas() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'snapshot[Capture a canvas snapshot (prints MEDIA:<path>)]' 'present[Show the canvas (optionally with a target URL/path)]' 'hide[Hide the canvas]' 'navigate[Navigate the canvas to a URL]' 'eval[Evaluate JavaScript in the canvas]' 'a2ui[Render A2UI content on the canvas]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (snapshot) _openclaw_nodes_canvas_snapshot ;;
        (present) _openclaw_nodes_canvas_present ;;
        (hide) _openclaw_nodes_canvas_hide ;;
        (navigate) _openclaw_nodes_canvas_navigate ;;
        (eval) _openclaw_nodes_canvas_eval ;;
        (a2ui) _openclaw_nodes_canvas_a2ui ;;
      esac
      ;;
  esac
}

_openclaw_nodes_camera_list() {
  _arguments -C \
    "--node[Node id, name, or IP]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_camera_snap() {
  _arguments -C \
    "--node[Node id, name, or IP]" \
    "--facing[Camera facing]" \
    "--device-id[Camera device id (from nodes camera list)]" \
    "--max-width[Max width in px (optional)]" \
    "--quality[JPEG quality (default 0.9)]" \
    "--delay-ms[Delay before capture in ms (macOS default 2000)]" \
    "--invoke-timeout[Node invoke timeout in ms (default 20000)]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_camera_clip() {
  _arguments -C \
    "--node[Node id, name, or IP]" \
    "--facing[Camera facing]" \
    "--device-id[Camera device id (from nodes camera list)]" \
    "--duration[Duration (default 3000ms; supports ms/s/m, e.g. 10s)]" \
    "--no-audio[Disable audio capture]" \
    "--invoke-timeout[Node invoke timeout in ms (default 90000)]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_camera() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'list[List available cameras on a node]' 'snap[Capture a photo from a node camera (prints MEDIA:<path>)]' 'clip[Capture a short video clip from a node camera (prints MEDIA:<path>)]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (list) _openclaw_nodes_camera_list ;;
        (snap) _openclaw_nodes_camera_snap ;;
        (clip) _openclaw_nodes_camera_clip ;;
      esac
      ;;
  esac
}

_openclaw_nodes_screen_record() {
  _arguments -C \
    "--node[Node id, name, or IP]" \
    "--screen[Screen index (0 = primary)]" \
    "--duration[Clip duration (ms or 10s)]" \
    "--fps[Frames per second]" \
    "--no-audio[Disable microphone audio capture]" \
    "--out[Output path]" \
    "--invoke-timeout[Node invoke timeout in ms (default 120000)]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_screen() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'record[Capture a short screen recording from a node (prints MEDIA:<path>)]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (record) _openclaw_nodes_screen_record ;;
      esac
      ;;
  esac
}

_openclaw_nodes_location_get() {
  _arguments -C \
    "--node[Node id, name, or IP]" \
    "--max-age[Use cached location newer than this (ms)]" \
    "--accuracy[Desired accuracy (default: balanced/precise depending on node setting)]" \
    "--location-timeout[Location fix timeout (ms)]" \
    "--invoke-timeout[Node invoke timeout in ms (default 20000)]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_nodes_location() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'get[Fetch the current location from a node]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (get) _openclaw_nodes_location_get ;;
      esac
      ;;
  esac
}

_openclaw_nodes() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'status[List known nodes with connection status and capabilities]' 'describe[Describe a node (capabilities + supported invoke commands)]' 'list[List pending and paired nodes]' 'pending[List pending pairing requests]' 'approve[Approve a pending pairing request]' 'reject[Reject a pending pairing request]' 'rename[Rename a paired node (display name override)]' 'invoke[Invoke a command on a paired node]' 'run[Run a shell command on a node (mac only)]' 'notify[Send a local notification on a node (mac only)]' 'push[Send an APNs test push to an iOS node]' 'canvas[Capture or render canvas content from a paired node]' 'camera[Capture camera media from a paired node]' 'screen[Capture screen recordings from a paired node]' 'location[Fetch location from a paired node]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (status) _openclaw_nodes_status ;;
        (describe) _openclaw_nodes_describe ;;
        (list) _openclaw_nodes_list ;;
        (pending) _openclaw_nodes_pending ;;
        (approve) _openclaw_nodes_approve ;;
        (reject) _openclaw_nodes_reject ;;
        (rename) _openclaw_nodes_rename ;;
        (invoke) _openclaw_nodes_invoke ;;
        (run) _openclaw_nodes_run ;;
        (notify) _openclaw_nodes_notify ;;
        (push) _openclaw_nodes_push ;;
        (canvas) _openclaw_nodes_canvas ;;
        (camera) _openclaw_nodes_camera ;;
        (screen) _openclaw_nodes_screen ;;
        (location) _openclaw_nodes_location ;;
      esac
      ;;
  esac
}

_openclaw_devices_list() {
  _arguments -C \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--password[Gateway password (password auth)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_devices_remove() {
  _arguments -C \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--password[Gateway password (password auth)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_devices_clear() {
  _arguments -C \
    "--pending[Also reject all pending pairing requests]" \
    "--yes[Confirm destructive clear]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--password[Gateway password (password auth)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_devices_approve() {
  _arguments -C \
    "--latest[Approve the most recent pending request]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--password[Gateway password (password auth)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_devices_reject() {
  _arguments -C \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--password[Gateway password (password auth)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_devices_rotate() {
  _arguments -C \
    "--device[Device id]" \
    "--role[Role name]" \
    "--scope[Scopes to attach to the token (repeatable)]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--password[Gateway password (password auth)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_devices_revoke() {
  _arguments -C \
    "--device[Device id]" \
    "--role[Role name]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--password[Gateway password (password auth)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_devices() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'list[List pending and paired devices]' 'remove[Remove a paired device entry]' 'clear[Clear paired devices from the gateway table]' 'approve[Approve a pending device pairing request]' 'reject[Reject a pending device pairing request]' 'rotate[Rotate a device token for a role]' 'revoke[Revoke a device token for a role]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (list) _openclaw_devices_list ;;
        (remove) _openclaw_devices_remove ;;
        (clear) _openclaw_devices_clear ;;
        (approve) _openclaw_devices_approve ;;
        (reject) _openclaw_devices_reject ;;
        (rotate) _openclaw_devices_rotate ;;
        (revoke) _openclaw_devices_revoke ;;
      esac
      ;;
  esac
}

_openclaw_node_run() {
  _arguments -C \
    "--host[Gateway host]" \
    "--port[Gateway port]" \
    "--tls[Use TLS for the gateway connection]" \
    "--tls-fingerprint[Expected TLS certificate fingerprint (sha256)]" \
    "--node-id[Override node id (clears pairing token)]" \
    "--display-name[Override node display name]"
}

_openclaw_node_status() {
  _arguments -C \
    "--json[Output JSON]"
}

_openclaw_node_install() {
  _arguments -C \
    "--host[Gateway host]" \
    "--port[Gateway port]" \
    "--tls[Use TLS for the gateway connection]" \
    "--tls-fingerprint[Expected TLS certificate fingerprint (sha256)]" \
    "--node-id[Override node id (clears pairing token)]" \
    "--display-name[Override node display name]" \
    "--runtime[Service runtime (node|bun). Default: node]" \
    "--force[Reinstall/overwrite if already installed]" \
    "--json[Output JSON]"
}

_openclaw_node_uninstall() {
  _arguments -C \
    "--json[Output JSON]"
}

_openclaw_node_stop() {
  _arguments -C \
    "--json[Output JSON]"
}

_openclaw_node_restart() {
  _arguments -C \
    "--json[Output JSON]"
}

_openclaw_node() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'run[Run the headless node host (foreground)]' 'status[Show node host status]' 'install[Install the node host service (launchd/systemd/schtasks)]' 'uninstall[Uninstall the node host service (launchd/systemd/schtasks)]' 'stop[Stop the node host service (launchd/systemd/schtasks)]' 'restart[Restart the node host service (launchd/systemd/schtasks)]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (run) _openclaw_node_run ;;
        (status) _openclaw_node_status ;;
        (install) _openclaw_node_install ;;
        (uninstall) _openclaw_node_uninstall ;;
        (stop) _openclaw_node_stop ;;
        (restart) _openclaw_node_restart ;;
      esac
      ;;
  esac
}

_openclaw_sandbox_list() {
  _arguments -C \
    "--json[Output result as JSON]" \
    "--browser[List browser containers only]"
}

_openclaw_sandbox_recreate() {
  _arguments -C \
    "--all[Recreate all sandbox containers]" \
    "--session[Recreate container for specific session]" \
    "--agent[Recreate containers for specific agent]" \
    "--browser[Only recreate browser containers]" \
    "--force[Skip confirmation prompt]"
}

_openclaw_sandbox_explain() {
  _arguments -C \
    "--session[Session key to inspect (defaults to agent main)]" \
    "--agent[Agent id to inspect (defaults to derived agent)]" \
    "--json[Output result as JSON]"
}

_openclaw_sandbox() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'list[List sandbox containers and their status]' 'recreate[Remove containers to force recreation with updated config]' 'explain[Explain effective sandbox/tool policy for a session/agent]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (list) _openclaw_sandbox_list ;;
        (recreate) _openclaw_sandbox_recreate ;;
        (explain) _openclaw_sandbox_explain ;;
      esac
      ;;
  esac
}

_openclaw_tui() {
  _arguments -C \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--password[Gateway password (if required)]" \
    "--session[Session key (default: \"main\", or \"global\" when scope is global)]" \
    "--deliver[Deliver assistant replies]" \
    "--thinking[Thinking level override]" \
    "--message[Send an initial message after connecting]" \
    "--timeout-ms[Agent timeout in ms (defaults to agents.defaults.timeoutSeconds)]" \
    "--history-limit[History entries to load]"
}

_openclaw_cron_status() {
  _arguments -C \
    "--json[Output JSON]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--expect-final[Wait for final response (agent)]"
}

_openclaw_cron_list() {
  _arguments -C \
    "--all[Include disabled jobs]" \
    "--json[Output JSON]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--expect-final[Wait for final response (agent)]"
}

_openclaw_cron_add() {
  _arguments -C \
    "--name[Job name]" \
    "--description[Optional description]" \
    "--disabled[Create job disabled]" \
    "--delete-after-run[Delete one-shot job after it succeeds]" \
    "--keep-after-run[Keep one-shot job after it succeeds]" \
    "--agent[Agent id for this job]" \
    "--session[Session target (main|isolated)]" \
    "--session-key[Session key for job routing (e.g. agent:my-agent:my-session)]" \
    "--wake[Wake mode (now|next-heartbeat)]" \
    "--at[Run once at time (ISO with offset, or +duration). Use --tz for offset-less datetimes]" \
    "--every[Run every duration (e.g. 10m, 1h)]" \
    "--cron[Cron expression (5-field or 6-field with seconds)]" \
    "--tz[Timezone for cron expressions (IANA)]" \
    "--stagger[Cron stagger window (e.g. 30s, 5m)]" \
    "--exact[Disable cron staggering (set stagger to 0)]" \
    "--system-event[System event payload (main session)]" \
    "--message[Agent message payload]" \
    "--thinking[Thinking level for agent jobs (off|minimal|low|medium|high|xhigh)]" \
    "--model[Model override for agent jobs (provider/model or alias)]" \
    "--timeout-seconds[Timeout seconds for agent jobs]" \
    "--light-context[Use lightweight bootstrap context for agent jobs]" \
    "--announce[Announce summary to a chat (subagent-style)]" \
    "--deliver[Deprecated (use --announce). Announces a summary to a chat.]" \
    "--no-deliver[Disable announce delivery and skip main-session summary]" \
    "--channel[Delivery channel (last)]" \
    "--to[Delivery destination (E.164, Telegram chatId, or Discord channel/user)]" \
    "--account[Channel account id for delivery (multi-account setups)]" \
    "--best-effort-deliver[Do not fail the job if delivery fails]" \
    "--json[Output JSON]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--expect-final[Wait for final response (agent)]"
}

_openclaw_cron_rm() {
  _arguments -C \
    "--json[Output JSON]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--expect-final[Wait for final response (agent)]"
}

_openclaw_cron_enable() {
  _arguments -C \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--expect-final[Wait for final response (agent)]"
}

_openclaw_cron_disable() {
  _arguments -C \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--expect-final[Wait for final response (agent)]"
}

_openclaw_cron_runs() {
  _arguments -C \
    "--id[Job id]" \
    "--limit[Max entries (default 50)]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--expect-final[Wait for final response (agent)]"
}

_openclaw_cron_run() {
  _arguments -C \
    "--due[Run only when due (default behavior in older versions)]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--expect-final[Wait for final response (agent)]"
}

_openclaw_cron_edit() {
  _arguments -C \
    "--name[Set name]" \
    "--description[Set description]" \
    "--enable[Enable job]" \
    "--disable[Disable job]" \
    "--delete-after-run[Delete one-shot job after it succeeds]" \
    "--keep-after-run[Keep one-shot job after it succeeds]" \
    "--session[Session target (main|isolated)]" \
    "--agent[Set agent id]" \
    "--clear-agent[Unset agent and use default]" \
    "--session-key[Set session key for job routing]" \
    "--clear-session-key[Unset session key]" \
    "--wake[Wake mode (now|next-heartbeat)]" \
    "--at[Set one-shot time (ISO) or duration like 20m]" \
    "--every[Set interval duration like 10m]" \
    "--cron[Set cron expression]" \
    "--tz[Timezone for cron expressions (IANA)]" \
    "--stagger[Cron stagger window (e.g. 30s, 5m)]" \
    "--exact[Disable cron staggering (set stagger to 0)]" \
    "--system-event[Set systemEvent payload]" \
    "--message[Set agentTurn payload message]" \
    "--thinking[Thinking level for agent jobs (off|minimal|low|medium|high|xhigh)]" \
    "--model[Model override for agent jobs]" \
    "--timeout-seconds[Timeout seconds for agent jobs]" \
    "--light-context[Enable lightweight bootstrap context for agent jobs]" \
    "--no-light-context[Disable lightweight bootstrap context for agent jobs]" \
    "--announce[Announce summary to a chat (subagent-style)]" \
    "--deliver[Deprecated (use --announce). Announces a summary to a chat.]" \
    "--no-deliver[Disable announce delivery]" \
    "--channel[Delivery channel (last)]" \
    "--to[Delivery destination (E.164, Telegram chatId, or Discord channel/user)]" \
    "--account[Channel account id for delivery (multi-account setups)]" \
    "--best-effort-deliver[Do not fail job if delivery fails]" \
    "--no-best-effort-deliver[Fail job when delivery fails]" \
    "--failure-alert[Enable failure alerts for this job]" \
    "--no-failure-alert[Disable failure alerts for this job]" \
    "--failure-alert-after[Alert after N consecutive job errors]" \
    "--failure-alert-channel[Failure alert channel (last)]" \
    "--failure-alert-to[Failure alert destination]" \
    "--failure-alert-cooldown[Minimum time between alerts (e.g. 1h, 30m)]" \
    "--failure-alert-mode[Failure alert delivery mode (announce or webhook)]" \
    "--failure-alert-account-id[Account ID for failure alert channel (multi-account setups)]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--expect-final[Wait for final response (agent)]"
}

_openclaw_cron() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'status[Show cron scheduler status]' 'list[List cron jobs]' 'add[Add a cron job]' 'rm[Remove a cron job]' 'enable[Enable a cron job]' 'disable[Disable a cron job]' 'runs[Show cron run history (JSONL-backed)]' 'run[Run a cron job now (debug)]' 'edit[Edit a cron job (patch fields)]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (status) _openclaw_cron_status ;;
        (list) _openclaw_cron_list ;;
        (add) _openclaw_cron_add ;;
        (rm) _openclaw_cron_rm ;;
        (enable) _openclaw_cron_enable ;;
        (disable) _openclaw_cron_disable ;;
        (runs) _openclaw_cron_runs ;;
        (run) _openclaw_cron_run ;;
        (edit) _openclaw_cron_edit ;;
      esac
      ;;
  esac
}

_openclaw_dns_setup() {
  _arguments -C \
    "--domain[Wide-area discovery domain (e.g. openclaw.internal)]" \
    "--apply[Install/update CoreDNS config and (re)start the service (requires sudo)]"
}

_openclaw_dns() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'setup[Set up CoreDNS to serve your discovery domain for unicast DNS-SD (Wide-Area Bonjour)]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (setup) _openclaw_dns_setup ;;
      esac
      ;;
  esac
}

_openclaw_docs() {
  _arguments -C \
    
}

_openclaw_hooks_list() {
  _arguments -C \
    "--eligible[Show only eligible hooks]" \
    "--json[Output as JSON]" \
    "(--verbose -v)"{--verbose,-v}"[Show more details including missing requirements]"
}

_openclaw_hooks_info() {
  _arguments -C \
    "--json[Output as JSON]"
}

_openclaw_hooks_check() {
  _arguments -C \
    "--json[Output as JSON]"
}

_openclaw_hooks_enable() {
  _arguments -C \
    
}

_openclaw_hooks_disable() {
  _arguments -C \
    
}

_openclaw_hooks_install() {
  _arguments -C \
    "(--link -l)"{--link,-l}"[Link a local path instead of copying]" \
    "--pin[Record npm installs as exact resolved <name>@<version>]"
}

_openclaw_hooks_update() {
  _arguments -C \
    "--all[Update all tracked hooks]" \
    "--dry-run[Show what would change without writing]"
}

_openclaw_hooks() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'list[List all hooks]' 'info[Show detailed information about a hook]' 'check[Check hooks eligibility status]' 'enable[Enable a hook]' 'disable[Disable a hook]' 'install[Deprecated: install a hook pack via `openclaw plugins install`]' 'update[Deprecated: update hook packs via `openclaw plugins update`]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (list) _openclaw_hooks_list ;;
        (info) _openclaw_hooks_info ;;
        (check) _openclaw_hooks_check ;;
        (enable) _openclaw_hooks_enable ;;
        (disable) _openclaw_hooks_disable ;;
        (install) _openclaw_hooks_install ;;
        (update) _openclaw_hooks_update ;;
      esac
      ;;
  esac
}

_openclaw_webhooks_gmail_setup() {
  _arguments -C \
    "--account[Gmail account to watch]" \
    "--project[GCP project id (OAuth client owner)]" \
    "--topic[Pub/Sub topic name]" \
    "--subscription[Pub/Sub subscription name]" \
    "--label[Gmail label to watch]" \
    "--hook-url[OpenClaw hook URL]" \
    "--hook-token[OpenClaw hook token]" \
    "--push-token[Push token for gog watch serve]" \
    "--bind[gog watch serve bind host]" \
    "--port[gog watch serve port]" \
    "--path[gog watch serve path]" \
    "--include-body[Include email body snippets]" \
    "--max-bytes[Max bytes for body snippets]" \
    "--renew-minutes[Renew watch every N minutes]" \
    "--tailscale[Expose push endpoint via tailscale (funnel|serve|off)]" \
    "--tailscale-path[Path for tailscale serve/funnel]" \
    "--tailscale-target[Tailscale serve/funnel target (port, host:port, or URL)]" \
    "--push-endpoint[Explicit Pub/Sub push endpoint]" \
    "--json[Output JSON summary]"
}

_openclaw_webhooks_gmail_run() {
  _arguments -C \
    "--account[Gmail account to watch]" \
    "--topic[Pub/Sub topic path (projects/.../topics/..)]" \
    "--subscription[Pub/Sub subscription name]" \
    "--label[Gmail label to watch]" \
    "--hook-url[OpenClaw hook URL]" \
    "--hook-token[OpenClaw hook token]" \
    "--push-token[Push token for gog watch serve]" \
    "--bind[gog watch serve bind host]" \
    "--port[gog watch serve port]" \
    "--path[gog watch serve path]" \
    "--include-body[Include email body snippets]" \
    "--max-bytes[Max bytes for body snippets]" \
    "--renew-minutes[Renew watch every N minutes]" \
    "--tailscale[Expose push endpoint via tailscale (funnel|serve|off)]" \
    "--tailscale-path[Path for tailscale serve/funnel]" \
    "--tailscale-target[Tailscale serve/funnel target (port, host:port, or URL)]"
}

_openclaw_webhooks_gmail() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'setup[Configure Gmail watch + Pub/Sub + OpenClaw hooks]' 'run[Run gog watch serve + auto-renew loop]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (setup) _openclaw_webhooks_gmail_setup ;;
        (run) _openclaw_webhooks_gmail_run ;;
      esac
      ;;
  esac
}

_openclaw_webhooks() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'gmail[Gmail Pub/Sub hooks (via gogcli)]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (gmail) _openclaw_webhooks_gmail ;;
      esac
      ;;
  esac
}

_openclaw_qr() {
  _arguments -C \
    "--remote[Use gateway.remote.url and gateway.remote token/password (ignores device-pair publicUrl)]" \
    "--url[Override gateway URL used in the setup payload]" \
    "--public-url[Override gateway public URL used in the setup payload]" \
    "--token[Override gateway token for setup payload]" \
    "--password[Override gateway password for setup payload]" \
    "--setup-code-only[Print only the setup code]" \
    "--no-ascii[Skip ASCII QR rendering]" \
    "--json[Output JSON]"
}

_openclaw_clawbot_qr() {
  _arguments -C \
    "--remote[Use gateway.remote.url and gateway.remote token/password (ignores device-pair publicUrl)]" \
    "--url[Override gateway URL used in the setup payload]" \
    "--public-url[Override gateway public URL used in the setup payload]" \
    "--token[Override gateway token for setup payload]" \
    "--password[Override gateway password for setup payload]" \
    "--setup-code-only[Print only the setup code]" \
    "--no-ascii[Skip ASCII QR rendering]" \
    "--json[Output JSON]"
}

_openclaw_clawbot() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'qr[Generate an iOS pairing QR code and setup code]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (qr) _openclaw_clawbot_qr ;;
      esac
      ;;
  esac
}

_openclaw_pairing_list() {
  _arguments -C \
    "--channel[Channel (slack)]" \
    "--account[Account id (for multi-account channels)]" \
    "--json[Print JSON]"
}

_openclaw_pairing_approve() {
  _arguments -C \
    "--channel[Channel (slack)]" \
    "--account[Account id (for multi-account channels)]" \
    "--notify[Notify the requester on the same channel]"
}

_openclaw_pairing() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'list[List pending pairing requests]' 'approve[Approve a pairing code and allow that sender]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (list) _openclaw_pairing_list ;;
        (approve) _openclaw_pairing_approve ;;
      esac
      ;;
  esac
}

_openclaw_plugins_list() {
  _arguments -C \
    "--json[Print JSON]" \
    "--enabled[Only show enabled plugins]" \
    "--verbose[Show detailed entries]"
}

_openclaw_plugins_inspect() {
  _arguments -C \
    "--all[Inspect all plugins]" \
    "--json[Print JSON]"
}

_openclaw_plugins_enable() {
  _arguments -C \
    
}

_openclaw_plugins_disable() {
  _arguments -C \
    
}

_openclaw_plugins_uninstall() {
  _arguments -C \
    "--keep-files[Keep installed files on disk]" \
    "--keep-config[Deprecated alias for --keep-files]" \
    "--force[Skip confirmation prompt]" \
    "--dry-run[Show what would be removed without making changes]"
}

_openclaw_plugins_install() {
  _arguments -C \
    "(--link -l)"{--link,-l}"[Link a local path instead of copying]" \
    "--pin[Record npm installs as exact resolved <name>@<version>]" \
    "--marketplace[Install a Claude marketplace plugin from a local repo/path or git/GitHub source]"
}

_openclaw_plugins_update() {
  _arguments -C \
    "--all[Update all tracked plugins and hook packs]" \
    "--dry-run[Show what would change without writing]"
}

_openclaw_plugins_doctor() {
  _arguments -C \
    
}

_openclaw_plugins_marketplace_list() {
  _arguments -C \
    "--json[Print JSON]"
}

_openclaw_plugins_marketplace() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'list[List plugins published by a marketplace source]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (list) _openclaw_plugins_marketplace_list ;;
      esac
      ;;
  esac
}

_openclaw_plugins() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'list[List discovered plugins]' 'inspect[Inspect plugin details]' 'enable[Enable a plugin in config]' 'disable[Disable a plugin in config]' 'uninstall[Uninstall a plugin]' 'install[Install a plugin or hook pack (path, archive, npm spec, clawhub:package, or marketplace entry)]' 'update[Update installed plugins and tracked hook packs]' 'doctor[Report plugin load issues]' 'marketplace[Inspect Claude-compatible plugin marketplaces]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (list) _openclaw_plugins_list ;;
        (inspect) _openclaw_plugins_inspect ;;
        (enable) _openclaw_plugins_enable ;;
        (disable) _openclaw_plugins_disable ;;
        (uninstall) _openclaw_plugins_uninstall ;;
        (install) _openclaw_plugins_install ;;
        (update) _openclaw_plugins_update ;;
        (doctor) _openclaw_plugins_doctor ;;
        (marketplace) _openclaw_plugins_marketplace ;;
      esac
      ;;
  esac
}

_openclaw_channels_list() {
  _arguments -C \
    "--no-usage[Skip model provider usage/quota snapshots]" \
    "--json[Output JSON]"
}

_openclaw_channels_status() {
  _arguments -C \
    "--probe[Probe channel credentials]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_channels_capabilities() {
  _arguments -C \
    "--channel[Channel (all|telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line)]" \
    "--account[Account id (only with --channel)]" \
    "--target[Channel target for permission audit (Discord channel:<id>)]" \
    "--timeout[Timeout in ms]" \
    "--json[Output JSON]"
}

_openclaw_channels_resolve() {
  _arguments -C \
    "--channel[Channel (telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line)]" \
    "--account[Account id (accountId)]" \
    "--kind[Target kind (auto|user|group)]" \
    "--json[Output JSON]"
}

_openclaw_channels_logs() {
  _arguments -C \
    "--channel[Channel (all|telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line)]" \
    "--lines[Number of lines (default: 200)]" \
    "--json[Output JSON]"
}

_openclaw_channels_add() {
  _arguments -C \
    "--channel[Channel (telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line)]" \
    "--account[Account id (default when omitted)]" \
    "--name[Display name for this account]" \
    "--token[Bot token (Telegram/Discord)]" \
    "--private-key[Nostr private key (nsec... or hex)]" \
    "--token-file[Bot token file (Telegram)]" \
    "--bot-token[Slack bot token (xoxb-...)]" \
    "--app-token[Slack app token (xapp-...)]" \
    "--signal-number[Signal account number (E.164)]" \
    "--cli-path[CLI path (signal-cli or imsg)]" \
    "--db-path[iMessage database path]" \
    "--service[iMessage service (imessage|sms|auto)]" \
    "--region[iMessage region (for SMS)]" \
    "--auth-dir[WhatsApp auth directory override]" \
    "--http-url[Signal HTTP daemon base URL]" \
    "--http-host[Signal HTTP host]" \
    "--http-port[Signal HTTP port]" \
    "--webhook-path[Webhook path (Google Chat/BlueBubbles)]" \
    "--webhook-url[Google Chat webhook URL]" \
    "--audience-type[Google Chat audience type (app-url|project-number)]" \
    "--audience[Google Chat audience value (app URL or project number)]" \
    "--homeserver[Matrix homeserver URL]" \
    "--user-id[Matrix user ID]" \
    "--access-token[Matrix access token]" \
    "--password[Matrix password]" \
    "--device-name[Matrix device name]" \
    "--initial-sync-limit[Matrix initial sync limit]" \
    "--ship[Tlon ship name (~sampel-palnet)]" \
    "--url[Tlon ship URL]" \
    "--relay-urls[Nostr relay URLs (comma-separated)]" \
    "--code[Tlon login code]" \
    "--group-channels[Tlon group channels (comma-separated)]" \
    "--dm-allowlist[Tlon DM allowlist (comma-separated ships)]" \
    "--auto-discover-channels[Tlon auto-discover group channels]" \
    "--no-auto-discover-channels[Disable Tlon auto-discovery]" \
    "--use-env[Use env token (default account only)]"
}

_openclaw_channels_remove() {
  _arguments -C \
    "--channel[Channel (telegram|whatsapp|discord|irc|googlechat|slack|signal|imessage|line)]" \
    "--account[Account id (default when omitted)]" \
    "--delete[Delete config entries (no prompt)]"
}

_openclaw_channels_login() {
  _arguments -C \
    "--channel[Channel alias (auto when only one is configured)]" \
    "--account[Account id (accountId)]" \
    "--verbose[Verbose connection logs]"
}

_openclaw_channels_logout() {
  _arguments -C \
    "--channel[Channel alias (auto when only one is configured)]" \
    "--account[Account id (accountId)]"
}

_openclaw_channels() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'list[List configured channels + auth profiles]' 'status[Show gateway channel status (use status --deep for local)]' 'capabilities[Show provider capabilities (intents/scopes + supported features)]' 'resolve[Resolve channel/user names to IDs]' 'logs[Show recent channel logs from the gateway log file]' 'add[Add or update a channel account]' 'remove[Disable or delete a channel account]' 'login[Link a channel account (if supported)]' 'logout[Log out of a channel session (if supported)]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (list) _openclaw_channels_list ;;
        (status) _openclaw_channels_status ;;
        (capabilities) _openclaw_channels_capabilities ;;
        (resolve) _openclaw_channels_resolve ;;
        (logs) _openclaw_channels_logs ;;
        (add) _openclaw_channels_add ;;
        (remove) _openclaw_channels_remove ;;
        (login) _openclaw_channels_login ;;
        (logout) _openclaw_channels_logout ;;
      esac
      ;;
  esac
}

_openclaw_directory_self() {
  _arguments -C \
    "--channel[Channel (auto when only one is configured)]" \
    "--account[Account id (accountId)]" \
    "--json[Output JSON]"
}

_openclaw_directory_peers_list() {
  _arguments -C \
    "--channel[Channel (auto when only one is configured)]" \
    "--account[Account id (accountId)]" \
    "--json[Output JSON]" \
    "--query[Optional search query]" \
    "--limit[Limit results]"
}

_openclaw_directory_peers() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'list[List peers]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (list) _openclaw_directory_peers_list ;;
      esac
      ;;
  esac
}

_openclaw_directory_groups_list() {
  _arguments -C \
    "--channel[Channel (auto when only one is configured)]" \
    "--account[Account id (accountId)]" \
    "--json[Output JSON]" \
    "--query[Optional search query]" \
    "--limit[Limit results]"
}

_openclaw_directory_groups_members() {
  _arguments -C \
    "--group-id[Group id]" \
    "--channel[Channel (auto when only one is configured)]" \
    "--account[Account id (accountId)]" \
    "--json[Output JSON]" \
    "--limit[Limit results]"
}

_openclaw_directory_groups() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'list[List groups]' 'members[List group members]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (list) _openclaw_directory_groups_list ;;
        (members) _openclaw_directory_groups_members ;;
      esac
      ;;
  esac
}

_openclaw_directory() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'self[Show the current account user]' 'peers[Peer directory (contacts/users)]' 'groups[Group directory]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (self) _openclaw_directory_self ;;
        (peers) _openclaw_directory_peers ;;
        (groups) _openclaw_directory_groups ;;
      esac
      ;;
  esac
}

_openclaw_security_audit() {
  _arguments -C \
    "--deep[Attempt live Gateway probe (best-effort)]" \
    "--token[Use explicit gateway token for deep probe auth]" \
    "--password[Use explicit gateway password for deep probe auth]" \
    "--fix[Apply safe fixes (tighten defaults + chmod state/config)]" \
    "--json[Print JSON]"
}

_openclaw_security() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'audit[Audit config + local state for common security foot-guns]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (audit) _openclaw_security_audit ;;
      esac
      ;;
  esac
}

_openclaw_secrets_reload() {
  _arguments -C \
    "--json[Output JSON]" \
    "--url[Gateway WebSocket URL (defaults to gateway.remote.url when configured)]" \
    "--token[Gateway token (if required)]" \
    "--timeout[Timeout in ms]" \
    "--expect-final[Wait for final response (agent)]"
}

_openclaw_secrets_audit() {
  _arguments -C \
    "--check[Exit non-zero when findings are present]" \
    "--allow-exec[Allow exec SecretRef resolution during audit (may execute provider commands)]" \
    "--json[Output JSON]"
}

_openclaw_secrets_configure() {
  _arguments -C \
    "--apply[Apply changes immediately after preflight]" \
    "--yes[Skip apply confirmation prompt]" \
    "--providers-only[Configure secrets.providers only, skip credential mapping]" \
    "--skip-provider-setup[Skip provider setup and only map credential fields to existing providers]" \
    "--agent[Agent id for auth-profiles targets (default: configured default agent)]" \
    "--allow-exec[Allow exec SecretRef preflight checks (may execute provider commands)]" \
    "--plan-out[Write generated plan JSON to a file]" \
    "--json[Output JSON]"
}

_openclaw_secrets_apply() {
  _arguments -C \
    "--from[Path to plan JSON]" \
    "--dry-run[Validate/preflight only]" \
    "--allow-exec[Allow exec SecretRef checks (may execute provider commands)]" \
    "--json[Output JSON]"
}

_openclaw_secrets() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'reload[Re-resolve secret references and atomically swap runtime snapshot]' 'audit[Audit plaintext secrets, unresolved refs, and precedence drift]' 'configure[Interactive secrets helper (provider setup + SecretRef mapping + preflight)]' 'apply[Apply a previously generated secrets plan]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (reload) _openclaw_secrets_reload ;;
        (audit) _openclaw_secrets_audit ;;
        (configure) _openclaw_secrets_configure ;;
        (apply) _openclaw_secrets_apply ;;
      esac
      ;;
  esac
}

_openclaw_skills_search() {
  _arguments -C \
    "--limit[Max results]" \
    "--json[Output as JSON]"
}

_openclaw_skills_install() {
  _arguments -C \
    "--version[Install a specific version]" \
    "--force[Overwrite an existing workspace skill]"
}

_openclaw_skills_update() {
  _arguments -C \
    "--all[Update all tracked ClawHub skills]"
}

_openclaw_skills_list() {
  _arguments -C \
    "--json[Output as JSON]" \
    "--eligible[Show only eligible (ready to use) skills]" \
    "(--verbose -v)"{--verbose,-v}"[Show more details including missing requirements]"
}

_openclaw_skills_info() {
  _arguments -C \
    "--json[Output as JSON]"
}

_openclaw_skills_check() {
  _arguments -C \
    "--json[Output as JSON]"
}

_openclaw_skills() {
  local -a commands
  local -a options
  
  _arguments -C \
     \
    "1: :_values 'command' 'search[Search ClawHub skills]' 'install[Install a skill from ClawHub into the active workspace]' 'update[Update ClawHub-installed skills in the active workspace]' 'list[List all available skills]' 'info[Show detailed information about a skill]' 'check[Check which skills are ready vs missing requirements]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (search) _openclaw_skills_search ;;
        (install) _openclaw_skills_install ;;
        (update) _openclaw_skills_update ;;
        (list) _openclaw_skills_list ;;
        (info) _openclaw_skills_info ;;
        (check) _openclaw_skills_check ;;
      esac
      ;;
  esac
}

_openclaw_update_wizard() {
  _arguments -C \
    "--timeout[Timeout for each update step in seconds (default: 1200)]"
}

_openclaw_update_status() {
  _arguments -C \
    "--json[Output result as JSON]" \
    "--timeout[Timeout for update checks in seconds (default: 3)]"
}

_openclaw_update() {
  local -a commands
  local -a options
  
  _arguments -C \
    "--json[Output result as JSON]" \
    "--no-restart[Skip restarting the gateway service after a successful update]" \
    "--dry-run[Preview update actions without making changes]" \
    "--channel[Persist update channel (git + npm)]" \
    "--tag[Override the package target for this update (dist-tag, version, or package spec)]" \
    "--timeout[Timeout for each update step in seconds (default: 1200)]" \
    "--yes[Skip confirmation prompts (non-interactive)]" \
    "1: :_values 'command' 'wizard[Interactive update wizard]' 'status[Show update channel and version status]'" \
    "*::arg:->args"

  case $state in
    (args)
      case $line[1] in
        (wizard) _openclaw_update_wizard ;;
        (status) _openclaw_update_status ;;
      esac
      ;;
  esac
}


compdef _openclaw_root_completion openclaw
