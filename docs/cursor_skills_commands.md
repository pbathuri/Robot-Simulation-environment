# Cursor Skills & Commands

Copy-pastable definitions for Cursor UI: **Skill** (name + trigger + procedure), **Command** (name + steps + expected outputs).

---

## Skills (agent-invoked)

### Sim2RealSpec

- **Name:** Sim2RealSpec  
- **Trigger:** User asks to turn a paper/idea into module specs, contracts, or test plan for sim-to-real.  
- **Procedure:** (1) Extract task variables, states, observations, actions from the source. (2) Draft or update contracts (run, step, metrics, gap_knobs) in `/contracts`. (3) List affected modules (sim core, physics, sensors, eval). (4) Propose a test plan (determinism, replay, SRCC/replay error placeholders). (5) Output summary and file list.

### GapKnobDesigner

- **Name:** GapKnobDesigner  
- **Trigger:** User asks for domain randomization knobs for a task or module.  
- **Procedure:** (1) Identify module (physics, sensors, control, env). (2) Enumerate parameters that affect reality gap (mass, friction, noise, latency, lighting, etc.). (3) Propose schema (name, type, bounds, default) for each knob. (4) Add or update `gap_knobs` in contracts and document in `docs/simulation_contracts.md`.

### ContractGenerator

- **Name:** ContractGenerator  
- **Trigger:** User asks to produce or update JSON Schema and TS/Python types for a data shape.  
- **Procedure:** (1) Define or update JSON Schema in `/contracts/v1/<name>.json`. (2) Add or sync Pydantic model in `apps/sim/contracts/` (or equivalent). (3) If requested, add instructions or script for generating TypeScript types. (4) List generated/updated files and how to validate.

### EvalHarnessBuilder

- **Name:** EvalHarnessBuilder  
- **Trigger:** User asks to add metrics pipelines, report outputs, or UI wiring for evaluation.  
- **Procedure:** (1) Identify metrics (SRCC, replay error, task success, etc.) and existing schemas. (2) Add or extend eval code in `apps/sim/eval/` (or `eval/`). (3) Ensure output is machine-readable (JSON/CSV) and matches contracts. (4) Wire API/dashboard to serve or display the metrics. (5) Document in `docs/evaluation.md` and provide run instructions.

### LLMResearchPipeline

- **Name:** LLMResearchPipeline  
- **Trigger:** User asks to generate prompts, run multi-provider LLM queries, dedupe, or store citations.  
- **Procedure:** (1) Use or create prompt templates in `tools/llm_research/prompts/`. (2) Call provider interface `query_llm(provider, model, prompt, ...)` with caching enabled. (3) Capture citations (URLs/DOIs) from response when available; store in `tools/llm_research/citations/`. (4) Dedupe by prompt hash or content hash if requested. (5) Return consolidated response and citation list; never log API keys.

---

## Commands (manual / slash)

### /bootstrap_repo

- **Steps:** Create repo structure (apps/sim, apps/api, apps/web, contracts, docs, tools/llm_research), add configs (ruff, mypy, pytest, eslint, prettier), add CI skeleton (e.g. GitHub Actions: lint, test, smoke). Add README with run instructions and .env.example.  
- **Expected output:** Repo can be cloned, deps installed, lint and test run; CI file present.

### /add_sim_task

- **Steps:** Add a new robot/task scenario: (1) Define or extend contracts (scenario config, actions, metrics). (2) Add scenario config file or entry in runner. (3) Add runner path for the scenario. (4) Add or extend metrics so task success/reward can be logged. Document in docs.  
- **Expected output:** New scenario can be run via runner or API; run produces replay and optional metrics.

### /add_sensor_model

- **Steps:** Add a new sensor model: (1) Implement `SensorModel` in `apps/sim/sim/sensors/` with observe(state, t, rng=...). (2) Add noise and latency options; add DR knobs to config. (3) Document observation schema. (4) Add a small test (deterministic vs stochastic).  
- **Expected output:** Sensor is pluggable into SimCore; observation shape documented.

### /add_physics_adapter

- **Steps:** Add a new physics engine adapter: (1) Implement `PhysicsEngine` in `apps/sim/sim/physics/`. (2) Add conformance tests (step determinism, get/set state round-trip). (3) Document engine-specific config and gap knobs.  
- **Expected output:** Adapter passes conformance tests; sim core runs with new adapter without code change.

### /run_batch_sims

- **Steps:** Run N sims with domain randomization: (1) Load or generate N configs (e.g. different seeds or DR samples). (2) Call runner for each (or use multiprocessing/Ray placeholder). (3) Store each run under `runs/<run_id>/` with replay and meta. (4) Optionally compute and attach metrics.  
- **Expected output:** N run directories; list of run_ids; optional summary CSV.

### /compute_eval

- **Steps:** Compute SRCC, replay error, task metrics for selected runs: (1) Load run bundles and any reference data. (2) Call eval functions (srcc, replay_error, task metrics). (3) Write metrics.json per run and/or aggregated report. (4) Ensure dashboard can fetch metrics via API.  
- **Expected output:** metrics.json (or report) per run; dashboard shows metrics for run.

### /calibrate_from_real

- **Steps:** Ingest real logs, run parameter search, update sim params: (1) Load real trajectory/log format. (2) Define parameter bounds (e.g. mass, friction). (3) Run optimizer (e.g. classical or quantum stub) to minimize replay error or other objective. (4) Output updated sim params and diff from default. (5) Record diff and run_id in audit or doc.  
- **Expected output:** New config or patch file; document what changed and why.
