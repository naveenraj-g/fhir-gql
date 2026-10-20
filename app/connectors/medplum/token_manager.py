"""
OAuth2 client_credentials token acquisition/caching for the Medplum
connector.

Unlike the internal connector's token_passthrough mode (which just forwards
the caller's own inbound JWT because fhir-server trusts the same IAM this
gateway does), Medplum has never heard of our IAM — it has its own OAuth2
authorization server (confirmed via its own
http://localhost:8103/.well-known/openid-configuration). This connector
authenticates as *itself* — this gateway's own client_id/client_secret,
registered as a Medplum ClientApplication (Project Admin -> Clients in the
Medplum app) — never as whichever end-user happens to be calling. See
dev-docs/17-static-architecture-and-generic-fhir-payloads.md and the
client-credentials discussion in this project's chat history for the full
reasoning.

The acquired access_token is reusable for its lifetime (Medplum's
client_credentials grant returns `expires_in: 3600`, i.e. one hour) —
fetching a fresh one on every request would be wasteful and risks being
rate-limited, so it's cached here and only re-fetched when missing,
about to expire, or explicitly invalidated (MedplumConnector calls
invalidate() after a 401, before retrying once with a fresh token).

An asyncio.Lock prevents concurrent requests from each independently
fetching a new token the moment the cached one expires — only the first
caller to notice does the fetch; the rest wait on the lock and reuse
whatever it got, instead of all hammering the token endpoint at once.
"""

import asyncio
import time

import httpx

# Refetch this many seconds before the token's actual expiry, so a request
# already in flight doesn't race a token that expires mid-call.
_EXPIRY_SAFETY_MARGIN_SECONDS = 30


class MedplumTokenManager:
    """Acquires, caches, and rotates an OAuth2 client_credentials access
    token for one Medplum connector instance. See module docstring."""

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        """
        Args:
            token_url: Medplum's OAuth2 token endpoint
                       (e.g. http://localhost:8103/oauth2/token).
            client_id: This connector's own Medplum ClientApplication ID.
            client_secret: That ClientApplication's secret.

        Raises:
            ValueError: If client_id or client_secret is empty — fails at
                construction time (app/connector startup) rather than at
                the first request, since an empty credential can only mean
                CONNECTORS__MEDPLUM__CLIENT_ID/_SECRET were never set.
        """
        if not client_id or not client_secret:
            raise ValueError(
                "MedplumTokenManager requires both client_id and client_secret — "
                "set them via the CONNECTORS__MEDPLUM__CLIENT_ID and "
                "CONNECTORS__MEDPLUM__CLIENT_SECRET environment variables "
                "(never configs/connectors/medplum.yaml)."
            )
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        # Separate client from MedplumConnector's own: the token endpoint
        # (/oauth2/token) lives outside the FHIR base_url (/fhir/R4), so it
        # isn't reachable through that client's base_url-relative requests.
        self._http = httpx.AsyncClient(timeout=10.0)
        self._access_token: str | None = None
        self._expires_at: float | None = None
        self._lock = asyncio.Lock()

    async def get_token(self) -> str:
        """Return a valid access token, fetching a fresh one first if the
        cached one is missing or about to expire."""
        async with self._lock:
            if (
                self._access_token is not None
                and self._expires_at is not None
                and time.monotonic() < self._expires_at
            ):
                return self._access_token
            await self._fetch_token()
            assert self._access_token is not None
            return self._access_token

    async def invalidate(self) -> None:
        """Discard the cached token — called after a 401 from Medplum, so
        the next get_token() fetches a fresh one instead of reusing a
        token Medplum has already rejected (revoked early, clock skew,
        etc.) rather than looping on the same bad token."""
        async with self._lock:
            self._access_token = None
            self._expires_at = None

    async def _fetch_token(self) -> None:
        """POST the client_credentials grant to Medplum's token endpoint
        and cache the result.

        Raises:
            httpx.HTTPStatusError: If the grant is rejected (bad
                client_id/secret) — left to propagate as a 5xx by
                MedplumConnector, since it means this connector itself is
                misconfigured, not that the caller's request was bad.
        """
        r = await self._http.post(
            self._token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
        )
        r.raise_for_status()
        body = r.json()
        self._access_token = body["access_token"]
        expires_in = body.get("expires_in", 3600)
        self._expires_at = time.monotonic() + expires_in - _EXPIRY_SAFETY_MARGIN_SECONDS

    async def aclose(self) -> None:
        """Close the token endpoint's own httpx connection pool. Called by
        MedplumConnector.aclose() during application shutdown."""
        await self._http.aclose()
