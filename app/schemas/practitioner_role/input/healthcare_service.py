"""PractitionerRole.healthcareService — mirrors fhir-server's
app/schemas/practitioner_role/input/healthcare_service.py field-for-field."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import IdentifierUse


class PractitionerRoleHealthcareServiceInput(BaseModel):
    """PractitionerRole.healthcareService — services provided at this role/location (Reference(HealthcareService))."""

    model_config = ConfigDict(extra="forbid")
    reference: str | None = Field(
        None,
        description="FHIR reference string to the healthcare service, e.g. 'HealthcareService/150001' — rejected with 422 if it doesn't exist in this org.",
    )
    reference_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the healthcare service in addition to the reference.",
    )
    reference_identifier_use: IdentifierUse | None = Field(
        None,
        description="Logical-identifier fallback (used when there's no resolvable HealthcareService reference) — identifies the purpose for that identifier, if known.",
    )
    reference_identifier_type_system: str | None = Field(
        None,
        description="Fallback identifier — the code system that defines the meaning of its type code.",
    )
    reference_identifier_type_version: str | None = Field(
        None,
        description="Fallback identifier — the version of the code system used for its type code.",
    )
    reference_identifier_type_code: str | None = Field(
        None,
        description="Fallback identifier — a symbol in syntax defined by the code system.",
    )
    reference_identifier_type_display: str | None = Field(
        None,
        description="Fallback identifier — a representation of the meaning of its type code.",
    )
    reference_identifier_type_text: str | None = Field(
        None,
        description="Fallback identifier — a human language representation of its type.",
    )
    reference_identifier_type_user_selected: bool | None = Field(
        None,
        description="Fallback identifier — whether its type coding was chosen by a user directly.",
    )
    reference_identifier_system: str | None = Field(
        None, description="Fallback identifier — the namespace URL for the value."
    )
    reference_identifier_value: str | None = Field(
        None,
        description="Fallback identifier — the portion typically relevant to the user, unique within the system.",
    )
    reference_identifier_period_start: datetime | None = Field(
        None, description="Fallback identifier — start of its validity period."
    )
    reference_identifier_period_end: datetime | None = Field(
        None, description="Fallback identifier — end of its validity period."
    )
