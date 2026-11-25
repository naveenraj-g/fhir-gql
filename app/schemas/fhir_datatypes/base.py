"""Element and BackboneElement: the bases of every FHIR datatype model (hand-kept)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.schemas.fhir_datatypes import Extension, String


class Element(BaseModel):
    "Base definition for all elements in a resource: a unique `id` within the resource and (safe-to-ignore) `extension`s."

    # `extra=ignore`: the validated raw body, not these models, is what gets stored, so an element
    # a model does not declare is never lost.
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: String | None = Field(
        None,
        description="Unique id for the element within a resource (for internal references). This may be any string value that does not contain spaces.",
    )
    extension: list[Extension] | None = Field(
        None,
        description="May be used to represent additional information that is not part of the basic definition of the element. To make the use of extensions safe and manageable, there is a strict set of governance  applied to the definition and use of extensions. Though any implementer can define an extension, there is a set of requirements that SHALL be met as part of the definition of the extension.",
    )


class BackboneElement(Element):
    "Base definition for all elements that contain other elements: an Element that can also carry `modifierExtension`, which cannot be ignored if unrecognized."

    modifierExtension: list[Extension] | None = Field(
        None,
        description="May be used to represent additional information that is not part of the basic definition of the element and that modifies the understanding of the element in which it is contained and/or the understanding of the containing element's descendants. Usually modifier elements provide negation or qualification. To make the use of extensions safe and manageable, there is a strict set of governance applied to the definition and use of extensions. Though any implementer can define an extension, there is a set of requirements that SHALL be met as part of the definition of the extension. Applications processing a resource are required to check for modifier extensions.\n\nModifier extensions SHALL NOT change the meaning of any elements on Resource or DomainResource (including cannot change the meaning of modifierExtension itself).",
    )
