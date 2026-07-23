"""
Shared tenant-scoped reference helpers reused across resource Services.

`check_tenant_ownership` was originally written private to
OrganizationsService (`_check_ownership`). Lifted out here once Location
needed the identical fetch-then-compare pattern on its own by-id routes.

`validate_reference` was added once a third pattern repeated across
Organization (`partof`), Location (`part_of`, `managing_organization`), and
HealthcareService (`provided_by`, `location[]`, `coverage_area[]`): parse a
FHIR reference string, fetch the referenced resource, and check tenant
ownership. See dev-docs/13-workflow-orchestration.md's guidance to lift a
same-resource rule into a shared helper at the point of its second
duplication, not before — by HealthcareService this pattern was well past
that point.
"""

from typing import Awaitable, Callable

from fastapi import HTTPException, status

from app.auth.models import AuthUser


def check_tenant_ownership(
    resource: dict, actor: AuthUser, *, not_found_detail: str = "Resource not found."
) -> None:
    """
    Raise 404 if `resource`'s org_id doesn't match the caller's org_id.

    Skipped when actor.org_id is None — per AuthUser's docstring, a None
    org_id means an org-less/super-admin token, which is intentionally not
    scoped to a single tenant. Returns 404 (not 403) so a caller can't
    distinguish "belongs to another org" from "doesn't exist" by
    guessing/incrementing an id.

    Args:
        resource:         The plain-JSON resource dict fetched from the fhir-server.
        actor:            The authenticated caller.
        not_found_detail: Message to raise — callers pass a resource-specific
                           phrase (e.g. "Location not found.", "Managing
                           organization not found.") so the error is legible
                           regardless of which resource type is being checked.

    Raises:
        HTTPException(404): If the resource belongs to a different org.
    """
    if actor.org_id is not None and resource.get("org_id") != actor.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=not_found_detail,
        )


async def validate_reference(
    ref: str,
    *,
    resource_type: str,
    get_by_id: Callable[[int], Awaitable[dict]],
    actor: AuthUser,
    field_name: str,
) -> dict:
    """
    Parse `ref` as `"<resource_type>/<id>"`, fetch it, and verify tenant ownership.

    Callers pass the target resource's own `get_by_id` (e.g.
    `self._org_client.get_by_id`) so this helper stays resource-agnostic —
    it never imports any specific `*Client` itself.

    Args:
        ref:           Raw FHIR reference string, e.g. "Organization/190001".
        resource_type: Expected reference prefix, e.g. "Organization", "Location".
        get_by_id:     Async callable resolving the referenced resource's
                       integer id to its plain-JSON dict.
        actor:         Authenticated caller — the referenced resource's org_id must match.
        field_name:    Name of the field being validated, used in the 422 message.

    Returns:
        The fetched resource dict — some callers need to inspect it further
        (e.g. Location's `part_of` cycle check reads `part_of_id` off it).

    Raises:
        HTTPException(422): If `ref` is not a well-formed "<resource_type>/<id>" reference.
        HTTPException(404): If the referenced resource doesn't exist, or belongs to a different tenant.
    """
    prefix = f"{resource_type}/"
    id_str = ref[len(prefix):] if ref.startswith(prefix) else ""
    if not id_str.isdigit():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} must be a reference in the form '{prefix}<id>', got '{ref}'.",
        )
    resource = await get_by_id(int(id_str))
    check_tenant_ownership(resource, actor, not_found_detail=f"{resource_type} not found.")
    return resource
