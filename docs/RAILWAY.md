# TradeGuard AI — Railway Setup Guide

Deploy the **FastAPI backend** (`apps/api`) on Railway. Keep the **Next.js UI** on Vercel.

```
Vercel (UI)  ──HTTPS──▶  Railway (API + Postgres + Redis)
```

Estimated time: **15–20 minutes**.

---

## Prerequisites

- GitHub repo: `pranaykumar20/tradeguard-ai`
- [Railway account](https://railway.app) (sign in with GitHub)
- Vercel app already deployed (for `CORS_ORIGINS` and `NEXT_PUBLIC_API_URL`)

---

## Step 1 — Create a Railway project

1. Go to [railway.app/new](https://railway.app/new)
2. **Deploy from GitHub repo** → select `tradeguard-ai`
3. Name the project e.g. `tradeguard-ai`

---

## Step 2 — Add PostgreSQL

1. In the project canvas, click **+ New** → **Database** → **PostgreSQL**
2. Wait until the service is healthy
3. Open the Postgres service → **Variables** → copy `DATABASE_URL`  
   (Railway uses `postgres://…`; the API auto-converts to `postgresql+asyncpg://…`)

The API runs `CREATE EXTENSION IF NOT EXISTS vector` on startup for RAG/pgvector.

---

## Step 3 — Add Redis

1. **+ New** → **Database** → **Redis**
2. Copy `REDIS_URL` from the Redis service variables

Celery broker/backend URLs (`/1` and `/2`) are **auto-derived** from `REDIS_URL` — you do not need to set `CELERY_BROKER_URL` manually unless you want custom paths.

---

## Step 4 — Configure the API service

If Railway created a service from GitHub, open it. Otherwise:

1. **+ New** → **GitHub Repo** → `tradeguard-ai`
2. **Settings** → **Root Directory** → `apps/api`
3. **Settings** → **Deploy** → **Custom Start Command** → **clear it** (leave empty)  
   If you see `npm run start --workspace=web`, delete it — that is the Vercel/Next.js command, not the API.
4. **Settings** → confirm builder uses **Dockerfile** (`railway.toml` sets the correct uvicorn start command)

### Link database variables

In the **API service** → **Variables**, add references (Railway’s **Variable Reference** UI):

| Variable | Value |
|----------|--------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` |

(Service names may differ — pick your Postgres/Redis service from the reference dropdown.)

### Required manual variables

| Variable | Example | Notes |
|----------|---------|--------|
| `APP_ENV` | `production` | |
| `STORAGE_BACKEND` | `postgres` | |
| `CORS_ORIGINS` | `https://your-app.vercel.app` | Your Vercel production URL (no trailing slash). Add preview URLs comma-separated if needed. |

### Recommended (Composer LLM)

| Variable | Example |
|----------|---------|
| `LLM_PROVIDER` | `cursor` |
| `LLM_MODEL` | `composer-2.5` |
| `CURSOR_API_KEY` | `crsr_…` from Cursor → Settings → API Keys |
| `CURSOR_CLOUD_REPO_URL` | `https://github.com/pranaykumar20/tradeguard-ai` |

Connect GitHub to Cursor (Settings → Integrations) so cloud agents can clone the repo.

### Optional feature keys

| Variable | Enables |
|----------|---------|
| `OPENAI_API_KEY` | RAG embeddings + fallback LLM |
| `POLYGON_API_KEY` | Live market data |
| `TAVILY_API_KEY` | Real-time market web search (news) |
| `NEWS_PROVIDER` | `auto` (prefers Tavily) · `tavily` · `polygon` · `mock` |
| `SLACK_WEBHOOK_URL` | Slack alerts |
| `CLERK_SECRET_KEY` | API auth |
| `CLERK_JWT_ISSUER` | Clerk JWT issuer URL |
| `ROBINHOOD_MCP_URL` + `ROBINHOOD_MCP_ENABLED=true` | Live MCP execution |

Copy other defaults from `apps/api/.env.example` as needed.

---

## Step 5 — Generate a public URL

1. API service → **Settings** → **Networking** → **Generate Domain**
2. Copy the URL, e.g. `https://tradeguard-api-production.up.railway.app`

---

## Step 6 — Connect Vercel

In **Vercel** → project → **Settings** → **Environment Variables**:

| Variable | Value |
|----------|--------|
| `NEXT_PUBLIC_API_URL` | Your Railway domain (no trailing slash) |

Redeploy Vercel.

Update Railway `CORS_ORIGINS` if you change Vercel domains.

---

## Step 7 — Verify

```bash
# Liveness
curl https://YOUR-RAILWAY-URL/health

# Readiness (Postgres + Redis)
curl https://YOUR-RAILWAY-URL/health/ready
```

Expect:

```json
{ "status": "ready", "phase": 9, "storage_backend": "postgres", ... }
```

Then open your Vercel app — dashboard and chat should load against Railway.

---

## Deploy flow

Every push to `main` that touches `apps/api` triggers a Railway rebuild (if GitHub deploy is enabled). CI also builds the Docker image on GitHub Actions.

**Database migrations** run automatically before each deploy via `preDeployCommand = "alembic upgrade head"` in `apps/api/railway.toml`. To run locally:

```bash
cd apps/api
alembic upgrade head
```

Health check path: `/health` (configured in `apps/api/railway.toml`).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Vercel UI can’t reach API | Check `NEXT_PUBLIC_API_URL`; redeploy Vercel |
| CORS errors in browser | Add exact Vercel URL to `CORS_ORIGINS` on Railway |
| `ready` fails / DB errors | Confirm `DATABASE_URL` reference; Postgres service running |
| `CREATE EXTENSION vector` fails | Railway Postgres may need pgvector — open a Railway support ticket or use a pgvector-enabled Postgres template |
| Chat returns template text | Set `CURSOR_API_KEY` + `CURSOR_CLOUD_REPO_URL`, or `OPENAI_API_KEY` with `LLM_PROVIDER=openai` |
| `column users.role does not exist` | Redeploy after pulling latest `main` — Alembic adds RBAC columns in pre-deploy. Or run `cd apps/api && alembic upgrade head` against production `DATABASE_URL`. |
| Build fails | Check **Deploy Logs**; ensure root directory is `apps/api` |
| `npm could not be found` on startup | API service → **Settings** → **Deploy** → clear **Custom Start Command**; redeploy. Root must be `apps/api`, not repo root. |
| Railway runs `npm run start --workspace=web` | Same fix — Railway guessed the monorepo web app. Use `apps/api` root + empty/correct start command. |

---

## Cost

Railway bills by usage (compute + Postgres + Redis). Hobby plans include a monthly credit. Monitor **Usage** in the Railway dashboard.

---

## Local parity

For development without Railway:

```bash
docker compose up -d
cp apps/api/.env.example apps/api/.env
# edit .env
cd apps/api && uvicorn app.main:app --reload
```

See [DEPLOY.md](./DEPLOY.md) for the full architecture overview.
