"""
Structured JSON logging setup for the application.

All log output is emitted as newline-delimited JSON so it can be ingested directly
by log aggregation systems (Datadog, Loki, CloudWatch Logs Insights, etc.) without
a parsing step. Each line contains at minimum: timestamp, level, logger name,
message, and any extra fields passed via the `extra={}` kwarg on logger calls.

Correlation fields (request_id / actor_user_id / actor_org_id) are injected
automatically from app.core.request_context's ContextVars, so no layer below
the GraphQL router has to accept or forward them — see that module's
docstring for why. The actor keys are prefixed `actor_` on purpose: FHIR
resources and request payloads carry their own user_id/org_id fields, so a
bare `user_id` in a log line would be ambiguous.

Usage:
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("Organisation created", extra={"org_id": 42})
"""

import functools
import inspect
import json
import logging
import re
import sys
import time
from typing import Any

from app.core.config import settings
from app.core.request_context import get_log_context

# Internal LogRecord attributes that carry no value in structured logs. Shared
# by both formatters below. Including them would double the size of every log
# line with fields like `pathname`, `threadName`, and `processName` that are
# noise in a container env.
_SKIP = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "taskName",
}

_REDACTED = "***REDACTED***"


class _JsonFormatter(logging.Formatter):
    """
    Custom logging.Formatter that serialises each LogRecord as a JSON object.

    Standard logging internals (pathname, thread, process, etc.) are excluded from
    the output to keep log lines compact. Any key in `extra={}` that is not in the
    skip list is promoted to a top-level JSON field, making structured querying easy.
    """

    _SKIP = _SKIP

    def format(self, record: logging.LogRecord) -> str:
        """
        Serialise a LogRecord into a JSON string.

        Builds a base dict with the four mandatory fields (timestamp, level, logger,
        message), merges in request_id/actor_user_id/actor_org_id (whichever are
        set — see app.core.request_context.get_log_context), then appends any
        extra fields the caller provided via `extra={}`. Exception tracebacks are
        included under the `traceback` key when present.

        Args:
            record: The LogRecord produced by a logger.info/error/... call.

        Returns:
            A single-line JSON string ready to be written to stdout.
        """
        # Mandatory fields present in every log line.
        out: dict = {
            "timestamp": self.formatTime(record),  # ISO-8601 formatted by default
            "level": record.levelname,              # DEBUG / INFO / WARNING / ERROR / CRITICAL
            "logger": record.name,                  # module path passed to get_logger()
            "message": record.getMessage(),         # formatted message string
        }

        # request_id / actor_user_id / actor_org_id, whichever are set.
        out.update(get_log_context())

        # Promote caller-supplied `extra={}` keys to top-level JSON fields.
        # Skip keys already in `out` to avoid overwriting the mandatory fields
        # (this is also what makes a stray extra={"actor_user_id": ...} a
        # silent no-op rather than a collision — the context above wins),
        # and skip internal LogRecord bookkeeping attributes from `_SKIP`.
        for k, v in record.__dict__.items():
            if k not in self._SKIP and k not in out:
                out[k] = v

        # Append the formatted traceback when the log call included exc_info=True
        # or was triggered by logger.exception(). Stored as a string under `traceback`
        # so it doesn't break JSON parsing of downstream consumers.
        if record.exc_info:
            out["traceback"] = self.formatException(record.exc_info)

        return json.dumps(out, default=str)


class _ConsoleFormatter(logging.Formatter):
    """Human-readable single line for local development — same data as
    _JsonFormatter, just laid out for eyes instead of for an indexer."""

    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)-8s %(name)s | %(message)s")

    # Set by logging.Formatter.format() itself (record.message = getMessage(),
    # record.asctime = formatTime()) as a side effect of the super().format()
    # call below — already rendered in `base`, so they must not be repeated
    # in the key=value suffix.
    _FORMATTER_SET = frozenset({"message", "asctime"})

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)

        ctx = get_log_context()
        request_id = ctx.get("request_id")
        prefix = f"[{request_id[:8]}] " if request_id else ""

        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k not in _SKIP and k not in self._FORMATTER_SET and k not in ctx
        }
        if record.exc_info:
            extras["traceback"] = self.formatException(record.exc_info)

        suffix = ""
        if extras:
            suffix = " " + " ".join(f"{k}={v!r}" for k, v in extras.items())

        return f"{prefix}{base}{suffix}"


def setup_logging() -> None:
    """
    Configure the root logger from configs/config.yaml's `logging` section
    (settings.logging — see app/core/config.py). Idempotent — replaces any
    previously installed handlers rather than stacking another one.

    Called once at application startup (app.main module level) before any other
    code runs so that even import-time log calls are captured.

    Implementation notes:
      - root.handlers.clear() removes any handlers added by third-party libraries
        (httpx, uvicorn, etc.) during their own imports, preventing duplicate log
        lines or conflicting plain-text output from mixing with JSON output.
      - All loggers in the process inherit the root logger's handler unless they
        define their own, so this single call covers the entire application.
    """
    log_settings = settings.logging

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        _ConsoleFormatter() if log_settings.format == "console" else _JsonFormatter()
    )

    root = logging.getLogger()
    root.setLevel(log_settings.level)

    # Clear existing handlers to avoid duplicate output when libraries (e.g. uvicorn)
    # have already attached their own StreamHandlers before setup_logging() is called.
    root.handlers.clear()
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """
    Retrieve a named logger for a module.

    Wraps logging.getLogger so all modules obtain loggers the same way without
    importing the stdlib logging module directly. Pass __name__ as the argument
    so log lines carry the full dotted module path (e.g. "app.services.organization_service").

    Args:
        name: Typically __name__ of the calling module.

    Returns:
        A standard logging.Logger instance that inherits the root JSON handler.
    """
    return logging.getLogger(name)


# ── Flow tracing ──────────────────────────────────────────────────────────────
#
# `logging.level: DEBUG` turns on an entry + exit line for EVERY public async
# method of every @trace_methods-decorated class, so a single GraphQL
# operation produces a complete top-to-bottom trace: resolver -> service
# method -> client method -> FhirClient. At INFO those lines disappear and
# only the per-operation line (app.gql.logging's GqlLoggingExtension) plus
# the access log (app.middleware.access_log) remain.
#
# Applied as a class decorator on service classes (app/services/*.py) and
# FHIR-client classes (app/fhir_client/*.py). It walks the full MRO, so a
# method inherited from a base class is covered too — a new subclass method
# needs no logging code of its own.
#
# Scope note: these classes are shared with the REST layer (app/routers/*.py
# calls the exact same OrganizationsService/OrganizationClient instances the
# GraphQL resolvers do), so a REST call incidentally gets traced too. That's
# fine — it's not REST-specific instrumentation (no per-REST-route logging
# was added), just visibility into code both layers already share.


def _redact(value: Any, redact_keys: set[str]) -> Any:
    """Recursively mask configured field names, matched case-insensitively at
    any nesting depth."""
    if isinstance(value, dict):
        return {
            k: (_REDACTED if str(k).lower() in redact_keys else _redact(v, redact_keys))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(v, redact_keys) for v in value]
    return value


def _snake(name: str) -> str:
    """OrganizationsService -> organizations.service; OrganizationClient -> organization.client"""
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
    return s.replace("_service", ".service").replace("_client", ".client")


def _describe(value: Any) -> Any:
    """Render one call argument for a log line. Pydantic models are dumped
    only when debug_payloads is on (they're request bodies — PHI); otherwise
    just the type name, so the flow is still traceable without the contents."""
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        if not settings.logging.debug_payloads:
            return f"<{type(value).__name__}>"
        return dump(mode="json", exclude_unset=True)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple, set)):
        return f"<{type(value).__name__}[{len(value)}]>"
    return f"<{type(value).__name__}>"


def _traced(fn, logger: logging.Logger, prefix: str, component: str):
    """Wrap one method so it announces itself.

    INFO  — a single line naming what is being called, e.g.
            "OrganizationsService.create". No arguments, no result, no
            timing. Reading the log top to bottom gives you the call chain:
            resolver -> service -> client -> FhirClient.
    DEBUG — the same entry line, now carrying call_args, plus a completion
            line with duration_ms and the result type (or the exception).
    """
    method = fn.__name__
    label = f"{component}.{method}"
    event = f"{prefix}.{method}"

    # Positional parameter names, read straight off the code object (`self`
    # dropped). Deliberately NOT inspect.signature(): under PEP 649 (Python
    # 3.14, this project's minimum) that forces evaluation of the function's
    # annotations, and a method whose own parameters are annotated with a
    # builtin shadowed by the method's own name (e.g. a method literally
    # named `list` with a `list[str]`-annotated parameter) raises
    # "TypeError: 'function' object is not subscriptable" — co_varnames needs
    # no annotations at all, and is far cheaper per call besides.
    _code = fn.__code__
    _pos_names = _code.co_varnames[1 : _code.co_argcount]

    @functools.wraps(fn)
    async def wrapper(self, *args, **kwargs):
        debug = logger.isEnabledFor(logging.DEBUG)

        extra = {"event": event, "component": component, "method": method}
        if debug:
            redact_keys = {k.lower() for k in settings.logging.redact}
            bound = dict(zip(_pos_names, args))
            bound.update(kwargs)
            # NB: key is "call_args", not "args" — LogRecord reserves "args"
            # and logging.makeRecord raises KeyError on a collision.
            extra["call_args"] = _redact(
                {k: _describe(v) for k, v in bound.items()}, redact_keys
            )

        logger.info(label, extra=extra)

        if not debug:
            return await fn(self, *args, **kwargs)

        started = time.perf_counter()
        try:
            result = await fn(self, *args, **kwargs)
        except Exception as exc:
            logger.debug(
                f"{label} raised {type(exc).__name__}",
                extra={
                    "event": f"{event}.error",
                    "component": component,
                    "method": method,
                    "error_type": type(exc).__name__,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            raise
        logger.debug(
            f"{label} ok",
            extra={
                "event": f"{event}.ok",
                "component": component,
                "method": method,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                "result": _describe(result),
            },
        )
        return result

    return wrapper


def trace_methods(cls):
    """Class decorator — makes every public async method announce itself.

    INFO gives one line per call (`OrganizationsService.create`), so the log
    reads as the call chain. DEBUG adds arguments, timing and results. See
    _traced().

    Walks the whole MRO so an inherited method is covered, and binds the
    wrapper onto `cls` itself. Underscore-prefixed methods are skipped
    deliberately — they're internal helpers that would bury the actual flow
    in noise.
    """
    prefix = _snake(cls.__name__)
    seen: set[str] = set()
    for klass in cls.__mro__:
        if klass is object:
            continue
        for name, attr in list(vars(klass).items()):
            if name in seen or name.startswith("_"):
                continue
            if not inspect.iscoroutinefunction(attr):
                continue
            seen.add(name)
            setattr(
                cls,
                name,
                _traced(attr, get_logger(klass.__module__), prefix, cls.__name__),
            )
    return cls
