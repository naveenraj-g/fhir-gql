"""
FHIR R4 Meta datatype — infrastructure-maintained metadata about a
resource (lastUpdated, versionId, profile, security, tag, ...).

`security`/`tag` reuse FhirCoding since both are 0..* Coding per spec.
`extension` is where resource metadata with no native Meta field rides —
e.g. fhir-server's Organization org_id/created_by/updated_by/created_at
(see app.fhir.mappers.organization.fhir._fhir_meta in that project) — same
raw, not-yet-registered-extension-definition convention as a resource's
own top-level `extension` field.

Spec: https://hl7.org/fhir/R4/resource.html#Meta
"""

from pydantic import BaseModel, Field

from app.fhir.schemas.datatypes.coding import FhirCoding


class FhirMeta(BaseModel):
    versionId: str | None = Field(default=None, description="Version-specific identifier")
    lastUpdated: str | None = Field(
        default=None, description="ISO-8601 instant the resource version last changed"
    )
    source: str | None = Field(
        default=None,
        description="URI identifying where this resource currently resides or was generated",
    )
    profile: list[str] | None = Field(
        default=None, description="Canonical URLs of profiles this resource claims to conform to"
    )
    security: list[FhirCoding] | None = Field(
        default=None, description="Security labels applied to this resource"
    )
    tag: list[FhirCoding] | None = Field(
        default=None, description="Tags applied to this resource for workflow/categorization"
    )
    extension: list[dict] | None = Field(
        default=None,
        description="Meta-level FHIR extensions, as raw [{url, valueType, value}, ...] entries",
    )
