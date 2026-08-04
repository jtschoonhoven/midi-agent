"""LangSmith configuration shared by the API entrypoints."""

import logging
import os

log = logging.getLogger(__name__)

DEFAULT_PROJECT = "midi-agent"
DEFAULT_ENDPOINT = "https://aws.api.smith.langchain.com"


def configure_tracing() -> bool:
    """Enable LangSmith tracing when a LangSmith key is configured.

    ``LANGCHAIN_API_KEY`` is retained as a compatibility alias because older
    LangChain integrations used that name. LangSmith's current SDK reads
    ``LANGSMITH_API_KEY``.

    Returns whether a key was available and tracing was configured.
    """
    api_key = os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY")
    if not api_key:
        log.info("LangSmith tracing disabled: no LANGSMITH_API_KEY or LANGCHAIN_API_KEY configured")
        return False

    os.environ.setdefault("LANGSMITH_API_KEY", api_key)
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    # Current SDKs read LANGSMITH_TRACING; the V2 aliases support older releases.
    os.environ.setdefault("LANGSMITH_TRACING_V2", os.environ["LANGSMITH_TRACING"])
    os.environ.setdefault("LANGCHAIN_TRACING_V2", os.environ["LANGSMITH_TRACING"])
    os.environ.setdefault("LANGSMITH_PROJECT", DEFAULT_PROJECT)
    os.environ.setdefault("LANGSMITH_ENDPOINT", DEFAULT_ENDPOINT)

    if os.environ["LANGSMITH_TRACING"].lower() != "true":
        log.info("LangSmith tracing disabled by LANGSMITH_TRACING")
        return False

    log.info(
        "LangSmith tracing enabled (project=%s endpoint=%s)",
        os.environ["LANGSMITH_PROJECT"],
        os.environ["LANGSMITH_ENDPOINT"],
    )
    return True
