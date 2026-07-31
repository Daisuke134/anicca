# Appeeky — Market Intelligence

Category charts, featured apps, new releases, trending data, download estimates, and chart movement tracking.

**Base URL:** `https://api.appeeky.com`
**Auth:** `X-API-Key` header (REST) or `Authorization: Bearer` (MCP)

## Endpoints

### Market Movers

Top gainers, losers, new entries, and apps that dropped out of the charts. Compares the two most recent chart snapshots (taken every 6 hours).

```bash
GET /v1/market/movers?country=us&chart=top-free&genre=all&limit=10
```

**MCP:** `get_market_movers(country, chart, genre, limit)`

**Use in skills:** `market-movers`, `market-pulse`, `competitor-analysis`

**Parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `country` | `us` | ISO country code |
| `chart` | `top-free` | `top-free`, `top-paid`, `top-grossing` |
| `genre` | `all` | Genre ID or `all` for overall chart |
| `limit` | `10` | Max results per section (1-25) |

**Response sections:** `topGainers`, `topLosers`, `newEntries`, `droppedOut`

Each item includes: `appId`, `appName`, `developer`, `iconUrl`, `genreId`, `genreName`, `currentRank`, `previousRank`, `rankChange`, `rating`, `reviewCount`.

### Market Activity

Live feed of all significant chart movements (3+ position changes, new entries, exits). Sorted by magnitude of change.

```bash
GET /v1/market/activity?country=us&chart=top-free&genre=all&limit=25
```

**MCP:** `get_market_activity(country, chart, genre, limit)`

**Use in skills:** `market-movers`, `market-pulse`, `competitor-analysis`

**Activity types:**

| Type | Description |
|------|-------------|
| `new_entry` | App appeared in top 100 (wasn't in previous snapshot) |
| `rank_up` | App improved by 3+ positions |
| `rank_down` | App dropped by 3+ positions |
| `dropped_out` | App left the top 100 |

### Category Charts

Top Free, Top Paid, and Top Grossing apps per category.

```bash
GET /v1/categories/:genreId/top?country=us&chart=top-free&limit=25
```

**MCP:** `get_category_top(genre_id, country, chart, limit)`

**Use in skills:** `competitor-analysis`, `app-launch`, `app-marketing-context`

**Genre IDs:**

| ID | Category | ID | Category |
|----|----------|----|----------|
| 6000 | Business | 6014 | Games |
| 6002 | Utilities | 6015 | Finance |
| 6005 | Social Networking | 6016 | Entertainment |
| 6007 | Productivity | 6017 | Education |
| 6008 | Photo & Video | 6012 | Lifestyle |
| 6013 | Health & Fitness | 6024 | Shopping |

Use `all` for overall chart (no category filter).

### Downloads to Top

Estimated daily downloads needed to reach specific chart positions (#1, #5, #10, #25, #50, #100).

```bash
GET /v1/categories/:genreId/downloads-to-top?country=us&chart=top-free
```

**MCP:** `get_downloads_to_top(genre_id, country, chart)`

**Use in skills:** `ua-campaign`, `app-launch`, `app-analytics`

**Example:**
```bash
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/categories/6014/downloads-to-top?country=us&chart=top-free"
```

**Response:**
```json
{
  "data": {
    "category": { "id": "6014", "name": "Games" },
    "tiers": [
      { "rank": 1, "estimatedDailyDownloads": 1500000, "app": { "name": "..." } },
      { "rank": 5, "estimatedDailyDownloads": 400000, "app": { "name": "..." } },
      { "rank": 10, "estimatedDailyDownloads": 227000, "app": null },
      { "rank": 25, "estimatedDailyDownloads": 107000, "app": null },
      { "rank": 50, "estimatedDailyDownloads": 60000, "app": null },
      { "rank": 100, "estimatedDailyDownloads": 34000, "app": null }
    ]
  }
}
```

### Featured Apps

Apps currently featured on the App Store Today tab — App of the Day, Game of the Day, and editorial collections.

```bash
GET /v1/featured?country=us
```

**MCP:** `get_featured_apps(country)`

**Use in skills:** `app-store-featured`, `competitor-analysis`

**Response includes:**
- `appOfTheDay` — Today's featured app
- `gameOfTheDay` — Today's featured game
- `groups` — Editorial collections and curated lists

### New Releases

Recently released apps from Apple RSS.

```bash
GET /v1/new-releases?country=us&maxDays=7
```

**MCP:** `get_new_releases(country, max_days)`

**Use in skills:** `app-launch`, `competitor-analysis`

### Discovery Feed

Curated discovery feed combining new releases and trending apps.

```bash
GET /v1/discover?country=us
```

**MCP:** `discover(country)`

**Use in skills:** `app-marketing-context`, `competitor-analysis`

### New #1 Apps

Apps that recently reached #1 in their category.

```bash
GET /v1/discover/new-number-1?country=us
```

**MCP:** `get_new_number_1(country)`

**Use in skills:** `competitor-analysis`, `app-launch`

### List Categories

All available App Store categories with genre IDs.

```bash
GET /v1/categories
```

**MCP:** `get_categories()`

## Common Workflows

### Market research for a new app idea

```bash
# 1. What's the competitive landscape?
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/categories/6013/top?country=us&chart=top-free&limit=10"

# 2. How many downloads to compete?
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/categories/6013/downloads-to-top?country=us&chart=top-free"

# 3. What's trending?
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/keywords/trending?country=us&days=7"

# 4. Any recent launches in the space?
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/new-releases?country=us&maxDays=14"

# 5. What's Apple featuring?
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/featured?country=us"
```

### Track market position weekly

```bash
# Who's gaining and losing in your category?
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/market/movers?country=us&chart=top-free&genre=$GENRE_ID&limit=10"

# Full activity feed
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/market/activity?country=us&chart=top-free&genre=$GENRE_ID"

# Your category chart position
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/apps/$APP_ID/country-rankings?chart=top-free"

# Downloads needed to move up
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/categories/$GENRE_ID/downloads-to-top?country=us"

# New competitors entering the market
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/new-releases?country=us&maxDays=7"

# Any new #1 apps in your category?
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/discover/new-number-1?country=us"
```

## Credit Costs

| Endpoint | Credits |
|----------|---------|
| Market movers | 3 |
| Market activity | 2 |
| Category charts | 2 |
| Downloads to top | 2 |
| Featured apps | 3 |
| New releases | 2 |
| Discovery feed | 2 |
| New #1 apps | 2 |
| List categories | 1 |
