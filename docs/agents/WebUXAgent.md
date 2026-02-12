# WebUXAgent

**Role:** Web dashboard and operator UX.

## Scope

- Next.js app: runs list, run detail, metrics chart placeholder, teleop placeholder.
- Data from API only; no simulation state in frontend.
- Responsive, accessible controls; clear labels and tooltips.

## Outputs

- Pages and components in `apps/web/src/`.
- API client types aligned with contracts (when generated).
- Documentation of UI contracts in `docs/api.md`.

## Acceptance

- Runs list and run detail load from API and display correctly.
- Teleop placeholder calls API endpoints (e.g. start run); no hard-coded state.
