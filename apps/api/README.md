# Anicca iOS API Server

Backend API server for Anicca iOS app, deployed on Railway.

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Create `.env` file:
   ```
   DATABASE_URL=postgresql://...
   OPENAI_API_KEY=...
   MEM0_API_KEY=...
   REVENUECAT_REST_API_KEY=...
   ```

3. Run locally:
   ```bash
   npm run dev:railway
   ```

## Deployment (Railway)

Railway auto-deploys from the `dev` branch.

### Prisma Migration (Important!)

For **existing databases**, run the following command before first deploy:

```bash
npx prisma migrate resolve --applied 0_init
```

This marks the baseline migration as already applied (since tables already exist).

For **new databases**, migrations run automatically via `prisma migrate deploy`.

## API Endpoints

### Mobile API (`/api/mobile/`)
- `/profile` - User profile CRUD
- `/entitlement` - Subscription status
- `/account` - Account management (deletion)
- `/nudge` - Nudge generation and feedback

### Admin API (`/api/admin/`)
- `/tiktok` - TikTok post management
- `/hook-candidates` - Hook candidate CRUD
- `/trigger-nudges` - Manual cron trigger

## Deprecated Endpoints (v1.6.0)

The following endpoints return `410 Gone`:
- `/api/mobile/behavior`
- `/api/mobile/feeling`
- `/api/mobile/daily_metrics`
- `/api/mobile/sensors`
- `/api/mobile/user-type`
- `/api/mobile/realtime`

These were removed as they were not called by the iOS app.