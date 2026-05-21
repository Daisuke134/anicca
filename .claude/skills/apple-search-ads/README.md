# 🍎 Apple Search Ads CLI

> **The missing command-line interface for Apple Search Ads.** Manage campaigns, keywords, and reporting using Apple's recommended 4-campaign structure.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Apple Ads API v5](https://img.shields.io/badge/Apple%20Ads%20API-v5-black.svg)](https://developer.apple.com/documentation/apple_ads)

```bash
# Add keywords with automatic routing
$ asa keywords add "photo editor,image filter" --type category

✓ Added 2 keywords to Category campaign (exact match)
✓ Added 2 keywords to Discovery campaign (broad match)
✓ Added 2 negative keywords to Discovery (prevents overlap)
```

## ✨ Features

- **🎯 4-Campaign Structure** — Implements Apple's best practices with Brand, Category, Competitor, and Discovery campaigns
- **🔀 Smart Keyword Routing** — Add keywords once; they're automatically distributed to the right campaigns with the right match types
- **📈 Automated Optimization** — One command analyzes Discovery, promotes winners, and blocks losers
- **📊 Rich Reporting** — Performance summaries, keyword reports, search term analysis, and impression share
- **🔒 Dry-Run Mode** — Preview every change before it happens
- **🤖 Claude Code Integration** — Includes SKILL.md for AI-assisted campaign management

## 🚀 Quick Start

### Installation

```bash
# Clone the repo
git clone https://github.com/cameronehrlich/apple-search-ads-cli.git
cd apple-search-ads-cli

# Run with uv (recommended, no install needed)
uv run asa --help

# Or install with pip
pip install -e .
asa --help
```

### Setup

```bash
# Configure your Apple Ads API credentials
asa config setup

# Test connection
asa config test

# Audit your existing campaigns
asa campaigns audit
```

<details>
<summary>📝 Getting API Credentials</summary>

1. Go to [Apple Ads](https://ads.apple.com/) → **Account Settings** → **API**
2. Create an API user with appropriate permissions
3. Generate an EC key pair:
   ```bash
   openssl ecparam -genkey -name prime256v1 -noout -out private-key.pem
   openssl ec -in private-key.pem -pubout -out public-key.pem
   ```
4. Upload the public key to Apple Ads dashboard
5. Note your **Client ID**, **Team ID**, **Key ID**, and **Org ID**

</details>

## 📖 Usage

### Campaign Management

```bash
# List all campaigns
asa campaigns list

# Audit against Apple's recommendations
asa campaigns audit --verbose

# Create the 4-campaign structure
asa campaigns setup --countries US --budget 50 --dry-run
asa campaigns setup --countries US --budget 50

# Pause/enable campaigns
asa campaigns pause --all
asa campaigns enable 12345678
```

### Keywords

```bash
# Add keywords (automatically routes to correct campaigns)
asa keywords add "my app,myapp" --type brand
asa keywords add "photo editor,image filter" --type category
asa keywords add "vsco,snapseed" --type competitor

# Block irrelevant terms
asa keywords add-negatives "auto clicker,testflight,crypto" --all

# Promote winning keywords from Discovery
asa keywords promote "best photo app" --target category

# List and filter keywords
asa keywords list --campaign 12345
asa keywords list --filter "photo" --status ACTIVE
```

### Reporting

```bash
# Performance summary
asa reports summary --days 7

# Keyword performance (sortable)
asa reports keywords --sort cpa

# Search term analysis
asa reports search-terms --winners    # Terms worth promoting
asa reports search-terms --negatives  # Terms to block

# Impression share / Share of Voice
asa reports impression-share --all
```

### Automated Optimization

The `optimize` command is your weekly campaign maintenance in one line:

```bash
# Preview changes
asa optimize --dry-run

# Run with confirmation
asa optimize

# Fully automated (for cron jobs)
asa optimize --auto-approve
```

**What it does:**
1. Analyzes Discovery search terms (last 14 days)
2. Identifies **winners**: ≥2 installs, CPA ≤ $5
3. Identifies **losers**: ≥$1 spend, 0 installs
4. Promotes winners → exact match in target campaign + negative in Discovery
5. Blocks losers → negative in all managed campaigns

```bash
# Customize thresholds
asa optimize --days 7 --cpa-threshold 3.00 --min-installs 3 --min-spend 2.00
```

## 🏗️ Campaign Structure

Apple recommends a **4-campaign structure** that separates intent and controls costs:

| Campaign | Purpose | Match Type | Search Match |
|----------|---------|------------|--------------|
| **Brand** | Your app/company name | Exact | OFF |
| **Category** | What your app does | Exact | OFF |
| **Competitor** | Other apps users might try | Exact | OFF |
| **Discovery** | Find new keywords | Broad | ON |

### How Keyword Routing Works

When you run `asa keywords add "term" --type category`:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   "term" ──┬──► Category Campaign (EXACT)                       │
│            │    Bids on exact matches only                      │
│            │                                                    │
│            ├──► Discovery Campaign (BROAD)                      │
│            │    Finds related search terms                      │
│            │                                                    │
│            └──► Discovery Campaign (NEGATIVE)                   │
│                 Prevents bidding on exact term in Discovery     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

This ensures:
- ✅ Maximum control over high-value exact terms
- ✅ Continued discovery of related search terms
- ✅ No duplicate spend on the same intent

## 📁 Configuration

Configuration is stored in `~/.asa-cli/`:

```
~/.asa-cli/
├── credentials.json    # API credentials (chmod 600)
└── config.json         # App settings (ID, name, countries, default bid)
```

## 🔧 API Behavior

| Feature | Behavior |
|---------|----------|
| **Error Handling** | Reports both successes and errors; duplicates don't fail the operation |
| **Authentication** | Auto-refreshes expired tokens with up to 2 retries |
| **Pagination** | Automatically handles large result sets (>1000 items) |
| **Rate Limiting** | Respects Apple's API limits |

## 🤖 Claude Code Integration

This CLI includes a `SKILL.md` file for use with [Claude Code](https://claude.ai/code). When loaded, Claude can manage your Apple Search Ads campaigns conversationally:

```
You: Add some category keywords for a photo editing app
Claude: [Runs asa keywords add "photo editor,image filter,picture effects" --type category]
```

## 📚 Documentation

- [Apple Search Ads Best Practices](https://ads.apple.com/app-store/best-practices/campaign-structure)
- [Apple Ads API Documentation](https://developer.apple.com/documentation/apple_ads)
- [SKILL.md](SKILL.md) — Full command reference for Claude Code

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

[MIT](LICENSE) © Cameron Ehrlich
