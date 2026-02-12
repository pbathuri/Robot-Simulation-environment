"""
Provider-agnostic LLM interface. Supports Gemini, Anthropic, Perplexity, OpenAI, Ollama.
API keys via env vars only; no secrets in logs.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

# Optional: actual API clients installed when needed
# import openai
# from anthropic import Anthropic
# etc.

CACHE_DIR = Path(__file__).resolve().parent / "cache"
CITATION_DIR = Path(__file__).resolve().parent / "citations"


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _prompt_hash(prompt: str, model: str) -> str:
    return hashlib.sha256(f"{model}:{prompt}".encode()).hexdigest()[:16]


def query_llm(
    provider: str,
    model: str,
    prompt: str,
    *,
    system: str | None = None,
    use_cache: bool = True,
    store_citation: bool = True,
) -> dict[str, Any]:
    """
    Send prompt to provider/model. Returns { "content": str, "citations": [], "from_cache": bool }.
    Placeholder: returns stub if no API key; real impl would call provider SDK.
    """
    cache_key = f"{provider}:{model}:{_prompt_hash(prompt, model)}"
    cache_path = CACHE_DIR / f"{cache_key}.json"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CITATION_DIR.mkdir(parents=True, exist_ok=True)

    if use_cache and cache_path.is_file():
        with open(cache_path) as f:
            data = json.load(f)
            data["from_cache"] = True
            return data

    # Placeholder: no API key => stub response
    api_key = _env("OPENAI_API_KEY") or _env("ANTHROPIC_API_KEY") or _env("GEMINI_API_KEY")
    if not api_key:
        out = {
            "content": f"[Stub] No API key set for {provider}. Set env var and retry.",
            "citations": [],
            "from_cache": False,
        }
    else:
        # Real impl would branch by provider and call SDK
        out = {
            "content": f"[Stub] Would call {provider}/{model}. Implement in provider.py.",
            "citations": [],
            "from_cache": False,
        }

    if store_citation and out.get("citations"):
        cite_path = CITATION_DIR / f"{cache_key}_citations.json"
        with open(cite_path, "w") as f:
            json.dump({"prompt_hash": cache_key, "citations": out["citations"]}, f, indent=2)

    if use_cache:
        to_cache = {**out, "from_cache": False}
        with open(cache_path, "w") as f:
            json.dump(to_cache, f, indent=2)

    return out


def get_prompt_template(name: str, **kwargs: str) -> str:
    """Load template from tools/llm_research/prompts/<name>.txt and format with kwargs."""
    path = Path(__file__).resolve().parent / "prompts" / f"{name}.txt"
    if not path.is_file():
        return f"[Template {name} not found]"
    return path.read_text().format(**kwargs)
