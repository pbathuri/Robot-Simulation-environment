# RoboDK Integration & API Guide

This guide details how to use the LABLAB API to integrate with RoboDK for robot programming, CAD synchronization, and quantum noise simulation.

## Overview

The integration consists of:
1.  **RoboDK Bridge**: A backend module that connects to a running RoboDK instance.
2.  **Design Store**: An in-memory store for 3D objects and robots in the LABLAB environment.
3.  **API Routes**: Endpoints to manipulate the design store, sync with RoboDK, and control robots.

## Prerequisites

-   **RoboDK** installed and running on the host machine.
-   **robodk** python package installed (`pip install robodk`).
-   LABLAB backend running (locally or via Docker).

> **Docker Note**: If running via `docker compose`, the backend automatically connects to RoboDK on the host machine using `host.docker.internal`.
> 
> **Local Run Note**: If running locally (`make backend`), the backend connects to RoboDK on `localhost` by default. No extra configuration is needed.

## API Endpoints

Base URL: `http://localhost:8000/api/robodk`

### Connection
-   `GET /status`: Check connection status.
-   `POST /reconnect`: Force reconnection attempt.

### Design Store & Sync
-   `GET /design/objects`: List all objects in the local environment.
-   `POST /design/objects`: Create a new object.
    ```json
    {
      "name": "MyBox",
      "object_type": "object",
      "pose": [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1],
      "source": "local"
    }
    ```
-   `PUT /design/objects/{id}/pose`: Update object pose (and optionally sync to RoboDK).
    ```json
    {
      "pose": [...],
      "sync_to_robodk": true
    }
    ```
-   `POST /design/objects/{id}/sync-to-robodk`: Force push current pose to RoboDK.

### Import/Export
-   `GET /station`: Get the full RoboDK station tree.
-   `GET /import/{item_ref}`: Import an item from RoboDK to the local store.
-   `POST /import-all`: Import all items from RoboDK.
-   `POST /add-file`: Upload a CAD file (STL, STEP) to RoboDK.
-   `GET /export/{item_ref}`: Download item geometry as STL.

### Robot Control
-   `GET /robots`: List available robots.
-   `GET /joints/{robot_name}`: Get current joint values.
-   `POST /move-joints`: Move robot to specific joints.
-   `POST /quantum-demo`: Run the quantum noise demonstration.

## Usage Examples

### 1. Import Station
To bring your RoboDK environment into LABLAB:
```bash
curl -X POST http://localhost:8000/api/robodk/import-all
```

### 2. Move Object
To move an object in LABLAB and see it move in RoboDK:
1.  Get object ID from `/design/objects`.
2.  Update pose with sync:
```bash
curl -X PUT http://localhost:8000/api/robodk/design/objects/YOUR_ID/pose \
  -H "Content-Type: application/json" \
  -d '{"pose": [1,0,0,100, 0,1,0,0, 0,0,1,0, 0,0,0,1], "sync_to_robodk": true}'
```

### 3. Quantum Demo
To visualize quantum noise on a robot:
```bash
curl -X POST http://localhost:8000/api/robodk/quantum-demo \
  -H "Content-Type: application/json" \
  -d '{"robot_name": "ABB IRB 120", "noise_scale": 0.1}'
```
