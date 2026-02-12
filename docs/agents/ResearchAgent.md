# ResearchAgent

**Role:** Paper-to-implementation translation and LLM-assisted research.

## Scope

- Use LLM research tools (`tools/llm_research/`) for summarization, derivation, implementation plans.
- Provider-agnostic interface; caching and citation capture.
- Prompt templates for math derivations, literature summary, formula verification, implementation plans.
- No secrets in prompts or logs.

## Outputs

- New prompt templates or provider integrations in `tools/llm_research/`.
- Documentation of procedures and verification steps.
- Citations stored with source URLs/DOIs where available.

## Acceptance

- Multi-provider queries work via single interface.
- Cache and citations are stored in defined paths; no API keys in logs.
