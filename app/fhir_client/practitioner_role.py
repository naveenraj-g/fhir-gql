"""
FHIR client for PractitionerRole resources.

Thin wrapper around the shared FhirClient that knows the fhir-server paths
for the PractitionerRole resource. No business logic lives here — all
validation now lives entirely on fhir-server itself (existence/tenant-match
checks for `practitioner`, `organization`, each `location[]` entry, and
each `healthcare_service[]` entry — see app/repository/practitioner_role/
full.py on fhir-server). Same shape as app/fhir_client/organization.py.

Every method takes `actor: AuthUser` and forwards it to FhirClient so the
Authorization header reaches the fhir-server — PractitionerRole now
validates JWTs independently (JWT/RBAC rollout), rather than trusting the
gateway unconditionally.

create/patch pass inject_audit=False: fhir-server derives created_by/
updated_by from the verified JWT's `sub` claim itself for PractitionerRole,
and its schemas (extra="forbid") no longer declare those fields at all — if
FhirClient injected them into the body here, fhir-server would reject the
request with 422.

`list_for_booking()` proxies to a `/practitioner-roles/booking` endpoint
that does not exist on the current fhir-server (verified: no such route in
app/routers/practitioner_role/core.py) — left untouched, out of scope for
this port (see the service/gql layers for the same note).

Reference: https://hl7.org/fhir/R4/practitionerrole.html
"""

from app.auth.models import AuthUser
from app.fhir_client.client import FhirClient

# Base path for all PractitionerRole endpoints on the fhir-server.
_PATH = "/practitioner-roles"


class PractitionerRoleClient:
    """
    Domain-specific HTTP client for PractitionerRole resources.

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
        """POST /practitioner-roles — create a new PractitionerRole resource."""
        return await self._fhir.post(_PATH, data, actor, accept=accept, inject_audit=False)

    async def get_by_id(
        self, resource_id: int, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """GET /practitioner-roles/{resource_id} — fetch a single PractitionerRole by integer ID."""
        return await self._fhir.get(f"{_PATH}/{resource_id}", accept=accept, actor=actor)

    async def list(self, actor: AuthUser, accept: str | None = None, **params) -> dict:
        """
        GET /practitioner-roles — list PractitionerRoles with optional filters.

        Strips None values from **params — a query string of `?name=None`
        would be rejected by the fhir-server, whereas an omitted param means
        "no filter" and is what we intend.
        """
        clean = {k: v for k, v in params.items() if v is not None}
        return await self._fhir.get(_PATH, params=clean, accept=accept, actor=actor)

    async def patch(
        self,
        resource_id: int,
        data: dict,
        actor: AuthUser,
        accept: str | None = None,
    ) -> dict:
        """PATCH /practitioner-roles/{resource_id} — partially update a PractitionerRole."""
        return await self._fhir.patch(
            f"{_PATH}/{resource_id}", data, actor, accept=accept, inject_audit=False
        )

    async def list_for_booking(self, accept: str | None = None, **params) -> dict:
        """
        GET /practitioner-roles/booking — list practitioners enriched for booking UIs.

        NOT part of the current fhir-server API (no such route exists on
        fhir-server as of this port) — left as-is, out of scope. Calling
        this will 404 against a real fhir-server instance.
        """
        clean = {k: v for k, v in params.items() if v is not None}
        return await self._fhir.get(f"{_PATH}/booking", params=clean, accept=accept)

    async def delete(self, resource_id: int, actor: AuthUser) -> None:
        """DELETE /practitioner-roles/{resource_id} — permanently remove a PractitionerRole."""
        await self._fhir.delete(f"{_PATH}/{resource_id}", actor=actor)
