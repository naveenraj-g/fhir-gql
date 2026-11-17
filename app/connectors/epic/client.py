"""
The connector for Epic on FHIR (R4) - read-only.

Authenticates as *itself* with SMART Backend Services (OAuth2
client_credentials + RS384-signed JWT client assertion), via the shared
app.connectors.token_manager. Epic gets our public
key from the JWK Set URL registered on the app (fhir.epic.com -> My Apps)
and decides what the app may call from the APIs ticked at registration, so
no `scope` is sent.

Read-only by design: the registered APIs are Organization/Location read
(Organizational Directory), and Epic does not offer those as writable APIs.
post/patch/delete therefore fail locally with 405 instead of making a call
Epic would reject.

`accept` and `inject_audit` are accepted but ignored (Protocol conformance).
"""

from enum import Enum

import httpx
from fastapi import HTTPException

from app.auth.models import AuthUser
from app.connectors.token_manager import build_token_manager
from app.core.logging import trace_methods

_READ_ONLY = "The Epic connector is read-only (Organization/Location read APIs only)."


@trace_methods
class EpicConnector:
    """Async HTTP wrapper around Epic's FHIR R4 API. See module docstring."""

    def __init__(
        self,
        base_url: str,
        token_url: str,
        auth_method: str,
        client_id: str,
        client_secret: str,
        private_key_path: str,
        scope: str,
    ) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={"Accept": "application/fhir+json"},
            timeout=20.0,
            follow_redirects=True,
        )
        self._token_manager = build_token_manager(
            auth_method,
            token_url=token_url,
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
        raise HTTPException(status_code=405, detail=_READ_ONLY)

    async def patch(
        self,
        path: str,
        data: dict | list[dict],
        actor: AuthUser,
        accept: str | None = None,
        inject_audit: bool = True,
    ) -> dict:
        raise HTTPException(status_code=405, detail=_READ_ONLY)

    async def delete(self, path: str, actor: AuthUser | None = None) -> None:
        raise HTTPException(status_code=405, detail=_READ_ONLY)

    async def aclose(self) -> None:
        await self._http.aclose()
        await self._token_manager.aclose()
