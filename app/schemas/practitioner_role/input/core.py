"""
Create/Patch/List schemas for the PractitionerRole resource, mirroring
app/schemas/practitioner_role/input/core.py in the fhir-server repo
field-for-field (same class names, same fields, same required/optional
split) — kept in sync manually, same convention as
app/schemas/organization/input/core.py.

org_id/created_by/updated_by are NOT exposed: fhir-server derives org_id
from the verified JWT's `activeOrganizationId` claim and created_by/
updated_by from its `sub` claim (JWT/RBAC rollout) — a client-supplied
value for any of the three would be rejected outright (extra="forbid", no
such field declared). Like Organization/Location/HealthcareService,
PractitionerRole has no user_id field at all — it's a shared tenant-level
entity, not scoped to an individual end-user.

NOTE: fhir-server's PractitionerRole has NO `characteristic`, `communication`,
or `contact`/`availability`-group sub-resources — those don't exist on the
FHIR R4 PractitionerRole resource at all (see
https://www.hl7.org/fhir/R4/practitionerrole.html — its actual elements are
identifier, active, period, practitioner, organization, code, specialty,
location, healthcareService, telecom, availableTime, notAvailable,
availabilityExceptions, endpoint). The pre-port gql schema carried those
three extra sub-resources plus a wrapping "availability" group around
available_time/not_available — neither matches the spec or fhir-server's
actual model, and both are dropped here. `telecom` (top-level, not nested)
and flat `available_time`/`not_available` lists are the correct R4 shape.

ListPractitionerRolesSchema is this gateway's own query-parameter schema
(fhir-server has no GraphQL/query-args concept, so it has no file-level
counterpart to mirror) — mirroring fhir-server's current Medplum-style
PractitionerRole search parameter set (see
app/routers/practitioner_role/core.py's list_practitioner_roles() on
fhir-server).
"""

from datetime import date as date_, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import IdentifierUse

from .available_time import PractitionerRoleAvailableTimeInput
from .code import PractitionerRoleCodeInput
from .endpoint import PractitionerRoleEndpointInput
from .healthcare_service import PractitionerRoleHealthcareServiceInput
from .identifier import PractitionerRoleIdentifierInput
from .location import PractitionerRoleLocationInput
from .not_available import PractitionerRoleNotAvailableInput
from .specialty import PractitionerRoleSpecialtyInput
from .telecom import PractitionerRoleTelecomInput


class PractitionerRoleCreateSchema(BaseModel):
    """Creates a PractitionerRole and any combination of its 9 sub-resource
    lists atomically in one request — same set-once-then-patch shape as
    Organization/HealthcareService, no separate scalar-only vs. full create
    split. org_id and created_by both come from the verified JWT (actor.org_id
    / actor.sub) — neither is a request body field. Like Organization,
    Location, and HealthcareService, PractitionerRole has no user_id field at
    all — it's a shared tenant-level entity (which practitioners may act in
    which roles at this org), not scoped to an individual end-user."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "active": True,
                "period_start": "2024-01-01T00:00:00Z",
                "practitioner": "Practitioner/30001",
                "practitioner_display": "Dr. Jane Smith",
                "organization": "Organization/190001",
                "organization_display": "General Hospital",
                "availability_exceptions": "Not available on public holidays",
                "code": [
                    {
                        "coding_system": "http://snomed.info/sct",
                        "coding_code": "59058001",
                        "coding_display": "General physician",
                    }
                ],
                "specialty": [
                    {
                        "coding_system": "http://snomed.info/sct",
                        "coding_code": "394814009",
                        "coding_display": "General practice",
                    }
                ],
                "location": [],
                "healthcare_service": [],
                "telecom": [{"system": "phone", "value": "555-1234", "use": "work"}],
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
        False, description="Whether this practitioner role record is in active use."
    )

    # period (0..1 Period) — flattened
    period_start: datetime | None = Field(
        None,
        description="Start of the period during which the practitioner is authorized to perform in these role(s).",
    )
    period_end: datetime | None = Field(
        None,
        description="End of the period during which the practitioner is authorized to perform in these role(s).",
    )

    # practitioner (0..1) Reference(Practitioner)
    practitioner: str | None = Field(
        None,
        description="Practitioner providing services for the organization, as a FHIR reference string (e.g. 'Practitioner/30001').",
    )
    practitioner_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the practitioner in addition to the reference.",
    )
    practitioner_identifier_use: IdentifierUse | None = Field(
        None,
        description="Logical-identifier fallback for practitioner (used when the practitioner isn't a resource in this system) — identifies the purpose for that identifier, if known.",
    )
    practitioner_identifier_type_system: str | None = Field(
        None,
        description="Fallback identifier — the code system that defines the meaning of its type code.",
    )
    practitioner_identifier_type_version: str | None = Field(
        None,
        description="Fallback identifier — the version of the code system used for its type code.",
    )
    practitioner_identifier_type_code: str | None = Field(
        None,
        description="Fallback identifier — a symbol in syntax defined by the code system.",
    )
    practitioner_identifier_type_display: str | None = Field(
        None,
        description="Fallback identifier — a representation of the meaning of its type code.",
    )
    practitioner_identifier_type_text: str | None = Field(
        None,
        description="Fallback identifier — a human language representation of its type.",
    )
    practitioner_identifier_type_user_selected: bool | None = Field(
        None,
        description="Fallback identifier — whether its type coding was chosen by a user directly.",
    )
    practitioner_identifier_system: str | None = Field(
        None, description="Fallback identifier — the namespace URL for the value."
    )
    practitioner_identifier_value: str | None = Field(
        None,
        description="Fallback identifier — the portion typically relevant to the user, unique within the system.",
    )
    practitioner_identifier_period_start: datetime | None = Field(
        None, description="Fallback identifier — start of its validity period."
    )
    practitioner_identifier_period_end: datetime | None = Field(
        None, description="Fallback identifier — end of its validity period."
    )

    # organization (0..1) Reference(Organization)
    organization: str | None = Field(
        None,
        description="Organization where the roles are available, as a FHIR reference string (e.g. 'Organization/190001').",
    )
    organization_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the organization in addition to the reference.",
    )
    organization_identifier_use: IdentifierUse | None = Field(
        None,
        description="Logical-identifier fallback for organization (used when the organization isn't a resource in this system) — identifies the purpose for that identifier, if known.",
    )
    organization_identifier_type_system: str | None = Field(
        None,
        description="Fallback identifier — the code system that defines the meaning of its type code.",
    )
    organization_identifier_type_version: str | None = Field(
        None,
        description="Fallback identifier — the version of the code system used for its type code.",
    )
    organization_identifier_type_code: str | None = Field(
        None,
        description="Fallback identifier — a symbol in syntax defined by the code system.",
    )
    organization_identifier_type_display: str | None = Field(
        None,
        description="Fallback identifier — a representation of the meaning of its type code.",
    )
    organization_identifier_type_text: str | None = Field(
        None,
        description="Fallback identifier — a human language representation of its type.",
    )
    organization_identifier_type_user_selected: bool | None = Field(
        None,
        description="Fallback identifier — whether its type coding was chosen by a user directly.",
    )
    organization_identifier_system: str | None = Field(
        None, description="Fallback identifier — the namespace URL for the value."
    )
    organization_identifier_value: str | None = Field(
        None,
        description="Fallback identifier — the portion typically relevant to the user, unique within the system.",
    )
    organization_identifier_period_start: datetime | None = Field(
        None, description="Fallback identifier — start of its validity period."
    )
    organization_identifier_period_end: datetime | None = Field(
        None, description="Fallback identifier — end of its validity period."
    )

    availability_exceptions: str | None = Field(
        None,
        description="A description of site availability exceptions, e.g. public holiday availability.",
    )

    identifier: list[PractitionerRoleIdentifierInput] | None = Field(
        None, description="Business identifiers that are specific to a role/location."
    )
    code: list[PractitionerRoleCodeInput] | None = Field(
        None, description="Roles which this practitioner may perform."
    )
    specialty: list[PractitionerRoleSpecialtyInput] | None = Field(
        None, description="Specific expertise of the practitioner."
    )
    location: list[PractitionerRoleLocationInput] | None = Field(
        None, description="The location(s) at which this practitioner provides care."
    )
    healthcare_service: list[PractitionerRoleHealthcareServiceInput] | None = Field(
        None, description="Healthcare services provided at this role/location."
    )
    telecom: list[PractitionerRoleTelecomInput] | None = Field(
        None, description="Contact details that are specific to the role/location/service."
    )
    available_time: list[PractitionerRoleAvailableTimeInput] | None = Field(
        None, description="A collection of times the role is available."
    )
    not_available: list[PractitionerRoleNotAvailableInput] | None = Field(
        None,
        description="This role is not available during this period of time due to the provided reason.",
    )
    endpoint: list[PractitionerRoleEndpointInput] | None = Field(
        None,
        description="Technical endpoints providing access to services operated for this role.",
    )


class PractitionerRolePatchSchema(BaseModel):
    """Partial update — only supplied fields are written. Every supplied
    sub-resource list (even `[]`) replaces the corresponding rows wholesale;
    omitted lists are left untouched. updated_by comes from the verified
    JWT (actor.sub), not a request body field.

    Every field/sub-resource list is patchable here — fhir-server's
    repository re-validates practitioner/organization/location[]/
    healthcare_service[] references on patch the same way it does on
    create (see app/repository/practitioner_role/full.py)."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "active": True,
                "telecom": [{"system": "phone", "value": "555-1234", "use": "work"}],
            }
        },
    )

    active: bool | None = Field(
        None, description="Whether this practitioner role record is in active use."
    )
    period_start: datetime | None = Field(
        None,
        description="Start of the period during which the practitioner is authorized to perform in these role(s).",
    )
    period_end: datetime | None = Field(
        None,
        description="End of the period during which the practitioner is authorized to perform in these role(s).",
    )

    practitioner: str | None = Field(
        None,
        description="Practitioner providing services for the organization, as a FHIR reference string (e.g. 'Practitioner/30001'). Set to null to clear.",
    )
    practitioner_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the practitioner in addition to the reference.",
    )
    practitioner_identifier_use: IdentifierUse | None = Field(
        None,
        description="Logical-identifier fallback for practitioner — identifies the purpose for that identifier, if known.",
    )
    practitioner_identifier_type_system: str | None = Field(
        None,
        description="Fallback identifier — the code system that defines the meaning of its type code.",
    )
    practitioner_identifier_type_version: str | None = Field(
        None,
        description="Fallback identifier — the version of the code system used for its type code.",
    )
    practitioner_identifier_type_code: str | None = Field(
        None,
        description="Fallback identifier — a symbol in syntax defined by the code system.",
    )
    practitioner_identifier_type_display: str | None = Field(
        None,
        description="Fallback identifier — a representation of the meaning of its type code.",
    )
    practitioner_identifier_type_text: str | None = Field(
        None,
        description="Fallback identifier — a human language representation of its type.",
    )
    practitioner_identifier_type_user_selected: bool | None = Field(
        None,
        description="Fallback identifier — whether its type coding was chosen by a user directly.",
    )
    practitioner_identifier_system: str | None = Field(
        None, description="Fallback identifier — the namespace URL for the value."
    )
    practitioner_identifier_value: str | None = Field(
        None,
        description="Fallback identifier — the portion typically relevant to the user, unique within the system.",
    )
    practitioner_identifier_period_start: datetime | None = Field(
        None, description="Fallback identifier — start of its validity period."
    )
    practitioner_identifier_period_end: datetime | None = Field(
        None, description="Fallback identifier — end of its validity period."
    )

    organization: str | None = Field(
        None,
        description="Organization where the roles are available, as a FHIR reference string (e.g. 'Organization/190001'). Set to null to clear.",
    )
    organization_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the organization in addition to the reference.",
    )
    organization_identifier_use: IdentifierUse | None = Field(
        None,
        description="Logical-identifier fallback for organization — identifies the purpose for that identifier, if known.",
    )
    organization_identifier_type_system: str | None = Field(
        None,
        description="Fallback identifier — the code system that defines the meaning of its type code.",
    )
    organization_identifier_type_version: str | None = Field(
        None,
        description="Fallback identifier — the version of the code system used for its type code.",
    )
    organization_identifier_type_code: str | None = Field(
        None,
        description="Fallback identifier — a symbol in syntax defined by the code system.",
    )
    organization_identifier_type_display: str | None = Field(
        None,
        description="Fallback identifier — a representation of the meaning of its type code.",
    )
    organization_identifier_type_text: str | None = Field(
        None,
        description="Fallback identifier — a human language representation of its type.",
    )
    organization_identifier_type_user_selected: bool | None = Field(
        None,
        description="Fallback identifier — whether its type coding was chosen by a user directly.",
    )
    organization_identifier_system: str | None = Field(
        None, description="Fallback identifier — the namespace URL for the value."
    )
    organization_identifier_value: str | None = Field(
        None,
        description="Fallback identifier — the portion typically relevant to the user, unique within the system.",
    )
    organization_identifier_period_start: datetime | None = Field(
        None, description="Fallback identifier — start of its validity period."
    )
    organization_identifier_period_end: datetime | None = Field(
        None, description="Fallback identifier — end of its validity period."
    )

    availability_exceptions: str | None = Field(
        None, description="A description of site availability exceptions."
    )

    identifier: list[PractitionerRoleIdentifierInput] | None = Field(
        None, description="Business identifiers — replaces the full list if supplied."
    )
    code: list[PractitionerRoleCodeInput] | None = Field(
        None,
        description="Roles which this practitioner may perform — replaces the full list if supplied.",
    )
    specialty: list[PractitionerRoleSpecialtyInput] | None = Field(
        None, description="Specialties — replaces the full list if supplied."
    )
    location: list[PractitionerRoleLocationInput] | None = Field(
        None,
        description="Location(s) at which this practitioner provides care — replaces the full list if supplied.",
    )
    healthcare_service: list[PractitionerRoleHealthcareServiceInput] | None = Field(
        None,
        description="Healthcare service(s) — replaces the full list if supplied.",
    )
    telecom: list[PractitionerRoleTelecomInput] | None = Field(
        None, description="Contact detail(s) — replaces the full list if supplied."
    )
    available_time: list[PractitionerRoleAvailableTimeInput] | None = Field(
        None,
        description="Available time window(s) — replaces the full list if supplied.",
    )
    not_available: list[PractitionerRoleNotAvailableInput] | None = Field(
        None,
        description="Not-available period(s) — replaces the full list if supplied.",
    )
    endpoint: list[PractitionerRoleEndpointInput] | None = Field(
        None, description="Technical endpoint(s) — replaces the full list if supplied."
    )


# ── Query-parameter schema (this gateway's own concept — no fhir-server equivalent) ──


class ListPractitionerRolesSchema(BaseModel):
    """Query parameters for listing practitioner roles — mirrors fhir-server's
    Medplum-mirrored PractitionerRole search parameter set.

    org_id is deliberately NOT a filter here: fhir-server always scopes
    PractitionerRole reads to the caller's own org via the verified JWT
    (JWT/RBAC rollout) — matches Organization's ListOrganizationsSchema.
    """

    active: bool | None = Field(None, description="Filter by active status.")
    date: date_ | None = Field(
        None,
        description="ISO date — matches rows whose period contains it (period.start <= date <= period.end).",
    )
    email: str | None = Field(
        None, description="Exact match against a telecom entry with system='email'."
    )
    phone: str | None = Field(
        None, description="Exact match against a telecom entry with system='phone'."
    )
    telecom: str | None = Field(
        None, description="Exact match against any telecom value, regardless of system."
    )
    identifier: str | None = Field(
        None, description="Exact match on a business identifier value."
    )
    role: str | None = Field(
        None, description="Exact match on a coded role (code[])."
    )
    specialty: str | None = Field(
        None, description="Exact match on a coded specialty."
    )
    practitioner: str | None = Field(
        None,
        description="FHIR reference string to the practitioner, e.g. 'Practitioner/30001'.",
    )
    organization: str | None = Field(
        None,
        description="FHIR reference string to the organization, e.g. 'Organization/190001'.",
    )
    location: str | None = Field(
        None, description="FHIR reference string, e.g. 'Location/230001'."
    )
    service: str | None = Field(
        None, description="FHIR reference string, e.g. 'HealthcareService/150001'."
    )
    endpoint: str | None = Field(
        None, description="FHIR reference string, e.g. 'Endpoint/1'."
    )
    sort: str | None = Field(None, description="Sort key, e.g. '-created_at'.")
    total_mode: Literal["accurate", "none"] = Field(
        "accurate", description="accurate|none — skip the COUNT(*) with 'none'."
    )
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)
