"""Organization coding — mirrors fhir-server's
app/schemas/organization/input/_shared.py field-for-field."""

from pydantic import BaseModel, ConfigDict, Field


class OrganizationCodingInput(BaseModel):
    """One entry of a CodeableConcept's `coding[]` — reused wherever
    Organization has a CodeableConcept whose coding is modeled as a real
    0..* list (Organization.type, Organization.identifier.type,
    Organization.contact.purpose): an org may need its own custom code for
    a concept AND a crosswalk to a standard terminology (e.g. SNOMED CT) at
    the same time. NOT used for a Reference's own logical-identifier
    fallback .type (e.g. identifier.assigner.identifier.type) — those stay a
    single flattened coding, since they're a reference's fallback, not a
    first-class identifier/type of this resource."""

    model_config = ConfigDict(extra="forbid")
    system: str | None = Field(
        None,
        description="The identification of the code system that defines the meaning of the symbol in the code.",
    )
    version: str | None = Field(
        None,
        description="The version of the code system which was used when choosing this code.",
    )
    code: str | None = Field(
        None,
        description="A symbol in syntax defined by the code system.",
    )
    display: str | None = Field(
        None,
        description="A representation of the meaning of the code in the system, following the rules of the system.",
    )
    user_selected: bool | None = Field(
        None,
        description="Indicates that this coding was chosen by a user directly, e.g. off a pick list of available items.",
    )
