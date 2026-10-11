"""PractitionerRole.code — mirrors fhir-server's
app/schemas/practitioner_role/input/code.py field-for-field."""

from pydantic import BaseModel, ConfigDict, Field


class PractitionerRoleCodeInput(BaseModel):
    """PractitionerRole.code — roles which this practitioner may perform (CodeableConcept)."""

    model_config = ConfigDict(extra="forbid")
    coding_system: str | None = Field(
        None, description="The code system that defines the meaning of this code."
    )
    coding_version: str | None = Field(
        None, description="The version of the code system which was used."
    )
    coding_code: str | None = Field(
        None, description="A symbol in syntax defined by the code system."
    )
    coding_display: str | None = Field(
        None, description="A representation of the meaning of the code."
    )
    text: str | None = Field(
        None, description="A human language representation of the role."
    )
    coding_user_selected: bool | None = Field(
        None, description="Indicates that this coding was chosen by a user directly."
    )
