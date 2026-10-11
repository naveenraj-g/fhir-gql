"""
FHIR client for Location resources.

Thin wrapper around the shared FhirClient that knows the fhir-server paths
for the Location resource. No business logic lives here — all validation
now lives entirely on fhir-server itself (existence/tenant-match/circular-
hierarchy checks for `part_of`, existence/tenant-match for
`managing_organization` — see app/repository/location/full.py on
fhir-server). Same shape as app/fhir_client/organization.py.

Every method takes `actor: AuthUser` and forwards it to FhirClient so the
Authorization header reaches the fhir-server — Location now validates JWTs
independently (JWT/RBAC rollout), rather than trusting the gateway
unconditionally.

create/patch pass inject_audit=False: fhir-server derives created_by/
updated_by from the verified JWT's `sub` claim itself for Location, and its
schemas (extra="forbid") no longer declare those fields at all — if
FhirClient injected them into the body here, fhir-server would reject the
request with 422.

Reference: https://hl7.org/fhir/R4/location.html
"""

from app.auth.models import AuthUser
from app.connectors.base import Connector
from app.core.logging import trace_methods

# Base path for all Location endpoints on the fhir-server.
_PATH = "/locations"


@trace_methods
class LocationClient:
    """
    Domain-specific HTTP client for Location resources.

    Delegates every request to the shared FhirClient singleton, which
    handles authentication headers, base-URL resolution, and error
    propagation. The `accept` parameter is threaded through all
    body-returning methods so the caller can request plain JSON or FHIR R4
    format.
    """

    def __init__(self, fhir: Connector) -> None:
        """
        Args:
            fhir: The singleton FhirClient — owns the httpx session and base URL config.
        """
        self._fhir = fhir

    async def create(
        self, data: dict, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """POST /locations — create a new Location resource."""
        return await self._fhir.post(_PATH, data, actor, accept=accept, inject_audit=False)

    async def get_by_id(self, location_id: int, actor: AuthUser, accept: str | None = None) -> dict:
        """GET /locations/{location_id} — fetch a single Location by integer ID."""
        return await self._fhir.get(f"{_PATH}/{location_id}", accept=accept, actor=actor)

    async def list(self, actor: AuthUser, accept: str | None = None, **params) -> dict:
        """
        GET /locations — list Locations with optional filters.

        Strips None values from **params — a query string of `?name=None`
        would be rejected by the fhir-server, whereas an omitted param means
        "no filter" and is what we intend.
        """
        clean = {k: v for k, v in params.items() if v is not None}
        return await self._fhir.get(_PATH, params=clean, accept=accept, actor=actor)

    async def patch(
        self,
        location_id: int,
        data: dict,
        actor: AuthUser,
        accept: str | None = None,
    ) -> dict:
        """PATCH /locations/{location_id} — partially update a Location."""
        return await self._fhir.patch(
            f"{_PATH}/{location_id}", data, actor, accept=accept, inject_audit=False
        )

    async def delete(self, location_id: int, actor: AuthUser) -> None:
        """DELETE /locations/{location_id} — permanently remove a Location."""
        await self._fhir.delete(f"{_PATH}/{location_id}", actor=actor)
