"""Organization.type — mirrors fhir-server's
app/schemas/organization/input/type.py field-for-field."""

from pydantic import BaseModel, ConfigDict, Field


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
