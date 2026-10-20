"""
Business logic service for the Organization resource.

OrganizationsService sits between the router/resolvers and OrganizationClient.
It is a thin pass-through — same shape as PatientService/PractitionerService
— because fhir-server now owns every rule that used to live here:
  - Duplicate-name dedup and the `partof` existence pre-check (previously
    done client-side) are gone. fhir-server's own `partof` validation is
    authoritative *and* correctly detects circular hierarchies (the old
    client-side check here explicitly didn't) — pre-checking here only
    risked disagreeing with the server. Let fhir-server's 422 respond
    directly (translate_errors/FhirClient._extract_detail surface it as a
    clean GraphQL error).
  - The old "fetch unauthenticated, check_tenant_ownership client-side, then
    refetch" dance on get_by_id/update/delete is gone too — fhir-server's
    `get_organization_scoped()` already 404s a cross-org access server-side
    once the caller's JWT is forwarded (see OrganizationClient), so each of
    those is now a single client call.

The service does NOT inject created_by/updated_by — FhirClient does that
automatically from actor.sub on every POST and PATCH.

There is no get_me()/myOrganizations equivalent here, unlike Patient/
Practitioner — fhir-server's Organization has no user_id at all (it's a
shared tenant-level entity, not scoped to an individual end-user), so there's
no way to scope a listing to "my own" organizations beyond the plain,
already-org-scoped list().
"""

from fastapi import HTTPException, status

from app.auth.models import AuthUser
from app.connectors.internal.clients.organization import OrganizationClient
from app.connectors.internal.schemas.organization.input import (
    ListOrganizationsSchema,
    OrganizationCreateSchema,
    OrganizationPatchSchema,
)
from app.core.logging import trace_methods


@trace_methods
class OrganizationsService:
    """
    Application service for Organization CRUD use cases.

    Instantiated per-request by the DI container (OrganizationContainer) via
    Factory provider, so it holds no shared state between requests.
    """

    def __init__(self, client: OrganizationClient) -> None:
        """
        Args:
            client: The OrganizationClient injected by the DI container.
                    Provides fhir-server access for all Organization operations.
        """
        self._client = client

    async def create(
        self, dto: OrganizationCreateSchema, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Create a new Organization resource on the fhir-server.

        fhir-server validates `partof` (existence, tenant match, and the
        circular-hierarchy business rule) server-side and returns 404/422 —
        this method does not re-implement any of that.

        Args:
            dto:    Validated create input from the resolver/router.
            actor:  Authenticated caller — used by FhirClient for created_by
                    and forwarded as the Authorization header.
            accept: Content-type preference forwarded to the fhir-server.

        Returns:
            The newly created Organization resource dict (plain JSON or FHIR R4).
        """
        payload = dto.model_dump(exclude_none=True, mode="json")
        return await self._client.create(payload, actor, accept=accept)

    async def get_by_id(
        self, organization_id: int, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Fetch a single Organization by its integer ID.

        fhir-server scopes this to the caller's own org via the verified JWT
        (get_organization_scoped()) and 404s a cross-org access itself — no
        client-side ownership check needed here.

        Args:
            organization_id: The integer primary key of the Organization.
            actor:           Authenticated caller — forwarded as the Authorization header.
            accept:          Content-type preference forwarded to the fhir-server.

        Returns:
            The Organization resource dict in the requested format.
        """
        return await self._client.get_by_id(organization_id, actor, accept=accept)

    async def list(
        self, filters: ListOrganizationsSchema, actor: AuthUser, accept: str | None = None
    ) -> dict:
        """
        Return a paginated, filtered list of Organization resources.

        org_id is never forwarded as a filter — fhir-server always scopes
        Organization reads to the caller's own org via the verified JWT.

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
            name=filters.name,
            identifier=filters.identifier,
            **{"type": filters.org_type},
            address=filters.address,
            **{
                "address-city": filters.address_city,
                "address-state": filters.address_state,
                "address-postalcode": filters.address_postal_code,
                "address-country": filters.address_country,
                "address-use": filters.address_use,
            },
            partof=filters.partof,
            endpoint=filters.endpoint,
            sort=filters.sort,
            total_mode=filters.total_mode,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def update(
        self,
        organization_id: int,
        dto: OrganizationPatchSchema,
        actor: AuthUser,
        accept: str | None = None,
    ) -> dict:
        """
        Partially update an Organization resource.

        fhir-server scopes this to the caller's own org (404 on mismatch)
        and validates `partof` (existence, tenant match, circular-hierarchy
        check) server-side.

        Args:
            organization_id: The integer primary key of the Organization to update.
            dto:             Validated partial payload; all fields Optional.
            actor:           Authenticated user — used by FhirClient for updated_by
                             and forwarded as the Authorization header.
            accept:          Content-type preference forwarded to the fhir-server.

        Returns:
            The updated Organization resource dict in the requested format.

        Raises:
            HTTPException(422): If the request body contained no updateable fields.
        """
        payload = dto.model_dump(exclude_none=True, mode="json")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one field must be provided for update.",
            )
        return await self._client.patch(organization_id, payload, actor, accept=accept)

    async def delete(self, organization_id: int, actor: AuthUser) -> None:
        """
        Delete an Organization resource.

        fhir-server scopes this to the caller's own org (404 on mismatch)
        server-side — no client-side ownership check needed here.

        Args:
            organization_id: The integer primary key of the Organization to delete.
            actor:           Authenticated user — forwarded as the Authorization header.
        """
        await self._client.delete(organization_id, actor)
