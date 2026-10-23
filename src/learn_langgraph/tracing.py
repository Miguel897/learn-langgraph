"""Optional Langfuse tracing. Everything here is a no-op until LANGFUSE_PUBLIC_KEY
and LANGFUSE_SECRET_KEY are set (plus LANGFUSE_BASE_URL for a self-hosted server)."""
import os
from typing import Any

from . import config  # noqa: F401  (loads .env so the LANGFUSE_* keys are visible)


def langfuse_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def tracing_config(trace_id: str | None = None) -> dict[str, Any]:
    """A RunnableConfig that sends the run to Langfuse, or {} when disabled.
    Pass a trace_id to group several invocations (and later scores) in one trace."""
    if not langfuse_enabled():
        return {}
    from langfuse.langchain import CallbackHandler

    handler = CallbackHandler(trace_context={"trace_id": trace_id} if trace_id else None)
    return {"callbacks": [handler]}
