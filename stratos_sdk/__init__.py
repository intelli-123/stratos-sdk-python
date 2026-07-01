"""@intelli-1113/stratos-sdk (Python) — stream OpenLLMetry telemetry to Stratos AI.

Config from env (so URL/token change without code edits):
  STRATOS_TOKEN      enrollment token from Stratos "Add agent"   (required)
  STRATOS_URL        Stratos origin (default http://localhost:4000)
  STRATOS_APP_NAME   display name for this agent
  STRATOS_MODEL      optional model hint (else detected from spans/env)
  STRATOS_TOOLS      optional comma list of tool names
  STRATOS_HEARTBEAT_MS  liveness interval (default 30000)

Usage:
  import stratos_sdk.register     # first import in your entrypoint, or
  from stratos_sdk import start; start()
"""
import importlib.util
import json
import os
import threading
import time
import urllib.request

_started = False


def _post(url, token, body=None):
    try:
        data = json.dumps(body or {}).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/json", "x-stratos-token": token},
        )
        urllib.request.urlopen(req, timeout=5).read()
    except Exception:
        pass


def _installed(mod):
    try:
        return importlib.util.find_spec(mod) is not None
    except Exception:
        return False


def _agent_deps():
    """Direct deps declared in the project (most reliable framework signal)."""
    names = set()
    try:
        with open("requirements.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                for sep in ("==", ">=", "<=", "~=", ">", "<", "[", " "):
                    line = line.split(sep)[0]
                if line:
                    names.add(line.strip().lower())
    except Exception:
        pass
    try:
        import tomllib  # py3.11+
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        deps = data.get("project", {}).get("dependencies", []) or []
        poetry = (((data.get("tool") or {}).get("poetry") or {}).get("dependencies") or {})
        for d in list(deps) + list(poetry.keys()):
            n = str(d)
            for sep in ("==", ">=", "<=", "~=", ">", "<", "[", " "):
                n = n.split(sep)[0]
            if n:
                names.add(n.strip().lower())
    except Exception:
        pass
    return names


def _detect_framework():
    deps = _agent_deps()

    def has(pkg, mod=None):
        return pkg.lower() in deps or _installed(mod or pkg.replace("-", "_"))

    # Higher-level agent frameworks first (several pull in langchain transitively).
    if has("google-adk", "google.adk") or _installed("google.adk"):
        return "google-adk"
    if has("openai-agents", "agents"):
        return "openai-agents"
    if has("llama-index", "llama_index") or _installed("llama_index"):
        return "llamaindex"
    if has("crewai"):
        return "crewai"
    if has("langgraph"):
        return "langgraph"
    if has("langchain"):
        return "langchain"
    if has("google-generativeai", "google.generativeai") or has("google-genai", "google.genai"):
        return "google-genai"
    if has("anthropic"):
        return "anthropic"
    if has("openai"):
        return "openai"
    return None


def _detect_model(model):
    if model:
        return model
    for k in ("STRATOS_MODEL", "OPENAI_MODEL", "ANTHROPIC_MODEL", "GOOGLE_MODEL",
              "GEMINI_MODEL", "LLM_MODEL", "MODEL"):
        v = os.environ.get(k)
        if v:
            return v
    return None


def start(token=None, url=None, app_name=None, model=None, tools=None, heartbeat_ms=None):
    global _started
    if _started:
        return
    token = token or os.environ.get("STRATOS_TOKEN", "")
    origin = (url or os.environ.get("STRATOS_URL", "http://localhost:4000")).rstrip("/")
    app = app_name or os.environ.get("STRATOS_APP_NAME") or "agent"
    try:
        hb = int(heartbeat_ms or os.environ.get("STRATOS_HEARTBEAT_MS", 30000))
    except ValueError:
        hb = 30000

    if not token:
        print("[stratos] STRATOS_TOKEN not set — telemetry disabled. Add the token from Stratos > Add agent.")
        return
    _started = True

    ingest = origin + "/api/ingest"
    heartbeat_url = origin + "/api/heartbeat"

    # Initialise OpenLLMetry with our JSON exporter (optional — if traceloop-sdk
    # isn't installed the heartbeat/metadata still work, just without spans).
    try:
        from traceloop.sdk import Traceloop
        from .exporter import StratosSpanExporter
        Traceloop.init(app_name=app, disable_batch=True, exporter=StratosSpanExporter(ingest, token))
    except Exception as e:
        print(f"[stratos] OpenLLMetry init skipped ({e}); heartbeat only.")

    fw = _detect_framework()
    mdl = _detect_model(model)
    tls = tools or [t.strip() for t in os.environ.get("STRATOS_TOOLS", "").split(",") if t.strip()]
    meta = {"framework": fw, "model": mdl, "tools": tls}

    _post(heartbeat_url, token, meta)  # immediately → online right away

    if hb > 0:
        def loop():
            while True:
                time.sleep(hb / 1000.0)
                _post(heartbeat_url, token, meta)
        threading.Thread(target=loop, daemon=True).start()

    print(f"[stratos] telemetry -> {ingest} (heartbeat {hb}ms, framework={fw})")
