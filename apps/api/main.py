"""
LABLAB API: mounts RoboDK + Design integration and other app routes.
Run: uvicorn apps.api.main:app --reload (from repo root)
"""
import sys
from pathlib import Path

# Ensure repo root on path when running from anywhere
_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes.robodk import router as robodk_router

app = FastAPI(title="LABLAB API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(robodk_router)


@app.get("/health")
def health():
    return {"status": "ok"}
