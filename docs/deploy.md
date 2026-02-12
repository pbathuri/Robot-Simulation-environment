# Deployment

## Docker (local / dev full stack)

Run backend + web + Redis + worker with Docker Compose:

```bash
# From repo root
docker compose up --build
```

- **Web:** http://localhost:3000  
- **API:** http://localhost:8000  
- **API docs:** http://localhost:8000/docs  

The web app proxies `/api/*` and `/api/v1/*` to the backend container. Runs and assets are stored in Docker volumes `qers_runs` and `qers_assets`. Sim jobs are queued to Redis and processed by the worker.

### Production-style compose (root Dockerfiles)

Use root-level production Dockerfiles and `restart: unless-stopped`:

```bash
docker compose -f docker-compose.prod.yml up --build
```

- `Dockerfile.backend` — backend + worker image (build once, worker uses same image).
- `Dockerfile.ui` — Next.js standalone build.

### Optional: backend only

```bash
docker compose up --build backend
```

Then run the Next.js UI locally with `make ui` (or `cd apps/web && pnpm dev`). It will proxy to `http://127.0.0.1:8000` by default.

---

## Railway (backend)

The FastAPI backend can be deployed to [Railway](https://railway.app) using the repo Dockerfile.

### Prerequisites

- Railway account
- Railway CLI optional: `npm i -g @railway/cli` and `railway login`

### Deploy steps

1. **Create a project and service**
   - In [Railway Dashboard](https://railway.app/dashboard), New Project → Deploy from GitHub repo.
   - Select this repo. Railway will use `railway.toml` and build with `apps/api/Dockerfile`.

2. **Configure (if not using config-as-code)**
   - **Root directory:** leave empty (build context = repo root).
   - **Dockerfile path:** `apps/api/Dockerfile` (or set in dashboard if not using `railway.toml`).
   - **Variables (optional):**
     - `PORT` — set automatically by Railway; app reads it for uvicorn.
     - `RUNS_DIR` — default `/app/runs` (ephemeral unless you add a volume).
     - `ASSETS_DIR` — default `/app/assets`.

3. **Generate domain**
   - In the service, Settings → Networking → Generate Domain. You get a URL like `https://<service>.up.railway.app`.

4. **Health check**
   - Railway uses `healthcheckPath = "/api/health"` from `railway.toml`. The app responds with `{"status": "ok", "service": "qers-api"}`.

### CLI deploy

```bash
railway link   # select project + service
railway up     # build and deploy from current branch
```

### Frontend pointing at Railway backend

If the Next.js app is hosted elsewhere (e.g. Vercel or another Railway service), set the backend URL at **build time**:

- **Vercel:** add env var `API_BACKEND_URL=https://<your-backend>.up.railway.app`, then redeploy.
- **Docker (web):** build with `--build-arg API_BACKEND_URL=https://<your-backend>.up.railway.app`.

The web app rewrites `/api/*` to this URL. CORS is enabled for all origins in the API (`allow_origins=["*"]`).

### Persistence on Railway

- **Runs and assets** live in the container filesystem by default and are **ephemeral** (lost on redeploy).
- For persistence, add a [Railway Volume](https://docs.railway.app/data-storage/volumes) and set:
  - `RUNS_DIR=/app/data/runs`
  - `ASSETS_DIR=/app/data/assets`
  and mount the volume at `/app/data`.

---

## How to run / test after changes

| Change        | How to run/test |
|---------------|------------------|
| Backend code  | `make backend` or `docker compose up backend`; hit http://localhost:8000/api/health and /docs. |
| Web code      | `make ui` or `docker compose up web`; open http://localhost:3000. |
| Full stack    | `docker compose up --build`; use Sim and Runs pages. |
| Railway       | `railway up` or push to connected branch; check service logs and generated URL. |
