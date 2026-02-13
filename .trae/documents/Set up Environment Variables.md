# Configure Environment Variables

I will create the `.env` file in the project root to configure the API keys and settings you provided.

## 1. Create `.env` File
I will populate `/Users/prady/Desktop/ai-tracking/.env` with the following values:
*   `OPENAI_API_KEY`: Set to the key you provided (`sk-proj-...`).
*   `GEMINI_API_KEY`: Set to the key you provided (`AIzaSy...`).
*   `ROBODK_IP`: Set to `0.0.0.0` as requested.
*   `ANTHROPIC_API_KEY`: **Skipping** for now. The value provided appeared to be a `curl` command rather than an API key (which usually starts with `sk-ant-`). I will leave this commented out or blank so it falls back to stub/placeholder mode.
*   `REDIS_URL`: `redis://localhost:6379/0` (Default from example, useful if you run Redis locally).

## 2. Verification
*   The application will automatically load these values on the next restart.
*   I will not modify any code, only create the configuration file.

**Note on `ROBODK_IP=0.0.0.0`:** This tells the bridge to connect to `0.0.0.0`. If RoboDK is running on the same machine (localhost), this works. If you are running the backend in Docker and RoboDK on the host, you might eventually need `host.docker.internal`, but I will stick to your specific instruction of `0.0.0.0` for now.
