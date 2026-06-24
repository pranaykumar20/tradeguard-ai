---
name: tradeguard-deploy-verify
description: >-
  Deploy and verify TradeGuard on Vercel + Railway. Use for production env vars,
  CORS, health checks, OAuth setup, and post-deploy smoke tests.
---

# TradeGuard Deploy & Verify

## Docs

- `docs/RAILWAY.md` — API on Railway
- `docs/DEPLOY.md` — full deploy overview
- `docs/MCP-SETUP.md` — Robinhood OAuth

## Architecture

- **Frontend**: Vercel (`apps/web`)
- **API**: Railway or Fly (`apps/api`)
- **Data**: Railway Postgres + Redis (or Docker Compose locally)

## Railway (API) required vars

| Variable | Example |
|----------|---------|
| `APP_ENV` | `production` |
| `STORAGE_BACKEND` | `postgres` |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` |
| `CORS_ORIGINS` | `https://your-app.vercel.app` |
| `API_PUBLIC_URL` | `https://your-api.up.railway.app` |
| `FRONTEND_URL` | `https://your-app.vercel.app` |

## Vercel (web)

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Railway API URL (no trailing slash) |

Redeploy Vercel after env changes.

## Post-deploy smoke tests

```bash
API=https://your-api.up.railway.app

# Liveness
curl -s "$API/health" | jq .status

# Readiness (Postgres + Redis)
curl -s "$API/health/ready" | jq .status

# Auth / demo user
curl -s "$API/api/auth/me" -H "Origin: https://your-app.vercel.app"

# Robinhood connect (should return authorization_url, not 500)
curl -s -X POST "$API/api/brokers/robinhood/connect" \
  -H "Content-Type: application/json" \
  -d '{"return_path":"/onboarding"}' | jq .authorization_url
```

## CORS troubleshooting

1. Confirm `CORS_ORIGINS` matches exact Vercel URL (no trailing slash).
2. If browser shows CORS error, curl the failing endpoint — often a 500 without CORS headers.
3. Check Railway deploy logs for stack traces.

## Migrations

- `apps/api/railway.toml` runs `python scripts/migrate.py` pre-deploy.
- Local: `cd apps/api && python scripts/migrate.py`

## Do not

- Commit `.env` files with secrets.
- Use `localhost` for `API_PUBLIC_URL` in production.
- Skip `/health/ready` after Postgres/Redis changes.
