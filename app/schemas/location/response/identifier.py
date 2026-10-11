from pydantic import Field

from ._shared import _AuditFields


class LocationIdentifierResponse(_AuditFields):
    id: int = Field(..., description="Internal row ID — use for sub-resource lookups.")
    use: str | None = Field(
        None, description="Identifies the purpose for this identifier, if known."
    )
    type_system: str | None = Field(
        None,
        description="The code system that defines the meaning of the identifier type code.",
    )
    type_version: str | None = Field(
        None,
        description="The version of the code system used for the identifier type code.",
    )
    type_code: str | None = Field(
        None,
        description="A symbol in syntax defined by the code system (e.g. NPI, DEA, license).",
    )
    type_display: str | None = Field(
        None, description="A representation of the meaning of the identifier type code."
    )
    type_text: str | None = Field(
        None, description="A human language representation of the identifier's type."
    )
    type_user_selected: bool | None = Field(
        None,
        description="Whether this identifier-type coding was chosen by a user directly.",
    )
    system: str | None = Field(
        None, description="Establishes the namespace for the value."
    )
    value: str | None = Field(
        None,
        description="The portion of the identifier typically relevant to the user, unique within the system.",
    )
    period_start: str | None = Field(
        None,
        description="Start of the time period during which this identifier is/was valid for use.",
    )
    period_end: str | None = Field(
        None,
        description="End of the time period during which this identifier is/was valid for use.",
    )
    assigner: str | None = Field(
        None,
        description="Resolved FHIR reference to the issuing organization, e.g. 'Organization/190001'.",
    )
    assigner_id: int | None = Field(
        None, description="Public ID of the resolved assigning Organization, if any."
    )
    assigner_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the assigning organization.",
    )
    assigner_identifier_use: str | None = Field(
        None, description="Fallback identifier — its purpose, if known."
    )
    assigner_identifier_type_system: str | None = Field(
        None, description="Fallback identifier — code system for its type."
    )
    assigner_identifier_type_version: str | None = Field(
        None, description="Fallback identifier — version of the type code system."
    )
    assigner_identifier_type_code: str | None = Field(
        None, description="Fallback identifier — code for its type."
    )
    assigner_identifier_type_display: str | None = Field(
        None, description="Fallback identifier — display for its type."
    )
    assigner_identifier_type_text: str | None = Field(
        None, description="Fallback identifier — human language rendering of its type."
    )
    assigner_identifier_type_user_selected: bool | None = Field(
        None, description="Fallback identifier — whether its type was user-selected."
    )
    assigner_identifier_system: str | None = Field(
        None, description="Fallback identifier — namespace URL for the value."
    )
    assigner_identifier_value: str | None = Field(
        None, description="Fallback identifier — value within the given system."
    )
    assigner_identifier_period_start: str | None = Field(
        None, description="Fallback identifier — start of validity period."
    )
    assigner_identifier_period_end: str | None = Field(
        None, description="Fallback identifier — end of validity period."
    )
