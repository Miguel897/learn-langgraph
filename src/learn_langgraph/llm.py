"""Model factories so every demo can switch between Ollama and Anthropic via .env."""
from __future__ import annotations

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from .config import get_settings


def get_chat_model(temperature: float = 0.0, provider: str | None = None) -> BaseChatModel:
    """Return a LangChain chat model. Any model returned here supports
    `.invoke`, `.stream`, `.bind_tools` and `.with_structured_output`."""
    s = get_settings()
    provider = (provider or s.llm_provider).lower()

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=s.ollama_model,
            base_url=s.ollama_base_url,
            temperature=temperature,
            num_ctx=s.ollama_num_ctx,
            # Qwen3 "thinking" mode is slow on small GPUs; turn it off for the demos.
            reasoning=False,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=s.anthropic_model, temperature=temperature)

    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r} (use 'ollama' or 'anthropic')")


def get_embeddings() -> Embeddings:
    """Embeddings for the RAG demo (always local Ollama: free and fast)."""
    from langchain_ollama import OllamaEmbeddings

    s = get_settings()
    return OllamaEmbeddings(model=s.ollama_embed_model, base_url=s.ollama_base_url)
