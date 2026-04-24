<div align="center">

# QERS · Quantum-Enhanced Robotics Simulator

**A robotics simulator that narrows the stochastic reality gap - classical macro-physics + a quantum-stochastic / adversarial / residual-learning micro layer, driven by an NLP "text → algorithm" workflow.**

<br/>

<img src="https://img.shields.io/badge/Physics-PyBullet%20%C2%B7%20MuJoCo-0D1117?style=for-the-badge&labelColor=161B22&color=FFA657" />
<img src="https://img.shields.io/badge/Quantum-Q--Plugin-0D1117?style=for-the-badge&labelColor=161B22&color=58A6FF" />
<img src="https://img.shields.io/badge/API-FastAPI-0D1117?style=for-the-badge&logo=fastapi&logoColor=58A6FF&labelColor=161B22" />
<img src="https://img.shields.io/badge/Web-Next.js%20%C2%B7%20Three.js-0D1117?style=for-the-badge&logo=nextdotjs&logoColor=58A6FF&labelColor=161B22" />
<img src="https://img.shields.io/badge/Registry-HuggingFace-0D1117?style=for-the-badge&logo=huggingface&logoColor=FFA657&labelColor=161B22" />

</div>

---

## TL;DR

> **Reinvent noise, not gravity.**

Macro-physics is solved. Real-world **stochasticity** isn't. QERS layers a quantum-noise plugin, a Bayesian sandbox, a SAGE adversary, and residual dynamics on top of standard physics engines - then lets you drive the whole thing from **NLP specs**.

---

## Key differentiators

- **Reinvent noise, not gravity** - build on PyBullet/MuJoCo, overlay Q-Plugin quantum noise + Bayesian sandbox + SAGE adversary + residual dynamics
- **POMDP-based gap metrics** - G_dyn, G_perc, G_perf
- **Design mode** - Mesh import → segmentation → linkage → URDF export via NLP
- **AI text → algorithm** - NLP spec → structured task JSON → planner → controller skeleton
- **Model registry** - HuggingFace models (VLA, policies, perception, planners)
- **Reality profiles** - configurable physics + sensor + actuation profiles

---

## Architecture

```mermaid
flowchart TB
    subgraph Web["Next.js · Three.js"]
        D[Dashboard] --- DG[Design] --- SM[Sim] --- MD[Models] --- BM[Benchmarks]
    end
    subgraph API["FastAPI"]
        P[/api/projects/] --- A[/api/assets/] --- DE[/api/design/] --- SI[/api/sim/]
    end
    subgraph Sim["Simulation core"]
        PH[Physics adapters<br/>PyBullet · MuJoCo] --- QP[Q-Plugin<br/>quantum noise] --- RES[Residual<br/>dynamics] --- ADV[SAGE<br/>adversary]
    end
    subgraph Ag["AI agents"]
        PL[Planner] --- CG[Controller gen] --- DA[Design assistant]
    end
    Web <--> API
    API --> Sim
    API --> Ag
    Ag --> Sim
```

---

## Repo layout

```
.cursor/rules/       Cursor rule files (.mdc)
contracts/           Versioned schemas
docs/                architecture · api · evaluation · design mode · AI workflow
apps/
  sim/               Simulation core - physics adapters, Q-Plugin, residual, adversary
  api/               FastAPI - /api/projects, /api/assets, /api/design, /api/sim
  web/               Next.js - Dashboard, Design, Sim, Models, Benchmarks (Three.js viewport)
  agents/            AI agents - planner, controller generator, design assistant
tools/
  llm_research/      Multi-LLM provider, caching, prompts
  benchmarks/        G_dyn, G_perc, G_perf computation
examples/            Demo URDFs, environments, reality profiles
runs/                Run outputs (created at runtime)
```

---

## Quick start

> Run everything from the repo root (where `Makefile` and `apps/` live).

```bash
python3 -m venv .venv
source .venv/bin/activate
make setup
```

Then, in two terminals (repo root, venv active):

```bash
# Terminal 1
make backend

# Terminal 2
make ui
```

Optional - example sim:

```bash
make demo
```

Open http://localhost:3000 → loads example robot → runs sim → shows metrics + logs.

### Platform notes

- **Multi-line paste into zsh** - run one command per line to avoid parse errors. Use `make setup` for a single install step. The UI step uses `pnpm` if available, else `npm` (Node.js must be installed).
- **Python 3.13 / macOS** - core install works without PyBullet or open3d. The sim uses **stub physics** when PyBullet isn't installed. For real physics: `pip install -r requirements-optional.txt` (pybullet may fail to build from source on macOS; use Docker or Python 3.11/3.12). No open3d 3.13 wheel yet.

### Docker (optional)

Not required for local dev. If Docker Desktop is installed, see the platform section of the docs for compose targets.

---

<div align="center">
<sub>Part of <a href="https://github.com/pbathuri">@pbathuri</a>'s <a href="https://github.com/pbathuri/Map_Projects_MAC">project portfolio</a> - robotics line.</sub>
</div>
