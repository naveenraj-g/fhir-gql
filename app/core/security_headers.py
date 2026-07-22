"""
Starlette middleware that adds standard security-hardening response headers.

These headers cost nothing to set and close off several classes of browser-side
attacks (clickjacking, MIME-sniffing, protocol downgrade) that a pure JSON API
is otherwise silently exposed to. None of them affect non-browser clients
(curl, httpx, mobile apps) — they are purely instructions to the browser.

Content-Security-Policy is scoped to exclude the interactive documentation
routes (Swagger UI at /docs, GraphiQL at /graphql) because both load their own
JS/CSS assets that a strict `default-src 'none'` policy would block. Every
other route returns plain JSON with no scripts/styles to allow, so the
strictest possible policy is safe there.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Routes that render an interactive HTML UI with their own script/style assets.
# CSP is skipped for these so Swagger UI / GraphiQL keep working; every other
# route is a plain JSON response with nothing for a CSP to legitimately allow.
_CSP_EXEMPT_PREFIXES = ("/docs", "/redoc", "/graphql")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds Content-Security-Policy, Strict-Transport-Security, X-Content-Type-Options,
    and X-Frame-Options to every response.

    Execution order note: registered in app.main alongside RequestIdMiddleware and
    RateLimitMiddleware — see that module's middleware-ordering comment. Headers are
    set on the way out (after call_next), so they're applied regardless of which
    route or exception handler produced the response.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Prevents browsers from guessing ("sniffing") a response's content type
        # away from the declared Content-Type header — blocks a class of attacks
        # where a malicious file is served as JSON but executed as HTML/JS.
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Refuses to let any page embed this API's responses in an <iframe>,
        # closing off clickjacking-style attacks. "DENY" rather than
        # "SAMEORIGIN" since this service has no legitimate reason to be framed.
        response.headers["X-Frame-Options"] = "DENY"

        # Tells browsers to only ever contact this host over HTTPS for the next
        # two years, including subdomains — mitigates protocol-downgrade and
        # cookie-stripping attacks on first-visit HTTP requests. Harmless to set
        # even when served over plain HTTP in local dev (browsers ignore HSTS
        # headers received over an insecure connection).
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

        # Skip CSP on the interactive doc UIs — see _CSP_EXEMPT_PREFIXES docstring.
        if not request.url.path.startswith(_CSP_EXEMPT_PREFIXES):
            # This is a JSON API: no route ever needs to load a script, style,
            # font, or frame, so the strictest possible policy is safe everywhere
            # else and requires no per-route tuning as new resources are added.
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

        return response
