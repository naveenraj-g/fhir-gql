"""
The connector for Medplum — a standards-compliant external FHIR R4 EHR,
used here as this project's reference "any genuinely FHIR-compliant
backend" connector (see
dev-docs/17-static-architecture-and-generic-fhir-payloads.md).

Unlike InternalConnector (our own fhir-server, token_passthrough auth — see
app.connectors.internal.client), this connector authenticates as *itself*
via OAuth2 client_credentials
(app.connectors.medplum.token_manager.MedplumTokenManager) — Medplum has
its own authorization server and has never heard of our IAM, so the
caller's inbound JWT (actor.token) is never forwarded here. `actor` is
still accepted on every method, for Connector Protocol conformance and
for whatever future audit use, but only `actor.sub` would ever be read —
`actor.token` is ignored entirely.

`accept` and `inject_audit` are likewise accepted-but-ignored on every
method, for the same Protocol-conformance reason: Medplum has no "plain
JSON" alternate shape to negotiate (it only ever speaks real FHIR R4 JSON,
set as this client's fixed Content-Type below) and no fhir-server-style
created_by/updated_by convention to stamp into the body.

Medplum follows the canonical FHIR REST convention (`/{ResourceType}/{id}`),
unlike fhir-server's own `/organizations`-style routes — so, unlike
FhirServerConnector/InternalConnector, this class sends/receives whatever
path and body a resource client passes in completely unmodified; there is
no plain<->FHIR translation on either side here.
"""

from enum import Enum

import httpx
from fastapi import HTTPException

from app.auth.models import AuthUser
from app.connectors.medplum.token_manager import MedplumTokenManager
from app.core.logging import trace_methods


@trace_methods
class MedplumConnector:
    """
    Async HTTP wrapper around Medplum's FHIR R4 API, authenticating via
    OAuth2 client_credentials. See module docstring.
    """

    def __init__(
        self, base_url: str, token_url: str, client_id: str, client_secret: str
    ) -> None:
        """
        Args:
            base_url: Medplum's FHIR R4 base (e.g. http://localhost:8103/fhir/R4).
            token_url: Medplum's OAuth2 token endpoint
                       (e.g. http://localhost:8103/oauth2/token).
            client_id: This connector's own Medplum ClientApplication ID —
                       see Project Admin -> Clients in the Medplum app. A
                       real env var (CONNECTORS__MEDPLUM__CLIENT_ID), never
                       committed to configs/connectors/medplum.yaml.
            client_secret: That ClientApplication's secret — same rule
                           (CONNECTORS__MEDPLUM__CLIENT_SECRET, env var only).
        """
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={"Content-Type": "application/fhir+json"},
            timeout=10.0,
            follow_redirects=True,
        )
        self._token_manager = MedplumTokenManager(
            token_url=token_url, client_id=client_id, client_secret=client_secret
        )

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """
        Attach a valid bearer token and send the request, retrying exactly
        once with a freshly-fetched token if Medplum responds 401 — covers
        the token expiring or being revoked between get_token() returning
        it and the request actually reaching Medplum.
        """
        token = await self._token_manager.get_token()
        headers = {**kwargs.pop("headers", {}), "Authorization": f"Bearer {token}"}
        r = await self._http.request(method, path, headers=headers, **kwargs)
        if r.status_code == 401:
            await self._token_manager.invalidate()
            token = await self._token_manager.get_token()
            headers["Authorization"] = f"Bearer {token}"
            r = await self._http.request(method, path, headers=headers, **kwargs)
        return r

    async def _handle(self, r: httpx.Response) -> dict | None:
        """Same shape as InternalConnector._handle — see its docstring."""
        if r.status_code == 204:
            return None
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError:
            raise HTTPException(status_code=r.status_code, detail=self._extract_detail(r))
        return r.json()

    @staticmethod
    def _extract_detail(r: httpx.Response) -> str | list[dict]:
        """Same FHIR OperationOutcome parsing as InternalConnector — this
        is the FHIR standard's own error shape, not fhir-server-specific,
        so Medplum's errors come back in exactly this format too."""
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
        """Send a POST (create) request to Medplum."""
        r = await self._request("POST", path, json=data)
        return await self._handle(r)

    async def patch(
        self,
        path: str,
        data: dict,
        actor: AuthUser,
        accept: str | None = None,
        inject_audit: bool = True,
    ) -> dict:
        """Send a PATCH (partial update) request to Medplum."""
        r = await self._request("PATCH", path, json=data)
        return await self._handle(r)

    async def get(
        self,
        path: str,
        params: dict | None = None,
        accept: str | None = None,
        actor: AuthUser | None = None,
    ) -> dict:
        """Send a GET request to Medplum."""
        if params is not None:
            params = {
                k: (v.value if isinstance(v, Enum) else v) for k, v in params.items()
            }
        r = await self._request("GET", path, params=params)
        return await self._handle(r)

    async def delete(self, path: str, actor: AuthUser | None = None) -> None:
        """Send a DELETE request to Medplum."""
        r = await self._request("DELETE", path)
        await self._handle(r)

    async def aclose(self) -> None:
        """Close both this client's and the token manager's httpx
        connection pools. Called during application shutdown."""
        await self._http.aclose()
        await self._token_manager.aclose()
