"""
GraphQL filter input for the `practitionerRoles` list query.

Bundles every PractitionerRole search parameter (matching fhir-server's
Medplum-mirrored PractitionerRole search parameter set — see
app/routers/practitioner_role/core.py's list_practitioner_roles()) into a
single input object, GraphQL's idiomatic convention for list-query filters —
same pattern as app/gql/organization/types/filter.py /
app/gql/location/types/filter.py / app/gql/healthcare_service/types/filter.py.

Hand-written as a plain `@strawberry.input` (not derived from
ListPractitionerRolesSchema via `strawberry.experimental.pydantic.input`)
because ListPractitionerRolesSchema also carries `sort`/`total_mode`/
`limit`/`offset` — pagination/ordering concerns, not filters — which stay
as separate top-level arguments on the `practitionerRoles` query in
queries.py rather than living inside this input.

Every field carries its own `description=` — same documentation bar as
fhir-server's per-parameter `Query()` descriptions.
"""

from datetime import date as date_

import strawberry

# Registers PractitionerRole-relevant enums as GraphQL enums (side-effect
# import) — required before referencing them below, though this input has
# no enum-typed fields today (all filters are plain strings/bool/date).
import app.gql.enums  # noqa: F401


@strawberry.input(description="Filter arguments for the `practitionerRoles` query.")
class PractitionerRoleFilterInput:
    active: bool | None = strawberry.field(
        default=None, description="Filter by active status."
    )
    date: date_ | None = strawberry.field(
        default=None,
        description="ISO date — matches rows whose period contains it (period.start <= date <= period.end).",
    )
    email: str | None = strawberry.field(
        default=None,
        description="Exact match against a telecom entry with system='email'.",
    )
    phone: str | None = strawberry.field(
        default=None,
        description="Exact match against a telecom entry with system='phone'.",
    )
    telecom: str | None = strawberry.field(
        default=None,
        description="Exact match against any telecom value, regardless of system.",
    )
    identifier: str | None = strawberry.field(
        default=None, description="Exact match on a business identifier value."
    )
    role: str | None = strawberry.field(
        default=None, description="Exact match on a coded role (code[])."
    )
    specialty: str | None = strawberry.field(
        default=None, description="Exact match on a coded specialty."
    )
    practitioner: str | None = strawberry.field(
        default=None,
        description="FHIR reference string to the practitioner, e.g. 'Practitioner/30001'.",
    )
    organization: str | None = strawberry.field(
        default=None,
        description="FHIR reference string to the organization, e.g. 'Organization/190001'.",
    )
    location: str | None = strawberry.field(
        default=None, description="FHIR reference string, e.g. 'Location/230001'."
    )
    service: str | None = strawberry.field(
        default=None,
        description="FHIR reference string, e.g. 'HealthcareService/150001'.",
    )
    endpoint: str | None = strawberry.field(
        default=None, description="FHIR reference string, e.g. 'Endpoint/1'."
    )


__all__ = ["PractitionerRoleFilterInput"]
