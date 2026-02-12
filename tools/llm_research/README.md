# LLM Research Tools

Multi-LLM calls (Gemini, Anthropic, Perplexity, OpenAI, Ollama) with provider-agnostic interface, caching, and citation capture.

## Usage

- Set env vars (see `.env.example`); never commit API keys.
- Use `query_llm(provider, model, prompt, options)` from `provider.py`.
- Prompt templates live in `prompts/`; cache and citations in `cache/` and response metadata.
