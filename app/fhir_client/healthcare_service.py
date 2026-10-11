"""
FHIR client for HealthcareService resources.

Thin wrapper around the shared FhirClient that knows the fhir-server path
for the HealthcareService resource. No business logic lives here — all
validation (provided_by/location/coverage_area existence+tenant checks) now
lives entirely on fhir-server itself (see
app/repository/healthcare_service/full.py on fhir-server). Same shape as
app/fhir_client/organization.py and app/fhir_client/location.py.

Every method takes `actor: AuthUser` and forwards it to FhirClient so the
Authorization header reaches the fhir-server — HealthcareService now
validates JWTs independently (JWT/RBAC rollout), rather than trusting the
gateway unconditionally.

create/patch pass inject_audit=False: fhir-server derives created_by/
updated_by from the verified JWT's `sub` claim itself for HealthcareService,
and its schemas (extra="forbid") no longer declare those fields at all — if
FhirClient injected them into the body here, fhir-server would reject the
request with 422.

The fhir-server registers this resource at /healthcare-services (hyphenated
— the FHIR convention for multi-word resource names in REST URLs).

Reference: https://hl7.org/fhir/R4/healthcareservice.html
"""

from app.auth.models import AuthUser
from app.connectors.base import Connector
from app.core.logging import trace_methods

# Base path for all HealthcareService endpoints on the fhir-server.
_PATH = "/healthcare-services"


@trace_methods
class HealthcareServiceClient:
    """
    Domain-specific HTTP client for HealthcareService resources.

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
        """POST /healthcare-services — create a new HealthcareService resource."""
        return await self._fhir.post(_PATH, data, actor, accept=accept, inject_audit=False)

    async def get_by_id(self, service_id: int, actor: AuthUser, accept: str | None = None) -> dict:
        """GET /healthcare-services/{service_id} — fetch a single HealthcareService by integer ID."""
        return await self._fhir.get(f"{_PATH}/{service_id}", accept=accept, actor=actor)

    async def list(self, actor: AuthUser, accept: str | None = None, **params) -> dict:
        """
        GET /healthcare-services — list HealthcareServices with optional filters.

        Strips None values from **params — an omitted param means "no
        filter", not a literal `?key=None` sent to the fhir-server.
        """
        clean = {k: v for k, v in params.items() if v is not None}
        return await self._fhir.get(_PATH, params=clean, accept=accept, actor=actor)

    async def patch(
        self,
        service_id: int,
        data: dict,
        actor: AuthUser,
        accept: str | None = None,
    ) -> dict:
        """PATCH /healthcare-services/{service_id} — partially update a HealthcareService."""
        return await self._fhir.patch(
            f"{_PATH}/{service_id}", data, actor, accept=accept, inject_audit=False
        )

    async def delete(self, service_id: int, actor: AuthUser) -> None:
        """DELETE /healthcare-services/{service_id} — permanently remove a HealthcareService."""
        await self._fhir.delete(f"{_PATH}/{service_id}", actor=actor)
