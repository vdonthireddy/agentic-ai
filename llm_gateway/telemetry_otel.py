"""
OpenTelemetry (OTel) Distributed Tracing & APM Export (llm_gateway/telemetry_otel.py).
Provides standard W3C trace context, span lifecycles, and latency waterfalls for LLM Gateway operations.
"""

import time
import uuid
from typing import Dict, Any, Optional
from contextlib import contextmanager

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource

    resource = Resource.create({"service.name": "agentic-ai-gateway", "service.version": "2.0.0"})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("agentic_ai.gateway")
    OTEL_AVAILABLE = True
except Exception:
    OTEL_AVAILABLE = False
    tracer = None

class GatewayTraceSpan:
    """Represents an OpenTelemetry execution span for gateway routing, tools, or supervisor agents."""

    def __init__(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        self.name = name
        self.span_id = f"span_{uuid.uuid4().hex[:8]}"
        self.trace_id = f"trace_{uuid.uuid4().hex[:16]}"
        self.attributes = attributes or {}
        self.start_time = 0.0
        self.end_time = 0.0
        self.duration_ms = 0.0
        self.otel_span = None

    def start(self):
        self.start_time = time.time()
        if OTEL_AVAILABLE and tracer is not None:
            try:
                self.otel_span = tracer.start_span(self.name, attributes=self.attributes)
            except Exception:
                pass
        return self

    def end(self, status: str = "OK", error: Optional[str] = None):
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000.0, 2)
        if error:
            self.attributes["error"] = error
            self.attributes["status"] = "ERROR"
        else:
            self.attributes["status"] = status

        if self.otel_span:
            try:
                for k, v in self.attributes.items():
                    self.otel_span.set_attribute(k, str(v))
                self.otel_span.end()
            except Exception:
                pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes
        }

@contextmanager
def trace_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    span = GatewayTraceSpan(name, attributes)
    span.start()
    try:
        yield span
        span.end(status="OK")
    except Exception as e:
        span.end(status="ERROR", error=str(e))
        raise
