# TradeGuard AI — Production Deployment

Frontend: **Vercel** (`apps/web`)  
Backend API: **Railway** or **Fly.io** (`apps/api`)  
Data: **PostgreSQL + pgvector** and **Redis** (managed add-ons or Docker)

---

## Architecture

```
Vercel (Next.js)  ──HTTPS──▶  Railway/Fly (FastAPI)
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              PostgreSQL         Redis          External APIs
              (pgvector)      (Celery)     Polygon, OpenAI, MCP
```

---

## 1. Backend — Railway (recommended)

**Step-by-step guide:** [RAILWAY.md](./RAILWAY.md)

### Create services

1. **New Project** → Add **PostgreSQL** and **Redis** plugins
2. **New Service** → Deploy from GitHub, set **Root Directory** to `apps/api`
3. Railway builds from `apps/api/Dockerfile` (see `railway.toml`)

### Required environment variables

| Variable | Source |
|----------|--------|
| `DATABASE_URL` | Reference `${{Postgres.DATABASE_URL}}` |
| `REDIS_URL` | Reference `${{Redis.REDIS_URL}}` |
| `CELERY_BROKER_URL` | Auto-derived from `REDIS_URL` → `/1` |
| `CELERY_RESULT_BACKEND` | Auto-derived from `REDIS_URL` → `/2` |
| `STORAGE_BACKEND` | `postgres` |
| `APP_ENV` | `production` |
| `CORS_ORIGINS` | Your Vercel URL(s), e.g. `https://tradeguard-ai.vercel.app` |

### Optional (enable live providers)

| Variable | Purpose |
|----------|---------|
| `CURSOR_API_KEY` + `CURSOR_CLOUD_REPO_URL` | Composer 2.5 LLM (production) |
| `LLM_PROVIDER` / `LLM_MODEL` | `cursor` / `composer-2.5` |
| `OPENAI_API_KEY` | Embeddings + fallback LLM |
| `POLYGON_API_KEY` | Live market data |
| `SLACK_WEBHOOK_URL` | Slack alerts |
| `SMTP_*` + `ALERT_EMAIL_TO` | Email alerts |
| `CLERK_SECRET_KEY` | API auth (Phase 5.2) |
| `ROBINHOOD_MCP_URL` + `ROBINHOOD_MCP_ENABLED=true` | Live execution |

### Health checks

- `GET /health` — liveness (always 200 when process up)
- `GET /health/ready` — readiness (Postgres + Redis ping)

---

## 2. Backend — Fly.io (alternative)

```bash
cd apps/api
fly launch --no-deploy   # link app, keep fly.toml
fly postgres create      # or attach existing
fly redis create         # or Upstash via Fly
fly secrets set DATABASE_URL=... REDIS_URL=... CORS_ORIGINS=...
fly deploy
```

Set `DATABASE_URL` to `postgresql+asyncpg://...` or plain `postgres://` (auto-normalized).

---

## 3. Frontend — Vercel

Already configured via `apps/web/vercel.json`:

```json
{
  "installCommand": "cd ../.. && npm install",
  "buildCommand": "npm run build"
}
```

### Vercel environment variables

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Railway/Fly API URL, e.g. `https://tradeguard-api.up.railway.app` |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk dashboard (Phase 5.2) |
| `CLERK_SECRET_KEY` | Server-side Clerk (if using SSR auth) |

Redeploy Vercel after setting `NEXT_PUBLIC_API_URL`.

---

## 4. Staging vs production

| Environment | Branch | Vercel | API |
|-------------|--------|--------|-----|
| **Production** | `main` | Production domain | Railway prod service |
| **Staging** | `staging` | Preview URL | Railway staging service |

GitHub Actions (`.github/workflows/staging.yml`) runs the same CI as `main` on pushes to `staging`.

---

## 5. Secrets checklist

Never commit secrets. Set in Railway/Fly/Vercel dashboards or GitHub Actions secrets:

- [ ] `DATABASE_URL`
- [ ] `REDIS_URL` / Celery URLs
- [ ] `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
- [ ] `POLYGON_API_KEY`
- [ ] `SLACK_WEBHOOK_URL`
- [ ] `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_EMAIL_TO`
- [ ] `CLERK_SECRET_KEY`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- [ ] `ROBINHOOD_MCP_URL`

---

## 6. Local Docker build (smoke test)

```bash
docker build -t tradeguard-api apps/api
docker run --rm -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://tradeguard:tradeguard@host.docker.internal:5433/tradeguard \
  -e REDIS_URL=redis://host.docker.internal:6380/0 \
  -e STORAGE_BACKEND=postgres \
  tradeguard-api
curl http://localhost:8000/health/ready
```

---

## 7. Post-deploy verification

1. `curl https://<api>/health/ready` → `"status": "ready"`
2. Open Vercel app → dashboard loads portfolio
3. Trigger monitoring check → alert in Slack/email (if configured)
4. Submit test chat → response from LLM or template mode
