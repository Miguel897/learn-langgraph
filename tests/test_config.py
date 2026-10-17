import pytest

from learn_langgraph import Settings


def test_settings_read_env_at_instantiation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "Anthropic")
    monkeypatch.setenv("OLLAMA_NUM_CTX", "2048")
    s = Settings()
    assert s.llm_provider == "anthropic"
    assert s.ollama_num_ctx == 2048


def test_explicit_values_override_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_MODEL", "from-env")
    assert Settings(ollama_model="explicit").ollama_model == "explicit"
