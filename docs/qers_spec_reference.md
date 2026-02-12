# QERS Specification Reference

This document is the **single detailed reference** for functions, specifications, logic, and math derived from the QERS requirements plan and related docs. Use it to align implementation with the stated purpose and to implement or extend features correctly.

---

## 1. Purpose and Success Criteria

**Purpose.** Build a robotics simulator that narrows the "stochastic reality gap" by:

- Combining **classical physics** (macro) with **quantum-stochastic + adversarial + residual-learning** (micro).
- Providing an **AI/LLM "text to algorithm"** workflow for behavior and environment configuration.
- Using **POMDP-based gap metrics** (G_dyn, G_perc, G_perf) so sim performance is predictive of real performance.

**Success (from spec).**

- Runnable MVP demo in under 2 minutes: backend + UI, load example robot, run sim with noise profile, show metrics + logs.
- Modular layout: `sim/`, `quantum/`, `agents/`, `ui/`, `benchmarks/`, `docs/`.
- Reproducibility: seed control, config snapshots per run, JSON report export.
- Safety: sandbox generated code, validate schemas, no arbitrary execution without user confirmation.
- `make demo` and `make benchmark` with at least success rate + G_perf proxy.

**Design principle.** "Reinvent noise, not gravity": build on PyBullet/MuJoCo; overlay Q-Plugin quantum noise, Bayesian sandbox, SAGE-style adversary, and residual dynamics.

---

## 2. POMDP and Gap Taxonomy

**POMDP framing.** The system is framed as a POMDP: state \(s\), action \(a\), observation \(o\), transition \(T(s'|s,a)\), observation model \(O(o|s)\). Reality gap is multi-factor; each source must be explicit and (where possible) measurable.

**Gap taxonomy (R1).**

| Gap source | What to model / log |
|------------|----------------------|
| **Dynamics** | Mass, inertia, friction, restitution, contact model, solver/step; log per-run "gap knobs" and integrator. |
| **Perception/sensing** | Noise, latency, resolution, FOV, distortion, lighting; sensor-wise config and observation stats. |
| **Actuation/control** | Delay, jitter, saturation, backlash, filter differences; config and (optional) logs. |
| **System/implementation** | Packet loss, latency, timing, numerical precision; logged where relevant. |

**Gap knobs.** Per-module config for domain randomization (e.g. `mass_scale`, `friction_range`, `noise_scale`, `latency_steps`, `camera_degrade`). Stored in run config and in `contracts` (e.g. `reality_profile`, `gap_knobs`).

---

## 3. Metrics: Definitions and Math

All metrics are **machine-readable** (JSON/CSV) and consumed by the dashboard. See `contracts/v1/metrics.json` and `docs/evaluation.md`.

### 3.1 G_dyn(Ms, Mr)

- **Definition.** Divergence between **transition** distributions: sim \(T_s(s'|s,a)\) vs real \(T_r(s'|s,a)\).
- **Interpretation.** High G_dyn ⇒ sim dynamics differ from real; low ⇒ dynamics are aligned.
- **Implementation options.**  
  - **KL proxy:** Estimate \(T_s\), \(T_r\) from samples \((s,a,s')\); compute KL or Jensen–Shannon.  
  - **MMD:** Maximum Mean Discrepancy between transition samples.  
  - **Replay proxy:** Run real actions in sim; compare resulting \(s'\) to real \(s'\) (overlaps with replay error).
- **Schema.** Report field: `g_dyn` (float or null), optional `g_dyn_method`.

### 3.2 G_perc(Ms, Mr)

- **Definition.** Divergence between **observation** distributions: sim \(O_s(o|s)\) vs real \(O_r(o|s)\).
- **Interpretation.** High G_perc ⇒ perception gap (sensors, rendering, noise).
- **Implementation options.**  
  - **Vision:** FID, KID, SSIM (placeholders acceptable until full impl).  
  - **Other sensors:** Compare mean/cov or simple stats of observations.
- **Schema.** Report fields: `g_perc`, optional `fid`, `kid`, `ssim` (nullable).

### 3.3 G_perf(Ms, Mr, π)

- **Definition.**  
  \[
  G_{\mathrm{perf}}(M_s, M_r, \pi) = \bigl| J_{\mathrm{sim}}(\pi) - J_{\mathrm{real}}(\pi) \bigr|
  \]  
  where \(J\) is task return (e.g. success rate or cumulative reward).
- **Interpretation.** Direct sim-vs-real performance gap for policy \(\pi\).
- **Proxy when no real data.** Use "proxy real" dataset or assume \(J_{\mathrm{real}} = \alpha \cdot J_{\mathrm{sim}}\) (e.g. \(\alpha = 0.8\)) for benchmarking.
- **Schema.** Report field: `g_perf` or `g_perf_proxy`; optional `j_sim`, `j_real`.

### 3.4 SRCC (Sim-to-Real Correlation Coefficient)

- **Definition.** Pearson correlation between **sim performance** and **real performance** across policies (or seeds/DR samples):  
  \[
  \rho = \frac{\operatorname{Cov}(J_s, J_r)}{\sigma_{J_s} \sigma_{J_r}}
  \]
- **Use.** High SRCC ⇒ sim improvements translate to reality; low ⇒ large reality gap.
- **Implementation.** `compute_srcc_placeholder(sim_success_rates, real_success_rates)` in `apps/sim/eval/metrics.py`; wire to benchmark when multiple policies/runs available.
- **Schema.** `metrics.srcc` (float or null), optional `srcc_confidence_interval`.

### 3.5 Offline Replay Error

- **Definition.** Execute **real** robot trajectories (action sequences) in **sim** open-loop; measure state deviation (e.g. position/velocity error over time).
- **Use.** Large error ⇒ missing dynamics or sensor/actuation modeling.
- **Math.** e.g. mean L2 over time:  
  \[
  \text{replay\_error} = \frac{1}{T}\sum_t \|s^{\mathrm{sim}}_t - s^{\mathrm{ref}}_t\|_2
  \]  
  or max error, per-step error; document units (e.g. metres).
- **Implementation.** `compute_replay_error_placeholder(real_actions, sim_states_after_replay, reference_states)` in `apps/sim/eval/metrics.py`; full pipeline: load real action log → run in sim → compare to reference states.
- **Schema.** `metrics.replay_error`, `replay_error_units`.

### 3.6 Task Metrics

- **Success rate.** Percentage of runs that meet task success criteria.
- **Cumulative reward.** Sum of rewards per episode when reward is defined.
- **Schema.** `metrics.task_success_rate`, `metrics.cumulative_reward`, optional `episode_lengths`.

### 3.7 Step Stability / Integrator

- **Log in run config and report:** integrator type (e.g. "euler"), timestep `dt`, optional step stability / accumulated error risk.
- **Purpose.** Reproducibility and debugging of numerical behaviour.

---

## 4. Core Algorithms and Interfaces

### 4.1 PhysicsAdapter (PhysicsEngine)

- **Interface.**  
  - `step(dt: float) -> None`  
  - `get_state() -> dict` (positions, velocities, etc., SI units)  
  - `set_state(state: dict) -> None`  
  - `apply_action(action: dict, dt: float) -> None`  
  - Optional: `get_diagnostics() -> dict` (contacts, forces) for Q-Plugin and residual.
- **Implementations.** PyBullet adapter (with URDF load), stub for tests/demo. No engine-specific types in sim core; neutral representation only.
- **Conformance.** Deterministic step for fixed seed; state get/set round-trip.

### 4.2 Q-Plugin (Quantum-Stochastic Layer)

- **Role.** Intercept \((s_t, a_t, \mathrm{diagnostics})\) and sample **stochastic perturbations** to state (or observations).
- **Contract.**  
  - Input: current state, action, engine diagnostics (e.g. contact count).  
  - Output: perturbed state (e.g. joint positions + noise).  
  - Support **state-dependent** and **non-Gaussian** noise; optional "quantum surface friction collapse" concept (e.g. contact count modulates noise).
- **Reproducibility.** All sampling via seeded RNG; quantum path seedable when using simulator backend.
- **Classical fallback.** When Qiskit unavailable or disabled: e.g. Gaussian or Laplace noise with state/diagnostics-dependent \(\sigma\).

### 4.3 ResidualModel

- **Formula.**  
  \[
  s'_{\mathrm{next}} = s'_{\mathrm{engine}} + f_\theta(s_t, a_t, o_t)
  \]  
  where \(s'_{\mathrm{engine}}\) is physics step output and \(f_\theta\) is learned (or stub) residual.
- **Interface.**  
  - `predict_delta(state, action, obs) -> delta_state`  
  - Keys of `delta_state` match state (e.g. `joint_positions`); add element-wise to engine state.
- **Stub.** Zero delta; training hook can replace with MLP or other model.
- **Integration.** In runner: after physics + optional Q-Plugin, compute delta and add to state; push corrected state back to physics for next step.

### 4.4 AdversarySearch (SAGE-like)

- **Role.** Find parameter sets that **maximize** G_perf (worst-case for robust training).
- **Procedure.**  
  1. Param bounds (e.g. friction, mass, noise scale).  
  2. Sample \(N\) param sets.  
  3. For each: run sim (via provided `run_fn`), compute G_perf (or proxy).  
  4. Return params with **max** G_perf and optionally full list of results.
- **Interface.**  
  - `run(run_fn, g_perf_fn?) -> { worst_params, worst_g_perf, all_results }`  
  - `run_fn(params) -> run_result`; `g_perf_fn(run_result) -> float` optional.

### 4.5 SensorSuite (Sensors)

- **Per-sensor.** Noise model (configurable scale), optional **latency** (e.g. N-step buffer), optional **degrade** (camera: extra blur/noise for sim-to-real).
- **Interface.** `observe(state, t, rng?) -> observation`; when `rng is None` output is deterministic.
- **Latency.** Implement as wrapper: buffer last \(N\) observations; return observation from \(N\) steps ago.
- **Contracts.** Observations conform to schema; no engine-specific types in core.

### 4.6 Sim Core Step Semantics

- **Deterministic.** `step(action)`: no randomness; same \((s, a)\) ⇒ same \(s'\), \(o\).
- **Stochastic.** `step_stochastic(action)`: sensors (and optionally physics) may use RNG; seed fixes outcome.
- **Quantum-stochastic.** `step_quantum(action)`: engine step then Q-Plugin perturbation; diagnostics passed to Q-Plugin; seed fixes outcome.
- **Residual.** Applied in runner after step: \(s' \leftarrow s' + \mathrm{residual.predict\_delta}(s, a, o)\).

---

## 5. API Specifications

Base URL: `/api`. All request/response bodies validated (e.g. Pydantic). See `docs/api.md` for versioning and auth.

| Method | Path | Purpose | Request / Response |
|--------|------|---------|--------------------|
| GET | /api/health | Liveness | `{ status, service }` |
| POST | /api/projects | Create project | Body: `{ name, description? }` → `{ project_id, name, description? }` |
| GET | /api/projects | List projects | → `{ projects: [...] }` |
| POST | /api/assets/import | Import URDF/USD/mesh | File upload → `{ asset_id, path, type }` |
| GET | /api/assets | List assets | → `{ assets: [{ asset_id, path, type }] }` |
| POST | /api/design/segment | Mesh → parts | Body: asset_id or mesh → `{ parts: [...] }` (stub: single or simple split) |
| POST | /api/design/linkage | Parts graph → linkage / URDF | Body: parts + edges/joint types → linkage spec; optional export to URDF |
| POST | /api/sim/run | Start sim run | Body: `project_id, urdf_path, steps?, dt?, seed?, use_q_plugin?, use_residual?, reality_profile?` → run metadata |
| GET/POST | /api/sim/step | Optional single step | run_id + step once → new state/obs (for single-step control) |
| GET | /api/sim/metrics/{run_id} | Metrics for run | → metrics JSON |
| GET | /api/sim/metrics (stream) | Live metrics | SSE or WebSocket: step time, inference, quantum, etc. |
| GET | /api/sim/report/{run_id} | Full report | → report JSON (config, metrics, timeline, integrator, G_*) |
| GET | /api/reality-profiles | List profiles | → `{ profiles: [{ id, name, description }] }` |

**Reality profile in run.** POST /api/sim/run accepts `reality_profile` (string id); runner loads profile (YAML/JSON) and applies `physics` (gravity, friction, restitution, timestep), `sensors` (latency_steps, noise_scale, camera_degrade), and `gap_knobs` to the run.

---

## 6. Contracts and Schemas

- **Run.** `run_id`, `status`, `created_at`, `config_snapshot`, `seeds`, `git_hash`, `asset_versions`, `metrics_summary`, `reality_profile`, `gap_knobs`. See `contracts/v1/run.json`.
- **Metrics.** `run_id`, `srcc`, `replay_error`, `replay_error_units`, `task_success_rate`, `cumulative_reward`, `fid`, `kid`, `ssim`, `computed_at`. See `contracts/v1/metrics.json`.
- **Reality profile.** `reality_profile`, `physics_config`, `sensors_config`, `gap_knobs`. See `contracts/v1/reality_profile.json`.
- **Replay bundle.** `run_id`, `config`, `seeds`, `initial_state`, `actions[]`; sufficient to re-run deterministically.
- **Gap knobs.** Nested: physics (mass, friction, restitution), sensors (noise, latency, gain), actuation (delay, jitter), etc.

---

## 7. UI/UX Specifications

- **Toolbar.** Play / Pause / Step / Reset, Scene, Import, Export, Profiles, AI Tools.
- **Scene tree.** Hierarchical: robot links/joints, env objects, sensors; select → inspector.
- **Viewport.** Three.js; optional overlays: forces, uncertainty clouds, contact points; camera: orbit, pan, zoom.
- **Inspector.** Physics params, noise params, sensors, controller; editable; sync to run config or asset.
- **Console.** Structured logs (timestamp, severity, component).
- **Metrics panel.** Latency, sim step time, inference time, quantum time, ROS msg latency (placeholders OK).
- **Mechanism Picker.** Classical DR / Bayesian / adversarial / Q-Plugin / residual on-off; send to POST /api/sim/run.

---

## 8. Design Mode and AI Workflow

- **Design pipeline.** Mesh import → segment (mesh → parts) → linkage (parts + edges/joint types) → optional NLP function assignment ("this part is gripper", "this joint is hinge") → export URDF/SDF/USD.
- **Task spec schema.** JSON: goal, constraints, reward spec, task type.
- **Planner.** Task spec → high-level plan: controller skeleton, reward spec, env modifiers, evaluation plan (structured JSON).
- **Review UI.** Show generated plan/code; Approve / Reject / Edit; **no execution** of generated code without explicit Approve.
- **Model registry.** By task (VLA, policy, perception, planner); config: local/remote, device, cache; uniform: `predict_action(obs, goal)`, `plan(goal, scene)`, `perceive(sensor_data)`.

---

## 9. Implementation Phases (Summary)

| Phase | Content |
|-------|--------|
| 3 | Reality Profiles: YAML/JSON, loader, apply in runner to physics + sensors. |
| 4 | Q-Plugin: state-dependent and non-Gaussian noise; sensors: latency, degrade; contracts: reality_profile, gap_knobs. |
| 5 | ResidualModel (predict_delta stub) + AdversarySearch (param sweep, worst-case G_perf); integrate residual in runner. |
| 6 | Design: /api/design/segment, /api/design/linkage; optional NLP; export URDF; Design page UI. |
| 7 | AI: task spec schema, planner stub, review UI; model registry (stub per category). |
| 8 | Benchmarks: G_dyn, G_perc (placeholders OK), G_perf + proxy real; report: integrator, step_stability_risk, G_*; dashboard: last report, run detail with G_*. |
| Cross-cutting | Contracts for design/task_spec/plan; safety (review UI, no exec without approve); API consistency; metrics stream (SSE/WS). |

---

## 10. File and Module Reference

| Spec / logic | File(s) |
|--------------|--------|
| Run config, seeds, report | `apps/sim/runner/qers_runner.py` |
| Physics interface | `apps/sim/sim/physics/base.py` |
| PyBullet adapter | `apps/sim/sim/physics/pybullet_adapter.py` |
| Q-Plugin | `apps/sim/sim/quantum/q_plugin.py` |
| Residual | `apps/sim/sim/residual/base.py`, `stub.py` |
| Adversary | `apps/sim/sim/adversary/search.py` |
| Sensors, latency | `apps/sim/sim/sensors/*.py`, `latency_wrapper.py` |
| SRCC, replay error, metrics | `apps/sim/eval/metrics.py` |
| G_perf proxy, benchmarks | `qers/benchmarks/run_all.py` |
| Reality profiles | `apps/sim/profiles/loader.py`, `examples/reality_profiles/*.yaml` |
| API | `apps/api/main.py` |
| Contracts | `contracts/v1/*.json` |
| Evaluation and report format | `docs/evaluation.md` |
| Plan (full requirements) | `.cursor/plans/qers_requirements_to_success_*.plan.md` (or repo copy) |

This reference should be updated when the plan or contracts change so that implementations stay aligned with the intended functions, specifications, logic, and math.
