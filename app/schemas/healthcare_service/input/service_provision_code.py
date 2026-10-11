"""HealthcareService.serviceProvisionCode — mirrors fhir-server's
app/schemas/healthcare_service/input/service_provision_code.py field-for-field.

Note the class name: HealthcareServiceServiceProvisionCodeInput (double
"Service") — matches fhir-server exactly, not the old
HealthcareServiceProvisionCodeInput this gateway used pre-JWT-rollout."""

from pydantic import BaseModel, ConfigDict, Field


class HealthcareServiceServiceProvisionCodeInput(BaseModel):
    """HealthcareService.serviceProvisionCode — conditions under which the service is available/offered (CodeableConcept)."""

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
        None, description="A symbol in syntax defined by the code system."
    )
    coding_display: str | None = Field(
        None, description="A representation of the meaning of the code in the system."
    )
    text: str | None = Field(
        None,
        description="A human language representation of the provision code, as seen/selected/entered by the user.",
    )
    coding_user_selected: bool | None = Field(
        None, description="Indicates that this coding was chosen by a user directly."
    )
