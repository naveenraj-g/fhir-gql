"""Organization.identifier — mirrors fhir-server's
app/schemas/organization/input/identifier.py field-for-field."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import IdentifierUse

from ._shared import OrganizationCodingInput


class OrganizationIdentifierInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    use: IdentifierUse | None = Field(
        None,
        description="Identifies the purpose for this identifier, if known — usual|official|temp|secondary|old.",
    )
    # type (0..1 CodeableConcept) — type_text is the CodeableConcept's own
    # field; type_coding is the real 0..* coding list (an org may need its
    # own custom identifier-type code AND a standard crosswalk at once). This
    # is distinct from assigner_identifier_type_* below (the *assigner's*
    # Identifier fallback's .type), which stays a single flattened coding —
    # see OrganizationCodingInput's docstring.
    type_coding: list[OrganizationCodingInput] | None = Field(
        None,
        description="Coding(s) for this identifier's type — e.g. NPI, DEA, license.",
    )
    type_text: str | None = Field(
        None,
        description="A human language representation of the identifier's type, as seen/selected/entered by the user.",
    )
    system: str | None = Field(
        None,
        description="Establishes the namespace for the value — that is, a URL that describes a set of unique values.",
    )
    value: str | None = Field(
        None,
        description="The portion of the identifier typically relevant to the user and which is unique within the context of the system.",
    )
    period_start: datetime | None = Field(
        None,
        description="Start of the time period during which this identifier is/was valid for use.",
    )
    period_end: datetime | None = Field(
        None,
        description="End of the time period during which this identifier is/was valid for use.",
    )
    assigner: str | None = Field(
        None,
        description="Organization that issued/manages this identifier, as a FHIR reference string (e.g. 'Organization/190001').",
    )
    assigner_display: str | None = Field(
        None,
        description="Plain text narrative that identifies the assigning organization in addition to the reference.",
    )
    assigner_identifier_use: IdentifierUse | None = Field(
        None,
        description="Logical-identifier fallback for the assigner (used when it isn't a resource in this system) — identifies the purpose for that identifier, if known.",
    )
    assigner_identifier_type_system: str | None = Field(
        None,
        description="Fallback identifier — the code system that defines the meaning of its type code.",
    )
    assigner_identifier_type_version: str | None = Field(
        None,
        description="Fallback identifier — the version of the code system used for its type code.",
    )
    assigner_identifier_type_code: str | None = Field(
        None,
        description="Fallback identifier — a symbol in syntax defined by the code system.",
    )
    assigner_identifier_type_display: str | None = Field(
        None,
        description="Fallback identifier — a representation of the meaning of its type code.",
    )
    assigner_identifier_type_text: str | None = Field(
        None,
        description="Fallback identifier — a human language representation of its type.",
    )
    assigner_identifier_type_user_selected: bool | None = Field(
        None,
        description="Fallback identifier — whether its type coding was chosen by a user directly.",
    )
    assigner_identifier_system: str | None = Field(
        None, description="Fallback identifier — the namespace URL for the value."
    )
    assigner_identifier_value: str | None = Field(
        None,
        description="Fallback identifier — the portion typically relevant to the user, unique within the system.",
    )
    assigner_identifier_period_start: datetime | None = Field(
        None, description="Fallback identifier — start of its validity period."
    )
    assigner_identifier_period_end: datetime | None = Field(
        None, description="Fallback identifier — end of its validity period."
    )
