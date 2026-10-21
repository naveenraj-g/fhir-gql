"""
Pydantic models representing the genuine FHIR R4 Organization resource
shape — the canonical shape shared by every connector and by the GraphQL
boundary itself.

Lives at the app level (app.fhir), not under any one connector, because
it isn't connector-specific: app.connectors.internal.translators.organization
and app.connectors.medplum.translators.organization both translate their
connector's own wire format to/from this same shape (see
app.connectors.base.OrganizationWireTranslator), and app.gql.organization's
types/queries/mutations import these models directly as the GraphQL
boundary's canonical shape, rather than redefining a second, drifting copy
of "what does a FHIR R4 Organization look like".

Every reusable, non-primitive FHIR datatype (Coding, CodeableConcept,
Period, Identifier, ContactPoint, Address, HumanName, Reference) is
imported from app.fhir.schemas.datatypes rather than redefined here — see
that package's docstring. Only `FhirOrgContact` stays local: it's not a
general-purpose FHIR datatype, it's Organization's own `contact`
BackboneElement (an anonymous nested structure the R4 spec defines
specifically for this resource, with no reuse across other resources).

`FhirOrganizationInput` is the write-side counterpart, used by both
`createFhirOrganization`/`updateFhirOrganization` (see
app.gql.organization.mutations) — see its own docstring for why one shape
covers both create and update.

FHIR R4 Organization resource spec: https://hl7.org/fhir/R4/organization.html
"""

from pydantic import BaseModel, Field

from app.fhir.schemas.datatypes import (
    FhirAddress,
    FhirCodeableConcept,
    FhirContactPoint,
    FhirHumanName,
    FhirIdentifier,
    FhirMeta,
    FhirReference,
)


class FhirOrgContact(BaseModel):
    purpose: FhirCodeableConcept | None = Field(
        default=None, description="The type of contact (ADMIN, BILL, HR, PATINF, PRESS)"
    )
    name: FhirHumanName | None = Field(
        default=None, description="A name associated with the contact"
    )
    telecom: list[FhirContactPoint] | None = Field(
        default=None, description="Contact details for the person"
    )
    address: FhirAddress | None = Field(
        default=None, description="Visiting or postal address for the contact"
    )


class FhirOrgResponse(BaseModel):
    resourceType: str = Field(
        default="Organization",
        description="Always 'Organization' — identifies the FHIR resource type",
    )
    id: str = Field(
        description="Logical FHIR resource ID (string representation of the DB primary key)"
    )
    meta: FhirMeta | None = Field(
        default=None,
        description=(
            "Infrastructure-maintained resource metadata — lastUpdated, plus "
            "org_id/created_by/updated_by/created_at as extensions (FHIR R4's "
            "Meta has no native field for those). Response-only: not part of "
            "FhirOrganizationInput, since this is server-derived audit/tenant "
            "data, not something a client writes."
        ),
    )
    extension: list[dict] | None = Field(
        default=None,
        description="Resource-level FHIR extensions, as raw [{url, valueType, value}, ...] entries",
    )
    active: bool | None = Field(
        default=None,
        description="Whether the organisation's record is still in active use",
    )
    name: str | None = Field(default=None, description="Name used for the organisation")
    identifier: list[FhirIdentifier] | None = Field(
        default=None, description="Identifies this organisation across multiple systems"
    )
    type: list[FhirCodeableConcept] | None = Field(
        default=None,
        description="Kind(s) of organisation (prov, dept, team, govt, ins, etc.)",
    )
    alias: list[str] | None = Field(
        default=None,
        description="A list of alternate names the organisation is known as",
    )
    telecom: list[FhirContactPoint] | None = Field(
        default=None, description="A contact detail for the organisation"
    )
    address: list[FhirAddress] | None = Field(
        default=None, description="An address for the organisation"
    )
    partOf: FhirReference | None = Field(
        default=None,
        description="The organisation of which this organisation forms a part",
    )
    contact: list[FhirOrgContact] | None = Field(
        default=None, description="Contact for the organisation for a certain purpose"
    )
    endpoint: list[FhirReference] | None = Field(
        default=None,
        description="Technical endpoints providing access to services operated for the organisation",
    )


class FhirBundleEntry(BaseModel):
    resource: FhirOrgResponse = Field(
        description="The FHIR Organization resource contained in this entry"
    )


class FhirBundleResponse(BaseModel):
    resourceType: str = Field(default="Bundle", description="Always 'Bundle'")
    type: str = Field(
        default="searchset", description="Always 'searchset' for search/list results"
    )
    total: int = Field(
        description="Total number of matching resources (before pagination)"
    )
    entry: list[FhirBundleEntry] | None = Field(
        default=None, description="Results — each entry wraps one Organization resource"
    )


class FhirOrganizationInput(BaseModel):
    """
    The write-side counterpart to FhirOrgResponse — same genuine FHIR R4
    Organization shape, minus `resourceType`/`id` (the id is a separate
    `id: str` mutation argument on update; create doesn't take one at all).

    Used as-is for BOTH create and update: fhir-server's own
    OrganizationCreateSchema/OrganizationPatchSchema are themselves nearly
    identical (Organization has no required-at-this-layer fields), so
    there is no create-vs-patch shape difference to encode here either.
    Any field a connector's translator can't reach on write (e.g. a
    Reference's logical-identifier fallback — fhir-server's
    partof_identifier_*/assigner_identifier_*/reference_identifier_*,
    since FhirReference/FhirIdentifier.assigner don't carry one) is simply
    left unset by that translator — see
    app.connectors.internal.translators.organization and
    app.connectors.medplum.translators.organization.
    """

    active: bool | None = Field(default=None)
    name: str | None = Field(default=None)
    identifier: list[FhirIdentifier] | None = Field(default=None)
    type: list[FhirCodeableConcept] | None = Field(default=None)
    alias: list[str] | None = Field(default=None)
    telecom: list[FhirContactPoint] | None = Field(default=None)
    address: list[FhirAddress] | None = Field(default=None)
    partOf: FhirReference | None = Field(default=None)
    contact: list[FhirOrgContact] | None = Field(default=None)
    endpoint: list[FhirReference] | None = Field(default=None)
    extension: list[dict] | None = Field(default=None)
