# Deploy: Docker & Railway

## Next steps (Docker is running)

1. **Verify the API** (container must be up):
   - If you use **port 8001** (docker-compose as shipped):  
     `./scripts/verify-api.sh 8001` or `PORT=8001 make verify`
   - If you use **port 8000**:  
     `./scripts/verify-api.sh` or `make verify`
   - Or open in browser: `http://localhost:8001/health` (or 8000), `http://localhost:8001/api/robodk/design/objects`

2. **Use the API**: See [ROBODK_INTEGRATION.md](ROBODK_INTEGRATION.md) for all endpoints (design store, import, sync to RoboDK, add file).

3. **Deploy to Railway**: Push to GitHub → Railway → Deploy from repo. See [Railway (backend)](#railway-backend) below.

---

## Verify locally (no Docker)

From repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

Then:

- http://localhost:8000/health → `{"status":"ok"}`
- http://localhost:8000/api/robodk/status → RoboDK connection status
- http://localhost:8000/api/robodk/design/objects → list design objects

## Docker (local)

From repo root:

```bash
# Build and run
docker compose up --build
```

This project's `docker-compose.yml` maps **host 8001 → container 8000**, so use:

- **API base:** http://localhost:8001
- **Health:** http://localhost:8001/health
- **RoboDK status:** http://localhost:8001/api/robodk/status
- **Design objects:** http://localhost:8001/api/robodk/design/objects

To verify all endpoints: `./scripts/verify-api.sh 8001` or `PORT=8001 make verify`.

Run in background:

```bash
docker compose up -d --build
docker compose logs -f api
```

Stop:

```bash
docker compose down
```

## Railway (backend)

**Checklist:**

1. **Connect repo**
   - [Railway](https://railway.app) → New Project → **Deploy from GitHub**.
   - Select this repository; root directory = repo root.

2. **Build**
   - Railway detects the root `Dockerfile` and builds the image.
   - No extra build command needed. `PORT` is set automatically at runtime.

3. **Deploy**
   - Push to the connected branch to trigger a deploy.
   - Wait for build + deploy to finish.

4. **Generate domain**
   - In the service: **Settings** → **Networking** → **Generate Domain** (e.g. `ai-tracking-api-production.up.railway.app`).

5. **Verify**
   - `curl https://<your-domain>/health` → `{"status":"ok"}`
   - `curl https://<your-domain>/api/robodk/design/objects` → `{"objects":[]}` or list

**Optional:** Service → Variables: add any env vars. Root Directory and Dockerfile path can stay default.

## Notes

- **RoboDK**: The RoboDK Python API and “Connect to RoboDK” only work when RoboDK desktop is running (e.g. on your machine). In Docker/Railway, `/api/robodk/status` will report not connected; design store and non-RoboDK endpoints still work.
- **CORS**: The API allows all origins; restrict in production if needed via FastAPI middleware.
