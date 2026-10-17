"""Settings loaded from environment variables (and a local .env file)."""
import os
from dataclasses import dataclass, field
from functools import cache

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str):
    """Read the variable when a Settings instance is created, not at import time."""
    return field(default_factory=lambda: os.getenv(name, default))


@dataclass(frozen=True)
class Settings:
    llm_provider: str = _env("LLM_PROVIDER", "ollama")

    ollama_base_url: str = _env("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = _env("OLLAMA_MODEL", "qwen3:4b-instruct")
    ollama_embed_model: str = _env("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    ollama_num_ctx: int = field(default_factory=lambda: int(os.getenv("OLLAMA_NUM_CTX", "4096")))

    anthropic_model: str = _env("ANTHROPIC_MODEL", "claude-sonnet-5-5")

    def __post_init__(self) -> None:
        object.__setattr__(self, "llm_provider", self.llm_provider.lower())  # frozen dataclass


@cache
def get_settings() -> Settings:
    return Settings()
