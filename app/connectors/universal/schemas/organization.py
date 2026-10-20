"""
The one canonical, FHIR R4-shaped Organization schema used at the GraphQL
boundary for the universal-FHIR-GraphQL experiment (see
app.connectors.universal's package docstring).

Reused as-is from app.connectors.internal.schemas.organization.fhir_schemas
rather than redefined here: those models already describe the genuine FHIR
R4 Organization shape (originally written only to document fhir-server's
own `Accept: application/fhir+json` response for OpenAPI purposes) — there
is nothing internal-connector-specific about the shape itself, only about
where it happened to be defined. Importing it here keeps a single source of
truth for "what does a FHIR R4 Organization look like" instead of a second,
drifting copy.

One module per resource (this one, more to follow as the experiment grows
past Organization) — see app.connectors.universal.schemas's __init__.py.
"""

from pydantic import BaseModel, Field

from app.connectors.internal.schemas.organization.fhir_schemas import (
    FhirAddress,
    FhirCodeableConcept,
    FhirCoding,
    FhirContactPoint,
    FhirHumanName,
    FhirIdentifier,
    FhirOrgContact,
    FhirOrgResponse,
    FhirPeriod,
    FhirReference,
)


class FhirOrganizationInput(BaseModel):
    """
    The write-side counterpart to FhirOrgResponse — same genuine FHIR R4
    Organization shape, minus `resourceType`/`id` (the id is a separate
    `id: str` mutation argument on update; create doesn't take one at all).

    Used as-is for BOTH create and update: fhir-server's own
    OrganizationCreateSchema/OrganizationPatchSchema are themselves nearly
    identical (Organization has no required-at-this-layer fields, see that
    module's docstring), so there is no create-vs-patch shape difference to
    encode here either. Any field a connector's translator can't reach on
    write (e.g. a Reference's logical-identifier fallback — fhir-server's
    partof_identifier_*/assigner_identifier_*/reference_identifier_* — since
    FhirReference/FhirIdentifier.assigner don't carry one) is simply left
    unset by that translator; see
    app.connectors.universal.translators.organization's
    to_wire_create/to_wire_patch.
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


__all__ = [
    "FhirAddress",
    "FhirCodeableConcept",
    "FhirCoding",
    "FhirContactPoint",
    "FhirHumanName",
    "FhirIdentifier",
    "FhirOrgContact",
    "FhirOrganizationInput",
    "FhirOrgResponse",
    "FhirPeriod",
    "FhirReference",
]
