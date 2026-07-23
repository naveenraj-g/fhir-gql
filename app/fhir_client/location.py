"""
FHIR client for Location resources.

Thin wrapper around the shared FhirClient that knows the fhir-server path
for the Location resource. No business logic lives here — all validation
(managing_organization/part_of existence+tenant checks, part_of cycle
detection) belongs in LocationService. Same shape as
app/fhir_client/organization.py.

Reference: https://hl7.org/fhir/R4/location.html
"""

from app.auth.models import AuthUser
from app.fhir_client.client import FhirClient

# Base path for all Location endpoints on the fhir-server.
_PATH = "/locations"


class LocationClient:
    """
    Domain-specific HTTP client for Location resources.

    Delegates every request to the shared FhirClient singleton, which
    handles authentication headers, base-URL resolution, and error
    propagation.
    """

    def __init__(self, fhir: FhirClient) -> None:
        """
        Args:
            fhir: The singleton FhirClient — owns the httpx session and base URL config.
        """
        self._fhir = fhir

    async def create(self, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """POST /locations — create a new Location resource."""
        return await self._fhir.post(_PATH, data, actor, accept=accept)

    async def get_by_id(self, location_id: int, accept: str | None = None) -> dict:
        """GET /locations/{location_id} — fetch a single Location by integer ID."""
        return await self._fhir.get(f"{_PATH}/{location_id}", accept=accept)

    async def list(self, accept: str | None = None, **params) -> dict:
        """
        GET /locations — list Locations with optional filters.

        Strips None values from **params — an omitted param means "no
        filter", not a literal `?key=None` sent to the fhir-server.
        """
        clean = {k: v for k, v in params.items() if v is not None}
        return await self._fhir.get(_PATH, params=clean, accept=accept)

    async def patch(self, location_id: int, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """PATCH /locations/{location_id} — partially update a Location."""
        return await self._fhir.patch(f"{_PATH}/{location_id}", data, actor, accept=accept)

    async def delete(self, location_id: int) -> None:
        """DELETE /locations/{location_id} — permanently remove a Location."""
        await self._fhir.delete(f"{_PATH}/{location_id}")
