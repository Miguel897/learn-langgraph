"""Settings loaded from environment variables (and a local .env file)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama").lower()

    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3:4b-instruct")
    ollama_embed_model: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    ollama_num_ctx: int = int(os.getenv("OLLAMA_NUM_CTX", "4096"))

    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")


@lru_cache
def get_settings() -> Settings:
    return Settings()
