"""
Top-level Organization response models, mirroring
app/schemas/organization/response/core.py's `Plain*` models in the
fhir-server repo field-for-field, dropping the `Plain` prefix — same
convention as app/schemas/patient/response.py and
app/schemas/practitioner/response.py (this gateway has no separate
FHIR-camelCase GraphQL shape; that's a REST-only content-negotiation
concept — see app/schemas/organization/fhir_schemas.py for the REST-only
OpenAPI-documentation models).

`extra="allow"` is set on all models so new fields added to the fhir-server
response are passed through transparently without requiring a schema update
here first — but note GraphQL can only *query* fields explicitly declared
below (strawberry's `all_fields=True` maps declared Pydantic fields to
GraphQL fields), so a genuinely new field still needs adding here to become
queryable.
"""

from pydantic import BaseModel, ConfigDict, Field

from .address import OrganizationAddressResponse
from .alias import OrganizationAliasResponse
from .contact import OrganizationContactResponse
from .endpoint import OrganizationEndpointResponse
from .identifier import OrganizationIdentifierResponse
from .telecom import OrganizationTelecomResponse
from .type import OrganizationTypeResponse


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int = Field(..., description="Public organization_id.")
    active: bool | None = Field(
        None, description="Whether the organization's record is still in active use."
    )
    name: str | None = Field(
        None, description="A name associated with the organization."
    )
    partof_reference: str | None = Field(
        None,
        description="The raw literal reference string as received — relative or an absolute URL to another system entirely — kept independently of whether it resolves locally.",
    )
    partof: str | None = Field(
        None,
        description="Resolved FHIR reference to the parent organization, e.g. 'Organization/190001' — populated only when partof_reference resolves to a local row.",
    )
    partof_type: str | None = Field(
        None, description="Resolved reference target type (always 'Organization')."
    )
    partof_id: int | None = Field(
        None, description="Internal ID of the resolved parent Organization, if any."
    )
    partof_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the parent organization.",
    )
    partof_identifier_use: str | None = Field(
        None, description="Fallback identifier — its purpose, if known."
    )
    partof_identifier_type_system: str | None = Field(
        None, description="Fallback identifier — code system for its type."
    )
    partof_identifier_type_version: str | None = Field(
        None, description="Fallback identifier — version of the type code system."
    )
    partof_identifier_type_code: str | None = Field(
        None, description="Fallback identifier — code for its type."
    )
    partof_identifier_type_display: str | None = Field(
        None, description="Fallback identifier — display for its type."
    )
    partof_identifier_type_text: str | None = Field(
        None, description="Fallback identifier — human language rendering of its type."
    )
    partof_identifier_type_user_selected: bool | None = Field(
        None, description="Fallback identifier — whether its type was user-selected."
    )
    partof_identifier_system: str | None = Field(
        None, description="Fallback identifier — namespace URL for the value."
    )
    partof_identifier_value: str | None = Field(
        None, description="Fallback identifier — value within the given system."
    )
    partof_identifier_period_start: str | None = Field(
        None, description="Fallback identifier — start of validity period."
    )
    partof_identifier_period_end: str | None = Field(
        None, description="Fallback identifier — end of validity period."
    )
    identifier: list[OrganizationIdentifierResponse] | None = Field(
        None,
        description="Identifier(s) for the organization that is used to identify the organization across multiple disparate systems.",
    )
    type: list[OrganizationTypeResponse] | None = Field(
        None, description="The kind(s) of organization that this is."
    )
    alias: list[OrganizationAliasResponse] | None = Field(
        None,
        description="A list of alternate names that the organization is known as, or was known as in the past.",
    )
    telecom: list[OrganizationTelecomResponse] | None = Field(
        None, description="A contact detail for the organization."
    )
    address: list[OrganizationAddressResponse] | None = Field(
        None, description="An address for the organization."
    )
    contact: list[OrganizationContactResponse] | None = Field(
        None, description="Contact for the organization for a certain purpose."
    )
    endpoint: list[OrganizationEndpointResponse] | None = Field(
        None,
        description="Technical endpoints providing access to services operated for the organization.",
    )
    extension: list[dict] | None = Field(
        None,
        description="Resource-level FHIR extensions, as raw [{url, valueType, value}, ...] entries.",
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


class PaginatedOrganizationResponse(BaseModel):
    total: int | None = Field(
        None, description="Total matching rows (null when total_mode=none)."
    )
    limit: int = Field(..., description="Page size used for this response.")
    offset: int = Field(..., description="Number of rows skipped before this page.")
    data: list[OrganizationResponse]
