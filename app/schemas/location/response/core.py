"""
Top-level Location response models, mirroring
app/schemas/location/response/core.py's `Plain*` models in the fhir-server
repo field-for-field, dropping the `Plain` prefix — same convention as
app/schemas/organization/response/core.py (this gateway has no separate
FHIR-camelCase GraphQL shape; that's a REST-only content-negotiation
concept — see app/schemas/location/fhir_schemas.py for the REST-only
OpenAPI-documentation models).

`extra="allow"` is set on all models so new fields added to the fhir-server
response are passed through transparently without requiring a schema update
here first — but note GraphQL can only *query* fields explicitly declared
below (strawberry's `all_fields=True` maps declared Pydantic fields to
GraphQL fields), so a genuinely new field still needs adding here to become
queryable.
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from .alias import LocationAliasResponse
from .endpoint import LocationEndpointResponse
from .hours_of_operation import LocationHoursOfOperationResponse
from .identifier import LocationIdentifierResponse
from .telecom import LocationTelecomResponse
from .type import LocationTypeResponse


class LocationResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int = Field(..., description="Public location_id.")
    status: str | None = Field(
        None,
        description="The status of the location as normally viewed by a user — active|suspended|inactive.",
    )
    operational_status_system: str | None = Field(
        None, description="Operational status — the code system for the code."
    )
    operational_status_version: str | None = Field(
        None, description="Operational status — the version of the code system."
    )
    operational_status_code: str | None = Field(
        None, description="Operational status — a symbol defined by the code system."
    )
    operational_status_display: str | None = Field(
        None, description="Operational status — the meaning of the code in the system."
    )
    operational_status_user_selected: bool | None = Field(
        None, description="Operational status — whether the coding was user-selected."
    )
    name: str | None = Field(
        None, description="Name of the location as used by humans."
    )
    description: str | None = Field(
        None, description="Description of the Location."
    )
    mode: str | None = Field(
        None,
        description="Whether this record describes a specific instance of a location, or a class of locations — instance|kind.",
    )

    address_use: str | None = Field(None, description="The purpose of this address.")
    address_type: str | None = Field(None, description="postal|physical|both.")
    address_text: str | None = Field(
        None, description="A full text representation of the address."
    )
    address_line: list[str] | None = Field(
        None,
        description="Street name, number, direction, PO Box etc. Split back out from the comma-separated column by the mapper.",
    )
    address_city: str | None = Field(None, description="City, town or village.")
    address_district: str | None = Field(
        None, description="The name of the administrative area (county)."
    )
    address_state: str | None = Field(None, description="Sub-unit of a country.")
    address_postal_code: str | None = Field(None, description="Postal code.")
    address_country: str | None = Field(None, description="Country.")
    address_period_start: str | None = Field(
        None, description="Start of the time period when this address was/is in use."
    )
    address_period_end: str | None = Field(
        None, description="End of the time period when this address was/is in use."
    )

    physical_type_system: str | None = Field(
        None, description="Physical form — the code system for the code."
    )
    physical_type_version: str | None = Field(
        None, description="Physical form — the version of the code system."
    )
    physical_type_code: str | None = Field(
        None, description="Physical form — a symbol defined by the code system."
    )
    physical_type_display: str | None = Field(
        None, description="Physical form — the meaning of the code in the system."
    )
    physical_type_text: str | None = Field(
        None, description="Physical form — a human language representation."
    )
    physical_type_user_selected: bool | None = Field(
        None, description="Physical form — whether the coding was user-selected."
    )

    position_longitude: Decimal | None = Field(
        None, description="Longitude with WGS84 datum."
    )
    position_latitude: Decimal | None = Field(
        None, description="Latitude with WGS84 datum."
    )
    position_altitude: Decimal | None = Field(
        None, description="Altitude with WGS84 datum."
    )

    managing_organization: str | None = Field(
        None,
        description="Resolved FHIR reference to the managing organization, e.g. 'Organization/190001'.",
    )
    managing_organization_type: str | None = Field(
        None, description="Resolved reference target type (always 'Organization')."
    )
    managing_organization_id: int | None = Field(
        None, description="Public ID of the resolved managing Organization, if any."
    )
    managing_organization_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the managing organization.",
    )
    managing_organization_identifier_use: str | None = Field(
        None, description="Fallback identifier — its purpose, if known."
    )
    managing_organization_identifier_type_system: str | None = Field(
        None, description="Fallback identifier — code system for its type."
    )
    managing_organization_identifier_type_version: str | None = Field(
        None, description="Fallback identifier — version of the type code system."
    )
    managing_organization_identifier_type_code: str | None = Field(
        None, description="Fallback identifier — code for its type."
    )
    managing_organization_identifier_type_display: str | None = Field(
        None, description="Fallback identifier — display for its type."
    )
    managing_organization_identifier_type_text: str | None = Field(
        None, description="Fallback identifier — human language rendering of its type."
    )
    managing_organization_identifier_type_user_selected: bool | None = Field(
        None, description="Fallback identifier — whether its type was user-selected."
    )
    managing_organization_identifier_system: str | None = Field(
        None, description="Fallback identifier — namespace URL for the value."
    )
    managing_organization_identifier_value: str | None = Field(
        None, description="Fallback identifier — value within the given system."
    )
    managing_organization_identifier_period_start: str | None = Field(
        None, description="Fallback identifier — start of validity period."
    )
    managing_organization_identifier_period_end: str | None = Field(
        None, description="Fallback identifier — end of validity period."
    )

    part_of: str | None = Field(
        None,
        description="Resolved FHIR reference to the containing location, e.g. 'Location/230001'.",
    )
    part_of_type: str | None = Field(
        None, description="Resolved reference target type (always 'Location')."
    )
    part_of_id: int | None = Field(
        None, description="Public ID of the resolved containing Location, if any."
    )
    part_of_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the containing location.",
    )
    part_of_identifier_use: str | None = Field(
        None, description="Fallback identifier — its purpose, if known."
    )
    part_of_identifier_type_system: str | None = Field(
        None, description="Fallback identifier — code system for its type."
    )
    part_of_identifier_type_version: str | None = Field(
        None, description="Fallback identifier — version of the type code system."
    )
    part_of_identifier_type_code: str | None = Field(
        None, description="Fallback identifier — code for its type."
    )
    part_of_identifier_type_display: str | None = Field(
        None, description="Fallback identifier — display for its type."
    )
    part_of_identifier_type_text: str | None = Field(
        None, description="Fallback identifier — human language rendering of its type."
    )
    part_of_identifier_type_user_selected: bool | None = Field(
        None, description="Fallback identifier — whether its type was user-selected."
    )
    part_of_identifier_system: str | None = Field(
        None, description="Fallback identifier — namespace URL for the value."
    )
    part_of_identifier_value: str | None = Field(
        None, description="Fallback identifier — value within the given system."
    )
    part_of_identifier_period_start: str | None = Field(
        None, description="Fallback identifier — start of validity period."
    )
    part_of_identifier_period_end: str | None = Field(
        None, description="Fallback identifier — end of validity period."
    )

    availability_exceptions: str | None = Field(
        None,
        description="A description of when the locations opening ours are different to normal.",
    )

    identifier: list[LocationIdentifierResponse] | None = Field(
        None, description="Unique code or number identifying the location to its users."
    )
    type: list[LocationTypeResponse] | None = Field(
        None, description="Indicates the type of function performed at the location."
    )
    alias: list[LocationAliasResponse] | None = Field(
        None,
        description="A list of alternate names that the location is known as, or was known as, in the past.",
    )
    telecom: list[LocationTelecomResponse] | None = Field(
        None,
        description="The contact details of communication devices available at the location.",
    )
    hours_of_operation: list[LocationHoursOfOperationResponse] | None = Field(
        None, description="What days/times during a week is this location usually open."
    )
    endpoint: list[LocationEndpointResponse] | None = Field(
        None,
        description="Technical endpoints providing access to services operated for the location.",
    )

    org_id: str | None = Field(
        None,
        description="ID of the tenant/account this record is scoped to (multi-tenancy), taken from the verified JWT's activeOrganizationId — not a FHIR concept, and unrelated to managing_organization.",
    )
    created_at: str | None = Field(None, description="When this row was created.")
    updated_at: str | None = Field(None, description="When this row was last updated.")
    created_by: str | None = Field(
        None,
        description="Acting user who created this record, taken from the verified JWT's sub.",
    )
    updated_by: str | None = Field(
        None,
        description="Acting user who last updated this record, taken from the verified JWT's sub.",
    )


class PaginatedLocationResponse(BaseModel):
    total: int | None = Field(
        None, description="Total matching rows (null when total_mode=none)."
    )
    limit: int = Field(..., description="Page size used for this response.")
    offset: int = Field(..., description="Number of rows skipped before this page.")
    data: list[LocationResponse]
