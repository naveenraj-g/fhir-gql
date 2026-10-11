"""
Create/Patch/List schemas for the Organization resource, mirroring
app/schemas/organization/input/core.py in the fhir-server repo field-for-field
(same class names, same fields, same required/optional split) — kept in sync
manually, same convention as app/schemas/patient/input.py and
app/schemas/practitioner/input.py.

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
(fhir-server has no GraphQL/query-args concept, so it has no file-level
counterpart to mirror) — mirroring fhir-server's current Medplum-style
Organization list filter set. There is no MeOrganizationsSchema/
myOrganizations equivalent — that only ever existed to filter by user_id,
which fhir-server no longer supports for Organization.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import AddressUse, IdentifierUse

from .address import OrganizationAddressInput
from .alias import OrganizationAliasInput
from .contact import OrganizationContactInput
from .endpoint import OrganizationEndpointInput
from .identifier import OrganizationIdentifierInput
from .telecom import OrganizationTelecomInput
from .type import OrganizationTypeInput

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
        False, description="Whether the organization's record is still in active use."
    )
    name: str = Field(..., description="A name associated with the organization.")
    # partOf (0..1) Reference(Organization) — "The organization of which this organization forms a part."
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


# ── Query-parameter schema (this gateway's own concept — no fhir-server equivalent) ──


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
    total_mode: Literal["accurate", "none"] = Field(
        "accurate", description="accurate|none — skip the COUNT(*) with 'none'."
    )
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)
