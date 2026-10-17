"""00 - Check that the environment works before running the other demos.

Verifies: Ollama is reachable, the configured models are pulled, and one
chat call round-trips.  Run:  uv run demos/00_check_setup.py
"""
import json
import urllib.request

from learn_langgraph import get_chat_model, get_settings, header

s = get_settings()
header(f"Provider: {s.llm_provider}")

if s.llm_provider == "ollama":
    try:
        with urllib.request.urlopen(f"{s.ollama_base_url}/api/tags", timeout=5) as r:
            models = [m["name"] for m in json.load(r)["models"]]
    except OSError as e:
        raise SystemExit(
            f"Cannot reach Ollama at {s.ollama_base_url} ({e}).\n"
            "Start it with:  docker start ollama"
        )
    print("Ollama models:", ", ".join(models))
    for wanted in (s.ollama_model, s.ollama_embed_model):
        tag = wanted if ":" in wanted else f"{wanted}:latest"
        status = "OK" if tag in models else f"MISSING -> docker exec ollama ollama pull {wanted}"
        print(f"  {wanted:<25} {status}")

header("One chat call")
reply = get_chat_model().invoke("Reply with exactly: setup works")
print(reply.content)
print("usage:", reply.usage_metadata)
