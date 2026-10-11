"""
Create/Patch/List schemas for the HealthcareService resource, mirroring
app/schemas/healthcare_service/input/core.py in the fhir-server repo
field-for-field (same class names, same fields, same required/optional
split) — kept in sync manually, same convention as
app/schemas/organization/input/core.py and app/schemas/location/input/core.py.

org_id/created_by/updated_by are NOT exposed: fhir-server derives org_id from
the verified JWT's `activeOrganizationId` claim and created_by/updated_by from
its `sub` claim (JWT/RBAC rollout) — a client-supplied value for any of the
three would be rejected outright (extra="forbid", no such field declared).
Like Organization and Location, HealthcareService has no user_id field at
all — it's a shared tenant-level entity (a service the org offers), not
scoped to an individual end-user.

Unlike this gateway's pre-rollout assumption (HealthcareServicePatchSchema
used to expose only scalar/photo fields), fhir-server's current
HealthcareServicePatchSchema supports every field/sub-resource list
Create does, including `provided_by` (with its identifier fallback) —
matching Location's fully-patchable shape, not Organization's create-only
`partof`.

ListHealthcareServicesSchema is this gateway's own query-parameter schema
(fhir-server has no GraphQL/query-args concept, so it has no file-level
counterpart to mirror) — mirroring fhir-server's current Medplum-style
HealthcareService search parameter set (see
app/routers/healthcare_service/core.py's list_healthcare_services() on
fhir-server).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import IdentifierUse

from .available_time import HealthcareServiceAvailableTimeInput
from .category import HealthcareServiceCategoryInput
from .characteristic import HealthcareServiceCharacteristicInput
from .communication import HealthcareServiceCommunicationInput
from .coverage_area import HealthcareServiceCoverageAreaInput
from .eligibility import HealthcareServiceEligibilityInput
from .endpoint import HealthcareServiceEndpointInput
from .identifier import HealthcareServiceIdentifierInput
from .location import HealthcareServiceLocationInput
from .not_available import HealthcareServiceNotAvailableInput
from .program import HealthcareServiceProgramInput
from .referral_method import HealthcareServiceReferralMethodInput
from .service_provision_code import HealthcareServiceServiceProvisionCodeInput
from .specialty import HealthcareServiceSpecialtyInput
from .telecom import HealthcareServiceTelecomInput
from .type import HealthcareServiceTypeInput


class HealthcareServiceCreateSchema(BaseModel):
    """Creates a HealthcareService and any combination of its 16 sub-resource
    lists atomically in one request — same set-once-then-patch shape as
    Organization, no separate scalar-only vs. full create split. org_id and
    created_by both come from the verified JWT (actor.org_id / actor.sub) —
    neither is a request body field. Like Organization and Location,
    HealthcareService has no user_id field at all — it's a shared
    tenant-level entity (a service the org offers), not scoped to an
    individual end-user."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "active": True,
                "name": "General Practice Consultation",
                "provided_by": "Organization/190001",
                "provided_by_display": "General Hospital",
                "comment": "Walk-in and appointment-based GP service",
                "extra_details": "Extended hours on Tuesdays until 20:00.",
                "appointment_required": False,
                "availability_exceptions": "Closed public holidays",
                "category": [
                    {
                        "coding_system": "http://example.org/service-category",
                        "coding_code": "17",
                        "coding_display": "General Practice",
                    }
                ],
                "type": [{"coding_code": "57", "coding_display": "Immunization"}],
                "specialty": [
                    {
                        "coding_system": "http://snomed.info/sct",
                        "coding_code": "394814009",
                        "coding_display": "General practice",
                    }
                ],
                "location": [],
                "telecom": [{"system": "phone", "value": "555-1234", "use": "work"}],
                "coverage_area": [],
                "service_provision_code": [],
                "eligibility": [],
                "program": [],
                "characteristic": [],
                "communication": [],
                "referral_method": [],
                "available_time": [
                    {
                        "days_of_week": ["mon", "tue", "wed", "thu", "fri"],
                        "available_start_time": "09:00:00",
                        "available_end_time": "17:00:00",
                    }
                ],
                "not_available": [],
                "endpoint": [],
                "identifier": [],
            }
        },
    )

    active: bool | None = Field(
        False, description="Whether this healthcare service record is in active use."
    )
    name: str = Field(
        ...,
        description="Further description of the service as it would be presented to a consumer while searching.",
    )

    # providedBy (0..1) Reference(Organization)
    provided_by: str | None = Field(
        None,
        description="The organization that provides this healthcare service, as a FHIR reference string (e.g. 'Organization/190001').",
    )
    provided_by_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the providing organization in addition to the reference.",
    )
    provided_by_identifier_use: IdentifierUse | None = Field(
        None,
        description="Logical-identifier fallback for providedBy (used when the providing organization isn't a resource in this system) — identifies the purpose for that identifier, if known.",
    )
    provided_by_identifier_type_system: str | None = Field(
        None,
        description="Fallback identifier — the code system that defines the meaning of its type code.",
    )
    provided_by_identifier_type_version: str | None = Field(
        None,
        description="Fallback identifier — the version of the code system used for its type code.",
    )
    provided_by_identifier_type_code: str | None = Field(
        None,
        description="Fallback identifier — a symbol in syntax defined by the code system.",
    )
    provided_by_identifier_type_display: str | None = Field(
        None,
        description="Fallback identifier — a representation of the meaning of its type code.",
    )
    provided_by_identifier_type_text: str | None = Field(
        None,
        description="Fallback identifier — a human language representation of its type.",
    )
    provided_by_identifier_type_user_selected: bool | None = Field(
        None,
        description="Fallback identifier — whether its type coding was chosen by a user directly.",
    )
    provided_by_identifier_system: str | None = Field(
        None, description="Fallback identifier — the namespace URL for the value."
    )
    provided_by_identifier_value: str | None = Field(
        None,
        description="Fallback identifier — the portion typically relevant to the user, unique within the system.",
    )
    provided_by_identifier_period_start: datetime | None = Field(
        None, description="Fallback identifier — start of its validity period."
    )
    provided_by_identifier_period_end: datetime | None = Field(
        None, description="Fallback identifier — end of its validity period."
    )

    comment: str | None = Field(
        None,
        description="Any additional description of the service and/or any specific issues not covered elsewhere.",
    )
    extra_details: str | None = Field(
        None,
        description="Extra details about the service that can't be placed in the other fields (markdown).",
    )

    # photo (0..1 Attachment) — flattened
    photo_content_type: str | None = Field(
        None, description="MIME type of the photo (e.g. image/png)."
    )
    photo_language: str | None = Field(
        None, description="Human language of the photo content, as a BCP-47 code."
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
    photo_creation: datetime | None = Field(
        None, description="Date the photo attachment was first created."
    )

    appointment_required: bool | None = Field(
        None,
        description="Indicates whether or not a prospective consumer will require an appointment for this service.",
    )
    availability_exceptions: str | None = Field(
        None,
        description="A description of site availability exceptions, e.g. public holiday availability.",
    )

    identifier: list[HealthcareServiceIdentifierInput] | None = Field(
        None, description="External identifiers for this item."
    )
    category: list[HealthcareServiceCategoryInput] | None = Field(
        None,
        description="Identifies the broad category of service being performed or delivered.",
    )
    type: list[HealthcareServiceTypeInput] | None = Field(
        None,
        description="The specific type of service that may be delivered or performed.",
    )
    specialty: list[HealthcareServiceSpecialtyInput] | None = Field(
        None, description="Collection of specialties handled by the service site."
    )
    location: list[HealthcareServiceLocationInput] | None = Field(
        None,
        description="The location(s) where this healthcare service may be provided.",
    )
    telecom: list[HealthcareServiceTelecomInput] | None = Field(
        None, description="Contact details for the healthcare service."
    )
    coverage_area: list[HealthcareServiceCoverageAreaInput] | None = Field(
        None,
        description="The location(s) that this service is available to (not the location of the service).",
    )
    service_provision_code: list[HealthcareServiceServiceProvisionCodeInput] | None = (
        Field(
            None,
            description="The code(s) that detail the conditions under which the healthcare service is available/offered.",
        )
    )
    eligibility: list[HealthcareServiceEligibilityInput] | None = Field(
        None,
        description="Specific eligibility requirements required to use the service.",
    )
    program: list[HealthcareServiceProgramInput] | None = Field(
        None, description="Programs that this service is applicable to."
    )
    characteristic: list[HealthcareServiceCharacteristicInput] | None = Field(
        None, description="Collection of characteristics (attributes)."
    )
    communication: list[HealthcareServiceCommunicationInput] | None = Field(
        None,
        description="Ways that the service accepts referrals, if this is not provided then it is not necessary to check.",
    )
    referral_method: list[HealthcareServiceReferralMethodInput] | None = Field(
        None, description="Ways that the service accepts referrals."
    )
    available_time: list[HealthcareServiceAvailableTimeInput] | None = Field(
        None, description="A collection of times the healthcare service is available."
    )
    not_available: list[HealthcareServiceNotAvailableInput] | None = Field(
        None,
        description="The healthcare service is not available during this period of time due to the provided reason.",
    )
    endpoint: list[HealthcareServiceEndpointInput] | None = Field(
        None,
        description="Technical endpoints providing access to services operated for this healthcare service.",
    )


class HealthcareServicePatchSchema(BaseModel):
    """Partial update — only supplied fields are written. Every supplied
    sub-resource list (even `[]`) replaces the corresponding rows wholesale;
    omitted lists are left untouched. updated_by comes from the verified
    JWT (actor.sub), not a request body field."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "active": True,
                "name": "General Practice Consultation",
                "telecom": [{"system": "phone", "value": "555-1234", "use": "work"}],
            }
        },
    )

    active: bool | None = Field(
        None, description="Whether this healthcare service record is in active use."
    )
    name: str | None = Field(
        None,
        description="Further description of the service as it would be presented to a consumer while searching.",
    )

    provided_by: str | None = Field(
        None,
        description="The organization that provides this healthcare service, as a FHIR reference string (e.g. 'Organization/190001'). Set to null to clear.",
    )
    provided_by_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the providing organization in addition to the reference.",
    )
    provided_by_identifier_use: IdentifierUse | None = Field(
        None,
        description="Logical-identifier fallback for providedBy — identifies the purpose for that identifier, if known.",
    )
    provided_by_identifier_type_system: str | None = Field(
        None,
        description="Fallback identifier — the code system that defines the meaning of its type code.",
    )
    provided_by_identifier_type_version: str | None = Field(
        None,
        description="Fallback identifier — the version of the code system used for its type code.",
    )
    provided_by_identifier_type_code: str | None = Field(
        None,
        description="Fallback identifier — a symbol in syntax defined by the code system.",
    )
    provided_by_identifier_type_display: str | None = Field(
        None,
        description="Fallback identifier — a representation of the meaning of its type code.",
    )
    provided_by_identifier_type_text: str | None = Field(
        None,
        description="Fallback identifier — a human language representation of its type.",
    )
    provided_by_identifier_type_user_selected: bool | None = Field(
        None,
        description="Fallback identifier — whether its type coding was chosen by a user directly.",
    )
    provided_by_identifier_system: str | None = Field(
        None, description="Fallback identifier — the namespace URL for the value."
    )
    provided_by_identifier_value: str | None = Field(
        None,
        description="Fallback identifier — the portion typically relevant to the user, unique within the system.",
    )
    provided_by_identifier_period_start: datetime | None = Field(
        None, description="Fallback identifier — start of its validity period."
    )
    provided_by_identifier_period_end: datetime | None = Field(
        None, description="Fallback identifier — end of its validity period."
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
        None, description="Human language of the photo content, as a BCP-47 code."
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
    photo_creation: datetime | None = Field(
        None, description="Date the photo attachment was first created."
    )

    appointment_required: bool | None = Field(
        None,
        description="Indicates whether or not a prospective consumer will require an appointment.",
    )
    availability_exceptions: str | None = Field(
        None, description="A description of site availability exceptions."
    )

    identifier: list[HealthcareServiceIdentifierInput] | None = Field(
        None, description="External identifiers — replaces the full list if supplied."
    )
    category: list[HealthcareServiceCategoryInput] | None = Field(
        None,
        description="Broad category of service — replaces the full list if supplied.",
    )
    type: list[HealthcareServiceTypeInput] | None = Field(
        None,
        description="Specific type(s) of service — replaces the full list if supplied.",
    )
    specialty: list[HealthcareServiceSpecialtyInput] | None = Field(
        None, description="Specialties handled — replaces the full list if supplied."
    )
    location: list[HealthcareServiceLocationInput] | None = Field(
        None,
        description="Location(s) where this service may be provided — replaces the full list if supplied.",
    )
    telecom: list[HealthcareServiceTelecomInput] | None = Field(
        None, description="Contact detail(s) — replaces the full list if supplied."
    )
    coverage_area: list[HealthcareServiceCoverageAreaInput] | None = Field(
        None,
        description="Geographic coverage area(s) — replaces the full list if supplied.",
    )
    service_provision_code: list[HealthcareServiceServiceProvisionCodeInput] | None = (
        Field(
            None,
            description="Service provision code(s) — replaces the full list if supplied.",
        )
    )
    eligibility: list[HealthcareServiceEligibilityInput] | None = Field(
        None,
        description="Eligibility requirement(s) — replaces the full list if supplied.",
    )
    program: list[HealthcareServiceProgramInput] | None = Field(
        None, description="Applicable program(s) — replaces the full list if supplied."
    )
    characteristic: list[HealthcareServiceCharacteristicInput] | None = Field(
        None, description="Characteristic(s) — replaces the full list if supplied."
    )
    communication: list[HealthcareServiceCommunicationInput] | None = Field(
        None,
        description="Communication language(s) — replaces the full list if supplied.",
    )
    referral_method: list[HealthcareServiceReferralMethodInput] | None = Field(
        None, description="Referral method(s) — replaces the full list if supplied."
    )
    available_time: list[HealthcareServiceAvailableTimeInput] | None = Field(
        None,
        description="Available time window(s) — replaces the full list if supplied.",
    )
    not_available: list[HealthcareServiceNotAvailableInput] | None = Field(
        None,
        description="Not-available period(s) — replaces the full list if supplied.",
    )
    endpoint: list[HealthcareServiceEndpointInput] | None = Field(
        None, description="Technical endpoint(s) — replaces the full list if supplied."
    )


# ── Query-parameter schema (this gateway's own concept — no fhir-server equivalent) ──


class ListHealthcareServicesSchema(BaseModel):
    """Query parameters for listing healthcare services — mirrors fhir-server's
    Medplum-mirrored HealthcareService search parameter set.

    org_id is deliberately NOT a filter here: fhir-server always scopes
    HealthcareService reads to the caller's own org via the verified JWT
    (JWT/RBAC rollout) — matches Organization's/Location's ListXSchema.
    """

    active: bool | None = Field(None, description="Filter by active status.")
    name: str | None = Field(
        None, description="Partial match against the service name."
    )
    identifier: str | None = Field(
        None, description="Exact match on a business identifier value."
    )
    category: str | None = Field(
        None, description="Exact match on a coded service category."
    )
    service_type: str | None = Field(
        None, description="Exact match on a coded service type."
    )
    specialty: str | None = Field(
        None, description="Exact match on a coded specialty."
    )
    characteristic: str | None = Field(
        None, description="Exact match on a coded service characteristic."
    )
    program: str | None = Field(
        None, description="Exact match on a coded program supported by this service."
    )
    provided_by: str | None = Field(
        None,
        description="FHIR reference string to the providing Organization, e.g. 'Organization/190001'.",
    )
    location: str | None = Field(
        None, description="FHIR reference string, e.g. 'Location/230001'."
    )
    coverage_area: str | None = Field(
        None, description="FHIR reference string, e.g. 'Location/230001'."
    )
    endpoint: str | None = Field(
        None, description="FHIR reference string, e.g. 'Endpoint/1'."
    )
    sort: str | None = Field(None, description="Sort key, e.g. '-name'.")
    total_mode: Literal["accurate", "none"] = Field(
        "accurate", description="accurate|none — skip the COUNT(*) with 'none'."
    )
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)
