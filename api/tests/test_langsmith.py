"""Tests for LangSmith environment configuration."""

from api import langsmith


def test_configure_tracing_accepts_legacy_langchain_key(monkeypatch):
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.setenv("LANGCHAIN_API_KEY", "test-key")
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGSMITH_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)
    monkeypatch.delenv("LANGSMITH_ENDPOINT", raising=False)

    assert langsmith.configure_tracing() is True
    assert langsmith.os.environ["LANGSMITH_API_KEY"] == "test-key"
    assert langsmith.os.environ["LANGSMITH_TRACING"] == "true"
    assert langsmith.os.environ["LANGSMITH_TRACING_V2"] == "true"
    assert langsmith.os.environ["LANGSMITH_PROJECT"] == "midi-agent"
    assert langsmith.os.environ["LANGSMITH_ENDPOINT"] == "https://aws.api.smith.langchain.com"


def test_configure_tracing_respects_disabled_setting(monkeypatch):
    monkeypatch.setenv("LANGSMITH_API_KEY", "test-key")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")

    assert langsmith.configure_tracing() is False
