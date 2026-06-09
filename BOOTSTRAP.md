# BOOTSTRAP.md — First-Run Setup

⚠️ **Complete this checklist before enabling heartbeats or cron jobs.**
Heartbeats cost money on every cycle. Running them before setup is complete wastes credits and produces errors.

Felix will walk through this checklist on first conversation. Once complete, Felix deletes this file.

---

## Step 1: Set Your Model

Felix works best on Claude. Set your model in OpenClaw config:

```yaml
agent:
  model: anthropic/claude-sonnet-4-5   # Recommended default
  # model: anthropic/claude-opus-4-5   # For complex reasoning (costs more)
```

⚠️ **Do NOT use GPT-4.1-mini or other cheap models as default.** Felix's personality, memory system, and autonomous behaviors require a capable model. Sonnet is the minimum recommended tier. Using weaker models will cause heartbeat failures, personality degradation, and wasted credits.

**To change model:** Run `openclaw config` or edit your agent config directly.

## Step 2: Create Memory Structure

Run this to scaffold the memory directories Felix needs:

```bash
# From your OpenClaw workspace directory (usually ~/clawd/)
mkdir -p ~/life/{projects,areas/{people,companies},resources,archives}
mkdir -p memory
touch MEMORY.md
touch ~/life/index.md

# Create today's daily note
echo "# $(date +%Y-%m-%d)" > "memory/$(date +%Y-%m-%d).md"
```

Without these directories, Felix's heartbeat will fail silently when trying to write facts and daily notes.

## Step 3: Configure Your Identity

Edit these files with your business details:

- **IDENTITY.md** — Your company name, revenue target, key products
- **HEARTBEAT.md** — Your production sites, monitoring targets, specific checks
- **AGENTS.md** — Your available tools and API keys (use the Access table)

## Step 4: Set Up Core Integrations

Check which tools you have and mark them in AGENTS.md:

| Integration | Required? | How to Set Up |
|------------|-----------|---------------|
| Anthropic API key | ✅ Required | Set in OpenClaw auth config |
| Stripe | Optional | `~/.config/stripe/` — for revenue tracking |
| GitHub (`gh`) | Optional | `brew install gh && gh auth login` |
| Email (himalaya) | Optional | Configure `~/.config/himalaya/config.toml` |
| X/Twitter (bird) | Optional | Export browser cookies to `~/.config/bird/` |
| OpenAI (Codex) | Optional | For coding agent delegation |
| Brave Search | Optional | For web research |

**You don't need everything to start.** Felix works with just the Anthropic key. Add integrations as you need them.

## Step 5: Enable Heartbeats

Only after completing steps 1-4:

```bash
openclaw cron add --schedule "*/5 * * * *" --task "Run HEARTBEAT.md"
```

Start with every 5 minutes (not 3) until you're confident things are working. You can tighten the interval later.

## Step 6: Verify Everything Works

Ask Felix:
1. "What model are you running on?" — Should say Claude Sonnet or Opus
2. "Write a test note to today's daily notes" — Should succeed without errors
3. "Check if ~/life/ exists" — Should show the PARA structure
4. "Run through your heartbeat checklist" — Should complete without file-not-found errors

---

## After Setup

Once all steps are complete, tell Felix: **"Bootstrap is done, delete BOOTSTRAP.md"**

Felix will delete this file and switch to normal operating mode.
