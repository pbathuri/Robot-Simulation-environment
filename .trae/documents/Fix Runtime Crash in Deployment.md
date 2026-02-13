# Deployment Fix Plan

The build logs confirm that the image builds successfully now (Python 3.10 fixed the PyBullet installation), but the **Healthcheck** is still failing. This strongly suggests the application is crashing on startup or failing to bind to port 8000.

## Root Cause Analysis
1.  **Build Success:** `pip install pybullet` succeeded, and the image was exported. This is a huge win.
2.  **Runtime Failure:** `Attempt #1 failed with service unavailable`. This means `curl http://127.0.0.1:8000/api/health` returned an error or connection refused.
3.  **Likely Culprit:**
    *   **Import Errors:** Python 3.10 might be missing a dependency that was implicitly present before, or code is using syntax not supported in 3.10 (unlikely for `uvicorn`, but possible for type hints like `str | None` which requires `from __future__ import annotations` in 3.9/3.10).
    *   **Missing System Deps:** Even with X11 libs, `libgl1` might still be tricky in headless environments.
    *   **CORS/Host Binding:** We are binding to `0.0.0.0`, so that should be fine.

## Plan
1.  **Verify Code Compatibility (Python 3.10):** Check `apps/api/main.py` for modern syntax (e.g., `X | Y` type unions) which might need `from __future__ import annotations` or `typing.Union` in Python 3.10.
2.  **Pin Dependencies:** Ensure `requirements.txt` versions are compatible with Python 3.10.
3.  **Debug Healthcheck:** Add a "pre-flight" check to the Dockerfile to print startup errors to the log instead of just failing silently.
4.  **Action:**
    *   Add `from __future__ import annotations` to key files to support modern type hinting in 3.10.
    *   Update `Dockerfile.backend` to run a smoke test during the build phase (try importing the app).

I will start by checking the codebase for Python 3.10 compatibility issues.
