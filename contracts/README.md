# Contracts

Versioned schemas for cross-boundary data. Generate Python (Pydantic) and TypeScript types from JSON Schema here.

## Layout

- `v1/` – first version of run, step, replay_bundle, metrics, gap_knobs.
- Python models can live in `apps/sim/contracts/` or be generated into `contracts/python/`.
- TypeScript types can be generated into `apps/web/src/types/` or `contracts/ts/`.

## Generation (optional)

```bash
# Python (example with datamodel-codegen)
pip install datamodel-code-generator
datamodel-codegen --input contracts/v1/run.json --output apps/sim/contracts/run_v1.py

# TypeScript (example with json-schema-to-typescript)
npx json2ts -i contracts/v1/run.json -o apps/web/src/types/run.d.ts
```

For now, Pydantic models in `apps/sim/contracts/` and TS types in `apps/web` are kept in sync manually or via a single script; extend as needed.
