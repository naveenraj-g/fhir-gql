"""
Top-level HealthcareService response models, mirroring
app/schemas/healthcare_service/response/core.py's `Plain*` models in the
fhir-server repo field-for-field, dropping the `Plain` prefix — same
convention as app/schemas/organization/response/core.py and
app/schemas/location/response/core.py (this gateway has no separate
FHIR-camelCase GraphQL shape; that's a REST-only content-negotiation
concept — see app/schemas/healthcare_service/fhir_schemas.py for the
REST-only OpenAPI-documentation models).

`extra="allow"` is set on all models so new fields added to the fhir-server
response are passed through transparently without requiring a schema update
here first — but note GraphQL can only *query* fields explicitly declared
below (strawberry's `all_fields=True` maps declared Pydantic fields to
GraphQL fields), so a genuinely new field still needs adding here to become
queryable.
"""

from pydantic import BaseModel, ConfigDict, Field

from .available_time import HealthcareServiceAvailableTimeResponse
from .category import HealthcareServiceCategoryResponse
from .characteristic import HealthcareServiceCharacteristicResponse
from .communication import HealthcareServiceCommunicationResponse
from .coverage_area import HealthcareServiceCoverageAreaResponse
from .eligibility import HealthcareServiceEligibilityResponse
from .endpoint import HealthcareServiceEndpointResponse
from .identifier import HealthcareServiceIdentifierResponse
from .location import HealthcareServiceLocationResponse
from .not_available import HealthcareServiceNotAvailableResponse
from .program import HealthcareServiceProgramResponse
from .referral_method import HealthcareServiceReferralMethodResponse
from .service_provision_code import HealthcareServiceServiceProvisionCodeResponse
from .specialty import HealthcareServiceSpecialtyResponse
from .telecom import HealthcareServiceTelecomResponse
from .type import HealthcareServiceTypeResponse


class HealthcareServiceResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int = Field(..., description="Public healthcare_service_id.")
    active: bool | None = Field(
        None, description="Whether this healthcare service record is in active use."
    )
    name: str | None = Field(
        None,
        description="Further description of the service as presented to a consumer while searching.",
    )
    provided_by: str | None = Field(
        None,
        description="Resolved FHIR reference to the providing organization, e.g. 'Organization/190001'.",
    )
    provided_by_type: str | None = Field(
        None, description="Resolved reference target type (always 'Organization')."
    )
    provided_by_id: int | None = Field(
        None, description="Public organization_id of the resolved Organization, if any."
    )
    provided_by_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the providing organization.",
    )
    provided_by_identifier_use: str | None = Field(
        None, description="Fallback identifier — its purpose, if known."
    )
    provided_by_identifier_type_system: str | None = Field(
        None, description="Fallback identifier — code system for its type."
    )
    provided_by_identifier_type_version: str | None = Field(
        None, description="Fallback identifier — version of the type code system."
    )
    provided_by_identifier_type_code: str | None = Field(
        None, description="Fallback identifier — code for its type."
    )
    provided_by_identifier_type_display: str | None = Field(
        None, description="Fallback identifier — display for its type."
    )
    provided_by_identifier_type_text: str | None = Field(
        None, description="Fallback identifier — human language rendering of its type."
    )
    provided_by_identifier_type_user_selected: bool | None = Field(
        None, description="Fallback identifier — whether its type was user-selected."
    )
    provided_by_identifier_system: str | None = Field(
        None, description="Fallback identifier — namespace URL for the value."
    )
    provided_by_identifier_value: str | None = Field(
        None, description="Fallback identifier — value within the given system."
    )
    provided_by_identifier_period_start: str | None = Field(
        None, description="Fallback identifier — start of validity period."
    )
    provided_by_identifier_period_end: str | None = Field(
        None, description="Fallback identifier — end of validity period."
    )
    comment: str | None = Field(
        None, description="Any additional description of the service."
    )
    extra_details: str | None = Field(
        None, description="Extra details about the service (markdown)."
    )
    photo_content_type: str | None = Field(
        None, description="MIME type of the photo (e.g. image/png)."
    )
    photo_language: str | None = Field(
        None, description="Human language of the photo content."
    )
    photo_data: str | None = Field(
        None, description="The actual photo data, base64-encoded."
    )
    photo_url: str | None = Field(
        None, description="A URL where the photo can be retrieved instead of inline."
    )
    photo_size: int | None = Field(
        None,
        description="Number of bytes of content, measured after decoding, if applicable.",
    )
    photo_hash: str | None = Field(
        None, description="Base64-encoded hash (SHA-1) of the photo data."
    )
    photo_title: str | None = Field(
        None, description="Label to display in place of the photo content."
    )
    photo_creation: str | None = Field(
        None, description="ISO 8601 datetime the photo was first created."
    )
    appointment_required: bool | None = Field(
        None, description="Whether a prospective consumer will require an appointment."
    )
    availability_exceptions: str | None = Field(
        None, description="A description of site availability exceptions."
    )
    identifier: list[HealthcareServiceIdentifierResponse] | None = Field(
        None, description="External identifiers for this item."
    )
    category: list[HealthcareServiceCategoryResponse] | None = Field(
        None, description="Broad category of service."
    )
    type: list[HealthcareServiceTypeResponse] | None = Field(
        None, description="Specific type(s) of service."
    )
    specialty: list[HealthcareServiceSpecialtyResponse] | None = Field(
        None, description="Specialties handled by the service site."
    )
    location: list[HealthcareServiceLocationResponse] | None = Field(
        None, description="Location(s) where this service may be provided."
    )
    telecom: list[HealthcareServiceTelecomResponse] | None = Field(
        None, description="Contact details for the healthcare service."
    )
    coverage_area: list[HealthcareServiceCoverageAreaResponse] | None = Field(
        None, description="Location(s) this service is available to."
    )
    service_provision_code: (
        list[HealthcareServiceServiceProvisionCodeResponse] | None
    ) = Field(None, description="Conditions under which the service is available.")
    eligibility: list[HealthcareServiceEligibilityResponse] | None = Field(
        None, description="Specific eligibility requirements."
    )
    program: list[HealthcareServiceProgramResponse] | None = Field(
        None, description="Applicable program(s)."
    )
    characteristic: list[HealthcareServiceCharacteristicResponse] | None = Field(
        None, description="Characteristic(s) of the service."
    )
    communication: list[HealthcareServiceCommunicationResponse] | None = Field(
        None, description="Communication language(s)."
    )
    referral_method: list[HealthcareServiceReferralMethodResponse] | None = Field(
        None, description="Referral method(s)."
    )
    available_time: list[HealthcareServiceAvailableTimeResponse] | None = Field(
        None, description="Available time window(s)."
    )
    not_available: list[HealthcareServiceNotAvailableResponse] | None = Field(
        None, description="Not-available period(s)."
    )
    endpoint: list[HealthcareServiceEndpointResponse] | None = Field(
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


class PaginatedHealthcareServiceResponse(BaseModel):
    total: int | None = Field(
        None, description="Total matching rows (null when total_mode=none)."
    )
    limit: int = Field(..., description="Page size used for this response.")
    offset: int = Field(..., description="Number of rows skipped before this page.")
    data: list[HealthcareServiceResponse]
