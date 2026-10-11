"""
Business logic service for the HealthcareService resource.

HealthcareServiceService sits between the router/resolvers and
HealthcareServiceClient. It is a thin pass-through — same shape as
OrganizationsService/LocationService — because fhir-server now owns every
rule that used to live here:
  - `provided_by` (-> Organization), `location[]` (-> Location), and
    `coverage_area[]` (-> Location) existence/tenant-match validation
    (previously done client-side against OrganizationClient/LocationClient)
    are gone. fhir-server's own repository-level validation is authoritative
    — see app/repository/healthcare_service/full.py on fhir-server, which
    raises a 404 on a missing/cross-tenant reference — pre-checking here
    only risked disagreeing with the server. This validation now applies on
    both create AND update, since fhir-server's HealthcareServicePatchSchema
    exposes `provided_by`/`location`/`coverage_area` too (unlike this
    gateway's pre-rollout assumption that only scalar/photo fields were
    patchable).
  - The old "fetch unauthenticated, check_tenant_ownership client-side, then
    refetch" dance on get_by_id/update/delete is gone too — fhir-server's
    `get_healthcare_service_scoped()` already 404s a cross-org access
    server-side once the caller's JWT is forwarded (see
    HealthcareServiceClient), so each of those is now a single client call.

The service does NOT inject created_by/updated_by — FhirClient does that
automatically from actor.sub on every POST and PATCH.
"""

from fastapi import HTTPException, status

from app.auth.models import AuthUser
from app.fhir_client.healthcare_service import HealthcareServiceClient
from app.schemas.healthcare_service.input import (
    HealthcareServiceCreateSchema,
    HealthcareServicePatchSchema,
    ListHealthcareServicesSchema,
)


class HealthcareServiceService:
    """
    Application service for HealthcareService CRUD use cases.

    Instantiated per-request by the DI container (HealthcareServiceContainer)
    via Factory provider, so it holds no shared state between requests.
    """

    def __init__(self, client: HealthcareServiceClient) -> None:
        """
        Args:
            client: The HealthcareServiceClient injected by the DI container.
                    Provides fhir-server access for all HealthcareService operations.
        """
        self._client = client

    async def create(
        self,
        dto: HealthcareServiceCreateSchema,
        actor: AuthUser,
        accept: str | None = None,
    ) -> dict:
        """
        Create a new HealthcareService resource on the fhir-server.

        fhir-server validates `provided_by`/`location`/`coverage_area`
        (existence, tenant match) server-side and returns 404/422 — this
        method does not re-implement any of that.

        Args:
            dto:    Validated create input from the resolver/router.
            actor:  Authenticated caller — used by FhirClient for created_by
                    and forwarded as the Authorization header.
            accept: Content-type preference forwarded to the fhir-server.

        Returns:
            The newly created HealthcareService resource dict (plain JSON or FHIR R4).
        """
        payload = dto.model_dump(exclude_none=True, mode="json")
        return await self._client.create(payload, actor, accept=accept)

    async def get_by_id(
        self, service_id: int, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Fetch a single HealthcareService by its integer ID.

        fhir-server scopes this to the caller's own org via the verified JWT
        (get_healthcare_service_scoped()) and 404s a cross-org access itself
        — no client-side ownership check needed here.

        Args:
            service_id: The integer primary key of the HealthcareService.
            actor:      Authenticated caller — forwarded as the Authorization header.
            accept:     Content-type preference forwarded to the fhir-server.

        Returns:
            The HealthcareService resource dict in the requested format.
        """
        return await self._client.get_by_id(service_id, actor, accept=accept)

    async def list(
        self,
        filters: ListHealthcareServicesSchema,
        actor: AuthUser,
        accept: str | None = None,
    ) -> dict:
        """
        Return a paginated, filtered list of HealthcareService resources.

        org_id is never forwarded as a filter — fhir-server always scopes
        HealthcareService reads to the caller's own org via the verified JWT.

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
            name=filters.name,
            active=filters.active,
            identifier=filters.identifier,
            specialty=filters.specialty,
            characteristic=filters.characteristic,
            program=filters.program,
            location=filters.location,
            endpoint=filters.endpoint,
            sort=filters.sort,
            total_mode=filters.total_mode,
            limit=filters.limit,
            offset=filters.offset,
            # Query-string names below diverge from the Python field names
            # they come from (fhir-server's router aliases them, e.g.
            # `service-category` for category) — passed as a merged dict
            # since they aren't valid Python keyword-argument names on their own.
            **{
                "service-category": filters.category,
                "service-type": filters.service_type,
                "organization": filters.provided_by,
                "coverage-area": filters.coverage_area,
            },
        )

    async def update(
        self,
        service_id: int,
        dto: HealthcareServicePatchSchema,
        actor: AuthUser,
        accept: str | None = None,
    ) -> dict:
        """
        Partially update a HealthcareService resource.

        fhir-server scopes this to the caller's own org (404 on mismatch)
        and validates `provided_by`/`location`/`coverage_area` (existence,
        tenant match) server-side.

        Args:
            service_id: The integer primary key of the HealthcareService to update.
            dto:        Validated partial payload; all fields Optional.
            actor:      Authenticated user — used by FhirClient for updated_by
                        and forwarded as the Authorization header.
            accept:     Content-type preference forwarded to the fhir-server.

        Returns:
            The updated HealthcareService resource dict in the requested format.

        Raises:
            HTTPException(422): If the request body contained no updateable fields.
        """
        payload = dto.model_dump(exclude_none=True, mode="json")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one field must be provided for update.",
            )
        return await self._client.patch(service_id, payload, actor, accept=accept)

    async def delete(self, service_id: int, actor: AuthUser) -> None:
        """
        Delete a HealthcareService resource.

        fhir-server scopes this to the caller's own org (404 on mismatch)
        server-side — no client-side ownership check needed here.

        Args:
            service_id: The integer primary key of the HealthcareService to delete.
            actor:      Authenticated user — forwarded as the Authorization header.
        """
        await self._client.delete(service_id, actor)
