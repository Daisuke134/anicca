# Appeeky — App Store Connect Metrics

Synced Sales and Trends data from your connected App Store Connect account — real downloads, revenue, IAPs, and subscriptions. No ASC credentials needed per request; data is synced nightly into Appeeky.

**Base URL:** `https://api.appeeky.com`
**Auth:** `X-API-Key` header (REST) or `Authorization: Bearer` (MCP)
**Plan:** Indie or higher — 2 credits per request

> **Requires:** Connect your ASC API key and Vendor Number in [appeeky.com → Settings → Integrations](https://appeeky.com). Data syncs nightly (and on manual sync). Up to 90 days of history.

## Why Use This vs. Appeeky Estimates

| Data | Appeeky Connect | Appeeky Intelligence |
|------|----------------|---------------------|
| Downloads | **Exact** (from ASC) | Estimated |
| Revenue | **Exact** (from ASC) | Estimated |
| IAP count | **Exact** (from ASC) | Not available |
| Subscriptions | **Exact** snapshot | Not available |
| Free trials | **Exact** snapshot | Not available |
| Competitor data | ✗ | ✓ |
| Any app | Own apps only | Any app |

## Endpoints

### Overview Metrics

Totals and per-app breakdown for a date range.

```bash
GET /v1/connect/metrics?from=YYYY-MM-DD&to=YYYY-MM-DD&appId=optional
```

**Parameters:**

| Name | Default | Description |
|------|---------|-------------|
| `from` | 30 days ago | Start date `YYYY-MM-DD` |
| `to` | today | End date `YYYY-MM-DD` |
| `appId` | — | Optional: filter to one app |

**Example:**
```bash
curl "https://api.appeeky.com/v1/connect/metrics?from=2026-02-19&to=2026-03-21" \
  -H "X-API-Key: $KEY"
```

**Response:**
```json
{
  "data": {
    "from": "2026-02-19",
    "to": "2026-03-21",
    "totals": {
      "downloads": 1250,
      "revenue": 89.5,
      "subscriptions": 42,
      "trials": 12,
      "iap_count": 320
    },
    "apps": [
      {
        "appId": "6759740679",
        "appName": "Voice Tape Record",
        "downloads": 1100,
        "revenue": 75.2,
        "subscriptions": 38,
        "trials": 10,
        "iap_count": 280
      }
    ],
    "rows": [
      {
        "app_apple_id": "6759740679",
        "app_name": "Voice Tape Record",
        "metric_date": "2026-03-20",
        "downloads": 45,
        "revenue": 3.2,
        "subscriptions": 2,
        "trials": 0,
        "iap_count": 12
      }
    ]
  }
}
```

**Use in skills:** `asc-metrics`, `app-analytics`, `monetization-strategy`, `retention-optimization`

### List Apps with Metrics

Returns app IDs that have synced metrics data.

```bash
GET /v1/connect/metrics/apps
```

**Use in skills:** `asc-metrics`

### App Detail (Daily Series + Countries)

Daily time series and country/territory breakdown for one app.

```bash
GET /v1/connect/metrics/apps/:appId?from=YYYY-MM-DD&to=YYYY-MM-DD
```

**Parameters:**

| Name | Default | Description |
|------|---------|-------------|
| `appId` | required | App Store Connect numeric ID |
| `from` | 90 days ago | Start date `YYYY-MM-DD` |
| `to` | today | End date `YYYY-MM-DD` |

**Example:**
```bash
curl "https://api.appeeky.com/v1/connect/metrics/apps/6759740679?from=2026-02-19&to=2026-03-21" \
  -H "X-API-Key: $KEY"
```

**Response includes:**
- `daily[]` — `metric_date`, `downloads`, `revenue`, `subscriptions`, `trials`, `iap_count`
- `countries[]` — `country` (ISO code), `downloads`, `revenue`
- `totals` — Aggregated totals for the range

**Use in skills:** `asc-metrics`, `app-analytics`, `localization`

## Common Workflows

### Performance snapshot for the last 30 days

```bash
# Overall portfolio
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/connect/metrics"

# Drill into a specific app
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/connect/metrics/apps/$APP_ID"
```

### Trend analysis — compare two periods

```bash
# Current month
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/connect/metrics/apps/$APP_ID?from=2026-03-01&to=2026-03-21"

# Previous month (same window)
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/connect/metrics/apps/$APP_ID?from=2026-02-01&to=2026-02-21"
```

### Top countries by downloads

```bash
curl -H "X-API-Key: $KEY" \
  "https://api.appeeky.com/v1/connect/metrics/apps/$APP_ID?from=2026-01-01"
# Sort `countries[]` by downloads descending
```