"""
FHIR client for Organization resources.

Thin wrapper around the shared FhirClient that knows the fhir-server paths
for the Organization resource. No business logic lives here — all
validation belongs in OrganizationsService. Same shape as
app/fhir_client/patient.py.

Unlike Patient/Practitioner, Organization has no separately-routed
sub-resources on the fhir-server — its child arrays (identifier, type,
alias, telecom, address, contact, endpoint) are set at creation time and
only ever read back as part of the parent resource, so this client exposes
only the five core verbs.

Every method takes `actor: AuthUser` and forwards it to FhirClient so the
Authorization header reaches the fhir-server — Organization now validates
JWTs independently (JWT/RBAC rollout), rather than trusting the gateway
unconditionally.

create/patch pass inject_audit=False: fhir-server derives created_by/
updated_by from the verified JWT's `sub` claim itself for Organization, and
its schemas (extra="forbid") no longer declare those fields at all — if
FhirClient injected them into the body here, fhir-server would reject the
request with 422.

Reference: https://hl7.org/fhir/R4/organization.html
"""

from app.auth.models import AuthUser
from app.connectors.base import Connector
from app.core.logging import trace_methods

# Base path for all Organization endpoints on the fhir-server.
_PATH = "/organizations"


@trace_methods
class OrganizationClient:
    """
    Domain-specific HTTP client for Organization resources.

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
        """POST /organizations — create a new Organization resource."""
        return await self._fhir.post(
            _PATH, data, actor, accept=accept, inject_audit=False
        )

    async def get_by_id(
        self, organization_id: int, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """GET /organizations/{organization_id} — fetch a single Organization by integer ID."""
        return await self._fhir.get(
            f"{_PATH}/{organization_id}", accept=accept, actor=actor
        )

    async def list(self, actor: AuthUser, accept: str | None = None, **params) -> dict:
        """
        GET /organizations — list Organizations with optional filters.

        Strips None values from **params — a query string of `?name=None`
        would be rejected by the fhir-server, whereas an omitted param means
        "no filter" and is what we intend.
        """
        clean = {k: v for k, v in params.items() if v is not None}
        return await self._fhir.get(_PATH, params=clean, accept=accept, actor=actor)

    async def patch(
        self,
        organization_id: int,
        data: dict,
        actor: AuthUser,
        accept: str | None = None,
    ) -> dict:
        """PATCH /organizations/{organization_id} — partially update an Organization."""
        return await self._fhir.patch(
            f"{_PATH}/{organization_id}", data, actor, accept=accept, inject_audit=False
        )

    async def delete(self, organization_id: int, actor: AuthUser) -> None:
        """DELETE /organizations/{organization_id} — permanently remove an Organization."""
        await self._fhir.delete(f"{_PATH}/{organization_id}", actor=actor)
