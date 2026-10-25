import logging
import sys
import typing as t

from loguru import logger
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.trace import (
    INVALID_SPAN,
    INVALID_SPAN_CONTEXT,
    get_current_span,
    get_tracer_provider,
)


class _LoguruOpenTelemetryHandler(LoggingHandler):
    """Export Loguru records through the configured OTel logger provider.
    Before emitting, records the extra metadata as top-level attributes on the log record."""

    def __init__(self) -> None:
        super().__init__(level=logging.NOTSET, log_code_attributes=True)

    def emit(self, record: logging.LogRecord) -> None:
        extra = record.__dict__.pop("extra", {})
        for key, value in extra.items():
            if key not in record.__dict__:
                setattr(record, key, value)

        super().emit(record)


def instrument_loguru() -> None:
    """Add OpenTelemetry trace context to every Loguru record. Implementation referenced from:
    https://loguru.readthedocs.io/en/latest/resources/recipes html#add-opentelemetry-trace-id-and-span-id-to-logs"""

    provider = get_tracer_provider()
    service_name = None

    def add_trace_context(record):
        record["extra"]["otelSpanID"] = "0"
        record["extra"]["otelTraceID"] = "0"
        record["extra"]["otelTraceSampled"] = False

        nonlocal service_name
        if service_name is None:
            resource = getattr(provider, "resource", None)
            if resource:
                service_name = resource.attributes.get("service.name") or ""
            else:
                service_name = ""

        record["extra"]["otelServiceName"] = service_name

        span = get_current_span()
        if span != INVALID_SPAN:
            context = span.get_span_context()
            if context != INVALID_SPAN_CONTEXT:
                record["extra"]["otelSpanID"] = format(context.span_id, "016x")
                record["extra"]["otelTraceID"] = format(context.trace_id, "032x")
                record["extra"]["otelTraceSampled"] = context.trace_flags.sampled

    logger.configure(patcher=add_trace_context)

    logger.remove()
    format_ = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} {level} [{name}] [{file}:{line}] "
        "[trace_id={extra[otelTraceID]} span_id={extra[otelSpanID]} "
        "resource.service.name={extra[otelServiceName]} trace_sampled={extra[otelTraceSampled]}] - {message}"
    )
    logger.add(sys.stderr, format=format_)
    logger.add(
        _LoguruOpenTelemetryHandler(),
        format=lambda _: "{message}",
        enqueue=False,
        diagnose=False,
        backtrace=False,
    )
