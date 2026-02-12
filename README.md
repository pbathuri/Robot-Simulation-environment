# LABLAB API (ai-tracking)

Backend for RoboDK integration and design store: import from RoboDK, manipulate objects via API, sync poses back.

## Quick start

**Docker (recommended)**

```bash
docker compose up --build
```

API is at **http://localhost:8001** (see [docs/DEPLOY.md](docs/DEPLOY.md) if your compose uses a different port).

**Verify**

```bash
./scripts/verify-api.sh 8001
# or: PORT=8001 make verify
```

**Local (no Docker)**

```bash
make venv && source .venv/bin/activate
make run
# then: make verify  (default port 8000)
```

## Docs

- **[docs/DEPLOY.md](docs/DEPLOY.md)** – Docker, Railway deploy, next steps
- **[docs/ROBODK_INTEGRATION.md](docs/ROBODK_INTEGRATION.md)** – API reference, design store, import/sync

## Main endpoints

| What            | URL (replace `:8001` if needed)                    |
|-----------------|----------------------------------------------------|
| Health          | http://localhost:8001/health                       |
| RoboDK status   | http://localhost:8001/api/robodk/status            |
| Design objects  | http://localhost:8001/api/robodk/design/objects    |
