"""
Business logic service for the Location resource.

LocationService sits between the router/resolvers and LocationClient. It is
a thin pass-through — same shape as OrganizationsService — because
fhir-server now owns every rule that used to live here:
  - `part_of` (parent Location) existence/tenant-match/circular-hierarchy
    validation, and `managing_organization` existence/tenant-match
    validation (previously done client-side against OrganizationClient) are
    gone. fhir-server's own repository-level validation is authoritative —
    see app/repository/location/full.py on fhir-server, which raises a 404
    on a missing/cross-tenant reference and a 409 on a circular hierarchy —
    pre-checking here only risked disagreeing with the server.
  - The old "fetch unauthenticated, check_tenant_ownership client-side, then
    refetch" dance on get_by_id/update/delete is gone too — fhir-server's
    `get_location_scoped()` already 404s a cross-org access server-side once
    the caller's JWT is forwarded (see LocationClient), so each of those is
    now a single client call.

The service does NOT inject created_by/updated_by — FhirClient does that
automatically from actor.sub on every POST and PATCH.
"""

from fastapi import HTTPException, status

from app.auth.models import AuthUser
from app.fhir_client.location import LocationClient
from app.schemas.location.input import (
    ListLocationsSchema,
    LocationCreateSchema,
    LocationPatchSchema,
)
from app.core.logging import trace_methods


@trace_methods
class LocationService:
    """
    Application service for Location CRUD use cases.

    Instantiated per-request by the DI container (LocationContainer) via
    Factory provider, so it holds no shared state between requests.
    """

    def __init__(self, client: LocationClient) -> None:
        """
        Args:
            client: The LocationClient injected by the DI container.
                    Provides fhir-server access for all Location operations.
        """
        self._client = client

    async def create(
        self, dto: LocationCreateSchema, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Create a new Location resource on the fhir-server.

        fhir-server validates `part_of` (existence, tenant match, and the
        circular-hierarchy business rule) and `managing_organization`
        (existence, tenant match) server-side and returns 404/409/422 —
        this method does not re-implement any of that.

        Args:
            dto:    Validated create input from the resolver/router.
            actor:  Authenticated caller — used by FhirClient for created_by
                    and forwarded as the Authorization header.
            accept: Content-type preference forwarded to the fhir-server.

        Returns:
            The newly created Location resource dict (plain JSON or FHIR R4).
        """
        payload = dto.model_dump(exclude_none=True, mode="json")
        return await self._client.create(payload, actor, accept=accept)

    async def get_by_id(
        self, location_id: int, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Fetch a single Location by its integer ID.

        fhir-server scopes this to the caller's own org via the verified JWT
        (get_location_scoped()) and 404s a cross-org access itself — no
        client-side ownership check needed here.

        Args:
            location_id: The integer primary key of the Location.
            actor:       Authenticated caller — forwarded as the Authorization header.
            accept:      Content-type preference forwarded to the fhir-server.

        Returns:
            The Location resource dict in the requested format.
        """
        return await self._client.get_by_id(location_id, actor, accept=accept)

    async def list(
        self, filters: ListLocationsSchema, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Return a paginated, filtered list of Location resources.

        org_id is never forwarded as a filter — fhir-server always scopes
        Location reads to the caller's own org via the verified JWT.

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
            identifier=filters.identifier,
            organization=filters.organization,
            partof=filters.partof,
            endpoint=filters.endpoint,
            near=filters.near,
            sort=filters.sort,
            total_mode=filters.total_mode,
            limit=filters.limit,
            offset=filters.offset,
            # Query-string names below diverge from the Python field names
            # they come from (fhir-server's router aliases them, e.g.
            # `status` for location_status) — passed as a merged dict since
            # they aren't valid Python keyword-argument names on their own.
            **{
                "status": filters.location_status,
                "operational-status": filters.operational_status,
                "type": filters.location_type,
                "physical-type": filters.physical_type,
                "address-city": filters.address_city,
                "address-state": filters.address_state,
                "address-postalcode": filters.address_postal_code,
                "address-country": filters.address_country,
                "address-use": filters.address_use,
            },
            address=filters.address,
        )

    async def update(
        self,
        location_id: int,
        dto: LocationPatchSchema,
        actor: AuthUser,
        accept: str | None = None,
    ) -> dict:
        """
        Partially update a Location resource.

        fhir-server scopes this to the caller's own org (404 on mismatch)
        and validates `part_of`/`managing_organization` (existence, tenant
        match, circular-hierarchy check for `part_of`) server-side.

        Args:
            location_id: The integer primary key of the Location to update.
            dto:         Validated partial payload; all fields Optional.
            actor:       Authenticated user — used by FhirClient for updated_by
                         and forwarded as the Authorization header.
            accept:      Content-type preference forwarded to the fhir-server.

        Returns:
            The updated Location resource dict in the requested format.

        Raises:
            HTTPException(422): If the request body contained no updateable fields.
        """
        payload = dto.model_dump(exclude_none=True, mode="json")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one field must be provided for update.",
            )
        return await self._client.patch(location_id, payload, actor, accept=accept)

    async def delete(self, location_id: int, actor: AuthUser) -> None:
        """
        Delete a Location resource.

        fhir-server scopes this to the caller's own org (404 on mismatch)
        server-side — no client-side ownership check needed here.

        Args:
            location_id: The integer primary key of the Location to delete.
            actor:       Authenticated user — forwarded as the Authorization header.
        """
        await self._client.delete(location_id, actor)
