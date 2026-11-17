"""
OAuth2 client_credentials token acquisition/caching for connectors that use
the SMART Backend Services login (RFC 7523 signed JWT) - shared by the
OpenEMR and Epic connectors.

For OpenEMR the *system* scopes (`system/Organization.read`, ...) do not accept a
client secret. Instead this gateway proves who it is by signing a short
JWT (the "client assertion") with its PRIVATE key; OpenEMR checks that
signature against the PUBLIC key (JWKS) registered for the client
(Administration -> System -> API Clients). The access token it returns
is then used as a normal Bearer token.

The assertion (RS384 = RSA PKCS#1 v1.5 with SHA-384):

    header : {"alg": "RS384", "kid": <key id>, "typ": "JWT"}
    payload: {"iss": client_id, "sub": client_id, "aud": token_url,
              "jti": <fresh random id>, "iat": now, "exp": now + 4 min}

A new assertion (new `jti`) is built for every token request - OpenEMR
rejects a `jti` it has already seen, so assertions are never reused.
`aud` must equal OpenEMR's token endpoint exactly, so `token_url` in the
config is both where we POST and the audience we sign for.

`kid` is the RFC 7638 thumbprint of the public half of the private key, so
it matches the `kid` in the JWKS registered with OpenEMR as long as that
JWKS was generated from this same key (it is derived, never configured).

OpenEMR access tokens live 300 s, so the cache refreshes shortly before
expiry. An asyncio.Lock stops concurrent callers from each fetching one.
"""

import asyncio
import base64
import hashlib
import json
import time
import uuid
from pathlib import Path

import httpx
import jwt
from cryptography.hazmat.primitives.serialization import load_pem_private_key

_EXPIRY_SAFETY_MARGIN_SECONDS = 30
# OpenEMR rejects assertions that expire more than 24 h out. A fresh one is
# made per token request, so a few minutes is plenty.
_ASSERTION_LIFETIME_SECONDS = 240
_CLIENT_ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"


def _b64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _rfc7638_thumbprint(public_numbers) -> str:
    """RFC 7638 JWK thumbprint of an RSA public key (members in
    lexicographic order, no whitespace) - the `kid` convention OpenEMR's
    client registration screen uses."""
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


class SmartBackendTokenManager:
    """Signs the client assertion, exchanges it for an access token, and
    caches that token. See module docstring."""

    def __init__(
        self,
        token_url: str,
        client_id: str,
        private_key_path: str,
        scope: str | None = None,
    ) -> None:
        """
        Raises:
            ValueError: client_id / private_key_path empty or the key file
                is missing - at construction (startup), not on first request.
        """
        if not client_id or not private_key_path:
            raise ValueError(
                "SmartBackendTokenManager requires client_id and private_key_path - set "
                "CONNECTORS__<NAME>__CLIENT_ID and CONNECTORS__<NAME>__PRIVATE_KEY_PATH "
                "(env vars, never the YAML)."
            )
        path = Path(private_key_path)
        if not path.is_file():
            raise ValueError(f"Private key not found: {private_key_path}")
        self._private_key_pem = path.read_bytes()
        key = load_pem_private_key(self._private_key_pem, password=None)
        self._kid = _rfc7638_thumbprint(key.public_key().public_numbers())

        self._token_url = token_url
        self._client_id = client_id
        self._scope = scope
        self._http = httpx.AsyncClient(timeout=10.0)
        self._access_token: str | None = None
        self._expires_at: float | None = None
        self._lock = asyncio.Lock()

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

    async def get_token(self) -> str:
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
        """Drop the cached token (called after a 401) so the next
        get_token() signs a fresh assertion and fetches a new one."""
        async with self._lock:
            self._access_token = None
            self._expires_at = None

    async def _fetch_token(self) -> None:
        form = {
            "grant_type": "client_credentials",
            "client_assertion_type": _CLIENT_ASSERTION_TYPE,
            "client_assertion": self._build_assertion(),
        }
        if self._scope:  # OpenEMR needs it; Epic takes its scopes from the app registration
            form["scope"] = self._scope
        r = await self._http.post(self._token_url, data=form)
        r.raise_for_status()
        body = r.json()
        self._access_token = body["access_token"]
        expires_in = body.get("expires_in", 300)  # OpenEMR 300 s, Epic ~300 s
        self._expires_at = time.monotonic() + expires_in - _EXPIRY_SAFETY_MARGIN_SECONDS

    async def aclose(self) -> None:
        await self._http.aclose()
