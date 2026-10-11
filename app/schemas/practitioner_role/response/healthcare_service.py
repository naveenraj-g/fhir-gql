from pydantic import Field

from ._shared import _AuditFields


class PractitionerRoleHealthcareServiceResponse(_AuditFields):
    id: int = Field(..., description="Internal row ID — use for sub-resource lookups.")
    reference: str | None = Field(
        None,
        description="Resolved FHIR reference to the healthcare service, e.g. 'HealthcareService/150001'.",
    )
    reference_type: str | None = Field(
        None, description="Resolved reference target type (always 'HealthcareService')."
    )
    reference_id: int | None = Field(
        None,
        description="Public healthcare_service_id of the resolved HealthcareService, if any.",
    )
    reference_display: str | None = Field(
        None, description="Plain text narrative that identifies the healthcare service."
    )
    reference_identifier_use: str | None = Field(
        None, description="Fallback identifier — its purpose, if known."
    )
    reference_identifier_type_system: str | None = Field(
        None, description="Fallback identifier — code system for its type."
    )
    reference_identifier_type_version: str | None = Field(
        None, description="Fallback identifier — version of the type code system."
    )
    reference_identifier_type_code: str | None = Field(
        None, description="Fallback identifier — code for its type."
    )
    reference_identifier_type_display: str | None = Field(
        None, description="Fallback identifier — display for its type."
    )
    reference_identifier_type_text: str | None = Field(
        None, description="Fallback identifier — human language rendering of its type."
    )
    reference_identifier_type_user_selected: bool | None = Field(
        None, description="Fallback identifier — whether its type was user-selected."
    )
    reference_identifier_system: str | None = Field(
        None, description="Fallback identifier — namespace URL for the value."
    )
    reference_identifier_value: str | None = Field(
        None, description="Fallback identifier — value within the given system."
    )
    reference_identifier_period_start: str | None = Field(
        None, description="Fallback identifier — start of validity period."
    )
    reference_identifier_period_end: str | None = Field(
        None, description="Fallback identifier — end of validity period."
    )
