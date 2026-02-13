I will implement the full RoboDK integration and finalize the Docker/Railway hosting setup.

### 1. Implement Full RoboDK Integration (Missing Features)
The current codebase has basic RoboDK connectivity but lacks the **Design Store**, **Synchronization**, and **CAD Manipulation** features requested. I will:
- **Create `apps/sim/design_store.py`**: An in-memory store to manage your 3D environment objects (CAD models, robots) with their poses and properties.
- **Update `apps/sim/robodk_bridge.py`**: Add missing methods:
  - `import_item(name_or_id)`: Import geometry from RoboDK.
  - `set_item_pose(name, pose)`: Sync object movement from our sim to RoboDK.
  - `add_object_to_robodk(file, name, pose)`: Push local CAD files to RoboDK.
  - `export_item_geometry(item)`: Export STL for local use.
- **Update `apps/api/routes/robodk.py`**: Add API endpoints for:
  - Design Store CRUD (`GET/POST/PUT/DELETE /api/robodk/design/objects`).
  - Live Sync (`POST .../sync-to-robodk`).
  - File Import/Export (`POST .../add-file`, `GET .../export`).

### 2. Finalize Hosting Configuration
- **Railway**: The `railway.toml` is correctly set up to use `Dockerfile.backend`.
- **Docker**: The `Dockerfile.backend` is production-ready.
- **Verification**: I will create a `scripts/verify-api.sh` script to test all new endpoints automatically.

### 3. Execution Plan
1.  Create `apps/sim/design_store.py`.
2.  Update `apps/sim/robodk_bridge.py` with advanced features.
3.  Update `apps/api/routes/robodk.py` with new endpoints.
4.  Create `scripts/verify-api.sh` and `docs/ROBODK_INTEGRATION.md`.
5.  Run verification to confirm everything works.
