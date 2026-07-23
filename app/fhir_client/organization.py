"""
FHIR client for Organization resources.

Thin wrapper around the shared FhirClient that knows the fhir-server paths
for the Organization resource. No business logic lives here — all
validation and rules (dedup-by-name, tenant ownership checks) belong in
OrganizationsService. Same shape as app/fhir_client/patient.py.

Unlike Patient, Organization has no separately-routed sub-resources on the
fhir-server — its child arrays (identifier, type, alias, telecom, address,
contact, endpoint) are set at creation time and only ever read back as part
of the parent resource, so this client exposes only the five core verbs.

Reference: https://hl7.org/fhir/R4/organization.html
"""

from app.auth.models import AuthUser
from app.fhir_client.client import FhirClient

# Base path for all Organization endpoints on the fhir-server.
_PATH = "/organizations"


class OrganizationClient:
    """
    Domain-specific HTTP client for Organization resources.

    Delegates every request to the shared FhirClient singleton, which
    handles authentication headers, base-URL resolution, and error
    propagation. The `accept` parameter is threaded through all
    body-returning methods so the caller can request plain JSON or FHIR R4
    format.
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
        """POST /organizations — create a new Organization resource."""
        return await self._fhir.post(_PATH, data, actor, accept=accept)

    async def get_by_id(self, organization_id: int, accept: str | None = None) -> dict:
        """GET /organizations/{organization_id} — fetch a single Organization by integer ID."""
        return await self._fhir.get(f"{_PATH}/{organization_id}", accept=accept)

    async def list(self, accept: str | None = None, **params) -> dict:
        """
        GET /organizations — list Organizations with optional filters.

        Strips None values from **params — a query string of `?name=None`
        would be rejected by the fhir-server, whereas an omitted param means
        "no filter" and is what we intend.
        """
        clean = {k: v for k, v in params.items() if v is not None}
        return await self._fhir.get(_PATH, params=clean, accept=accept)

    async def patch(
        self,
        organization_id: int,
        data: dict,
        actor: AuthUser,
        accept: str | None = None,
    ) -> dict:
        """PATCH /organizations/{organization_id} — partially update an Organization."""
        return await self._fhir.patch(
            f"{_PATH}/{organization_id}", data, actor, accept=accept
        )

    async def delete(self, organization_id: int) -> None:
        """DELETE /organizations/{organization_id} — permanently remove an Organization."""
        await self._fhir.delete(f"{_PATH}/{organization_id}")
