# intelli-1113-stratos-sdk (Python)

One import for **Stratos AI**: [OpenLLMetry](https://traceloop.com/docs/openllmetry) agent
telemetry (tokens, cost, prompts, tools) + a heartbeat that auto-reports **framework / model /
tools** — the Python twin of `@intelli-1113/stratos-sdk` (Node).

## Install
```bash
pip install intelli-1113-stratos-sdk
```

## Configure (environment)
```bash
STRATOS_TOKEN=<token from Stratos → Add agent>   # required
STRATOS_URL=https://stratos.lnt.com              # optional, default http://localhost:4000
STRATOS_APP_NAME=my-agent                         # optional display name
STRATOS_MODEL=gpt-4o                              # optional (else detected from spans/env)
STRATOS_TOOLS=search,lookup                       # optional comma list
```

## Use — pick one
```python
import stratos_sdk.register        # FIRST import in your entrypoint (before openai/langchain/…)
```
```python
from stratos_sdk import start       # or call explicitly
start()                              # or start(token=..., url=..., app_name=..., tools=[...])
```

## What it does
- Initialises OpenLLMetry and exports spans as **OTLP-JSON to `/api/ingest`** (custom exporter).
- **Heartbeat** keeps the agent online and auto-fills **framework** (detected from your project
  deps / installed packages: google-adk, openai-agents, llamaindex, crewai, langgraph, langchain,
  anthropic, openai…), **model** (env), and **tools** (`STRATOS_TOOLS` or captured from spans).
- URL/token come from env — change and restart, no code edit.

> If `traceloop-sdk` isn't installed, the SDK still sends the heartbeat + metadata (agent shows
> online with framework/model), just without per-call spans.
