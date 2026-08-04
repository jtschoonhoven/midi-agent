"""Startup configuration tests."""

from api import main


def test_weave_export_is_optional_without_wandb_key(monkeypatch):
    monkeypatch.setenv("WEAVE_TRACING", "true")
    monkeypatch.setenv("PROJECT_ID", "example/midi-agent")
    monkeypatch.delenv("WANDB_API_KEY", raising=False)
    monkeypatch.setattr(main.weave, "init", lambda _: (_ for _ in ()).throw(AssertionError("should not initialize")))

    main.init_weave_observability()
