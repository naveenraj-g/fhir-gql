"""
FHIR client for HealthcareService resources.

Thin wrapper around the shared FhirClient that knows the fhir-server path
for the HealthcareService resource. No business logic lives here — all
validation (provided_by/location/coverage_area existence+tenant checks)
belongs in HealthcareServiceService. Same shape as
app/fhir_client/organization.py and app/fhir_client/location.py.

The fhir-server registers this resource at /healthcare-services (hyphenated
— the FHIR convention for multi-word resource names in REST URLs).

Reference: https://hl7.org/fhir/R4/healthcareservice.html
"""

from app.auth.models import AuthUser
from app.fhir_client.client import FhirClient

_PATH = "/healthcare-services"


class HealthcareServiceClient:
    """
    Domain-specific HTTP client for HealthcareService resources.

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

    async def create(
        self, data: dict, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """POST /healthcare-services — create a new HealthcareService resource."""
        return await self._fhir.post(_PATH, data, actor, accept=accept)

    async def get_by_id(self, service_id: int, accept: str | None = None) -> dict:
        """GET /healthcare-services/{service_id} — fetch a single HealthcareService by integer ID."""
        return await self._fhir.get(f"{_PATH}/{service_id}", accept=accept)

    async def list(self, accept: str | None = None, **params) -> dict:
        """
        GET /healthcare-services — list HealthcareServices with optional filters.

        Strips None values from **params — an omitted param means "no
        filter", not a literal `?key=None` sent to the fhir-server.
        """
        clean = {k: v for k, v in params.items() if v is not None}
        return await self._fhir.get(_PATH, params=clean, accept=accept)

    async def patch(
        self, service_id: int, data: dict, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """PATCH /healthcare-services/{service_id} — partially update a HealthcareService."""
        return await self._fhir.patch(
            f"{_PATH}/{service_id}", data, actor, accept=accept
        )

    async def delete(self, service_id: int) -> None:
        """DELETE /healthcare-services/{service_id} — permanently remove a HealthcareService."""
        await self._fhir.delete(f"{_PATH}/{service_id}")
