"""
The connector for *this application* — our own fhir-server.

Low-level async HTTP client implementing app.connectors.base.Connector
against fhir-server's own REST conventions (base path /api/fhir/v1,
plain-JSON `created_by`/`updated_by` audit injection on write, FHIR
`OperationOutcome` error bodies). This is the one point of contact between
this gateway and fhir-server — it wraps httpx.AsyncClient to:
  - Set a shared base URL and Content-Type header on every request.
  - Automatically inject audit fields (created_by / updated_by) into write request
    bodies from the caller's JWT subject so fhir-server can record audit trails
    without callers needing to remember to include those fields.
  - Normalise HTTP error responses into FastAPI HTTPExceptions with the status code
    and detail message forwarded from fhir-server's own error body.

Every resource client (app/fhir_client/organization.py, etc.) is written
against the Connector Protocol, not against this class directly — this is
just today's only implementation of it. Selected via configs/config.yaml's
`connectors.active` (see app.connectors.registry) and constructed once as a
Singleton by app.di.core.CoreContainer, so the underlying httpx connection
pool is shared and reused across all requests. `aclose()` must be called
during application shutdown to drain the pool cleanly.
"""

from enum import Enum

import httpx
from fastapi import HTTPException

from app.auth.models import AuthUser
from app.core.logging import trace_methods


@trace_methods
class FhirServerConnector:
    """
    Async HTTP wrapper around fhir-server's REST API — the connector for
    *this application*. See module docstring.

    All domain-specific clients (e.g. OrganizationClient) depend on the
    Connector Protocol this class satisfies to perform the actual HTTP
    calls. This separation keeps FHIR-path knowledge in the domain clients
    while error handling and actor injection live here once.
    """

    def __init__(self, base_url: str):
        """
        Initialise the HTTP client with fhir-server's base URL.

        Args:
            base_url: Root URL of fhir-server (e.g. http://localhost:8001/api/fhir/v1).
                      All path arguments passed to post/get/patch/delete are appended
                      to this base URL by httpx automatically.
        """
        # timeout=10.0 seconds balances user-facing latency with avoiding indefinite
        # hangs if fhir-server is slow or unreachable. Adjust if bulk operations
        # are introduced that legitimately take longer.
        # follow_redirects=True: FastAPI routers emit 307 Temporary Redirect when a
        # trailing-slash variant of a URL is requested (e.g. /organizations →
        # /organizations/). Without this flag httpx returns the 307 as-is and the
        # middleware propagates it to the caller instead of following through.
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={"Content-Type": "application/json"},
            timeout=10.0,
            follow_redirects=True,
        )

    async def _handle(self, r: httpx.Response) -> dict | None:
        """
        Normalise an httpx response into a Python dict or raise HTTPException.

        Handles three cases:
          1. 204 No Content — successful operation with no body (e.g. DELETE). Returns None.
          2. 4xx/5xx — raises HTTPException with fhir-server's status code and
             a detail message extracted from its FHIR `OperationOutcome` error body
             (falls back to raw text if the body isn't JSON or isn't an OperationOutcome).
          3. 2xx with body — parses and returns the JSON dict.

        Args:
            r: The raw httpx.Response from fhir-server.

        Returns:
            Parsed JSON dict for successful responses with a body, or None for 204.

        Raises:
            HTTPException: Forwarding fhir-server's status code and error detail
                to the API consumer. This preserves semantic errors (e.g. 404 Not Found,
                409 Conflict) without re-mapping them at this layer.
        """
        # 204 means success but no body — return None so callers don't try to parse.
        if r.status_code == 204:
            return None
        try:
            # raise_for_status() raises httpx.HTTPStatusError on 4xx/5xx.
            r.raise_for_status()
        except httpx.HTTPStatusError:
            raise HTTPException(
                status_code=r.status_code, detail=self._extract_detail(r)
            )
        return r.json()

    @staticmethod
    def _extract_detail(r: httpx.Response) -> str | list[dict]:
        """
        Extract a client-facing error message from fhir-server's response body.

        fhir-server does not use a flat `{"detail": ...}` shape — every error
        (validation, not-found, conflict, unhandled) is normalised by its own global
        handlers into a FHIR `OperationOutcome` resource, e.g.:
            {"resourceType": "OperationOutcome", "issue": [
                {"severity": "error", "code": "invalid",
                 "diagnostics": "Schedule 'Schedule/9' not found.",
                 "expression": ["schedule"]}
            ]}
        `expression` (a field path) is only present for field-level validation errors.

        A single issue with no `expression` collapses to a plain string so the common
        case (a single 404/409/422 message) stays a simple string, matching what most
        API consumers already expect. Multiple issues, or any issue carrying an
        `expression`, produce a `list[dict]` of `{"field": ..., "message": ...}`
        entries — deliberately the same shape FastAPI's own `RequestValidationError`
        produces (see `validation_exception_handler` in app/main.py), so REST/GraphQL
        consumers don't need a second branch for fhir-server-sourced 422s.
        """
        try:
            body = r.json()
        except Exception:
            return r.text

        if not isinstance(body, dict) or body.get("resourceType") != "OperationOutcome":
            return r.text

        issues = body.get("issue") or []
        if not issues:
            return r.text

        if len(issues) == 1 and not issues[0].get("expression"):
            return issues[0].get("diagnostics", r.text)

        return [
            {
                "field": (issue.get("expression") or [None])[0],
                "message": issue.get("diagnostics"),
            }
            for issue in issues
        ]

    async def post(
        self,
        path: str,
        data: dict,
        actor: AuthUser,
        accept: str | None = None,
        inject_audit: bool = True,
    ) -> dict:
        """
        Send a POST (create) request to fhir-server.

        Injects actor identity fields into the request body so fhir-server
        can record who created the resource without requiring callers to include
        those fields manually in every service call.

        Args:
            path:         fhir-server endpoint path relative to base_url (e.g. "/organizations").
            data:         Resource payload from the schema's model_dump().
            actor:        Authenticated user performing the operation — `sub` stamps
                          `created_by` (unless inject_audit=False); `token` is forwarded
                          as the Authorization header for resources (e.g. Patient) that
                          validate the caller's JWT themselves rather than trusting the
                          gateway unconditionally.
            accept:       Optional Accept header value forwarded from the client request.
                          When set to "application/fhir+json", fhir-server returns the
                          resource in FHIR R4 format instead of plain JSON.
            inject_audit: When True (default), injects `created_by` from actor.sub.
                          Pass False for sub-resource endpoints whose input schemas use
                          extra="forbid" and do not declare a created_by field.

        Returns:
            The newly created resource dict — in FHIR R4 or plain JSON format
            depending on the `accept` value.
        """
        # Inject the audit field unless the caller opts out (e.g. sub-resource schemas
        # that use extra="forbid" and have no created_by field).
        body = {**data, "created_by": actor.sub} if inject_audit else data
        # Forward the Accept header per-request so fhir-server applies content
        # negotiation. httpx merges per-request headers with client-level headers.
        extra_headers = {"Accept": accept} if accept else {}
        extra_headers["Authorization"] = f"Bearer {actor.token}"
        r = await self._http.post(path, json=body, headers=extra_headers)
        return await self._handle(r)

    async def patch(
        self,
        path: str,
        data: dict,
        actor: AuthUser,
        accept: str | None = None,
        inject_audit: bool = True,
    ) -> dict:
        """
        Send a PATCH (partial update) request to fhir-server.

        Injects `updated_by` so fhir-server can record who last modified the
        resource without callers needing to supply it.

        Args:
            path:         fhir-server endpoint path including the resource ID.
            data:         Partial payload from the schema's model_dump(exclude_none=True, mode="json").
            actor:        Authenticated user performing the operation — `token` is forwarded
                          as the Authorization header (see post()'s docstring for why).
            accept:       Optional Accept header forwarded from the client request for
                          content negotiation — same semantics as in post().
            inject_audit: When True (default), injects `updated_by` from actor.sub.
                          Pass False for sub-resource endpoints whose input schemas use
                          extra="forbid" and do not declare an updated_by field.

        Returns:
            The updated resource dict in FHIR R4 or plain JSON format.
        """
        body = {**data, "updated_by": actor.sub} if inject_audit else data
        extra_headers = {"Accept": accept} if accept else {}
        extra_headers["Authorization"] = f"Bearer {actor.token}"
        r = await self._http.patch(path, json=body, headers=extra_headers)
        return await self._handle(r)

    async def get(
        self,
        path: str,
        params: dict | None = None,
        accept: str | None = None,
        actor: AuthUser | None = None,
    ) -> dict:
        """
        Send a GET request to fhir-server.

        No audit-field injection is needed for reads. `actor` is optional here
        (unlike post()/patch()) because most resources still don't validate a
        JWT on fhir-server — pass it for resources (e.g. Patient) that do,
        so the Authorization header is forwarded.

        Args:
            path:   fhir-server endpoint path (resource collection or specific resource).
            params: Optional query parameters dict (e.g. {"name": "Acme", "limit": 10}).
            accept: Optional Accept header forwarded from the client request.
                    When "application/fhir+json", fhir-server returns FHIR R4 format.
                    Omit (or pass None) for internal calls that always need plain JSON
                    (e.g. duplicate-detection pre-checks in the service layer).
            actor:  Authenticated caller — when provided, forwards `token` as the
                    Authorization header. Optional; omit for resources fhir-server
                    doesn't yet authenticate directly.

        Returns:
            The resource or paginated collection dict from fhir-server, in the
            format determined by the `accept` value.
        """
        extra_headers = {"Accept": accept} if accept else {}
        if actor is not None:
            extra_headers["Authorization"] = f"Bearer {actor.token}"
        # httpx stringifies query param values with str(), and a plain `str, Enum`
        # member's __str__ returns "ClassName.member_name" (not its actual value)
        # on Python < 3.11 — unwrap any Enum filter value (e.g. gender=AdministrativeGender.male)
        # to its raw .value so fhir-server always receives "male", not "AdministrativeGender.male".
        if params is not None:
            params = {
                k: (v.value if isinstance(v, Enum) else v) for k, v in params.items()
            }
        r = await self._http.get(path, params=params, headers=extra_headers)
        return await self._handle(r)

    async def delete(self, path: str, actor: AuthUser | None = None) -> None:
        """
        Send a DELETE request to fhir-server.

        fhir-server returns 204 on success; _handle() converts that to None
        which this method discards, so callers simply await without checking a return.

        Args:
            path:  fhir-server endpoint path including the resource ID to delete.
            actor: Authenticated caller — when provided, forwards `token` as the
                   Authorization header (see get()'s docstring for why this is optional).
        """
        extra_headers = (
            {"Authorization": f"Bearer {actor.token}"} if actor is not None else {}
        )
        r = await self._http.delete(path, headers=extra_headers)
        await self._handle(r)

    async def aclose(self) -> None:
        """
        Close the underlying httpx connection pool gracefully.

        Must be called during application shutdown (app.main lifespan teardown)
        to allow in-flight requests to complete and release socket resources.
        Failing to call this leaks file descriptors and may cause ResourceWarning
        in test environments.
        """
        await self._http.aclose()
