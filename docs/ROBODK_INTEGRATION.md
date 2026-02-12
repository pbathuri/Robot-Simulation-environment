# RoboDK Full Integration

Objects are **fully manipulable in the LABLAB environment** via the API and internal design store. You can import designs from RoboDK, edit them in our environment, and sync changes back to RoboDK.

## Overview

- **Design store**: In-memory list of objects (from RoboDK or created locally). Each has `id`, `name`, `type`, `pose` (4×4 matrix), `source` (`robodk` | `local`), and optional `robodk_id` for sync.
- **RoboDK bridge**: Connects to the running RoboDK app, reads station tree/items/poses, exports geometry, and pushes pose/joint updates.

## API Base

All endpoints are under **`/api/robodk`** (e.g. `http://localhost:8000/api/robodk/status`).

### 1. Connection

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/robodk/status` | Check if RoboDK is connected |
| POST | `/api/robodk/connect` | Connect to RoboDK (503 if not running) |

### 2. Import from RoboDK

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/robodk/station` | Full station tree (items with name, type, pose, children) |
| GET | `/api/robodk/import/{item_ref}` | Import one item by **name** or **id**; adds to design store and returns object + `stored_id` |
| POST | `/api/robodk/import-all` | Import every item from the station into the design store |

Use `item_ref` as the RoboDK item name (e.g. `"ABB IRB120"`) or numeric id.

### 3. Design Store (Our Environment) – Full CRUD

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/robodk/design/objects` | List all objects in our environment |
| GET | `/api/robodk/design/objects/{obj_id}` | Get one object by id |
| PUT | `/api/robodk/design/objects/{obj_id}/pose` | Update pose (body: `{ "pose": [[4x4]], "sync_to_robodk": false }`) |
| DELETE | `/api/robodk/design/objects/{obj_id}` | Remove from design (does not delete in RoboDK) |
| POST | `/api/robodk/design/objects` | Create object (body: `{ "name", "object_type?", "pose?" }`) |

**Pose format**: 4×4 row-major matrix (e.g. identity):

```json
[
  [1, 0, 0, 0],
  [0, 1, 0, 0],
  [0, 0, 1, 0],
  [0, 0, 0, 1]
]
```

### 4. Sync to RoboDK

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/robodk/design/objects/{obj_id}/sync-to-robodk` | Push current pose of this object to RoboDK (only if it has `robodk_id`) |

### 5. Robots

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/robodk/robots/joints` | Set robot joints in RoboDK (body: `{ "robot_name", "joints": [] }`) |
| POST | `/api/robodk/quantum-demo` | Run quantum demo (query: `robot_name`, `duration_sec`) |

### 6. Files

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/robodk/add-file` | Upload STL/STEP etc.; add to RoboDK and optionally to design store (`add_to_design=true`) |
| GET | `/api/robodk/export/{item_ref}` | Export item geometry from RoboDK as STL download |

## Using This in Your Design Page

1. **Connect**: Call `GET /api/robodk/status` on load; show “Connect to RoboDK” if `connected: false`. On button click, call `POST /api/robodk/connect`.
2. **Import**: After connect, call `GET /api/robodk/station` to show the tree. “Import all” → `POST /api/robodk/import-all`. Or “Import” one item → `GET /api/robodk/import/{name_or_id}`.
3. **List manipulable objects**: `GET /api/robodk/design/objects` and render them in your 3D view (use `pose` for transform).
4. **Edit pose**: When user moves an object in your viewer, send `PUT /api/robodk/design/objects/{id}/pose` with `sync_to_robodk: true` to update both our store and RoboDK.
5. **Add geometry**: “Add file” → `POST /api/robodk/add-file` with `multipart/form-data` file + optional `name`, `add_to_design=true`.
6. **Export**: “Export STL” for an item → `GET /api/robodk/export/{item_ref}` (opens download).

## How to Run

From repo root:

```bash
# Install
pip install fastapi uvicorn robodk  # optional: robodk for RoboDK link

# Run API (ensure RoboDK is running for connect/import/sync)
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

Then open the design UI and point it at `http://localhost:8000`.

## Design UI – Fetch Examples

Use these from your design page (replace `API` with your backend base, e.g. `http://localhost:8000`):

```js
const API = 'http://localhost:8000';

// Status & connect
const status = await fetch(`${API}/api/robodk/status`).then(r => r.json());
await fetch(`${API}/api/robodk/connect`, { method: 'POST' });

// Station tree (for import dropdown)
const { items } = await fetch(`${API}/api/robodk/station`).then(r => r.json());

// Import one item into our environment
const { object, stored_id } = await fetch(`${API}/api/robodk/import/Robot`).then(r => r.json());

// Import all
await fetch(`${API}/api/robodk/import-all`, { method: 'POST' }).then(r => r.json());

// List manipulable objects (our environment)
const { objects } = await fetch(`${API}/api/robodk/design/objects`).then(r => r.json());

// Update pose and sync to RoboDK
await fetch(`${API}/api/robodk/design/objects/${objId}/pose`, {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ pose: fourByFourMatrix, sync_to_robodk: true }),
});

// Sync current pose to RoboDK
await fetch(`${API}/api/robodk/design/objects/${objId}/sync-to-robodk`, { method: 'POST' });

// Add file (multipart)
const fd = new FormData();
fd.append('file', fileInput.files[0]);
await fetch(`${API}/api/robodk/add-file?add_to_design=true`, { method: 'POST', body: fd });
```

## Files

- `apps/sim/robodk_bridge.py` – RoboDK connection, station tree, import, pose/joints, export, add file.
- `apps/sim/design_store.py` – In-memory design store and `update_pose(..., sync_to_robodk)`.
- `apps/api/routes/robodk.py` – All HTTP endpoints above.
- `apps/api/main.py` – FastAPI app that mounts the RoboDK router.
