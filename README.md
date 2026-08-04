# midi-agent

Compose and perform MIDI using natural language prompts

## LangSmith tracing

The API traces MIDI-generation runs, model calls, and tool calls to LangSmith when
`LANGSMITH_API_KEY` is set. `LANGCHAIN_API_KEY` is also accepted for compatibility
with older LangChain configuration. Traces use the `midi-agent` project by default;
override it with `LANGSMITH_PROJECT`. Set `LANGSMITH_TRACING=false` to disable
exporting without removing the key. It uses the AWS endpoint by default; override
it with `LANGSMITH_ENDPOINT` for another LangSmith deployment.

The previous Weave/W&B exporter is disabled by default so missing or stale W&B
credentials cannot block API startup. Set `WEAVE_TRACING=true` only when its
`PROJECT_ID` and `WANDB_API_KEY` are configured.

## License

This project is licensed under the GNU General Public License v3.0 only (GPL-3.0-only).

You may contact the copyright holder to request an alternative license agreement.

Copyright (c) 2026 Jonathan Schoonhoven
