"""
The connector for Oracle Health (Cerner Millennium) FHIR R4.

Authenticates as *itself* (never forwarding the caller's inbound JWT) with
OAuth2 client_credentials, using either a client secret (HTTP Basic) or a
signed JWT - chosen by `connectors.oracle_health.auth_method`, see
app.connectors.token_manager.

What Oracle allows (see README.md in this folder, from Oracle's endpoint list):

* Organization: read, search, create. No update, patch or delete.
* Location: read and search only.

So `post` is only allowed for Organization; every other write fails locally
with 405 rather than making a call Oracle would reject. Organization create
needs the `system/Organization.write` scope in `connectors.oracle_health.scope`.

`accept` and `inject_audit` are accepted but ignored (Protocol conformance).
"""

from enum import Enum

import httpx
from fastapi import HTTPException

from app.auth.models import AuthUser
from app.connectors.token_manager import build_token_manager
from app.core.logging import trace_methods

_NO_WRITE = "Oracle Health only supports create for Organization; update, patch and delete are not available."


@trace_methods
class OracleHealthConnector:
    """Async HTTP wrapper around Oracle Health's FHIR R4 API. See module docstring."""

    def __init__(
        self,
        base_url: str,
        token_url: str,
        tenant_id: str,
        auth_method: str,
        client_id: str,
        client_secret: str,
        private_key_path: str,
        scope: str,
    ) -> None:
        # The tenant id sits in both URLs as {tenant_id}.
        self._http = httpx.AsyncClient(
            base_url=base_url.format(tenant_id=tenant_id),
            headers={
                "Accept": "application/fhir+json",
                "Content-Type": "application/fhir+json",
            },
            timeout=20.0,
            follow_redirects=True,
        )
        self._token_manager = build_token_manager(
            auth_method,
            token_url=token_url.format(tenant_id=tenant_id),
            client_id=client_id,
            client_secret=client_secret,
            private_key_path=private_key_path,
            scope=scope,
        )

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Attach a bearer token; on 401 fetch a fresh one and retry once."""
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
        if r.status_code == 204:
            return None
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError:
            raise HTTPException(status_code=r.status_code, detail=self._extract_detail(r))
        return r.json()

    @staticmethod
    def _extract_detail(r: httpx.Response) -> str | list[dict]:
        """FHIR OperationOutcome -> readable detail; anything else -> raw text."""
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
            issue = issues[0]
            return issue.get("diagnostics") or (issue.get("details") or {}).get("text") or r.text
        return [
            {
                "field": (issue.get("expression") or [None])[0],
                "message": issue.get("diagnostics")
                or (issue.get("details") or {}).get("text"),
            }
            for issue in issues
        ]

    async def get(
        self,
        path: str,
        params: dict | None = None,
        accept: str | None = None,
        actor: AuthUser | None = None,
    ) -> dict:
        if params is not None:
            params = {
                k: (v.value if isinstance(v, Enum) else v) for k, v in params.items()
            }
        return await self._handle(await self._request("GET", path, params=params))

    async def post(
        self,
        path: str,
        data: dict,
        actor: AuthUser,
        accept: str | None = None,
        inject_audit: bool = True,
    ) -> dict:
        """Create - Organization only. Oracle answers 201 with the new id in
        the Location header and may return no body, so re-read the resource."""
        if path.rstrip("/") != "/Organization":
            raise HTTPException(status_code=405, detail=_NO_WRITE)
        r = await self._request("POST", path, json=data)
        if r.status_code == 201 and not r.content.strip():
            loc = r.headers.get("Location") or r.headers.get("Content-Location")
            if loc:
                parts = [p for p in loc.split("?")[0].split("/") if p]
                if "_history" in parts:
                    parts = parts[: parts.index("_history")]
                if parts:
                    return await self._handle(
                        await self._request("GET", f"{path}/{parts[-1]}")
                    )
        return await self._handle(r)

    async def patch(
        self,
        path: str,
        data: dict | list[dict],
        actor: AuthUser,
        accept: str | None = None,
        inject_audit: bool = True,
    ) -> dict:
        raise HTTPException(status_code=405, detail=_NO_WRITE)

    async def delete(self, path: str, actor: AuthUser | None = None) -> None:
        raise HTTPException(status_code=405, detail=_NO_WRITE)

    async def aclose(self) -> None:
        await self._http.aclose()
        await self._token_manager.aclose()
