"""Optional OpenTelemetry instrumentation for the IAM backend.

Disabled by default.  Set ``OTEL_ENABLED=true`` and configure the OTLP exporter
via environment variables (``OTEL_EXPORTER_OTLP_ENDPOINT``, etc.) to activate.
"""

import logging

from django.conf import settings

logger = logging.getLogger("iam.core.otel")


def setup_otel() -> bool:
    """Initialise OpenTelemetry SDK and instrument Django.

    Returns ``True`` if instrumentation was applied, ``False`` if skipped.
    """
    enabled = getattr(settings, "OTEL_ENABLED", False)
    if not enabled:
        logger.info("OpenTelemetry disabled (OTEL_ENABLED is falsy)")
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.django import DjangoInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": "iam-backend", "service.version": "3.0.0"})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter()
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        DjangoInstrumentor().instrument()

        logger.info("OpenTelemetry initialised — exporting to %s", getattr(settings, "OTEL_EXPORTER_OTLP_ENDPOINT", "default"))
        return True

    except Exception as e:
        logger.warning("Failed to initialise OpenTelemetry: %s", e)
        return False
