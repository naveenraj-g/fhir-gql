"""
Business logic service for the PractitionerRole resource.

PractitionerRoleService sits between the router/resolvers and
PractitionerRoleClient. It is a thin pass-through — same shape as
OrganizationsService/LocationService/HealthcareServiceService — because
fhir-server now owns every rule that used to live here:
  - `practitioner`, `organization`, `location[]`, and `healthcare_service[]`
    existence/tenant-match validation (previously done client-side against
    four sibling clients) is gone. fhir-server's own repository-level
    validation is authoritative for all four — see
    app/repository/practitioner_role/full.py on fhir-server, which
    validates every one of them on both create AND patch (PractitionerRole's
    PatchSchema now exposes every field/sub-resource list, not just the four
    scalar fields this port previously assumed) and raises 404 on a
    missing/cross-tenant reference — pre-checking here only risked
    disagreeing with the server.
  - No tenant-ownership enforcement is added on by-id routes either —
    fhir-server's `get_practitioner_role_scoped()` already 404s a cross-org
    access server-side once the caller's JWT is forwarded (see
    PractitionerRoleClient), so each of those is now a single client call.
  - `list_for_booking()` remains a straightforward proxy — unrelated to the
    JWT-rollout/reference-validation work above. NOTE: `/practitioner-roles/
    booking` does not exist on the current fhir-server (verified: no such
    route in app/routers/practitioner_role/core.py) — this method predates
    that observation and is left untouched as out of scope for this port;
    calling it will 404 against a real fhir-server instance.

The service does NOT inject created_by/updated_by — FhirClient does that
automatically from actor.sub on every POST and PATCH.
"""

from fastapi import HTTPException, status

from app.auth.models import AuthUser
from app.fhir_client.practitioner_role import PractitionerRoleClient
from app.schemas.practitioner_role.input import (
    ListPractitionerRolesSchema,
    PractitionerRoleCreateSchema,
    PractitionerRolePatchSchema,
)
from app.core.logging import trace_methods


@trace_methods
class PractitionerRoleService:
    """
    Application service for PractitionerRole CRUD use cases.

    Instantiated per-request by the DI container (PractitionerRoleContainer)
    via Factory provider, so it holds no shared state between requests.
    """

    def __init__(self, client: PractitionerRoleClient) -> None:
        """
        Args:
            client: The PractitionerRoleClient injected by the DI container.
                    Provides fhir-server access for all PractitionerRole operations.
        """
        self._client = client

    async def create(
        self, dto: PractitionerRoleCreateSchema, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Create a new PractitionerRole resource on the fhir-server.

        fhir-server validates `practitioner`, `organization`, each
        `location[]` entry, and each `healthcare_service[]` entry
        (existence + tenant match) server-side and returns 404/422 — this
        method does not re-implement any of that.

        Args:
            dto:    Validated create input from the resolver/router.
            actor:  Authenticated caller — used by FhirClient for created_by
                    and forwarded as the Authorization header.
            accept: Content-type preference forwarded to the fhir-server.

        Returns:
            The newly created PractitionerRole resource dict (plain JSON or FHIR R4).
        """
        payload = dto.model_dump(exclude_none=True, mode="json")
        return await self._client.create(payload, actor, accept=accept)

    async def get_by_id(
        self, resource_id: int, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Fetch a single PractitionerRole by its integer ID.

        fhir-server scopes this to the caller's own org via the verified JWT
        (get_practitioner_role_scoped()) and 404s a cross-org access itself
        — no client-side ownership check needed here.

        Args:
            resource_id: The integer primary key of the PractitionerRole.
            actor:       Authenticated caller — forwarded as the Authorization header.
            accept:      Content-type preference forwarded to the fhir-server.

        Returns:
            The PractitionerRole resource dict in the requested format.
        """
        return await self._client.get_by_id(resource_id, actor, accept=accept)

    async def list(
        self, filters: ListPractitionerRolesSchema, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Return a paginated, filtered list of PractitionerRole resources.

        org_id is never forwarded as a filter — fhir-server always scopes
        PractitionerRole reads to the caller's own org via the verified JWT.

        Args:
            filters: Validated query parameters from the resolver/router.
            actor:   Authenticated caller — forwarded as the Authorization header.
            accept:  Content-type preference — FHIR R4 wraps results in a Bundle.

        Returns:
            Paginated plain JSON dict or FHIR Bundle depending on `accept`.
        """
        return await self._client.list(
            actor,
            accept=accept,
            active=filters.active,
            date=filters.date,
            email=filters.email,
            phone=filters.phone,
            telecom=filters.telecom,
            identifier=filters.identifier,
            role=filters.role,
            specialty=filters.specialty,
            practitioner=filters.practitioner,
            organization=filters.organization,
            location=filters.location,
            service=filters.service,
            endpoint=filters.endpoint,
            sort=filters.sort,
            total_mode=filters.total_mode,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def update(
        self,
        resource_id: int,
        dto: PractitionerRolePatchSchema,
        actor: AuthUser,
        accept: str | None = None,
    ) -> dict:
        """
        Partially update a PractitionerRole resource.

        fhir-server scopes this to the caller's own org (404 on mismatch)
        and re-validates `practitioner`/`organization`/`location[]`/
        `healthcare_service[]` (existence, tenant match) server-side
        whenever the caller includes them in the patch payload.

        Args:
            resource_id: The integer primary key of the PractitionerRole to update.
            dto:         Validated partial payload; all fields Optional.
            actor:       Authenticated user — used by FhirClient for updated_by
                         and forwarded as the Authorization header.
            accept:      Content-type preference forwarded to the fhir-server.

        Returns:
            The updated PractitionerRole resource dict in the requested format.

        Raises:
            HTTPException(422): If the request body contained no updateable fields.
        """
        payload = dto.model_dump(exclude_none=True, mode="json")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one field must be provided for update.",
            )
        return await self._client.patch(resource_id, payload, actor, accept=accept)

    async def list_for_booking(
        self,
        active: bool = True,
        specialty_code: str | None = None,
        day_of_week: str | None = None,
        org_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
        accept: str | None = None,
    ) -> dict:
        """
        List PractitionerRoles enriched with Practitioner details for booking UIs.

        NOT part of the current fhir-server API — see this module's
        docstring. Left untouched, out of scope for this port.
        """
        return await self._client.list_for_booking(
            accept=accept,
            active=active,
            specialty_code=specialty_code,
            day_of_week=day_of_week,
            org_id=org_id,
            limit=limit,
            offset=offset,
        )

    async def delete(self, resource_id: int, actor: AuthUser) -> None:
        """
        Delete a PractitionerRole resource.

        fhir-server scopes this to the caller's own org (404 on mismatch)
        server-side — no client-side ownership check needed here.

        Args:
            resource_id: The integer primary key of the PractitionerRole to delete.
            actor:       Authenticated user — forwarded as the Authorization header.
        """
        await self._client.delete(resource_id, actor)
