"""
Pydantic input schemas for the Organization resource, mirroring
app/schemas/organization/input.py in the fhir-server repo field-for-field
(same class names, same fields) — kept in sync manually, same convention as
app/schemas/patient/input.py and app/schemas/practitioner/input.py.

Organization is a set-once-rarely-edited resource on fhir-server — unlike
Patient/Practitioner there are no standalone sub-resource endpoints, so each
sub-resource has a single input shape (no separate Patch variant): every
supplied list on OrganizationCreateSchema/OrganizationPatchSchema (even `[]`)
replaces the corresponding rows wholesale.

org_id/created_by/updated_by are NOT exposed: fhir-server derives org_id from
the verified JWT's `activeOrganizationId` claim and created_by/updated_by from
its `sub` claim (JWT/RBAC rollout) — a client-supplied value for any of the
three would be rejected outright (extra="forbid", no such field declared).
Unlike every other resource, Organization has no user_id field at all — it's
a shared tenant-level entity, not scoped to an individual end-user.

ListOrganizationsSchema is this gateway's own query-parameter schema
(fhir-server has no GraphQL/query-args concept) — mirroring fhir-server's
current Medplum-style Organization list filter set. There is no
MeOrganizationsSchema/myOrganizations equivalent — that only ever existed to
filter by user_id, which fhir-server no longer supports for Organization.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import (
    AddressType,
    AddressUse,
    ContactPointSystem,
    ContactPointUse,
    HumanNameUse,
    IdentifierUse,
)

# ── Sub-resource schemas (mirror fhir-server exactly) ──────────────────────────


class OrganizationIdentifierInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    use: IdentifierUse | None = Field(
        None,
        description="Identifies the purpose for this identifier, if known — usual|official|temp|secondary|old.",
    )
    type_system: str | None = Field(
        None,
        description="The identification of the code system that defines the meaning of the identifier type code.",
    )
    type_version: str | None = Field(
        None,
        description="The version of the code system which was used when choosing this identifier type code.",
    )
    type_code: str | None = Field(
        None,
        description="A symbol in syntax defined by the code system (e.g. NPI, DEA, license).",
    )
    type_display: str | None = Field(
        None,
        description="A representation of the meaning of the identifier type code, following the rules of the system.",
    )
    type_text: str | None = Field(
        None,
        description="A human language representation of the identifier's type, as seen/selected/entered by the user.",
    )
    type_user_selected: bool | None = Field(
        None,
        description="Indicates that this identifier-type coding was chosen by a user directly, e.g. off a pick list of available items.",
    )
    system: str | None = Field(
        None,
        description="Establishes the namespace for the value — that is, a URL that describes a set of unique values.",
    )
    value: str = Field(
        ...,
        description="The portion of the identifier typically relevant to the user and which is unique within the context of the system.",
    )
    period_start: datetime | None = Field(
        None,
        description="Start of the time period during which this identifier is/was valid for use.",
    )
    period_end: datetime | None = Field(
        None,
        description="End of the time period during which this identifier is/was valid for use.",
    )
    assigner: str | None = Field(
        None,
        description="Organization that issued/manages this identifier, as a FHIR reference string (e.g. 'Organization/190001').",
    )
    assigner_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the assigning organization in addition to the reference.",
    )
    assigner_identifier_use: IdentifierUse | None = Field(
        None,
        description="Logical-identifier fallback for the assigner (used when it isn't a resource in this system) — identifies the purpose for that identifier, if known.",
    )
    assigner_identifier_type_system: str | None = Field(
        None,
        description="Fallback identifier — the code system that defines the meaning of its type code.",
    )
    assigner_identifier_type_version: str | None = Field(
        None,
        description="Fallback identifier — the version of the code system used for its type code.",
    )
    assigner_identifier_type_code: str | None = Field(
        None,
        description="Fallback identifier — a symbol in syntax defined by the code system.",
    )
    assigner_identifier_type_display: str | None = Field(
        None,
        description="Fallback identifier — a representation of the meaning of its type code.",
    )
    assigner_identifier_type_text: str | None = Field(
        None,
        description="Fallback identifier — a human language representation of its type.",
    )
    assigner_identifier_type_user_selected: bool | None = Field(
        None,
        description="Fallback identifier — whether its type coding was chosen by a user directly.",
    )
    assigner_identifier_system: str | None = Field(
        None, description="Fallback identifier — the namespace URL for the value."
    )
    assigner_identifier_value: str | None = Field(
        None,
        description="Fallback identifier — the portion typically relevant to the user, unique within the system.",
    )
    assigner_identifier_period_start: datetime | None = Field(
        None, description="Fallback identifier — start of its validity period."
    )
    assigner_identifier_period_end: datetime | None = Field(
        None, description="Fallback identifier — end of its validity period."
    )


class OrganizationTypeInput(BaseModel):
    """Organization.type — the kind(s) of organization that this is (CodeableConcept)."""

    model_config = ConfigDict(extra="forbid")
    coding_system: str | None = Field(
        None,
        description="The identification of the code system that defines the meaning of the symbol in the code.",
    )
    coding_version: str | None = Field(
        None,
        description="The version of the code system which was used when choosing this code.",
    )
    coding_code: str | None = Field(
        None,
        description="A symbol in syntax defined by the code system (e.g. 'prov' for Healthcare Provider).",
    )
    coding_display: str | None = Field(
        None,
        description="A representation of the meaning of the code in the system, following the rules of the system.",
    )
    text: str | None = Field(
        None,
        description="A human language representation of the organization type, as seen/selected/entered by the user.",
    )
    coding_user_selected: bool | None = Field(
        None,
        description="Indicates that this coding was chosen by a user directly, e.g. off a pick list of available items.",
    )


class OrganizationAliasInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str = Field(
        ...,
        description="An alternate name that the organization is known as, or was known as in the past.",
    )


class OrganizationTelecomInput(BaseModel):
    """Organization.telecom — a contact detail for the organization (ContactPoint)."""

    model_config = ConfigDict(extra="forbid")
    system: ContactPointSystem = Field(
        ...,
        description="Telecommunications form for the contact point — what communications system is required to make use of it: phone|fax|email|pager|url|sms|other.",
    )
    value: str = Field(
        ...,
        description="The actual contact point details, in a form meaningful to the designated communication system (e.g. a phone number or email address).",
    )
    use: ContactPointUse | None = Field(
        None,
        description="Identifies the purpose for the contact point — home|work|temp|old|mobile.",
    )
    rank: int | None = Field(
        None,
        ge=1,
        description="Specifies a preferred order in which to use a set of contacts. Lower values are more preferred than higher values.",
    )
    period_start: datetime | None = Field(
        None,
        description="Start of the time period when this contact point was/is in use.",
    )
    period_end: datetime | None = Field(
        None,
        description="End of the time period when this contact point was/is in use.",
    )


class OrganizationAddressInput(BaseModel):
    """Organization.address — an address for the organization (Address)."""

    model_config = ConfigDict(extra="forbid")
    use: AddressUse | None = Field(
        None, description="The purpose of this address — home|work|temp|old|billing."
    )
    type: AddressType = Field(
        ...,
        description="Distinguishes between physical addresses (those you can visit) and mailing addresses (e.g. PO Boxes and care-of addresses) — postal|physical|both.",
    )
    text: str | None = Field(
        None,
        description="Specifies the entire address as it should be displayed, e.g. on a postal label.",
    )
    line: list[str] | None = Field(
        None,
        description="The house number, apartment number, street name, street direction, P.O. Box number, delivery hints, and similar information.",
    )
    city: str = Field(
        ...,
        description="The name of the city, town, suburb, village or other community or delivery center.",
    )
    district: str | None = Field(
        None, description="The name of the administrative area (county)."
    )
    state: str = Field(
        ...,
        description="Sub-unit of a country with limited sovereignty in a federally organized country.",
    )
    postal_code: str = Field(
        ...,
        description="A postal code designating a region defined by the postal service.",
    )
    country: str = Field(
        ...,
        description="Country — a nation as commonly understood or generally accepted.",
    )
    period_start: datetime | None = Field(
        None, description="Start of the time period when this address was/is in use."
    )
    period_end: datetime | None = Field(
        None, description="End of the time period when this address was/is in use."
    )


class OrganizationContactTelecomInput(BaseModel):
    """Organization.contact.telecom — a contact detail for the contact person (ContactPoint)."""

    model_config = ConfigDict(extra="forbid")
    system: ContactPointSystem = Field(
        ...,
        description="Telecommunications form for the contact point — what communications system is required to make use of it: phone|fax|email|pager|url|sms|other.",
    )
    value: str = Field(
        ...,
        description="The actual contact point details, in a form meaningful to the designated communication system.",
    )
    use: ContactPointUse | None = Field(
        None,
        description="Identifies the purpose for the contact point — home|work|temp|old|mobile.",
    )
    rank: int | None = Field(
        None,
        ge=1,
        description="Specifies a preferred order in which to use a set of contacts. Lower values are more preferred than higher values.",
    )
    period_start: datetime | None = Field(
        None,
        description="Start of the time period when this contact point was/is in use.",
    )
    period_end: datetime | None = Field(
        None,
        description="End of the time period when this contact point was/is in use.",
    )


class OrganizationContactInput(BaseModel):
    """Organization.contact — contact for the organization for a certain purpose (BackboneElement)."""

    model_config = ConfigDict(extra="forbid")
    purpose_system: str | None = Field(
        None,
        description="The identification of the code system that defines the meaning of the contact's purpose code.",
    )
    purpose_code: str | None = Field(
        None,
        description="A symbol in syntax defined by the code system (e.g. 'ADMIN', 'BILL', 'PRESS').",
    )
    purpose_display: str | None = Field(
        None,
        description="A representation of the meaning of the purpose code, following the rules of the system.",
    )
    purpose_text: str | None = Field(
        None, description="A human language representation of the contact's purpose."
    )
    name_use: HumanNameUse | None = Field(
        None, description="Identifies the purpose for this name."
    )
    name_text: str | None = Field(
        None,
        description="Specifies the entire name as it should be displayed, e.g. on an application UI.",
    )
    name_family: str | None = Field(
        None, description="The part of the name that links to the genealogy."
    )
    name_given: list[str] | None = Field(None, description="Given name(s).")
    name_prefix: list[str] | None = Field(
        None,
        description="Part(s) of the name acquired as a title due to academic, legal, employment or nobility status, etc., appearing at the start of the name.",
    )
    name_suffix: list[str] | None = Field(
        None,
        description="Part(s) of the name acquired as a title due to academic, legal, employment or nobility status, etc., appearing at the end of the name.",
    )
    name_period_start: datetime | None = Field(
        None,
        description="Start of the period during which this name was valid for the contact.",
    )
    name_period_end: datetime | None = Field(
        None,
        description="End of the period during which this name was valid for the contact.",
    )
    address_use: AddressUse | None = Field(
        None, description="The purpose of this address — home|work|temp|old|billing."
    )
    address_type: AddressType = Field(
        ...,
        description="Distinguishes between physical addresses (those you can visit) and mailing addresses — postal|physical|both.",
    )
    address_text: str | None = Field(
        None,
        description="Specifies the entire address as it should be displayed, e.g. on a postal label.",
    )
    address_line: list[str] | None = Field(
        None,
        description="The house number, apartment number, street name, and similar information.",
    )
    address_city: str = Field(
        ...,
        description="The name of the city, town, suburb, village or other community or delivery center.",
    )
    address_district: str | None = Field(
        None, description="The name of the administrative area (county)."
    )
    address_state: str = Field(
        ...,
        description="Sub-unit of a country with limited sovereignty in a federally organized country.",
    )
    address_postal_code: str = Field(
        ...,
        description="A postal code designating a region defined by the postal service.",
    )
    address_country: str = Field(
        ...,
        description="Country — a nation as commonly understood or generally accepted.",
    )
    address_period_start: datetime | None = Field(
        None, description="Start of the time period when this address was/is in use."
    )
    address_period_end: datetime | None = Field(
        None, description="End of the time period when this address was/is in use."
    )
    telecom: list[OrganizationContactTelecomInput] | None = Field(
        None,
        description="A contact detail (e.g. a telephone number or an email address) by which the contact person may be reached.",
    )


class OrganizationEndpointInput(BaseModel):
    """Organization.endpoint — technical endpoints providing access to services
    operated for the organization (Reference(Endpoint))."""

    model_config = ConfigDict(extra="forbid")
    reference: str | None = Field(
        None,
        description="FHIR reference string to the endpoint, e.g. 'Endpoint/1' (Endpoint is not a modeled resource in this system — supply the identifier fallback fields below when there's nothing to reference).",
    )
    reference_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the endpoint in addition to the reference.",
    )
    reference_identifier_use: IdentifierUse | None = Field(
        None,
        description="Logical-identifier fallback (used when there's no resolvable Endpoint reference) — identifies the purpose for that identifier, if known.",
    )
    reference_identifier_type_system: str | None = Field(
        None,
        description="Fallback identifier — the code system that defines the meaning of its type code.",
    )
    reference_identifier_type_version: str | None = Field(
        None,
        description="Fallback identifier — the version of the code system used for its type code.",
    )
    reference_identifier_type_code: str | None = Field(
        None,
        description="Fallback identifier — a symbol in syntax defined by the code system.",
    )
    reference_identifier_type_display: str | None = Field(
        None,
        description="Fallback identifier — a representation of the meaning of its type code.",
    )
    reference_identifier_type_text: str | None = Field(
        None,
        description="Fallback identifier — a human language representation of its type.",
    )
    reference_identifier_type_user_selected: bool | None = Field(
        None,
        description="Fallback identifier — whether its type coding was chosen by a user directly.",
    )
    reference_identifier_system: str | None = Field(
        None, description="Fallback identifier — the namespace URL for the value."
    )
    reference_identifier_value: str | None = Field(
        None,
        description="Fallback identifier — the portion typically relevant to the user, unique within the system.",
    )
    reference_identifier_period_start: datetime | None = Field(
        None, description="Fallback identifier — start of its validity period."
    )
    reference_identifier_period_end: datetime | None = Field(
        None, description="Fallback identifier — end of its validity period."
    )


# ── Create / Patch schemas ─────────────────────────────────────────────────────


class OrganizationCreateSchema(BaseModel):
    """Creates an Organization and any combination of its sub-resources
    (identifier, type, alias, telecom, address, contact, endpoint) atomically
    in one request — Organization has no separate scalar-only vs. full
    create split like Patient/Practitioner, since it's set once at onboarding
    rather than built up incrementally. org_id and created_by both come from
    the verified JWT (actor.org_id / actor.sub) — neither is a request body
    field. Unlike every other resource, Organization has no user_id field at
    all — it's a shared tenant-level entity, not scoped to an individual
    end-user."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "active": True,
                "name": "General Hospital",
                "partof": "Organization/190001",
                "partof_display": "Parent Health System",
                "identifier": [
                    {
                        "value": "12345",
                        "system": "http://example.org/facility-ids",
                        "use": "official",
                    }
                ],
                "type": [
                    {
                        "coding_system": "http://terminology.hl7.org/CodeSystem/organization-type",
                        "coding_code": "prov",
                        "coding_display": "Healthcare Provider",
                    }
                ],
                "alias": [{"value": "Gen Hosp"}],
                "telecom": [{"system": "phone", "value": "555-1234", "use": "work"}],
                "address": [
                    {
                        "use": "work",
                        "type": "both",
                        "line": ["123 Main St"],
                        "city": "Anytown",
                        "state": "CA",
                        "postal_code": "12345",
                        "country": "US",
                    }
                ],
                "contact": [
                    {
                        "purpose_code": "ADMIN",
                        "purpose_system": "http://terminology.hl7.org/CodeSystem/contactentity-type",
                        "name_family": "Smith",
                        "name_given": ["John"],
                        "address_type": "both",
                        "address_city": "Anytown",
                        "address_state": "CA",
                        "address_postal_code": "12345",
                        "address_country": "US",
                        "telecom": [{"system": "phone", "value": "555-0001"}],
                    }
                ],
                "endpoint": [],
            }
        },
    )

    active: bool | None = Field(
        None, description="Whether the organization's record is still in active use."
    )
    name: str | None = Field(
        None, description="A name associated with the organization."
    )
    partof: str | None = Field(
        None,
        description="The organization of which this organization forms a part, as a FHIR reference string (e.g. 'Organization/190001').",
    )
    partof_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the parent organization in addition to the reference.",
    )
    partof_identifier_use: IdentifierUse | None = Field(
        None,
        description="Logical-identifier fallback for partOf (used when the parent organization isn't a resource in this system) — identifies the purpose for that identifier, if known.",
    )
    partof_identifier_type_system: str | None = Field(
        None,
        description="Fallback identifier — the code system that defines the meaning of its type code.",
    )
    partof_identifier_type_version: str | None = Field(
        None,
        description="Fallback identifier — the version of the code system used for its type code.",
    )
    partof_identifier_type_code: str | None = Field(
        None,
        description="Fallback identifier — a symbol in syntax defined by the code system.",
    )
    partof_identifier_type_display: str | None = Field(
        None,
        description="Fallback identifier — a representation of the meaning of its type code.",
    )
    partof_identifier_type_text: str | None = Field(
        None,
        description="Fallback identifier — a human language representation of its type.",
    )
    partof_identifier_type_user_selected: bool | None = Field(
        None,
        description="Fallback identifier — whether its type coding was chosen by a user directly.",
    )
    partof_identifier_system: str | None = Field(
        None, description="Fallback identifier — the namespace URL for the value."
    )
    partof_identifier_value: str | None = Field(
        None,
        description="Fallback identifier — the portion typically relevant to the user, unique within the system.",
    )
    partof_identifier_period_start: datetime | None = Field(
        None, description="Fallback identifier — start of its validity period."
    )
    partof_identifier_period_end: datetime | None = Field(
        None, description="Fallback identifier — end of its validity period."
    )

    identifier: list[OrganizationIdentifierInput] | None = Field(
        None,
        description="Identifier(s) for the organization that is used to identify the organization across multiple disparate systems.",
    )
    type: list[OrganizationTypeInput] | None = Field(
        None, description="The kind(s) of organization that this is."
    )
    alias: list[OrganizationAliasInput] | None = Field(
        None,
        description="A list of alternate names that the organization is known as, or was known as in the past.",
    )
    telecom: list[OrganizationTelecomInput] | None = Field(
        None, description="A contact detail for the organization."
    )
    address: list[OrganizationAddressInput] | None = Field(
        None, description="An address for the organization."
    )
    contact: list[OrganizationContactInput] | None = Field(
        None, description="Contact for the organization for a certain purpose."
    )
    endpoint: list[OrganizationEndpointInput] | None = Field(
        None,
        description="Technical endpoints providing access to services operated for the organization.",
    )


class OrganizationPatchSchema(BaseModel):
    """Partial update — only supplied fields are written. Every supplied
    sub-resource list (even `[]`) replaces the corresponding rows wholesale;
    omitted lists are left untouched. No separate scalar-only vs. full patch
    split — see OrganizationCreateSchema's docstring. updated_by comes from
    the verified JWT (actor.sub), not a request body field."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "active": True,
                "name": "General Hospital",
                "alias": [{"value": "Gen Hosp"}],
                "telecom": [{"system": "phone", "value": "555-1234", "use": "work"}],
            }
        },
    )

    active: bool | None = Field(
        None, description="Whether the organization's record is still in active use."
    )
    name: str | None = Field(
        None, description="A name associated with the organization."
    )
    partof: str | None = Field(
        None,
        description="The organization of which this organization forms a part, as a FHIR reference string (e.g. 'Organization/190001'). Set to null to clear.",
    )
    partof_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the parent organization in addition to the reference.",
    )
    partof_identifier_use: IdentifierUse | None = Field(
        None,
        description="Logical-identifier fallback for partOf — identifies the purpose for that identifier, if known.",
    )
    partof_identifier_type_system: str | None = Field(
        None,
        description="Fallback identifier — the code system that defines the meaning of its type code.",
    )
    partof_identifier_type_version: str | None = Field(
        None,
        description="Fallback identifier — the version of the code system used for its type code.",
    )
    partof_identifier_type_code: str | None = Field(
        None,
        description="Fallback identifier — a symbol in syntax defined by the code system.",
    )
    partof_identifier_type_display: str | None = Field(
        None,
        description="Fallback identifier — a representation of the meaning of its type code.",
    )
    partof_identifier_type_text: str | None = Field(
        None,
        description="Fallback identifier — a human language representation of its type.",
    )
    partof_identifier_type_user_selected: bool | None = Field(
        None,
        description="Fallback identifier — whether its type coding was chosen by a user directly.",
    )
    partof_identifier_system: str | None = Field(
        None, description="Fallback identifier — the namespace URL for the value."
    )
    partof_identifier_value: str | None = Field(
        None,
        description="Fallback identifier — the portion typically relevant to the user, unique within the system.",
    )
    partof_identifier_period_start: datetime | None = Field(
        None, description="Fallback identifier — start of its validity period."
    )
    partof_identifier_period_end: datetime | None = Field(
        None, description="Fallback identifier — end of its validity period."
    )

    identifier: list[OrganizationIdentifierInput] | None = Field(
        None,
        description="Identifier(s) for the organization — replaces the full list if supplied.",
    )
    type: list[OrganizationTypeInput] | None = Field(
        None,
        description="The kind(s) of organization that this is — replaces the full list if supplied.",
    )
    alias: list[OrganizationAliasInput] | None = Field(
        None,
        description="Alternate name(s) for the organization — replaces the full list if supplied.",
    )
    telecom: list[OrganizationTelecomInput] | None = Field(
        None,
        description="Contact detail(s) for the organization — replaces the full list if supplied.",
    )
    address: list[OrganizationAddressInput] | None = Field(
        None,
        description="Address(es) for the organization — replaces the full list if supplied.",
    )
    contact: list[OrganizationContactInput] | None = Field(
        None,
        description="Contact(s) for the organization — replaces the full list if supplied.",
    )
    endpoint: list[OrganizationEndpointInput] | None = Field(
        None,
        description="Technical endpoint(s) for the organization — replaces the full list if supplied.",
    )


# ── Query-parameter schemas (this gateway's own concept — no fhir-server equivalent) ──


class ListOrganizationsSchema(BaseModel):
    """Query parameters for listing organizations — mirrors fhir-server's
    Medplum-mirrored Organization search parameter set.

    org_id is deliberately NOT a filter here: fhir-server always scopes
    Organization reads to the caller's own org via the verified JWT (JWT/RBAC
    rollout) — matches Patient's/Practitioner's ListXSchema.
    """

    active: bool | None = Field(None, description="Filter by active status.")
    name: str | None = Field(
        None,
        description="Partial, case-insensitive match against organization name or any alias.",
    )
    identifier: str | None = Field(
        None, description="Exact match on a business identifier value."
    )
    org_type: str | None = Field(
        None, description="Exact match on a coded organization type (FHIR `type`)."
    )
    address: str | None = Field(
        None,
        description="Partial match against any Address sub-field (line, city, district, state, country, postalCode, text).",
    )
    address_city: str | None = Field(
        None, description="Filter by address city — partial match."
    )
    address_state: str | None = Field(
        None, description="Filter by address state — partial match."
    )
    address_postal_code: str | None = Field(
        None, description="Filter by address postal code — exact match."
    )
    address_country: str | None = Field(
        None, description="Filter by address country — partial match."
    )
    address_use: AddressUse | None = Field(
        None, description="home|work|temp|old|billing."
    )
    partof: str | None = Field(
        None, description="FHIR reference string, e.g. 'Organization/190001'."
    )
    endpoint: str | None = Field(
        None, description="FHIR reference string, e.g. 'Endpoint/1'."
    )
    sort: str | None = Field(None, description="Sort key, e.g. '-name'.")
    total_mode: str = Field(
        "accurate", description="accurate|none — skip the COUNT(*) with 'none'."
    )
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)
