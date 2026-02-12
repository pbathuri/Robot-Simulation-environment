# Sim-to-Real Playbook

This playbook is enforced in docs and commands. Use it to close the reality gap systematically.

## Loop (7 Steps)

1. **Identify task variables**  
   Define required states, observations, and actions for the task. Document in scenario/contract.

2. **Implement baseline sim fidelity**  
   Get a working sim (physics + sensors + control) that can execute the task in sim. Establish a deterministic baseline (fixed seed).

3. **Gap-reduction**  
   - **Calibration:** Compare sim vs real logs where available; run system ID to update parameters (mass, inertia, friction, etc.).  
   - **Improve models:** Refine sensor models (noise, latency), actuation delays, and any known model errors.

4. **Gap-overcoming**  
   - **Domain randomization (DR):** Sample from "gap knobs" (mass, friction, restitution, noise, lighting, etc.) during training.  
   - **Adaptation:** If using adaptive policies, expose sim parameters as context.  
   - **Modular policies:** Prefer policies that rely on observable state and robust features.

5. **Train/test in parallel sims**  
   Run many sim instances (e.g. batch runner) with different DR samples; aggregate metrics.

6. **Evaluate in target env**  
   Deploy to real (or target) environment; collect success rate, rewards, and trajectory data.

7. **Iterate**  
   Use real performance and trajectory comparisons to update calibration, DR ranges, or residual models; retrain and repeat.

## Reality-Gap Taxonomy

Track and configure gaps explicitly:

- **Dynamics:** mass, inertia, friction, restitution, contact model, compliance.
- **Perception/sensing:** noise, latency, resolution, FOV, distortion, lighting.
- **Actuation/control:** delay, jitter, saturation, backlash, filter differences.
- **System/implementation:** packet loss, latency, timing, numerical precision.

Each module (physics, sensors, control) has a **gap knobs** config; see `/contracts` and scenario files.

## Commands That Implement the Playbook

- `/add_sim_task` – Add scenario + contracts + runner + metrics.
- `/run_batch_sims` – Run N sims with DR; store run bundles.
- `/compute_eval` – Compute SRCC, replay error, task metrics; publish to dashboard.
- `/calibrate_from_real` – Ingest real logs, parameter search, update sim params, record diff.

See `docs/cursor_skills_commands.md` for full command and skill definitions.

## Research context

For how this playbook relates to pseudo-reality evaluation (Ligot & Birattari), neural-augmented simulation (Golemo et al.), gap visualization (SIM2REALVIZ), and sim2real surveys (e.g. Scheuch), see **`docs/research_context_and_next_phase.md`**.
