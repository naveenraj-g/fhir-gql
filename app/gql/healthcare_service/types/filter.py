"""
GraphQL filter input for the `healthcareServices` list query.

Bundles every HealthcareService search parameter (matching fhir-server's
Medplum-mirrored HealthcareService search parameter set — see
app/routers/healthcare_service/core.py's list_healthcare_services()) into a
single input object, GraphQL's idiomatic convention for list-query filters —
same pattern as app/gql/organization/types/filter.py's
OrganizationFilterInput and app/gql/location/types/filter.py's
LocationFilterInput.

Hand-written as a plain `@strawberry.input` (not derived from
ListHealthcareServicesSchema via `strawberry.experimental.pydantic.input`)
because ListHealthcareServicesSchema also carries `sort`/`total_mode`/
`limit`/`offset` — pagination/ordering concerns, not filters — which stay as
separate top-level arguments on the `healthcareServices` query in
queries.py (using the shared app.gql.common.pagination aliases) rather than
living inside this input.

Every field carries its own `description=` — same documentation bar as
fhir-server's per-parameter `Query()` descriptions.
"""

import strawberry


@strawberry.input(description="Filter arguments for the `healthcareServices` query.")
class HealthcareServiceFilterInput:
    name: str | None = strawberry.field(
        default=None, description="Partial match against the service name."
    )
    active: bool | None = strawberry.field(
        default=None, description="Filter by active status."
    )
    identifier: str | None = strawberry.field(
        default=None, description="Exact match on a business identifier value."
    )
    category: str | None = strawberry.field(
        default=None, description="Exact match on a coded service category."
    )
    service_type: str | None = strawberry.field(
        default=None, description="Exact match on a coded service type."
    )
    specialty: str | None = strawberry.field(
        default=None, description="Exact match on a coded specialty."
    )
    characteristic: str | None = strawberry.field(
        default=None, description="Exact match on a coded service characteristic."
    )
    program: str | None = strawberry.field(
        default=None,
        description="Exact match on a coded program supported by this service.",
    )
    provided_by: str | None = strawberry.field(
        default=None,
        description="FHIR reference string to the providing Organization, e.g. 'Organization/190001'.",
    )
    location: str | None = strawberry.field(
        default=None, description="FHIR reference string, e.g. 'Location/230001'."
    )
    coverage_area: str | None = strawberry.field(
        default=None, description="FHIR reference string, e.g. 'Location/230001'."
    )
    endpoint: str | None = strawberry.field(
        default=None, description="FHIR reference string, e.g. 'Endpoint/1'."
    )


__all__ = ["HealthcareServiceFilterInput"]
