"""OTLP/JSON span exporter for Stratos AI.

Traceloop's Python exporter defaults to OTLP *protobuf* at ``<endpoint>/v1/traces``;
Stratos ingests OTLP *JSON* at ``/api/ingest``. This exporter serialises spans to the
exact JSON shape Stratos parses and POSTs them there — mirroring the Node SDK.
"""
import json
import urllib.request

from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult


def _attr(key, value):
    if isinstance(value, bool):
        val = {"boolValue": value}
    elif isinstance(value, int):
        val = {"intValue": str(value)}
    elif isinstance(value, float):
        val = {"doubleValue": value}
    elif isinstance(value, (list, tuple)):
        val = {"stringValue": json.dumps(list(value))}
    else:
        val = {"stringValue": str(value)}
    return {"key": key, "value": val}


class StratosSpanExporter(SpanExporter):
    def __init__(self, url, token):
        self.url = url
        self.token = token

    def export(self, spans):
        try:
            svc = "otel-agent"
            out = []
            for s in spans:
                ctx = s.get_span_context()
                res = dict((s.resource.attributes if s.resource else {}) or {})
                if res.get("service.name"):
                    svc = res["service.name"]
                out.append({
                    "traceId": format(ctx.trace_id, "032x"),
                    "spanId": format(ctx.span_id, "016x"),
                    "name": s.name,
                    "startTimeUnixNano": str(s.start_time),
                    "endTimeUnixNano": str(s.end_time),
                    "attributes": [_attr(k, v) for k, v in dict(s.attributes or {}).items()],
                })
            body = {"resourceSpans": [{
                "resource": {"attributes": [_attr("service.name", svc)]},
                "scopeSpans": [{"spans": out}],
            }]}
            data = json.dumps(body).encode("utf-8")
            req = urllib.request.Request(
                self.url, data=data, method="POST",
                headers={"Content-Type": "application/json", "x-stratos-token": self.token},
            )
            urllib.request.urlopen(req, timeout=8).read()
            return SpanExportResult.SUCCESS
        except Exception:
            return SpanExportResult.FAILURE

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis=30000):
        return True
