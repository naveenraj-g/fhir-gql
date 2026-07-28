"""
FHIR client for PractitionerRole resources.

Thin wrapper around the shared FhirClient that knows the fhir-server path
for the PractitionerRole resource. No business logic lives here — all
validation (practitioner/organization/location/healthcare_service existence
+ tenant checks) belongs in PractitionerRoleService. Same shape as
app/fhir_client/organization.py.

A PractitionerRole describes the role a Practitioner plays within an
Organization at a given Location and/or for a set of HealthcareServices.

Reference: https://hl7.org/fhir/R4/practitionerrole.html
"""

from app.auth.models import AuthUser
from app.fhir_client.client import FhirClient

_PATH = "/practitioner-roles"


class PractitionerRoleClient:
    """
    Domain-specific HTTP client for PractitionerRole resources.

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
        """POST /practitioner-roles — create a new PractitionerRole resource."""
        return await self._fhir.post(_PATH, data, actor, accept=accept)

    async def get_by_id(self, resource_id: int, accept: str | None = None) -> dict:
        """GET /practitioner-roles/{resource_id} — fetch a single PractitionerRole by integer ID."""
        return await self._fhir.get(f"{_PATH}/{resource_id}", accept=accept)

    async def list(self, accept: str | None = None, **params) -> dict:
        """
        GET /practitioner-roles — list PractitionerRoles with optional filters.

        Strips None values from **params — an omitted param means "no
        filter", not a literal `?key=None` sent to the fhir-server.
        """
        clean = {k: v for k, v in params.items() if v is not None}
        return await self._fhir.get(_PATH, params=clean, accept=accept)

    async def patch(self, resource_id: int, data: dict, actor: AuthUser, accept: str | None = None) -> dict:
        """PATCH /practitioner-roles/{resource_id} — partially update a PractitionerRole."""
        return await self._fhir.patch(f"{_PATH}/{resource_id}", data, actor, accept=accept)

    async def list_for_booking(self, accept: str | None = None, **params) -> dict:
        """
        GET /practitioner-roles/booking — list practitioners enriched for booking UIs.

        Proxies to the fhir-server's /practitioner-roles/booking endpoint,
        which joins each PractitionerRole with its linked Practitioner record
        (name, gender, photo, qualifications) and enriched Location/
        HealthcareService data — no joining happens in fhir-gql itself.
        """
        clean = {k: v for k, v in params.items() if v is not None}
        return await self._fhir.get(f"{_PATH}/booking", params=clean, accept=accept)

    async def delete(self, resource_id: int) -> None:
        """DELETE /practitioner-roles/{resource_id} — permanently remove a PractitionerRole."""
        await self._fhir.delete(f"{_PATH}/{resource_id}")
