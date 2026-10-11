"""HealthcareService.eligibility — mirrors fhir-server's
app/schemas/healthcare_service/input/eligibility.py field-for-field."""

from pydantic import BaseModel, ConfigDict, Field


class HealthcareServiceEligibilityInput(BaseModel):
    """HealthcareService.eligibility — specific eligibility requirements for using the service (BackboneElement)."""

    model_config = ConfigDict(extra="forbid")
    code_system: str | None = Field(
        None,
        description="Coding for the eligibility code — the identification of the code system that defines its meaning.",
    )
    code_version: str | None = Field(
        None,
        description="The version of the code system which was used when choosing this code.",
    )
    code_code: str | None = Field(
        None, description="A symbol in syntax defined by the code system."
    )
    code_display: str | None = Field(
        None, description="A representation of the meaning of the eligibility code."
    )
    code_text: str | None = Field(
        None,
        description="A human language representation of the eligibility code, as seen/selected/entered by the user.",
    )
    code_user_selected: bool | None = Field(
        None, description="Indicates that this coding was chosen by a user directly."
    )
    comment: str | None = Field(
        None,
        description="Describes the eligibility conditions in more detail, as free text or an HTML fragment.",
    )
