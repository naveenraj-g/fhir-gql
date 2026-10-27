"""
FHIR R4 Attachment datatype — content in a format defined elsewhere.

Spec: https://hl7.org/fhir/R4/datatypes.html#Attachment
"""

from pydantic import BaseModel, Field


class FhirAttachment(BaseModel):
    contentType: str | None = Field(
        default=None, description="Mime type of the content, e.g. image/png"
    )
    language: str | None = Field(
        default=None, description="Human language of the content, as a BCP-47 code"
    )
    data: str | None = Field(default=None, description="The actual data, base64-encoded")
    url: str | None = Field(
        default=None, description="A URI where the data can be found instead of inline"
    )
    size: int | None = Field(
        default=None,
        description="Number of bytes of content, measured after decoding, if applicable",
    )
    hash: str | None = Field(
        default=None, description="Base64-encoded hash (SHA-1) of the data"
    )
    title: str | None = Field(
        default=None, description="Label to display in place of the content"
    )
    creation: str | None = Field(
        default=None, description="ISO 8601 datetime the attachment was first created"
    )
