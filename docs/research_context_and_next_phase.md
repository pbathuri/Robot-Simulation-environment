# Research Context & Next Phase

This document grounds the ai-tracking (LABLAB/QERS) platform in the robotics and sim2real literature you provided. Use it before the next development phase so design choices align with established practice.

---

## What We're Building (Recap)

- **Simulator core:** Physics adapters (PyBullet/stub), sensors with noise/DR, optional quantum-stochastic layer; deterministic and stochastic stepping; replay and telemetry per run.
- **Job system:** Celery + Redis; async sim runs with status, metrics, report, cancel; sync fallback when no Redis.
- **API & UI:** REST for runs, job status, metrics, reports; Next.js dashboard (runs list, run detail, sim viewport, design/models/benchmarks placeholders).
- **Sim2real stance:** Reduce the reality gap via stochastic modeling, domain randomization, system identification, residual learning, and standardized evaluation (SRCC, replay error, task metrics). See `docs/sim2real_playbook.md` and `docs/evaluation.md`.

---

## Literature Mapping

### 1. Capsules Bot – Robotics Projects (Blog)

[Robotics Projects: Navigation, Mapping, Control, Deep RL and others](https://capsulesbot.com/blog/2018/06/11/robotics-projects.html) outlines a typical robotics pipeline:

- **Perception** → **Decision** → **Control** (e.g. rover: perception pipeline → wall-follower / decision step → actuation).
- Stack: ROS, Gazebo, RViz, MoveIt!; localization (AMCL), SLAM (rtabmap), deep RL for manipulation.
- Lessons: tune many parameters (AMCL, costmaps, planners); sim-only then port to real; follow-me / segmentation (FCN) for drones.

**Alignment with our repo:** Our sim core + sensors + control/policies map to the same pipeline. Reality profiles and gap knobs (physics, sensors, actuation) are our way of encoding the “dozens of parameters” and tuning for transfer. Design mode and AI text→algorithm fit into the “design control software / behaviors” part of that workflow.

---

### 2. Ligot & Birattari (LigBir2019SI) – Pseudo-Reality & Reality Gap

**Source:** *Simulation-only experiments to mimic the effects of the reality gap in the automatic design of robot swarms* (Ligot & Birattari).

- **Reality gap:** Performance drop and **rank inversion** when control software designed in simulation is evaluated in reality (or in a second simulation).
- **Pseudo-reality:** A second simulation model M_B used as a stand-in for “reality.” Design on M_A, evaluate on M_B; the gap is simulated, not physical.
- **Finding:** The drop is not necessarily because “reality is more complex.” It can be explained by **overfitting to design conditions**; the same phenomenon appears when swapping roles (design on M_B, evaluate on M_A).
- **Methodological takeaway:** Use **multiple pseudo-realities** (models sampled around the design model) to assess robustness of design methods and infer robustness to the real reality gap.

**Alignment:** Our “reality profiles” (e.g. `examples/reality_profiles/*.yaml`) and gap knobs are a way to define **multiple evaluation contexts** (pseudo-realities). A natural next step is to support **multi-profile evaluation**: run the same scenario/config across several reality profiles and compare metrics (e.g. performance drop, rank stability) as in Ligot & Birattari.

---

### 3. Golemo et al. (golemo18a) – Neural-Augmented Simulation (NAS)

**Source:** *Sim-to-Real Transfer with Neural-Augmented Robot Simulation* (CoRL 2018).

- **Idea:** Learn a **residual model** φ(s, a, h) = real_state − sim_state (LSTM) from paired sim/real rollouts; use it to **augment the simulator** during policy learning so that policies see “corrected” states.
- **Benefits:** Policy learns in sim but with a sim that has been grounded in real data; one learned correction can serve **multiple tasks** (multi-task sim2real).
- **Contrast:** Pure forward model (no sim) compounds error; NAS corrects sim and reuses it.

**Alignment:** Our playbook already mentions “residual learning” and “system identification.” A possible extension is an optional **NAS-style module**: train a small model on (sim_state, action) → state_delta (or observation_delta) from real or high-fidelity logs, and apply it inside the runner so that evaluation (or training) uses an augmented sim. This fits under “gap-overcoming” and “residual models” in `docs/sim2real_playbook.md`.

---

### 4. SIM2REALVIZ – Visualizing the Sim2Real Gap

**Source:** *SIM2REALVIZ: Visualizing the Sim2Real Gap in Robot Ego-Pose Estimation* (Jaunet et al., XAI4Debugging@NeurIPS 2021).

- **Goal:** Help experts **understand and reduce** the sim2real gap for ego-pose (and similar) models via **visual analytics**.
- **Features:** Compare SIM vs REAL predictions (e.g. on a 2D geo-map); heatmaps (grad-CAM, occlusion, feature-distance) to see what the model attends to; identify biases (e.g. regression to mean) and sensitivity to layout (e.g. moved objects, doors).
- **Loop:** Use insights to adjust simulator (e.g. remove misleading objects), add filters (e.g. brightness), or refine domain randomization.

**Alignment:** Our dashboard already shows runs, metrics, and a sim viewport. A **gap-visualization** direction would be: when we have sim vs real (or sim vs pseudo-reality) trajectories or predictions, show side-by-side or overlaid (e.g. geo-map or timeline), plus simple attention/error heatmaps if we have model internals. That supports the “identify sources of the gap” and “close the loop” steps in our playbook.

---

### 5. Luis Scheuch (PA_Luis-Scheuch) – Sim-to-Real Survey (Legged / NAO)

**Source:** *Sim-to-Real Transfer for Locomotion Tasks on Legged Robots: A Survey* (Luis Scheuch, 2025).

- **Findings:** **Domain randomization** is the most common technique; successful transfer usually combines **multiple techniques** (system ID, observation design, DR, curriculum, simulation grounding, etc.). **Hardware constraints** (e.g. NAO) drive method choice.
- **Pipeline:** System identification → observation design (e.g. I/O history) → domain randomization → curriculum learning → simulation grounding (e.g. GSL/GAT) → online system ID → predictive control.

**Alignment:** Our playbook and architecture already reflect this: we have gap knobs (DR), calibration/system ID, and contracts for observations/actions. The **seven-step loop** in `docs/sim2real_playbook.md` and the **reality-profile + eval** design are consistent with a multi-technique, pipeline-oriented approach. Next phases can explicitly add: curriculum (e.g. difficulty in scenarios), optional **grounded simulation** (NAS or GAT-style correction), and clearer observation/action contracts for different platforms.

---

## Next Phase: Suggested Alignment

When choosing the next phase (CI, Railway, model registry, UI layout, observability, benchmarks, design-mode pipeline, AI text→algorithm), the following keep the product aligned with the literature:

1. **Pseudo-reality / multi-profile evaluation (Ligot & Birattari)**  
   - Support running the same scenario against **multiple reality profiles**; aggregate and compare metrics (e.g. performance drop, rank) to assess robustness without real hardware.

2. **Gap visualization (SIM2REALVIZ-style)**  
   - When sim vs real (or sim vs pseudo-reality) data exists, add **comparison views** (e.g. trajectories or key metrics on a map/timeline) and, if applicable, simple error/attention heatmaps to help experts pinpoint gap sources.

3. **Residual / NAS-style augmentation (Golemo et al.)**  
   - Optional **residual correction** trained from real or high-fidelity logs, applied in the runner to produce an augmented sim for evaluation or training; document in playbook as one of the “gap-overcoming” options.

4. **Pipeline and contracts (Scheuch + playbook)**  
   - Harden **observation/action contracts** and **reality-profile schema** so they support system ID, DR, and (later) curriculum and grounded simulation in a single pipeline.

5. **Robotics pipeline (Capsules Bot)**  
   - Keep a clear **perception → decision → control** boundary in the sim and in the UI (e.g. design mode for “control software,” models for perception/policy), so the stack stays recognizable to robotics practitioners.

---

## References (Short)

- Capsules Bot: [Robotics Projects](https://capsulesbot.com/blog/2018/06/11/robotics-projects.html).
- Ligot, A., Birattari, M.: *Simulation-only experiments to mimic the effects of the reality gap in the automatic design of robot swarms* (LigBir2019SI).
- Golemo, F., et al.: *Sim-to-Real Transfer with Neural-Augmented Robot Simulation* (CoRL 2018, golemo18a).
- Jaunet, T., et al.: *SIM2REALVIZ: Visualizing the Sim2Real Gap in Robot Ego-Pose Estimation* (XAI4Debugging@NeurIPS 2021).
- Scheuch, L.: *Sim-to-Real Transfer for Locomotion Tasks on Legged Robots: A Survey* (PA_Luis-Scheuch, 2025).

Internal: `docs/sim2real_playbook.md`, `docs/evaluation.md`, `docs/architecture.md`, `docs/qers_spec_reference.md`.
