"""
The one token manager every external connector uses.

A connector's config (`connectors.<name>.auth_method`) picks how this gateway
logs in to that backend's token endpoint; `build_token_manager()` returns the
matching manager. All of them do the OAuth2 ``client_credentials`` grant, cache
the access token until shortly before it expires, refetch behind an
asyncio.Lock (so concurrent requests don't each hit the token endpoint), and
support ``invalidate()`` after a 401.

auth_method values
------------------
* ``client_secret``   - client id + secret. Sent as HTTP Basic by default
  (``send_secret_as="basic"``, the OAuth2 standard / Oracle Health) or in the
  form body (``"body"``, Medplum). Needs CLIENT_ID and CLIENT_SECRET.
* ``private_key_jwt`` - SMART Backend Services / RFC 7523. A short
  RS384-signed JWT (the "client assertion") proves who we are: we sign with our
  PRIVATE key and the backend checks it against the PUBLIC key (JWKS) registered
  for the client. Needs CLIENT_ID and PRIVATE_KEY_PATH. Used by OpenEMR, Epic,
  and optionally Oracle Health.
* ``token_passthrough`` is NOT handled here: the internal connector forwards the
  caller's own bearer JWT and never acquires a token (no manager at all).

The signed assertion (private_key_jwt):

    header : {"alg": "RS384", "kid": <key id>, "typ": "JWT"}
    payload: {"iss": client_id, "sub": client_id, "aud": token_url,
              "jti": <fresh random id>, "iat": now, "exp": now + 4 min}

A new assertion (new `jti`) is built per token request - backends reject a
`jti` they've seen. `aud` must equal the token endpoint exactly. `kid` is the
RFC 7638 thumbprint of the key's public half, so it matches the JWKS generated
from the same key (derived, never configured).

The access token is returned as ``expires_in`` seconds (OpenEMR/Epic/Oracle
roughly 300-570, Medplum 3600); `scope` is sent only when set.
"""

import asyncio
import base64
import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Literal

import httpx
import jwt
from cryptography.hazmat.primitives.serialization import load_pem_private_key

_EXPIRY_SAFETY_MARGIN_SECONDS = 30
_ASSERTION_LIFETIME_SECONDS = 240
_CLIENT_ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"


class _CachedTokenManager:
    """Token cache + lock + refresh. Subclasses implement `_request_form()`:
    the (data, auth) for the token POST."""

    def __init__(self, token_url: str) -> None:
        self._token_url = token_url
        self._http = httpx.AsyncClient(timeout=10.0)
        self._access_token: str | None = None
        self._expires_at: float | None = None
        self._lock = asyncio.Lock()

    def _request_form(self) -> tuple[dict, tuple[str, str] | None]:
        raise NotImplementedError

    async def get_token(self) -> str:
        """A valid access token, fetched first if missing or about to expire."""
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
        """Drop the cached token (after a 401) so the next get_token() refetches."""
        async with self._lock:
            self._access_token = None
            self._expires_at = None

    async def _fetch_token(self) -> None:
        data, auth = self._request_form()
        r = await self._http.post(
            self._token_url,
            data=data,
            auth=auth,
            headers={"Accept": "application/json"},
        )
        r.raise_for_status()
        body = r.json()
        self._access_token = body["access_token"]
        expires_in = body.get("expires_in", 300)
        self._expires_at = time.monotonic() + expires_in - _EXPIRY_SAFETY_MARGIN_SECONDS

    async def aclose(self) -> None:
        await self._http.aclose()


class ClientSecretTokenManager(_CachedTokenManager):
    """client_credentials with a client id + secret."""

    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        scope: str | None = None,
        send_secret_as: Literal["basic", "body"] = "basic",
    ) -> None:
        if not client_id or not client_secret:
            raise ValueError(
                "auth_method=client_secret needs both client_id and client_secret - set "
                "CONNECTORS__<NAME>__CLIENT_ID and CONNECTORS__<NAME>__CLIENT_SECRET "
                "(env vars, never the YAML)."
            )
        super().__init__(token_url)
        self._client_id = client_id
        self._client_secret = client_secret
        self._scope = scope
        self._send_secret_as = send_secret_as

    def _request_form(self) -> tuple[dict, tuple[str, str] | None]:
        data: dict = {"grant_type": "client_credentials"}
        if self._scope:
            data["scope"] = self._scope
        if self._send_secret_as == "basic":
            return data, (self._client_id, self._client_secret)
        data["client_id"] = self._client_id
        data["client_secret"] = self._client_secret
        return data, None


def _b64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _rfc7638_thumbprint(public_numbers) -> str:
    """RFC 7638 JWK thumbprint of an RSA public key - the `kid` convention."""
    canonical = json.dumps(
        {
            "e": _b64url_uint(public_numbers.e),
            "kty": "RSA",
            "n": _b64url_uint(public_numbers.n),
        },
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


class SignedJwtTokenManager(_CachedTokenManager):
    """client_credentials with a signed JWT client assertion (private_key_jwt)."""

    def __init__(
        self,
        token_url: str,
        client_id: str,
        private_key_path: str,
        scope: str | None = None,
    ) -> None:
        if not client_id or not private_key_path:
            raise ValueError(
                "auth_method=private_key_jwt needs client_id and private_key_path - set "
                "CONNECTORS__<NAME>__CLIENT_ID and CONNECTORS__<NAME>__PRIVATE_KEY_PATH "
                "(env vars, never the YAML)."
            )
        path = Path(private_key_path)
        if not path.is_file():
            raise ValueError(f"Private key not found: {private_key_path}")
        super().__init__(token_url)
        self._private_key_pem = path.read_bytes()
        key = load_pem_private_key(self._private_key_pem, password=None)
        self._kid = _rfc7638_thumbprint(key.public_key().public_numbers())
        self._client_id = client_id
        self._scope = scope

    def _build_assertion(self) -> str:
        now = int(time.time())
        return jwt.encode(
            {
                "iss": self._client_id,
                "sub": self._client_id,
                "aud": self._token_url,
                "jti": uuid.uuid4().hex,
                "iat": now,
                "exp": now + _ASSERTION_LIFETIME_SECONDS,
            },
            self._private_key_pem,
            algorithm="RS384",
            headers={"kid": self._kid, "typ": "JWT"},
        )

    def _request_form(self) -> tuple[dict, tuple[str, str] | None]:
        data = {
            "grant_type": "client_credentials",
            "client_assertion_type": _CLIENT_ASSERTION_TYPE,
            "client_assertion": self._build_assertion(),
        }
        if self._scope:  # OpenEMR/Oracle need it; Epic takes scopes from the app registration
            data["scope"] = self._scope
        return data, None


def build_token_manager(
    auth_method: str,
    *,
    token_url: str,
    client_id: str,
    client_secret: str = "",
    private_key_path: str = "",
    scope: str | None = None,
    send_secret_as: Literal["basic", "body"] = "basic",
):
    """The token manager for a connector's configured `auth_method`."""
    if auth_method == "client_secret":
        return ClientSecretTokenManager(
            token_url, client_id, client_secret, scope or None, send_secret_as
        )
    if auth_method == "private_key_jwt":
        return SignedJwtTokenManager(token_url, client_id, private_key_path, scope or None)
    raise ValueError(
        f"auth_method {auth_method!r} has no token manager "
        "(token_passthrough connectors never acquire a token)."
    )
