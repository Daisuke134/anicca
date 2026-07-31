# Appeeky — Keyword Intelligence

Keyword research, volume scoring, difficulty analysis, and competitive keyword tools.

**Base URL:** `https://api.appeeky.com`
**Auth:** `X-API-Key` header (REST) or `Authorization: Bearer` (MCP)

## Endpoints

### Keyword Suggestions

Get Apple Search autocomplete suggestions with volume and difficulty scores.

```bash
GET /v1/keywords/suggestions?term=meditation&country=us
```

**MCP:** `get_keyword_suggestions(term, country)`

**Use in skills:** `keyword-research`, `localization`

**Example:**
```bash
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/keywords/suggestions?term=meditation&country=us"
```

**Response:**
```json
{
  "data": {
    "term": "meditation",
    "suggestions": [
      "meditation app",
      "meditation timer",
      "meditation music",
      "meditation for beginners",
      "meditation and sleep"
    ]
  }
}
```

**Tips:**
- Try different seed terms to discover unexpected keywords
- Use category-specific terms ("fitness tracker" vs "health app")
- Try problem-based terms ("can't sleep", "stress relief")
- Suggestions reflect real user search behavior

### Keyword Metrics

Search volume score and difficulty score for a specific keyword.

```bash
GET /v1/keywords/metrics?keyword=meditation&country=us
```

**MCP:** `get_keyword_metrics(keyword, country)`

**Use in skills:** `keyword-research`, `aso-audit`, `metadata-optimization`

**Response includes:**
- `volumeScore` — Relative search volume (1-100)
- `difficulty` — Competition level (1-100)
- `resultCount` — Number of apps returned for this search
- `topApps` — Top-ranking apps for this keyword

**Interpreting scores:**

| Volume | Meaning |
|--------|---------|
| 70-100 | Very high — competitive but high traffic |
| 40-69 | Medium — good balance of traffic and competition |
| 20-39 | Low-medium — niche but easier to rank |
| 1-19 | Low — very niche, easy to rank |

| Difficulty | Meaning |
|-----------|---------|
| 70-100 | Very hard — dominated by top apps |
| 40-69 | Medium — achievable with good ASO |
| 20-39 | Easy-medium — good opportunity |
| 1-19 | Easy — low competition |

### Keyword Rankings

All apps ranking for a specific keyword with metadata.

```bash
GET /v1/keywords/ranks?keyword=meditation&country=us
```

**MCP:** `get_keyword_ranks(keyword, country)`

**Use in skills:** `keyword-research`, `competitor-analysis`

**Response:** Ranked list of apps with position, title, rating, reviews, and developer.

### Keyword Comparison

Compare keyword overlap between two apps — find gaps and shared keywords.

```bash
GET /v1/keywords/compare?appId1=544007664&appId2=493145008&country=us
```

**MCP:** `compare_keywords(app_id_1, app_id_2, country)`

**Use in skills:** `competitor-analysis`, `keyword-research`

**Response includes:**
- `shared` — Keywords both apps rank for
- `onlyApp1` — Keywords only the first app ranks for
- `onlyApp2` — Keywords only the second app ranks for (keyword gaps)
- `overlap` — Overlap percentage

### Trending Keywords

Keywords with the fastest-growing reach in the App Store.

```bash
GET /v1/keywords/trending?country=us&days=7&limit=50
```

**MCP:** `get_trending_keywords(country, days, limit)`

**Use in skills:** `keyword-research`, `app-launch`

**Response includes:**
- `keyword` — The trending keyword
- `growthPercent` — Growth rate
- `volumeScore` — Current search volume
- `difficulty` — Competition level

### Track Keyword

Add a keyword to the daily scraping pipeline for historical tracking.

```bash
POST /v1/keywords/track
Content-Type: application/json

{"keyword": "meditation app", "country": "us"}
```

**MCP:** `track_keyword(keyword, country)`

**Use in skills:** `keyword-research`, `aso-audit`

## Common Workflows

### Full keyword research for a new app

```bash
# 1. Get suggestions from seed terms
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/keywords/suggestions?term=meditation&country=us"

curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/keywords/suggestions?term=mindfulness&country=us"

curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/keywords/suggestions?term=sleep+sounds&country=us"

# 2. Get metrics for top candidates
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/keywords/metrics?keyword=meditation+app&country=us"

# 3. See who ranks for target keywords
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/keywords/ranks?keyword=meditation+app&country=us"

# 4. Compare with top competitor
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/keywords/compare?appId1=YOUR_ID&appId2=COMPETITOR_ID&country=us"

# 5. Track important keywords
curl -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"keyword":"meditation app","country":"us"}' \
  "https://api.appeeky.com/v1/keywords/track"
```

### Find keyword opportunities (high volume, low difficulty)

Use the MCP tool `aso_find_opportunities` or manually:

```bash
# Get suggestions
# → For each suggestion, get metrics
# → Filter: volumeScore > 40 AND difficulty < 40
# → Sort by (volumeScore - difficulty) descending
# → These are your best opportunities
```

### Monitor keyword performance weekly

```bash
# Check current rankings
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/apps/$APP_ID/keywords?country=us"

# Check trends for key terms
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/apps/$APP_ID/keywords/trends?keyword=meditation&country=us&days=30"

# Check what's trending (new opportunities?)
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/keywords/trending?country=us&days=7"
```

## Credit Costs

| Endpoint | Credits |
|----------|---------|
| Keyword suggestions | 1 |
| Keyword metrics | 2 |
| Keyword rankings | 2 |
| Keyword comparison | 3 |
| Trending keywords | 2 |
| Track keyword | 1 |
