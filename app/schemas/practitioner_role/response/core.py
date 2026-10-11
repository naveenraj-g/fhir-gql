"""
Top-level PractitionerRole response models, mirroring
app/schemas/practitioner_role/response/core.py's `Plain*` models in the
fhir-server repo field-for-field, dropping the `Plain` prefix — same
convention as app/schemas/organization/response/core.py (this gateway has
no separate FHIR-camelCase GraphQL shape; that's a REST-only content-
negotiation concept — see app/schemas/practitioner_role/fhir_schemas.py for
the REST-only OpenAPI-documentation models).

`extra="allow"` is set on all models so new fields added to the fhir-server
response are passed through transparently without requiring a schema update
here first — but note GraphQL can only *query* fields explicitly declared
below (strawberry's `all_fields=True` maps declared Pydantic fields to
GraphQL fields), so a genuinely new field still needs adding here to become
queryable.

Booking-specific response models (PractitionerRoleBookingResponse and its
supporting types) live in response/booking.py — they have no fhir-server
counterpart at all (no `/practitioner-roles/booking` route exists on the
current fhir-server) and are out of scope for this port; kept as-is.
"""

from pydantic import BaseModel, ConfigDict, Field

from .available_time import PractitionerRoleAvailableTimeResponse
from .code import PractitionerRoleCodeResponse
from .endpoint import PractitionerRoleEndpointResponse
from .healthcare_service import PractitionerRoleHealthcareServiceResponse
from .identifier import PractitionerRoleIdentifierResponse
from .location import PractitionerRoleLocationResponse
from .not_available import PractitionerRoleNotAvailableResponse
from .specialty import PractitionerRoleSpecialtyResponse
from .telecom import PractitionerRoleTelecomResponse


class PractitionerRoleResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int = Field(..., description="Public practitioner_role_id.")
    active: bool | None = Field(
        None, description="Whether this practitioner role record is in active use."
    )
    period_start: str | None = Field(
        None,
        description="Start of the period during which the practitioner is authorized to perform in these role(s).",
    )
    period_end: str | None = Field(
        None,
        description="End of the period during which the practitioner is authorized to perform in these role(s).",
    )
    practitioner: str | None = Field(
        None,
        description="Resolved FHIR reference to the practitioner, e.g. 'Practitioner/30001'.",
    )
    practitioner_type: str | None = Field(
        None, description="Resolved reference target type (always 'Practitioner')."
    )
    practitioner_id: int | None = Field(
        None, description="Public practitioner_id of the resolved Practitioner, if any."
    )
    practitioner_display: str | None = Field(
        None, description="Plain text narrative that identifies the practitioner."
    )
    practitioner_identifier_use: str | None = Field(
        None, description="Fallback identifier — its purpose, if known."
    )
    practitioner_identifier_type_system: str | None = Field(
        None, description="Fallback identifier — code system for its type."
    )
    practitioner_identifier_type_version: str | None = Field(
        None, description="Fallback identifier — version of the type code system."
    )
    practitioner_identifier_type_code: str | None = Field(
        None, description="Fallback identifier — code for its type."
    )
    practitioner_identifier_type_display: str | None = Field(
        None, description="Fallback identifier — display for its type."
    )
    practitioner_identifier_type_text: str | None = Field(
        None, description="Fallback identifier — human language rendering of its type."
    )
    practitioner_identifier_type_user_selected: bool | None = Field(
        None, description="Fallback identifier — whether its type was user-selected."
    )
    practitioner_identifier_system: str | None = Field(
        None, description="Fallback identifier — namespace URL for the value."
    )
    practitioner_identifier_value: str | None = Field(
        None, description="Fallback identifier — value within the given system."
    )
    practitioner_identifier_period_start: str | None = Field(
        None, description="Fallback identifier — start of validity period."
    )
    practitioner_identifier_period_end: str | None = Field(
        None, description="Fallback identifier — end of validity period."
    )
    organization: str | None = Field(
        None,
        description="Resolved FHIR reference to the organization, e.g. 'Organization/190001'.",
    )
    organization_type: str | None = Field(
        None, description="Resolved reference target type (always 'Organization')."
    )
    organization_id: int | None = Field(
        None, description="Public organization_id of the resolved Organization, if any."
    )
    organization_display: str | None = Field(
        None, description="Plain text narrative that identifies the organization."
    )
    organization_identifier_use: str | None = Field(
        None, description="Fallback identifier — its purpose, if known."
    )
    organization_identifier_type_system: str | None = Field(
        None, description="Fallback identifier — code system for its type."
    )
    organization_identifier_type_version: str | None = Field(
        None, description="Fallback identifier — version of the type code system."
    )
    organization_identifier_type_code: str | None = Field(
        None, description="Fallback identifier — code for its type."
    )
    organization_identifier_type_display: str | None = Field(
        None, description="Fallback identifier — display for its type."
    )
    organization_identifier_type_text: str | None = Field(
        None, description="Fallback identifier — human language rendering of its type."
    )
    organization_identifier_type_user_selected: bool | None = Field(
        None, description="Fallback identifier — whether its type was user-selected."
    )
    organization_identifier_system: str | None = Field(
        None, description="Fallback identifier — namespace URL for the value."
    )
    organization_identifier_value: str | None = Field(
        None, description="Fallback identifier — value within the given system."
    )
    organization_identifier_period_start: str | None = Field(
        None, description="Fallback identifier — start of validity period."
    )
    organization_identifier_period_end: str | None = Field(
        None, description="Fallback identifier — end of validity period."
    )
    availability_exceptions: str | None = Field(
        None, description="A description of site availability exceptions."
    )
    identifier: list[PractitionerRoleIdentifierResponse] | None = Field(
        None, description="Business identifiers that are specific to a role/location."
    )
    code: list[PractitionerRoleCodeResponse] | None = Field(
        None, description="Roles which this practitioner may perform."
    )
    specialty: list[PractitionerRoleSpecialtyResponse] | None = Field(
        None, description="Specific expertise of the practitioner."
    )
    location: list[PractitionerRoleLocationResponse] | None = Field(
        None, description="Location(s) at which this practitioner provides care."
    )
    healthcare_service: list[PractitionerRoleHealthcareServiceResponse] | None = Field(
        None, description="Healthcare service(s) provided at this role/location."
    )
    telecom: list[PractitionerRoleTelecomResponse] | None = Field(
        None, description="Contact detail(s) specific to the role/location/service."
    )
    available_time: list[PractitionerRoleAvailableTimeResponse] | None = Field(
        None, description="Available time window(s)."
    )
    not_available: list[PractitionerRoleNotAvailableResponse] | None = Field(
        None, description="Not-available period(s)."
    )
    endpoint: list[PractitionerRoleEndpointResponse] | None = Field(
        None, description="Technical endpoint(s)."
    )
    org_id: str | None = Field(
        None,
        description="Gateway-forwarded ID of the tenant/account this record is scoped to (multi-tenancy) — not a FHIR concept.",
    )
    created_at: str | None = Field(None, description="When this row was created.")
    updated_at: str | None = Field(None, description="When this row was last updated.")
    created_by: str | None = Field(
        None,
        description="Acting user who created this record, forwarded by the gateway.",
    )
    updated_by: str | None = Field(
        None,
        description="Acting user who last updated this record, forwarded by the gateway.",
    )


class PaginatedPractitionerRoleResponse(BaseModel):
    total: int | None = Field(
        None, description="Total matching rows (null when total_mode=none)."
    )
    limit: int = Field(..., description="Page size used for this response.")
    offset: int = Field(..., description="Number of rows skipped before this page.")
    data: list[PractitionerRoleResponse]
